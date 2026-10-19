import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.event import ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant
from app.models.metrics import MerchantMetricsDaily
from app.models.order import Order
from app.models.shopper import Shopper
from app.services.analytics import (
    get_conversion_funnel,
    get_revenue_analytics,
    get_shopper_behavior_analytics,
    get_shopper_journey_analytics,
)


@pytest.fixture
async def session():
    await engine.dispose()
    s = AsyncSessionLocal()
    try:
        await s.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Database unavailable: {exc}")

    yield s
    await s.rollback()
    await s.close()
    await engine.dispose()


@pytest.fixture
async def setup_analytics_data(session):
    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    base_date = now_utc.date()

    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"shop-analytics-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Shopper Analytics Store",
        email=f"analytics-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=60),
    )
    session.add(merchant)

    yield {
        "merchant_id": merchant_id,
        "base_date": base_date,
        "now_utc": now_utc,
    }

    # Teardown test data
    await session.execute(delete(ShopperJourneyEvent).where(
        ShopperJourneyEvent.journey_id.in_(
            select(ShopperJourney.journey_id).where(ShopperJourney.merchant_id == merchant_id)
        )
    ))
    await session.execute(delete(ShopperJourney).where(ShopperJourney.merchant_id == merchant_id))
    await session.execute(delete(ShopperEvent).where(ShopperEvent.merchant_id == merchant_id))
    await session.execute(delete(Order).where(Order.merchant_id == merchant_id))
    await session.execute(delete(Shopper).where(Shopper.merchant_id == merchant_id))
    await session.execute(delete(MerchantMetricsDaily).where(MerchantMetricsDaily.merchant_id == merchant_id))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await session.commit()


@pytest.mark.asyncio
async def test_conversion_funnel(session, setup_analytics_data):
    ctx = setup_analytics_data
    merchant_id = ctx["merchant_id"]
    base_date = ctx["base_date"]

    start_date = base_date - timedelta(days=6)
    end_date = base_date

    # 1. Zero state
    zero_funnel = await get_conversion_funnel(session, merchant_id, start_date, end_date)
    assert zero_funnel is not None
    assert zero_funnel.merchant_id == merchant_id
    assert zero_funnel.overall_conversion_rate == Decimal("0.0")
    assert len(zero_funnel.stages) == 5
    assert all(s.count == 0 for s in zero_funnel.stages)

    # 2. Seed metrics across multiple days
    # Day 1: 600 sessions, 300 views, 120 carts, 60 checkouts, 30 purchases
    # Day 2: 400 sessions, 200 views, 80 carts, 40 checkouts, 20 purchases
    # Total: 1000 sessions, 500 views, 200 carts, 100 checkouts, 50 purchases
    m1 = MerchantMetricsDaily(
        merchant_id=merchant_id,
        metric_date=start_date,
        session_count=600,
        converted_session_count=30,
        product_view_count=300,
        wishlist_add_count=15,
        save_for_later_count=10,
        add_to_cart_count=120,
        checkout_count=60,
        purchase_count=30,
        order_count=30,
        revenue=1500.0,
        conversion_rate=0.05,
        average_order_value=50.0,
        unique_shoppers=200,
        new_shoppers=50,
        platform_login_count=1,
        campaign_created_count=0,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=ctx["now_utc"],
    )
    m2 = MerchantMetricsDaily(
        merchant_id=merchant_id,
        metric_date=start_date + timedelta(days=1),
        session_count=400,
        converted_session_count=20,
        product_view_count=200,
        wishlist_add_count=15,
        save_for_later_count=10,
        add_to_cart_count=80,
        checkout_count=40,
        purchase_count=20,
        order_count=20,
        revenue=1000.0,
        conversion_rate=0.05,
        average_order_value=50.0,
        unique_shoppers=150,
        new_shoppers=30,
        platform_login_count=1,
        campaign_created_count=0,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=ctx["now_utc"],
    )
    session.add_all([m1, m2])
    await session.commit()

    funnel = await get_conversion_funnel(session, merchant_id, start_date, end_date)
    assert funnel is not None
    assert len(funnel.stages) == 5

    stage_map = {s.stage_name: s for s in funnel.stages}
    assert stage_map["Sessions"].count == 1000
    assert stage_map["Product Views"].count == 500
    assert stage_map["Add to Cart"].count == 200
    assert stage_map["Checkout Started"].count == 100
    assert stage_map["Purchases"].count == 50

    # Step conversion rates:
    # Views: 500/1000 = 0.5000
    # Cart: 200/500 = 0.4000
    # Checkout: 100/200 = 0.5000
    # Purchases: 50/100 = 0.5000
    assert stage_map["Product Views"].step_conversion_rate == Decimal("0.5000")
    assert stage_map["Add to Cart"].step_conversion_rate == Decimal("0.4000")
    assert stage_map["Checkout Started"].step_conversion_rate == Decimal("0.5000")
    assert stage_map["Purchases"].step_conversion_rate == Decimal("0.5000")

    # Drop-off rates
    assert stage_map["Product Views"].drop_off_count == 500
    assert stage_map["Product Views"].drop_off_rate == Decimal("0.5000")
    assert stage_map["Add to Cart"].drop_off_count == 300
    assert stage_map["Add to Cart"].drop_off_rate == Decimal("0.6000")

    # Summary
    assert funnel.overall_conversion_rate == Decimal("0.0500")
    assert funnel.cart_abandonment_rate == Decimal("0.7500")  # (200 - 50) / 200 = 0.75
    assert funnel.checkout_abandonment_rate == Decimal("0.5000")  # (100 - 50) / 100 = 0.5
    assert funnel.secondary_engagement["wishlist_add_count"] == 30
    assert funnel.secondary_engagement["save_for_later_count"] == 20


