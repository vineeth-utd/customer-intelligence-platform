import { apiClient } from './client';
import type { DevTokenRequest, DevTokenResponse, DevPrincipalsResponse } from '../types';

export const authApi = {
  getDevToken: (data: DevTokenRequest) => {
    return apiClient.post<DevTokenResponse>('/api/v1/auth/dev-token', data);
  },
  getDevPrincipals: () => {
    return apiClient.get<DevPrincipalsResponse>('/api/v1/auth/dev-principals');
  },
};

