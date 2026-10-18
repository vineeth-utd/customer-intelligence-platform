import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.models.event import ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant
from app.models.profile import ShopperProfile
from app.models.shopper import Shopper
from app.schemas.events.event_types import ShopperEventType
from app.services.segment_rules import evaluate_segment_rule


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
async def setup_base(session):
    merchant_id = uuid.uuid4()
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"test-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Rule Test Store",
        email=f"rule-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    shopper_id = uuid.uuid4()
    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant_id,
        email="shopper_rule@test.com",
    )
    session.add_all([merchant, shopper])
    await session.commit()
    return {"merchant_id": merchant_id, "shopper_id": shopper_id}


@pytest.mark.asyncio
async def test_rule_has_recent_session(session, setup_base):
    shopper_id = setup_base["shopper_id"]
    merchant_id = setup_base["merchant_id"]
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

    rule_def = {"type": "behavioral", "condition": "has_recent_session", "days": 30}

    # 1. No events -> False
    res = await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now)
    assert res is False

    # 2. Event older than 30 days -> False
    old_event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=now - timedelta(days=31),
        payload={},
        source="storefront",
    )
    session.add(old_event)
    await session.commit()

    res = await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now)
    assert res is False

    # 3. Non-SESSION_STARTED event within 30 days -> False
    view_event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=now - timedelta(days=5),
        payload={},
        source="storefront",
    )
    session.add(view_event)
    await session.commit()

    res = await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now)
    assert res is False

    # 4. Valid SESSION_STARTED within 30 days -> True
    recent_event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=now - timedelta(days=10),
        payload={},
        source="storefront",
    )
    session.add(recent_event)
    await session.commit()

    res = await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now)
    assert res is True

    # 5. Missing required 'days' parameter -> must evaluate to False (rule definition owns parameter)
    missing_days_def = {"type": "behavioral", "condition": "has_recent_session"}
    res_missing = await evaluate_segment_rule(session, shopper_id, missing_days_def, evaluation_time=now)
    assert res_missing is False

    invalid_days_def = {"type": "behavioral", "condition": "has_recent_session", "days": -5}
    assert await evaluate_segment_rule(session, shopper_id, invalid_days_def, evaluation_time=now) is False


@pytest.mark.asyncio
async def test_rule_total_spend_transactional(session, setup_base):
    shopper_id = setup_base["shopper_id"]
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

    rule_gte_500 = {"type": "transactional", "metric": "total_spend", "operator": ">=", "value": 500}

    # 1. No profile exists yet -> defaults total_spend to 0.0 -> False
    assert await evaluate_segment_rule(session, shopper_id, rule_gte_500, evaluation_time=now) is False

    # 2. Profile with total_spend = 350 -> False
    profile = ShopperProfile(
        shopper_id=shopper_id,
        total_orders=2,
        total_spend=350.0,
        average_order_value=175.0,
        wishlist_item_count=0,
        save_for_later_item_count=0,
        campaign_engagement_count=0,
        generated_at=now,
    )
    session.add(profile)
    await session.commit()

    assert await evaluate_segment_rule(session, shopper_id, rule_gte_500, evaluation_time=now) is False

    # 3. Update total_spend to 500.0 -> True
    profile.total_spend = 500.0
    await session.commit()
    assert await evaluate_segment_rule(session, shopper_id, rule_gte_500, evaluation_time=now) is True

    # 4. Test operators
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": ">", "value": 499}, evaluation_time=now) is True
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": ">", "value": 500}, evaluation_time=now) is False
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": "<=", "value": 500}, evaluation_time=now) is True
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": "<", "value": 500}, evaluation_time=now) is False
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": "==", "value": 500}, evaluation_time=now) is True
    assert await evaluate_segment_rule(session, shopper_id, {"type": "transactional", "metric": "total_spend", "operator": "!=", "value": 500}, evaluation_time=now) is False

    # 5. Unsupported metric (e.g. lifetime_value) must evaluate to False
    unsupported_metric = {"type": "transactional", "metric": "lifetime_value", "operator": ">=", "value": 500}
    assert await evaluate_segment_rule(session, shopper_id, unsupported_metric, evaluation_time=now) is False


@pytest.mark.asyncio
async def test_rule_abandoned_cart_24h(session, setup_base):
    shopper_id = setup_base["shopper_id"]
    merchant_id = setup_base["merchant_id"]
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)

    rule_def = {"type": "behavioral", "condition": "abandoned_cart_24h"}

    # 1. No journeys -> False
    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is False

    # 2. Open journey with ADD_TO_CART only 5 hours ago (< 24h) -> False
    journey_1 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        started_at=now - timedelta(hours=6),
        journey_status="OPEN",
        converted=False,
        generated_at=now,
    )
    event_1 = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey_1.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type=ShopperEventType.ADD_TO_CART.value,
        event_timestamp=now - timedelta(hours=5),
        sequence_number=1,
    )
    session.add_all([journey_1, event_1])
    await session.commit()

    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is False

    # 3. Update event_timestamp to 30 hours ago (>= 24h) in open journey -> True
    event_1.event_timestamp = now - timedelta(hours=30)
    await session.commit()
    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is True

    # 4. Converted journey does NOT qualify: if journey_1 converted -> False
    journey_1.converted = True
    journey_1.journey_status = "CONVERTED"
    await session.commit()
    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is False

    # 5. Non-converting timed-out journey with CHECKOUT_STARTED 48 hours ago -> True
    journey_2 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        started_at=now - timedelta(hours=50),
        journey_status="NON_CONVERTING",
        converted=False,
        generated_at=now,
    )
    event_2 = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey_2.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type=ShopperEventType.CHECKOUT_STARTED.value,
        event_timestamp=now - timedelta(hours=48),
        sequence_number=1,
    )
    session.add_all([journey_2, event_2])
    await session.commit()

    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is True

    # 6. Unrelated converted journey (journey_1 converted) does NOT negate unconverted abandonment in journey_2
    assert await evaluate_segment_rule(session, shopper_id, rule_def, evaluation_time=now) is True
