export interface SubscriptionResponse {
  plan_id: string;
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
