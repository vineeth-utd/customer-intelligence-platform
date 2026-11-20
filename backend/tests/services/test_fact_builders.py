import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.models.campaign import Campaign
from app.models.event import CampaignEvent, ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant, Subscription, SubscriptionPlan
from app.models.merchant_health import MerchantHealth
from app.models.metrics import MerchantMetricsDaily, PlatformMetricsDaily
from app.models.order import Order
from app.models.profile import MerchantProfile, ShopperProfile
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.reference_data.plans import PlanKey
from app.schemas.events.event_types import CampaignEventType, ShopperEventType
from app.schemas.knowledge import KnowledgeAccessScope, KnowledgeType
from app.services.fact_builders import (
    build_campaign_summary_facts,
    build_merchant_performance_facts,
    build_merchant_summary_facts,
    build_platform_performance_facts,
    build_shopper_behaviour_facts,
    build_shopper_journey_facts,
)
from app.services.knowledge import generate_knowledge_point_id
from app.services.merchant import initialize_reference_data


@pytest.fixture
async def session(db_session):
    yield db_session


@pytest.fixture
async def sample_merchant(session):
    await initialize_reference_data(session)
    await session.commit()

    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"fact-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Fact Builder Store",
        email=f"fact-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=60),
        last_active_at=now_utc,
    )
    session.add(merchant)

    growth_plan = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_key == PlanKey.GROWTH.value)
    )
    subscription = Subscription(
        subscription_id=uuid.uuid4(),
        merchant_id=merchant_id,
        plan_id=growth_plan.plan_id,
        status="ACTIVE",
        billing_cycle="MONTHLY",
        amount_paid=99.0,
        started_at=now_utc - timedelta(days=30),
        renewal_at=now_utc + timedelta(days=30),
    )
    session.add(subscription)

    health = MerchantHealth(
        merchant_id=merchant_id,
        health_score=85.5,
        health_status="HEALTHY",
        churn_risk_score=12.0,
        engagement_score=90.0,
        feature_adoption_score=80.0,
        business_performance_score=85.0,
        calculated_at=now_utc,
    )
    session.add(health)

    profile = MerchantProfile(
        merchant_id=merchant_id,
        total_shoppers=42,
        total_products=15,
        total_orders=120,
        total_revenue=15400.50,
        average_order_value=128.34,
        conversion_rate=0.035,
        total_campaigns=4,
        active_campaign_count=2,
        enabled_feature_count=3,
        last_order_at=now_utc - timedelta(days=1),
        last_campaign_at=now_utc - timedelta(days=3),
        generated_at=now_utc,
    )
    session.add(profile)
    await session.commit()
    return merchant


