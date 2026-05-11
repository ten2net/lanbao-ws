import { create } from 'zustand';
import type { SystemConfig } from '../types/config';

interface ConfigState {
  config: SystemConfig | null;
  isLoading: boolean;
  isSaving: boolean;
  setConfig: (config: SystemConfig | null) => void;
  setLoading: (loading: boolean) => void;
  setSaving: (saving: boolean) => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  isLoading: false,
  isSaving: false,
  setConfig: (config) => set({ config }),
  setLoading: (isLoading) => set({ isLoading }),
  setSaving: (isSaving) => set({ isSaving }),
}));
