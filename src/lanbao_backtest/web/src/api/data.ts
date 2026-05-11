import { apiClient } from './client';
import type { DataSummary, DataTableInfo, SyncTask, QualityReport, TablePreview } from '../types/data';

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
};
