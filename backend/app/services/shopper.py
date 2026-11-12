import asyncio
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant import get_merchant_by_id
from app.data_access.order import create_order, create_order_items, get_order
from app.data_access.processing_state import record_domain_activity
from app.data_access.product import decrement_inventory, get_product_variant_with_product
from app.data_access.shopper import (
    enrich_shopper_email,
    get_shopper as dal_get_shopper,
    list_merchant_shoppers_paginated,
    upsert_shopper,
)
from app.data_access.shopper_events import list_shopper_events_paginated
from app.models.shopper import Shopper
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import (
    CheckoutStartedPayload,
    PurchaseCompletedPayload,
    SessionStartedPayload,
)
from app.schemas.shopper import ShopperActivityEventResponse


class IdentityConflictError(ValueError):
    """Raised when an event attempts to assign an email to a shopper that already belongs to another shopper."""


class UnresolvedReferenceError(ValueError):
    """Raised when a referenced Product, ProductVariant, or Merchant does not exist or mismatches."""


class InsufficientInventoryError(ValueError):
    """Raised when an order tries to purchase more inventory than is available."""


async def _handle_identity_enrichment(session: AsyncSession, envelope: ShopperEventEnvelope, email: str | None) -> None:
    if not email:
        return
    success = await enrich_shopper_email(session, envelope.merchant_id, envelope.shopper_id, email)
    if not success:
        raise IdentityConflictError(
            f"Email {email} is already used by another shopper under merchant {envelope.merchant_id}"
        )


async def _handle_purchase_completed(session: AsyncSession, envelope: ShopperEventEnvelope) -> None:
    payload = PurchaseCompletedPayload.model_validate(envelope.payload)
    
    await _handle_identity_enrichment(session, envelope, payload.email)

    merchant = await get_merchant_by_id(session, envelope.merchant_id)
    if not merchant:
        for _ in range(6):
            await asyncio.sleep(0.5)
            merchant = await get_merchant_by_id(session, envelope.merchant_id)
            if merchant:
                break
        else:
            raise UnresolvedReferenceError(f"Merchant {envelope.merchant_id} does not exist.")

    # Using explicit lookup to prevent duplicate exception control flow
    existing_order = await get_order(session, payload.order_id)
    if existing_order is not None:
        raise IntegrityError(
            f"Order {payload.order_id} already exists.", params=None, orig=None
        )

    order = await create_order(
        session,
        order_id=payload.order_id,
        merchant_id=envelope.merchant_id,
        shopper_id=envelope.shopper_id,
        currency=merchant.store_currency,
        total_amount=float(payload.total_amount),
        placed_at=envelope.event_timestamp,
        completed_at=envelope.event_timestamp,
        session_id=envelope.session_id,
    )

    items_data = []
    for item in payload.items:
        # 1. Validate the complete ownership chain
        row = await get_product_variant_with_product(session, item.variant_id)
        if not row:
            for _ in range(6):
                await asyncio.sleep(0.5)
                row = await get_product_variant_with_product(session, item.variant_id)
                if row:
                    break
            else:
                raise UnresolvedReferenceError(f"Variant {item.variant_id} does not exist.")
        variant, product = row

        if product.product_id != item.product_id:
            raise UnresolvedReferenceError(
                f"Variant {item.variant_id} belongs to product {variant.product_id}, not {item.product_id}."
            )
        
        if product.merchant_id != envelope.merchant_id:
            raise UnresolvedReferenceError(
                f"Product {product.product_id} belongs to merchant {product.merchant_id}, not {envelope.merchant_id}."
            )

        # Inventory check
        if variant.inventory_quantity < item.quantity:
            raise InsufficientInventoryError(
                f"Variant {item.variant_id} has insufficient inventory ({variant.inventory_quantity} < {item.quantity})."
            )

        # Decrement inventory
        success = await decrement_inventory(session, item.variant_id, item.quantity)
        if not success:
            raise InsufficientInventoryError(
                f"Concurrent modification caused inventory deficit for variant {item.variant_id}."
            )

        line_total = float(item.unit_price * item.quantity)
        items_data.append((item.variant_id, item.quantity, float(item.unit_price), line_total))

    create_order_items(session, payload.order_id, items_data)


