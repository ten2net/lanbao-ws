import { apiClient } from './client';

export interface FavorCondition {
  id?: number;
  name: string;
  query: string;
  description: string;
  enabled: boolean;
  priority: number;
  max_results: number;
  filter_hot_sector: boolean;
  filter_min_cap_yi?: number;
}

export interface WatchlistItem {
  code: string;
  name: string;
  account_id: string;
  group_name: string;
  source_condition: string;
  signal_type: string;
  confidence: number;
  added_at: string;
}

export interface PickRequest {
  condition_names?: string[];
  clear_existing?: boolean;
  account_id?: string;
}

export interface PickResponse {
  success: boolean;
  message: string;
  total_unique: number;
  added: number;
  existing: number;
  codes: string[];
  stocks: { code: string; name: string }[];
}

export interface EastMoneyWatchlistItem {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  high: number;
  low: number;
}

export interface EastMoneyGroup {
  id: string;
  name: string;
}

export interface EastMoneySyncResponse {
  success: boolean;
  message: string;
  synced: number;
}

export const favorApi = {
  pick: (params: PickRequest) =>
    apiClient.post<PickResponse>('/favor/pick', params).then(r => r.data),

  getWatchlist: (account_id?: string, group_name?: string) =>
    apiClient.get<{ items: WatchlistItem[] }>('/favor/watchlist', {
      params: { account_id, group_name }
    }).then(r => r.data),

  addToWatchlist: (item: { code: string; name?: string; account_id?: string; group_name?: string; source_condition?: string }) =>
    apiClient.post('/favor/watchlist', item).then(r => r.data),

  removeFromWatchlist: (code: string, account_id?: string, group_name?: string) =>
    apiClient.delete(`/favor/watchlist/${code}`, {
      params: { account_id, group_name }
    }).then(r => r.data),

  getEastMoneyWatchlist: (group_name?: string) =>
    apiClient.get<{ items: EastMoneyWatchlistItem[]; group_name: string }>('/favor/eastmoney/watchlist', {
      params: { group_name }
    }).then(r => r.data),

  getEastMoneyGroups: () =>
    apiClient.get<{ groups: EastMoneyGroup[] }>('/favor/eastmoney/groups').then(r => r.data),

  syncToEastMoney: (sys_group?: string, em_group?: string) =>
    apiClient.post<EastMoneySyncResponse>('/favor/eastmoney/sync', null, {
      params: { sys_group, em_group }
    }).then(r => r.data),

  listConditions: () =>
    apiClient.get<{ conditions: FavorCondition[] }>('/favor/conditions').then(r => r.data),

  saveCondition: (condition: FavorCondition) =>
    apiClient.post('/favor/conditions', condition).then(r => r.data),

  deleteCondition: (id: number) =>
    apiClient.delete(`/favor/conditions/${id}`).then(r => r.data),
};
