/**
 * rosbridge_suite WebSocket 客户端
 * 协议: rosbridge v2（与 ros2-web-bridge 兼容）
 * 启动后端: ros2 launch rosbridge_server rosbridge_websocket_launch.xml
 */
import { useWSStore } from '../stores/wsStore';
import type { ROS2BridgeMessage } from '../types/ros2';

const WS_URL = import.meta.env.VITE_ROS2_WS_URL || 'ws://localhost:9090';

const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;

export class ROS2WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = INITIAL_RECONNECT_DELAY;
  private subscribers = new Map<string, Set<(msg: unknown) => void>>();
  private pendingSubscriptions = new Set<string>();
  private isIntentionallyClosed = false;

  constructor() {
    this.connect();
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.CONNECTING || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    useWSStore.getState().setConnectionState('connecting');

    try {
      this.ws = new WebSocket(WS_URL);
    } catch {
      useWSStore.getState().setConnectionState('disconnected');
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectDelay = INITIAL_RECONNECT_DELAY;
      useWSStore.getState().setConnectionState('connected');
      this.resubscribeAll();
    };

    this.ws.onmessage = (event) => {
      let data: { topic?: string; msg?: unknown };
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      if (typeof data.topic === 'string' && data.msg !== undefined) {
        const callbacks = this.subscribers.get(data.topic);
        if (callbacks) {
          callbacks.forEach((cb) => cb(data.msg));
        }
      }
    };

    this.ws.onerror = () => {
      useWSStore.getState().setConnectionState('reconnecting');
    };

    this.ws.onclose = () => {
      useWSStore.getState().setConnectionState('disconnected');
      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    useWSStore.getState().setConnectionState('reconnecting');
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY);
  }

  private resubscribeAll(): void {
    for (const topic of this.pendingSubscriptions) {
      this.send({ op: 'subscribe', topic });
    }
  }

  private send(msg: ROS2BridgeMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  subscribe(topic: string, callback: (msg: unknown) => void): void {
    let callbacks = this.subscribers.get(topic);
    if (!callbacks) {
      callbacks = new Set();
      this.subscribers.set(topic, callbacks);
    }
    callbacks.add(callback);

    this.pendingSubscriptions.add(topic);
    useWSStore.getState().addSubscribedTopic(topic);
    this.send({ op: 'subscribe', topic });
  }

  unsubscribe(topic: string, callback: (msg: unknown) => void): void {
    const callbacks = this.subscribers.get(topic);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.subscribers.delete(topic);
        this.pendingSubscriptions.delete(topic);
        useWSStore.getState().removeSubscribedTopic(topic);
        this.send({ op: 'unsubscribe', topic });
      }
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    useWSStore.getState().setConnectionState('disconnected');
  }
}

export const ros2WS = new ROS2WebSocketManager();