@pytest.mark.asyncio
async def test_shopper_journey_analytics(session, setup_analytics_data):
    ctx = setup_analytics_data
    merchant_id = ctx["merchant_id"]
    base_date = ctx["base_date"]
    start_date = base_date - timedelta(days=6)
    end_date = base_date

    shopper = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="journey_test@test.com",
    )
    session.add(shopper)

    t0 = datetime.combine(start_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    # 2 Converted journeys
    j_conv1 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0,
        ended_at=t0 + timedelta(minutes=15),
        journey_status="CONVERTED",
        converted=True,
        entry_source="google.com",
        generated_at=t0,
    )
    j_conv2 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=1),
        ended_at=t0 + timedelta(hours=1, minutes=45),
        journey_status="CONVERTED",
        converted=True,
        entry_source="direct",
        generated_at=t0,
    )

    # 3 NON_CONVERTING journeys with events determining drop-off
    j_nc1 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=2),
        ended_at=t0 + timedelta(hours=3),
        journey_status="NON_CONVERTING",
        converted=False,
        entry_source="google.com",
        generated_at=t0,
    )
    # Event for j_nc1 ending at PRODUCT_VIEWED
    ev1 = ShopperJourneyEvent(
        journey_id=j_nc1.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="SESSION_STARTED",
        event_timestamp=t0 + timedelta(hours=2),
        sequence_number=1,
    )
    ev2 = ShopperJourneyEvent(
        journey_id=j_nc1.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="PRODUCT_VIEWED",
        event_timestamp=t0 + timedelta(hours=2, minutes=5),
        sequence_number=2,
    )

    j_nc2 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=4),
        ended_at=t0 + timedelta(hours=5),
        journey_status="NON_CONVERTING",
        converted=False,
        entry_source="facebook.com",
        generated_at=t0,
    )
    # Event for j_nc2 ending at ADD_TO_CART
    ev3 = ShopperJourneyEvent(
        journey_id=j_nc2.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="SESSION_STARTED",
        event_timestamp=t0 + timedelta(hours=4),
        sequence_number=1,
    )
    ev4 = ShopperJourneyEvent(
        journey_id=j_nc2.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="ADD_TO_CART",
        event_timestamp=t0 + timedelta(hours=4, minutes=10),
        sequence_number=2,
    )

    j_nc3 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=6),
        ended_at=t0 + timedelta(hours=7),
        journey_status="NON_CONVERTING",
        converted=False,
        entry_source="direct",
        generated_at=t0,
    )
    # Event for j_nc3 ending at CHECKOUT_STARTED
    ev5 = ShopperJourneyEvent(
        journey_id=j_nc3.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="CHECKOUT_STARTED",
        event_timestamp=t0 + timedelta(hours=6, minutes=20),
        sequence_number=1,
    )

    # 2 OPEN journeys (must be excluded from conversion denominator)
    j_open1 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=8),
        journey_status="OPEN",
        converted=False,
        entry_source="direct",
        generated_at=t0,
    )
    j_open2 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=t0 + timedelta(hours=9),
        journey_status="OPEN",
        converted=False,
        entry_source="google.com",
        generated_at=t0,
    )

    session.add_all([
        j_conv1, j_conv2, j_nc1, j_nc2, j_nc3, j_open1, j_open2,
        ev1, ev2, ev3, ev4, ev5,
    ])
    await session.commit()

    res = await get_shopper_journey_analytics(session, merchant_id, start_date, end_date)
    assert res is not None
    assert res.total_journeys == 7
    assert res.converted_journeys == 2
    assert res.non_converting_journeys == 3
    assert res.open_journeys == 2

    # Resolved = 2 + 3 = 5. Conversion rate = 2 / 5 = 0.4000 (OPEN excluded!)
    assert res.journey_conversion_rate == Decimal("0.4000")

    # Average conversion duration = (15 mins + 45 mins) / 2 = 30 mins = 1800 seconds
    assert res.average_conversion_duration_seconds == pytest.approx(1800.0, 1.0)

    # Drop-off stages: each non-converting journey had 1 unique drop-off event
    assert res.drop_off_stages == {
        "PRODUCT_VIEWED": 1,
        "ADD_TO_CART": 1,
        "CHECKOUT_STARTED": 1,
    }

    # By entry source: google.com (1 conv, 1 non-conv, 1 open), direct (1 conv, 1 non-conv, 1 open), facebook.com (0 conv, 1 non-conv, 0 open)
    sources = {s.entry_source: s for s in res.by_entry_source}
    assert "google.com" in sources
    assert sources["google.com"].total_journeys == 3
    assert sources["google.com"].converted_journeys == 1
    assert sources["google.com"].conversion_rate == Decimal("0.5000")  # 1 / (1+1)


