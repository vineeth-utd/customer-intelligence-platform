from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
            generated_at = EXCLUDED.generated_at;
    """)
    await session.execute(stmt, {"metric_date": metric_date})


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
                payload->>'plan_key' AS plan_key
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
                (SELECT payload->>'plan_key' FROM merchant_events me WHERE me.merchant_id = u.merchant_id AND me.event_timestamp <= u.event_timestamp AND me.event_type IN ('SUBSCRIPTION_STARTED', 'SUBSCRIPTION_UPGRADED', 'SUBSCRIPTION_DOWNGRADED', 'SUBSCRIPTION_CANCELLED') ORDER BY me.event_timestamp DESC LIMIT 1) as plan_key,
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
