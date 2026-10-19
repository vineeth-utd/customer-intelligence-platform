from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.processing_state import record_domain_activity
from app.models.metrics import MerchantMetricsDaily, PlatformMetricsDaily
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    ConversionFunnelResult,
    ConversionFunnelStage,
    CustomerRevenueBreakdown,
    FeatureMetricsResult,
    JourneyEntrySourcePerformance,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
    PlatformSummaryResult,
    PlatformTrendResult,
    PriorPeriodComparison,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
)

async def generate_merchant_metrics_daily(session: AsyncSession, metric_date: date) -> None:
    stmt = text("""
        WITH date_bounds AS (
            SELECT 
                CAST(:metric_date AS DATE) AS m_date,
                CAST(:metric_date AS TIMESTAMP) AT TIME ZONE 'UTC' AS start_ts,
                CAST(:metric_date + interval '1 day' AS TIMESTAMP) AT TIME ZONE 'UTC' AS end_ts
        ),
        shopper_stats AS (
            SELECT 
                s.merchant_id,
                COUNT(DISTINCT s.shopper_id) AS new_shoppers
            FROM shoppers s
            CROSS JOIN date_bounds db
            WHERE s.created_at >= db.start_ts AND s.created_at < db.end_ts
            GROUP BY s.merchant_id
        ),
        event_stats AS (
            SELECT 
                se.merchant_id,
                COUNT(DISTINCT se.shopper_id) AS unique_shoppers,
                COUNT(DISTINCT se.session_id) AS session_count,
                COUNT(DISTINCT CASE WHEN se.event_type = 'PURCHASE_COMPLETED' THEN se.session_id END) AS converted_session_count,
                COUNT(CASE WHEN se.event_type = 'PRODUCT_VIEWED' THEN 1 END) AS product_view_count,
                COUNT(CASE WHEN se.event_type = 'WISHLIST_ADDED' THEN 1 END) AS wishlist_add_count,
                COUNT(CASE WHEN se.event_type = 'SAVE_FOR_LATER_ADDED' THEN 1 END) AS save_for_later_count,
                COUNT(CASE WHEN se.event_type = 'ADD_TO_CART' THEN 1 END) AS add_to_cart_count,
                COUNT(CASE WHEN se.event_type = 'CHECKOUT_STARTED' THEN 1 END) AS checkout_count,
                COUNT(CASE WHEN se.event_type = 'PURCHASE_COMPLETED' THEN 1 END) AS purchase_count
            FROM shopper_events se
            CROSS JOIN date_bounds db
            WHERE se.event_timestamp >= db.start_ts AND se.event_timestamp < db.end_ts
            GROUP BY se.merchant_id
        ),
        order_stats AS (
            SELECT 
                o.merchant_id,
                COUNT(o.order_id) AS order_count,
                COALESCE(SUM(o.total_amount), 0) AS revenue
            FROM orders o
            CROSS JOIN date_bounds db
            WHERE o.placed_at >= db.start_ts AND o.placed_at < db.end_ts
            GROUP BY o.merchant_id
        ),
        merchant_event_stats AS (
            SELECT 
                me.merchant_id,
                COUNT(CASE WHEN me.event_type = 'MERCHANT_LOGIN' THEN 1 END) AS platform_login_count,
                COUNT(CASE WHEN me.event_type = 'FEATURE_ENABLED' THEN 1 END) AS feature_enable_count,
                COUNT(CASE WHEN me.event_type = 'FEATURE_DISABLED' THEN 1 END) AS feature_disable_count
            FROM merchant_events me
            CROSS JOIN date_bounds db
            WHERE me.event_timestamp >= db.start_ts AND me.event_timestamp < db.end_ts
            GROUP BY me.merchant_id
        ),
        campaign_event_stats AS (
            SELECT 
                ce.merchant_id,
                COUNT(CASE WHEN ce.event_type = 'CAMPAIGN_CREATED' THEN 1 END) AS campaign_created_count
            FROM campaign_events ce
            CROSS JOIN date_bounds db
            WHERE ce.event_timestamp >= db.start_ts AND ce.event_timestamp < db.end_ts
            GROUP BY ce.merchant_id
        ),
        active_merchants AS (
            SELECT merchant_id FROM shopper_stats
            UNION
            SELECT merchant_id FROM event_stats
            UNION
            SELECT merchant_id FROM order_stats
            UNION
            SELECT merchant_id FROM merchant_event_stats
            UNION
            SELECT merchant_id FROM campaign_event_stats
        )
        INSERT INTO merchant_metrics_daily (
            merchant_id, metric_date, revenue, order_count, unique_shoppers, new_shoppers,
            session_count, converted_session_count, product_view_count, wishlist_add_count,
            save_for_later_count, add_to_cart_count, checkout_count, purchase_count,
            conversion_rate, average_order_value, platform_login_count, campaign_created_count,
            feature_enable_count, feature_disable_count, generated_at
        )
        SELECT 
            am.merchant_id,
            db.m_date,
            COALESCE(o.revenue, 0),
            COALESCE(o.order_count, 0),
            COALESCE(e.unique_shoppers, 0),
            COALESCE(s.new_shoppers, 0),
            COALESCE(e.session_count, 0),
            COALESCE(e.converted_session_count, 0),
            COALESCE(e.product_view_count, 0),
            COALESCE(e.wishlist_add_count, 0),
            COALESCE(e.save_for_later_count, 0),
            COALESCE(e.add_to_cart_count, 0),
            COALESCE(e.checkout_count, 0),
            COALESCE(e.purchase_count, 0),
            CASE WHEN COALESCE(e.session_count, 0) > 0 
                 THEN CAST(COALESCE(e.converted_session_count, 0) AS NUMERIC) / e.session_count 
                 ELSE 0 END,
            CASE WHEN COALESCE(o.order_count, 0) > 0 
                 THEN COALESCE(o.revenue, 0) / o.order_count 
                 ELSE 0 END,
            COALESCE(me.platform_login_count, 0),
            COALESCE(ce.campaign_created_count, 0),
            COALESCE(me.feature_enable_count, 0),
            COALESCE(me.feature_disable_count, 0),
            NOW()
        FROM active_merchants am
        CROSS JOIN date_bounds db
        LEFT JOIN shopper_stats s ON am.merchant_id = s.merchant_id
        LEFT JOIN event_stats e ON am.merchant_id = e.merchant_id
        LEFT JOIN order_stats o ON am.merchant_id = o.merchant_id
        LEFT JOIN merchant_event_stats me ON am.merchant_id = me.merchant_id
        LEFT JOIN campaign_event_stats ce ON am.merchant_id = ce.merchant_id
        ON CONFLICT (merchant_id, metric_date) DO UPDATE SET
            revenue = EXCLUDED.revenue,
            order_count = EXCLUDED.order_count,
            unique_shoppers = EXCLUDED.unique_shoppers,
            new_shoppers = EXCLUDED.new_shoppers,
            session_count = EXCLUDED.session_count,
            converted_session_count = EXCLUDED.converted_session_count,
            product_view_count = EXCLUDED.product_view_count,
            wishlist_add_count = EXCLUDED.wishlist_add_count,
            save_for_later_count = EXCLUDED.save_for_later_count,
            add_to_cart_count = EXCLUDED.add_to_cart_count,
            checkout_count = EXCLUDED.checkout_count,
            purchase_count = EXCLUDED.purchase_count,
            conversion_rate = EXCLUDED.conversion_rate,
            average_order_value = EXCLUDED.average_order_value,
            platform_login_count = EXCLUDED.platform_login_count,
            campaign_created_count = EXCLUDED.campaign_created_count,
            feature_enable_count = EXCLUDED.feature_enable_count,
            feature_disable_count = EXCLUDED.feature_disable_count,
            generated_at = EXCLUDED.generated_at
        RETURNING merchant_id;
    """)
    result = await session.execute(stmt, {"metric_date": metric_date})
    merchant_ids = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    for m_id in merchant_ids:
        await record_domain_activity(session, "merchant", m_id, "analytics", now)


