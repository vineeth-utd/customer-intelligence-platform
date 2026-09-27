import { useQuery } from '@tanstack/react-query';
import { merchantsApi } from '../../api';

export const merchantKeys = {
  all: ['merchants'] as const,
  list: (limit: number, offset: number) => [...merchantKeys.all, 'list', limit, offset] as const,
  detail: (merchantId: string) => [...merchantKeys.all, 'detail', merchantId] as const,
  shoppers: (merchantId: string, limit: number, offset: number) => [...merchantKeys.all, 'shoppers', merchantId, limit, offset] as const,
  orders: (merchantId: string, limit: number, offset: number) => [...merchantKeys.all, 'orders', merchantId, limit, offset] as const,
  metricsSummary: (merchantId: string, startDate: string, endDate: string) => [...merchantKeys.all, 'metrics', 'summary', merchantId, startDate, endDate] as const,
  metricsTrend: (merchantId: string, startDate: string, endDate: string) => [...merchantKeys.all, 'metrics', 'trend', merchantId, startDate, endDate] as const,
  campaignAnalytics: (merchantId: string) => [...merchantKeys.all, 'campaigns', 'analytics', merchantId] as const,
};

export const useMerchants = (limit = 50, offset = 0) => {
  return useQuery({
    queryKey: merchantKeys.list(limit, offset),
    queryFn: () => merchantsApi.getMerchants(limit, offset),
  });
};

export const useMerchant = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.detail(merchantId),
    queryFn: () => merchantsApi.getMerchant(merchantId),
    enabled: !!merchantId,
  });
};

export const useMerchantShoppers = (merchantId: string, limit = 50, offset = 0) => {
  return useQuery({
    queryKey: merchantKeys.shoppers(merchantId, limit, offset),
    queryFn: () => merchantsApi.getMerchantShoppers(merchantId, limit, offset),
    enabled: !!merchantId,
  });
};

export const useMerchantOrders = (merchantId: string, limit = 50, offset = 0) => {
  return useQuery({
    queryKey: merchantKeys.orders(merchantId, limit, offset),
    queryFn: () => merchantsApi.getMerchantOrders(merchantId, limit, offset),
    enabled: !!merchantId,
  });
};

export const useMerchantMetricsSummary = (merchantId: string, startDate: string, endDate: string) => {
  return useQuery({
    queryKey: merchantKeys.metricsSummary(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantMetricsSummary(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

export const useMerchantMetricsTrend = (merchantId: string, startDate: string, endDate: string) => {
  return useQuery({
    queryKey: merchantKeys.metricsTrend(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantMetricsTrend(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

export const useMerchantCampaignAnalytics = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.campaignAnalytics(merchantId),
    queryFn: () => merchantsApi.getCampaignAnalytics(merchantId),
    enabled: !!merchantId,
  });
};
