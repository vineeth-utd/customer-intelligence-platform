import { apiClient } from './client';
import type { PlatformDashboardResponse, MerchantDashboardResponse } from '../types';

export const dashboardApi = {
  getPlatformDashboard: (startDate: string, endDate: string) => {
    return apiClient.get<PlatformDashboardResponse>('/api/v1/dashboard/platform', {
      start_date: startDate,
      end_date: endDate,
    });
  },
  getMerchantDashboard: (merchantId: string, startDate: string, endDate: string) => {
    return apiClient.get<MerchantDashboardResponse>(`/api/v1/dashboard/merchants/${merchantId}`, {
      start_date: startDate,
      end_date: endDate,
    });
  },
};

