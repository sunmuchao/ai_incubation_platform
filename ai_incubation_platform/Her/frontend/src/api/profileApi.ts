/**
 * 个人信息收集 API
 *
 * 用于对话式收集用户偏好和资料
 */

import apiClient from './apiClient'
import { authStorage, devStorage } from '../utils/storage'

// ========== 类型定义 ==========

export interface QuestionOption {
  value: string
  label: string
  icon?: string
}

export interface QuestionCard {
  question: string
  subtitle?: string
  question_type: 'single_choice' | 'multiple_choice' | 'tags'
  options: QuestionOption[]
  dimension: string
  depth?: number
}

export interface ProfileQuestionRequest {
  user_id?: string
  conversation_context?: Array<{ role: string; content: string }>
  trigger_reason?: 'user_intent' | 'matching_need' | 'profile_update' | 'explicit_request'
}

export interface ProfileQuestionResponse {
  success: boolean
  need_collection: boolean
  need_follow_up?: boolean
  question_card?: QuestionCard
  ai_message: string
  profile_gaps?: string[]
}

export interface ProfileAnswerRequest {
  user_id?: string
  dimension: string
  answer: string | string[]
  depth?: number
  previous_context?: Array<{ role: string; content: string }>
}

export interface ProfileAnswerResponse {
  success: boolean
  ai_message: string
  updated_profile?: Record<string, any>
  has_more_questions?: boolean
  next_question?: QuestionCard
}

// ========== API 函数 ==========

/**
 * 获取下一个问题卡片
 */
export async function getProfileQuestion(
  request: ProfileQuestionRequest
): Promise<ProfileQuestionResponse> {
  const token = authStorage.getToken()
  const testUserId = devStorage.getTestUserId() || 'user-anonymous-dev'

  const response = await apiClient.post('/api/profile/question', {
    ...request,
    user_id: request.user_id || testUserId,
  }, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  return response.data
}

/**
 * 提交用户回答
 */
export async function submitProfileAnswer(
  request: ProfileAnswerRequest
): Promise<ProfileAnswerResponse> {
  const token = authStorage.getToken()
  const testUserId = devStorage.getTestUserId() || 'user-anonymous-dev'

  const response = await apiClient.post('/api/profile/answer', {
    ...request,
    user_id: request.user_id || testUserId,
  }, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  return response.data
}

/**
 * 获取追问问题
 */
export async function getFollowUpQuestion(
  request: ProfileAnswerRequest
): Promise<ProfileQuestionResponse> {
  const token = authStorage.getToken()
  const testUserId = devStorage.getTestUserId() || 'user-anonymous-dev'

  const response = await apiClient.post('/api/profile/follow-up', {
    ...request,
    user_id: request.user_id || testUserId,
  }, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  return response.data
}

/**
 * 获取用户画像缺口
 */
export async function getProfileGaps(userId?: string): Promise<{
  success: boolean
  gaps: Array<{ dimension: string; name: string; priority: number }>
  total_dimensions: number
  filled_dimensions: number
}> {
  const token = authStorage.getToken()
  const testUserId = devStorage.getTestUserId() || 'user-anonymous-dev'

  const response = await apiClient.get(`/api/profile/gaps/${userId || testUserId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  return response.data
}

// ========== 导出 ==========

export const profileApi = {
  getQuestion: getProfileQuestion,
  submitAnswer: submitProfileAnswer,
  getFollowUp: getFollowUpQuestion,
  getGaps: getProfileGaps,
}

export default profileApi