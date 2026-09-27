import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.event import ShopperEvent
from app.models.merchant import Merchant
from app.models.shopper import Shopper


@pytest.fixture
async def db_session():
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
async def merchant(db_session):
    merch = Merchant(
        merchant_name="Test Merchant",
        email="merchant@test.com",
        shopify_store_id=f"test-store-{uuid.uuid4()}",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    db_session.add(merch)
    await db_session.commit()
    return merch


@pytest.mark.asyncio
async def test_shopper_multiple_anonymous(db_session, merchant):
    # Should allow multiple shoppers with null email for the same merchant
    anon1 = Shopper(merchant_id=merchant.merchant_id, email=None)
    anon2 = Shopper(merchant_id=merchant.merchant_id, email=None)

    db_session.add(anon1)
    db_session.add(anon2)
    await db_session.commit()

    assert anon1.shopper_id is not None
    assert anon2.shopper_id is not None
    assert anon1.shopper_id != anon2.shopper_id


@pytest.mark.asyncio
async def test_shopper_unique_email(db_session, merchant):
    # Should enforce uniqueness for non-null emails for a merchant
    identified1 = Shopper(merchant_id=merchant.merchant_id, email="test@example.com")
    db_session.add(identified1)
    await db_session.commit()

    identified2 = Shopper(merchant_id=merchant.merchant_id, email="test@example.com")
    db_session.add(identified2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
        
    await db_session.rollback()


@pytest.mark.asyncio
async def test_shopper_event_session_id_schema(db_session, merchant):
    shopper = Shopper(merchant_id=merchant.merchant_id, email=None)
    db_session.add(shopper)
    await db_session.commit()

    event = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant.merchant_id,
        shopper_id=shopper.shopper_id,
        session_id=uuid.uuid4(),
        event_type="SESSION_STARTED",
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        payload={"referrer": None},
        source="test",
    )
    db_session.add(event)
    await db_session.commit()

    # Query using session_id
    stmt = text("SELECT session_id FROM shopper_events WHERE event_id = :id")
    result = await db_session.execute(stmt, {"id": event.event_id})
    row = result.fetchone()
    assert row is not None
    assert row[0] == event.session_id
