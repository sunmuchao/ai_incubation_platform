/**
 * AI Native API 客户端
 * 对接后端 AI 功能接口
 */

import { API_BASE_URL } from './api';
import type {
  ChatMessage,
  ConversationState,
  GenerativeUIResponse,
  DecisionVisualization,
  AIAgent,
  FeedItem,
  AuthorType,
  DashboardWidget,
  TransparencyStats,
  Reputation,
  Notification,
} from '@/types/ai-native';

const AI_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8007';

interface RequestOptions extends RequestInit {
  timeout?: number;
}

async function request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = `${AI_BASE_URL}${endpoint}`;
  const timeout = options?.timeout || 30000;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return response.json();
    }

    return {} as T;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

/**
 * AI Agent Chat API
 */
export const agentChatApi = {
  /** 与 AI Agent 对话 */
  async chat(
    userId: string,
    message: string,
    conversationId?: string,
    context?: Record<string, any>
  ) {
    return request<{
      conversation_id: string;
      message: ChatMessage;
      suggested_actions: any[];
      metadata: Record<string, any>;
    }>('/api/v2/chat', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        message,
        conversation_id: conversationId,
        context,
      }),
    });
  },

  /** 获取对话历史 */
  async getConversation(conversationId: string) {
    return request<ConversationState>(`/api/v2/chat/${conversationId}`);
  },

  /** 获取聊天历史（分页） */
  async getChatHistory(conversationId: string, limit: number = 50) {
    return request<{ messages: ChatMessage[]; total_count: number }>(
      `/api/v2/chat/${conversationId}/history?limit=${limit}`
    );
  },

  /** 删除对话 */
  async deleteConversation(conversationId: string) {
    return request<{ message: string }>(`/api/v2/chat/${conversationId}`, {
      method: 'DELETE',
    });
  },
};

/**
 * Generative UI API
 */
export const generativeUiApi = {
  /** 获取内容流（带人机身份标识） */
  async getContentFeed(
    limit: number = 20,
    authorType?: AuthorType
  ) {
    const params = new URLSearchParams();
    params.set('limit', limit.toString());
    if (authorType) params.set('author_type', authorType);
    return request<GenerativeUIResponse>(`/api/v2/ui/content-feed?${params.toString()}`);
  },

  /** 获取决策过程可视化 */
  async getDecisionVisualization(traceId: string) {
    return request<DecisionVisualization>(`/api/v2/ui/decision/${traceId}`);
  },

  /** 获取透明度仪表盘 */
  async getTransparencyDashboard(period: string = 'current_month') {
    return request<GenerativeUIResponse>(
      `/api/v2/ui/transparency-dashboard?period=${period}`
    );
  },

  /** 获取 AI Agent 状态 */
  async getAgentStatus() {
    return request<{ agents: AIAgent[] }>('/api/v2/ui/agent-status');
  },

  /** 获取推荐组件 */
  async getRecommendationWidgets(userId: string) {
    return request<{
      widgets: DashboardWidget[];
      layout: Record<string, any>;
    }>(`/api/v2/ui/recommendation-widgets?user_id=${userId}`);
  },
};

/**
 * AI Features API
 */
export const aiFeaturesApi = {
  /** AI 版主自动处理举报 */
  async autoProcessReports(batchSize: number = 50) {
    return request<{ success: boolean; stats: any }>('/api/ai/moderator/auto-process', {
      method: 'POST',
      body: JSON.stringify({ batch_size: batchSize }),
    });
  },

  /** 获取 AI 版主统计 */
  async getModeratorStats() {
    return request<{ success: boolean; stats: any }>('/api/ai/moderator/stats');
  },

  /** AI 润色内容 */
  async polishContent(content: string, style: string = 'formal', userId?: string) {
    return request<{ success: boolean; data: any }>('/api/ai/assist/polish', {
      method: 'POST',
      body: JSON.stringify({ content, style, user_id: userId }),
    });
  },

  /** AI 扩写内容 */
  async expandContent(
    content: string,
    direction: string = 'detail',
    targetLength?: number,
    userId?: string
  ) {
    return request<{ success: boolean; data: any }>('/api/ai/assist/expand', {
      method: 'POST',
      body: JSON.stringify({ content, direction, target_length: targetLength, user_id: userId }),
    });
  },

  /** AI 翻译内容 */
  async translateContent(
    content: string,
    targetLang: string = 'en',
    userId?: string
  ) {
    return request<{ success: boolean; data: any }>('/api/ai/assist/translate', {
      method: 'POST',
      body: JSON.stringify({ content, target_lang: targetLang, user_id: userId }),
    });
  },

  /** AI 摘要内容 */
  async summarizeContent(content: string, maxLength: number = 200, userId?: string) {
    return request<{ success: boolean; data: any }>('/api/ai/assist/summarize', {
      method: 'POST',
      body: JSON.stringify({ content, max_length: maxLength, user_id: userId }),
    });
  },

  /** AI 生成内容 */
  async generateContent(
    topic: string,
    style: string = 'normal',
    length: string = 'medium',
    userId?: string
  ) {
    return request<{ success: boolean; data: any; ai_generated: boolean; badge: string }>(
      '/api/ai/assist/generate',
      {
        method: 'POST',
        body: JSON.stringify({ topic, style, length, user_id: userId }),
      }
    );
  },

  /** 获取写作建议 */
  async getWritingSuggestions(content: string, userId?: string) {
    return request<{ success: boolean; data: any }>('/api/ai/assist/suggest', {
      method: 'POST',
      body: JSON.stringify({ content, user_id: userId }),
    });
  },

  /** 获取 AI 辅助历史 */
  async getAssistHistory(userId?: string, limit: number = 20) {
    return request<{ success: boolean; history: any[] }>(
      `/api/ai/assist/history?${userId ? `user_id=${userId}&` : ''}limit=${limit}`
    );
  },

  /** 个性化推荐 */
  async getPersonalizedRecommendations(
    userId: string,
    limit: number = 20,
    excludeRead: boolean = true
  ) {
    return request<{ success: boolean; recommendations: any[]; algorithm: string }>(
      '/api/ai/recommend/personalized',
      {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, limit, exclude_read: excludeRead }),
      }
    );
  },

  /** 热门推荐 */
  async getHotRecommendations(limit: number = 20, timeRange: string = '24h') {
    return request<{ success: boolean; recommendations: any[]; time_range: string }>(
      `/api/ai/recommend/hot?limit=${limit}&time_range=${timeRange}`
    );
  },

  /** 相似内容推荐 */
  async getSimilarContent(postId: string, limit: number = 10) {
    return request<{ success: boolean; recommendations: any[]; source_post_id: string }>(
      `/api/ai/recommend/similar/${postId}?limit=${limit}`
    );
  },
};

