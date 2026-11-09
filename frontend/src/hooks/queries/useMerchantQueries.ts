import { useQuery } from '@tanstack/react-query';
import { merchantsApi } from '../../api';

export const merchantKeys = {
  all: ['merchants'] as const,
  list: (limit: number, offset: number) => [...merchantKeys.all, 'list', limit, offset] as const,
  detail: (merchantId: string) => [...merchantKeys.all, 'detail', merchantId] as const,
  profile: (merchantId: string) => [...merchantKeys.all, 'profile', merchantId] as const,
  health: (merchantId: string) => [...merchantKeys.all, 'health', merchantId] as const,
  journeys: (merchantId: string) => [...merchantKeys.all, 'journeys', merchantId] as const,
  journeyDetail: (merchantId: string, journeyId: string) =>
    [...merchantKeys.all, 'journeys', merchantId, journeyId] as const,
  features: (merchantId: string) => [...merchantKeys.all, 'features', merchantId] as const,
  subscription: (merchantId: string) => [...merchantKeys.all, 'subscription', merchantId] as const,
  shoppers: (merchantId: string, limit: number, offset: number) =>
    [...merchantKeys.all, 'shoppers', merchantId, limit, offset] as const,
  orders: (merchantId: string, limit: number, offset: number) =>
    [...merchantKeys.all, 'orders', merchantId, limit, offset] as const,
  metricsSummary: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'metrics', 'summary', merchantId, startDate, endDate] as const,
  metricsTrend: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'metrics', 'trend', merchantId, startDate, endDate] as const,
  campaignAnalytics: (merchantId: string) =>
    [...merchantKeys.all, 'campaigns', 'analytics', merchantId] as const,
  funnel: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'funnel', merchantId, startDate, endDate] as const,
  shopperJourneys: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'analytics', 'journeys', merchantId, startDate, endDate] as const,
  shopperBehavior: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'analytics', 'behavior', merchantId, startDate, endDate] as const,
  revenue: (merchantId: string, startDate: string, endDate: string) =>
    [...merchantKeys.all, 'analytics', 'revenue', merchantId, startDate, endDate] as const,
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

export const useMerchantProfile = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.profile(merchantId),
    queryFn: () => merchantsApi.getMerchantProfile(merchantId),
    enabled: !!merchantId,
  });
};

export const useMerchantHealth = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.health(merchantId),
    queryFn: () => merchantsApi.getMerchantHealth(merchantId),
    enabled: !!merchantId,
  });
};

export const useMerchantJourneys = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.journeys(merchantId),
    queryFn: () => merchantsApi.getMerchantJourneys(merchantId),
    enabled: !!merchantId,
  });
};

export const useMerchantJourneyDetail = (merchantId: string, journeyId: string) => {
  return useQuery({
    queryKey: merchantKeys.journeyDetail(merchantId, journeyId),
    queryFn: () => merchantsApi.getMerchantJourneyDetail(merchantId, journeyId),
    enabled: !!merchantId && !!journeyId,
  });
};

export const useMerchantFeatures = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.features(merchantId),
    queryFn: () => merchantsApi.getMerchantFeatures(merchantId),
    enabled: !!merchantId,
  });
};

export const useMerchantSubscription = (merchantId: string) => {
  return useQuery({
    queryKey: merchantKeys.subscription(merchantId),
    queryFn: () => merchantsApi.getMerchantSubscription(merchantId),
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

export const useMerchantFunnel = (merchantId: string, startDate: string, endDate: string) => {
  return useQuery({
    queryKey: merchantKeys.funnel(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantFunnel(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

export const useMerchantShopperJourneysAnalytics = (
  merchantId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: merchantKeys.shopperJourneys(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantShopperJourneysAnalytics(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

export const useMerchantShopperBehavior = (
  merchantId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: merchantKeys.shopperBehavior(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantShopperBehavior(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

export const useMerchantRevenue = (
  merchantId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: merchantKeys.revenue(merchantId, startDate, endDate),
    queryFn: () => merchantsApi.getMerchantRevenue(merchantId, startDate, endDate),
    enabled: !!merchantId && !!startDate && !!endDate,
  });
};

