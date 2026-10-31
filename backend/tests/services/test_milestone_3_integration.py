import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.campaign import Campaign
from app.models.event import CampaignEvent, MerchantEvent, ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant, MerchantFeature, PlanFeature, PlatformFeature, Subscription, SubscriptionPlan
from app.models.merchant_health import MerchantHealth
from app.models.metrics import CampaignAnalyticsDaily, MerchantMetricsDaily
from app.models.order import Order
from app.models.processing_state import EntityDomainActivity, EntityProcessingState
from app.models.profile import MerchantProfile, ShopperProfile
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.reference_data.plans import PlanKey
from app.reference_data.segments import SEGMENT_CATALOG
from app.scheduler.incremental import process_incremental_target
from app.scheduler.journey_job import run_shopper_journey_job
from app.scheduler.merchant_health_job import run_merchant_health_job
from app.scheduler.profile_job import run_merchant_profile_job, run_shopper_profile_job
from app.scheduler.segment_job import run_shopper_segment_membership_job
from app.services.analytics import (
    generate_daily_metrics,
    get_campaign_attribution,
    get_campaign_audience_analysis,
    get_campaign_performance,
    get_conversion_funnel,
    get_revenue_analytics,
    get_shopper_behavior_analytics,
    get_shopper_journey_analytics,
    refresh_aggregate_views,
)
from app.services.merchant import initialize_reference_data
from app.services.merchant_health import get_merchant_health, get_merchant_health_with_factors
from app.services.processing_state import get_eligible_entities_for_target
from app.services.segment import (
    get_members_for_segment,
    get_segments_for_shopper,
    initialize_merchant_segments,
)


@pytest.fixture
async def session():
    await engine.dispose()
    s = AsyncSessionLocal()
    try:
        await s.execute(text("SELECT 1"))
    except Exception as exc:
        await s.close()
        pytest.skip(f"Database unavailable: {exc}")

    yield s
    await s.close()
    await engine.dispose()


@pytest.fixture
async def setup_milestone_3_data(session: AsyncSession):
    """Seed a clean, minimal merchant ecosystem spanning catalog, plans, segments, and shoppers."""
    await initialize_reference_data(session)
    await session.commit()

    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    base_date = now_utc.date()

    # 1. Merchant & Subscription
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"shop-m3-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="M3 Integration Store",
        email=f"m3-{merchant_id.hex[:8]}@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=60),
    )
    session.add(merchant)

    res_plan = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.plan_key == PlanKey.GROWTH.value))
    growth_plan = res_plan.scalar_one()

    sub = Subscription(
        subscription_id=uuid.uuid4(),
        merchant_id=merchant_id,
        plan_id=growth_plan.plan_id,
        status="active",
        billing_cycle="monthly",
        amount_paid=79.0,
        started_at=now_utc - timedelta(days=30),
        renewal_at=now_utc + timedelta(days=30),
    )
    session.add(sub)

    # 2. Canonical Segments for Merchant
    await initialize_merchant_segments(session, merchant_id)
    await session.flush()

    res_segs = await session.execute(select(ShopperSegment).where(ShopperSegment.merchant_id == merchant_id))
    segments_by_name = {s.segment_name: s for s in res_segs.scalars().all()}
    vip_segment = segments_by_name["High Value Customers"]

    # 3. Campaign targeting VIP segment
    campaign = Campaign(
        campaign_id=uuid.uuid4(),
        merchant_id=merchant_id,
        segment_id=vip_segment.segment_id,
        campaign_name="VIP Rewards Fall",
        campaign_type="email",
        campaign_medium="email",
        status="active",
        start_at=now_utc - timedelta(days=20),
    )
    session.add(campaign)

    # 4. Two Shoppers
    # Shopper 1: Active VIP shopper with orders
    shopper_1 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        first_seen_at=now_utc - timedelta(days=40),
        created_at=now_utc - timedelta(days=40),
    )
    # Shopper 2: Cart abandoner / drop-off shopper
    shopper_2 = Shopper(
        shopper_id=uuid.uuid4(),
        merchant_id=merchant_id,
        first_seen_at=now_utc - timedelta(days=5),
        created_at=now_utc - timedelta(days=5),
    )
    session.add_all([shopper_1, shopper_2])
    await session.commit()

    yield {
        "merchant_id": merchant_id,
        "campaign_id": campaign.campaign_id,
        "shopper_1_id": shopper_1.shopper_id,
        "shopper_2_id": shopper_2.shopper_id,
        "segments": segments_by_name,
        "now_utc": now_utc,
        "base_date": base_date,
    }

    # Teardown
    await session.execute(delete(ShopperJourneyEvent).where(
        ShopperJourneyEvent.journey_id.in_(
            select(ShopperJourney.journey_id).where(ShopperJourney.merchant_id == merchant_id)
        )
    ))
    await session.execute(delete(ShopperJourney).where(ShopperJourney.merchant_id == merchant_id))
    await session.execute(delete(ShopperSegmentMember).where(
        ShopperSegmentMember.segment_id.in_([s.segment_id for s in segments_by_name.values()])
    ))
    await session.execute(delete(MerchantHealth).where(MerchantHealth.merchant_id == merchant_id))
    await session.execute(delete(MerchantProfile).where(MerchantProfile.merchant_id == merchant_id))
    await session.execute(delete(ShopperProfile).where(
        ShopperProfile.shopper_id.in_([shopper_1.shopper_id, shopper_2.shopper_id])
    ))
    await session.execute(delete(CampaignAnalyticsDaily).where(CampaignAnalyticsDaily.campaign_id == campaign.campaign_id))
    await session.execute(delete(CampaignEvent).where(CampaignEvent.merchant_id == merchant_id))
    await session.execute(delete(Campaign).where(Campaign.merchant_id == merchant_id))
    await session.execute(delete(Order).where(Order.merchant_id == merchant_id))
    await session.execute(delete(ShopperEvent).where(ShopperEvent.merchant_id == merchant_id))
    await session.execute(delete(Shopper).where(Shopper.merchant_id == merchant_id))
    await session.execute(delete(ShopperSegment).where(ShopperSegment.merchant_id == merchant_id))
    await session.execute(delete(Subscription).where(Subscription.merchant_id == merchant_id))
    await session.execute(delete(MerchantMetricsDaily).where(MerchantMetricsDaily.merchant_id == merchant_id))
    await session.execute(delete(EntityDomainActivity).where(
        EntityDomainActivity.entity_id.in_([merchant_id, shopper_1.shopper_id, shopper_2.shopper_id])
    ))
    await session.execute(delete(EntityProcessingState).where(
        EntityProcessingState.entity_id.in_([merchant_id, shopper_1.shopper_id, shopper_2.shopper_id])
    ))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await session.commit()


