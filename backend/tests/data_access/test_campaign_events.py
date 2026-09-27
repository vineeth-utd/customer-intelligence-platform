"""Integration test against a live local Postgres for campaign event persistence.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.data_access.campaign_events import get_campaign_event, insert_campaign_event, mark_campaign_event_processed
from app.db.session import AsyncSessionLocal, engine
from app.models.event import CampaignEvent
from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType


@pytest.fixture
async def db_session():
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
async def campaign_ref(db_session: AsyncSession):
    merchant_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    yield merchant_id, campaign_id
    await db_session.execute(delete(CampaignEvent).where(CampaignEvent.campaign_id == campaign_id))
    await db_session.commit()


def _envelope(
    merchant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    shopper_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> CampaignEventEnvelope:
    return CampaignEventEnvelope(
        event_id=event_id or uuid.uuid4(),
        event_type=CampaignEventType.CAMPAIGN_CREATED,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        merchant_id=merchant_id,
        campaign_id=campaign_id,
        shopper_id=shopper_id,
        payload={
            "campaign_name": "Summer Launch",
            "campaign_type": "promotional",
            "campaign_medium": "email",
            "segment_id": str(uuid.uuid4()),
            "status": "draft",
            "start_at": None,
            "end_at": None,
        },
        source="test",
    )


async def test_insert_campaign_event_persists_with_initial_processing_state(db_session, campaign_ref):
    merchant_id, campaign_id = campaign_ref
    envelope = _envelope(merchant_id, campaign_id)

    inserted = await insert_campaign_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(CampaignEvent, envelope.event_id)
    assert row is not None
    assert row.processed is False
    assert row.processed_at is None
    assert row.event_type == CampaignEventType.CAMPAIGN_CREATED.value
    assert row.payload == envelope.payload
    assert row.source == envelope.source


async def test_insert_campaign_event_with_none_shopper_id_persists_successfully(db_session, campaign_ref):
    merchant_id, campaign_id = campaign_ref
    envelope = _envelope(merchant_id, campaign_id, shopper_id=None)

    inserted = await insert_campaign_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(CampaignEvent, envelope.event_id)
    assert row is not None
    assert row.shopper_id is None


async def test_insert_campaign_event_with_known_shopper_id_persists_successfully(db_session, campaign_ref):
    merchant_id, campaign_id = campaign_ref
    shopper_id = uuid.uuid4()
    envelope = _envelope(merchant_id, campaign_id, shopper_id=shopper_id)

    inserted = await insert_campaign_event(db_session, envelope)

    assert inserted is True
    row = await db_session.get(CampaignEvent, envelope.event_id)
    assert row is not None
    assert row.shopper_id == shopper_id


async def test_insert_campaign_event_is_idempotent_on_duplicate_event_id(db_session, campaign_ref):
    merchant_id, campaign_id = campaign_ref
    envelope = _envelope(merchant_id, campaign_id)

    first = await insert_campaign_event(db_session, envelope)
    second = await insert_campaign_event(db_session, envelope)

    assert first is True
    assert second is False
    count = await db_session.scalar(
        select(func.count()).select_from(CampaignEvent).where(CampaignEvent.event_id == envelope.event_id)
    )
    assert count == 1


async def test_get_campaign_event_returns_none_for_unknown_event_id(db_session):
    assert await get_campaign_event(db_session, uuid.uuid4()) is None


async def test_mark_campaign_event_processed_sets_processed_state(db_session, campaign_ref):
    merchant_id, campaign_id = campaign_ref
    envelope = _envelope(merchant_id, campaign_id)
    await insert_campaign_event(db_session, envelope)
    processed_at = datetime.now(timezone.utc)

    await mark_campaign_event_processed(db_session, envelope.event_id, processed_at)
    await db_session.commit()

    row = await get_campaign_event(db_session, envelope.event_id)
    assert row is not None
    assert row.processed is True
    assert row.processed_at is not None
