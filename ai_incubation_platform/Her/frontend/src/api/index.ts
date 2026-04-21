// API 服务层 - 对接后端 AI Native 接口

// ==================== 核心 API ====================

import apiClient, { getAuthHeaders } from './apiClient'
import { authStorage } from '../utils/storage'
import { getCurrentUserId } from '../hooks/useCurrentUserId'
import { herAdvisorApi } from './herAdvisorApi'
import { deerflowClient } from './deerflowClient'
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
  User,
} from '../types'

/** 将 /api/matching/recommend 返回的扁平结构转为 MatchCandidate（含 user.avatar_url） */
function normalizeRecommendationRow(raw: Record<string, unknown>): MatchCandidate {
  const r = raw as Record<string, any>
  if (r?.user?.id) {
    return r as MatchCandidate
  }
  const id = (r.id ?? r.user_id) as string
  const interests = Array.isArray(r.interests) ? r.interests : []
  const user: User = {
    id,
    name: r.name || r.username || '用户',
    age: typeof r.age === 'number' ? r.age : Number(r.age) || 0,
    gender: r.gender || '',
    location: r.location || '',
    avatar: r.avatar,
    avatar_url: r.avatar_url,
    bio: r.bio || '',
    interests,
    goal: r.goal || r.relationship_goal || '',
    verified: !!r.verified,
  }
  return {
    user,
    compatibility_score: typeof r.compatibility_score === 'number' ? r.compatibility_score : Number(r.score) || 0,
    score_breakdown: (r.score_breakdown as MatchCandidate['score_breakdown']) || {},
    common_interests: (r.common_interests as string[]) || [],
    reasoning: (r.match_reason || r.compatibility_reason || r.reasoning || 'AI 综合评估推荐') as string,
    vector_match_highlights: (r.vector_match_highlights as MatchCandidate['vector_match_highlights']) || undefined,
  }
}

