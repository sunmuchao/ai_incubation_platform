/**
 * AI Native 服务
 *
 * 提供 AI 主动推送、实时通知等功能
 */
import { message } from 'antd';
import { wsService, WSMessage } from './websocket';

// 推送通知类型
export interface PushNotification {
  id: string;
  type: 'opportunity' | 'reminder' | 'achievement' | 'warning' | 'info';
  title: string;
  content: string;
  data?: Record<string, any>;
  timestamp: string;
  read: boolean;
  action?: {
    label: string;
    handler: () => void;
  };
}

// 主动建议类型
export interface AISuggestion {
  id: string;
  category: 'career' | 'skill' | 'opportunity' | 'performance';
  title: string;
  description: string;
  confidence: number;
  data?: Record<string, any>;
  actions?: Array<{
    action: string;
    label: string;
  }>;
}

// 机会推送数据
export interface OpportunityPushData {
  opportunity_id: string;
  type: 'promotion' | 'transfer' | 'project';
  title: string;
  department?: string;
  match_score: number;
  reason: string;
}

class AINativeService {
  private notifications: PushNotification[] = [];
  private suggestionListeners: Set<(suggestion: AISuggestion) => void> = new Set();
  private notificationListeners: Set<(notification: PushNotification) => void> = new Set();
  private connected = false;

  // 初始化服务
  async initialize(): Promise<void> {
    if (this.connected) return;

    try {
      await wsService.connect();
      this.connected = true;

      // 订阅机会推送
      wsService.on('opportunity_push', this.handleOpportunityPush);

      // 订阅 AI 建议
      wsService.on('ai_suggestion', this.handleAISuggestion);

      // 订阅通知
      wsService.on('notification', this.handleNotification);

      // 订阅 Agent 状态更新
      wsService.on('agent_status', this.handleAgentStatus);

      console.log('[AI Native] Service initialized');
    } catch (error) {
      console.error('[AI Native] Failed to initialize:', error);
    }
  }

  // 断开连接
  disconnect(): void {
    wsService.disconnect();
    this.connected = false;
    this.suggestionListeners.clear();
    this.notificationListeners.clear();
  }

  // 订阅 AI 建议
  onSuggestion(listener: (suggestion: AISuggestion) => void): () => void {
    this.suggestionListeners.add(listener);
    return () => this.suggestionListeners.delete(listener);
  }

  // 订阅通知
  onNotification(listener: (notification: PushNotification) => void): () => void {
    this.notificationListeners.add(listener);
    return () => this.notificationListeners.delete(listener);
  }

  // 获取未读通知
  getUnreadNotifications(): PushNotification[] {
    return this.notifications.filter(n => !n.read);
  }

  // 获取所有通知
  getNotifications(): PushNotification[] {
    return [...this.notifications];
  }

  // 标记通知为已读
  markAsRead(notificationId: string): void {
    const notification = this.notifications.find(n => n.id === notificationId);
    if (notification) {
      notification.read = true;
    }
  }

  // 标记所有通知为已读
  markAllAsRead(): void {
    this.notifications.forEach(n => n.read = true);
  }

  // 处理机会推送
  private handleOpportunityPush = (data: unknown): void => {
    const pushData = data as OpportunityPushData;
    const notification: PushNotification = {
      id: `opp-${Date.now()}`,
      type: 'opportunity',
      title: '新的工作机会',
      content: `AI 为您匹配到新机会：${pushData.title} (${pushData.match_score * 100}% 匹配)`,
      data: pushData,
      timestamp: new Date().toISOString(),
      read: false,
      action: {
        label: '立即查看',
        handler: () => {
          // 导航到机会详情页面
          window.location.hash = `/opportunities/${pushData.opportunity_id}`;
        }
      }
    };

    this.notifications.unshift(notification);
    this.notificationListeners.forEach(listener => listener(notification));

    // 显示通知
    message.info({
      content: notification.content,
      duration: 5,
      onClick: notification.action?.handler,
    });
  };

  // 处理 AI 建议
  private handleAISuggestion = (data: unknown): void => {
    const suggestion = data as AISuggestion;
    this.suggestionListeners.forEach(listener => listener(suggestion));

    // 高置信度建议显示通知
    if (suggestion.confidence >= 0.8) {
      message.info({
        content: `[AI 建议] ${suggestion.title}`,
        duration: 4,
      });
    }
  };

  // 处理通知
  private handleNotification = (data: unknown): void => {
    const notification = data as PushNotification;
    this.notifications.unshift(notification);
    this.notificationListeners.forEach(listener => listener(notification));

    // 根据类型显示不同样式的通知
    const methods: Record<string, any> = {
      opportunity: message.info,
      reminder: message.warning,
      achievement: message.success,
      warning: message.warning,
      info: message.info,
    };

    const method = methods[notification.type] || message.info;
    method({
      content: notification.content,
      duration: 4,
    });
  };

  // 处理 Agent 状态更新
  private handleAgentStatus = (data: unknown): void => {
    const statusData = data as { status: string; message?: string };
    console.log('[AI Native] Agent status updated:', statusData);
  };

  // 请求 AI 主动分析
  async requestProactiveAnalysis(userId: string): Promise<void> {
    if (!this.connected) {
      console.warn('[AI Native] Not connected');
      return;
    }

    wsService.send('request_analysis', {
      user_id: userId,
      analysis_types: ['career', 'skill', 'opportunity'],
    });
  }

  // 订阅主动推送
  async subscribeToPush(userId: string): Promise<void> {
    if (!this.connected) {
      console.warn('[AI Native] Not connected');
      return;
    }

    wsService.send('subscribe_push', {
      user_id: userId,
      push_types: ['opportunity', 'reminder', 'achievement'],
    });
  }
}

// 导出单例
export const aiNativeService = new AINativeService();
export default aiNativeService;
