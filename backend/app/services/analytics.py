from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.analytics import (
    generate_merchant_metrics_daily,
    generate_platform_metrics_daily,
    generate_feature_metrics_daily,
    generate_campaign_analytics_daily,
)


async def generate_daily_metrics(session: AsyncSession, metric_date: date) -> None:
    """
    Idempotent analytical business processing.
    Delegates to set-based PostgreSQL aggregations to rebuild derived state for a UTC calendar boundary.
    """
    await generate_merchant_metrics_daily(session, metric_date)
    await generate_platform_metrics_daily(session, metric_date)
    await generate_feature_metrics_daily(session, metric_date)
    await generate_campaign_analytics_daily(session, metric_date)
