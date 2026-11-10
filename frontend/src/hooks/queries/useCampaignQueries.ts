import { useQuery } from '@tanstack/react-query';
import { campaignsApi } from '../../api';
import type { CampaignStatus } from '../../types';

export const campaignKeys = {
  all: ['campaigns'] as const,
  list: (merchantId: string, limit: number, offset: number, status?: CampaignStatus) =>
    [...campaignKeys.all, 'list', merchantId, limit, offset, status] as const,
  detail: (merchantId: string, campaignId: string) =>
    [...campaignKeys.all, 'detail', merchantId, campaignId] as const,
  performance: (merchantId: string, campaignId: string, startDate: string, endDate: string) =>
    [...campaignKeys.all, 'performance', merchantId, campaignId, startDate, endDate] as const,
  attribution: (merchantId: string, campaignId: string, startDate: string, endDate: string) =>
    [...campaignKeys.all, 'attribution', merchantId, campaignId, startDate, endDate] as const,
  journeyCorrelation: (
    merchantId: string,
    campaignId: string,
    startDate: string,
    endDate: string
  ) =>
    [...campaignKeys.all, 'journeyCorrelation', merchantId, campaignId, startDate, endDate] as const,
  audience: (merchantId: string, campaignId: string) =>
    [...campaignKeys.all, 'audience', merchantId, campaignId] as const,
};

export const useCampaigns = (
  merchantId: string,
  limit = 50,
  offset = 0,
  status?: CampaignStatus
) => {
  return useQuery({
    queryKey: campaignKeys.list(merchantId, limit, offset, status),
    queryFn: () => campaignsApi.getCampaigns(merchantId, limit, offset, status),
    enabled: !!merchantId,
  });
};

export const useCampaign = (merchantId: string, campaignId: string) => {
  return useQuery({
    queryKey: campaignKeys.detail(merchantId, campaignId),
    queryFn: () => campaignsApi.getCampaign(merchantId, campaignId),
    enabled: !!merchantId && !!campaignId,
  });
};

export const useCampaignPerformance = (
  merchantId: string,
  campaignId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: campaignKeys.performance(merchantId, campaignId, startDate, endDate),
    queryFn: () =>
      campaignsApi.getCampaignPerformance(merchantId, campaignId, startDate, endDate),
    enabled: !!merchantId && !!campaignId && !!startDate && !!endDate,
  });
};

export const useCampaignAttribution = (
  merchantId: string,
  campaignId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: campaignKeys.attribution(merchantId, campaignId, startDate, endDate),
    queryFn: () =>
      campaignsApi.getCampaignAttribution(merchantId, campaignId, startDate, endDate),
    enabled: !!merchantId && !!campaignId && !!startDate && !!endDate,
  });
};

export const useCampaignJourneyCorrelation = (
  merchantId: string,
  campaignId: string,
  startDate: string,
  endDate: string
) => {
  return useQuery({
    queryKey: campaignKeys.journeyCorrelation(merchantId, campaignId, startDate, endDate),
    queryFn: () =>
      campaignsApi.getCampaignJourneyCorrelation(merchantId, campaignId, startDate, endDate),
    enabled: !!merchantId && !!campaignId && !!startDate && !!endDate,
  });
};

export const useCampaignAudience = (merchantId: string, campaignId: string) => {
  return useQuery({
    queryKey: campaignKeys.audience(merchantId, campaignId),
    queryFn: () => campaignsApi.getCampaignAudience(merchantId, campaignId),
    enabled: !!merchantId && !!campaignId,
  });
};