async def generate_platform_metrics_daily(session: AsyncSession, metric_date: date) -> None:
    stmt = text("""
        WITH date_bounds AS (
            SELECT 
                CAST(:metric_date AS DATE) AS m_date,
                CAST(:metric_date AS TIMESTAMP) AT TIME ZONE 'UTC' AS start_ts,
                CAST(:metric_date + interval '1 day' AS TIMESTAMP) AT TIME ZONE 'UTC' AS end_ts
        ),
        merchant_state AS (
            SELECT DISTINCT ON (merchant_id)
                merchant_id,
                event_type
            FROM merchant_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp < db.end_ts
              AND event_type IN ('APP_INSTALLED', 'APP_UNINSTALLED')
            ORDER BY merchant_id, event_timestamp DESC
        ),
        installed_stats AS (
            SELECT 
                COUNT(CASE WHEN event_type = 'APP_INSTALLED' THEN 1 END) AS installed_merchants,
                COUNT(CASE WHEN event_type = 'APP_UNINSTALLED' THEN 1 END) AS uninstalled_merchants
            FROM merchant_state
        ),
        merchant_daily_events AS (
            SELECT 
                COUNT(CASE WHEN event_type = 'MERCHANT_CREATED' THEN 1 END) AS new_merchants,
                COUNT(CASE WHEN event_type = 'SUBSCRIPTION_STARTED' THEN 1 END) AS new_subscriptions,
                COUNT(CASE WHEN event_type = 'SUBSCRIPTION_UPGRADED' THEN 1 END) AS subscription_upgrades,
                COUNT(CASE WHEN event_type = 'SUBSCRIPTION_DOWNGRADED' THEN 1 END) AS subscription_downgrades,
                COUNT(CASE WHEN event_type = 'SUBSCRIPTION_CANCELLED' THEN 1 END) AS subscription_cancellations
            FROM merchant_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp >= db.start_ts AND event_timestamp < db.end_ts
        ),
        active_merchants AS (
            SELECT merchant_id FROM merchant_metrics_daily 
            CROSS JOIN date_bounds db
            WHERE metric_date = db.m_date
            AND (session_count > 0 OR platform_login_count > 0 OR campaign_created_count > 0 OR order_count > 0)
        ),
        active_shoppers AS (
            SELECT COUNT(DISTINCT shopper_id) AS active_shoppers
            FROM shopper_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp >= db.start_ts AND event_timestamp < db.end_ts
        ),
        daily_revenue AS (
            SELECT 
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COALESCE(SUM(order_count), 0) AS total_orders
            FROM merchant_metrics_daily
            CROSS JOIN date_bounds db
            WHERE metric_date = db.m_date
        )
        INSERT INTO platform_metrics_daily (
            metric_date, active_merchants, new_merchants, installed_merchants, uninstalled_merchants,
            new_subscriptions, subscription_upgrades, subscription_downgrades, subscription_cancellations,
            total_revenue, total_orders, active_shoppers, generated_at
        )
        SELECT 
            db.m_date,
            COALESCE((SELECT COUNT(*) FROM active_merchants), 0),
            COALESCE(mde.new_merchants, 0),
            COALESCE(i.installed_merchants, 0),
            COALESCE(i.uninstalled_merchants, 0),
            COALESCE(mde.new_subscriptions, 0),
            COALESCE(mde.subscription_upgrades, 0),
            COALESCE(mde.subscription_downgrades, 0),
            COALESCE(mde.subscription_cancellations, 0),
            COALESCE(dr.total_revenue, 0),
            COALESCE(dr.total_orders, 0),
            COALESCE(a.active_shoppers, 0),
            NOW()
        FROM date_bounds db
        CROSS JOIN installed_stats i
        CROSS JOIN merchant_daily_events mde
        CROSS JOIN daily_revenue dr
        CROSS JOIN active_shoppers a
        ON CONFLICT (metric_date) DO UPDATE SET
            active_merchants = EXCLUDED.active_merchants,
            new_merchants = EXCLUDED.new_merchants,
            installed_merchants = EXCLUDED.installed_merchants,
            uninstalled_merchants = EXCLUDED.uninstalled_merchants,
            new_subscriptions = EXCLUDED.new_subscriptions,
            subscription_upgrades = EXCLUDED.subscription_upgrades,
            subscription_downgrades = EXCLUDED.subscription_downgrades,
            subscription_cancellations = EXCLUDED.subscription_cancellations,
            total_revenue = EXCLUDED.total_revenue,
            total_orders = EXCLUDED.total_orders,
            active_shoppers = EXCLUDED.active_shoppers,
            generated_at = EXCLUDED.generated_at;
    """)
    await session.execute(stmt, {"metric_date": metric_date})


