import { apiClient } from './client';
import type {
  PaginatedResponse,
  MerchantSummaryResponse,
  MerchantDetailResponse,
  ShopperResponse,
  OrderResponse,
  MerchantMetricsSummaryResult,
  MerchantMetricsTrendResult,
  CampaignAnalyticsResult,
} from '../types';

export const merchantsApi = {
  getMerchants: (limit = 50, offset = 0) => {
    return apiClient.get<PaginatedResponse<MerchantSummaryResponse>>('/api/v1/merchants', { limit, offset });
  },
  getMerchant: (merchantId: string) => {
    return apiClient.get<MerchantDetailResponse>(`/api/v1/merchants/${merchantId}`);
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
};
