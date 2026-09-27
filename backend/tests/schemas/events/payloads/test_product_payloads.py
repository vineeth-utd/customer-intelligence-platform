from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.events.event_types import ProductEventType
from app.schemas.events.payloads.product import (
    ProductArchivedPayload,
    ProductCreatedPayload,
    ProductVariantArchivedPayload,
    ProductVariantCreatedPayload,
    ProductVariantUpdatedPayload,
)
from app.schemas.events.registry import get_payload_schema


@pytest.mark.parametrize(
    "event_type",
    [
        ProductEventType.PRODUCT_CREATED,
        ProductEventType.PRODUCT_UPDATED,
        ProductEventType.PRODUCT_ARCHIVED,
        ProductEventType.PRODUCT_VARIANT_CREATED,
        ProductEventType.PRODUCT_VARIANT_UPDATED,
        ProductEventType.PRODUCT_VARIANT_ARCHIVED,
    ],
)
def test_every_product_event_type_has_a_registered_v1_payload(event_type):
    assert get_payload_schema(event_type.value, 1) is not None


def test_product_created_payload_registered_under_its_event_type():
    assert get_payload_schema(ProductEventType.PRODUCT_CREATED.value, 1) is ProductCreatedPayload


def test_product_created_payload_accepts_optional_category_and_vendor():
    payload = ProductCreatedPayload(product_name="Trail Runner", category="Footwear", vendor="Acme", status="ACTIVE")
    assert payload.category == "Footwear"
    assert payload.vendor == "Acme"


def test_product_archived_payload_carries_no_fields():
    assert ProductArchivedPayload().model_dump() == {}


def test_product_variant_created_payload_uses_decimal_price():
    variant_id = uuid4()
    payload = ProductVariantCreatedPayload(
        variant_id=variant_id,
        variant_name="Trail Runner - Size 10",
        sku="TR-10-BLK",
        price=Decimal("129.99"),
        size="10",
        color="Black",
        inventory_quantity=25,
        status="ACTIVE",
    )
    assert payload.variant_id == variant_id
    assert payload.price == Decimal("129.99")
    assert isinstance(payload.price, Decimal)


def test_product_variant_created_payload_serializes_price_without_float_precision_loss():
    payload = ProductVariantCreatedPayload(
        variant_id=uuid4(),
        variant_name="Trail Runner - Size 10",
        sku="TR-10-BLK",
        price=Decimal("19.99"),
        inventory_quantity=1,
        status="ACTIVE",
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["price"] == "19.99"


def test_product_variant_updated_payload_carries_variant_id_and_changed_values():
    variant_id = uuid4()
    payload = ProductVariantUpdatedPayload(variant_id=variant_id, changed_values={"price": "24.99"})
    assert payload.variant_id == variant_id
    assert payload.changed_values == {"price": "24.99"}


def test_product_variant_archived_payload_requires_variant_id():
    variant_id = uuid4()
    payload = ProductVariantArchivedPayload(variant_id=variant_id)
    assert payload.variant_id == variant_id
