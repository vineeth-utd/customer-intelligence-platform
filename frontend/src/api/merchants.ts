import { apiClient } from './client';
import type {
  PaginatedResponse,
  MerchantSummaryResponse,
  MerchantDetailResponse,
  MerchantProfileResponse,
  MerchantHealthResponse,
  MerchantJourneyResponse,
  MerchantJourneyDetailResponse,
  MerchantFeatureResponse,
  SubscriptionResponse,
  ShopperResponse,
  OrderResponse,
  MerchantMetricsSummaryResult,
  MerchantMetricsTrendResult,
  CampaignAnalyticsResult,
  ConversionFunnelResult,
  ShopperJourneyAnalyticsResult,
  ShopperBehaviorAnalyticsResult,
  RevenueAnalyticsResult,
} from '../types';

export const merchantsApi = {
  getMerchants: (limit = 50, offset = 0) => {
    return apiClient.get<PaginatedResponse<MerchantSummaryResponse>>('/api/v1/merchants', { limit, offset });
  },
  getMerchant: (merchantId: string) => {
    return apiClient.get<MerchantDetailResponse>(`/api/v1/merchants/${merchantId}`);
  },
  getMerchantProfile: (merchantId: string) => {
    return apiClient.get<MerchantProfileResponse>(`/api/v1/merchants/${merchantId}/profile`);
  },
  getMerchantHealth: (merchantId: string) => {
    return apiClient.get<MerchantHealthResponse>(`/api/v1/merchants/${merchantId}/health`);
  },
  getMerchantJourneys: (merchantId: string) => {
    return apiClient.get<MerchantJourneyResponse[]>(`/api/v1/merchants/${merchantId}/journeys`);
  },
  getMerchantJourneyDetail: (merchantId: string, journeyId: string) => {
    return apiClient.get<MerchantJourneyDetailResponse>(`/api/v1/merchants/${merchantId}/journeys/${journeyId}`);
  },
  getMerchantFeatures: (merchantId: string) => {
    return apiClient.get<MerchantFeatureResponse[]>(`/api/v1/merchants/${merchantId}/features`);
  },
  getMerchantSubscription: (merchantId: string) => {
    return apiClient.get<SubscriptionResponse>(`/api/v1/merchants/${merchantId}/subscription`);
  },
  getMerchantShoppers: (merchantId: string, limit = 50, offset = 0) => {
    return apiClient.get<PaginatedResponse<ShopperResponse>>(`/api/v1/merchants/${merchantId}/shoppers`, { limit, offset });
  },
  getMerchantOrders: (merchantId: string, limit = 50, offset = 0) => {
    return apiClient.get<PaginatedResponse<OrderResponse>>(`/api/v1/merchants/${merchantId}/orders`, { limit, offset });
  },
  getMerchantMetricsSummary: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<MerchantMetricsSummaryResult>(`/api/v1/merchants/${merchantId}/analytics/summary`, { start_date: startDate, end_date: endDate });
  },
  getMerchantMetricsTrend: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<MerchantMetricsTrendResult[]>(`/api/v1/merchants/${merchantId}/analytics/trend`, { start_date: startDate, end_date: endDate });
  },
  getCampaignAnalytics: (merchantId: string) => {
    return apiClient.get<CampaignAnalyticsResult[]>(`/api/v1/merchants/${merchantId}/campaigns/analytics`);
  },
  getMerchantFunnel: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<ConversionFunnelResult>(`/api/v1/merchants/${merchantId}/analytics/funnel`, { start_date: startDate, end_date: endDate });
  },
  getMerchantShopperJourneysAnalytics: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<ShopperJourneyAnalyticsResult>(`/api/v1/merchants/${merchantId}/analytics/journeys`, { start_date: startDate, end_date: endDate });
  },
  getMerchantShopperBehavior: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<ShopperBehaviorAnalyticsResult>(`/api/v1/merchants/${merchantId}/analytics/behavior`, { start_date: startDate, end_date: endDate });
  },
  getMerchantRevenue: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<RevenueAnalyticsResult>(`/api/v1/merchants/${merchantId}/analytics/revenue`, { start_date: startDate, end_date: endDate });
  },
};

