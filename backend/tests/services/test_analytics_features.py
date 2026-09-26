import uuid
from datetime import datetime, timezone, date

import pytest
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.event import MerchantEvent, ShopperEvent
from app.models.metrics import FeatureMetricsDaily
from app.data_access.merchant import create_merchant
from app.services.merchant import initialize_reference_data
from app.services.analytics import generate_daily_metrics

@pytest.fixture
async def db_session():
    await engine.dispose()
    session = AsyncSessionLocal()
    yield session
    await session.close()

@pytest.mark.asyncio
async def test_feature_metrics_daily_with_subscription_changes(db_session: AsyncSession):
    metric_date = date(2025, 3, 1)
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    
    await db_session.execute(text("TRUNCATE TABLE merchants CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE merchant_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE shopper_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE feature_metrics_daily CASCADE"))
    await db_session.commit()
    
    await initialize_reference_data(db_session)
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
    
    # 2. Events: install, start PRO, enable recommendations, then UPGRADE to PREMIUM, then shopper interacts with recommendations
    # PRO has recommendations, PREMIUM has recommendations.
    events = [
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="APP_INSTALLED",
            event_version=1, event_timestamp=datetime(2025, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
            payload={"install_channel": "shopify"}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="SUBSCRIPTION_STARTED",
            event_version=1, event_timestamp=datetime(2025, 3, 1, 9, 5, 0, tzinfo=timezone.utc),
            payload={"plan_key": "pro", "billing_cycle": "monthly", "amount_paid": 49}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="FEATURE_ENABLED",
            event_version=1, event_timestamp=datetime(2025, 3, 1, 9, 10, 0, tzinfo=timezone.utc),
            payload={"feature_key": "recommendations"}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="SUBSCRIPTION_UPGRADED",
            event_version=1, event_timestamp=datetime(2025, 3, 1, 9, 15, 0, tzinfo=timezone.utc),
            payload={"previous_plan_key": "pro", "new_plan_key": "premium", "billing_cycle": "monthly", "amount_paid": 99}, source="test"
        )
    ]
    db_session.add_all(events)
    
    se = ShopperEvent(
        event_id=uuid.uuid4(), merchant_id=merchant_id, shopper_id=shopper_id, session_id=uuid.uuid4(),
        event_type="RECOMMENDATION_VIEWED", event_version=1,
        event_timestamp=datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        payload={"product_id": str(uuid.uuid4()), "variant_id": str(uuid.uuid4())}, source="test"
    )
    db_session.add(se)
    await db_session.commit()

    # 3. Generate metrics
    await generate_daily_metrics(db_session, metric_date)
    await db_session.commit()
    
    # 4. Check feature metrics for recommendations
    res = await db_session.execute(text("SELECT feature_id FROM platform_features WHERE feature_key = 'recommendations'"))
    rec_feature_id = res.scalar_one()
    
    stmt = select(FeatureMetricsDaily).where(
        FeatureMetricsDaily.feature_id == rec_feature_id,
        FeatureMetricsDaily.metric_date == metric_date
    )
    fmd = (await db_session.execute(stmt)).scalar_one_or_none()
    
    assert fmd is not None
    assert fmd.eligible_merchant_count == 1
    assert fmd.enabled_merchant_count == 1
    assert fmd.active_merchant_count == 1
    assert fmd.feature_event_count == 1

@pytest.mark.asyncio
async def test_feature_metrics_daily_with_subscription_downgrade(db_session: AsyncSession):
    metric_date = date(2025, 4, 1)
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    
    await db_session.execute(text("TRUNCATE TABLE merchants CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE merchant_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE shopper_events CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE feature_metrics_daily CASCADE"))
    await db_session.commit()
    
    await initialize_reference_data(db_session)
    await db_session.commit()

    # 1. Setup Merchant
    await create_merchant(
        db_session,
        merchant_id=merchant_id,
        shopify_store_id=f"store-{merchant_id}",
        merchant_name="Analytics Store Downgrade",
        email=f"analytics-downgrade-{merchant_id}@store.com",
        country="US",
        timezone="UTC",
        store_currency="USD",
        app_install_status="installed",
    )
    
    # 2. Events: install, start PREMIUM, enable wishlist, then DOWNGRADE to FREE, then shopper interacts with wishlist
    # PREMIUM has wishlist, FREE has wishlist.
    events = [
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="APP_INSTALLED",
            event_version=1, event_timestamp=datetime(2025, 4, 1, 9, 0, 0, tzinfo=timezone.utc),
            payload={"install_channel": "shopify"}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="SUBSCRIPTION_STARTED",
            event_version=1, event_timestamp=datetime(2025, 4, 1, 9, 5, 0, tzinfo=timezone.utc),
            payload={"plan_key": "premium", "billing_cycle": "monthly", "amount_paid": 99}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="FEATURE_ENABLED",
            event_version=1, event_timestamp=datetime(2025, 4, 1, 9, 10, 0, tzinfo=timezone.utc),
            payload={"feature_key": "wishlist"}, source="test"
        ),
        MerchantEvent(
            event_id=uuid.uuid4(), merchant_id=merchant_id, event_type="SUBSCRIPTION_DOWNGRADED",
            event_version=1, event_timestamp=datetime(2025, 4, 1, 9, 15, 0, tzinfo=timezone.utc),
            payload={"previous_plan_key": "premium", "new_plan_key": "free", "billing_cycle": "monthly", "amount_paid": 0}, source="test"
        )
    ]
    db_session.add_all(events)
    
    se = ShopperEvent(
        event_id=uuid.uuid4(), merchant_id=merchant_id, shopper_id=shopper_id, session_id=uuid.uuid4(),
        event_type="WISHLIST_ADDED", event_version=1,
        event_timestamp=datetime(2025, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        payload={"product_id": str(uuid.uuid4()), "variant_id": str(uuid.uuid4())}, source="test"
    )
    db_session.add(se)
    await db_session.commit()

    # 3. Generate metrics
    await generate_daily_metrics(db_session, metric_date)
    await db_session.commit()
    
    # 4. Check feature metrics for wishlist
    res = await db_session.execute(text("SELECT feature_id FROM platform_features WHERE feature_key = 'wishlist'"))
    wishlist_feature_id = res.scalar_one()
    
    stmt = select(FeatureMetricsDaily).where(
        FeatureMetricsDaily.feature_id == wishlist_feature_id,
        FeatureMetricsDaily.metric_date == metric_date
    )
    fmd = (await db_session.execute(stmt)).scalar_one_or_none()
    
    assert fmd is not None
    assert fmd.eligible_merchant_count == 1
    assert fmd.enabled_merchant_count == 1
    assert fmd.active_merchant_count == 1
    assert fmd.feature_event_count == 1

