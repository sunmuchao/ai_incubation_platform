// API 服务层 - 对接后端 AI Native 接口

// ==================== 核心 API ====================

import apiClient from './apiClient'
import { authStorage, devStorage } from '../utils/storage'
import type {
  ConversationMatchRequest,
  ConversationMatchResponse,
  DailyRecommendResponse,
  RelationshipAnalysisRequest,
  RelationshipAnalysisResponse,
  TopicSuggestionRequest,
  TopicSuggestionResponse,
  CompatibilityAnalysis,
  MatchCandidate,
  StreamChunk,
} from '../types'

export const conversationMatchingApi = {
  /**
   * 对话式匹配 - 用户通过自然语言表达匹配需求
   */
  async match(request: ConversationMatchRequest): Promise<ConversationMatchResponse> {
    const response = await apiClient.post('/api/conversation-matching/match', request)
    return response.data
  },

  /**
   * 对话式匹配 - 流式响应版本
   */
  async matchStream(
    request: ConversationMatchRequest,
    onChunk: (chunk: StreamChunk) => void
  ): Promise<void> {
    const token = authStorage.getToken()
    const testUserId = devStorage.getTestUserId() || 'user-test-001'

    const response = await fetch('/api/conversation-matching/match-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : { 'X-Dev-User-Id': testUserId }),
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('ReadableStream not supported')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留不完整的一行

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const chunk: StreamChunk = JSON.parse(line.slice(6))
            onChunk(chunk)
          } catch (e) {
            console.error('Failed to parse stream chunk:', e)
          }
        }
      }
    }
  },

  /**
   * 每日自主推荐 - AI 主动分析用户状态，推送每日匹配
   */
  async dailyRecommend(): Promise<DailyRecommendResponse> {
    const response = await apiClient.get('/api/conversation-matching/daily-recommend')
    return response.data
  },

  /**
   * 关系健康度分析
   */
  async analyzeRelationship(
    request: RelationshipAnalysisRequest
  ): Promise<RelationshipAnalysisResponse> {
    const response = await apiClient.post('/api/conversation-matching/relationship/analyze', request)
    return response.data
  },

  /**
   * 获取关系状态
   */
  async getRelationshipStatus(matchId: string) {
    const response = await apiClient.get(`/api/conversation-matching/relationship/${matchId}/status`)
    return response.data
  },

  /**
   * 智能话题推荐
   */
  async suggestTopics(request: TopicSuggestionRequest): Promise<TopicSuggestionResponse> {
    const response = await apiClient.post('/api/conversation-matching/topics/suggest', request)
    return response.data
  },

  /**
   * 兼容性分析
   */
  async getCompatibility(targetUserId: string): Promise<CompatibilityAnalysis> {
    const response = await apiClient.get(`/api/conversation-matching/compatibility/${targetUserId}`)
    return response.data
  },

  /**
   * 获取 AI 主动推送
   */
  async getAiPushRecommendations() {
    const response = await apiClient.get('/api/conversation-matching/ai/push/recommendations')
    return response.data
  },
}

// AI 感知 API - 全知感知系统
export const aiAwarenessApi = {
  /**
   * 获取 AI 全知感知数据
   */
  async getOmniscientAwareness(userId: string) {
    const response = await apiClient.get(`/api/ai/awareness?user_id=${userId}`)
    return response.data
  },

  /**
   * 获取主动洞察
   */
  async getActiveInsights(userId: string) {
    const response = await apiClient.get(`/api/ai/awareness/insights?user_id=${userId}`)
    return response.data
  },

  /**
   * 获取 AI 主动建议
   */
  async getProactiveSuggestion(userId: string) {
    const response = await apiClient.get(`/api/ai/awareness/suggestion?user_id=${userId}`)
    return response.data
  },

  /**
   * 获取行为模式
   */
  async getBehaviorPatterns(userId: string) {
    const response = await apiClient.get(`/api/ai/awareness/patterns?user_id=${userId}`)
    return response.data
  },

  /**
   * 获取 AI 旁白
   */
  async getAiCommentary(userId: string) {
    const response = await apiClient.get(`/api/ai/awareness/commentary?user_id=${userId}`)
    return response.data
  },

  /**
   * 追踪行为事件
   */
  async trackBehavior(
    userId: string,
    eventType: string,
    targetId?: string,
    eventData?: Record<string, any>
  ) {
    const response = await apiClient.post(
      `/api/ai/awareness/track?user_id=${userId}&event_type=${eventType}${targetId ? `&target_id=${targetId}` : ''}`,
      eventData || {}
    )
    return response.data
  },

  /**
   * 追踪查看资料
   */
  async trackProfileView(viewerId: string, profileId: string) {
    const response = await apiClient.post(
      `/api/ai/awareness/track/profile-view?user_id=${viewerId}&profile_id=${profileId}`
    )
    return response.data
  },

  /**
   * 追踪滑动行为
   */
  async trackSwipe(userId: string, targetId: string, action: 'like' | 'pass' | 'super_like') {
    const response = await apiClient.post(
      `/api/ai/awareness/track/swipe?user_id=${userId}&target_id=${targetId}&action=${action}`
    )
    return response.data
  },

  /**
   * 追踪聊天消息
   */
  async trackChatMessage(senderId: string, receiverId: string, contentLength: number) {
    const response = await apiClient.post(
      `/api/ai/awareness/track/chat-message?sender_id=${senderId}&receiver_id=${receiverId}&content_length=${contentLength}`
    )
    return response.data
  },
}

