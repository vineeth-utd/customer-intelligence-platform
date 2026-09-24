import uuid
from datetime import datetime, timezone, timedelta, date

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.metrics import (
    MerchantMetricsDaily,
    PlatformMetricsDaily,
    FeatureMetricsDaily,
    CampaignAnalyticsDaily,
)
from app.models.event import MerchantEvent, ShopperEvent, CampaignEvent
from app.models.order import Order
from app.models.merchant import Merchant, SubscriptionPlan
from app.services.analytics import generate_daily_metrics
from app.data_access.merchant import create_merchant
from app.data_access.shopper import upsert_shopper
from app.data_access.segment import upsert_merchant_segment
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


@pytest.mark.asyncio
async def test_generate_daily_metrics_idempotent(db_session: AsyncSession):
    metric_date = date(2025, 2, 1)
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    campaign_id = uuid.uuid4()
    order_id = uuid.uuid4()
    await db_session.execute(text("TRUNCATE TABLE merchants CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE platform_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE merchant_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE shopper_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE campaign_events CASCADE"))
    await db_session.commit()
    
    # 1. Setup Merchant
    await create_merchant(
        db_session,
        merchant_id=merchant_id,
        shopify_store_id=f"store-{merchant_id}",
        merchant_name="Analytics Store",
        email=f"analytics-{merchant_id}@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    
    # 2. Setup Shopper
    await upsert_shopper(
        db_session,
        shopper_id=shopper_id,
        merchant_id=merchant_id,
        event_timestamp=datetime(2025, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    # Manually override created_at for the test since upsert_shopper doesn't let us pass it
    from sqlalchemy import update
    from app.models.shopper import Shopper
    await db_session.execute(update(Shopper).where(Shopper.shopper_id == shopper_id).values(created_at=datetime(2025, 2, 1, 10, 0, 0, tzinfo=timezone.utc)))

    segment_id = uuid.uuid4()
    await upsert_merchant_segment(
        db_session, 
        merchant_id, 
        SegmentCatalogEntry(segment_name="Test Segment", segment_definition={})
    )
    await db_session.flush() # ensure it exists
    
    # get the actual segment created, though upsert_merchant_segment handles merchant segment creation based on config
    # wait, upsert_merchant_segment might assign a new UUID. Let's capture it.
    segment = await upsert_merchant_segment(
        db_session, 
        merchant_id, 
        SegmentCatalogEntry(segment_name="Test Segment", segment_definition={})
    )
    await db_session.flush()

    from app.models.campaign import Campaign
    campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        segment_id=segment.segment_id,
        campaign_name="Test Campaign",
        campaign_type="email",
        campaign_medium="newsletter",
        status="active"
    )
    db_session.add(campaign)

    # 3. Setup Order
    order = Order(
        order_id=order_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        order_status="completed",
        currency="USD",
        total_amount=150.00,
        placed_at=datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    db_session.add(order)
    
    # 4. Setup Events
    me1 = MerchantEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        event_type="APP_INSTALLED",
        event_version=1,
        event_timestamp=datetime(2025, 2, 1, 9, 0, 0, tzinfo=timezone.utc),
        payload={},
        source="test"
    )
    db_session.add(me1)
    
    se1 = ShopperEvent(
        event_id=uuid.uuid4(),
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        session_id=uuid.uuid4(),
        event_type="PURCHASE_COMPLETED",
        event_version=1,
        event_timestamp=datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc),
        payload={},
        source="test"
    )
    db_session.add(se1)
    
    ce1 = CampaignEvent(
        event_id=uuid.uuid4(),
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        event_type="EMAIL_DELIVERED",
        event_version=1,
        event_timestamp=datetime(2025, 2, 1, 11, 0, 0, tzinfo=timezone.utc),
        payload={},
        source="test"
    )
    db_session.add(ce1)
    
    await db_session.commit()

    # Generate metrics
    await generate_daily_metrics(db_session, metric_date)
    await db_session.commit()
    
    # Verify MerchantMetricsDaily
    stmt = select(MerchantMetricsDaily).where(MerchantMetricsDaily.merchant_id == merchant_id, MerchantMetricsDaily.metric_date == metric_date)
    mm = (await db_session.execute(stmt)).scalar_one_or_none()
    assert mm is not None
    assert float(mm.revenue) == 150.00
    assert mm.order_count == 1
    assert mm.new_shoppers == 1
    assert mm.purchase_count == 1
    
    # Verify PlatformMetricsDaily
    stmt = select(PlatformMetricsDaily).where(PlatformMetricsDaily.metric_date == metric_date)
    pm = (await db_session.execute(stmt)).scalar_one_or_none()
    assert pm is not None
    assert pm.active_merchants >= 1
    
    # Verify CampaignAnalyticsDaily
    stmt = select(CampaignAnalyticsDaily).where(CampaignAnalyticsDaily.campaign_id == campaign_id, CampaignAnalyticsDaily.metric_date == metric_date)
    cm = (await db_session.execute(stmt)).scalar_one_or_none()
    assert cm is not None
    assert cm.delivered_count == 1

    # Rerun to test idempotency
    await generate_daily_metrics(db_session, metric_date)
    await db_session.commit()
    
    stmt = select(MerchantMetricsDaily).where(MerchantMetricsDaily.merchant_id == merchant_id, MerchantMetricsDaily.metric_date == metric_date)
    mm2 = (await db_session.execute(stmt)).scalar_one()
    assert float(mm2.revenue) == 150.00
    assert mm2.order_count == 1