@pytest.mark.asyncio
async def test_milestone_3_pipeline_and_dependency_cascade(session: AsyncSession, setup_milestone_3_data: dict):
    """
    Scenario 1: Cross-product dependency cascade and scheduled processing flow.
    Verifies that raw events -> profile/journey jobs -> segment membership and merchant health jobs
    advance processing states and produce fully populated derived products.
    """
    ctx = setup_milestone_3_data
    merchant_id = ctx["merchant_id"]
    shopper_1_id = ctx["shopper_1_id"]
    shopper_2_id = ctx["shopper_2_id"]
    now = ctx["now_utc"]

    # 1. Ingest operational events for Shopper 1 (session + purchase = high spend)
    sess_1 = uuid.uuid4()
    order_1_id = uuid.uuid4()
    ev_session_1 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=sess_1,
        event_type="SESSION_STARTED",
        event_version=1,
        event_timestamp=now - timedelta(days=2),
        payload={"referrer": "https://google.com"},
        source="storefront",
        processed=True,
    )
    ev_order_1 = Order(
        order_id=order_1_id,
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=sess_1,
        order_status="completed",
        currency="USD",
        total_amount=600.0,
        placed_at=now - timedelta(days=2),
        completed_at=now - timedelta(days=2),
    )
    session.add_all([ev_session_1, ev_order_1])
    await session.commit()

    # 2. Run Milestone 2 generators
    # Shopper journeys & profiles
    await run_shopper_journey_job()
    await run_shopper_profile_job()
    await run_merchant_profile_job()

    # Verify Shopper 1 is eligible for segment_membership (profile activity recorded)
    eligible_segments = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_1_id in eligible_segments

    # 3. Run Milestone 3 scheduled jobs
    await run_shopper_segment_membership_job()
    await run_merchant_health_job()

    # 4. Verify derived products
    # Shopper 1 should belong to "All Active Shoppers" and "High Value Customers"
    memberships = await get_segments_for_shopper(session, shopper_1_id)
    membership_names = {m.segment.segment_name for m in memberships}
    assert "All Active Shoppers" in membership_names
    assert "High Value Customers" in membership_names

    # Merchant Health record created and populated
    health = await get_merchant_health(session, merchant_id)
    assert health is not None
    assert health.merchant_id == merchant_id
    assert 0.0 <= float(health.health_score) <= 100.0
    assert health.health_status in ["HEALTHY", "NEEDS_ATTENTION", "AT_RISK"]

    # Verify processing states advanced atomically to SUCCESS
    res_state_seg = await session.execute(
        select(EntityProcessingState).where(
            EntityProcessingState.entity_id == shopper_1_id,
            EntityProcessingState.target_type == "segment_membership",
        )
    )
    state_seg = res_state_seg.scalar_one_or_none()
    assert state_seg is not None
    assert state_seg.last_generation_status == "SUCCESS"
    assert state_seg.last_generated_at is not None

    res_state_health = await session.execute(
        select(EntityProcessingState).where(
            EntityProcessingState.entity_id == merchant_id,
            EntityProcessingState.target_type == "merchant_health",
        )
    )
    state_health = res_state_health.scalar_one_or_none()
    assert state_health is not None
    assert state_health.last_generation_status == "SUCCESS"
    assert state_health.last_generated_at is not None