@pytest.mark.asyncio
async def test_build_merchant_summary_facts(session, sample_merchant):
    merchant = sample_merchant
    payload = await build_merchant_summary_facts(session, merchant.merchant_id)

    assert payload.metadata.knowledge_type == KnowledgeType.MERCHANT_SUMMARY
    assert payload.metadata.entity_type == "merchant"
    assert payload.metadata.entity_id == merchant.merchant_id
    assert payload.metadata.is_current is True
    assert payload.metadata.access_scope == KnowledgeAccessScope.MERCHANT

    expected_point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant.merchant_id)
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.merchant_name == "Fact Builder Store"
    assert facts.total_shoppers == 42
    assert facts.total_products == 15
    assert facts.total_orders == 120
    assert facts.total_revenue == Decimal("15400.50")
    assert facts.health_score == Decimal("85.5")
    assert facts.health_status == "HEALTHY"
    assert facts.churn_risk_score == Decimal("12.0")

    source_types = [s.source_type for s in payload.metadata.source_references]
    assert "merchants" in source_types
    assert "merchant_profiles" in source_types
    assert "merchant_health" in source_types

    # Non-existent merchant must raise ValueError
    with pytest.raises(ValueError, match="not found"):
        await build_merchant_summary_facts(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_build_shopper_behaviour_facts(session, sample_merchant):
    merchant = sample_merchant
    shopper_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant.merchant_id,
        email="shopper_fact@test.com",
        first_seen_at=now_utc - timedelta(days=20),
        last_seen_at=now_utc,
    )
    session.add(shopper)

    profile = ShopperProfile(
        shopper_id=shopper_id,
        total_orders=3,
        total_spend=320.00,
        average_order_value=106.67,
        wishlist_item_count=5,
        save_for_later_item_count=2,
        campaign_engagement_count=12,
        preferred_category="Footwear",
        preferred_size="9.5",
        last_purchase_at=now_utc - timedelta(days=2),
        generated_at=now_utc,
    )
    session.add(profile)

    segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        segment_name="VIP Shoppers",
        segment_definition={"type": "vip"},
    )
    session.add(segment)
    await session.flush()

    member = ShopperSegmentMember(
        segment_id=segment.segment_id,
        shopper_id=shopper_id,
        generated_at=now_utc - timedelta(days=5),
    )
    session.add(member)

    # Add a converted journey
    journey_id = uuid.uuid4()
    journey = ShopperJourney(
        journey_id=journey_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        started_at=now_utc - timedelta(days=3),
        ended_at=now_utc - timedelta(days=3, hours=-1),
        journey_status="CONVERTED",
        converted=True,
        entry_source="google",
        generated_at=now_utc,
    )
    session.add(journey)
    await session.commit()

    payload = await build_shopper_behaviour_facts(session, shopper_id)

    assert payload.metadata.knowledge_type == KnowledgeType.SHOPPER_BEHAVIOUR
    assert payload.metadata.entity_type == "shopper"
    assert payload.metadata.entity_id == shopper_id
    assert payload.metadata.is_current is True
    assert payload.metadata.access_scope == KnowledgeAccessScope.MERCHANT

    expected_point_id = generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR, shopper_id)
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.total_orders == 3
    assert facts.total_spend == Decimal("320.00")
    assert facts.average_order_value == Decimal("106.67")
    assert facts.wishlist_item_count == 5
    assert facts.save_for_later_item_count == 2
    assert facts.campaign_engagement_count == 12
    assert facts.preferred_category == "Footwear"
    assert facts.preferred_size == "9.5"
    assert "VIP Shoppers" in facts.segments
    assert facts.total_journeys == 1
    assert facts.converted_journeys == 1

    # Ensure no PII fields exist on facts schema
    assert not hasattr(facts, "email")
    assert not hasattr(facts, "customer_lifetime_value")
    assert not hasattr(facts, "purchase_frequency")
    assert not hasattr(facts, "lifecycle_stage")

    # Non-existent shopper must raise ValueError
    with pytest.raises(ValueError, match="not found"):
        await build_shopper_behaviour_facts(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_build_shopper_journey_facts_completed(session, sample_merchant):
    merchant = sample_merchant
    shopper_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant.merchant_id,
        email="journey_fact@test.com",
        first_seen_at=now_utc - timedelta(days=5),
        last_seen_at=now_utc,
    )
    session.add(shopper)

    order_id = uuid.uuid4()
    order = Order(
        order_id=order_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        currency="USD",
        total_amount=175.50,
        placed_at=now_utc - timedelta(hours=1),
        order_status="completed",
        created_at=now_utc - timedelta(hours=1),
    )
    session.add(order)

    # Create source events
    p_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    se1 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        session_id=sess_id,
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        source="shopify",
        event_timestamp=now_utc - timedelta(hours=2),
        payload={"product_id": str(p_id)},
    )
    se2 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        session_id=sess_id,
        event_type=ShopperEventType.PRODUCT_SEARCHED.value,
        event_version=1,
        source="shopify",
        event_timestamp=now_utc - timedelta(hours=1, minutes=50),
        payload={"search_query": "running shoes"},
    )
    se3 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        session_id=sess_id,
        event_type=ShopperEventType.ADD_TO_CART.value,
        event_version=1,
        source="shopify",
        event_timestamp=now_utc - timedelta(hours=1, minutes=40),
        payload={"product_id": str(p_id), "quantity": 1},
    )
    se4 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        session_id=sess_id,
        event_type=ShopperEventType.CHECKOUT_STARTED.value,
        event_version=1,
        source="shopify",
        event_timestamp=now_utc - timedelta(hours=1, minutes=20),
        payload={"cart_value": 175.50},
    )
    se5 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        session_id=sess_id,
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        source="shopify",
        event_timestamp=now_utc - timedelta(hours=1),
        payload={"order_id": str(order_id), "total_amount": 175.50},
    )
    session.add_all([se1, se2, se3, se4, se5])
    await session.flush()

    # Create journey
    journey_id = uuid.uuid4()
    journey = ShopperJourney(
        journey_id=journey_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        started_at=now_utc - timedelta(hours=2),
        ended_at=now_utc - timedelta(hours=1),
        journey_status="CONVERTED",
        converted=True,
        order_id=order_id,
        entry_source="direct",
        generated_at=now_utc,
    )
    session.add(journey)
    await session.flush()

    # Add journey events linking to source events
    for idx, se in enumerate([se1, se2, se3, se4, se5], start=1):
        je = ShopperJourneyEvent(
            journey_event_id=uuid.uuid4(),
            journey_id=journey_id,
            source_event_category="shopper",
            source_event_id=se.event_id,
            event_type=se.event_type,
            event_timestamp=se.event_timestamp,
            sequence_number=idx,
        )
        session.add(je)
    await session.commit()

    payload = await build_shopper_journey_facts(session, journey_id)

    assert payload.metadata.knowledge_type == KnowledgeType.SHOPPER_JOURNEY
    assert payload.metadata.entity_type == "journey"
    assert payload.metadata.entity_id == journey_id
    assert payload.metadata.is_current is False
    assert payload.metadata.access_scope == KnowledgeAccessScope.MERCHANT

    expected_point_id = generate_knowledge_point_id(KnowledgeType.SHOPPER_JOURNEY, journey_id)
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.journey_status == "CONVERTED"
    assert facts.converted is True
    assert facts.order_id == order_id
    assert facts.order_total_amount == Decimal("175.50")
    assert facts.duration_seconds == 3600
    assert str(p_id) in facts.products_viewed
    assert "running shoes" in facts.search_queries
    assert facts.cart_add_count == 1
    assert facts.checkout_started is True
    assert facts.touchpoint_count == 5

    source_types = [s.source_type for s in payload.metadata.source_references]
    assert "shopper_journeys" in source_types
    assert "orders" in source_types


