import { apiClient } from './client';
import type { PlatformSummaryResult, PlatformTrendResult, FeatureMetricsResult } from '../types';

export const analyticsApi = {
  getPlatformSummary: () => {
    return apiClient.get<PlatformSummaryResult>('/api/v1/analytics/platform/summary');
  },
  getPlatformTrend: (startDate: string, endDate: string) => {
    return apiClient.get<PlatformTrendResult[]>('/api/v1/analytics/platform/trend', { start_date: startDate, end_date: endDate });
  },
  getFeatureMetrics: () => {
    return apiClient.get<FeatureMetricsResult[]>('/api/v1/analytics/features');
  },
};
