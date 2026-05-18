import { apiClient } from './client';
import type { DataSummary, DataTableInfo, SyncTask, QualityReport, TablePreview } from '../types/data';

export interface KLineItem {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface KLineResponse {
  symbol: string;
  count: number;
  data: KLineItem[];
  has_history: boolean;
  has_today: boolean;
  today_debug?: string;
}

export const dataApi = {
  summary: async () => {
    const { data } = await apiClient.get<DataSummary>('/data/summary');
    return data;
  },

  tables: async () => {
    const { data } = await apiClient.get<DataTableInfo[]>('/data/tables');
    return data;
  },

  syncStatus: async () => {
    const { data } = await apiClient.get<SyncTask[]>('/data/sync');
    return data;
  },

  triggerSync: async (source?: string) => {
    const { data } = await apiClient.post<SyncTask>('/data/sync', { source });
    return data;
  },

  quality: async (table?: string) => {
    const params = new URLSearchParams();
    if (table) params.set('table', table);
    const { data } = await apiClient.get<QualityReport[]>(`/data/quality?${params}`);
    return data;
  },

  preview: async (tableName: string) => {
    const { data } = await apiClient.get<TablePreview>(`/data/preview/${encodeURIComponent(tableName)}`);
    return data;
  },

  getKLine: async (symbol: string, days: number = 30) => {
    const { data } = await apiClient.get<KLineResponse>(`/market/kline/${encodeURIComponent(symbol)}`, {
      params: { days },
    });
    return data;
  },
};
