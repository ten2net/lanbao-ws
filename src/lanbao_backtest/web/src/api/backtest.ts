import { apiClient } from './client';
import type {
  BacktestListResponse,
  BacktestDetail,
  BacktestFilters,
  EquityPoint,
  Trade,
  MonthlyMatrix,
  RunBacktestRequest,
} from '../types/backtest';

export const backtestApi = {
  list: async (filters: BacktestFilters, page = 1, limit = 20) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('limit', String(limit));
    if (filters.strategy) params.set('strategy', filters.strategy);
    if (filters.symbol) params.set('symbol', filters.symbol);
    if (filters.tags.length > 0) params.set('tag', filters.tags[0]);
    const { data } = await apiClient.get<BacktestListResponse>(`/backtests?${params}`);
    return data;
  },

  get: async (backtestId: string) => {
    const { data } = await apiClient.get<BacktestDetail>(`/backtests/${backtestId}`);
    return data;
  },

  delete: async (backtestId: string) => {
    await apiClient.delete(`/backtests/${backtestId}`);
  },

  run: async (request: RunBacktestRequest) => {
    const { data } = await apiClient.post('/backtest/run', request);
    return data;
  },

  getEquity: async (backtestId: string) => {
    const { data } = await apiClient.get<{ series: EquityPoint[] }>(`/backtests/${backtestId}/equity`);
    return data.series;
  },

  getTrades: async (backtestId: string) => {
    const { data } = await apiClient.get<{ trades: Trade[] }>(`/backtests/${backtestId}/trades`);
    return data.trades;
  },

  getMonthly: async (backtestId: string) => {
    const { data } = await apiClient.get<{ matrix: MonthlyMatrix }>(`/backtests/${backtestId}/monthly`);
    return data.matrix;
  },
};
