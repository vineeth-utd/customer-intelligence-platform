import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.models.profile import MerchantProfile, ShopperProfile
from app.models.order import Order, OrderItem
from app.models.shopper import Shopper
from app.models.product import Product, ProductVariant
from app.models.campaign import Campaign
from app.models.metrics import MerchantMetricsDaily
from app.services.profile import generate_merchant_profile_callback, generate_shopper_profile_callback


@pytest.fixture
async def session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")

    yield session

    await session.close()


@pytest.fixture
async def merchant(session: AsyncSession) -> Merchant:
    merchant = Merchant(
        merchant_name="Test Merchant for Profile",
        email="profile@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        shopify_store_id=f"profile-{uuid.uuid4().hex[:8]}.myshopify.com",
        app_install_status="installed",
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)
    return merchant


@pytest.mark.asyncio
async def test_generate_merchant_profile_callback_empty(session: AsyncSession, merchant: Merchant):
    # Generating for a merchant with no shoppers, products, etc.
    await generate_merchant_profile_callback(session, merchant.merchant_id)
    await session.commit()

    # Verify
    stmt = select(MerchantProfile).where(MerchantProfile.merchant_id == merchant.merchant_id)
    res = await session.execute(stmt)
    profile = res.scalar_one_or_none()

    assert profile is not None
    assert profile.total_shoppers == 0
    assert profile.total_products == 0
    assert profile.total_orders == 0
    assert profile.total_revenue == 0.0
    assert profile.average_order_value == 0.0
    assert profile.conversion_rate == 0.0
    assert profile.total_campaigns == 0


@pytest.mark.asyncio
async def test_generate_merchant_profile_callback_with_data(session: AsyncSession, merchant: Merchant):
    # Add some data
    shopper1 = Shopper(merchant_id=merchant.merchant_id, email="s1@test.com")
    shopper2 = Shopper(merchant_id=merchant.merchant_id, email="s2@test.com")
    
    product1 = Product(merchant_id=merchant.merchant_id, product_name="P1", status="active")
    
    campaign1 = Campaign(
        merchant_id=merchant.merchant_id,
        segment_id=uuid.uuid4(),  # We won't strictly enforce fk here if tests don't require it, or wait, it might fail.
        campaign_name="C1",
        campaign_type="email",
        campaign_medium="email",
        status="ACTIVE"
    )
    # Actually segment_id fk might fail if not inserted, let's skip campaign insert if it requires segment.
    # We will test what we can simply without breaking FKs.
    
    order1 = Order(
        merchant_id=merchant.merchant_id,
        shopper_id=shopper1.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=100.0,
        placed_at=datetime.now(timezone.utc)
    )
    
    session.add_all([shopper1, shopper2, product1])
    await session.commit()
    
    # Needs valid shopper_id for order
    order1.shopper_id = shopper1.shopper_id
    session.add(order1)
    await session.commit()

    # Add metrics daily for conversion rate
    metrics = MerchantMetricsDaily(
        merchant_id=merchant.merchant_id,
        metric_date=datetime.now(timezone.utc).date(),
        revenue=100.0,
        order_count=1,
        unique_shoppers=1,
        new_shoppers=1,
        session_count=10,
        converted_session_count=2,
        product_view_count=5,
        wishlist_add_count=0,
        save_for_later_count=0,
        add_to_cart_count=1,
        checkout_count=1,
        purchase_count=1,
        conversion_rate=0.2,
        average_order_value=100.0,
        platform_login_count=1,
        campaign_created_count=0,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=datetime.now(timezone.utc)
    )
    session.add(metrics)
    await session.commit()

    await generate_merchant_profile_callback(session, merchant.merchant_id)
    await session.commit()

    stmt = select(MerchantProfile).where(MerchantProfile.merchant_id == merchant.merchant_id)
    res = await session.execute(stmt)
    profile = res.scalar_one_or_none()

    assert profile is not None
    assert profile.total_shoppers == 2
    assert profile.total_products == 1
    assert profile.total_orders == 1
    assert profile.total_revenue == 100.0
    assert profile.average_order_value == 100.0
    assert profile.conversion_rate == 0.2  # 2/10


@pytest.mark.asyncio
async def test_generate_shopper_profile_callback_empty(session: AsyncSession, merchant: Merchant):
    shopper = Shopper(merchant_id=merchant.merchant_id, email="empty_shopper@test.com")
    session.add(shopper)
    await session.commit()
    await session.refresh(shopper)

    await generate_shopper_profile_callback(session, shopper.shopper_id)
    await session.commit()

    stmt = select(ShopperProfile).where(ShopperProfile.shopper_id == shopper.shopper_id)
    res = await session.execute(stmt)
    profile = res.scalar_one_or_none()

    assert profile is not None
    assert profile.total_orders == 0
    assert profile.total_spend == 0.0
    assert profile.average_order_value == 0.0
    assert profile.wishlist_item_count == 0
    assert profile.save_for_later_item_count == 0
    assert profile.campaign_engagement_count == 0
    assert profile.customer_lifetime_value is None
    assert profile.purchase_frequency is None
    assert profile.cart_abandonment_count is None
    assert profile.preferred_category is None
    assert profile.preferred_size is None


@pytest.mark.asyncio
async def test_generate_shopper_profile_callback_with_data(session: AsyncSession, merchant: Merchant):
    shopper = Shopper(merchant_id=merchant.merchant_id, email="data_shopper@test.com")
    product = Product(merchant_id=merchant.merchant_id, product_name="P1", category="Shoes", status="active")
    session.add_all([shopper, product])
    await session.commit()
    await session.refresh(shopper)
    await session.refresh(product)

    variant = ProductVariant(
        product_id=product.product_id, sku="SKU1", variant_name="V1", price=50.0, size="10", inventory_quantity=10, status="active"
    )
    session.add(variant)
    await session.commit()
    await session.refresh(variant)

    order = Order(
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=50.0,
        placed_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    order_item = OrderItem(
        order_id=order.order_id,
        variant_id=variant.variant_id,
        quantity=1,
        unit_price=50.0,
        line_total=50.0
    )
    session.add(order_item)
    await session.commit()

    await generate_shopper_profile_callback(session, shopper.shopper_id)
    await session.commit()

    stmt = select(ShopperProfile).where(ShopperProfile.shopper_id == shopper.shopper_id)
    res = await session.execute(stmt)
    profile = res.scalar_one_or_none()

    assert profile is not None
    assert profile.total_orders == 1
    assert profile.total_spend == 50.0
    assert profile.average_order_value == 50.0
    assert profile.preferred_category == "Shoes"
    assert profile.preferred_size == "10"