@pytest.mark.asyncio
async def test_shopper_behavior_analytics(session, setup_analytics_data):
    ctx = setup_analytics_data
    merchant_id = ctx["merchant_id"]
    base_date = ctx["base_date"]
    start_date = base_date - timedelta(days=6)
    end_date = base_date

    t_prior = datetime.combine(start_date - timedelta(days=10), datetime.min.time(), tzinfo=timezone.utc)
    t_window = datetime.combine(start_date + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)

    # Shopper 1: First seen in window (New Shopper)
    s1 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="new_shopper@test.com",
        first_seen_at=t_window,
        last_seen_at=t_window,
    )
    # Shopper 2: First seen prior to window (Returning Shopper)
    s2 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="returning_shopper@test.com",
        first_seen_at=t_prior,
        last_seen_at=t_window,
    )
    session.add_all([s1, s2])

    # Events in window for both
    ev1 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=s1.shopper_id,
        session_id=uuid.uuid4(),
        event_type="PRODUCT_VIEWED",
        event_version=1,
        event_timestamp=t_window,
        payload={},
        source="web",
    )
    ev2 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=s2.shopper_id,
        session_id=uuid.uuid4(),
        event_type="PRODUCT_VIEWED",
        event_version=1,
        event_timestamp=t_window,
        payload={},
        source="web",
    )
    session.add_all([ev1, ev2])

    # Shopper 2 has a prior completed order AND a window completed order -> Repeat Buyer!
    o_prior = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=s2.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=50.0,
        placed_at=t_prior,
    )
    o_window1 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=s2.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=75.0,
        placed_at=t_window,
    )
    # Shopper 1 has a window completed order -> First-time Buyer!
    o_window2 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=s1.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=125.0,
        placed_at=t_window,
    )
    session.add_all([o_prior, o_window1, o_window2])
    await session.commit()

    res = await get_shopper_behavior_analytics(session, merchant_id, start_date, end_date)
    assert res is not None
    assert res.total_active_shoppers == 2
    assert res.new_shoppers == 1
    assert res.returning_shoppers == 1
    assert res.total_purchasing_shoppers == 2
    assert res.repeat_purchasing_shoppers == 1  # s2 has 2 lifetime completed orders
    assert res.repeat_purchase_rate == Decimal("0.5000")  # 1 / 2
    assert res.average_order_value == Decimal("100.00")  # (75 + 125) / 2


