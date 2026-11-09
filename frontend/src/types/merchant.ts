export interface SubscriptionResponse {
  plan_id: string;
  plan_name: string;
  status: string;
  billing_cycle: string;
  amount_paid: number;
  started_at: string;
  renewal_at: string | null;
  cancelled_at: string | null;
}

export interface MerchantDetailResponse {
  merchant_id: string;
  merchant_name: string;
  shopify_store_id: string;
  email: string;
  country: string | null;
  timezone: string | null;
  store_currency: string;
  app_install_status: string;
  last_active_at: string | null;
  active_subscription: SubscriptionResponse | null;
}

export interface MerchantSummaryResponse {
  merchant_id: string;
  merchant_name: string;
  shopify_store_id: string;
  email: string;
  store_currency: string;
  app_install_status: string;
  last_active_at: string | null;
}

export interface MerchantProfileResponse {
  merchant_id: string;
  total_shoppers: number;
  total_products: number;
  total_orders: number;
  total_revenue: number;
  average_order_value: number;
  conversion_rate: number;
  total_campaigns: number;
  active_campaign_count: number;
  enabled_feature_count: number;
  last_order_at: string | null;
  last_campaign_at: string | null;
  generated_at: string;
}

export type MerchantHealthStatus = 'HEALTHY' | 'NEEDS_ATTENTION' | 'AT_RISK';

export interface MerchantHealthFactors {
  feature_adoption: Record<string, unknown>;
  engagement: Record<string, unknown>;
  business_performance: Record<string, unknown>;
  subscription: Record<string, unknown>;
  risk_alerts: string[];
}

export interface MerchantHealthResponse {
  merchant_id: string;
  health_score: number;
  health_status: MerchantHealthStatus;
  churn_risk_score: number;
  engagement_score: number;
  feature_adoption_score: number;
  business_performance_score: number;
  calculated_at: string;
  contributing_factors: MerchantHealthFactors;
}

export type MerchantJourneyStatus = 'OPEN' | 'COMPLETED';

export interface MerchantJourneyEventResponse {
  merchant_journey_event_id: string;
  source_event_category: string;
  source_event_id: string;
  event_type: string;
  event_timestamp: string;
  sequence_number: number;
}

export interface MerchantJourneyResponse {
  merchant_journey_id: string;
  merchant_id: string;
  started_at: string;
  ended_at: string | null;
  journey_status: MerchantJourneyStatus;
  generated_at: string;
}

export interface MerchantJourneyDetailResponse extends MerchantJourneyResponse {
  events: MerchantJourneyEventResponse[];
}

export interface MerchantFeatureResponse {
  feature_id: string;
  feature_key: string;
  feature_name: string;
  feature_category: string;
  description: string | null;
  is_entitled: boolean;
  is_enabled: boolean;
}

