import pytest
import uuid
from datetime import datetime, timezone, date

from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.campaign import Campaign
from app.models.metrics import CampaignAnalyticsDaily
from app.models.event import CampaignEvent
from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.envelope import CampaignEventEnvelope
from app.services.campaign import (
    process_campaign_event,
    UnresolvedReferenceError,
    UnsupportedConfigurationFieldError,
    AttributionError
)
from app.data_access.merchant import create_merchant
from app.data_access.segment import upsert_merchant_segment
from app.data_access.shopper import upsert_shopper
from app.data_access.order import create_order
from app.reference_data.segments import SegmentCatalogEntry


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
async def setup_data(db_session: AsyncSession):
    merchant_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    shopper_id = uuid.uuid4()

    await create_merchant(
        db_session,
        merchant_id=merchant_id,
        shopify_store_id=f"store-{merchant_id}",
        merchant_name="Test Store",
        email=f"test-{merchant_id}@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed"
    )

    segment_config = SegmentCatalogEntry(
        segment_name="Test Segment",
        segment_definition={}
    )
    segment = await upsert_merchant_segment(db_session, merchant_id, segment_config)
    await db_session.flush() # ensure segment_id is populated
    segment_id = segment.segment_id

    await upsert_shopper(
        db_session,
        shopper_id=shopper_id,
        merchant_id=merchant_id,
        event_timestamp=datetime.now(timezone.utc)
    )
    
    await db_session.commit()
    
    return {
        "merchant_id": merchant_id,
        "segment_id": segment_id,
        "shopper_id": shopper_id,
    }

def build_envelope(event_type: str, campaign_id: uuid.UUID, merchant_id: uuid.UUID, payload: dict, shopper_id: uuid.UUID | None = None) -> CampaignEventEnvelope:
    return CampaignEventEnvelope(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        campaign_id=campaign_id,
        shopper_id=shopper_id,
        event_type=event_type,
        event_version=1,
        event_timestamp=datetime.now(timezone.utc),
        payload=payload,
        source="test"
    )

@pytest.mark.asyncio
async def test_campaign_created(db_session: AsyncSession, setup_data):
    campaign_id = uuid.uuid4()
    envelope = build_envelope(
        CampaignEventType.CAMPAIGN_CREATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {
            "campaign_name": "My Campaign",
            "campaign_type": "email",
            "campaign_medium": "newsletter",
            "segment_id": str(setup_data["segment_id"]),
            "status": "draft",
        }
    )
    await process_campaign_event(db_session, envelope)
    await db_session.commit()

    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    campaign = (await db_session.execute(stmt)).scalar_one()
    assert campaign.campaign_name == "My Campaign"
    assert campaign.status == "draft"



@pytest.mark.asyncio
async def test_campaign_updated_valid_iso_datetime(db_session: AsyncSession, setup_data):
    campaign_id = uuid.uuid4()
    # Create campaign
    env_create = build_envelope(
        CampaignEventType.CAMPAIGN_CREATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {
            "campaign_name": "My Campaign",
            "campaign_type": "email",
            "campaign_medium": "newsletter",
            "segment_id": str(setup_data["segment_id"]),
            "status": "draft",
        }
    )
    await process_campaign_event(db_session, env_create)
    await db_session.commit()

    # Update with valid ISO strings for start_at and end_at
    env_update = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {
            "changed_values": {
                "start_at": "2026-09-21T10:00:00Z",
                "end_at": "2026-10-21T10:00:00+00:00",
                "status": "active"
            }
        }
    )
    await process_campaign_event(db_session, env_update)
    await db_session.commit()

    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    campaign = (await db_session.execute(stmt)).scalar_one()
    assert campaign.status == "active"
    assert campaign.start_at == datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    assert campaign.end_at == datetime(2026, 10, 21, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_campaign_updated_invalid_values(db_session: AsyncSession, setup_data):
    campaign_id = uuid.uuid4()
    # Create campaign
    env_create = build_envelope(
        CampaignEventType.CAMPAIGN_CREATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {
            "campaign_name": "My Campaign",
            "campaign_type": "email",
            "campaign_medium": "newsletter",
            "segment_id": str(setup_data["segment_id"]),
            "status": "draft",
        }
    )
    await process_campaign_event(db_session, env_create)
    await db_session.commit()

    # Test invalid datetime string
    env_update_invalid_dt = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {"changed_values": {"start_at": "not-a-datetime"}}
    )
    with pytest.raises(UnsupportedConfigurationFieldError, match="Invalid datetime format"):
        await process_campaign_event(db_session, env_update_invalid_dt)

    # Test invalid UUID for segment_id
    env_update_invalid_uuid = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {"changed_values": {"segment_id": "not-a-uuid"}}
    )
    with pytest.raises(UnsupportedConfigurationFieldError, match="Invalid UUID for segment_id"):
        await process_campaign_event(db_session, env_update_invalid_uuid)

    # Test None for segment_id
    env_update_none_segment = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {"changed_values": {"segment_id": None}}
    )
    with pytest.raises(UnsupportedConfigurationFieldError, match="segment_id cannot be None"):
        await process_campaign_event(db_session, env_update_none_segment)

    # Test None for start_at and end_at (should pass)
    env_update_none_dates = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED.value,
        campaign_id,
        setup_data["merchant_id"],
        {"changed_values": {"start_at": None, "end_at": None}}
    )
    await process_campaign_event(db_session, env_update_none_dates)
    await db_session.commit()

    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    campaign = (await db_session.execute(stmt)).scalar_one()
    assert campaign.start_at is None
    assert campaign.end_at is None


async def test_campaign_activity_timestamp_is_monotonic(db_session: AsyncSession, setup_data):
    merchant_id = setup_data["merchant_id"]
    campaign_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. Process an event
    env1 = build_envelope(
        CampaignEventType.CAMPAIGN_CREATED, 
        campaign_id, 
        merchant_id, 
        {
            "campaign_name": "Test", 
            "campaign_type": "promotional",
            "campaign_medium": "email",
            "segment_id": str(setup_data["segment_id"]),
            "status": "draft"
        }
    )
    env1.event_timestamp = base_time
    await process_campaign_event(db_session, env1)
    
    # 2. Process an older event
    from datetime import timedelta
    env2 = build_envelope(
        CampaignEventType.CAMPAIGN_UPDATED, 
        campaign_id, 
        merchant_id, 
        {
            "changed_values": {"status": "active"}
        }
    )
    env2.event_timestamp = base_time - timedelta(days=1)
    await process_campaign_event(db_session, env2)
    
    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    campaign = (await db_session.execute(stmt)).scalar_one()
    assert campaign.last_business_activity_at == base_time
