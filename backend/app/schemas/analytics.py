from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlatformSummaryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_merchants: int
    active_merchants: int
    total_revenue: Decimal
    total_orders: int
    active_shoppers: int
    active_subscriptions: int


class PlatformTrendResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_date: date
    active_merchants: int
    new_merchants: int
    installed_merchants: int
    uninstalled_merchants: int
    new_subscriptions: int
    subscription_upgrades: int
    subscription_downgrades: int
    subscription_cancellations: int
    total_revenue: Decimal
    total_orders: int
    active_shoppers: int


class FeatureMetricsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_id: UUID
    feature_key: str
    feature_name: str
    feature_category: str
    eligible_merchant_count: int
    enabled_merchant_count: int
    active_merchant_count: int
    total_feature_events: int
    adoption_rate: Decimal
    usage_rate: Decimal


class MerchantMetricsSummaryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    revenue: Decimal
    order_count: int
    unique_shoppers: int
    new_shoppers: int
    session_count: int
    converted_session_count: int
    product_view_count: int
    wishlist_add_count: int
    save_for_later_count: int
    add_to_cart_count: int
    checkout_count: int
    purchase_count: int
    conversion_rate: Decimal
    average_order_value: Decimal
    platform_login_count: int
    campaign_created_count: int
    feature_enable_count: int
    feature_disable_count: int


class MerchantMetricsTrendResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_date: date
    merchant_id: UUID
    revenue: Decimal
    order_count: int
    unique_shoppers: int
    new_shoppers: int
    session_count: int
    converted_session_count: int
    product_view_count: int
    wishlist_add_count: int
    save_for_later_count: int
    add_to_cart_count: int
    checkout_count: int
    purchase_count: int
    conversion_rate: Decimal
    average_order_value: Decimal
    platform_login_count: int
    campaign_created_count: int
    feature_enable_count: int
    feature_disable_count: int


class CampaignAnalyticsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    campaign_name: str
    campaign_type: str
    campaign_medium: str
    status: str
    delivered_count: int
    opened_count: int
    clicked_count: int
    converted_count: int
    attributed_order_count: int
    attributed_revenue: Decimal
    open_rate: Decimal
    click_through_rate: Decimal
    conversion_rate: Decimal


class ConversionFunnelStage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage_name: str
    count: int
    step_conversion_rate: Optional[Decimal] = None
    drop_off_count: int = 0
    drop_off_rate: Decimal = Decimal("0.0")
    overall_conversion_rate: Decimal = Decimal("0.0")


class ConversionFunnelResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    start_date: date
    end_date: date
    stages: list[ConversionFunnelStage]
    overall_conversion_rate: Decimal
    cart_abandonment_rate: Decimal
    checkout_abandonment_rate: Decimal
    secondary_engagement: dict[str, int]


class JourneyEntrySourcePerformance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_source: str
    total_journeys: int
    converted_journeys: int
    non_converting_journeys: int
    open_journeys: int
    conversion_rate: Decimal


class ShopperJourneyAnalyticsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    start_date: date
    end_date: date
    total_journeys: int
    converted_journeys: int
    non_converting_journeys: int
    open_journeys: int
    journey_conversion_rate: Decimal
    average_conversion_duration_seconds: Optional[float] = None
    drop_off_stages: dict[str, int]
    by_entry_source: list[JourneyEntrySourcePerformance]


class ShopperBehaviorAnalyticsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    start_date: date
    end_date: date
    total_active_shoppers: int
    new_shoppers: int
    returning_shoppers: int
    total_purchasing_shoppers: int
    repeat_purchasing_shoppers: int
    repeat_purchase_rate: Decimal
    average_order_value: Decimal
    secondary_engagement: dict[str, int]


class PriorPeriodComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prior_start_date: date
    prior_end_date: date
    prior_revenue: Decimal
    prior_orders: int
    prior_average_order_value: Decimal
    revenue_growth_pct: Optional[Decimal] = None
    order_growth_pct: Optional[Decimal] = None
    aov_growth_pct: Optional[Decimal] = None


class CustomerRevenueBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    new_customer_revenue: Decimal
    new_customer_order_count: int
    repeat_customer_revenue: Decimal
    repeat_customer_order_count: int


class RevenueAnalyticsResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    start_date: date
    end_date: date
    total_revenue: Decimal
    total_orders: int
    average_order_value: Decimal
    prior_period_comparison: PriorPeriodComparison
    customer_revenue_breakdown: CustomerRevenueBreakdown


class CampaignDailyTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_date: date
    delivered_count: int
    opened_count: int
    clicked_count: int
    converted_count: int
    attributed_order_count: int
    attributed_revenue: Decimal
    open_rate: Decimal
    click_through_rate: Decimal
    conversion_rate: Decimal


class CampaignPerformanceDetailResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    merchant_id: UUID
    campaign_name: str
    campaign_type: str
    campaign_medium: str
    status: str
    start_date: date
    end_date: date
    delivered_count: int
    opened_count: int
    clicked_count: int
    open_rate: Decimal
    click_through_rate: Decimal
    trends: list[CampaignDailyTrendPoint]
    prior_period_delivered: int
    prior_period_opened: int
    prior_period_clicked: int
    delivered_growth_pct: Optional[Decimal] = None
    opened_growth_pct: Optional[Decimal] = None
    clicked_growth_pct: Optional[Decimal] = None


class AttributionModelMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversions_count: int
    attributed_revenue: Decimal
    average_order_value: Decimal


class CampaignAttributionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    merchant_id: UUID
    start_date: date
    end_date: date
    direct_session: AttributionModelMetric
    first_touch_journey: AttributionModelMetric
    last_touch_journey: AttributionModelMetric
    assisted_journey: AttributionModelMetric
    explicit_recorded: AttributionModelMetric
    direct_vs_cross_session_journeys: dict[str, int]


class CampaignJourneyCorrelationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    merchant_id: UUID
    start_date: date
    end_date: date
    total_journeys_touched: int
    converted_journeys: int
    non_converting_journeys: int
    open_journeys: int
    journey_conversion_rate: Decimal
    average_touch_to_conversion_seconds: Optional[float] = None
    drop_off_stages: dict[str, int]


class CurrentSegmentAudienceMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: UUID
    segment_name: str
    current_members_count: int
    reached_shoppers_count: int
    engaged_shoppers_count: int
    converted_shoppers_count: int
    conversion_rate: Decimal


class CampaignAudienceAnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    merchant_id: UUID
    target_segment_id: UUID
    target_segment_name: str
    target_segment_current_members: int
    unique_shoppers_reached: int
    unique_shoppers_engaged: int
    unique_shoppers_converted: int
    target_segment_current_members_reached: int
    target_segment_current_members_engaged: int
    target_segment_current_members_converted: int
    non_target_current_shoppers_reached: int
    non_target_current_shoppers_engaged: int
    non_target_current_shoppers_converted: int
    current_segments_breakdown: list[CurrentSegmentAudienceMetric]

