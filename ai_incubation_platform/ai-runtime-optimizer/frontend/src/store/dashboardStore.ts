import { create } from 'zustand';
import type { DashboardOverview, Alert, Service, HealthScore } from '@/types';

interface DashboardState {
  overview: DashboardOverview | null;
  services: Service[];
  alerts: Alert[];
  healthScores: HealthScore[];
  loading: boolean;
  lastUpdated: Date | null;

  setOverview: (overview: DashboardOverview) => void;
  setServices: (services: Service[]) => void;
  setAlerts: (alerts: Alert[]) => void;
  setHealthScores: (scores: HealthScore[]) => void;
  setLoading: (loading: boolean) => void;
  refresh: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  overview: null,
  services: [],
  alerts: [],
  healthScores: [],
  loading: false,
  lastUpdated: null,

  setOverview: (overview) => set({ overview, lastUpdated: new Date() }),
  setServices: (services) => set({ services, lastUpdated: new Date() }),
  setAlerts: (alerts) => set({ alerts, lastUpdated: new Date() }),
  setHealthScores: (healthScores) => set({ healthScores, lastUpdated: new Date() }),
  setLoading: (loading) => set({ loading }),
  refresh: () => set({ lastUpdated: new Date() }),
}));

// 告警状态 Store
interface AlertState {
  unreadCount: number;
  acknowledgedAlerts: string[];

  setUnreadCount: (count: number) => void;
  acknowledgeAlert: (alertId: string) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  unreadCount: 0,
  acknowledgedAlerts: [],
  setUnreadCount: (count) => set({ unreadCount: count }),
  acknowledgeAlert: (alertId) =>
    set((state) => ({
      acknowledgedAlerts: [...state.acknowledgedAlerts, alertId],
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),
}));

// 设置 Store
interface SettingsState {
  refreshInterval: number;
  theme: 'dark' | 'light';
  notifications: {
    email: boolean;
    slack: boolean;
    dingtalk: boolean;
    wechat: boolean;
  };

  setRefreshInterval: (interval: number) => void;
  setTheme: (theme: 'dark' | 'light') => void;
  updateNotification: (channel: keyof SettingsState['notifications'], enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  refreshInterval: 30,
  theme: 'dark',
  notifications: {
    email: true,
    slack: false,
    dingtalk: true,
    wechat: false,
  },
  setRefreshInterval: (interval) => set({ refreshInterval: interval }),
  setTheme: (theme) => set({ theme }),
  updateNotification: (channel, enabled) =>
    set((state) => ({
      notifications: {
        ...state.notifications,
        [channel]: enabled,
      },
    })),
}));

export default useDashboardStore;
