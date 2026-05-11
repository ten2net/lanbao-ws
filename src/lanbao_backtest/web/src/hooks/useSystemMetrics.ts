import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { SystemMetricsMsg } from '../types/ros2';

export function useSystemMetrics(): void {
  const addMetric = useMonitorStore((state) => state.addMetric);

  const onMessage = useCallback(
    (msg: SystemMetricsMsg) => {
      addMetric(msg);
    },
    [addMetric],
  );

  useROSTopic<SystemMetricsMsg>('/system/metrics', onMessage);
}
