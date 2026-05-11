import { create } from 'zustand';
import type { ConnectionState } from '../types/ros2';

interface WSState {
  connectionState: ConnectionState;
  subscribedTopics: Set<string>;
  setConnectionState: (state: ConnectionState) => void;
  addSubscribedTopic: (topic: string) => void;
  removeSubscribedTopic: (topic: string) => void;
}

export const useWSStore = create<WSState>((set) => ({
  connectionState: 'disconnected',
  subscribedTopics: new Set(),
  setConnectionState: (connectionState) => set({ connectionState }),
  addSubscribedTopic: (topic) =>
    set((state) => {
      const newSet = new Set(state.subscribedTopics);
      newSet.add(topic);
      return { subscribedTopics: newSet };
    }),
  removeSubscribedTopic: (topic) =>
    set((state) => {
      const newSet = new Set(state.subscribedTopics);
      newSet.delete(topic);
      return { subscribedTopics: newSet };
    }),
}));
