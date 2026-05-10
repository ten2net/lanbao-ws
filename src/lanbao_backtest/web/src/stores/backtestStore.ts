import { create } from 'zustand';
import type { BacktestFilters, BacktestListItem } from '../types/backtest';

interface BacktestState {
  backtests: BacktestListItem[];
  total: number;
  page: number;
  limit: number;
  filters: BacktestFilters;
  selectedIds: Set<string>;
  isLoading: boolean;
  isRunning: boolean;
  error: string | null;
  setBacktests: (backtests: BacktestListItem[], total: number) => void;
  setPage: (page: number) => void;
  setFilters: (filters: Partial<BacktestFilters>) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  setLoading: (loading: boolean) => void;
  setRunning: (running: boolean) => void;
  setError: (error: string | null) => void;
}

export const useBacktestStore = create<BacktestState>((set) => ({
  backtests: [], total: 0, page: 1, limit: 20,
  filters: { strategy: undefined, symbol: undefined, tags: [], dateRange: undefined },
  selectedIds: new Set(), isLoading: false, isRunning: false, error: null,
  setBacktests: (backtests, total) => set({ backtests, total }),
  setPage: (page) => set({ page }),
  setFilters: (partial) => set((state) => ({ filters: { ...state.filters, ...partial }, page: 1 })),
  toggleSelection: (id) => set((state) => {
    const newSet = new Set(state.selectedIds);
    newSet.has(id) ? newSet.delete(id) : newSet.add(id);
    return { selectedIds: newSet };
  }),
  clearSelection: () => set({ selectedIds: new Set() }),
  setLoading: (isLoading) => set({ isLoading }),
  setRunning: (isRunning) => set({ isRunning }),
  setError: (error) => set({ error }),
}));
