import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.data_access.journey import get_qualifying_events_for_shopper
from app.models.merchant import Merchant
from app.models.shopper import Shopper
from app.models.event import ShopperEvent, CampaignEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.order import Order
from app.schemas.events.event_types import ShopperEventType, CampaignEventType
from app.services.journey import (
    generate_shopper_journey_event_id,
    generate_shopper_journey_id,
    generate_shopper_journeys_for_shopper,
)


@pytest.fixture
async def session(db_session):
    yield db_session


@pytest.fixture
async def merchant(session: AsyncSession) -> Merchant:
    merchant = Merchant(
        merchant_name="Test Merchant for Journey",
        email="journey@test.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        shopify_store_id=f"journey-{uuid.uuid4().hex[:8]}.myshopify.com",
        app_install_status="installed",
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)
    return merchant


@pytest.fixture
async def shopper(session: AsyncSession, merchant: Merchant) -> Shopper:
    shopper = Shopper(merchant_id=merchant.merchant_id, email="shopper_journey@test.com")
    session.add(shopper)
    await session.commit()
    await session.refresh(shopper)
    return shopper


@pytest.mark.asyncio
async def test_generate_shopper_journeys_empty(session: AsyncSession, shopper: Shopper):
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    stmt = select(ShopperJourney).where(ShopperJourney.shopper_id == shopper.shopper_id)
    res = await session.execute(stmt)
    assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_generate_shopper_journeys_window_and_conversion(session: AsyncSession, merchant: Merchant, shopper: Shopper):
    base_time = datetime.now(timezone.utc) - timedelta(days=10)

    # Journey 1: Open, but reaches 7-day window.
    # Event 1: Campaign click with UTM
    c_event1 = CampaignEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        campaign_id=uuid.uuid4(),
        event_type=CampaignEventType.EMAIL_CLICKED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={"url": "http://test.com/?utm_source=newsletter"},
        source="test"
    )
    # Event 2: Some product view 2 days later
    s_event1 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=2),
        payload={},
        source="test"
    )
    # Event 3: 8 days later (exceeds 7-day window from base_time). Starts Journey 2.
    # It converts.
    s_event2 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8),
        payload={"referrer": "http://google.com"},
        source="test"
    )
    
    order_id = uuid.uuid4()
    order = Order(
        order_id=order_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=50.0,
        placed_at=base_time + timedelta(days=8, hours=1),
    )

    s_event3 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8, hours=1),
        payload={"order_id": str(order_id)},
        source="test"
    )

    # Event 4: 1 hour after conversion. Starts Journey 3.
    s_event4 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8, hours=2),
        payload={},
        source="test"
    )

    session.add_all([c_event1, s_event1, s_event2, order, s_event3, s_event4])
    await session.commit()

    # Generate journeys
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    stmt = select(ShopperJourney).where(ShopperJourney.shopper_id == shopper.shopper_id).order_by(ShopperJourney.started_at)
    res = await session.execute(stmt)
    journeys = res.scalars().all()

    assert len(journeys) == 3

    # Journey 1: non-converting
    j1 = journeys[0]
    assert j1.journey_status == "NON_CONVERTING"
    assert j1.converted is False
    assert j1.entry_source == "newsletter"
    assert j1.ended_at == s_event1.event_timestamp

    # Journey 2: converted
    j2 = journeys[1]
    assert j2.journey_status == "CONVERTED"
    assert j2.converted is True
    assert j2.order_id == order_id
    assert j2.entry_source == "google.com"
    assert j2.started_at == s_event2.event_timestamp
    assert j2.ended_at == s_event3.event_timestamp

    # Journey 3: open
    j3 = journeys[2]
    assert j3.journey_status == "OPEN"
    assert j3.converted is False
    assert j3.entry_source == "direct"
    assert j3.started_at == s_event4.event_timestamp
    assert j3.ended_at is None


