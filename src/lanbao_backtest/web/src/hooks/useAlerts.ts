import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { RiskAlertMsg } from '../types/ros2';

const MAX_ALERTS = 100;

export function useAlerts(): void {
  const setAlerts = useMonitorStore((state) => state.setAlerts);

  const onMessage = useCallback(
    (msg: RiskAlertMsg) => {
      setAlerts((prev) => {
        const filtered = prev.filter((a) => a.alert_id !== msg.alert_id);
        const next = [...filtered, msg];
        next.sort((a, b) => b.timestamp - a.timestamp);
        if (next.length > MAX_ALERTS) {
          next.length = MAX_ALERTS;
        }
        return next;
      });
    },
    [setAlerts],
  );

  useROSTopic<RiskAlertMsg>('/risk/alerts', onMessage);
}
