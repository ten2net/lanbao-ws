import { useCallback } from 'react';
import { useROSTopic } from './useROSTopic';
import { useMonitorStore } from '../stores/monitorStore';
import type { NodeStatusMsg } from '../types/ros2';

export function useNodeStatus(): void {
  const setNodes = useMonitorStore((state) => state.setNodes);

  const onMessage = useCallback(
    (msg: NodeStatusMsg) => {
      setNodes((prev) => {
        const filtered = prev.filter((n) => n.node_name !== msg.node_name);
        return [...filtered, msg];
      });
    },
    [setNodes],
  );

  useROSTopic<NodeStatusMsg>('/node/status', onMessage);
}