async def generate_feature_metrics_daily(session: AsyncSession, metric_date: date) -> None:
    stmt = text("""
        WITH date_bounds AS (
            SELECT 
                CAST(:metric_date AS DATE) AS m_date,
                CAST(:metric_date + interval '1 day' AS TIMESTAMP) AT TIME ZONE 'UTC' AS end_ts
        ),
        merchant_install_state AS (
            SELECT DISTINCT ON (merchant_id)
                merchant_id,
                event_type AS install_status
            FROM merchant_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp < db.end_ts
              AND event_type IN ('APP_INSTALLED', 'APP_UNINSTALLED')
            ORDER BY merchant_id, event_timestamp DESC
        ),
        merchant_sub_state AS (
            SELECT DISTINCT ON (merchant_id)
                merchant_id,
                event_type AS sub_status,
                COALESCE(payload->>'plan_key', payload->>'new_plan_key') AS plan_key
            FROM merchant_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp < db.end_ts
              AND event_type IN ('SUBSCRIPTION_STARTED', 'SUBSCRIPTION_UPGRADED', 'SUBSCRIPTION_DOWNGRADED', 'SUBSCRIPTION_CANCELLED')
            ORDER BY merchant_id, event_timestamp DESC
        ),
        merchant_feature_state AS (
            SELECT DISTINCT ON (merchant_id, payload->>'feature_key')
                merchant_id,
                payload->>'feature_key' AS feature_key,
                event_type AS feature_status
            FROM merchant_events
            CROSS JOIN date_bounds db
            WHERE event_timestamp < db.end_ts
              AND event_type IN ('FEATURE_ENABLED', 'FEATURE_DISABLED')
            ORDER BY merchant_id, payload->>'feature_key', event_timestamp DESC
        ),
        eligible_merchants AS (
            SELECT 
                i.merchant_id,
                sp.plan_id,
                sp.plan_key
            FROM merchant_install_state i
            JOIN merchant_sub_state s ON i.merchant_id = s.merchant_id
            JOIN subscription_plans sp ON sp.plan_key = s.plan_key
            WHERE i.install_status = 'APP_INSTALLED'
              AND s.sub_status != 'SUBSCRIPTION_CANCELLED'
        ),
        feature_eligibility AS (
            SELECT 
                pf.feature_id,
                e.merchant_id
            FROM eligible_merchants e
            JOIN plan_features pf ON pf.plan_id = e.plan_id
        ),
        enabled_features AS (
            SELECT 
                pf.feature_id,
                f.merchant_id
            FROM merchant_feature_state f
            JOIN platform_features pf ON pf.feature_key = f.feature_key
            WHERE f.feature_status = 'FEATURE_ENABLED'
        ),
        feature_usage_events AS (
            SELECT 
                se.merchant_id,
                fem.feature_id,
                se.event_timestamp
            FROM shopper_events se
            JOIN feature_event_mappings fem ON fem.event_domain = 'shopper' AND fem.event_type = se.event_type
            CROSS JOIN date_bounds db
            WHERE se.event_timestamp >= CAST(:metric_date AS TIMESTAMP) AT TIME ZONE 'UTC'
              AND se.event_timestamp < db.end_ts
        ),
        usage_with_state AS (
            SELECT 
                u.merchant_id,
                u.feature_id,
                (SELECT event_type FROM merchant_events me WHERE me.merchant_id = u.merchant_id AND me.event_timestamp <= u.event_timestamp AND me.event_type IN ('APP_INSTALLED', 'APP_UNINSTALLED') ORDER BY me.event_timestamp DESC LIMIT 1) as install_status,
                (SELECT COALESCE(payload->>'plan_key', payload->>'new_plan_key') FROM merchant_events me WHERE me.merchant_id = u.merchant_id AND me.event_timestamp <= u.event_timestamp AND me.event_type IN ('SUBSCRIPTION_STARTED', 'SUBSCRIPTION_UPGRADED', 'SUBSCRIPTION_DOWNGRADED', 'SUBSCRIPTION_CANCELLED') ORDER BY me.event_timestamp DESC LIMIT 1) as plan_key,
                (SELECT event_type FROM merchant_events me WHERE me.merchant_id = u.merchant_id AND me.event_timestamp <= u.event_timestamp AND me.event_type IN ('SUBSCRIPTION_STARTED', 'SUBSCRIPTION_UPGRADED', 'SUBSCRIPTION_DOWNGRADED', 'SUBSCRIPTION_CANCELLED') ORDER BY me.event_timestamp DESC LIMIT 1) as sub_status,
                (SELECT event_type FROM merchant_events me JOIN platform_features pf ON pf.feature_key = me.payload->>'feature_key' WHERE me.merchant_id = u.merchant_id AND pf.feature_id = u.feature_id AND me.event_timestamp <= u.event_timestamp AND me.event_type IN ('FEATURE_ENABLED', 'FEATURE_DISABLED') ORDER BY me.event_timestamp DESC LIMIT 1) as feature_status
            FROM feature_usage_events u
        ),
        valid_usage AS (
            SELECT 
                u.feature_id,
                u.merchant_id
            FROM usage_with_state u
            LEFT JOIN subscription_plans sp ON sp.plan_key = u.plan_key
            LEFT JOIN plan_features pf ON pf.plan_id = sp.plan_id AND pf.feature_id = u.feature_id
            WHERE u.install_status = 'APP_INSTALLED'
              AND u.sub_status != 'SUBSCRIPTION_CANCELLED'
              AND pf.feature_id IS NOT NULL
              AND u.feature_status = 'FEATURE_ENABLED'
        ),
        usage_stats AS (
            SELECT 
                feature_id,
                COUNT(merchant_id) AS feature_event_count,
                COUNT(DISTINCT merchant_id) AS active_merchant_count
            FROM valid_usage
            GROUP BY feature_id
        ),
        feature_metrics AS (
            SELECT 
                f.feature_id,
                COUNT(DISTINCT fe.merchant_id) AS eligible_merchant_count,
                COUNT(DISTINCT CASE WHEN ef.feature_id IS NOT NULL THEN fe.merchant_id END) AS enabled_merchant_count
            FROM platform_features f
            LEFT JOIN feature_eligibility fe ON f.feature_id = fe.feature_id
            LEFT JOIN enabled_features ef ON fe.merchant_id = ef.merchant_id AND fe.feature_id = ef.feature_id
            GROUP BY f.feature_id
        )
        INSERT INTO feature_metrics_daily (
            feature_id, metric_date, eligible_merchant_count, enabled_merchant_count,
            active_merchant_count, feature_event_count, adoption_rate, usage_rate, generated_at
        )
        SELECT 
            fm.feature_id,
            db.m_date,
            fm.eligible_merchant_count,
            fm.enabled_merchant_count,
            COALESCE(us.active_merchant_count, 0),
            COALESCE(us.feature_event_count, 0),
            CASE WHEN fm.eligible_merchant_count > 0 
                 THEN CAST(fm.enabled_merchant_count AS NUMERIC) / fm.eligible_merchant_count 
                 ELSE 0 END,
            CASE WHEN fm.enabled_merchant_count > 0 
                 THEN CAST(COALESCE(us.active_merchant_count, 0) AS NUMERIC) / fm.enabled_merchant_count 
                 ELSE 0 END,
            NOW()
        FROM feature_metrics fm
        CROSS JOIN date_bounds db
        LEFT JOIN usage_stats us ON fm.feature_id = us.feature_id
        ON CONFLICT (feature_id, metric_date) DO UPDATE SET
            eligible_merchant_count = EXCLUDED.eligible_merchant_count,
            enabled_merchant_count = EXCLUDED.enabled_merchant_count,
            active_merchant_count = EXCLUDED.active_merchant_count,
            feature_event_count = EXCLUDED.feature_event_count,
            adoption_rate = EXCLUDED.adoption_rate,
            usage_rate = EXCLUDED.usage_rate,
            generated_at = EXCLUDED.generated_at;
    """)
    await session.execute(stmt, {"metric_date": metric_date})


