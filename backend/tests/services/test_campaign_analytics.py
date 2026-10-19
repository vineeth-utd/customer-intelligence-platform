import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text

from app.db.session import AsyncSessionLocal, engine
from app.models.campaign import Campaign
from app.models.event import CampaignEvent, ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.merchant import Merchant
from app.models.metrics import CampaignAnalyticsDaily
from app.models.order import Order
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.services.analytics import (
    get_campaign_attribution,
    get_campaign_audience_analysis,
    get_campaign_journey_correlation,
    get_campaign_performance,
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
async def setup_campaign_data(session):
    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    base_date = now_utc.date()

    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"shop-camp-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Campaign Analytics Store",
        email=f"camp-{merchant_id.hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
        created_at=now_utc - timedelta(days=60),
    )
    session.add(merchant)

    target_segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant_id,
        segment_name="High Intent VIPs",
        segment_definition={"type": "vip"},
        created_at=now_utc - timedelta(days=30),
    )
    other_segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant_id,
        segment_name="At Risk Browsers",
        segment_definition={"type": "at_risk"},
        created_at=now_utc - timedelta(days=30),
    )
    session.add_all([target_segment, other_segment])
    await session.flush()

    campaign_a = Campaign(
        campaign_id=uuid.uuid4(),
        merchant_id=merchant_id,
        segment_id=target_segment.segment_id,
        campaign_name="VIP Fall Launch",
        campaign_type="email",
        campaign_medium="email",
        status="active",
        start_at=now_utc - timedelta(days=20),
    )
    campaign_b = Campaign(
        campaign_id=uuid.uuid4(),
        merchant_id=merchant_id,
        segment_id=other_segment.segment_id,
        campaign_name="Winback SMS",
        campaign_type="sms",
        campaign_medium="sms",
        status="active",
        start_at=now_utc - timedelta(days=20),
    )
    session.add_all([campaign_a, campaign_b])
    await session.flush()

    yield {
        "merchant_id": merchant_id,
        "target_segment_id": target_segment.segment_id,
        "other_segment_id": other_segment.segment_id,
        "campaign_a_id": campaign_a.campaign_id,
        "campaign_b_id": campaign_b.campaign_id,
        "base_date": base_date,
        "now_utc": now_utc,
    }

    # Teardown
    await session.execute(delete(ShopperJourneyEvent).where(
        ShopperJourneyEvent.journey_id.in_(
            select(ShopperJourney.journey_id).where(ShopperJourney.merchant_id == merchant_id)
        )
    ))
    await session.execute(delete(ShopperJourney).where(ShopperJourney.merchant_id == merchant_id))
    await session.execute(delete(ShopperSegmentMember).where(
        ShopperSegmentMember.segment_id.in_([target_segment.segment_id, other_segment.segment_id])
    ))
    await session.execute(delete(CampaignAnalyticsDaily).where(
        CampaignAnalyticsDaily.campaign_id.in_([campaign_a.campaign_id, campaign_b.campaign_id])
    ))
    await session.execute(delete(CampaignEvent).where(CampaignEvent.merchant_id == merchant_id))
    await session.execute(delete(Campaign).where(Campaign.merchant_id == merchant_id))
    await session.execute(delete(Order).where(Order.merchant_id == merchant_id))
    await session.execute(delete(ShopperEvent).where(ShopperEvent.merchant_id == merchant_id))
    await session.execute(delete(Shopper).where(Shopper.merchant_id == merchant_id))
    await session.execute(delete(ShopperSegment).where(ShopperSegment.merchant_id == merchant_id))
    await session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_id))
    await session.commit()


