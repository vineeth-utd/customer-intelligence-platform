export type CampaignStatus = 'draft' | 'active' | 'completed';

export interface CampaignSummaryResponse {
  campaign_id: string;
  merchant_id: string;
  segment_id: string;
  campaign_name: string;
  campaign_type: string;
  campaign_medium: string;
  status: string;
  start_at: string | null;
  end_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignDetailResponse extends CampaignSummaryResponse {
  target_segment_name: string | null;
}

export interface CampaignDailyTrendPoint {
  metric_date: string;
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

export interface CampaignPerformanceDetailResult {
  campaign_id: string;
  merchant_id: string;
  campaign_name: string;
  campaign_type: string;
  campaign_medium: string;
  status: string;
  start_date: string;
  end_date: string;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  open_rate: number;
  click_through_rate: number;
  trends: CampaignDailyTrendPoint[];
  prior_period_delivered: number;
  prior_period_opened: number;
  prior_period_clicked: number;
  delivered_growth_pct: number | null;
  opened_growth_pct: number | null;
  clicked_growth_pct: number | null;
}

export interface AttributionModelMetric {
  conversions_count: number;
  attributed_revenue: number;
  average_order_value: number;
}

export interface CampaignAttributionResult {
  campaign_id: string;
  merchant_id: string;
  start_date: string;
  end_date: string;
  direct_session: AttributionModelMetric;
  first_touch_journey: AttributionModelMetric;
  last_touch_journey: AttributionModelMetric;
  assisted_journey: AttributionModelMetric;
  explicit_recorded: AttributionModelMetric;
  direct_vs_cross_session_journeys: Record<string, number>;
}

export interface CampaignJourneyCorrelationResult {
  campaign_id: string;
  merchant_id: string;
  start_date: string;
  end_date: string;
  total_journeys_touched: number;
  converted_journeys: number;
  non_converting_journeys: number;
  open_journeys: number;
  journey_conversion_rate: number;
  average_touch_to_conversion_seconds: number | null;
  drop_off_stages: Record<string, number>;
}

export interface CurrentSegmentAudienceMetric {
  segment_id: string;
  segment_name: string;
  current_members_count: number;
  reached_shoppers_count: number;
  engaged_shoppers_count: number;
  converted_shoppers_count: number;
  conversion_rate: number;
}

export interface CampaignAudienceAnalysisResult {
  campaign_id: string;
  merchant_id: string;
  target_segment_id: string;
  target_segment_name: string;
  target_segment_current_members: number;
  unique_shoppers_reached: number;
  unique_shoppers_engaged: number;
  unique_shoppers_converted: number;
  target_segment_current_members_reached: number;
  target_segment_current_members_engaged: number;
  target_segment_current_members_converted: number;
  non_target_current_shoppers_reached: number;
  non_target_current_shoppers_engaged: number;
  non_target_current_shoppers_converted: number;
  current_segments_breakdown: CurrentSegmentAudienceMetric[];
}

