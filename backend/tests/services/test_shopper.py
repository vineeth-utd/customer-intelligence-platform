import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.models.shopper import Shopper
from app.models.order import Order, OrderItem
from app.models.merchant import Merchant
from app.models.product import Product, ProductVariant
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType
from app.services.shopper import (
    process_shopper_event,
    IdentityConflictError,
    UnresolvedReferenceError,
    InsufficientInventoryError,
)
from app.db.session import AsyncSessionLocal, engine

@pytest.fixture
async def db_session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")
    yield session
    await session.rollback()
    await session.close()

@pytest.fixture
async def setup_data(db_session):
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    
    merchant = Merchant(merchant_id=merchant_id, shopify_store_id=f"store-{uuid.uuid4().hex[:8]}", merchant_name="Test Merchant", email="test@test.com", country="US", timezone="UTC", store_currency="USD", app_install_status="installed")
    product = Product(product_id=product_id, merchant_id=merchant_id, product_name="Product", status="active")
    variant = ProductVariant(variant_id=variant_id, product_id=product_id, variant_name="Variant", sku="SKU", price=Decimal("10.00"), inventory_quantity=10, status="active")
    
    db_session.add(merchant)
    db_session.add(product)
    db_session.add(variant)
    await db_session.commit()
    
    yield merchant_id, product_id, variant_id

def _envelope(event_type, merchant_id, shopper_id, payload) -> ShopperEventEnvelope:
    return ShopperEventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        payload=payload,
        source="test",
    )

async def test_session_started_upserts_anonymous_shopper(db_session, setup_data):
    merchant_id, _, _ = setup_data
    shopper_id = uuid.uuid4()
    
    envelope = _envelope(
        ShopperEventType.SESSION_STARTED, merchant_id, shopper_id, {"referrer": None, "email": None}
    )
    
    await process_shopper_event(db_session, envelope)
    
    shopper = await db_session.get(Shopper, shopper_id)
    assert shopper is not None
    assert shopper.email is None
    assert shopper.merchant_id == merchant_id

async def test_identity_conflict_raises_error(db_session, setup_data):
    merchant_id, _, _ = setup_data
    shopper_id_1 = uuid.uuid4()
    shopper_id_2 = uuid.uuid4()
    email = "conflict@test.com"
    
    env1 = _envelope(ShopperEventType.SESSION_STARTED, merchant_id, shopper_id_1, {"referrer": None, "email": email})
    await process_shopper_event(db_session, env1)
    
    env2 = _envelope(ShopperEventType.SESSION_STARTED, merchant_id, shopper_id_2, {"referrer": None, "email": email})
    with pytest.raises(IdentityConflictError):
        await process_shopper_event(db_session, env2)

async def test_purchase_completed_success(db_session, setup_data):
    merchant_id, product_id, variant_id = setup_data
    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()
    
    env_start = _envelope(ShopperEventType.SESSION_STARTED, merchant_id, shopper_id, {"referrer": None, "email": "buyer@test.com"})
    await process_shopper_event(db_session, env_start)
    
    env_purchase = _envelope(
        ShopperEventType.PURCHASE_COMPLETED,
        merchant_id,
        shopper_id,
        {
            "order_id": str(order_id),
            "total_amount": "15.00",
            "email": "buyer@test.com",
            "items": [
                {
                    "product_id": str(product_id),
                    "variant_id": str(variant_id),
                    "quantity": 2,
                    "unit_price": "7.50"
                }
            ]
        }
    )
    await process_shopper_event(db_session, env_purchase)
    
    order = await db_session.get(Order, order_id)
    assert order is not None
    assert order.total_amount == Decimal("15.00")
    
    stmt = select(OrderItem).where(OrderItem.order_id == order_id)
    items = (await db_session.execute(stmt)).scalars().all()
    assert len(items) == 1
    assert items[0].quantity == 2
    assert items[0].unit_price == Decimal("7.50")
    
    variant = await db_session.get(ProductVariant, variant_id)
    assert variant.inventory_quantity == 8

async def test_purchase_insufficient_inventory(db_session, setup_data):
    merchant_id, product_id, variant_id = setup_data
    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()
    
    env_purchase = _envelope(
        ShopperEventType.PURCHASE_COMPLETED, merchant_id, shopper_id,
        {
            "order_id": str(order_id), "total_amount": "100.00", "email": None,
            "items": [{"product_id": str(product_id), "variant_id": str(variant_id), "quantity": 11, "unit_price": "10.00"}]
        }
    )
    with pytest.raises(InsufficientInventoryError):
        await process_shopper_event(db_session, env_purchase)

async def test_purchase_wrong_product_ownership(db_session, setup_data):
    merchant_id, product_id, variant_id = setup_data
    wrong_merchant_id = uuid.uuid4()
    
    merchant2 = Merchant(merchant_id=wrong_merchant_id, shopify_store_id="store2", merchant_name="m2", email="m2@test.com", country="US", timezone="UTC", store_currency="USD", app_install_status="installed")
    db_session.add(merchant2)
    await db_session.flush()

    shopper_id = uuid.uuid4()
    order_id = uuid.uuid4()
    
    env_purchase = _envelope(
        ShopperEventType.PURCHASE_COMPLETED, wrong_merchant_id, shopper_id,
        {
            "order_id": str(order_id), "total_amount": "10.00", "email": None,
            "items": [{"product_id": str(product_id), "variant_id": str(variant_id), "quantity": 1, "unit_price": "10.00"}]
        }
    )
    with pytest.raises(UnresolvedReferenceError, match="belongs to merchant"):
        await process_shopper_event(db_session, env_purchase)
