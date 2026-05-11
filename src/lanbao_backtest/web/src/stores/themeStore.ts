import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeMode, ThemeState } from '../types/theme';

function getInitialDark(mode: ThemeMode): boolean {
  if (mode === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return mode === 'dark';
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'auto',
      isDark: getInitialDark('auto'),
      setMode: (mode) => {
        set({ mode, isDark: getInitialDark(mode) });
      },
      toggle: () => {
        const currentMode = get().mode;
        const nextMode: ThemeMode = currentMode === 'dark' ? 'light' : 'dark';
        set({ mode: nextMode, isDark: getInitialDark(nextMode) });
      },
    }),
    {
      name: 'lanbao-theme',
      partialize: (state) => ({ mode: state.mode }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isDark = getInitialDark(state.mode);
        }
      },
    },
  ),
);

// Listen for system preference changes
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleChange = () => {
    const store = useThemeStore.getState();
    if (store.mode === 'auto') {
      useThemeStore.setState({ isDark: mediaQuery.matches });
    }
  };
  mediaQuery.addEventListener('change', handleChange);
}
