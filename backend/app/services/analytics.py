from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.analytics import (
    generate_merchant_metrics_daily,
    generate_platform_metrics_daily,
    generate_feature_metrics_daily,
    generate_campaign_analytics_daily,
    get_platform_summary as da_get_platform_summary,
    get_platform_metrics_trend as da_get_platform_metrics_trend,
    get_feature_metrics_summary as da_get_feature_metrics_summary,
    get_merchant_metrics_summary as da_get_merchant_metrics_summary,
    get_merchant_metrics_trend as da_get_merchant_metrics_trend,
    get_campaign_analytics_summary as da_get_campaign_analytics_summary,
)
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    FeatureMetricsResult,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
    PlatformSummaryResult,
    PlatformTrendResult,
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

async def refresh_aggregate_views(session: AsyncSession) -> None:
    """
    Refresh the materialized views summarizing lifetime/current performance.
    """
    from app.data_access.analytics import refresh_aggregate_views as da_refresh_aggregate_views
    await da_refresh_aggregate_views(session)

async def get_platform_summary(session: AsyncSession) -> Optional[PlatformSummaryResult]:
    return await da_get_platform_summary(session)

async def get_platform_metrics_trend(session: AsyncSession, start_date: date, end_date: date) -> List[PlatformTrendResult]:
    return await da_get_platform_metrics_trend(session, start_date, end_date)

async def get_feature_metrics_summary(session: AsyncSession) -> List[FeatureMetricsResult]:
    return await da_get_feature_metrics_summary(session)

async def get_merchant_metrics_summary(session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date) -> Optional[MerchantMetricsSummaryResult]:
    return await da_get_merchant_metrics_summary(session, merchant_id, start_date, end_date)

async def get_merchant_metrics_trend(session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date) -> List[MerchantMetricsTrendResult]:
    return await da_get_merchant_metrics_trend(session, merchant_id, start_date, end_date)

async def get_campaign_analytics_for_merchant(session: AsyncSession, merchant_id: UUID) -> List[CampaignAnalyticsResult]:
    return await da_get_campaign_analytics_summary(session, merchant_id)
