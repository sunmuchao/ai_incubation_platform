/**
 * P13 API 服务 - 情感调解增强
 * 包含：爱之语画像、关系趋势预测、预警分级响应
 */

import axios from 'axios'
import type {
  LoveLanguageProfile,
  LoveLanguageDescription,
  RelationshipTrendPrediction,
  EmotionWarning,
  WarningResponseStrategy,
  WarningResponseRecord,
  ComprehensiveRelationshipAnalysis,
  AnalyzeLoveLanguageRequest,
  PredictRelationshipTrendRequest,
  GetWarningResponseStrategyRequest,
  ExecuteWarningResponseRequest,
  SubmitWarningResponseFeedbackRequest,
  ComprehensiveAnalysisRequest,
} from '../types/p13_types'

const API_BASE_URL = ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ==================== 爱之语画像 API ====================

export const loveLanguageProfileApi = {
  /**
   * 分析用户的爱之语偏好
   */
  async analyzeUserLoveLanguage(
    user_id: string
  ): Promise<{ success: boolean; profile: LoveLanguageProfile }> {
    const response = await api.post('/api/p13/love-language-profile/analyze', { user_id })
    return response.data
  },

  /**
   * 获取用户的爱之语画像
   */
  async getUserLoveLanguageProfile(
    user_id: string
  ): Promise<{ success: boolean; profile: LoveLanguageProfile | null; message?: string }> {
    const response = await api.get(`/api/p13/love-language-profile/${user_id}`)
    return response.data
  },

  /**
   * 获取爱之语类型的描述
   */
  async getLoveLanguageDescription(
    love_language: string
  ): Promise<{ success: boolean; love_language: string; description: LoveLanguageDescription }> {
    const response = await api.get(`/api/p13/love-language-profile/description/${love_language}`)
    return response.data
  },
}

// ==================== 关系趋势预测 API ====================

export const relationshipTrendApi = {
  /**
   * 生成关系趋势预测
   */
  async generateTrendPrediction(
    user_a_id: string,
    user_b_id: string,
    prediction_period: '7d' | '14d' | '30d' = '7d'
  ): Promise<{ success: boolean; prediction: RelationshipTrendPrediction }> {
    const response = await api.post('/api/p13/relationship-trend/predict', {
      user_a_id,
      user_b_id,
      prediction_period,
    })
    return response.data
  },

  /**
   * 获取关系趋势预测记录
   */
  async getTrendPrediction(
    prediction_id: string
  ): Promise<{ success: boolean; prediction: RelationshipTrendPrediction }> {
    const response = await api.get(`/api/p13/relationship-trend/${prediction_id}`)
    return response.data
  },
}

// ==================== 预警分级响应 API ====================

export const warningResponseApi = {
  /**
   * 根据预警级别获取响应策略
   */
  async getWarningResponseStrategy(
    warning_level: 'low' | 'medium' | 'high' | 'critical',
    context?: Record<string, any>
  ): Promise<{ success: boolean; strategy: WarningResponseStrategy }> {
    const response = await api.post('/api/p13/warning-response/strategy', {
      warning_level,
      context,
    })
    return response.data
  },

  /**
   * 执行预警响应
   */
  async executeWarningResponse(
    request: ExecuteWarningResponseRequest
  ): Promise<{ success: boolean; response_record: WarningResponseRecord }> {
    const response = await api.post('/api/p13/warning-response/execute', request)
    return response.data
  },

  /**
   * 提交预警响应反馈
   */
  async submitWarningResponseFeedback(
    request: SubmitWarningResponseFeedbackRequest
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/api/p13/warning-response/feedback', request)
    return response.data
  },

  /**
   * 获取用户的预警响应历史
   */
  async getUserWarningResponseHistory(
    user_id: string
  ): Promise<{ success: boolean; count: number; history: WarningResponseRecord[] }> {
    const response = await api.get(`/api/p13/warning-response/history/${user_id}`)
    return response.data
  },

  /**
   * 获取用户的预警列表
   */
  async getUserWarnings(
    user_id: string,
    unresolved_only = true
  ): Promise<{ success: boolean; warnings: EmotionWarning[] }> {
    const response = await api.get(`/api/p12/emotion/warnings/${user_id}`, {
      params: { unresolved_only },
    })
    return response.data
  },
}

// ==================== P13 综合分析 API ====================

export const comprehensiveAnalysisApi = {
  /**
   * 综合关系分析
   */
  async comprehensiveRelationshipAnalysis(
    user_a_id: string,
    user_b_id: string
  ): Promise<{
    success: boolean
    analysis: ComprehensiveRelationshipAnalysis
  }> {
    const response = await api.post('/api/p13/comprehensive/analyze', {
      user_a_id,
      user_b_id,
    })
    return response.data
  },
}
