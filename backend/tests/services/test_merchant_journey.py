import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.campaign import Campaign
from app.models.event import CampaignEvent, MerchantEvent
from app.models.journey import MerchantJourney, MerchantJourneyEvent
from app.models.merchant import Merchant
from app.models.processing_state import EntityProcessingState
from app.data_access.processing_state import record_domain_activity
from app.scheduler.merchant_journey_job import run_merchant_journey_job
from app.schemas.events.event_types import CampaignEventType, MerchantEventType
from app.services.merchant_journey import generate_merchant_journeys_for_merchant


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
    await engine.dispose()


@pytest.fixture
async def merchant(session: AsyncSession) -> Merchant:
    merchant = Merchant(
        merchant_name="Test Merchant for Merchant Journey",
        email=f"merchant_{uuid.uuid4().hex[:8]}@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        shopify_store_id=f"merchant-journey-{uuid.uuid4().hex[:8]}.myshopify.com",
        app_install_status="installed",
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)
    return merchant


@pytest.mark.asyncio
async def test_generate_merchant_journeys_empty(session: AsyncSession, merchant: Merchant):
    """If there are no events, no journeys should be created, and any previous should be deleted."""
    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    stmt = select(MerchantJourney).where(MerchantJourney.merchant_id == merchant.merchant_id)
    res = await session.execute(stmt)
    journeys = res.scalars().all()
    assert len(journeys) == 0


@pytest.mark.asyncio
async def test_generate_merchant_journeys_lifecycle_boundaries_and_reinstall(
    session: AsyncSession, merchant: Merchant
):
    """
    Test merchant journey lifecycle boundaries:
    - Events before APP_INSTALLED are ignored.
    - APP_INSTALLED starts a journey (status=OPEN).
    - Merchant and Campaign events during install are sequenced and recorded.
    - APP_UNINSTALLED closes the journey (status=COMPLETED).
    - Events after APP_UNINSTALLED are ignored.
    - Subsequent APP_INSTALLED begins a new journey.
    """
    base_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    campaign_id = uuid.uuid4()

    # Event 0: Pre-install event (should NOT start a journey)
    pre_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.MERCHANT_CREATED.value,
        event_version=1,
        event_timestamp=base_time - timedelta(days=1),
        payload={"merchant_name": merchant.merchant_name},
        source="shopify",
        processed=True,
    )

    # Journey 1 Events:
    install_event_1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={"install_channel": "shopify_app_store"},
        source="shopify",
        processed=True,
    )
    sub_event_1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.SUBSCRIPTION_STARTED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=1),
        payload={"plan_key": "growth"},
        source="billing",
        processed=True,
    )
    campaign_event_1 = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        campaign_id=campaign_id,
        event_type=CampaignEventType.CAMPAIGN_CREATED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=2),
        payload={"name": "Welcome Series"},
        source="marketing",
        processed=True,
    )
    feature_event_1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.FEATURE_ENABLED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=3),
        payload={"feature_key": "ai_insights"},
        source="platform",
        processed=True,
    )
    uninstall_event_1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_UNINSTALLED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=10),
        payload={"reason": "too_expensive"},
        source="shopify",
        processed=True,
    )

    # Post-uninstall event before reinstall (should be ignored)
    post_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.MERCHANT_LOGIN.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=15),
        payload={"login_channel": "web"},
        source="auth",
        processed=True,
    )

    # Journey 2 Events (Reinstall):
    install_event_2 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=20),
        payload={"install_channel": "partner"},
        source="shopify",
        processed=True,
    )
    sub_event_2 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.SUBSCRIPTION_STARTED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=20, hours=2),
        payload={"plan_key": "enterprise"},
        source="billing",
        processed=True,
    )

    session.add_all([
        pre_event,
        install_event_1,
        sub_event_1,
        campaign_event_1,
        feature_event_1,
        uninstall_event_1,
        post_event,
        install_event_2,
        sub_event_2,
    ])
    await session.commit()

    # Generate merchant journeys
    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    # Verify Journeys
    stmt = (
        select(MerchantJourney)
        .where(MerchantJourney.merchant_id == merchant.merchant_id)
        .order_by(MerchantJourney.started_at)
    )
    res = await session.execute(stmt)
    journeys = res.scalars().all()
    assert len(journeys) == 2

    # Journey 1 checks
    j1 = journeys[0]
    assert j1.started_at == base_time
    assert j1.ended_at == base_time + timedelta(days=10)
    assert j1.journey_status == "COMPLETED"

    events_stmt = (
        select(MerchantJourneyEvent)
        .where(MerchantJourneyEvent.merchant_journey_id == j1.merchant_journey_id)
        .order_by(MerchantJourneyEvent.sequence_number)
    )
    res = await session.execute(events_stmt)
    j1_events = res.scalars().all()
    assert len(j1_events) == 5

    assert j1_events[0].sequence_number == 1
    assert j1_events[0].event_type == MerchantEventType.APP_INSTALLED.value
    assert j1_events[0].source_event_category == "merchant"
    assert j1_events[0].source_event_id == install_event_1.event_id

    assert j1_events[1].sequence_number == 2
    assert j1_events[1].event_type == MerchantEventType.SUBSCRIPTION_STARTED.value
    assert j1_events[1].source_event_category == "merchant"
    assert j1_events[1].source_event_id == sub_event_1.event_id

    assert j1_events[2].sequence_number == 3
    assert j1_events[2].event_type == CampaignEventType.CAMPAIGN_CREATED.value
    assert j1_events[2].source_event_category == "campaign"
    assert j1_events[2].source_event_id == campaign_event_1.event_id

    assert j1_events[3].sequence_number == 4
    assert j1_events[3].event_type == MerchantEventType.FEATURE_ENABLED.value
    assert j1_events[3].source_event_category == "merchant"
    assert j1_events[3].source_event_id == feature_event_1.event_id

    assert j1_events[4].sequence_number == 5
    assert j1_events[4].event_type == MerchantEventType.APP_UNINSTALLED.value
    assert j1_events[4].source_event_category == "merchant"
    assert j1_events[4].source_event_id == uninstall_event_1.event_id

    # Journey 2 checks (Reinstall, currently OPEN)
    j2 = journeys[1]
    assert j2.started_at == base_time + timedelta(days=20)
    assert j2.ended_at is None
    assert j2.journey_status == "OPEN"

    events_stmt_2 = (
        select(MerchantJourneyEvent)
        .where(MerchantJourneyEvent.merchant_journey_id == j2.merchant_journey_id)
        .order_by(MerchantJourneyEvent.sequence_number)
    )
    res = await session.execute(events_stmt_2)
    j2_events = res.scalars().all()
    assert len(j2_events) == 2

    assert j2_events[0].sequence_number == 1
    assert j2_events[0].event_type == MerchantEventType.APP_INSTALLED.value
    assert j2_events[0].source_event_id == install_event_2.event_id

    assert j2_events[1].sequence_number == 2
    assert j2_events[1].event_type == MerchantEventType.SUBSCRIPTION_STARTED.value
    assert j2_events[1].source_event_id == sub_event_2.event_id