@pytest.mark.asyncio
async def test_build_shopper_journey_facts_open_rejected(session, sample_merchant):
    merchant = sample_merchant
    shopper_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant.merchant_id,
        email="open_journey@test.com",
        first_seen_at=now_utc,
        last_seen_at=now_utc,
    )
    session.add(shopper)

    journey_id = uuid.uuid4()
    journey = ShopperJourney(
        journey_id=journey_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper_id,
        started_at=now_utc - timedelta(minutes=15),
        ended_at=None,
        journey_status="OPEN",
        converted=False,
        entry_source="direct",
        generated_at=now_utc,
    )
    session.add(journey)
    await session.commit()

    with pytest.raises(ValueError, match="OPEN journeys remain excluded because they are incomplete and mutable"):
        await build_shopper_journey_facts(session, journey_id)


@pytest.mark.asyncio
async def test_build_campaign_summary_facts(session, sample_merchant):
    merchant = sample_merchant
    campaign_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)

    segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        segment_name="Newsletter Subscribers",
        segment_definition={"type": "newsletter"},
    )
    session.add(segment)
    await session.flush()

    campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant.merchant_id,
        segment_id=segment.segment_id,
        campaign_name="Spring Sale Launch",
        campaign_type="promotional",
        campaign_medium="email",
        status="active",
        start_at=now_utc - timedelta(days=7),
        end_at=now_utc + timedelta(days=7),
        created_at=now_utc - timedelta(days=7),
    )
    session.add(campaign)
    await session.commit()

    payload = await build_campaign_summary_facts(session, campaign_id)

    assert payload.metadata.knowledge_type == KnowledgeType.CAMPAIGN_SUMMARY
    assert payload.metadata.entity_type == "campaign"
    assert payload.metadata.entity_id == campaign_id
    assert payload.metadata.is_current is True
    assert payload.metadata.access_scope == KnowledgeAccessScope.MERCHANT

    expected_point_id = generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY, campaign_id)
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.campaign_name == "Spring Sale Launch"
    assert facts.campaign_type == "promotional"
    assert facts.campaign_medium == "email"
    assert facts.target_segment_name == "Newsletter Subscribers"
    assert facts.status == "active"
    assert facts.first_touch_conversions == 0
    assert facts.audience_reached_count == 0

    with pytest.raises(ValueError, match="not found"):
        await build_campaign_summary_facts(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_build_merchant_performance_facts(session, sample_merchant):
    merchant = sample_merchant
    d_start = date(2026, 1, 1)
    d_end = date(2026, 1, 31)

    await session.execute(
        delete(MerchantMetricsDaily).where(
            MerchantMetricsDaily.merchant_id == merchant.merchant_id,
            MerchantMetricsDaily.metric_date >= d_start,
            MerchantMetricsDaily.metric_date <= d_end,
        )
    )
    await session.commit()

    # Insert daily metrics for the period
    shopper = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        email="perf_shopper@test.com",
        first_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    session.add(shopper)
    await session.flush()

    order = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        currency="USD",
        total_amount=1200.00,
        placed_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        order_status="completed",
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )
    session.add(order)

    m1 = MerchantMetricsDaily(
        merchant_id=merchant.merchant_id,
        metric_date=date(2026, 1, 15),
        revenue=1200.00,
        order_count=1,
        unique_shoppers=8,
        new_shoppers=4,
        session_count=50,
        converted_session_count=10,
        product_view_count=100,
        wishlist_add_count=10,
        save_for_later_count=5,
        add_to_cart_count=20,
        checkout_count=12,
        purchase_count=10,
        conversion_rate=0.20,
        average_order_value=1200.00,
        platform_login_count=1,
        campaign_created_count=0,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(m1)
    await session.commit()

    payload = await build_merchant_performance_facts(session, merchant.merchant_id, d_start, d_end)

    assert payload.metadata.knowledge_type == KnowledgeType.MERCHANT_PERFORMANCE
    assert payload.metadata.entity_type == "merchant"
    assert payload.metadata.entity_id == merchant.merchant_id
    assert payload.metadata.period_start == d_start
    assert payload.metadata.period_end == d_end
    assert payload.metadata.is_current is False
    assert payload.metadata.access_scope == KnowledgeAccessScope.MERCHANT

    expected_point_id = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE, merchant.merchant_id, d_start, d_end
    )
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.period_start == d_start
    assert facts.period_end == d_end
    assert facts.total_revenue == Decimal("1200.00")
    assert facts.order_count == 1
    assert facts.unique_shoppers == 8
    assert facts.new_shoppers == 4

    # Invalid range must raise ValueError
    with pytest.raises(ValueError, match="period_start cannot be after period_end"):
        await build_merchant_performance_facts(session, merchant.merchant_id, d_end, d_start)