async def generate_campaign_analytics_daily(session: AsyncSession, metric_date: date) -> None:
    stmt = text("""
        WITH date_bounds AS (
            SELECT 
                CAST(:metric_date AS DATE) AS m_date,
                CAST(:metric_date AS TIMESTAMP) AT TIME ZONE 'UTC' AS start_ts,
                CAST(:metric_date + interval '1 day' AS TIMESTAMP) AT TIME ZONE 'UTC' AS end_ts
        ),
        campaign_event_stats AS (
            SELECT 
                ce.campaign_id,
                COUNT(CASE WHEN ce.event_type IN ('EMAIL_DELIVERED', 'SMS_DELIVERED', 'PUSH_DELIVERED', 'AD_VIEWED') THEN 1 END) AS delivered_count,
                COUNT(CASE WHEN ce.event_type IN ('EMAIL_OPENED', 'PUSH_OPENED') THEN 1 END) AS opened_count,
                COUNT(CASE WHEN ce.event_type IN ('EMAIL_CLICKED', 'SMS_CLICKED', 'AD_CLICKED') THEN 1 END) AS clicked_count
            FROM campaign_events ce
            CROSS JOIN date_bounds db
            WHERE ce.event_timestamp >= db.start_ts AND ce.event_timestamp < db.end_ts
            GROUP BY ce.campaign_id
        ),
        conversion_stats AS (
            SELECT 
                ce.campaign_id,
                COUNT(DISTINCT ce.payload->>'order_id') AS converted_count,
                COUNT(DISTINCT ce.payload->>'order_id') AS attributed_order_count,
                SUM(o.total_amount) AS attributed_revenue
            FROM campaign_events ce
            JOIN orders o ON o.order_id = CAST(ce.payload->>'order_id' AS UUID)
            CROSS JOIN date_bounds db
            WHERE ce.event_type = 'CAMPAIGN_CONVERTED'
              AND ce.event_timestamp >= db.start_ts AND ce.event_timestamp < db.end_ts
            GROUP BY ce.campaign_id
        ),
        active_campaigns AS (
            SELECT campaign_id FROM campaign_event_stats
            UNION
            SELECT campaign_id FROM conversion_stats
        )
        INSERT INTO campaign_analytics_daily (
            campaign_id, metric_date, delivered_count, opened_count, clicked_count,
            converted_count, attributed_order_count, attributed_revenue,
            open_rate, click_through_rate, conversion_rate, generated_at
        )
        SELECT 
            ac.campaign_id,
            db.m_date,
            COALESCE(ce.delivered_count, 0),
            COALESCE(ce.opened_count, 0),
            COALESCE(ce.clicked_count, 0),
            COALESCE(cs.converted_count, 0),
            COALESCE(cs.attributed_order_count, 0),
            COALESCE(cs.attributed_revenue, 0),
            CASE WHEN COALESCE(ce.delivered_count, 0) > 0 
                 THEN CAST(COALESCE(ce.opened_count, 0) AS NUMERIC) / ce.delivered_count 
                 ELSE 0 END,
            CASE WHEN COALESCE(ce.delivered_count, 0) > 0 
                 THEN CAST(COALESCE(ce.clicked_count, 0) AS NUMERIC) / ce.delivered_count 
                 ELSE 0 END,
            CASE WHEN COALESCE(ce.delivered_count, 0) > 0 
                 THEN CAST(COALESCE(cs.converted_count, 0) AS NUMERIC) / ce.delivered_count 
                 ELSE 0 END,
            NOW()
        FROM active_campaigns ac
        CROSS JOIN date_bounds db
        LEFT JOIN campaign_event_stats ce ON ac.campaign_id = ce.campaign_id
        LEFT JOIN conversion_stats cs ON ac.campaign_id = cs.campaign_id
        ON CONFLICT (campaign_id, metric_date) DO UPDATE SET
            delivered_count = EXCLUDED.delivered_count,
            opened_count = EXCLUDED.opened_count,
            clicked_count = EXCLUDED.clicked_count,
            converted_count = EXCLUDED.converted_count,
            attributed_order_count = EXCLUDED.attributed_order_count,
            attributed_revenue = EXCLUDED.attributed_revenue,
            open_rate = EXCLUDED.open_rate,
            click_through_rate = EXCLUDED.click_through_rate,
            conversion_rate = EXCLUDED.conversion_rate,
            generated_at = EXCLUDED.generated_at;
    """)
    await session.execute(stmt, {"metric_date": metric_date})

