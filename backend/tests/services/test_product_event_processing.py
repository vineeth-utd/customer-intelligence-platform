"""Integration tests against a live local Postgres for Product event routing/processing.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable, mirroring tests/services/test_merchant_event_processing.py.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text

from app.config.settings import settings
from app.data_access.product import get_product_by_id, get_product_variant_by_id
from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.models.product import Product, ProductVariant
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType
from app.services.product import (
    InvalidChangedValueError,
    UnresolvedReferenceError,
    UnsupportedProductFieldError,
    UnsupportedVariantFieldError,
    process_product_event,
)


@pytest.fixture
async def db_session():
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first so a stale
    # connection bound to a previous test's loop is never reused here.
    await engine.dispose()

    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable at {settings.postgres_host}:{settings.postgres_port}: {exc}")
    yield session
    await session.close()


@pytest.fixture
async def merchant(db_session):
    merchant_id = uuid.uuid4()
    merchant_row = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"store-{uuid.uuid4().hex[:8]}",
        merchant_name="Test Merchant",
        email="test-merchant@example.com",
        country="US",
        timezone="America/New_York",
        store_currency="USD",
        app_install_status="installed",
    )
    db_session.add(merchant_row)
    await db_session.commit()
    yield merchant_row
    await db_session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await db_session.commit()


async def _cleanup_product(session, product_id: uuid.UUID) -> None:
    await session.execute(delete(ProductVariant).where(ProductVariant.product_id == product_id))
    await session.execute(delete(Product).where(Product.product_id == product_id))
    await session.commit()


def _envelope(
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    event_type: ProductEventType,
    payload: dict,
    event_id: uuid.UUID | None = None,
) -> ProductEventEnvelope:
    return ProductEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=event_type,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        product_id=product_id,
        payload=payload,
        source="test",
    )


def _created_payload(**overrides) -> dict:
    payload = {"product_name": "Trail Runner", "category": "Footwear", "vendor": "Acme", "status": "active"}
    payload.update(overrides)
    return payload


def _variant_created_payload(variant_id: uuid.UUID, **overrides) -> dict:
    payload = {
        "variant_id": str(variant_id),
        "variant_name": "Size 10",
        "sku": f"SKU-{variant_id.hex[:6]}",
        "price": "129.99",
        "size": "10",
        "color": "Black",
        "inventory_quantity": 25,
        "status": "active",
    }
    payload.update(overrides)
    return payload


async def test_full_product_lifecycle_produces_expected_operational_state(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    second_variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        product = await get_product_by_id(db_session, product_id)
        assert product is not None
        assert product.product_name == "Trail Runner"
        assert product.status == "active"

        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id, product_id, ProductEventType.PRODUCT_UPDATED, {"changed_values": {"category": "Outdoor"}}
            ),
        )
        product = await get_product_by_id(db_session, product_id)
        assert product.category == "Outdoor"

        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(variant_id),
            ),
        )
        variant = await get_product_variant_by_id(db_session, variant_id)
        assert variant is not None
        assert variant.price == Decimal("129.99")
        assert variant.inventory_quantity == 25

        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_UPDATED,
                {"variant_id": str(variant_id), "changed_values": {"price": "119.99", "inventory_quantity": 10}},
            ),
        )
        variant = await get_product_variant_by_id(db_session, variant_id)
        assert variant.price == Decimal("119.99")
        assert variant.inventory_quantity == 10

        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(second_variant_id, sku=f"SKU-{second_variant_id.hex[:6]}"),
            ),
        )

        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id, product_id, ProductEventType.PRODUCT_VARIANT_ARCHIVED, {"variant_id": str(variant_id)}
            ),
        )
        variant = await get_product_variant_by_id(db_session, variant_id)
        assert variant.status == "archived"
        second_variant = await get_product_variant_by_id(db_session, second_variant_id)
        assert second_variant.status == "active"

        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_ARCHIVED, {})
        )
        product = await get_product_by_id(db_session, product_id)
        assert product.status == "archived"
        second_variant = await get_product_variant_by_id(db_session, second_variant_id)
        assert second_variant.status == "archived"
        variant = await get_product_variant_by_id(db_session, variant_id)
        assert variant.status == "archived"

        await db_session.commit()
    finally:
        await _cleanup_product(db_session, product_id)


async def test_product_archived_archives_all_active_variants(db_session, merchant):
    product_id = uuid.uuid4()
    already_archived_variant_id = uuid.uuid4()
    active_variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        for variant_id in (already_archived_variant_id, active_variant_id):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_CREATED,
                    _variant_created_payload(variant_id, sku=f"SKU-{variant_id.hex[:6]}"),
                ),
            )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_ARCHIVED,
                {"variant_id": str(already_archived_variant_id)},
            ),
        )

        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_ARCHIVED, {})
        )

        product = await get_product_by_id(db_session, product_id)
        assert product.status == "archived"
        assert (await get_product_variant_by_id(db_session, already_archived_variant_id)).status == "archived"
        assert (await get_product_variant_by_id(db_session, active_variant_id)).status == "archived"

        await db_session.commit()
    finally:
        await _cleanup_product(db_session, product_id)


async def test_product_created_is_idempotent(db_session, merchant):
    product_id = uuid.uuid4()
    try:
        envelope = _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        await process_product_event(db_session, envelope)
        await process_product_event(db_session, envelope)
        await db_session.commit()

        result = await db_session.execute(select(Product).where(Product.product_id == product_id))
        assert len(result.scalars().all()) == 1
    finally:
        await _cleanup_product(db_session, product_id)


async def test_product_variant_created_is_idempotent(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        variant_envelope = _envelope(
            merchant.merchant_id, product_id, ProductEventType.PRODUCT_VARIANT_CREATED, _variant_created_payload(variant_id)
        )
        await process_product_event(db_session, variant_envelope)
        await process_product_event(db_session, variant_envelope)
        await db_session.commit()

        result = await db_session.execute(select(ProductVariant).where(ProductVariant.variant_id == variant_id))
        assert len(result.scalars().all()) == 1
    finally:
        await _cleanup_product(db_session, product_id)


async def test_unsupported_product_field_raises(db_session, merchant):
    product_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        with pytest.raises(UnsupportedProductFieldError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_UPDATED,
                    {"changed_values": {"merchant_id": str(uuid.uuid4())}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_unsupported_variant_field_raises(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(variant_id),
            ),
        )
        # status is deliberately not a supported variant update field (no
        # meaningful non-terminal transition - see Unit 3.5B generator).
        with pytest.raises(UnsupportedVariantFieldError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_UPDATED,
                    {"variant_id": str(variant_id), "changed_values": {"status": "active"}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_negative_inventory_quantity_raises(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(variant_id),
            ),
        )
        with pytest.raises(InvalidChangedValueError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_UPDATED,
                    {"variant_id": str(variant_id), "changed_values": {"inventory_quantity": -5}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_malformed_price_raises(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(variant_id),
            ),
        )
        with pytest.raises(InvalidChangedValueError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_UPDATED,
                    {"variant_id": str(variant_id), "changed_values": {"price": "not-a-number"}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_negative_price_raises(db_session, merchant):
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id,
                product_id,
                ProductEventType.PRODUCT_VARIANT_CREATED,
                _variant_created_payload(variant_id),
            ),
        )
        with pytest.raises(InvalidChangedValueError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_UPDATED,
                    {"variant_id": str(variant_id), "changed_values": {"price": "-5.00"}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_unresolved_variant_reference_raises(db_session, merchant):
    product_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        with pytest.raises(UnresolvedReferenceError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_id,
                    ProductEventType.PRODUCT_VARIANT_UPDATED,
                    {"variant_id": str(uuid.uuid4()), "changed_values": {"price": "10.00"}},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_id)


async def test_variant_belonging_to_different_product_is_rejected(db_session, merchant):
    product_a = uuid.uuid4()
    product_b = uuid.uuid4()
    variant_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_a, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_b, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await process_product_event(
            db_session,
            _envelope(
                merchant.merchant_id, product_a, ProductEventType.PRODUCT_VARIANT_CREATED, _variant_created_payload(variant_id)
            ),
        )

        with pytest.raises(UnresolvedReferenceError):
            await process_product_event(
                db_session,
                _envelope(
                    merchant.merchant_id,
                    product_b,
                    ProductEventType.PRODUCT_VARIANT_ARCHIVED,
                    {"variant_id": str(variant_id)},
                ),
            )
    finally:
        await _cleanup_product(db_session, product_a)
        await _cleanup_product(db_session, product_b)


async def test_process_product_event_does_not_commit(db_session, merchant):
    # session.rollback() expires the identity map, so re-querying through the
    # same session (rather than opening a second pooled connection) still
    # proves the mutation was never actually committed to the database.
    product_id = uuid.uuid4()
    try:
        await process_product_event(
            db_session, _envelope(merchant.merchant_id, product_id, ProductEventType.PRODUCT_CREATED, _created_payload())
        )
        await db_session.rollback()

        assert await get_product_by_id(db_session, product_id) is None
    finally:
        await _cleanup_product(db_session, product_id)