@pytest.mark.asyncio
async def test_build_platform_performance_facts(session):
    d_start = date(2025, 7, 1)
    d_end = date(2025, 7, 31)

    await session.execute(
        delete(PlatformMetricsDaily).where(
            PlatformMetricsDaily.metric_date >= d_start,
            PlatformMetricsDaily.metric_date <= d_end,
        )
    )
    await session.commit()

    # Insert daily metrics for the period
    p1 = PlatformMetricsDaily(
        metric_date=date(2025, 7, 15),
        active_merchants=5,
        new_merchants=2,
        installed_merchants=2,
        uninstalled_merchants=0,
        new_subscriptions=2,
        subscription_upgrades=0,
        subscription_downgrades=0,
        subscription_cancellations=0,
        total_revenue=5000.00,
        total_orders=45,
        active_shoppers=80,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(p1)
    await session.commit()

    payload = await build_platform_performance_facts(session, d_start, d_end)

    assert payload.metadata.knowledge_type == KnowledgeType.PLATFORM_PERFORMANCE
    assert payload.metadata.entity_type == "platform"
    assert payload.metadata.entity_id is None
    assert payload.metadata.merchant_id is None
    assert payload.metadata.period_start == d_start
    assert payload.metadata.period_end == d_end
    assert payload.metadata.is_current is False
    assert payload.metadata.access_scope == KnowledgeAccessScope.INTERNAL

    expected_point_id = generate_knowledge_point_id(
        KnowledgeType.PLATFORM_PERFORMANCE, period_start=d_start, period_end=d_end
    )
    assert payload.metadata.point_id == expected_point_id

    facts = payload.facts
    assert facts.period_start == d_start
    assert facts.period_end == d_end
    assert facts.active_merchants == 5
    assert facts.new_merchants == 2
    assert facts.total_revenue == Decimal("5000.00")
    assert facts.total_orders == 45
    assert facts.active_shoppers == 80

    # Invalid range must raise ValueError
    with pytest.raises(ValueError, match="period_start cannot be after period_end"):
        await build_platform_performance_facts(session, d_end, d_start)
