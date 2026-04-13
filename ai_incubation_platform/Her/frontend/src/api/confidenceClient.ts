/**
 * 用户置信度 API 客户端
 *
 * 端点：
 * - GET /api/profile/confidence - 获取完整置信度详情
 * - GET /api/profile/confidence/summary - 获取置信度摘要
 * - POST /api/profile/confidence/refresh - 手动刷新评估
 * - GET /api/profile/confidence/recommendations - 获取验证建议
 */

import apiClient, { getAuthHeaders, getCurrentUserId } from './apiClient'
import type { AxiosResponse } from 'axios'

// ==================== 类型定义 ====================

export interface ConfidenceDetail {
  success: boolean
  user_id: string
  overall_confidence: number
  confidence_level: 'low' | 'medium' | 'high' | 'very_high'
  confidence_level_name: string
  dimensions: {
    identity: number
    cross_validation: number
    behavior: number
    social: number
    time: number
  }
  cross_validation_flags: Record<string, CrossValidationFlag>
  recommendations: VerificationRecommendation[]
  last_evaluated_at: string | null
}

export interface ConfidenceSummary {
  confidence: number
  level: 'low' | 'medium' | 'high' | 'very_high'
  level_name: string
  verified: boolean
  flags_count: number
}

export interface CrossValidationFlag {
  severity: 'low' | 'medium' | 'high'
  detail: string
  claimed_age?: number
  claimed_education?: string
  claimed_occupation?: string
  claimed_income?: string
}

export interface VerificationRecommendation {
  type: string
  priority: 'high' | 'medium' | 'low'
  estimated_confidence_boost: number
  reason: string
}

export interface ConfidenceExplanation {
  success: boolean
  explanation: {
    title: string
    description: string
    dimensions: Array<{
      name: string
      weight: string
      description: string
      how_to_improve: string
    }>
    levels: Array<{
      name: string
      range: string
      color: string
    }>
    privacy_note: string
  }
}

// ==================== API 函数 ====================

/**
 * 获取当前用户置信度详情
 */
export async function getConfidenceDetail(): Promise<ConfidenceDetail> {
  const response: AxiosResponse<ConfidenceDetail> = await apiClient.get(
    '/api/profile/confidence'
  )
  return response.data
}

/**
 * 获取当前用户置信度摘要
 */
export async function getConfidenceSummary(): Promise<ConfidenceSummary> {
  const response: AxiosResponse<ConfidenceSummary> = await apiClient.get(
    '/api/profile/confidence/summary'
  )
  return response.data
}

/**
 * 获取其他用户的置信度摘要
 */
export async function getOtherUserConfidenceSummary(userId: string): Promise<ConfidenceSummary> {
  const response: AxiosResponse<ConfidenceSummary> = await apiClient.get(
    `/api/profile/confidence/user/${userId}/summary`
  )
  return response.data
}

/**
 * 手动刷新置信度评估
 */
export async function refreshConfidence(force: boolean = false): Promise<{
  success: boolean
  message: string
  confidence: number
  level: string
  change: number
}> {
  const response = await apiClient.post(
    '/api/profile/confidence/refresh',
    { force }
  )
  return response.data
}

/**
 * 获取验证建议
 */
export async function getVerificationRecommendations(): Promise<{
  success: boolean
  recommendations: VerificationRecommendation[]
  total_count: number
  high_priority_count: number
}> {
  const response = await apiClient.get(
    '/api/profile/confidence/recommendations'
  )
  return response.data
}

/**
 * 获取置信度系统解释
 */
export async function getConfidenceExplanation(): Promise<ConfidenceExplanation> {
  const response: AxiosResponse<ConfidenceExplanation> = await apiClient.get(
    '/api/profile/confidence/explain'
  )
  return response.data
}

// ==================== 默认导出 ====================

export default {
  getConfidenceDetail,
  getConfidenceSummary,
  getOtherUserConfidenceSummary,
  refreshConfidence,
  getVerificationRecommendations,
  getConfidenceExplanation,
}