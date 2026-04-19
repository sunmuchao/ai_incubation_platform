/**
 * 置信度 API Client
 *
 * 用于用户信息可信度评估和验证建议
 */

import apiClient from './apiClient'

// ==================== 类型定义 ====================

export interface ConfidenceSummary {
  /** 置信度等级 */
  level: 'very_high' | 'high' | 'medium' | 'low'
  /** 置信度分数 (0-1) */
  confidence: number
  /** 是否已验证 */
  verified: boolean
  /** 异常标记数量 */
  flags_count: number
  /** 评估时间 */
  evaluated_at?: string
}

export interface ConfidenceDetail {
  /** 置信度等级 */
  confidence_level: 'very_high' | 'high' | 'medium' | 'low'
  /** 置信度等级名称 */
  confidence_level_name: string
  /** 总置信度 */
  overall_confidence: number
  /** 各维度置信度 */
  dimensions: {
    identity: number
    cross_validation: number
    behavior: number
    social: number
    time: number
  }
  /** 跨验证异常标记 */
  cross_validation_flags?: Record<string, {
    severity: 'high' | 'medium' | 'low'
    detail: string
  }>
  /** 上次评估时间 */
  last_evaluated_at?: string
}

export interface VerificationRecommendation {
  /** 推荐类型 */
  type: 'identity_verify' | 'face_verify' | 'education_verify' | 'occupation_verify' | 'profile_complete'
  /** 优先级 */
  priority: 'high' | 'medium' | 'low'
  /** 推荐原因 */
  reason: string
  /** 预估置信度提升 */
  estimated_confidence_boost: number
}

export interface ConfidenceExplanation {
  /** 置信度计算说明 */
  formula: string
  /** 各维度权重 */
  weights: Record<string, number>
  /** 关键因素 */
  key_factors: string[]
}

// ==================== API 方法 ====================

const confidenceApi = {
  /**
   * 获取当前用户置信度摘要
   */
  async getConfidenceSummary(): Promise<ConfidenceSummary> {
    const response = await apiClient.get('/api/profile/confidence/summary')
    return response.data
  },

  /**
   * 获取其他用户置信度摘要
   */
  async getOtherUserConfidenceSummary(userId: string): Promise<ConfidenceSummary> {
    const response = await apiClient.get(`/api/profile/confidence/summary/${userId}`)
    return response.data
  },

  /**
   * 获取置信度详情
   */
  async getConfidenceDetail(): Promise<ConfidenceDetail> {
    const response = await apiClient.get('/api/profile/confidence/detail')
    return response.data
  },

  /**
   * 获取验证建议
   */
  async getVerificationRecommendations(): Promise<{ recommendations: VerificationRecommendation[] }> {
    const response = await apiClient.get('/api/profile/confidence/recommendations')
    return response.data
  },

  /**
   * 刷新置信度评估
   */
  async refreshConfidence(force: boolean = false): Promise<{ success: boolean }> {
    const response = await apiClient.post('/api/profile/confidence/refresh', { force })
    return response.data
  },

  /**
   * 获取置信度解释
   */
  async getConfidenceExplanation(): Promise<ConfidenceExplanation> {
    const response = await apiClient.get('/api/profile/confidence/explanation')
    return response.data
  },
}

export default confidenceApi
