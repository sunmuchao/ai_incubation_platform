/**
 * Her 顾问 API
 *
 * 【架构变更说明 - 2026-04-13】
 *
 * 对话式匹配 API - 调用后端 ConversationMatchService
 *
 * 架构：
 * - 对话入口：herAdvisorApi.chat() → /api/her/chat
 * - ConversationMatchService：意图理解 + 画像获取 + 认知偏差识别 + 匹配执行
 * - HerAdvisorService：专业婚恋顾问分析 + 匹配建议生成
 *
 * 这是正确的调用路径，不要跳过这个 API 直接调用 DeerFlow！
 */

import apiClient from './apiClient'
import { authStorage } from '../utils/storage'
import { getCurrentUserId } from '../hooks/useCurrentUserId'

// ==================== 类型定义 ====================

export interface HerChatRequest {
  message: string
  user_id?: string
  thread_id?: string
  message_history?: Array<{ role: string; content: string }>
}

export interface HerChatResponse {
  ai_message: string
  intent_type: string
  matches?: Array<{
    id: string
    name: string
    score: number
    reasoning: string
    her_advice?: HerMatchAdvice
    risk_warnings?: string[]
  }>
  bias_analysis?: HerBiasAnalysis
  proactive_suggestion?: HerProactiveSuggestion
  generative_ui?: {
    component_type: string
    props: Record<string, any>
  }
  suggested_actions?: Array<{ label: string; action: string }>
}

export interface HerBiasAnalysis {
  has_bias: boolean
  bias_type?: string
  bias_description?: string
  actual_suitable_type?: string
  potential_risks?: string[]
  adjustment_suggestion?: string
  confidence: number
}

export interface HerMatchAdvice {
  advice_type: string
  advice_content: string
  reasoning?: string
  suggestions_for_user?: string[]
  potential_issues?: string[]
  compatibility_score: number
}

export interface HerProactiveSuggestion {
  suggestions: Array<{
    type: string
    importance: string
    message: string
    suggestion: string
  }>
  has_critical_suggestion: boolean
}

export interface HerUserProfile {
  user_id: string
  self_profile: {
    basic: Record<string, any>
    personality: Record<string, any>
    communication: Record<string, any>
    emotional_needs: Record<string, any>
    power_dynamic: Record<string, any>
    social_feedback: Record<string, any>
    confidence: Record<string, any>
  }
  desire_profile: {
    surface_preference: string
    actual_preference: string
    ideal_type_description: string
    deal_breakers?: string[]
    search_patterns?: any[]
    clicked_types?: string[]
    preference_gap?: string
    confidence: number
  }
  self_profile_confidence: number
  desire_profile_confidence: number
  self_profile_completeness: number
  desire_profile_completeness: number
}

export interface HerKnowledgeCase {
  id: string
  case_type: 'warning_case' | 'success_case' | 'typical_pattern'
  tags: string[]
  case_description: string
  her_analysis: string
  her_suggestion: string
  key_insights: string[]
}

// ==================== API 实现 ====================