@pytest.mark.asyncio
async def test_revenue_analytics(session, setup_analytics_data):
    ctx = setup_analytics_data
    merchant_id = ctx["merchant_id"]
    base_date = ctx["base_date"]

    # Current window: 7 days
    start_date = base_date - timedelta(days=6)
    end_date = base_date
    window_days = 7

    # Prior window: [start_date - 7 days, start_date - 1 day]
    prior_start_date = start_date - timedelta(days=window_days)
    prior_end_date = start_date - timedelta(days=1)

    shopper_new = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="new_rev@test.com",
    )
    shopper_rep = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        email="rep_rev@test.com",
    )
    session.add_all([shopper_new, shopper_rep])

    t_prior = datetime.combine(prior_start_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    t_curr = datetime.combine(start_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    # Prior period order for shopper_rep: $100
    o_prior = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_rep.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=100.0,
        placed_at=t_prior,
    )
    # Current period orders:
    # 1. shopper_rep second order: $200 (Repeat revenue!)
    o_curr1 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_rep.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=200.0,
        placed_at=t_curr,
    )
    # 2. shopper_new first order: $100 (New customer revenue!)
    o_curr2 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_new.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=100.0,
        placed_at=t_curr,
    )
    session.add_all([o_prior, o_curr1, o_curr2])
    await session.commit()

    res = await get_revenue_analytics(session, merchant_id, start_date, end_date)
    assert res is not None
    assert res.total_revenue == Decimal("300.00")
    assert res.total_orders == 2
    assert res.average_order_value == Decimal("150.00")

    # Prior comparison
    comp = res.prior_period_comparison
    assert comp.prior_start_date == prior_start_date
    assert comp.prior_end_date == prior_end_date
    assert comp.prior_revenue == Decimal("100.00")
    assert comp.prior_orders == 1
    assert comp.prior_average_order_value == Decimal("100.00")

    # Growth %
    # Rev growth: (300 - 100) / 100 = +200%
    assert comp.revenue_growth_pct == Decimal("200.00")
    # Order growth: (2 - 1) / 1 = +100%
    assert comp.order_growth_pct == Decimal("100.00")
    # AOV growth: (150 - 100) / 100 = +50%
    assert comp.aov_growth_pct == Decimal("50.00")

    # Customer breakdown
    breakdown = res.customer_revenue_breakdown
    assert breakdown.new_customer_revenue == Decimal("100.00")
    assert breakdown.new_customer_order_count == 1
    assert breakdown.repeat_customer_revenue == Decimal("200.00")
    assert breakdown.repeat_customer_order_count == 1


@pytest.mark.asyncio
async def test_analytics_validations_and_non_existent_merchant(session):
    now = date.today()
    random_id = uuid.uuid4()

    # Invalid date range
    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_conversion_funnel(session, random_id, now, now - timedelta(days=1))

    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_revenue_analytics(session, random_id, now, now - timedelta(days=1))

    # Non-existent merchant returns None
    assert await get_conversion_funnel(session, random_id, now - timedelta(days=7), now) is None
    assert await get_shopper_journey_analytics(session, random_id, now - timedelta(days=7), now) is None
    assert await get_shopper_behavior_analytics(session, random_id, now - timedelta(days=7), now) is None
    assert await get_revenue_analytics(session, random_id, now - timedelta(days=7), now) is None
