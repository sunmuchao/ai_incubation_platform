/**
 * AI Native 状态管理
 */

import { create } from 'zustand';
import type {
  ChatMessage,
  Diagnosis,
  WorkflowExecution,
  AIDashboardResponse,
  Alert,
  ServiceHealth,
  RecommendedAction,
} from '@/types';

// Agent 状态类型（内部使用）
export interface AgentStateItem {
  name: string;
  status: 'idle' | 'perceiving' | 'diagnosing' | 'remediating' | 'optimizing' | 'error';
  current_task?: string;
  progress?: number;
  last_activity: Date;
}

// ============================================================================
// Chat Store - 对话状态管理
// ============================================================================

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  currentDiagnosis: Diagnosis | null;
  suggestedActions: RecommendedAction[];

  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  setLoading: (loading: boolean) => void;
  setDiagnosis: (diagnosis: Diagnosis | null) => void;
  setSuggestedActions: (actions: RecommendedAction[]) => void;
  executeAction: (actionId: string) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  currentDiagnosis: null,
  suggestedActions: [],

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setLoading: (loading) => set({ isLoading: loading }),

  setDiagnosis: (diagnosis) => set({ currentDiagnosis: diagnosis }),

  setSuggestedActions: (actions) => set({ suggestedActions: actions }),

  executeAction: async (actionId) => {
    const actions = get().suggestedActions;
    const action = actions.find((a) => a.id === actionId);
    if (action) {
      // 添加到对话
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: `执行操作：${action.name}`,
        timestamp: new Date(),
      };
      get().addMessage(userMessage);

      // 这里应该调用 API 执行操作
      console.log('Executing action:', action);
    }
  },
}));

// ============================================================================
// Dashboard Store - 仪表板状态管理
// ============================================================================

interface DashboardState {
  dashboardData: AIDashboardResponse | null;
  services: ServiceHealth[];
  alerts: Alert[];
  loading: boolean;
  lastUpdated: Date | null;

  setDashboardData: (data: AIDashboardResponse) => void;
  setServices: (services: ServiceHealth[]) => void;
  setAlerts: (alerts: Alert[]) => void;
  setLoading: (loading: boolean) => void;
  refresh: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  dashboardData: null,
  services: [],
  alerts: [],
  loading: false,
  lastUpdated: null,

  setDashboardData: (data) => set({ dashboardData: data, lastUpdated: new Date() }),

  setServices: (services) => set({ services, lastUpdated: new Date() }),

  setAlerts: (alerts) => set({ alerts, lastUpdated: new Date() }),

  setLoading: (loading) => set({ loading }),

  refresh: () => set({ lastUpdated: new Date() }),
}));

// ============================================================================
// Agent Store - Agent 状态管理
// ============================================================================

interface AgentState {
  agents: AgentStateItem[];
  workflows: WorkflowExecution[];
  loading: boolean;

  setAgents: (agents: AgentStateItem[]) => void;
  setWorkflows: (workflows: WorkflowExecution[]) => void;
  updateAgentStatus: (agentName: string, status: AgentStateItem['status']) => void;
  addWorkflow: (workflow: WorkflowExecution) => void;
  updateWorkflow: (workflowId: string, updates: Partial<WorkflowExecution>) => void;
  setLoading: (loading: boolean) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  workflows: [],
  loading: false,

  setAgents: (agents) => set({ agents }),

  setWorkflows: (workflows) => set({ workflows }),

  updateAgentStatus: (agentName, status) =>
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.name === agentName ? { ...agent, status } : agent
      ),
    })),

  addWorkflow: (workflow) =>
    set((state) => ({
      workflows: [...state.workflows, workflow],
    })),

  updateWorkflow: (workflowId, updates) =>
    set((state) => ({
      workflows: state.workflows.map((wf) =>
        wf.id === workflowId ? { ...wf, ...updates } : wf
      ),
    })),

  setLoading: (loading) => set({ loading }),
}));

// ============================================================================
// Notification Store - 通知状态管理
// ============================================================================

interface NotificationState {
  notifications: Array<{
    id: string;
    type: 'info' | 'warning' | 'error' | 'success';
    title: string;
    message: string;
    timestamp: Date;
    read: boolean;
  }>;
  unreadCount: number;

  addNotification: (notification: {
    type: 'info' | 'warning' | 'error' | 'success';
    title: string;
    message: string;
  }) => void;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        {
          ...notification,
          id: Date.now().toString(),
          timestamp: new Date(),
          read: false,
        },
        ...state.notifications,
      ],
      unreadCount: state.unreadCount + 1,
    })),

  markAsRead: (notificationId) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
}));

// ============================================================================
// Settings Store - 设置状态管理
// ============================================================================

interface SettingsState {
  theme: 'dark' | 'light';
  autoRefresh: boolean;
  refreshInterval: number;
  aiAutoExecute: boolean;
  notificationsEnabled: boolean;

  setTheme: (theme: 'dark' | 'light') => void;
  setAutoRefresh: (enabled: boolean) => void;
  setRefreshInterval: (interval: number) => void;
  setAiAutoExecute: (enabled: boolean) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  theme: 'dark',
  autoRefresh: true,
  refreshInterval: 30,
  aiAutoExecute: false,
  notificationsEnabled: true,

  setTheme: (theme) => set({ theme }),
  setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
  setRefreshInterval: (interval) => set({ refreshInterval: interval }),
  setAiAutoExecute: (enabled) => set({ aiAutoExecute: enabled }),
  setNotificationsEnabled: (enabled) => set({ notificationsEnabled: enabled }),
}));

export default useChatStore;
