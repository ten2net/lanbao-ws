import { create } from 'zustand';
import type { DataSummary, DataTableInfo, SyncTask, QualityReport } from '../types/data';

interface DataState {
  summary: DataSummary | null;
  tables: DataTableInfo[];
  syncTasks: SyncTask[];
  quality: QualityReport[];
  setSummary: (summary: DataSummary | null) => void;
  setTables: (tables: DataTableInfo[]) => void;
  setSyncTasks: (syncTasks: SyncTask[]) => void;
  setQuality: (quality: QualityReport[]) => void;
}

export const useDataStore = create<DataState>((set) => ({
  summary: null,
  tables: [],
  syncTasks: [],
  quality: [],
  setSummary: (summary) => set({ summary }),
  setTables: (tables) => set({ tables }),
  setSyncTasks: (syncTasks) => set({ syncTasks }),
  setQuality: (quality) => set({ quality }),
}));
