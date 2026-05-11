export interface ROS2BridgeMessage {
  op: 'subscribe' | 'unsubscribe' | 'publish';
  topic: string;
  type?: string;
  msg?: unknown;
}

export interface ROS2BridgeEvent<T = unknown> {
  topic: string;
  msg: T;
  timestamp: number;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface SystemMetricsMsg {
  timestamp: { sec: number; nanosec: number };
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
  load_average_1m: number;
}

export interface NodeStatusMsg {
  header: { stamp: { sec: number; nanosec: number } };
  node_name: string;
  node_type: string;
  status: 'INITIALIZING' | 'RUNNING' | 'ERROR' | 'STOPPED';
  cpu_usage: number;
  memory_usage: number;
  message_count: number;
  last_error: string;
  timestamp: number;
}

export interface RiskAlertMsg {
  header: { stamp: { sec: number; nanosec: number } };
  alert_id: string;
  alert_type: 'POSITION' | 'DRAWDOWN' | 'VOLATILITY' | 'SYSTEM';
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
  current_value: number;
  threshold: number;
  affected_strategies: string[];
  timestamp: number;
}
