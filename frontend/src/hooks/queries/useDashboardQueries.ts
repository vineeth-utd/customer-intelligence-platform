import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../../api';

export const dashboardKeys = {
  all: ['dashboard'] as const,
  platform: (startDate: string, endDate: string) =>
    [...dashboardKeys.all, 'platform', startDate, endDate] as const,
  merchant: (merchantId: string, startDate: string, endDate: string) =>
    [...dashboardKeys.all, 'merchant', merchantId, startDate, endDate] as const,
};

export const usePlatformDashboard = (startDate: string, endDate: string, enabled = true) => {
  return useQuery({
    queryKey: dashboardKeys.platform(startDate, endDate),
    queryFn: () => dashboardApi.getPlatformDashboard(startDate, endDate),
    enabled: enabled && !!startDate && !!endDate,
  });
};

export const useMerchantDashboard = (
  merchantId: string,
  startDate: string,
  endDate: string,
  enabled = true
) => {
  return useQuery({
    queryKey: dashboardKeys.merchant(merchantId, startDate, endDate),
    queryFn: () => dashboardApi.getMerchantDashboard(merchantId, startDate, endDate),
    enabled: enabled && !!merchantId && !!startDate && !!endDate,
  });
};

