"""update_materialized_views

Revision ID: c619c8f70888
Revises: 3a8ae5045daa
Create Date: 2026-09-24 13:26:20.373365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c619c8f70888'
down_revision: Union[str, Sequence[str], None] = '3a8ae5045daa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# We drop and recreate the views to fix the usage_rate formula, zero denominators, and add unique indexes

CAMPAIGN_ANALYTICS_SQL_V2 = """
CREATE MATERIALIZED VIEW campaign_analytics AS
SELECT
    campaign_id,
    SUM(delivered_count) AS delivered_count,
    SUM(opened_count) AS opened_count,
    SUM(clicked_count) AS clicked_count,
    SUM(converted_count) AS converted_count,
    SUM(attributed_order_count) AS attributed_order_count,
    SUM(attributed_revenue) AS attributed_revenue,
    COALESCE(SUM(opened_count)::numeric / NULLIF(SUM(delivered_count), 0), 0) AS open_rate,
    COALESCE(SUM(clicked_count)::numeric / NULLIF(SUM(delivered_count), 0), 0) AS click_through_rate,
    COALESCE(SUM(converted_count)::numeric / NULLIF(SUM(delivered_count), 0), 0) AS conversion_rate
FROM campaign_analytics_daily
GROUP BY campaign_id
"""

FEATURE_METRICS_SQL_V2 = """
CREATE MATERIALIZED VIEW feature_metrics AS
SELECT
    latest.feature_id,
    latest.eligible_merchant_count,
    latest.enabled_merchant_count,
    latest.active_merchant_count,
    totals.total_feature_events,
    COALESCE(latest.enabled_merchant_count::numeric / NULLIF(latest.eligible_merchant_count, 0), 0) AS adoption_rate,
    COALESCE(latest.active_merchant_count::numeric / NULLIF(latest.enabled_merchant_count, 0), 0) AS usage_rate
FROM (
    SELECT DISTINCT ON (feature_id)
        feature_id, eligible_merchant_count, enabled_merchant_count, active_merchant_count
    FROM feature_metrics_daily
    ORDER BY feature_id, metric_date DESC
) latest
JOIN (
    SELECT feature_id, SUM(feature_event_count) AS total_feature_events
    FROM feature_metrics_daily
    GROUP BY feature_id
) totals ON totals.feature_id = latest.feature_id
"""

PLATFORM_METRICS_SQL_V2 = """
CREATE MATERIALIZED VIEW platform_metrics AS
SELECT
    (SELECT COUNT(*) FROM merchants) AS total_merchants,
    latest.active_merchants,
    totals.total_revenue,
    totals.total_orders,
    latest.active_shoppers,
    (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') AS active_subscriptions
FROM (
    SELECT active_merchants, active_shoppers
    FROM platform_metrics_daily
    ORDER BY metric_date DESC
    LIMIT 1
) latest
CROSS JOIN (
    SELECT SUM(total_revenue) AS total_revenue, SUM(total_orders) AS total_orders
    FROM platform_metrics_daily
) totals
"""

# V1 Definitions for downgrade
CAMPAIGN_ANALYTICS_SQL_V1 = """
CREATE MATERIALIZED VIEW campaign_analytics AS
SELECT
    campaign_id,
    SUM(delivered_count) AS delivered_count,
    SUM(opened_count) AS opened_count,
    SUM(clicked_count) AS clicked_count,
    SUM(converted_count) AS converted_count,
    SUM(attributed_order_count) AS attributed_order_count,
    SUM(attributed_revenue) AS attributed_revenue,
    SUM(opened_count)::numeric / NULLIF(SUM(delivered_count), 0) AS open_rate,
    SUM(clicked_count)::numeric / NULLIF(SUM(delivered_count), 0) AS click_through_rate,
    SUM(converted_count)::numeric / NULLIF(SUM(delivered_count), 0) AS conversion_rate
FROM campaign_analytics_daily
GROUP BY campaign_id
"""

FEATURE_METRICS_SQL_V1 = """
CREATE MATERIALIZED VIEW feature_metrics AS
SELECT
    latest.feature_id,
    latest.eligible_merchant_count,
    latest.enabled_merchant_count,
    latest.active_merchant_count,
    totals.total_feature_events,
    latest.enabled_merchant_count::numeric / NULLIF(latest.eligible_merchant_count, 0) AS adoption_rate,
    latest.active_merchant_count::numeric / NULLIF(latest.eligible_merchant_count, 0) AS usage_rate
FROM (
    SELECT DISTINCT ON (feature_id)
        feature_id, eligible_merchant_count, enabled_merchant_count, active_merchant_count
    FROM feature_metrics_daily
    ORDER BY feature_id, metric_date DESC
) latest
JOIN (
    SELECT feature_id, SUM(feature_event_count) AS total_feature_events
    FROM feature_metrics_daily
    GROUP BY feature_id
) totals ON totals.feature_id = latest.feature_id
"""

PLATFORM_METRICS_SQL_V1 = """
CREATE MATERIALIZED VIEW platform_metrics AS
SELECT
    (SELECT COUNT(*) FROM merchants) AS total_merchants,
    latest.active_merchants,
    totals.total_revenue,
    totals.total_orders,
    latest.active_shoppers,
    (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') AS active_subscriptions
FROM (
    SELECT active_merchants, active_shoppers
    FROM platform_metrics_daily
    ORDER BY metric_date DESC
    LIMIT 1
) latest
CROSS JOIN (
    SELECT SUM(total_revenue) AS total_revenue, SUM(total_orders) AS total_orders
    FROM platform_metrics_daily
) totals
"""

def upgrade() -> None:
    # Drop existing views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS platform_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS feature_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS campaign_analytics")
    
    # Recreate views with V2 queries
    op.execute(CAMPAIGN_ANALYTICS_SQL_V2)
    op.execute(FEATURE_METRICS_SQL_V2)
    op.execute(PLATFORM_METRICS_SQL_V2)
    
    # Add unique indexes for CONCURRENTLY refreshes
    op.execute("CREATE UNIQUE INDEX ix_campaign_analytics_id ON campaign_analytics (campaign_id)")
    op.execute("CREATE UNIQUE INDEX ix_feature_metrics_id ON feature_metrics (feature_id)")


def downgrade() -> None:
    # Drop existing views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS platform_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS feature_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS campaign_analytics")
    
    # Recreate views with V1 queries
    op.execute(CAMPAIGN_ANALYTICS_SQL_V1)
    op.execute(FEATURE_METRICS_SQL_V1)
    op.execute(PLATFORM_METRICS_SQL_V1)
