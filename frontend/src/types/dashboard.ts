import type {
  PlatformSummaryResult,
  PlatformTrendResult,
  FeatureMetricsResult,
  MerchantMetricsSummaryResult,
  RevenueAnalyticsResult,
  ConversionFunnelResult,
  ShopperJourneyAnalyticsResult,
  ShopperBehaviorAnalyticsResult,
  CampaignAnalyticsResult,
} from './analytics';
import type {
  MerchantDetailResponse,
  MerchantHealthResponse,
} from './merchant';

export interface PlatformDashboardResponse {
  summary: PlatformSummaryResult;
  trends: PlatformTrendResult[];
  features: FeatureMetricsResult[];
}

export interface MerchantDashboardResponse {
  merchant_id: string;
  start_date: string;
  end_date: string;
  merchant: MerchantDetailResponse;
  health: MerchantHealthResponse | null;
  summary: MerchantMetricsSummaryResult;
  revenue: RevenueAnalyticsResult;
  funnel: ConversionFunnelResult;
  journeys: ShopperJourneyAnalyticsResult;
  behavior: ShopperBehaviorAnalyticsResult;
  campaigns: CampaignAnalyticsResult[];
}

