"""Integration test against a live local Postgres for shopper event persistence.

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
from app.data_access.shopper_events import get_shopper_event, insert_shopper_event
from app.db.session import AsyncSessionLocal, engine
from app.models.event import ShopperEvent
from app.schemas.events.envelope import ShopperEventEnvelope
from app.schemas.events.event_types import ShopperEventType


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
async def shopper_ref(db_session: AsyncSession):
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    yield merchant_id, shopper_id
    await db_session.execute(delete(ShopperEvent).where(ShopperEvent.shopper_id == shopper_id))
    await db_session.commit()


def _envelope(
    merchant_id: uuid.UUID, shopper_id: uuid.UUID, event_id: uuid.UUID | None = None
) -> ShopperEventEnvelope:
    return ShopperEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=ShopperEventType.SESSION_STARTED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        payload={"referrer": None, "email": None},
        source="test",
    )


async def test_insert_shopper_event_persists_with_initial_processing_state(db_session, shopper_ref):
    merchant_id, shopper_id = shopper_ref
    envelope = _envelope(merchant_id, shopper_id)

    inserted = await insert_shopper_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(ShopperEvent, envelope.event_id)
    assert row is not None
    assert row.processed is False
    assert row.processed_at is None
    assert row.event_type == ShopperEventType.SESSION_STARTED.value
    assert row.payload == envelope.payload
    assert row.session_id == envelope.session_id


async def test_insert_shopper_event_is_idempotent_on_duplicate_event_id(db_session, shopper_ref):
    merchant_id, shopper_id = shopper_ref
    envelope = _envelope(merchant_id, shopper_id)

    first = await insert_shopper_event(db_session, envelope)
    second = await insert_shopper_event(db_session, envelope)

    assert first is True
    assert second is False
    count = await db_session.scalar(
        select(func.count()).select_from(ShopperEvent).where(ShopperEvent.event_id == envelope.event_id)
    )
    assert count == 1


async def test_get_shopper_event_returns_none_for_unknown_event_id(db_session):
    assert await get_shopper_event(db_session, uuid.uuid4()) is None