@pytest.mark.asyncio
async def test_campaign_performance(session, setup_campaign_data):
    ctx = setup_campaign_data
    camp_a_id = ctx["campaign_a_id"]
    base_date = ctx["base_date"]

    start_date = base_date - timedelta(days=6)
    end_date = base_date

    # Seed 3 days of metrics in current period
    d1 = CampaignAnalyticsDaily(
        campaign_id=camp_a_id,
        metric_date=start_date,
        delivered_count=100,
        opened_count=40,
        clicked_count=10,
        converted_count=2,
        attributed_order_count=2,
        attributed_revenue=150.0,
        open_rate=0.4,
        click_through_rate=0.1,
        conversion_rate=0.02,
        generated_at=ctx["now_utc"],
    )
    d2 = CampaignAnalyticsDaily(
        campaign_id=camp_a_id,
        metric_date=start_date + timedelta(days=1),
        delivered_count=200,
        opened_count=100,
        clicked_count=30,
        converted_count=5,
        attributed_order_count=5,
        attributed_revenue=400.0,
        open_rate=0.5,
        click_through_rate=0.15,
        conversion_rate=0.025,
        generated_at=ctx["now_utc"],
    )
    session.add_all([d1, d2])
    await session.commit()

    res = await get_campaign_performance(session, camp_a_id, start_date, end_date)
    assert res is not None
    assert res.campaign_id == camp_a_id
    assert res.delivered_count == 300
    assert res.opened_count == 140
    assert res.clicked_count == 40
    assert res.open_rate == Decimal("140") / Decimal("300")
    assert res.click_through_rate == Decimal("40") / Decimal("300")
    assert len(res.trends) == 2
    # Prior period had zero activity
    assert res.prior_period_delivered == 0
    assert res.delivered_growth_pct is None


