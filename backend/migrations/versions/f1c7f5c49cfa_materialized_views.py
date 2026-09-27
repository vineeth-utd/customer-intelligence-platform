"""materialized views

Revision ID: f1c7f5c49cfa
Revises: 9131d3af4ed2
Create Date: 2026-09-12 23:04:46.149199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1c7f5c49cfa'
down_revision: Union[str, Sequence[str], None] = '9131d3af4ed2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CAMPAIGN_ANALYTICS_SQL = """
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

FEATURE_METRICS_SQL = """
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

PLATFORM_METRICS_SQL = """
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
    """Upgrade schema."""
    op.execute(CAMPAIGN_ANALYTICS_SQL)
    op.execute(FEATURE_METRICS_SQL)
    op.execute(PLATFORM_METRICS_SQL)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS platform_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS feature_metrics")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS campaign_analytics")