async def process_shopper_event(session: AsyncSession, envelope: ShopperEventEnvelope) -> None:
    """Route a validated Shopper event to its operational mutation."""
    # Ensure referenced merchant exists before creating shopper
    merchant = await get_merchant_by_id(session, envelope.merchant_id)
    if merchant is None:
        for _ in range(6):
            await asyncio.sleep(0.5)
            merchant = await get_merchant_by_id(session, envelope.merchant_id)
            if merchant is not None:
                break
        else:
            raise UnresolvedReferenceError(f"Merchant {envelope.merchant_id} does not exist.")

    # All events upsert the shopper and update last_seen_at
    await upsert_shopper(session, envelope.merchant_id, envelope.shopper_id, envelope.event_timestamp)

    if envelope.event_type == ShopperEventType.SESSION_STARTED:
        payload = SessionStartedPayload.model_validate(envelope.payload)
        await _handle_identity_enrichment(session, envelope, payload.email)
    
    elif envelope.event_type == ShopperEventType.CHECKOUT_STARTED:
        payload = CheckoutStartedPayload.model_validate(envelope.payload)
        await _handle_identity_enrichment(session, envelope, payload.email)
        
    elif envelope.event_type == ShopperEventType.PURCHASE_COMPLETED:
        await _handle_purchase_completed(session, envelope)
        await record_domain_activity(session, "shopper", envelope.shopper_id, "order", envelope.event_timestamp)
        await record_domain_activity(session, "merchant", envelope.merchant_id, "order", envelope.event_timestamp)

    # All other behavioral events simply rely on the upsert_shopper call above.
    
    await record_domain_activity(session, "shopper", envelope.shopper_id, "shopper", envelope.event_timestamp)
    await record_domain_activity(session, "merchant", envelope.merchant_id, "shopper", envelope.event_timestamp)


async def list_shoppers(session: AsyncSession, merchant_id: uuid.UUID, limit: int, offset: int) -> tuple[list[Shopper], int]:
    return await list_merchant_shoppers_paginated(session, merchant_id, limit, offset)


async def get_shopper(session: AsyncSession, merchant_id: uuid.UUID, shopper_id: uuid.UUID) -> Shopper | None:
    """Retrieve a shopper by ID ensuring strict merchant ownership boundary."""
    return await dal_get_shopper(session, merchant_id, shopper_id)


def _extract_activity_details(payload: dict[str, Any]) -> dict[str, Any]:
    """Curate business drill-down fields from event payload, omitting raw mechanical fields."""
    allowed_keys = {
        "url",
        "path",
        "referrer",
        "search_query",
        "query",
        "category_id",
        "category_name",
        "product_id",
        "variant_id",
        "product_name",
        "price",
        "unit_price",
        "quantity",
        "cart_total",
        "item_count",
        "order_id",
        "total_amount",
        "currency",
        "recommendation_id",
        "session_duration_seconds",
    }
    return {k: v for k, v in payload.items() if k in allowed_keys}


async def list_shopper_activity(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    shopper_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[ShopperActivityEventResponse], int] | None:
    """
    Retrieve curated activity events for a shopper under a merchant.
    Returns None if the shopper does not exist or does not belong to the merchant.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        return None

    start_time: datetime | None = None
    if start_date is not None:
        start_time = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)

    end_time: datetime | None = None
    if end_date is not None:
        end_time = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)

    events, total = await list_shopper_events_paginated(
        session,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )

    activity_items = [
        ShopperActivityEventResponse(
            event_id=e.event_id,
            session_id=e.session_id,
            event_type=e.event_type,
            event_timestamp=e.event_timestamp,
            source=e.source,
            activity_details=_extract_activity_details(e.payload),
        )
        for e in events
    ]
    return activity_items, total