@pytest.mark.asyncio
async def test_milestone_3_incremental_invalidation_and_idempotency(session: AsyncSession, setup_milestone_3_data: dict):
    """
    Scenario 2: Incremental invalidation and idempotent recomputation.
    Verifies that new downstream domain activity marks entities eligible,
    re-running updates memberships deterministically, and re-running without changes is a no-op.
    """
    ctx = setup_milestone_3_data
    merchant_id = ctx["merchant_id"]
    shopper_2_id = ctx["shopper_2_id"]
    now = ctx["now_utc"]

    # Initial run: shopper_2 has no qualifying events
    await run_shopper_journey_job()
    await run_shopper_profile_job()
    await run_shopper_segment_membership_job()

    initial_memberships = await get_segments_for_shopper(session, shopper_2_id)
    assert len(initial_memberships) == 0

    # Ensure shopper_2 is no longer eligible
    eligible = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_2_id not in eligible

    # Simulate late-arriving cart abandonment activity (> 24 hours ago)
    journey = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_2_id,
        started_at=now - timedelta(hours=30),
        journey_status="OPEN",
        converted=False,
        generated_at=now,
    )
    session.add(journey)
    await session.flush()

    sje = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="ADD_TO_CART",
        event_timestamp=now - timedelta(hours=30),
        sequence_number=1,
    )
    session.add(sje)
    await session.commit()

    # Invalidate shopper_2 via journey activity
    t_inval = now + timedelta(seconds=1)
    activity = EntityDomainActivity(
        entity_type="shopper",
        entity_id=shopper_2_id,
        domain="journey",
        last_activity_at=t_inval,
    )
    await session.merge(activity)
    await session.commit()

    # Shopper 2 becomes eligible again
    eligible_after = await get_eligible_entities_for_target(session, "shopper", "segment_membership")
    assert shopper_2_id in eligible_after

    # Run segment job again
    await run_shopper_segment_membership_job()

    # Shopper 2 now deterministically qualifies for Cart Abandoners
    memberships_after = await get_segments_for_shopper(session, shopper_2_id)
    assert any(m.segment.segment_name == "Cart Abandoners" for m in memberships_after)

    # Idempotency check: run job once more, verify no duplicate records or state changes
    await run_shopper_segment_membership_job()
    memberships_repeat = await get_segments_for_shopper(session, shopper_2_id)
    assert len(memberships_repeat) == len(memberships_after)