/**
 * Reputation API
 */
export const reputationApi = {
  /** 获取当前用户声誉 */
  async getMyReputation() {
    return request<Reputation>('/api/reputation/me');
  },

  /** 获取成员声誉 */
  async getMemberReputation(memberId: string) {
    return request<Reputation>(`/api/reputation/${memberId}`);
  },

  /** 获取声誉排行榜 */
  async getRanking(
    rankingType: string = 'overall',
    memberType?: string,
    limit: number = 100,
    offset: number = 0
  ) {
    const params = new URLSearchParams();
    params.set('ranking_type', rankingType);
    if (memberType) params.set('member_type', memberType);
    params.set('limit', limit.toString());
    params.set('offset', offset.toString());
    return request<{ rankings: any[]; total: number }>(`/api/reputation/ranking?${params.toString()}`);
  },

  /** 获取行为日志 */
  async getBehaviorLogs(
    memberId?: string,
    isPositive?: boolean,
    dimension?: string,
    limit: number = 50,
    offset: number = 0
  ) {
    const params = new URLSearchParams();
    if (memberId) params.set('member_id', memberId);
    if (isPositive !== undefined) params.set('is_positive', isPositive.toString());
    if (dimension) params.set('dimension', dimension);
    params.set('limit', limit.toString());
    params.set('offset', offset.toString());
    return request<{ logs: any[]; total: number }>(`/api/reputation/behavior-logs?${params.toString()}`);
  },
};

/**
 * Feed API
 */
export const feedApi = {
  /** 获取个性化 Feed */
  async getPersonalizedFeed(userId: string, limit: number = 20, offset: number = 0) {
    return request<any>(
      `/api/feed/personalized?user_id=${userId}&limit=${limit}&offset=${offset}`
    );
  },

  /** 获取实时热榜 */
  async getTrendingFeed(
    channelId?: string,
    tag?: string,
    timeRange: string = '2h',
    limit: number = 20
  ) {
    const params = new URLSearchParams();
    if (channelId) params.set('channel_id', channelId);
    if (tag) params.set('tag', tag);
    params.set('time_range', timeRange);
    params.set('limit', limit.toString());
    return request<any>(`/api/feed/trending?${params.toString()}`);
  },

  /** 分析 Feed 多样性 */
  async analyzeFeedDiversity(userId: string, limit: number = 20) {
    return request<{
      author_diversity: number;
      channel_diversity: number;
      ai_human_ratio: number;
      tag_diversity: number;
      recommendations: string[];
    }>(`/api/feed/diversity?user_id=${userId}&limit=${limit}`);
  },
};

/**
 * Notifications API
 */
export const notificationsApi = {
  /** 获取用户通知 */
  async getUserNotifications(userId: string, limit: number = 50, status?: string) {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    return request<{ notifications: Notification[]; total: number }>(
      `/api/notifications/user/${userId}?limit=${limit}&${params.toString()}`
    );
  },

  /** 获取未读数量 */
  async getUnreadCount(userId: string) {
    return request<{ unread_count: number }>(
      `/api/notifications/user/${userId}/unread-count`
    );
  },

  /** 标记为已读 */
  async markAsRead(userId: string, notificationId: string) {
    return request<{ success: boolean; notification_id: string }>(
      `/api/notifications/user/${userId}/mark-as-read/${notificationId}`,
      { method: 'POST' }
    );
  },

  /** 标记所有为已读 */
  async markAllAsRead(userId: string) {
    return request<{ success: boolean; marked_count: number }>(
      `/api/notifications/user/${userId}/mark-all-as-read`,
      { method: 'POST' }
    );
  },
};

// 导出统一的 API 对象
export const aiApi = {
  chat: agentChatApi,
  ui: generativeUiApi,
  features: aiFeaturesApi,
  reputation: reputationApi,
  feed: feedApi,
  notifications: notificationsApi,
};