@pytest.mark.asyncio
async def test_generate_merchant_journeys_filters_shopper_campaign_engagement(
    session: AsyncSession, merchant: Merchant
):
    """
    Ensure campaign events are only included when merchant-level (e.g. CAMPAIGN_CREATED, CAMPAIGN_UPDATED).
    Shopper engagement events (EMAIL_OPENED, EMAIL_CLICKED, AD_CLICKED) are NOT included in Merchant Journeys.
    """
    base_time = datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
    campaign_id = uuid.uuid4()

    install_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={"install_channel": "direct"},
        source="shopify",
        processed=True,
    )
    campaign_created = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        campaign_id=campaign_id,
        event_type=CampaignEventType.CAMPAIGN_CREATED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=1),
        payload={"campaign_name": "Test Campaign"},
        source="marketing",
        processed=True,
    )
    campaign_updated = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        campaign_id=campaign_id,
        event_type=CampaignEventType.CAMPAIGN_UPDATED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=2),
        payload={"status": "running"},
        source="marketing",
        processed=True,
    )
    # Shopper-level campaign events that should NOT appear in merchant journey:
    email_opened = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        campaign_id=campaign_id,
        event_type=CampaignEventType.EMAIL_OPENED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=3),
        payload={"shopper_email": "shopper@example.com"},
        source="email_service",
        processed=True,
    )
    email_clicked = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        campaign_id=campaign_id,
        event_type=CampaignEventType.EMAIL_CLICKED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=4),
        payload={"url": "https://example.com/promo"},
        source="email_service",
        processed=True,
    )

    session.add_all([
        install_event,
        campaign_created,
        campaign_updated,
        email_opened,
        email_clicked,
    ])
    await session.commit()

    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    stmt = select(MerchantJourney).where(MerchantJourney.merchant_id == merchant.merchant_id)
    res = await session.execute(stmt)
    journey = res.scalars().one()

    events_stmt = (
        select(MerchantJourneyEvent)
        .where(MerchantJourneyEvent.merchant_journey_id == journey.merchant_journey_id)
        .order_by(MerchantJourneyEvent.sequence_number)
    )
    res = await session.execute(events_stmt)
    events = res.scalars().all()

    # Only APP_INSTALLED, CAMPAIGN_CREATED, and CAMPAIGN_UPDATED should be present
    assert len(events) == 3
    assert [e.event_type for e in events] == [
        MerchantEventType.APP_INSTALLED.value,
        CampaignEventType.CAMPAIGN_CREATED.value,
        CampaignEventType.CAMPAIGN_UPDATED.value,
    ]


