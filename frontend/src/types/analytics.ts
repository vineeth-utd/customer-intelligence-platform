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