@pytest.mark.asyncio
async def test_campaign_attribution_multi_perspective(session, setup_campaign_data):
    ctx = setup_campaign_data
    merchant_id = ctx["merchant_id"]
    camp_a_id = ctx["campaign_a_id"]
    camp_b_id = ctx["campaign_b_id"]
    now_utc = ctx["now_utc"]
    base_date = ctx["base_date"]

    start_date = base_date - timedelta(days=6)
    end_date = base_date

    # 1. Direct Session Order (Shopper 1, Session 1)
    # Campaign A click in Session 1, Order 1 completed in Session 1
    shopper_1 = Shopper(shopper_id=uuid.uuid4(), merchant_id=merchant_id, first_seen_at=now_utc - timedelta(days=10))
    session.add(shopper_1)
    await session.flush()

    sess_1 = uuid.uuid4()
    order_1 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1.shopper_id,
        order_status="completed",
        currency="USD",
        session_id=sess_1,
        total_amount=150.0,
        placed_at=now_utc - timedelta(days=3),
        completed_at=now_utc - timedelta(days=3),
    )
    ce_click_1 = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_1.shopper_id,
        session_id=sess_1,
        event_type="EMAIL_CLICKED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=3, hours=1),
        payload={"url": "https://example.com"},
        source="email",
        processed=True,
    )
    session.add_all([order_1, ce_click_1])

    # 2. Cross-Session Multi-Campaign Journey (Shopper 2)
    # Touch 1: Campaign A click in Session 2 (day -5)
    # Touch 2: Campaign B click in Session 3 (day -2)
    # Order 2: Session 3 (day -2), amount 250.0
    # Journey: started day -5, ended day -2, status CONVERTED
    shopper_2 = Shopper(shopper_id=uuid.uuid4(), merchant_id=merchant_id, first_seen_at=now_utc - timedelta(days=10))
    session.add(shopper_2)
    await session.flush()

    sess_2 = uuid.uuid4()
    sess_3 = uuid.uuid4()

    ce_touch_a = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_2.shopper_id,
        session_id=sess_2,
        event_type="EMAIL_CLICKED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=5),
        payload={"url": "https://example.com/a"},
        source="email",
        processed=True,
    )
    ce_touch_b = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_b_id,
        merchant_id=merchant_id,
        shopper_id=shopper_2.shopper_id,
        session_id=sess_3,
        event_type="SMS_CLICKED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=2),
        payload={"url": "https://example.com/b"},
        source="sms",
        processed=True,
    )
    order_2 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_2.shopper_id,
        order_status="completed",
        currency="USD",
        session_id=sess_3,
        total_amount=250.0,
        placed_at=now_utc - timedelta(days=2),
        completed_at=now_utc - timedelta(days=2),
    )
    journey_2 = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_2.shopper_id,
        started_at=now_utc - timedelta(days=5),
        ended_at=now_utc - timedelta(days=2),
        journey_status="CONVERTED",
        converted=True,
        order_id=order_2.order_id,
        entry_source="email",
        generated_at=now_utc,
    )
    session.add_all([ce_touch_a, ce_touch_b, order_2, journey_2])
    await session.flush()

    sje_1 = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey_2.journey_id,
        source_event_category="campaign",
        source_event_id=ce_touch_a.event_id,
        event_type="EMAIL_CLICKED",
        event_timestamp=ce_touch_a.event_timestamp,
        sequence_number=1,
    )
    sje_2 = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=journey_2.journey_id,
        source_event_category="campaign",
        source_event_id=ce_touch_b.event_id,
        event_type="SMS_CLICKED",
        event_timestamp=ce_touch_b.event_timestamp,
        sequence_number=2,
    )
    session.add_all([sje_1, sje_2])

    # 3. Explicit CAMPAIGN_CONVERTED event for Campaign A
    order_3 = Order(
        order_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_1.shopper_id,
        order_status="completed",
        currency="USD",
        session_id=None,
        total_amount=75.0,
        placed_at=now_utc - timedelta(days=1),
        completed_at=now_utc - timedelta(days=1),
    )
    ce_explicit = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_1.shopper_id,
        session_id=None,
        event_type="CAMPAIGN_CONVERTED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=1),
        payload={"order_id": str(order_3.order_id)},
        source="campaign",
        processed=True,
    )
    session.add_all([order_3, ce_explicit])
    await session.commit()

    # Query attribution for Campaign A
    res_a = await get_campaign_attribution(session, camp_a_id, start_date, end_date)
    assert res_a is not None

    # Direct session: Order 1 (150.0)
    assert res_a.direct_session.conversions_count == 1
    assert res_a.direct_session.attributed_revenue == Decimal("150.0")

    # Journey First-Touch: Order 2 (250.0) - Campaign A was sequence 1!
    assert res_a.first_touch_journey.conversions_count == 1
    assert res_a.first_touch_journey.attributed_revenue == Decimal("250.0")

    # Journey Last-Touch: 0 for Campaign A (Campaign B was sequence 2!)
    assert res_a.last_touch_journey.conversions_count == 0
    assert res_a.last_touch_journey.attributed_revenue == Decimal("0.0")

    # Journey Assisted (Any-Touch): Order 2 (250.0)
    assert res_a.assisted_journey.conversions_count == 1
    assert res_a.assisted_journey.attributed_revenue == Decimal("250.0")

    # Explicit recorded conversion: Order 3 (75.0)
    assert res_a.explicit_recorded.conversions_count == 1
    assert res_a.explicit_recorded.attributed_revenue == Decimal("75.0")

    # Query attribution for Campaign B
    res_b = await get_campaign_attribution(session, camp_b_id, start_date, end_date)
    assert res_b is not None

    # Journey First-Touch: 0 for Campaign B
    assert res_b.first_touch_journey.conversions_count == 0
    # Journey Last-Touch: 1 for Campaign B (Order 2, 250.0)
    assert res_b.last_touch_journey.conversions_count == 1
    assert res_b.last_touch_journey.attributed_revenue == Decimal("250.0")
    # Journey Assisted: 1 for Campaign B (Order 2, 250.0)
    assert res_b.assisted_journey.conversions_count == 1
    assert res_b.assisted_journey.attributed_revenue == Decimal("250.0")
    # Last touch was in same session as order (sess_3 == sess_3)
    assert res_b.direct_vs_cross_session_journeys["direct_session"] == 1


