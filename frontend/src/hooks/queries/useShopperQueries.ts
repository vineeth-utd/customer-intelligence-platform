import { useQuery } from '@tanstack/react-query';
import { shoppersApi } from '../../api';

export const shopperKeys = {
  all: ['shoppers'] as const,
  detail: (merchantId: string, shopperId: string) =>
    [...shopperKeys.all, 'detail', merchantId, shopperId] as const,
  profile: (merchantId: string, shopperId: string) =>
    [...shopperKeys.all, 'profile', merchantId, shopperId] as const,
  journeys: (merchantId: string, shopperId: string) =>
    [...shopperKeys.all, 'journeys', merchantId, shopperId] as const,
  journeyDetail: (merchantId: string, shopperId: string, journeyId: string) =>
    [...shopperKeys.all, 'journeys', merchantId, shopperId, journeyId] as const,
  orders: (merchantId: string, shopperId: string, limit: number, offset: number) =>
    [...shopperKeys.all, 'orders', merchantId, shopperId, limit, offset] as const,
  segments: (merchantId: string, shopperId: string) =>
    [...shopperKeys.all, 'segments', merchantId, shopperId] as const,
  activity: (
    merchantId: string,
    shopperId: string,
    limit: number,
    offset: number,
    startDate?: string,
    endDate?: string
  ) =>
    [...shopperKeys.all, 'activity', merchantId, shopperId, limit, offset, startDate, endDate] as const,
};

export const useShopper = (merchantId: string, shopperId: string) => {
  return useQuery({
    queryKey: shopperKeys.detail(merchantId, shopperId),
    queryFn: () => shoppersApi.getShopper(merchantId, shopperId),
    enabled: !!merchantId && !!shopperId,
  });
};

export const useShopperProfile = (merchantId: string, shopperId: string) => {
  return useQuery({
    queryKey: shopperKeys.profile(merchantId, shopperId),
    queryFn: () => shoppersApi.getShopperProfile(merchantId, shopperId),
    enabled: !!merchantId && !!shopperId,
  });
};

export const useShopperJourneys = (merchantId: string, shopperId: string) => {
  return useQuery({
    queryKey: shopperKeys.journeys(merchantId, shopperId),
    queryFn: () => shoppersApi.getShopperJourneys(merchantId, shopperId),
    enabled: !!merchantId && !!shopperId,
  });
};

export const useShopperJourneyDetail = (
  merchantId: string,
  shopperId: string,
  journeyId: string
) => {
  return useQuery({
    queryKey: shopperKeys.journeyDetail(merchantId, shopperId, journeyId),
    queryFn: () => shoppersApi.getShopperJourneyDetail(merchantId, shopperId, journeyId),
    enabled: !!merchantId && !!shopperId && !!journeyId,
  });
};

export const useShopperOrders = (
  merchantId: string,
  shopperId: string,
  limit = 50,
  offset = 0
) => {
  return useQuery({
    queryKey: shopperKeys.orders(merchantId, shopperId, limit, offset),
    queryFn: () => shoppersApi.getShopperOrders(merchantId, shopperId, limit, offset),
    enabled: !!merchantId && !!shopperId,
  });
};

export const useShopperSegments = (merchantId: string, shopperId: string) => {
  return useQuery({
    queryKey: shopperKeys.segments(merchantId, shopperId),
    queryFn: () => shoppersApi.getShopperSegments(merchantId, shopperId),
    enabled: !!merchantId && !!shopperId,
  });
};

export const useShopperActivity = (
  merchantId: string,
  shopperId: string,
  limit = 50,
  offset = 0,
  startDate?: string,
  endDate?: string
) => {
  return useQuery({
    queryKey: shopperKeys.activity(merchantId, shopperId, limit, offset, startDate, endDate),
    queryFn: () =>
      shoppersApi.getShopperActivity(merchantId, shopperId, limit, offset, startDate, endDate),
    enabled: !!merchantId && !!shopperId,
  });
};

