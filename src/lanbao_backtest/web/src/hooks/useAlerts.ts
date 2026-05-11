import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { SystemAlertMsg } from '../types/ros2';

const MAX_ALERTS = 100;

export function useAlerts(): void {
  const setAlerts = useMonitorStore((state) => state.setAlerts);

  const onMessage = useCallback(
    (msg: SystemAlertMsg) => {
      setAlerts((prev) => {
        // 去重：相同 component + 相同 timestamp
        const filtered = prev.filter(
          (a) => !(a.component === msg.component && a.timestamp === msg.timestamp)
        );
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

  useROSTopic<SystemAlertMsg>('/system/alerts', onMessage);
}
