import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics import (
    get_platform_summary,
    get_platform_metrics_trend,
    get_feature_metrics_summary,
    get_merchant_metrics_summary,
    get_merchant_metrics_trend,
    get_campaign_analytics_for_merchant,
    refresh_aggregate_views,
    generate_daily_metrics
)
from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine

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

@pytest.mark.asyncio
async def test_analytics_read_capabilities(db_session: AsyncSession):
    # Setup base testing data
    merchant_id = uuid.uuid4()
    metric_date = date(2025, 3, 1)

    # Note: We rely on the db state from test_analytics.py or we can mock it here
    # For a robust test, we insert dummy daily metrics directly
    await db_session.execute(text("TRUNCATE TABLE merchant_metrics_daily CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE platform_metrics_daily CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE feature_metrics_daily CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE campaign_analytics_daily CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE platform_features CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE campaigns CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE merchants CASCADE"))
    await db_session.commit()

    # Create dummy merchant
    await db_session.execute(text("""
        INSERT INTO merchants (merchant_id, shopify_store_id, merchant_name, email, country, timezone, store_currency, app_install_status)
        VALUES (:id, 'store-1', 'Test Store', 'test@store.com', 'US', 'UTC', 'USD', 'installed')
    """), {"id": merchant_id})

    # Create dummy platform feature
    feature_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO platform_features (feature_id, feature_key, feature_name, feature_category, description)
        VALUES (:id, 'read_feature', 'Read Feature', 'test', 'desc')
    """), {"id": feature_id})

    # Create dummy segment
    segment_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO shopper_segments (segment_id, merchant_id, segment_name, segment_definition)
        VALUES (:id, :m_id, 'Test Segment', '{}')
    """), {"id": segment_id, "m_id": merchant_id})

    # Create dummy campaign
    campaign_id = uuid.uuid4()
    await db_session.execute(text("""
        INSERT INTO campaigns (campaign_id, merchant_id, segment_id, campaign_name, campaign_type, campaign_medium, status, start_at)
        VALUES (:id, :m_id, :s_id, 'Read Campaign', 'email', 'newsletter', 'active', :ts)
    """), {"id": campaign_id, "m_id": merchant_id, "s_id": segment_id, "ts": datetime.now(timezone.utc)})

    # Insert daily metrics
    await db_session.execute(text("""
        INSERT INTO platform_metrics_daily (
            metric_date, active_merchants, new_merchants, installed_merchants, uninstalled_merchants,
            new_subscriptions, subscription_upgrades, subscription_downgrades, subscription_cancellations,
            total_revenue, total_orders, active_shoppers, generated_at
        )
        VALUES (:d, 10, 1, 10, 0, 5, 0, 0, 0, 500.0, 5, 10, :ts)
    """), {"d": metric_date, "ts": datetime.now(timezone.utc)})

    await db_session.execute(text("""
        INSERT INTO merchant_metrics_daily (
            merchant_id, metric_date, revenue, order_count, unique_shoppers, new_shoppers,
            session_count, converted_session_count, product_view_count, wishlist_add_count,
            save_for_later_count, add_to_cart_count, checkout_count, purchase_count,
            conversion_rate, average_order_value, platform_login_count, campaign_created_count,
            feature_enable_count, feature_disable_count, generated_at
        )
        VALUES (:m, :d, 150.0, 2, 5, 1, 10, 2, 20, 5, 2, 5, 2, 2, 0.2, 75.0, 1, 0, 0, 0, :ts)
    """), {"m": merchant_id, "d": metric_date, "ts": datetime.now(timezone.utc)})
    
    # Second day for merchant to test aggregation
    metric_date_2 = date(2025, 3, 2)
    await db_session.execute(text("""
        INSERT INTO merchant_metrics_daily (
            merchant_id, metric_date, revenue, order_count, unique_shoppers, new_shoppers,
            session_count, converted_session_count, product_view_count, wishlist_add_count,
            save_for_later_count, add_to_cart_count, checkout_count, purchase_count,
            conversion_rate, average_order_value, platform_login_count, campaign_created_count,
            feature_enable_count, feature_disable_count, generated_at
        )
        VALUES (:m, :d, 50.0, 0, 1, 0, 5, 0, 5, 0, 0, 0, 0, 0, 0.0, 0.0, 1, 0, 0, 0, :ts)
    """), {"m": merchant_id, "d": metric_date_2, "ts": datetime.now(timezone.utc)})

    await db_session.execute(text("""
        INSERT INTO feature_metrics_daily (
            feature_id, metric_date, eligible_merchant_count, enabled_merchant_count,
            active_merchant_count, feature_event_count, adoption_rate, usage_rate, generated_at
        )
        VALUES (:f, :d, 100, 50, 20, 1000, 0.5, 0.4, :ts)
    """), {"f": feature_id, "d": metric_date, "ts": datetime.now(timezone.utc)})

    await db_session.execute(text("""
        INSERT INTO campaign_analytics_daily (
            campaign_id, metric_date, delivered_count, opened_count, clicked_count,
            converted_count, attributed_order_count, attributed_revenue,
            open_rate, click_through_rate, conversion_rate, generated_at
        )
        VALUES (:c, :d, 1000, 200, 50, 10, 10, 250.0, 0.2, 0.05, 0.01, :ts)
    """), {"c": campaign_id, "d": metric_date, "ts": datetime.now(timezone.utc)})

    await db_session.commit()

    # Refresh views
    await refresh_aggregate_views(db_session)

    # 1. Test get_platform_summary
    plat_summary = await get_platform_summary(db_session)
    # The view platform_metrics aggregates from current operational tables in the DB.
    # We might not have data in those since we only seeded metrics_daily tables, but we can verify it doesn't crash.
    assert plat_summary is not None
    assert hasattr(plat_summary, "total_revenue")

    # 2. Test get_platform_metrics_trend
    plat_trends = await get_platform_metrics_trend(db_session, start_date=date(2025, 3, 1), end_date=date(2025, 3, 2))
    assert len(plat_trends) == 1
    assert float(plat_trends[0].total_revenue) == 500.0

    # 3. Test get_feature_metrics_summary
    feature_summary = await get_feature_metrics_summary(db_session)
    assert len(feature_summary) == 1
    assert feature_summary[0].feature_id == feature_id
    assert feature_summary[0].feature_name == "Read Feature"
    assert float(feature_summary[0].adoption_rate) == 0.5

    # 4. Test get_merchant_metrics_summary (Aggregation)
    merch_summary = await get_merchant_metrics_summary(db_session, merchant_id, date(2025, 3, 1), date(2025, 3, 2))
    assert merch_summary is not None
    assert float(merch_summary.revenue) == 200.0 # 150 + 50
    assert merch_summary.order_count == 2
    assert merch_summary.session_count == 15
    assert merch_summary.converted_session_count == 2
    # conversion_rate = 2 / 15
    assert float(merch_summary.conversion_rate) == pytest.approx(2 / 15)
    # average_order_value = 200 / 2
    assert float(merch_summary.average_order_value) == 100.0

    # 5. Test get_merchant_metrics_trend
    merch_trends = await get_merchant_metrics_trend(db_session, merchant_id, date(2025, 3, 1), date(2025, 3, 2))
    assert len(merch_trends) == 2
    assert float(merch_trends[0].revenue) == 150.0

    # 6. Test get_campaign_analytics_for_merchant
    camp_summary = await get_campaign_analytics_for_merchant(db_session, merchant_id)
    assert len(camp_summary) == 1
    assert camp_summary[0].campaign_name == "Read Campaign"
    assert float(camp_summary[0].attributed_revenue) == 250.0
