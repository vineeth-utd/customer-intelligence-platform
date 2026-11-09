export interface PlatformSummaryResult {
  total_merchants: number;
  active_merchants: number;
  total_revenue: number;
  total_orders: number;
  active_shoppers: number;
  active_subscriptions: number;
}

export interface PlatformTrendResult {
  metric_date: string;
  active_merchants: number;
  new_merchants: number;
  installed_merchants: number;
  uninstalled_merchants: number;
  new_subscriptions: number;
  subscription_upgrades: number;
  subscription_downgrades: number;
  subscription_cancellations: number;
  total_revenue: number;
  total_orders: number;
  active_shoppers: number;
}

export interface FeatureMetricsResult {
  feature_id: string;
  feature_key: string;
  feature_name: string;
  feature_category: string;
  eligible_merchant_count: number;
  enabled_merchant_count: number;
  active_merchant_count: number;
  total_feature_events: number;
  adoption_rate: number;
  usage_rate: number;
}

export interface MerchantMetricsSummaryResult {
  merchant_id: string;
  revenue: number;
  order_count: number;
  unique_shoppers: number;
  new_shoppers: number;
  session_count: number;
  converted_session_count: number;
  product_view_count: number;
  wishlist_add_count: number;
  save_for_later_count: number;
  add_to_cart_count: number;
  checkout_count: number;
  purchase_count: number;
  conversion_rate: number;
  average_order_value: number;
  platform_login_count: number;
  campaign_created_count: number;
  feature_enable_count: number;
  feature_disable_count: number;
}

export interface MerchantMetricsTrendResult {
  metric_date: string;
  merchant_id: string;
  revenue: number;
  order_count: number;
  unique_shoppers: number;
  new_shoppers: number;
  session_count: number;
  converted_session_count: number;
  product_view_count: number;
  wishlist_add_count: number;
  save_for_later_count: number;
  add_to_cart_count: number;
  checkout_count: number;
  purchase_count: number;
  conversion_rate: number;
  average_order_value: number;
  platform_login_count: number;
  campaign_created_count: number;
  feature_enable_count: number;
  feature_disable_count: number;
}

export interface CampaignAnalyticsResult {
  campaign_id: string;
  campaign_name: string;
  campaign_type: string;
  campaign_medium: string;
  status: string;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  converted_count: number;
  attributed_order_count: number;
  attributed_revenue: number;
  open_rate: number;
  click_through_rate: number;
  conversion_rate: number;
}

export interface ConversionFunnelStage {
  stage_name: string;
  count: number;
  step_conversion_rate: number | null;
  drop_off_count: number;
  drop_off_rate: number;
  overall_conversion_rate: number;
}

export interface ConversionFunnelResult {
  merchant_id: string;
  start_date: string;
  end_date: string;
  stages: ConversionFunnelStage[];
  overall_conversion_rate: number;
  cart_abandonment_rate: number;
  checkout_abandonment_rate: number;
  secondary_engagement: Record<string, number>;
}

export interface JourneyEntrySourcePerformance {
  entry_source: string;
  total_journeys: number;
  converted_journeys: number;
  non_converting_journeys: number;
  open_journeys: number;
  conversion_rate: number;
}

export interface ShopperJourneyAnalyticsResult {
  merchant_id: string;
  start_date: string;
  end_date: string;
  total_journeys: number;
  converted_journeys: number;
  non_converting_journeys: number;
  open_journeys: number;
  journey_conversion_rate: number;
  average_conversion_duration_seconds: number | null;
  drop_off_stages: Record<string, number>;
  by_entry_source: JourneyEntrySourcePerformance[];
}

export interface ShopperBehaviorAnalyticsResult {
  merchant_id: string;
  start_date: string;
  end_date: string;
  total_active_shoppers: number;
  new_shoppers: number;
  returning_shoppers: number;
  total_purchasing_shoppers: number;
  repeat_purchasing_shoppers: number;
  repeat_purchase_rate: number;
  average_order_value: number;
  secondary_engagement: Record<string, number>;
}

export interface PriorPeriodComparison {
  prior_start_date: string;
  prior_end_date: string;
  prior_revenue: number;
  prior_orders: number;
  prior_average_order_value: number;
  revenue_growth_pct: number | null;
  order_growth_pct: number | null;
  aov_growth_pct: number | null;
}

export interface CustomerRevenueBreakdown {
  new_customer_revenue: number;
  new_customer_order_count: number;
  repeat_customer_revenue: number;
  repeat_customer_order_count: number;
}

export interface RevenueAnalyticsResult {
  merchant_id: string;
  start_date: string;
  end_date: string;
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  prior_period_comparison: PriorPeriodComparison;
  customer_revenue_breakdown: CustomerRevenueBreakdown;
}