@pytest.mark.asyncio
async def test_campaign_journey_correlation(session, setup_campaign_data):
    ctx = setup_campaign_data
    merchant_id = ctx["merchant_id"]
    camp_a_id = ctx["campaign_a_id"]
    now_utc = ctx["now_utc"]
    base_date = ctx["base_date"]

    start_date = base_date - timedelta(days=6)
    end_date = base_date

    shopper = Shopper(shopper_id=uuid.uuid4(), merchant_id=merchant_id, first_seen_at=now_utc - timedelta(days=10))
    session.add(shopper)
    await session.flush()

    # Journey 1: Converted
    j_conv = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=now_utc - timedelta(days=4),
        ended_at=now_utc - timedelta(days=4) + timedelta(hours=2),
        journey_status="CONVERTED",
        converted=True,
        entry_source="email",
        generated_at=now_utc,
    )
    # Journey 2: Completed Non-Converting (dropped off at CHECKOUT_STARTED)
    j_drop = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=now_utc - timedelta(days=3),
        ended_at=now_utc - timedelta(days=3) + timedelta(hours=1),
        journey_status="NON_CONVERTING",
        converted=False,
        entry_source="email",
        generated_at=now_utc,
    )
    # Journey 3: Still Open
    j_open = ShopperJourney(
        journey_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper.shopper_id,
        started_at=now_utc - timedelta(days=1),
        journey_status="OPEN",
        converted=False,
        entry_source="email",
        generated_at=now_utc,
    )
    session.add_all([j_conv, j_drop, j_open])
    await session.flush()

    # Link events from Campaign A to each journey
    for j in [j_conv, j_drop, j_open]:
        ce = CampaignEvent(
            event_id=uuid.uuid4(),
            campaign_id=camp_a_id,
            merchant_id=merchant_id,
            shopper_id=shopper.shopper_id,
            session_id=uuid.uuid4(),
            event_type="EMAIL_CLICKED",
            event_version=1,
            event_timestamp=j.started_at,
            payload={},
            source="email",
            processed=True,
        )
        session.add(ce)
        await session.flush()
        sje = ShopperJourneyEvent(
            journey_event_id=uuid.uuid4(),
            journey_id=j.journey_id,
            source_event_category="campaign",
            source_event_id=ce.event_id,
            event_type="EMAIL_CLICKED",
            event_timestamp=j.started_at,
            sequence_number=1,
        )
        session.add(sje)

    # Add drop-off event for j_drop
    sje_drop = ShopperJourneyEvent(
        journey_event_id=uuid.uuid4(),
        journey_id=j_drop.journey_id,
        source_event_category="shopper",
        source_event_id=uuid.uuid4(),
        event_type="CHECKOUT_STARTED",
        event_timestamp=j_drop.ended_at,
        sequence_number=2,
    )
    session.add(sje_drop)
    await session.commit()

    res = await get_campaign_journey_correlation(session, camp_a_id, start_date, end_date)
    assert res is not None
    assert res.total_journeys_touched == 3
    assert res.converted_journeys == 1
    assert res.non_converting_journeys == 1
    assert res.open_journeys == 1
    # Conversion rate calculated from resolved journeys only (1 / 2 = 0.50)
    assert res.journey_conversion_rate == Decimal("0.5")
    # Drop-off stage is CHECKOUT_STARTED
    assert res.drop_off_stages == {"CHECKOUT_STARTED": 1}
    # Duration was 2 hours = 7200 seconds
    assert res.average_touch_to_conversion_seconds == 7200.0