@pytest.mark.asyncio
async def test_generate_shopper_journeys_stable_deterministic_identity(
    session: AsyncSession, merchant: Merchant, shopper: Shopper
):
    base_time = datetime.now(timezone.utc) - timedelta(days=12)

    # Journey 1 opening event (campaign click)
    c1_id = uuid.uuid4()
    c1 = CampaignEvent(
        event_id=c1_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        campaign_id=uuid.uuid4(),
        event_type=CampaignEventType.EMAIL_CLICKED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={"url": "https://test.com/?utm_source=promo"},
        source="test",
    )
    # Journey 1 second event
    s1_id = uuid.uuid4()
    s1 = ShopperEvent(
        event_id=s1_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=2),
        payload={},
        source="test",
    )

    # Journey 2 opening event (8 days later, starts new journey)
    s2_id = uuid.uuid4()
    s2 = ShopperEvent(
        event_id=s2_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8),
        payload={"referrer": "https://bing.com"},
        source="test",
    )
    order_id = uuid.uuid4()
    order = Order(
        order_id=order_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=99.99,
        placed_at=base_time + timedelta(days=8, hours=1),
    )
    s3_id = uuid.uuid4()
    s3 = ShopperEvent(
        event_id=s3_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8, hours=1),
        payload={"order_id": str(order_id)},
        source="test",
    )

    # Journey 3 opening event (starts after purchase)
    s4_id = uuid.uuid4()
    s4 = ShopperEvent(
        event_id=s4_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(days=8, hours=3),
        payload={},
        source="test",
    )

    session.add_all([c1, s1, s2, order, s3, s4])
    await session.commit()

    # Pass 1: Initial generation
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    stmt = (
        select(ShopperJourney)
        .where(ShopperJourney.shopper_id == shopper.shopper_id)
        .options(selectinload(ShopperJourney.events))
        .order_by(ShopperJourney.started_at.asc())
    )
    res = await session.execute(stmt)
    journeys_pass1 = res.scalars().all()

    assert len(journeys_pass1) == 3

    # Verify formula-based deterministic IDs on Pass 1
    expected_j1_id = generate_shopper_journey_id(shopper.shopper_id, "campaign", c1_id)
    expected_j2_id = generate_shopper_journey_id(shopper.shopper_id, "shopper", s2_id)
    expected_j3_id = generate_shopper_journey_id(shopper.shopper_id, "shopper", s4_id)

    assert journeys_pass1[0].journey_id == expected_j1_id
    assert journeys_pass1[1].journey_id == expected_j2_id
    assert journeys_pass1[2].journey_id == expected_j3_id

    # Verify deterministic journey event IDs on Pass 1
    j1_events = sorted(journeys_pass1[0].events, key=lambda e: e.sequence_number)
    assert j1_events[0].journey_event_id == generate_shopper_journey_event_id(expected_j1_id, "campaign", c1_id)
    assert j1_events[1].journey_event_id == generate_shopper_journey_event_id(expected_j1_id, "shopper", s1_id)

    j2_events = sorted(journeys_pass1[1].events, key=lambda e: e.sequence_number)
    assert j2_events[0].journey_event_id == generate_shopper_journey_event_id(expected_j2_id, "shopper", s2_id)
    assert j2_events[1].journey_event_id == generate_shopper_journey_event_id(expected_j2_id, "shopper", s3_id)

    j3_events = sorted(journeys_pass1[2].events, key=lambda e: e.sequence_number)
    assert j3_events[0].journey_event_id == generate_shopper_journey_event_id(expected_j3_id, "shopper", s4_id)

    # Snapshot all attributes from Pass 1
    snapshot_pass1 = [
        (
            j.journey_id,
            j.journey_status,
            j.converted,
            j.entry_source,
            j.order_id,
            j.started_at,
            j.ended_at,
            [(e.journey_event_id, e.source_event_category, e.source_event_id, e.sequence_number) for e in sorted(j.events, key=lambda x: x.sequence_number)],
        )
        for j in journeys_pass1
    ]

    # Pass 2: Regeneration (simulate re-running incremental generation against identical source data)
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    res = await session.execute(stmt)
    journeys_pass2 = res.scalars().all()

    snapshot_pass2 = [
        (
            j.journey_id,
            j.journey_status,
            j.converted,
            j.entry_source,
            j.order_id,
            j.started_at,
            j.ended_at,
            [(e.journey_event_id, e.source_event_category, e.source_event_id, e.sequence_number) for e in sorted(j.events, key=lambda x: x.sequence_number)],
        )
        for j in journeys_pass2
    ]

    # Every single journey ID, event ID, sequence, status, and attribute must be identical!
    assert snapshot_pass2 == snapshot_pass1

    # Pass 3: Re-verify on third generation
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    res = await session.execute(stmt)
    journeys_pass3 = res.scalars().all()

    snapshot_pass3 = [
        (
            j.journey_id,
            j.journey_status,
            j.converted,
            j.entry_source,
            j.order_id,
            j.started_at,
            j.ended_at,
            [(e.journey_event_id, e.source_event_category, e.source_event_id, e.sequence_number) for e in sorted(j.events, key=lambda x: x.sequence_number)],
        )
        for j in journeys_pass3
    ]
    assert snapshot_pass3 == snapshot_pass1