async def refresh_aggregate_views(session: AsyncSession) -> None:
    """
    Refresh the materialized views summarizing lifetime/current performance.
    
    Must be executed outside a transaction block because REFRESH MATERIALIZED VIEW CONCURRENTLY 
    cannot run inside a transaction. We open a dedicated connection with AUTOCOMMIT.
    """
    engine = session.bind
    if engine is None:
        raise RuntimeError("Session is not bound to an engine")
        
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(
            text("REFRESH MATERIALIZED VIEW CONCURRENTLY campaign_analytics")
        )
        await conn.execute(
            text("REFRESH MATERIALIZED VIEW CONCURRENTLY feature_metrics")
        )
        await conn.execute(
            text("REFRESH MATERIALIZED VIEW platform_metrics")
        )

async def get_platform_summary(session: AsyncSession) -> Optional[PlatformSummaryResult]:
    stmt = text("SELECT total_merchants, active_merchants, total_revenue, total_orders, active_shoppers, active_subscriptions FROM platform_metrics LIMIT 1")
    res = await session.execute(stmt)
    row = res.fetchone()
    if row:
        return PlatformSummaryResult.model_validate(row)
    return None

async def get_platform_metrics_trend(session: AsyncSession, start_date: date, end_date: date) -> List[PlatformTrendResult]:
    stmt = select(PlatformMetricsDaily).where(
        PlatformMetricsDaily.metric_date >= start_date,
        PlatformMetricsDaily.metric_date <= end_date
    ).order_by(PlatformMetricsDaily.metric_date.asc())
    res = await session.execute(stmt)
    return [PlatformTrendResult.model_validate(row) for row in res.scalars().all()]

async def get_feature_metrics_summary(session: AsyncSession) -> List[FeatureMetricsResult]:
    stmt = text("""
        SELECT 
            fm.feature_id, 
            pf.feature_key, 
            pf.feature_name, 
            pf.feature_category,
            fm.eligible_merchant_count, 
            fm.enabled_merchant_count, 
            fm.active_merchant_count, 
            fm.total_feature_events, 
            fm.adoption_rate, 
            fm.usage_rate
        FROM feature_metrics fm
        JOIN platform_features pf ON pf.feature_id = fm.feature_id
    """)
    res = await session.execute(stmt)
    return [FeatureMetricsResult.model_validate(row) for row in res.fetchall()]

async def get_merchant_metrics_summary(session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date) -> Optional[MerchantMetricsSummaryResult]:
    stmt = text("""
        SELECT
            merchant_id,
            SUM(revenue) AS revenue,
            SUM(order_count) AS order_count,
            SUM(unique_shoppers) AS unique_shoppers,
            SUM(new_shoppers) AS new_shoppers,
            SUM(session_count) AS session_count,
            SUM(converted_session_count) AS converted_session_count,
            SUM(product_view_count) AS product_view_count,
            SUM(wishlist_add_count) AS wishlist_add_count,
            SUM(save_for_later_count) AS save_for_later_count,
            SUM(add_to_cart_count) AS add_to_cart_count,
            SUM(checkout_count) AS checkout_count,
            SUM(purchase_count) AS purchase_count,
            CASE WHEN SUM(session_count) > 0 
                 THEN CAST(SUM(converted_session_count) AS NUMERIC) / SUM(session_count) 
                 ELSE 0 END AS conversion_rate,
            CASE WHEN SUM(order_count) > 0 
                 THEN SUM(revenue) / SUM(order_count) 
                 ELSE 0 END AS average_order_value,
            SUM(platform_login_count) AS platform_login_count,
            SUM(campaign_created_count) AS campaign_created_count,
            SUM(feature_enable_count) AS feature_enable_count,
            SUM(feature_disable_count) AS feature_disable_count
        FROM merchant_metrics_daily
        WHERE merchant_id = :merchant_id
          AND metric_date >= :start_date 
          AND metric_date <= :end_date
        GROUP BY merchant_id
    """)
    res = await session.execute(stmt, {"merchant_id": merchant_id, "start_date": start_date, "end_date": end_date})
    row = res.fetchone()
    if row:
        return MerchantMetricsSummaryResult.model_validate(row)
    return None

async def get_merchant_metrics_trend(session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date) -> List[MerchantMetricsTrendResult]:
    stmt = select(MerchantMetricsDaily).where(
        MerchantMetricsDaily.merchant_id == merchant_id,
        MerchantMetricsDaily.metric_date >= start_date,
        MerchantMetricsDaily.metric_date <= end_date
    ).order_by(MerchantMetricsDaily.metric_date.asc())
    res = await session.execute(stmt)
    return [MerchantMetricsTrendResult.model_validate(row) for row in res.scalars().all()]

async def get_campaign_analytics_summary(session: AsyncSession, merchant_id: UUID) -> List[CampaignAnalyticsResult]:
    stmt = text("""
        SELECT 
            ca.campaign_id,
            c.campaign_name,
            c.campaign_type,
            c.campaign_medium,
            c.status,
            ca.delivered_count,
            ca.opened_count,
            ca.clicked_count,
            ca.converted_count,
            ca.attributed_order_count,
            ca.attributed_revenue,
            ca.open_rate,
            ca.click_through_rate,
            ca.conversion_rate
        FROM campaign_analytics ca
        JOIN campaigns c ON c.campaign_id = ca.campaign_id
        WHERE c.merchant_id = :merchant_id
    """)
    res = await session.execute(stmt, {"merchant_id": merchant_id})
    return [CampaignAnalyticsResult.model_validate(row) for row in res.fetchall()]


