import { apiClient } from './client';
import type { SystemConfig } from '../types/config';

export const configApi = {
  get: async () => {
    const { data } = await apiClient.get<SystemConfig>('/config');
    return data;
  },

  update: async (config: SystemConfig) => {
    const { data } = await apiClient.put<SystemConfig>('/config', config);
    return data;
  },
};
