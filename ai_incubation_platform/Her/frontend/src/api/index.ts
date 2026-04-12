// API 服务层 - 对接后端 AI Native 接口

// ==================== 核心 API ====================

import apiClient from './apiClient'
import { authStorage } from '../utils/storage'
import { getCurrentUserId } from '../hooks/useCurrentUserId'
import { conversationMatchmakerSkill } from './skillClient'
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

// conversation_matching API 已删除，改用 conversationMatchmakerSkill
export const conversationMatchingApi = {
  /**
   * 对话式匹配 - 用户通过自然语言表达匹配需求
   * 改用 Skill 调用
   */
  async match(request: ConversationMatchRequest): Promise<ConversationMatchResponse> {
    const userId = getCurrentUserId()
    const result = await conversationMatchmakerSkill.matchByIntent(userId, request.text || '')
    return {
      success: result.success,
      candidates: result.candidates || [],
      ai_message: result.ai_message || ''
    }
  },

  /**
   * 对话式匹配 - 流式响应版本（保留原有实现）
   * 注：流式响应仍通过 Skill API 的 SSE 实现
   */
  async matchStream(
    request: ConversationMatchRequest,
    onChunk: (chunk: StreamChunk) => void
  ): Promise<void> {
    // 改用 Skill SSE 流式调用
    const userId = getCurrentUserId()
    const token = authStorage.getToken()

    const response = await fetch('/api/skills/conversation_matchmaker/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        skill_name: 'conversation_matchmaker',
        params: {
          user_id: userId,
          action: 'match_by_intent',
          intent_text: request.text
        },
        stream: true
      }),
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
      buffer = lines.pop() || ''

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
    const userId = getCurrentUserId()
    const result = await conversationMatchmakerSkill.getDailyRecommend(userId)
    return {
      success: result.success,
      recommendations: result.recommendations || []
    }
  },

  /**
   * 关系健康度分析
   */
  async analyzeRelationship(
    request: RelationshipAnalysisRequest
  ): Promise<RelationshipAnalysisResponse> {
    // 改用 relationshipCoachSkill
    const { relationshipCoachSkill } = await import('./skillClient')
    const result = await relationshipCoachSkill.healthCheck(request.match_id || '')
    return {
      success: result.success ?? false,
      health_score: result.health_score || 0,
      issues: result.issues || [],
      recommendations: result.recommendations || []
    }
  },

  /**
   * 获取关系状态
   */
  async getRelationshipStatus(matchId: string) {
    // 改用 relationshipCoachSkill
    const { relationshipCoachSkill } = await import('./skillClient')
    const result = await relationshipCoachSkill.healthCheck(matchId)
    return { success: result.success, status: result }
  },

  /**
   * 智能话题推荐
   */
  async suggestTopics(request: TopicSuggestionRequest): Promise<TopicSuggestionResponse> {
    const userId = getCurrentUserId()
    const result = await conversationMatchmakerSkill.suggestTopics(userId, request.match_id || '')
    return {
      success: result.success,
      topics: result.topics || []
    }
  },

  /**
   * 兼容性分析
   */
  async getCompatibility(targetUserId: string): Promise<CompatibilityAnalysis> {
    const userId = getCurrentUserId()
    const result = await conversationMatchmakerSkill.analyzeCompatibility(userId, targetUserId)
    return {
      success: result.success,
      compatibility_score: result.compatibility_score || 0,
      analysis: result.analysis || {}
    }
  },

  /**
   * 获取 AI 主动推送
   */
  async getAiPushRecommendations() {
    const userId = getCurrentUserId()
    const result = await conversationMatchmakerSkill.getDailyRecommend(userId)
    return { success: result.success, recommendations: result.recommendations || [] }
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

  /**
   * 获取每日滑动限制
   */
  async getDailyLimits(userId: string): Promise<{
    daily_likes: number
    daily_super_likes: number
    likes_used: number
    super_likes_used: number
    likes_remaining: number
    super_likes_remaining: number
    is_unlimited: boolean
  }> {
    const response = await apiClient.get(`/api/membership/usage/${userId}/daily`)
    return response.data
  },

  /**
   * 撤销滑动（会员功能）
   */
  async undoSwipe(swipeId: string) {
    const response = await apiClient.post(`/api/matching/swipe/${swipeId}/undo`)
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

// registration_conversation API 已删除，改用 profileCollectionSkill
export const registrationConversationApi = {
  /**
   * 开始注册对话
   */
  async startConversation(userId: string, userName: string) {
    const { profileCollectionSkill } = await import('./skillClient')
    const result = await profileCollectionSkill.startSession(userId)
    return {
      success: result.success,
      session_id: result.session_id,
      opening_message: result.opening_message
    }
  },

  /**
   * 发送对话消息
   */
  async sendMessage(userId: string, message: string) {
    const { profileCollectionSkill } = await import('./skillClient')
    // 需要先获取 session_id，这里简化处理
    const result = await profileCollectionSkill.sendMessage(`session-${userId}`, userId, message)
    return {
      success: result.success,
      ai_response: result.ai_response,
      profile_updates: result.profile_updates
    }
  },

  /**
   * 获取会话状态
   */
  async getSession(userId: string) {
    const { profileCollectionSkill } = await import('./skillClient')
    const result = await profileCollectionSkill.getProgress(userId)
    return {
      success: result.success,
      progress: result.progress,
      completed_dimensions: result.completed_dimensions
    }
  },

  /**
   * 完成对话
   */
  async completeConversation(userId: string) {
    const { profileCollectionSkill } = await import('./skillClient')
    const result = await profileCollectionSkill.completeSession(userId)
    return {
      success: result.success,
      profile: result.profile,
      recommendations: result.recommendations
    }
  },
}

// ==================== 合并后的 API ====================

// 聊天 API（合并 quick_chat + conversations）
export * from './chatApi'

// 视频约会 API（合并 video）
export * from './videoDateApi'

// ==================== 已删除的 API（改用 Skill 调用）====================
// emotionAnalysisApi 已删除：改用 emotionAnalysisSkill
// loveLanguageProfileApi 已删除：改用 relationshipCoachSkill.analyzeLoveLanguage
// dateSimulationApi 已删除：改用 twinSimulatorSkill
// quickStartApi 已删除：改用 matchmakingSkill + profileCollectionSkill

// ==================== 生活融合 API ====================

export * from './lifeIntegrationApi'

// ==================== 关系里程碑 API ====================

export * from './milestoneApi'

// ==================== Your Turn 提醒 API ====================

export * from './yourTurnApi'

// ==================== Who Likes Me API ====================

export * from './whoLikesMeApi'

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