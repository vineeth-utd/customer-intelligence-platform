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
    get_conversion_funnel as da_get_conversion_funnel,
    get_shopper_journey_analytics as da_get_shopper_journey_analytics,
    get_shopper_behavior_analytics as da_get_shopper_behavior_analytics,
    get_revenue_analytics as da_get_revenue_analytics,
    get_campaign_performance as da_get_campaign_performance,
    get_campaign_attribution as da_get_campaign_attribution,
    get_campaign_journey_correlation as da_get_campaign_journey_correlation,
    get_campaign_audience_analysis as da_get_campaign_audience_analysis,
    refresh_aggregate_views as da_refresh_aggregate_views,
)
from app.data_access.campaign import get_campaign
from app.data_access.merchant import get_merchant_by_id
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    CampaignAttributionResult,
    CampaignAudienceAnalysisResult,
    CampaignJourneyCorrelationResult,
    CampaignPerformanceDetailResult,
    ConversionFunnelResult,
    FeatureMetricsResult,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
    PlatformSummaryResult,
    PlatformTrendResult,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
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


async def get_conversion_funnel(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> Optional[ConversionFunnelResult]:
    """Retrieve store-level conversion funnel and engagement metrics."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None
    return await da_get_conversion_funnel(session, merchant_id, start_date, end_date)


async def get_shopper_journey_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> Optional[ShopperJourneyAnalyticsResult]:
    """Retrieve Shopper Journey multi-touch outcome and funnel analytics."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None
    return await da_get_shopper_journey_analytics(session, merchant_id, start_date, end_date)


async def get_shopper_behavior_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> Optional[ShopperBehaviorAnalyticsResult]:
    """Retrieve store-level shopper behavioral analytics."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None
    return await da_get_shopper_behavior_analytics(session, merchant_id, start_date, end_date)


async def get_revenue_analytics(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> Optional[RevenueAnalyticsResult]:
    """Retrieve revenue, order, and comparative period analytics."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None
    return await da_get_revenue_analytics(session, merchant_id, start_date, end_date)


async def get_campaign_performance(
    session: AsyncSession, campaign_id: UUID, start_date: date, end_date: date
) -> Optional[CampaignPerformanceDetailResult]:
    """Retrieve detailed campaign delivery, engagement trends, and period comparison."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    return await da_get_campaign_performance(session, campaign_id, start_date, end_date)


async def get_campaign_attribution(
    session: AsyncSession, campaign_id: UUID, start_date: date, end_date: date
) -> Optional[CampaignAttributionResult]:
    """Retrieve multi-perspective deterministic attribution for a campaign."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    return await da_get_campaign_attribution(session, campaign_id, start_date, end_date)


async def get_campaign_journey_correlation(
    session: AsyncSession, campaign_id: UUID, start_date: date, end_date: date
) -> Optional[CampaignJourneyCorrelationResult]:
    """Retrieve shopper journey outcome distribution and drop-offs for journeys touched by a campaign."""
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    return await da_get_campaign_journey_correlation(session, campaign_id, start_date, end_date)


async def get_campaign_audience_analysis(
    session: AsyncSession, campaign_id: UUID
) -> Optional[CampaignAudienceAnalysisResult]:
    """Retrieve reach, engagement, and conversion analysis across target and current segments for a campaign."""
    campaign = await get_campaign(session, campaign_id)
    if not campaign:
        return None
    return await da_get_campaign_audience_analysis(session, campaign_id)