@pytest.mark.asyncio
async def test_shopper_journey_identity_stability_as_events_accumulate(
    session: AsyncSession, merchant: Merchant, shopper: Shopper
):
    """
    Verify that an open journey preserves its stable journey_id as new events
    accumulate and as it eventually converts.
    """
    base_time = datetime.now(timezone.utc) - timedelta(days=2)

    # Step 1: Opening event (Session started)
    e1_id = uuid.uuid4()
    e1 = ShopperEvent(
        event_id=e1_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=base_time,
        payload={"referrer": "https://google.com"},
        source="test",
    )
    session.add(e1)
    await session.commit()

    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    stmt = (
        select(ShopperJourney)
        .where(ShopperJourney.shopper_id == shopper.shopper_id)
        .options(selectinload(ShopperJourney.events))
    )
    res = await session.execute(stmt)
    journeys_step1 = res.scalars().all()
    assert len(journeys_step1) == 1
    j_step1 = journeys_step1[0]
    expected_journey_id = generate_shopper_journey_id(shopper.shopper_id, "shopper", e1_id)
    assert j_step1.journey_id == expected_journey_id
    assert j_step1.journey_status == "OPEN"
    assert len(j_step1.events) == 1
    e1_journey_event_id = j_step1.events[0].journey_event_id

    # Step 2: Add browse event 1 hour later (journey remains OPEN)
    e2_id = uuid.uuid4()
    e2 = ShopperEvent(
        event_id=e2_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=1),
        payload={},
        source="test",
    )
    session.add(e2)
    await session.commit()

    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    res = await session.execute(stmt)
    journeys_step2 = res.scalars().all()
    assert len(journeys_step2) == 1
    j_step2 = journeys_step2[0]

    # Journey ID must remain identical!
    assert j_step2.journey_id == expected_journey_id
    assert j_step2.journey_status == "OPEN"
    assert len(j_step2.events) == 2
    events_by_seq = {e.sequence_number: e for e in j_step2.events}
    # First event's journey_event_id must also remain identical!
    assert events_by_seq[1].journey_event_id == e1_journey_event_id
    assert events_by_seq[2].journey_event_id == generate_shopper_journey_event_id(expected_journey_id, "shopper", e2_id)

    # Step 3: Add purchase event 2 hours later (journey transitions to CONVERTED)
    order_id = uuid.uuid4()
    order = Order(
        order_id=order_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=150.0,
        placed_at=base_time + timedelta(hours=2),
    )
    e3_id = uuid.uuid4()
    e3 = ShopperEvent(
        event_id=e3_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PURCHASE_COMPLETED.value,
        event_version=1,
        event_timestamp=base_time + timedelta(hours=2),
        payload={"order_id": str(order_id)},
        source="test",
    )
    session.add_all([order, e3])
    await session.commit()

    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    res = await session.execute(stmt)
    journeys_step3 = res.scalars().all()
    assert len(journeys_step3) == 1
    j_step3 = journeys_step3[0]

    # Journey ID must still be identical even after converting!
    assert j_step3.journey_id == expected_journey_id
    assert j_step3.journey_status == "CONVERTED"
    assert j_step3.converted is True
    assert j_step3.order_id == order_id
    assert len(j_step3.events) == 3

    events_by_seq3 = {e.sequence_number: e for e in j_step3.events}
    assert events_by_seq3[1].journey_event_id == e1_journey_event_id
    assert events_by_seq3[2].journey_event_id == generate_shopper_journey_event_id(expected_journey_id, "shopper", e2_id)
    assert events_by_seq3[3].journey_event_id == generate_shopper_journey_event_id(expected_journey_id, "shopper", e3_id)


