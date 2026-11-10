import { apiClient } from './client';
import type {
  PaginatedResponse,
  ShopperResponse,
  ShopperProfileResponse,
  ShopperJourneyResponse,
  ShopperJourneyDetailResponse,
  ShopperSegmentMembershipResponse,
  ShopperActivityEventResponse,
  OrderResponse,
} from '../types';

export const shoppersApi = {
  getShopper: (merchantId: string, shopperId: string) => {
    return apiClient.get<ShopperResponse>(`/api/v1/merchants/${merchantId}/shoppers/${shopperId}`);
  },

  getShopperProfile: (merchantId: string, shopperId: string) => {
    return apiClient.get<ShopperProfileResponse>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/profile`
    );
  },

  getShopperJourneys: (merchantId: string, shopperId: string) => {
    return apiClient.get<ShopperJourneyResponse[]>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/journeys`
    );
  },

  getShopperJourneyDetail: (merchantId: string, shopperId: string, journeyId: string) => {
    return apiClient.get<ShopperJourneyDetailResponse>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/journeys/${journeyId}`
    );
  },

  getShopperOrders: (merchantId: string, shopperId: string, limit = 50, offset = 0) => {
    return apiClient.get<PaginatedResponse<OrderResponse>>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/orders`,
      { limit, offset }
    );
  },

  getShopperSegments: (merchantId: string, shopperId: string) => {
    return apiClient.get<ShopperSegmentMembershipResponse[]>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/segments`
    );
  },

  getShopperActivity: (
    merchantId: string,
    shopperId: string,
    limit = 50,
    offset = 0,
    startDate?: string,
    endDate?: string
  ) => {
    const params: Record<string, string | number> = { limit, offset };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    return apiClient.get<PaginatedResponse<ShopperActivityEventResponse>>(
      `/api/v1/merchants/${merchantId}/shoppers/${shopperId}/activity`,
      params
    );
  },
};

