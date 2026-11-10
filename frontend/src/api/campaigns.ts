import { apiClient } from './client';
import type {
  PaginatedResponse,
  CampaignStatus,
  CampaignSummaryResponse,
  CampaignDetailResponse,
  CampaignPerformanceDetailResult,
  CampaignAttributionResult,
  CampaignJourneyCorrelationResult,
  CampaignAudienceAnalysisResult,
} from '../types';

export const campaignsApi = {
  getCampaigns: (
    merchantId: string,
    limit = 50,
    offset = 0,
    status?: CampaignStatus
  ) => {
    return apiClient.get<PaginatedResponse<CampaignSummaryResponse>>(
      `/api/v1/merchants/${merchantId}/campaigns`,
      { limit, offset, status: status || undefined }
    );
  },

  getCampaign: (merchantId: string, campaignId: string) => {
    return apiClient.get<CampaignDetailResponse>(
      `/api/v1/merchants/${merchantId}/campaigns/${campaignId}`
    );
  },

  getCampaignPerformance: (
    merchantId: string,
    campaignId: string,
    startDate: string,
    endDate: string
  ) => {
    return apiClient.get<CampaignPerformanceDetailResult>(
      `/api/v1/merchants/${merchantId}/campaigns/${campaignId}/performance`,
      { start_date: startDate, end_date: endDate }
    );
  },

  getCampaignAttribution: (
    merchantId: string,
    campaignId: string,
    startDate: string,
    endDate: string
  ) => {
    return apiClient.get<CampaignAttributionResult>(
      `/api/v1/merchants/${merchantId}/campaigns/${campaignId}/attribution`,
      { start_date: startDate, end_date: endDate }
    );
  },

  getCampaignJourneyCorrelation: (
    merchantId: string,
    campaignId: string,
    startDate: string,
    endDate: string
  ) => {
    return apiClient.get<CampaignJourneyCorrelationResult>(
      `/api/v1/merchants/${merchantId}/campaigns/${campaignId}/journey-correlation`,
      { start_date: startDate, end_date: endDate }
    );
  },

  getCampaignAudience: (merchantId: string, campaignId: string) => {
    return apiClient.get<CampaignAudienceAnalysisResult>(
      `/api/v1/merchants/${merchantId}/campaigns/${campaignId}/audience`
    );
  },
};

