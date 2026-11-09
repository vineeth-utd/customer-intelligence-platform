from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.analytics import (
    CampaignAnalyticsResult,
    ConversionFunnelResult,
    FeatureMetricsResult,
    MerchantMetricsSummaryResult,
    PlatformSummaryResult,
    PlatformTrendResult,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
)
from app.schemas.merchant import (
    MerchantDetailResponse,
    MerchantHealthResponse,
)


class PlatformDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: PlatformSummaryResult
    trends: List[PlatformTrendResult]
    features: List[FeatureMetricsResult]


class MerchantDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    start_date: date
    end_date: date
    merchant: MerchantDetailResponse
    health: Optional[MerchantHealthResponse] = None
    summary: MerchantMetricsSummaryResult
    revenue: RevenueAnalyticsResult
    funnel: ConversionFunnelResult
    journeys: ShopperJourneyAnalyticsResult
    behavior: ShopperBehaviorAnalyticsResult
    campaigns: List[CampaignAnalyticsResult]

