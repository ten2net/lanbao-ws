import { useEffect } from 'react';
import { ros2WS } from '../services/ros2WebSocket';

export function useROSTopic<T>(topic: string, onMessage: (msg: T) => void): void {
  useEffect(() => {
    ros2WS.subscribe(topic, onMessage as (msg: unknown) => void);
    return () => ros2WS.unsubscribe(topic, onMessage as (msg: unknown) => void);
  }, [topic, onMessage]);
}