@pytest.mark.asyncio
async def test_campaign_audience_analysis(session, setup_campaign_data):
    ctx = setup_campaign_data
    merchant_id = ctx["merchant_id"]
    target_seg_id = ctx["target_segment_id"]
    other_seg_id = ctx["other_segment_id"]
    camp_a_id = ctx["campaign_a_id"]
    now_utc = ctx["now_utc"]

    # Shopper 1 in target segment
    shopper_target = Shopper(shopper_id=uuid.uuid4(), merchant_id=merchant_id, first_seen_at=now_utc - timedelta(days=20))
    # Shopper 2 in other segment
    shopper_other = Shopper(shopper_id=uuid.uuid4(), merchant_id=merchant_id, first_seen_at=now_utc - timedelta(days=20))
    session.add_all([shopper_target, shopper_other])
    await session.flush()

    mem_1 = ShopperSegmentMember(segment_id=target_seg_id, shopper_id=shopper_target.shopper_id, generated_at=now_utc)
    mem_2 = ShopperSegmentMember(segment_id=other_seg_id, shopper_id=shopper_other.shopper_id, generated_at=now_utc)
    session.add_all([mem_1, mem_2])

    # Campaign A delivers to both shoppers, but only shopper_target engages (opens & clicks) and converts
    ce_del_1 = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_target.shopper_id,
        event_type="EMAIL_DELIVERED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=5),
        payload={},
        source="email",
        processed=True,
    )
    ce_open_1 = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_target.shopper_id,
        event_type="EMAIL_OPENED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=5),
        payload={},
        source="email",
        processed=True,
    )
    ce_del_2 = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_other.shopper_id,
        event_type="EMAIL_DELIVERED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=5),
        payload={},
        source="email",
        processed=True,
    )
    ce_conv = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=camp_a_id,
        merchant_id=merchant_id,
        shopper_id=shopper_target.shopper_id,
        event_type="CAMPAIGN_CONVERTED",
        event_version=1,
        event_timestamp=now_utc - timedelta(days=4),
        payload={},
        source="campaign",
        processed=True,
    )
    session.add_all([ce_del_1, ce_open_1, ce_del_2, ce_conv])
    await session.commit()

    res = await get_campaign_audience_analysis(session, camp_a_id)
    assert res is not None
    assert res.target_segment_id == target_seg_id
    assert res.target_segment_current_members == 1
    assert res.unique_shoppers_reached == 2
    assert res.unique_shoppers_engaged == 1
    assert res.unique_shoppers_converted == 1

    # Target segment vs non-target
    assert res.target_segment_current_members_reached == 1
    assert res.target_segment_current_members_engaged == 1
    assert res.target_segment_current_members_converted == 1

    assert res.non_target_current_shoppers_reached == 1
    assert res.non_target_current_shoppers_engaged == 0
    assert res.non_target_current_shoppers_converted == 0

    # Breakdown has both segments
    seg_names = {s.segment_name for s in res.current_segments_breakdown}
    assert "High Intent VIPs" in seg_names
    assert "At Risk Browsers" in seg_names


@pytest.mark.asyncio
async def test_campaign_analytics_validations(session, setup_campaign_data):
    ctx = setup_campaign_data
    camp_a_id = ctx["campaign_a_id"]
    base_date = ctx["base_date"]

    # Invalid date range
    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_campaign_performance(session, camp_a_id, base_date, base_date - timedelta(days=1))

    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_campaign_attribution(session, camp_a_id, base_date, base_date - timedelta(days=1))

    with pytest.raises(ValueError, match="start_date cannot be after end_date"):
        await get_campaign_journey_correlation(session, camp_a_id, base_date, base_date - timedelta(days=1))

    # Non-existent campaign
    non_existent = uuid.uuid4()
    assert await get_campaign_performance(session, non_existent, base_date, base_date) is None
    assert await get_campaign_attribution(session, non_existent, base_date, base_date) is None
    assert await get_campaign_journey_correlation(session, non_existent, base_date, base_date) is None
    assert await get_campaign_audience_analysis(session, non_existent) is None
