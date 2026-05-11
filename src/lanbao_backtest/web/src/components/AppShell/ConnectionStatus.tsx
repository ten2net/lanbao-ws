import { Badge, Tooltip } from 'antd';
import { useWSStore } from '../../stores/wsStore';
import type { ConnectionState } from '../../types/ros2';

const statusConfig: Record<ConnectionState, { color: string; text: string }> = {
  connected: { color: 'green', text: '在线' },
  connecting: { color: 'yellow', text: '连接中' },
  reconnecting: { color: 'orange', text: '重连中' },
  disconnected: { color: 'red', text: '离线' },
};

export function ConnectionStatus() {
  const connectionState = useWSStore((state) => state.connectionState);
  const config = statusConfig[connectionState];

  return (
    <Tooltip title={`ROS2 WebSocket: ${config.text}`}>
      <Badge color={config.color} text={config.text} />
    </Tooltip>
  );
}
