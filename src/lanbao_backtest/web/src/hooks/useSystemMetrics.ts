import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { SystemMetricsMsg, NodeStatusMsg } from '../types/ros2';

export function useSystemMetrics(): void {
  const addMetric = useMonitorStore((state) => state.addMetric);
  const setNodes = useMonitorStore((state) => state.setNodes);

  const onMessage = useCallback(
    (msg: SystemMetricsMsg) => {
      addMetric(msg);

      // 将 system_metrics_node 加入节点状态列表，使其在监控面板可见
      const nodeStatus: NodeStatusMsg = {
        header: { stamp: msg.timestamp },
        node_name: 'system_metrics_node',
        node_type: 'system_metrics',
        status: 'RUNNING',
        cpu_usage: msg.cpu_percent,
        memory_usage: msg.memory_percent,
        message_count: 0,
        last_error: '',
        timestamp: msg.timestamp.sec * 1000 + Math.floor(msg.timestamp.nanosec / 1_000_000),
      };
      setNodes((prev) => {
        const filtered = prev.filter((n) => n.node_name !== nodeStatus.node_name);
        return [...filtered, nodeStatus];
      });
    },
    [addMetric, setNodes],
  );

  useROSTopic<SystemMetricsMsg>('/system/metrics', onMessage);
}