@pytest.mark.asyncio
async def test_deterministic_ordering_tiebreaker_with_identical_timestamps(
    session: AsyncSession, merchant: Merchant, shopper: Shopper
):
    """
    Verify that when events have identical timestamps, qualifying events are sorted
    deterministically by (event_timestamp, source_event_category, source_event_id).
    """
    shared_ts = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Generate fresh UUIDs sorted to ensure s_id_1 < s_id_2
    u1, u2 = sorted([uuid.uuid4(), uuid.uuid4()])
    s_id_1, s_id_2 = u1, u2
    c_id = uuid.uuid4()

    c_event = CampaignEvent(
        event_id=c_id,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        campaign_id=uuid.uuid4(),
        event_type=CampaignEventType.EMAIL_OPENED.value,
        event_version=1,
        event_timestamp=shared_ts,
        payload={},
        source="test",
    )
    s_event_2 = ShopperEvent(
        event_id=s_id_2,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.PRODUCT_VIEWED.value,
        event_version=1,
        event_timestamp=shared_ts,
        payload={},
        source="test",
    )
    s_event_1 = ShopperEvent(
        event_id=s_id_1,
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED.value,
        event_version=1,
        event_timestamp=shared_ts,
        payload={"referrer": "https://google.com"},
        source="test",
    )

    session.add_all([c_event, s_event_2, s_event_1])
    await session.commit()

    # Query qualifying events directly
    qualifying = await get_qualifying_events_for_shopper(session, shopper.shopper_id)
    assert len(qualifying) == 3

    # Tiebreaker:
    # 1. source_event_category: "campaign" comes before "shopper" ('c' < 's')
    # 2. for category "shopper": s_id_1 ("1111...") comes before s_id_2 ("2222...")
    assert qualifying[0][0] == "campaign"
    assert qualifying[0][1] == c_id

    assert qualifying[1][0] == "shopper"
    assert qualifying[1][1] == s_id_1

    assert qualifying[2][0] == "shopper"
    assert qualifying[2][1] == s_id_2

    # Now verify journey generation creates deterministic stable IDs based on this total order
    await generate_shopper_journeys_for_shopper(session, shopper.shopper_id)
    await session.commit()

    stmt = (
        select(ShopperJourney)
        .where(ShopperJourney.shopper_id == shopper.shopper_id)
        .options(selectinload(ShopperJourney.events))
    )
    res = await session.execute(stmt)
    journeys = res.scalars().all()
    assert len(journeys) == 1
    # Opening event is the campaign event (first in total order)
    expected_journey_id = generate_shopper_journey_id(shopper.shopper_id, "campaign", c_id)
    assert journeys[0].journey_id == expected_journey_id

    events = sorted(journeys[0].events, key=lambda e: e.sequence_number)
    assert events[0].source_event_id == c_id
    assert events[1].source_event_id == s_id_1
    assert events[2].source_event_id == s_id_2


