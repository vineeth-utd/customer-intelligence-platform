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

    from app.data_access.shopper import upsert_shopper
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
async def test_campaign_analytics_delivered(db_session: AsyncSession, setup_data):
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
    
    envelope = build_envelope(
        CampaignEventType.EMAIL_DELIVERED.value,
        campaign_id,
        setup_data["merchant_id"],
        {}
    )
    await process_campaign_event(db_session, envelope)
    await db_session.commit()

    stmt = select(CampaignAnalyticsDaily).where(CampaignAnalyticsDaily.campaign_id == campaign_id)
    analytics = (await db_session.execute(stmt)).scalar_one()
    assert analytics.delivered_count == 1
    assert analytics.opened_count == 0
    assert analytics.open_rate == 0.0

@pytest.mark.asyncio
async def test_campaign_converted(db_session: AsyncSession, setup_data):
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
            "status": "active",
            "start_at": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        }
    )
    await process_campaign_event(db_session, env_create)
    
    # Create order
    order_id = uuid.uuid4()
    await create_order(
        db_session,
        order_id=order_id,
        merchant_id=setup_data["merchant_id"],
        shopper_id=setup_data["shopper_id"],
        currency="USD",
        total_amount=100.50,
        placed_at=datetime.now(timezone.utc)
    )
    await db_session.commit()

    env_conv = build_envelope(
        CampaignEventType.CAMPAIGN_CONVERTED.value,
        campaign_id,
        setup_data["merchant_id"],
        {"order_id": str(order_id)},
        shopper_id=setup_data["shopper_id"]
    )
    await process_campaign_event(db_session, env_conv)
    await db_session.commit()

    stmt = select(CampaignAnalyticsDaily).where(CampaignAnalyticsDaily.campaign_id == campaign_id)
    analytics = (await db_session.execute(stmt)).scalar_one()
    assert analytics.converted_count == 1
    assert analytics.attributed_order_count == 1
    assert float(analytics.attributed_revenue) == 100.50