// conversation_matching API - 使用 ConversationMatchService（Her 顾问服务）
// 不要跳过这个 API 直接调用 DeerFlow！
export const conversationMatchingApi = {
  /**
   * 对话式匹配 - 用户通过自然语言表达匹配需求
   *
   * 正确调用路径：
   * 前端 → /api/her/chat → ConversationMatchService → HerAdvisorService
   *
   * 这样才能获得：
   * - 认知偏差分析（你想要的 ≠ 你适合的）
   * - Her 专业匹配建议
   * - 主动建议系统
   */
  async match(request: ConversationMatchRequest): Promise<ConversationMatchResponse> {
    const userId = getCurrentUserId()

    // 调用 Her 顾问服务（正确的路径！）
    const result = await herAdvisorApi.chat({
      message: request.text || '帮我找对象',
      user_id: userId,
    })

    return {
      success: true,
      candidates: result.matches || [],
      ai_message: result.ai_message || '',
      bias_analysis: result.bias_analysis,
      proactive_suggestion: result.proactive_suggestion,
    }
  },

  /**
   * 对话式匹配 - 流式响应版本
   * 注：流式响应通过 DeerFlow SSE 实现
   */
  async matchStream(
    request: ConversationMatchRequest,
    onChunk: (chunk: StreamChunk) => void
  ): Promise<void> {
    const userId = getCurrentUserId()
    const token = authStorage.getToken()

    // 使用 DeerFlow 流式 API
    await deerflowClient.stream(request.text || '帮我找对象', `her-match-${userId}`, (event) => {
      if (event.type === 'messages-tuple' || event.type === 'values') {
        onChunk({
          type: event.type,
          content: event.data?.content || '',
          candidates: event.data?.matches || []
        })
      }
    })
  },

  /**
   * 每日自主推荐 - AI 主动分析用户状态，推送每日匹配
   */
  async dailyRecommend(): Promise<DailyRecommendResponse> {
    const userId = getCurrentUserId()
    const result = await deerflowClient.chat('今日推荐', `her-daily-${userId}`)

    // Agent Native 架构：优先从 ai_message 解析 JSON
    const parsed = deerflowClient.parseToolResult(result)
    if (parsed?.type === 'matches' || parsed?.type === 'recommendations') {
      return {
        success: result.success,
        recommendations: parsed.data.matches || parsed.data.recommendations || []
      }
    }

    // 降级：从 tool_result.data 获取（兼容旧架构）
    return {
      success: result.success,
      recommendations: result.tool_result?.data?.recommendations || []
    }
  },

  /**
   * 关系健康度分析
   */
  async analyzeRelationship(
    request: RelationshipAnalysisRequest
  ): Promise<RelationshipAnalysisResponse> {
    const userId = getCurrentUserId()
    const result = await deerflowClient.chat(
      `分析我和 ${request.match_id} 的关系健康度`,
      `her-rel-${userId}`
    )

    // Agent Native 架构：优先从 ai_message 解析 JSON
    const parsed = deerflowClient.parseToolResult(result)
    if (parsed?.type === 'relationship_health') {
      return {
        success: result.success,
        health_score: parsed.data.health_score || 0,
        issues: parsed.data.issues || [],
        recommendations: parsed.data.suggestions || []
      }
    }

    // 降级：从 tool_result.data 获取（兼容旧架构）
    return {
      success: result.success,
      health_score: result.tool_result?.data?.health_score || 0,
      issues: result.tool_result?.data?.issues || [],
      recommendations: result.tool_result?.data?.suggestions || []
    }
  },

  /**
   * 获取关系状态
   */
  async getRelationshipStatus(matchId: string) {
    const userId = getCurrentUserId()
    const result = await deerflowClient.chat(`获取关系状态 ${matchId}`, `her-rel-status-${userId}`)

    // Agent Native 架构：优先从 ai_message 解析 JSON
    const parsed = deerflowClient.parseToolResult(result)
    if (parsed) {
      return { success: result.success, status: parsed.data }
    }

    // 降级：从 tool_result.data 获取（兼容旧架构）
    return { success: result.success, status: result.tool_result?.data }
  },

  /**
   * 智能话题推荐
   */
  async suggestTopics(request: TopicSuggestionRequest): Promise<TopicSuggestionResponse> {
    const userId = getCurrentUserId()
    const result = await deerflowClient.chat(
      `推荐我和 ${request.match_id} 的聊天话题`,
      `her-topics-${userId}`
    )

    // Agent Native 架构：优先从 ai_message 解析 JSON
    const parsed = deerflowClient.parseToolResult(result)
    if (parsed?.type === 'topics') {
      return {
        success: result.success,
        topics: parsed.data.topics || []
      }
    }

    // 降级：从 tool_result.data 获取（兼容旧架构）
    return {
      success: result.success,
      topics: result.tool_result?.data?.topics || []
    }
  },

  /**
   * 兼容性分析
   */
  async getCompatibility(targetUserId: string): Promise<CompatibilityAnalysis> {
    const userId = getCurrentUserId()
    const result = await deerflowClient.chat(
      `分析我和 ${targetUserId} 的兼容性`,
      `her-compat-${userId}`
    )

    // Agent Native 架构：优先从 ai_message 解析 JSON
    const parsed = deerflowClient.parseToolResult(result)
    if (parsed?.type === 'compatibility') {
      return {
        success: result.success,
        compatibility_score: parsed.data.overall_score || parsed.data.compatibility_score || 0,
        analysis: parsed.data
      }
    }

    // 降级：从 tool_result.data 获取（兼容旧架构）
    return {
      success: result.success,
      compatibility_score: result.tool_result?.data?.overall_score || result.tool_result?.data?.compatibility_score || 0,
      analysis: result.tool_result?.data || {}
    }
  },

  /**
   * 获取 AI 主动推送
   *
   * 🔧 性能优化：改为异步执行，不阻塞页面渲染
   * - 新用户没有完整画像，不需要立即推送
   * - 老用户的推荐可以异步加载
   */
  async getAiPushRecommendations() {
    const userId = getCurrentUserId()

    // 在后台异步调用，不阻塞页面渲染
    deerflowClient.chat('AI 主动推送推荐', `her-push-${userId}`)
      .then(result => {
        console.log('[AI推送] 后台加载完成')
      })
      .catch(err => {
        console.warn('[AI推送] 后台加载失败:', err)
      })

    // 立即返回空结果，让页面先渲染
    return { success: true, recommendations: [] }
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

  /**
   * 触发 LLM 对近期行为做选择性摘要（结果写入服务端 behavior_digest.jsonl）
   */
  async runBehaviorDigest(userId: string, limit = 150) {
    const response = await apiClient.post(
      `/api/ai/awareness/behavior-digest?user_id=${encodeURIComponent(userId)}&limit=${limit}`
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
    const data = response.data
    if (!Array.isArray(data)) return []
    return data.map((row: Record<string, unknown>) => normalizeRecommendationRow(row))
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
    email: string
    password: string
    name: string
    age: number
    gender: string
    location: string
    bio?: string
    interests?: string[]
  }) {
    const response = await apiClient.post('/api/users/register', userData)
    return response.data
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser() {
    try {
      const response = await apiClient.get('/api/users/me')
      return response.data
    } catch (error: any) {
      // 兼容部分环境中尚未提供 /me 端点，回退到按 userId 查询
      if (error?.status === 404) {
        const fallbackUserId = authStorage.getUserId()
        if (fallbackUserId && fallbackUserId !== 'anonymous') {
          const fallback = await apiClient.get(`/api/users/${encodeURIComponent(fallbackUserId)}`)
          return fallback.data
        }

        const cachedUser = authStorage.getUser()
        if (cachedUser) {
          return cachedUser
        }
      }
      throw error
    }
  },

  /**
   * 按用户 ID 获取用户信息
   */
  async getUserById(userId: string) {
    const response = await apiClient.get(`/api/users/${encodeURIComponent(userId)}`)
    return response.data
  },

  /**
   * 更新当前用户信息
   */
  async updateCurrentUser(userId: string, data: Record<string, any>) {
    const response = await apiClient.put(`/api/users/${encodeURIComponent(userId)}`, data)
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

// registration_conversation API 改用 DeerFlow Agent
export const registrationConversationApi = {
  /**
   * 开始注册对话
   */
  async startConversation(userId: string, userName: string) {
    const result = await deerflowClient.chat(
      `你好，我是 ${userName}，请帮我完善我的个人资料`,
      `her-register-${userId}`
    )
    return {
      success: result.success,
      session_id: `session-${userId}`,
      opening_message: result.ai_message
    }
  },

  /**
   * 发送对话消息
   */
  async sendMessage(userId: string, message: string) {
    const result = await deerflowClient.chat(message, `her-register-${userId}`)
    return {
      success: result.success,
      ai_response: result.ai_message,
      profile_updates: result.tool_result?.data?.profile_updates || {}
    }
  },

  /**
   * 获取会话状态
   */
  async getSession(userId: string) {
    const result = await deerflowClient.chat('查看我的资料完善进度', `her-register-${userId}`)
    return {
      success: result.success,
      progress: result.tool_result?.data?.progress || 50,
      completed_dimensions: result.tool_result?.data?.completed_dimensions || []
    }
  },

  /**
   * 完成对话
   */
  async completeConversation(userId: string) {
    const result = await deerflowClient.chat('完成资料收集', `her-register-${userId}`)
    return {
      success: result.success,
      profile: result.tool_result?.data?.profile || {},
      recommendations: result.tool_result?.data?.recommendations || []
    }
  },
}

// ==================== 合并后的 API ====================

// Her 顾问 API - 对话为唯一入口（新）
export { herAdvisorApi } from './herAdvisorApi'
export type {
  HerChatRequest,
  HerChatResponse,
  HerBiasAnalysis,
  HerMatchAdvice,
  HerProactiveSuggestion,
  HerUserProfile,
  HerKnowledgeCase,
} from './herAdvisorApi'

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

// ==================== 人脸认证 API ====================

export * from './faceVerificationApi'

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

// ==================== 统一认证入口 ====================

// 导出认证函数，供其他模块使用
export { getAuthHeaders, getCurrentUserId }