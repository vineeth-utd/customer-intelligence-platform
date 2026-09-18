"""Integration test against a live local Postgres for merchant event persistence.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable, mirroring the local-infrastructure-dependent tests
under tests/kafka/.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.data_access.merchant_events import get_merchant_event, insert_merchant_event, mark_merchant_event_processed
from app.db.session import AsyncSessionLocal, engine
from app.models.event import MerchantEvent
from app.models.merchant import Merchant
from app.schemas.events.envelope import MerchantEventEnvelope
from app.schemas.events.event_types import MerchantEventType


@pytest.fixture
async def db_session():
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first so a stale
    # connection bound to a previous test's loop is never reused here.
    await engine.dispose()

    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable at {settings.postgres_host}:{settings.postgres_port}: {exc}")
    yield session
    await session.close()


@pytest.fixture
async def merchant(db_session: AsyncSession):
    merchant_row = Merchant(
        merchant_id=uuid.uuid4(),
        shopify_store_id=f"store-{uuid.uuid4().hex[:8]}",
        merchant_name="Test Merchant",
        email="test-merchant@example.com",
        country="US",
        timezone="America/New_York",
        app_install_status="installed",
    )
    db_session.add(merchant_row)
    await db_session.commit()
    yield merchant_row
    await db_session.execute(delete(MerchantEvent).where(MerchantEvent.merchant_id == merchant_row.merchant_id))
    await db_session.execute(delete(Merchant).where(Merchant.merchant_id == merchant_row.merchant_id))
    await db_session.commit()


def _envelope(merchant_id: uuid.UUID, event_id: uuid.UUID | None = None) -> MerchantEventEnvelope:
    return MerchantEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=MerchantEventType.MERCHANT_LOGIN,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        payload={"login_channel": "admin_dashboard"},
        source="test",
    )


async def test_insert_merchant_event_persists_with_initial_processing_state(db_session, merchant):
    envelope = _envelope(merchant.merchant_id)

    inserted = await insert_merchant_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(MerchantEvent, envelope.event_id)
    assert row is not None
    assert row.processed is False
    assert row.processed_at is None
    assert row.event_type == MerchantEventType.MERCHANT_LOGIN.value
    assert row.payload == envelope.payload


async def test_insert_merchant_event_is_idempotent_on_duplicate_event_id(db_session, merchant):
    envelope = _envelope(merchant.merchant_id)

    first = await insert_merchant_event(db_session, envelope)
    second = await insert_merchant_event(db_session, envelope)

    assert first is True
    assert second is False
    count = await db_session.scalar(
        select(func.count()).select_from(MerchantEvent).where(MerchantEvent.event_id == envelope.event_id)
    )
    assert count == 1


async def test_get_merchant_event_returns_none_for_unknown_event_id(db_session):
    assert await get_merchant_event(db_session, uuid.uuid4()) is None


async def test_mark_merchant_event_processed_sets_processed_state(db_session, merchant):
    envelope = _envelope(merchant.merchant_id)
    await insert_merchant_event(db_session, envelope)
    processed_at = datetime.now(timezone.utc)

    await mark_merchant_event_processed(db_session, envelope.event_id, processed_at)
    await db_session.commit()

    row = await get_merchant_event(db_session, envelope.event_id)
    assert row.processed is True
    assert row.processed_at is not None


async def test_mark_merchant_event_processed_is_idempotent(db_session, merchant):
    envelope = _envelope(merchant.merchant_id)
    await insert_merchant_event(db_session, envelope)

    await mark_merchant_event_processed(db_session, envelope.event_id, datetime.now(timezone.utc))
    await mark_merchant_event_processed(db_session, envelope.event_id, datetime.now(timezone.utc))
    await db_session.commit()

    row = await get_merchant_event(db_session, envelope.event_id)
    assert row.processed is True
