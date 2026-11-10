export interface ShopperResponse {
  shopper_id: string;
  merchant_id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  country: string | null;
  state: string | null;
  city: string | null;
  timezone: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
}

export interface ShopperProfileResponse {
  shopper_id: string;
  total_orders: number;
  total_spend: number;
  average_order_value: number;
  customer_lifetime_value: number | null;
  purchase_frequency: number | null;
  wishlist_item_count: number;
  save_for_later_item_count: number;
  cart_abandonment_count: number | null;
  campaign_engagement_count: number;
  preferred_category: string | null;
  preferred_size: string | null;
  last_purchase_at: string | null;
  last_activity_at: string | null;
  lifecycle_stage: string | null;
  generated_at: string;
}

export interface ShopperJourneyEventResponse {
  journey_event_id: string;
  source_event_category: string;
  source_event_id: string;
  event_type: string;
  event_timestamp: string;
  sequence_number: number;
}

export interface ShopperJourneyResponse {
  journey_id: string;
  merchant_id: string;
  shopper_id: string;
  started_at: string;
  ended_at: string | null;
  journey_status: string;
  converted: boolean;
  order_id: string | null;
  entry_source: string | null;
  generated_at: string;
}

export interface ShopperJourneyDetailResponse extends ShopperJourneyResponse {
  events: ShopperJourneyEventResponse[];
}

export interface ShopperSegmentMembershipResponse {
  segment_id: string;
  segment_name: string;
  generated_at: string;
}

export interface ShopperActivityEventResponse {
  event_id: string;
  session_id: string;
  event_type: string;
  event_timestamp: string;
  source: string;
  activity_details: Record<string, unknown>;
}