export const herAdvisorApi = {
  /**
   * 对话式匹配 - Her 顾问服务入口
   *
   * 这是正确的调用路径！调用后端 ConversationMatchService：
   * - 意图理解 → IntentAnalyzer
   * - 画像获取 → UserProfileService
   * - 认知偏差识别 → CognitiveBiasDetector
   * - 匹配执行 → HerAdvisorService
   * - 主动建议 → ProactiveSuggestionGenerator
   *
   * 不要跳过这个 API 直接调用 DeerFlow！
   */
  async chat(request: HerChatRequest): Promise<HerChatResponse> {
    const token = authStorage.getToken()
    const userId = request.user_id || getCurrentUserId()

    const response = await apiClient.post('/api/her/chat', {
      message: request.message,
      user_id: userId,
      thread_id: request.thread_id,
      message_history: request.message_history,
    }, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    return response.data
  },

  /**
   * 认知偏差分析
   *
   * 让 Her 分析用户的认知偏差：
   * - 用户想要的 ≠ 用户适合的
   *
   * 注意：认知偏差识别由 LLM 自主判断，不硬编码规则
   */
  async analyzeBias(userId?: string): Promise<HerBiasAnalysis> {
    const token = authStorage.getToken()
    const uid = userId || getCurrentUserId()

    const response = await apiClient.post('/api/her/analyze-bias', {
      user_id: uid,
    }, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    return response.data
  },

  /**
   * 获取匹配建议
   *
   * 让 Her 分析两个用户的匹配度并给出专业建议
   */
  async getMatchAdvice(userIdA: string, userIdB: string): Promise<HerMatchAdvice> {
    const token = authStorage.getToken()

    const response = await apiClient.post('/api/her/match-advice', {
      user_id_a: userIdA,
      user_id_b: userIdB,
    }, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    return response.data
  },

  /**
   * 获取用户画像
   *
   * 返回双向画像：SelfProfile + DesireProfile
   */
  async getProfile(userId?: string): Promise<HerUserProfile> {
    const uid = userId || getCurrentUserId()
    const token = authStorage.getToken()

    const response = await apiClient.get(`/api/her/profile/${uid}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    return response.data
  },

  /**
   * 记录行为事件
   *
   * 行为事件用于更新用户画像：
   * - 搜索行为 → 更新 DesireProfile
   * - 点击行为 → 更新 DesireProfile
   * - 消息行为 → 更新 SelfProfile
   */
  async recordBehaviorEvent(
    eventType: string,
    eventData?: Record<string, any>,
    targetUserId?: string,
    userId?: string
  ): Promise<{ success: boolean; updated_dimensions?: string[] }> {
    const uid = userId || getCurrentUserId()
    const token = authStorage.getToken()

    const response = await apiClient.post('/api/her/behavior-event', {
      user_id: uid,
      event_type: eventType,
      event_data: eventData,
      target_user_id: targetUserId,
    }, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    return response.data
  },

  /**
   * 获取 Her 知识库案例
   *
   * 用于展示 Her 的专业知识能力
   */
  async getKnowledgeCases(
    caseType?: 'warning_case' | 'success_case' | 'typical_pattern',
    limit: number = 10
  ): Promise<HerKnowledgeCase[]> {
    const params = new URLSearchParams()
    if (caseType) params.append('case_type', caseType)
    params.append('limit', limit.toString())

    const response = await apiClient.get(`/api/her/knowledge-cases?${params.toString()}`)
    return response.data
  },

  /**
   * Her 服务健康检查
   */
  async healthCheck(): Promise<{
    status: string
    services: Record<string, string>
    features: string[]
  }> {
    const response = await apiClient.get('/api/her/health')
    return response.data
  },

  // ==================== 便捷方法 ====================

  /**
   * 【已删除】quickMatch 方法
   *
   * 此方法依赖于已删除的 chat 方法。
   * 请使用 deerflowClient.chat('帮我找对象', threadId) 替代。
   *
   * @deprecated 已删除，使用 deerflowClient.chat()
   */

  /**
   * 记录搜索行为
   */
  async recordSearch(query: string, filters?: Record<string, any>) {
    return this.recordBehaviorEvent('search_query', {
      query,
      filters,
    })
  },

  /**
   * 记录查看资料行为
   */
  async recordProfileView(targetUserId: string, targetType?: string) {
    return this.recordBehaviorEvent('profile_view', {
      target_type: targetType,
    }, targetUserId)
  },

  /**
   * 记录滑动行为
   */
  async recordSwipe(targetUserId: string, action: 'like' | 'pass' | 'super_like', targetType?: string) {
    return this.recordBehaviorEvent(
      action === 'like' ? 'swipe_like' : 'swipe_pass',
      { target_type: targetType },
      targetUserId
    )
  },

  /**
   * 记录匹配反馈
   */
  async recordMatchFeedback(targetUserId: string, feedback: 'like' | 'dislike', reason?: string) {
    return this.recordBehaviorEvent(
      feedback === 'like' ? 'match_like' : 'match_dislike',
      { reason },
      targetUserId
    )
  },
}

export default herAdvisorApi