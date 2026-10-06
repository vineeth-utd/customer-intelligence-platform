import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.models.shopper import Shopper
from app.models.event import ShopperEvent, CampaignEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.models.order import Order
from app.schemas.events.event_types import ShopperEventType, CampaignEventType
from app.services.journey import generate_shopper_journeys_for_shopper
from app.config.settings import settings


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

