import { apiClient } from '@/services/apiClient';

export interface HealthCheckResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface DatabaseHealthResponse {
  status: string;
  database: string;
  latencyMs: number;
}

export const systemService = {
  getHealth: async (): Promise<HealthCheckResponse> => {
    const response = await apiClient.get<HealthCheckResponse>('/health');
    return response.data;
  },

  getDbHealth: async (): Promise<DatabaseHealthResponse> => {
    const response = await apiClient.get<DatabaseHealthResponse>('/health/db');
    return response.data;
  },
};
