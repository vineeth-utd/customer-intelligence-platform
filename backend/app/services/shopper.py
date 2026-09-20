import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.shopper import (
    upsert_shopper,
    enrich_shopper_email,
    get_merchant,
    get_order,
    create_order,
    create_order_items,
    get_product_variant_with_product,
    decrement_inventory,
)
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.schemas.events.payloads.shopper import (
    SessionStartedPayload,
    CheckoutStartedPayload,
    PurchaseCompletedPayload,
)


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

    merchant = await get_merchant(session, envelope.merchant_id)
    if not merchant:
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
    )

    items_data = []
    for item in payload.items:
        # 1. Validate the complete ownership chain
        row = await get_product_variant_with_product(session, item.variant_id)
        if not row:
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

    # All other behavioral events simply rely on the upsert_shopper call above.
