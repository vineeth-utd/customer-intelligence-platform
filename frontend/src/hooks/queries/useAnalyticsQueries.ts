import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../api';

export const analyticsKeys = {
  all: ['analytics'] as const,
  platformSummary: () => [...analyticsKeys.all, 'platform', 'summary'] as const,
  platformTrend: (startDate: string, endDate: string) => [...analyticsKeys.all, 'platform', 'trend', startDate, endDate] as const,
  features: () => [...analyticsKeys.all, 'features'] as const,
};

export const usePlatformSummary = () => {
  return useQuery({
    queryKey: analyticsKeys.platformSummary(),
    queryFn: () => analyticsApi.getPlatformSummary(),
  });
};

export const usePlatformTrend = (startDate: string, endDate: string) => {
  return useQuery({
    queryKey: analyticsKeys.platformTrend(startDate, endDate),
    queryFn: () => analyticsApi.getPlatformTrend(startDate, endDate),
    enabled: !!startDate && !!endDate,
  });
};

export const useFeatureMetrics = () => {
  return useQuery({
    queryKey: analyticsKeys.features(),
    queryFn: () => analyticsApi.getFeatureMetrics(),
  });
};
