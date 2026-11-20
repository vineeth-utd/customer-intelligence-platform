import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.campaign import Campaign
from app.models.event import CampaignEvent
from app.models.merchant import Merchant, Subscription, SubscriptionPlan
from app.models.processing_state import EntityDomainActivity
from app.models.shopper import Shopper, ShopperSegment
from app.reference_data.plans import PlanKey
from app.schemas.events.event_types import CampaignEventType
from app.services.analytics import generate_daily_metrics
from app.services.merchant import initialize_reference_data
from app.services.merchant_health import generate_merchant_health_callback
from app.services.segment import refresh_shopper_segment_membership_callback


@pytest.fixture
async def session(db_session):
    yield db_session


@pytest.fixture
async def setup_test_merchant(session):
    await initialize_reference_data(session)
    await session.commit()

    merchant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    merchant = Merchant(
        merchant_id=merchant_id,
        shopify_store_id=f"dep-{merchant_id.hex[:8]}.myshopify.com",
        merchant_name="Dependency Test Store",
        email=f"dep-{merchant_id.hex[:8]}@test.com",
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
    await session.commit()
    return merchant


@pytest.mark.asyncio
async def test_merchant_health_emits_health_domain_activity(session, setup_test_merchant):
    merchant = setup_test_merchant
    now = datetime.now(timezone.utc)

    await generate_merchant_health_callback(session, merchant.merchant_id, evaluation_time=now)
    await session.commit()

    stmt = select(EntityDomainActivity).where(
        EntityDomainActivity.entity_type == "merchant",
        EntityDomainActivity.entity_id == merchant.merchant_id,
        EntityDomainActivity.domain == "health",
    )
    activity = await session.scalar(stmt)
    assert activity is not None
    assert activity.domain == "health"
    assert activity.last_activity_at == now


@pytest.mark.asyncio
async def test_segment_membership_emits_segment_domain_activity(session, setup_test_merchant):
    merchant = setup_test_merchant
    shopper_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    shopper = Shopper(
        shopper_id=shopper_id,
        merchant_id=merchant.merchant_id,
        email="shopper_segment@test.com",
        first_seen_at=now - timedelta(days=10),
        last_seen_at=now,
    )
    session.add(shopper)

    segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        segment_name="All Shoppers",
        segment_definition={"type": "all_shoppers"},
    )
    session.add(segment)
    await session.commit()

    await refresh_shopper_segment_membership_callback(session, shopper_id, as_of=now)
    await session.commit()

    stmt = select(EntityDomainActivity).where(
        EntityDomainActivity.entity_type == "shopper",
        EntityDomainActivity.entity_id == shopper_id,
        EntityDomainActivity.domain == "segment",
    )
    activity = await session.scalar(stmt)
    assert activity is not None
    assert activity.domain == "segment"
    assert activity.last_activity_at == now


@pytest.mark.asyncio
async def test_campaign_analytics_emits_analytics_domain_activity(session, setup_test_merchant):
    merchant = setup_test_merchant
    campaign_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    metric_date = now.date()

    segment = ShopperSegment(
        segment_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        segment_name="Target Seg",
        segment_definition={"type": "all_shoppers"},
    )
    session.add(segment)
    await session.flush()

    campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant.merchant_id,
        segment_id=segment.segment_id,
        campaign_name="Black Friday",
        campaign_type="promotional",
        campaign_medium="email",
        status="active",
        start_at=now - timedelta(days=5),
        created_at=now - timedelta(days=5),
    )
    session.add(campaign)

    # Add an event today for this campaign
    event = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=campaign_id,
        merchant_id=merchant.merchant_id,
        shopper_id=None,
        event_type=CampaignEventType.EMAIL_DELIVERED.value,
        event_version=1,
        source="klaviyo",
        event_timestamp=now,
        payload={},
    )
    session.add(event)
    await session.commit()

    await generate_daily_metrics(session, metric_date)
    await session.commit()

    stmt = select(EntityDomainActivity).where(
        EntityDomainActivity.entity_type == "campaign",
        EntityDomainActivity.entity_id == campaign_id,
        EntityDomainActivity.domain == "analytics",
    )
    activity = await session.scalar(stmt)
    assert activity is not None
    assert activity.domain == "analytics"
