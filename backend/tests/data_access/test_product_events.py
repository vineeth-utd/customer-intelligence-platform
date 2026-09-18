"""Integration test against a live local Postgres for product event persistence.

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
from app.data_access.product_events import get_product_event, insert_product_event
from app.db.session import AsyncSessionLocal, engine
from app.models.event import ProductEvent
from app.schemas.events.envelope import ProductEventEnvelope
from app.schemas.events.event_types import ProductEventType


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
async def product_ref(db_session: AsyncSession):
    """A synthetic (merchant_id, product_id) pair.

    No operational Merchant/Product rows are created: product_events.merchant_id
    and product_id are lineage/correlation identifiers, not enforced foreign
    keys, so persistence must succeed independently of the operational rows.
    """
    merchant_id = uuid.uuid4()
    product_id = uuid.uuid4()
    yield merchant_id, product_id
    await db_session.execute(delete(ProductEvent).where(ProductEvent.product_id == product_id))
    await db_session.commit()


def _envelope(
    merchant_id: uuid.UUID, product_id: uuid.UUID, event_id: uuid.UUID | None = None
) -> ProductEventEnvelope:
    return ProductEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=ProductEventType.PRODUCT_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        product_id=product_id,
        payload={"product_name": "Test Product", "category": None, "vendor": None, "status": "active"},
        source="test",
    )


async def test_insert_product_event_persists_with_initial_processing_state(db_session, product_ref):
    merchant_id, product_id = product_ref
    envelope = _envelope(merchant_id, product_id)

    inserted = await insert_product_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(ProductEvent, envelope.event_id)
    assert row is not None
    assert row.processed is False
    assert row.processed_at is None
    assert row.event_type == ProductEventType.PRODUCT_CREATED.value
    assert row.payload == envelope.payload


async def test_insert_product_event_is_idempotent_on_duplicate_event_id(db_session, product_ref):
    merchant_id, product_id = product_ref
    envelope = _envelope(merchant_id, product_id)

    first = await insert_product_event(db_session, envelope)
    second = await insert_product_event(db_session, envelope)

    assert first is True
    assert second is False
    count = await db_session.scalar(
        select(func.count()).select_from(ProductEvent).where(ProductEvent.event_id == envelope.event_id)
    )
    assert count == 1


async def test_get_product_event_returns_none_for_unknown_event_id(db_session):
    assert await get_product_event(db_session, uuid.uuid4()) is None
