import { create } from 'zustand';
import type { NodeStatusMsg, RiskAlertMsg, SystemMetricsMsg } from '../types/ros2';

interface MonitorState {
  nodes: NodeStatusMsg[];
  alerts: RiskAlertMsg[];
  metricsHistory: SystemMetricsMsg[];
  setNodes: (updater: (prev: NodeStatusMsg[]) => NodeStatusMsg[]) => void;
  setAlerts: (updater: (prev: RiskAlertMsg[]) => RiskAlertMsg[]) => void;
  addMetric: (metric: SystemMetricsMsg) => void;
}

const MAX_HISTORY = 360; // 30分钟 × 12条/分钟 (5秒间隔)

export const useMonitorStore = create<MonitorState>((set) => ({
  nodes: [],
  alerts: [],
  metricsHistory: [],
  setNodes: (updater) => set((state) => ({ nodes: updater(state.nodes) })),
  setAlerts: (updater) => set((state) => ({ alerts: updater(state.alerts) })),
  addMetric: (metric) =>
    set((state) => {
      const next = [...state.metricsHistory, metric];
      if (next.length > MAX_HISTORY) next.shift();
      return { metricsHistory: next };
    }),
}));