export const matchingApi = {
  /**
   * 获取推荐匹配列表
   */
  async getRecommendations(
    limit = 15,
    filters?: { age_min?: number; age_max?: number; distance?: number }
  ): Promise<MatchCandidate[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (filters?.age_min) params.append('age_min', filters.age_min.toString())
    if (filters?.age_max) params.append('age_max', filters.age_max.toString())
    if (filters?.distance) params.append('distance', filters.distance.toString())

    const response = await apiClient.get(`/api/matching/recommend`, { params })
    return response.data
  },

  /**
   * 滑动操作
   */
  async swipe(targetUserId: string, action: 'like' | 'pass' | 'super_like') {
    const response = await apiClient.post('/api/matching/swipe', {
      target_user_id: targetUserId,
      action,
    })
    return response.data
  },

  /**
   * 获取匹配列表
   */
  async getMatches(userId: string, limit = 10) {
    const response = await apiClient.get(`/api/matching/${userId}/matches`, {
      params: { limit },
    })
    return response.data
  },
}

export const chatApi = {
  /**
   * 获取会话列表
   */
  async getConversations() {
    const response = await apiClient.get('/api/chat/conversations')
    return response.data
  },

  /**
   * 获取聊天历史
   */
  async getHistory(otherUserId: string, limit = 50, offset = 0) {
    const response = await apiClient.get(`/api/chat/history/${otherUserId}`, {
      params: { limit, offset },
    })
    return response.data
  },

  /**
   * 发送消息
   */
  async sendMessage(data: { receiver_id: string; content: string; message_type?: string }) {
    const response = await apiClient.post('/api/chat/send', data)
    return response.data
  },

  /**
   * 模拟回复 (开发环境)
   */
  async simulateReply(conversationId: string, userMessage: string) {
    const response = await apiClient.post('/api/chat/simulate-reply', {}, {
      params: {
        conversation_id: conversationId,
        user_message: userMessage,
      },
    })
    return response.data
  },

  /**
   * 标记消息已读
   */
  async markMessageRead(messageId: string) {
    const response = await apiClient.post(`/api/chat/read/message/${messageId}`)
    return response.data
  },
}

export const userApi = {
  /**
   * 登录
   */
  async login(username: string, password: string) {
    const response = await apiClient.post('/api/users/login', {
      username,
      password,
    })
    return response.data
  },

  /**
   * 注册
   */
  async register(userData: {
    username: string
    password: string
    email: string
    name: string
    age: number
    gender: string
    location: string
    bio: string
    interests: string[]
  }) {
    const response = await apiClient.post('/api/users/register', userData)
    return response.data
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser() {
    const response = await apiClient.get('/api/users/me')
    return response.data
  },

  /**
   * 忘记密码 - 发送重置邮件
   */
  async forgotPassword(email: string) {
    const response = await apiClient.post('/api/users/forgot-password', { email })
    return response.data
  },

  /**
   * 重置密码 - 使用 token 设置新密码
   */
  async resetPassword(token: string, newPassword: string) {
    const response = await apiClient.post('/api/users/reset-password', {
      token,
      new_password: newPassword,
    })
    return response.data
  },

  /**
   * 登出 - 撤销 refresh token
   */
  async logout(refreshToken: string) {
    const response = await apiClient.post('/api/users/logout', {
      refresh_token: refreshToken,
    })
    return response.data
  },
}

export const registrationConversationApi = {
  /**
   * 开始注册对话
   */
  async startConversation(userId: string, userName: string) {
    const response = await apiClient.post('/api/registration-conversation/start', {
      user_id: userId,
      user_name: userName,
    })
    return response.data
  },

  /**
   * 发送对话消息
   */
  async sendMessage(userId: string, message: string) {
    const response = await apiClient.post('/api/registration-conversation/message', {
      user_id: userId,
      message,
    })
    return response.data
  },

  /**
   * 获取会话状态
   */
  async getSession(userId: string) {
    const response = await apiClient.get(`/api/registration-conversation/session/${userId}`)
    return response.data
  },

  /**
   * 完成对话
   */
  async completeConversation(userId: string) {
    const response = await apiClient.post(`/api/registration-conversation/complete/${userId}`)
    return response.data
  },
}

// ==================== P10-P17 API 导出 ====================

// P10: 关系里程碑、约会建议、双人互动游戏
export * from './p10_api'

// P13: 情感调解增强
export * from './p13_api'

// P14: 实战演习
export * from './p14_api'

// P15-P17: 虚实结合、圈子融合、终极共振
export * from './p15_p16_p17_api'

// Profile Collection API - AI Native 用户画像收集
export { profileApi } from './profileApi'
export type {
  QuestionOption,
  QuestionCard,
  ProfileQuestionRequest,
  ProfileQuestionResponse,
  ProfileAnswerRequest,
  ProfileAnswerResponse,
} from './profileApi'
