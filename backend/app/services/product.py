import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.product import (
    apply_variant_field_changes,
    archive_product,
    archive_product_variants,
    archive_variant_row,
    create_product,
    create_product_variant,
    get_product_variant_by_id,
    update_product_fields,
)
from app.models.product import ProductVariant
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType
from app.schemas.events.payloads.product import (
    ProductArchivedPayload,
    ProductCreatedPayload,
    ProductUpdatedPayload,
    ProductVariantArchivedPayload,
    ProductVariantCreatedPayload,
    ProductVariantUpdatedPayload,
)

_SUPPORTED_PRODUCT_UPDATE_FIELDS = {"product_name", "category", "vendor", "status"}
_SUPPORTED_VARIANT_UPDATE_FIELDS = {"variant_name", "price", "inventory_quantity", "size", "color"}


class UnresolvedReferenceError(RuntimeError):
    """Raised when a ProductVariant referenced by variant_id cannot be found under the envelope's product."""


class UnsupportedProductFieldError(ValueError):
    """Raised when PRODUCT_UPDATED references a field the Product model does not support."""


class UnsupportedVariantFieldError(ValueError):
    """Raised when PRODUCT_VARIANT_UPDATED references a field the ProductVariant model does not support."""


class InvalidChangedValueError(ValueError):
    """Raised when a changed_values value fails type/range validation for its field."""


def _coerce_variant_changed_values(changed_values: dict[str, Any]) -> dict[str, Any]:
    coerced = dict(changed_values)
    if "price" in coerced:
        try:
            price = Decimal(str(coerced["price"]))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidChangedValueError(f"price is not Decimal-compatible: {coerced['price']!r}") from exc
        if price < 0:
            raise InvalidChangedValueError(f"price must be non-negative: {price}")
        coerced["price"] = price
    if "inventory_quantity" in coerced:
        quantity = coerced["inventory_quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise InvalidChangedValueError(f"inventory_quantity must be a non-negative integer: {quantity!r}")
    return coerced


async def _handle_product_created(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    payload = ProductCreatedPayload.model_validate(envelope.payload)
    await create_product(
        session,
        product_id=envelope.product_id,
        merchant_id=envelope.merchant_id,
        product_name=payload.product_name,
        category=payload.category,
        vendor=payload.vendor,
        status=payload.status,
    )


async def _handle_product_updated(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    payload = ProductUpdatedPayload.model_validate(envelope.payload)
    unsupported = set(payload.changed_values) - _SUPPORTED_PRODUCT_UPDATE_FIELDS
    if unsupported:
        raise UnsupportedProductFieldError(f"Unsupported product field(s): {sorted(unsupported)}")
    await update_product_fields(session, envelope.product_id, dict(payload.changed_values))


async def _handle_product_archived(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    ProductArchivedPayload.model_validate(envelope.payload)
    await archive_product(session, envelope.product_id)
    await archive_product_variants(session, envelope.product_id)


async def _handle_product_variant_created(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    payload = ProductVariantCreatedPayload.model_validate(envelope.payload)
    await create_product_variant(
        session,
        variant_id=payload.variant_id,
        product_id=envelope.product_id,
        variant_name=payload.variant_name,
        sku=payload.sku,
        price=payload.price,
        size=payload.size,
        color=payload.color,
        inventory_quantity=payload.inventory_quantity,
        status=payload.status,
    )


async def _resolve_variant(session: AsyncSession, envelope: ProductEventEnvelope, variant_id: uuid.UUID) -> ProductVariant:
    variant = await get_product_variant_by_id(session, variant_id)
    if variant is None or variant.product_id != envelope.product_id:
        raise UnresolvedReferenceError(f"No variant {variant_id} under product {envelope.product_id}")
    return variant


async def _handle_product_variant_updated(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    payload = ProductVariantUpdatedPayload.model_validate(envelope.payload)
    unsupported = set(payload.changed_values) - _SUPPORTED_VARIANT_UPDATE_FIELDS
    if unsupported:
        raise UnsupportedVariantFieldError(f"Unsupported variant field(s): {sorted(unsupported)}")

    variant = await _resolve_variant(session, envelope, payload.variant_id)
    coerced = _coerce_variant_changed_values(payload.changed_values)
    apply_variant_field_changes(variant, coerced)


async def _handle_product_variant_archived(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    payload = ProductVariantArchivedPayload.model_validate(envelope.payload)
    variant = await _resolve_variant(session, envelope, payload.variant_id)
    archive_variant_row(variant)


_HANDLERS: dict[ProductEventType, Callable[[AsyncSession, ProductEventEnvelope], Awaitable[None]]] = {
    ProductEventType.PRODUCT_CREATED: _handle_product_created,
    ProductEventType.PRODUCT_UPDATED: _handle_product_updated,
    ProductEventType.PRODUCT_ARCHIVED: _handle_product_archived,
    ProductEventType.PRODUCT_VARIANT_CREATED: _handle_product_variant_created,
    ProductEventType.PRODUCT_VARIANT_UPDATED: _handle_product_variant_updated,
    ProductEventType.PRODUCT_VARIANT_ARCHIVED: _handle_product_variant_archived,
}


async def process_product_event(session: AsyncSession, envelope: ProductEventEnvelope) -> None:
    """Route a validated Product event to its operational mutation.

    Performs the mutation only: does not commit, does not persist the raw
    event, and does not touch processed-state or Kafka offsets. Composing
    this with event persistence, transaction boundaries, redelivery
    handling, and offset commits is ProductEventConsumer's responsibility.
    """
    handler = _HANDLERS[envelope.event_type]
    await handler(session, envelope)