async def get_conversion_funnel(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> ConversionFunnelResult:
    """
    Computes store-level conversion funnel and secondary engagement metrics
    from merchant_metrics_daily.
    """
    stmt = text("""
        SELECT
            COALESCE(SUM(session_count), 0) AS total_sessions,
            COALESCE(SUM(product_view_count), 0) AS total_product_views,
            COALESCE(SUM(add_to_cart_count), 0) AS total_carts,
            COALESCE(SUM(checkout_count), 0) AS total_checkouts,
            COALESCE(SUM(purchase_count), 0) AS total_purchases,
            COALESCE(SUM(wishlist_add_count), 0) AS total_wishlist,
            COALESCE(SUM(save_for_later_count), 0) AS total_save_for_later
        FROM merchant_metrics_daily
        WHERE merchant_id = :merchant_id
          AND metric_date >= :start_date
          AND metric_date <= :end_date
    """)
    res = await session.execute(stmt, {"merchant_id": merchant_id, "start_date": start_date, "end_date": end_date})
    row = res.fetchone()

    total_sessions = int(row[0]) if row else 0
    total_views = int(row[1]) if row else 0
    total_carts = int(row[2]) if row else 0
    total_checkouts = int(row[3]) if row else 0
    total_purchases = int(row[4]) if row else 0
    total_wishlist = int(row[5]) if row else 0
    total_save_for_later = int(row[6]) if row else 0

    raw_stages = [
        ("Sessions", total_sessions),
        ("Product Views", total_views),
        ("Add to Cart", total_carts),
        ("Checkout Started", total_checkouts),
        ("Purchases", total_purchases),
    ]

    stages: list[ConversionFunnelStage] = []
    prev_count: int | None = None

    for idx, (name, count) in enumerate(raw_stages):
        if idx == 0:
            step_rate = Decimal("1.0") if count > 0 else Decimal("0.0")
            drop_count = 0
            drop_rate = Decimal("0.0")
        else:
            if prev_count is not None and prev_count > 0:
                step_rate = round(Decimal(count) / Decimal(prev_count), 4)
                drop_count = max(0, prev_count - count)
                drop_rate = round(Decimal(drop_count) / Decimal(prev_count), 4)
            else:
                step_rate = Decimal("0.0")
                drop_count = 0
                drop_rate = Decimal("0.0")

        overall_rate = round(Decimal(count) / Decimal(total_sessions), 4) if total_sessions > 0 else Decimal("0.0")

        stages.append(
            ConversionFunnelStage(
                stage_name=name,
                count=count,
                step_conversion_rate=step_rate,
                drop_off_count=drop_count,
                drop_off_rate=drop_rate,
                overall_conversion_rate=overall_rate,
            )
        )
        prev_count = count

    overall_conversion = round(Decimal(total_purchases) / Decimal(total_sessions), 4) if total_sessions > 0 else Decimal("0.0")
    cart_abandonment = round(Decimal(max(0, total_carts - total_purchases)) / Decimal(total_carts), 4) if total_carts > 0 else Decimal("0.0")
    checkout_abandonment = round(Decimal(max(0, total_checkouts - total_purchases)) / Decimal(total_checkouts), 4) if total_checkouts > 0 else Decimal("0.0")

    return ConversionFunnelResult(
        merchant_id=merchant_id,
        start_date=start_date,
        end_date=end_date,
        stages=stages,
        overall_conversion_rate=overall_conversion,
        cart_abandonment_rate=cart_abandonment,
        checkout_abandonment_rate=checkout_abandonment,
        secondary_engagement={
            "wishlist_add_count": total_wishlist,
            "save_for_later_count": total_save_for_later,
        },
    )


async def get_shopper_journey_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> ShopperJourneyAnalyticsResult:
    """
    Computes multi-touch Shopper Journey outcome and funnel analytics.
    Excludes currently OPEN journeys from the conversion rate denominator.
    Evaluates drop-off stages using completed NON_CONVERTING journeys.
    """
    start_ts = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_ts = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    # 1. Aggregate journey outcome counts & duration
    stmt_outcomes = text("""
        SELECT
            COUNT(*) AS total_journeys,
            COUNT(CASE WHEN journey_status = 'CONVERTED' THEN 1 END) AS converted_journeys,
            COUNT(CASE WHEN journey_status = 'NON_CONVERTING' THEN 1 END) AS non_converting_journeys,
            COUNT(CASE WHEN journey_status = 'OPEN' THEN 1 END) AS open_journeys,
            AVG(CASE WHEN journey_status = 'CONVERTED' AND ended_at IS NOT NULL 
                     THEN EXTRACT(EPOCH FROM (ended_at - started_at)) END) AS avg_conversion_duration
        FROM shopper_journeys
        WHERE merchant_id = :merchant_id
          AND started_at >= :start_ts
          AND started_at < :end_ts
    """)
    res_outcomes = await session.execute(stmt_outcomes, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_outcomes = res_outcomes.fetchone()

    total_journeys = int(row_outcomes[0]) if row_outcomes and row_outcomes[0] else 0
    converted_journeys = int(row_outcomes[1]) if row_outcomes and row_outcomes[1] else 0
    non_converting_journeys = int(row_outcomes[2]) if row_outcomes and row_outcomes[2] else 0
    open_journeys = int(row_outcomes[3]) if row_outcomes and row_outcomes[3] else 0
    avg_duration = float(row_outcomes[4]) if row_outcomes and row_outcomes[4] is not None else None

    # Exclude OPEN journeys from conversion denominator
    resolved = converted_journeys + non_converting_journeys
    journey_conversion_rate = round(Decimal(converted_journeys) / Decimal(resolved), 4) if resolved > 0 else Decimal("0.0")

    # 2. Drop-off stages for completed NON_CONVERTING journeys
    stmt_dropoffs = text("""
        WITH non_converting_last_events AS (
            SELECT DISTINCT ON (sje.journey_id)
                sje.journey_id,
                sje.event_type
            FROM shopper_journey_events sje
            JOIN shopper_journeys sj ON sj.journey_id = sje.journey_id
            WHERE sj.merchant_id = :merchant_id
              AND sj.started_at >= :start_ts
              AND sj.started_at < :end_ts
              AND sj.journey_status = 'NON_CONVERTING'
            ORDER BY sje.journey_id, sje.sequence_number DESC
        )
        SELECT event_type, COUNT(*) AS count
        FROM non_converting_last_events
        GROUP BY event_type
        ORDER BY count DESC
    """)
    res_dropoffs = await session.execute(stmt_dropoffs, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    drop_off_stages = {str(r[0]): int(r[1]) for r in res_dropoffs.fetchall()}

    # 3. Performance by entry source
    stmt_sources = text("""
        SELECT
            COALESCE(entry_source, 'direct') AS entry_source,
            COUNT(*) AS total_journeys,
            COUNT(CASE WHEN journey_status = 'CONVERTED' THEN 1 END) AS converted_journeys,
            COUNT(CASE WHEN journey_status = 'NON_CONVERTING' THEN 1 END) AS non_converting_journeys,
            COUNT(CASE WHEN journey_status = 'OPEN' THEN 1 END) AS open_journeys
        FROM shopper_journeys
        WHERE merchant_id = :merchant_id
          AND started_at >= :start_ts
          AND started_at < :end_ts
        GROUP BY COALESCE(entry_source, 'direct')
        ORDER BY total_journeys DESC
    """)
    res_sources = await session.execute(stmt_sources, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    by_entry_source: list[JourneyEntrySourcePerformance] = []
    for r in res_sources.fetchall():
        s_total = int(r[1])
        s_conv = int(r[2])
        s_non_conv = int(r[3])
        s_open = int(r[4])
        s_resolved = s_conv + s_non_conv
        s_rate = round(Decimal(s_conv) / Decimal(s_resolved), 4) if s_resolved > 0 else Decimal("0.0")
        by_entry_source.append(
            JourneyEntrySourcePerformance(
                entry_source=str(r[0]),
                total_journeys=s_total,
                converted_journeys=s_conv,
                non_converting_journeys=s_non_conv,
                open_journeys=s_open,
                conversion_rate=s_rate,
            )
        )

    return ShopperJourneyAnalyticsResult(
        merchant_id=merchant_id,
        start_date=start_date,
        end_date=end_date,
        total_journeys=total_journeys,
        converted_journeys=converted_journeys,
        non_converting_journeys=non_converting_journeys,
        open_journeys=open_journeys,
        journey_conversion_rate=journey_conversion_rate,
        average_conversion_duration_seconds=avg_duration,
        drop_off_stages=drop_off_stages,
        by_entry_source=by_entry_source,
    )


async def get_shopper_behavior_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> ShopperBehaviorAnalyticsResult:
    """
    Computes store-level shopper behavioral analytics:
    - New vs returning shoppers determined by authoritative first_seen_at.
    - Repeat purchase rate based on lifetime completed orders.
    """
    start_ts = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_ts = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    # 1. Total active shoppers and returning shoppers from shopper_events & shoppers
    stmt_activity = text("""
        SELECT
            COUNT(DISTINCT se.shopper_id) AS total_active,
            COUNT(DISTINCT CASE WHEN s.first_seen_at < :start_ts THEN se.shopper_id END) AS returning_active
        FROM shopper_events se
        JOIN shoppers s ON s.shopper_id = se.shopper_id
        WHERE se.merchant_id = :merchant_id
          AND se.event_timestamp >= :start_ts
          AND se.event_timestamp < :end_ts
    """)
    res_act = await session.execute(stmt_activity, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_act = res_act.fetchone()
    total_active = int(row_act[0]) if row_act and row_act[0] else 0
    returning_shoppers = int(row_act[1]) if row_act and row_act[1] else 0

    # 2. New shoppers authoritative from first_seen_at
    stmt_new = text("""
        SELECT COUNT(DISTINCT shopper_id)
        FROM shoppers
        WHERE merchant_id = :merchant_id
          AND first_seen_at >= :start_ts
          AND first_seen_at < :end_ts
    """)
    res_new = await session.execute(stmt_new, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    new_shoppers = int(res_new.scalar() or 0)

    # 3. Purchasing shoppers & repeat purchasers (completed orders only)
    stmt_purchasers = text("""
        WITH window_buyers AS (
            SELECT DISTINCT o.shopper_id
            FROM orders o
            WHERE o.merchant_id = :merchant_id
              AND o.order_status = 'completed'
              AND o.placed_at >= :start_ts
              AND o.placed_at < :end_ts
        ),
        lifetime_counts AS (
            SELECT o.shopper_id, COUNT(*) AS lifetime_orders
            FROM orders o
            JOIN window_buyers wb ON wb.shopper_id = o.shopper_id
            WHERE o.merchant_id = :merchant_id
              AND o.order_status = 'completed'
            GROUP BY o.shopper_id
        )
        SELECT
            (SELECT COUNT(*) FROM window_buyers) AS total_purchasing,
            COUNT(CASE WHEN lifetime_orders >= 2 THEN 1 END) AS repeat_purchasing
        FROM lifetime_counts
    """)
    res_purch = await session.execute(stmt_purchasers, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_purch = res_purch.fetchone()
    total_purchasing = int(row_purch[0]) if row_purch and row_purch[0] else 0
    repeat_purchasing = int(row_purch[1]) if row_purch and row_purch[1] else 0

    repeat_rate = round(Decimal(repeat_purchasing) / Decimal(total_purchasing), 4) if total_purchasing > 0 else Decimal("0.0")

    # 4. Average order value & secondary engagement
    stmt_order_metrics = text("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_revenue,
            COUNT(order_id) AS total_orders
        FROM orders
        WHERE merchant_id = :merchant_id
          AND order_status = 'completed'
          AND placed_at >= :start_ts
          AND placed_at < :end_ts
    """)
    res_orders = await session.execute(stmt_order_metrics, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_orders = res_orders.fetchone()
    tot_rev = Decimal(str(row_orders[0])) if row_orders and row_orders[0] else Decimal("0.0")
    tot_orders = int(row_orders[1]) if row_orders and row_orders[1] else 0
    aov = round(tot_rev / Decimal(tot_orders), 2) if tot_orders > 0 else Decimal("0.0")

    stmt_secondary = text("""
        SELECT
            COALESCE(SUM(wishlist_add_count), 0),
            COALESCE(SUM(save_for_later_count), 0)
        FROM merchant_metrics_daily
        WHERE merchant_id = :merchant_id
          AND metric_date >= :start_date
          AND metric_date <= :end_date
    """)
    res_sec = await session.execute(stmt_secondary, {"merchant_id": merchant_id, "start_date": start_date, "end_date": end_date})
    row_sec = res_sec.fetchone()
    wishlist_adds = int(row_sec[0]) if row_sec and row_sec[0] else 0
    save_adds = int(row_sec[1]) if row_sec and row_sec[1] else 0

    return ShopperBehaviorAnalyticsResult(
        merchant_id=merchant_id,
        start_date=start_date,
        end_date=end_date,
        total_active_shoppers=total_active,
        new_shoppers=new_shoppers,
        returning_shoppers=returning_shoppers,
        total_purchasing_shoppers=total_purchasing,
        repeat_purchasing_shoppers=repeat_purchasing,
        repeat_purchase_rate=repeat_rate,
        average_order_value=aov,
        secondary_engagement={
            "wishlist_add_count": wishlist_adds,
            "save_for_later_count": save_adds,
        },
    )


async def get_revenue_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> RevenueAnalyticsResult:
    """
    Computes revenue and order analytics:
    - Period-over-period comparison against immediate preceding equal-length period.
    - Growth percentages return null when prior period baseline is zero.
    - New vs repeat customer revenue based on completed order sequence.
    """
    window_days = (end_date - start_date).days + 1
    prior_end_date = start_date - timedelta(days=1)
    prior_start_date = prior_end_date - timedelta(days=window_days - 1)

    start_ts = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_ts = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    prior_start_ts = datetime.combine(prior_start_date, time.min, tzinfo=timezone.utc)
    prior_end_ts = datetime.combine(prior_end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    # 1. Current window completed orders
    stmt_curr = text("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_revenue,
            COUNT(order_id) AS total_orders
        FROM orders
        WHERE merchant_id = :merchant_id
          AND order_status = 'completed'
          AND placed_at >= :start_ts
          AND placed_at < :end_ts
    """)
    res_curr = await session.execute(stmt_curr, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_curr = res_curr.fetchone()
    total_rev = Decimal(str(row_curr[0])) if row_curr and row_curr[0] else Decimal("0.0")
    total_orders = int(row_curr[1]) if row_curr and row_curr[1] else 0
    aov = round(total_rev / Decimal(total_orders), 2) if total_orders > 0 else Decimal("0.0")

    # 2. Prior window completed orders
    stmt_prior = text("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS prior_revenue,
            COUNT(order_id) AS prior_orders
        FROM orders
        WHERE merchant_id = :merchant_id
          AND order_status = 'completed'
          AND placed_at >= :prior_start_ts
          AND placed_at < :prior_end_ts
    """)
    res_prior = await session.execute(stmt_prior, {"merchant_id": merchant_id, "prior_start_ts": prior_start_ts, "prior_end_ts": prior_end_ts})
    row_prior = res_prior.fetchone()
    prior_rev = Decimal(str(row_prior[0])) if row_prior and row_prior[0] else Decimal("0.0")
    prior_orders = int(row_prior[1]) if row_prior and row_prior[1] else 0
    prior_aov = round(prior_rev / Decimal(prior_orders), 2) if prior_orders > 0 else Decimal("0.0")

    # Calculate growth percentage: None if prior denominator is 0
    rev_growth = round(((total_rev - prior_rev) / prior_rev) * 100, 2) if prior_rev > 0 else None
    order_growth = round(((Decimal(total_orders) - Decimal(prior_orders)) / Decimal(prior_orders)) * 100, 2) if prior_orders > 0 else None
    aov_growth = round(((aov - prior_aov) / prior_aov) * 100, 2) if prior_aov > 0 else None

    # 3. New vs Repeat customer revenue in current window
    stmt_breakdown = text("""
        WITH ranked_orders AS (
            SELECT
                o.order_id,
                o.total_amount,
                o.placed_at,
                ROW_NUMBER() OVER (
                    PARTITION BY o.shopper_id
                    ORDER BY o.placed_at ASC, o.order_id ASC
                ) as order_seq
            FROM orders o
            WHERE o.merchant_id = :merchant_id
              AND o.order_status = 'completed'
        )
        SELECT
            COALESCE(SUM(CASE WHEN order_seq = 1 THEN total_amount ELSE 0 END), 0) AS new_customer_revenue,
            COUNT(CASE WHEN order_seq = 1 THEN 1 END) AS new_customer_order_count,
            COALESCE(SUM(CASE WHEN order_seq > 1 THEN total_amount ELSE 0 END), 0) AS repeat_customer_revenue,
            COUNT(CASE WHEN order_seq > 1 THEN 1 END) AS repeat_customer_order_count
        FROM ranked_orders
        WHERE placed_at >= :start_ts
          AND placed_at < :end_ts
    """)
    res_b = await session.execute(stmt_breakdown, {"merchant_id": merchant_id, "start_ts": start_ts, "end_ts": end_ts})
    row_b = res_b.fetchone()
    new_rev = Decimal(str(row_b[0])) if row_b and row_b[0] else Decimal("0.0")
    new_count = int(row_b[1]) if row_b and row_b[1] else 0
    rep_rev = Decimal(str(row_b[2])) if row_b and row_b[2] else Decimal("0.0")
    rep_count = int(row_b[3]) if row_b and row_b[3] else 0

    return RevenueAnalyticsResult(
        merchant_id=merchant_id,
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_rev,
        total_orders=total_orders,
        average_order_value=aov,
        prior_period_comparison=PriorPeriodComparison(
            prior_start_date=prior_start_date,
            prior_end_date=prior_end_date,
            prior_revenue=prior_rev,
            prior_orders=prior_orders,
            prior_average_order_value=prior_aov,
            revenue_growth_pct=rev_growth,
            order_growth_pct=order_growth,
            aov_growth_pct=aov_growth,
        ),
        customer_revenue_breakdown=CustomerRevenueBreakdown(
            new_customer_revenue=new_rev,
            new_customer_order_count=new_count,
            repeat_customer_revenue=rep_rev,
            repeat_customer_order_count=rep_count,
        ),
    )

