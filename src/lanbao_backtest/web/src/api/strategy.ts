import { apiClient } from './client';
import type { StrategyTemplate } from '../types/backtest';

export const strategyApi = {
  list: async () => {
    const { data } = await apiClient.get<{ strategies: StrategyTemplate[] }>('/strategies');
    return data.strategies;
  },
};
