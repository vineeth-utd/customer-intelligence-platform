from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.events.event_types import ProductEventType
from app.schemas.events.registry import register_event_payload


@register_event_payload(ProductEventType.PRODUCT_CREATED.value, 1)
class ProductCreatedPayload(BaseModel):
    product_name: str
    category: str | None = None
    vendor: str | None = None
    status: str


@register_event_payload(ProductEventType.PRODUCT_UPDATED.value, 1)
class ProductUpdatedPayload(BaseModel):
    changed_values: dict[str, Any]


@register_event_payload(ProductEventType.PRODUCT_ARCHIVED.value, 1)
class ProductArchivedPayload(BaseModel):
    pass


@register_event_payload(ProductEventType.PRODUCT_VARIANT_CREATED.value, 1)
class ProductVariantCreatedPayload(BaseModel):
    variant_id: UUID
    variant_name: str
    sku: str
    price: Decimal
    size: str | None = None
    color: str | None = None
    inventory_quantity: int
    status: str


@register_event_payload(ProductEventType.PRODUCT_VARIANT_UPDATED.value, 1)
class ProductVariantUpdatedPayload(BaseModel):
    variant_id: UUID
    changed_values: dict[str, Any]


@register_event_payload(ProductEventType.PRODUCT_VARIANT_ARCHIVED.value, 1)
class ProductVariantArchivedPayload(BaseModel):
    variant_id: UUID