@pytest.mark.asyncio
async def test_milestone_3_primary_business_intelligence_questions(session: AsyncSession, setup_milestone_3_data: dict):
    """
    Scenario 3: Deterministic answerability of primary MVP business-intelligence questions.
    Demonstrates that the platform answers the 5 core business questions directly from
    Business Service calls without relying on the AI layer.
    """
    ctx = setup_milestone_3_data
    merchant_id = ctx["merchant_id"]
    campaign_id = ctx["campaign_id"]
    shopper_1_id = ctx["shopper_1_id"]
    base_date = ctx["base_date"]
    now = ctx["now_utc"]

    # 1. Seed store daily metrics for conversion funnel & shopper behavior
    m_daily = MerchantMetricsDaily(
        merchant_id=merchant_id,
        metric_date=base_date,
        revenue=1200.0,
        order_count=10,
        unique_shoppers=50,
        new_shoppers=20,
        session_count=200,
        converted_session_count=10,
        product_view_count=150,
        wishlist_add_count=15,
        save_for_later_count=5,
        add_to_cart_count=40,
        checkout_count=20,
        purchase_count=10,
        conversion_rate=0.05,
        average_order_value=120.0,
        platform_login_count=2,
        campaign_created_count=1,
        feature_enable_count=0,
        feature_disable_count=0,
        generated_at=now,
    )
    session.add(m_daily)

    # Seed campaign daily metric
    c_daily = CampaignAnalyticsDaily(
        campaign_id=campaign_id,
        metric_date=base_date,
        delivered_count=100,
        opened_count=50,
        clicked_count=20,
        converted_count=5,
        attributed_order_count=5,
        attributed_revenue=600.0,
        open_rate=0.5,
        click_through_rate=0.2,
        conversion_rate=0.05,
        generated_at=now,
    )
    session.add(c_daily)

    # Seed campaign events for audience analysis & attribution
    sess_camp = uuid.uuid4()
    ce_click = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=sess_camp,
        event_type="EMAIL_CLICKED",
        event_version=1,
        event_timestamp=now - timedelta(hours=3),
        payload={"url": "https://example.com/vip"},
        source="email",
        processed=True,
    )
    order_camp = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=sess_camp,
        order_status="completed",
        currency="USD",
        total_amount=200.0,
        placed_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=2),
    )
    ev_active = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1_id,
        session_id=sess_camp,
        event_type="SESSION_STARTED",
        event_version=1,
        event_timestamp=now - timedelta(hours=3),
        payload={"url": "https://example.com/vip"},
        source="storefront",
        processed=True,
    )
    session.add_all([ce_click, ev_active, order_camp])
    await session.commit()

    # Generate merchant health
    await run_merchant_health_job()

    # -------------------------------------------------------------------------
    # Question 1: "Why did conversion decrease yesterday / what is our conversion funnel?"
    # -------------------------------------------------------------------------
    funnel = await get_conversion_funnel(session, merchant_id, base_date, base_date)
    assert funnel is not None
    assert funnel.overall_conversion_rate == Decimal("10") / Decimal("200")
    assert funnel.cart_abandonment_rate == Decimal("0.7500")  # (40 carts - 10 purchases) / 40 = 75%
    assert funnel.checkout_abandonment_rate == Decimal("0.5")  # (20 checkouts - 10 purchases) / 20 = 50%
    assert len(funnel.stages) == 5

    # -------------------------------------------------------------------------
    # Question 2: "Why is Merchant ABC at risk of churning / what is health status?"
    # -------------------------------------------------------------------------
    health_factors = await get_merchant_health_with_factors(session, merchant_id)
    assert health_factors is not None
    assert "health_score" in health_factors
    assert "churn_risk_score" in health_factors
    assert "contributing_factors" in health_factors
    assert "feature_adoption" in health_factors["contributing_factors"]
    assert "engagement" in health_factors["contributing_factors"]
    assert "business_performance" in health_factors["contributing_factors"]

    # -------------------------------------------------------------------------
    # Question 3: "Which shopper segments respond best to campaigns?"
    # -------------------------------------------------------------------------
    audience = await get_campaign_audience_analysis(session, campaign_id)
    assert audience is not None
    assert audience.unique_shoppers_reached > 0
    assert len(audience.current_segments_breakdown) > 0
    # Cross-segment performance breakdown provides comparative response rates
    assert any(s.segment_name == "High Value Customers" for s in audience.current_segments_breakdown)

    # -------------------------------------------------------------------------
    # Question 4: "How can I improve my store's conversion rate / what is shopper behavior?"
    # -------------------------------------------------------------------------
    behavior = await get_shopper_behavior_analytics(session, merchant_id, base_date, base_date)
    assert behavior is not None
    assert behavior.total_active_shoppers == 1
    assert behavior.total_purchasing_shoppers == 1
    assert behavior.average_order_value == Decimal("200.00")
    # Combined with funnel abandonment rates (75% cart abandonment), bottleneck is clearly isolated

    # -------------------------------------------------------------------------
    # Question 5: "What is the revenue attribution for Campaign X?"
    # -------------------------------------------------------------------------
    attrib = await get_campaign_attribution(session, campaign_id, base_date, base_date)
    assert attrib is not None
    # Direct session conversion captured from matching session_id
    assert attrib.direct_session.conversions_count == 1
    assert attrib.direct_session.attributed_revenue == Decimal("200.0")
    assert attrib.direct_session.average_order_value == Decimal("200.0")