@pytest.mark.asyncio
async def test_generate_merchant_journeys_deterministic_ordering_tiebreaker(
    session: AsyncSession, merchant: Merchant
):
    """
    Events with the exact same timestamp should sort deterministically:
    APP_INSTALLED must start the journey (priority 0), other events in the middle (priority 1),
    and APP_UNINSTALLED must close it (priority 2).
    """
    same_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Insert events with identical timestamps
    install_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=same_time,
        payload={"install_channel": "shopify"},
        source="shopify",
        processed=True,
    )
    sub_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.SUBSCRIPTION_STARTED.value,
        event_version=1,
        event_timestamp=same_time,
        payload={"plan": "pro"},
        source="billing",
        processed=True,
    )
    uninstall_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_UNINSTALLED.value,
        event_version=1,
        event_timestamp=same_time,
        payload={"reason": "cancelled"},
        source="shopify",
        processed=True,
    )

    session.add_all([sub_event, uninstall_event, install_event])
    await session.commit()

    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    stmt = select(MerchantJourney).where(MerchantJourney.merchant_id == merchant.merchant_id)
    res = await session.execute(stmt)
    journey = res.scalars().one()
    assert journey.journey_status == "COMPLETED"

    events_stmt = (
        select(MerchantJourneyEvent)
        .where(MerchantJourneyEvent.merchant_journey_id == journey.merchant_journey_id)
        .order_by(MerchantJourneyEvent.sequence_number)
    )
    res = await session.execute(events_stmt)
    events = res.scalars().all()

    assert len(events) == 3
    assert events[0].event_type == MerchantEventType.APP_INSTALLED.value
    assert events[1].event_type == MerchantEventType.SUBSCRIPTION_STARTED.value
    assert events[2].event_type == MerchantEventType.APP_UNINSTALLED.value


@pytest.mark.asyncio
async def test_generate_merchant_journeys_idempotence(
    session: AsyncSession, merchant: Merchant
):
    """
    Running generation multiple times must be completely idempotent:
    replaces existing journeys and events deterministically without duplicate key violations.
    """
    t = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    event1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=t,
        payload={},
        source="shopify",
        processed=True,
    )
    session.add(event1)
    await session.commit()

    # First generation
    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    stmt = select(MerchantJourney).where(MerchantJourney.merchant_id == merchant.merchant_id)
    journeys_run_1 = (await session.execute(stmt)).scalars().all()
    assert len(journeys_run_1) == 1

    # Second generation (same input)
    await generate_merchant_journeys_for_merchant(session, merchant.merchant_id)
    await session.commit()

    journeys_run_2 = (await session.execute(stmt)).scalars().all()
    assert len(journeys_run_2) == 1
    assert journeys_run_2[0].journey_status == "OPEN"
    assert journeys_run_2[0].started_at == t


@pytest.mark.asyncio
async def test_run_merchant_journey_job_incremental(session: AsyncSession, merchant: Merchant):
    """
    Test that run_merchant_journey_job properly executes incremental processing for eligible merchants
    and advances EntityProcessingState.
    """
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Add qualifying event
    install_event = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        event_type=MerchantEventType.APP_INSTALLED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={},
        source="shopify",
        processed=True,
    )
    session.add(install_event)
    await session.commit()

    # Record domain activity to mark merchant eligible for "merchant_journey"
    await record_domain_activity(session, "merchant", merchant.merchant_id, "merchant", base_time)
    await session.commit()

    # Execute scheduled job
    await run_merchant_journey_job()

    # Verify processing state was recorded
    state_stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_type == "merchant",
        EntityProcessingState.entity_id == merchant.merchant_id,
        EntityProcessingState.target_type == "merchant_journey",
    )
    res = await session.execute(state_stmt)
    state = res.scalar_one_or_none()
    assert state is not None
    assert state.last_generation_status == "SUCCESS"
    assert state.last_generated_at is not None

    # Verify merchant journey was created
    journey_stmt = select(MerchantJourney).where(MerchantJourney.merchant_id == merchant.merchant_id)
    res = await session.execute(journey_stmt)
    journey = res.scalar_one_or_none()
    assert journey is not None
    assert journey.journey_status == "OPEN"
