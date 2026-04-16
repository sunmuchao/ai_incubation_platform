/**
 * 人脸认证 API 客户端
 *
 * 参考 Tinder Blue Star 认证徽章：
 * - 人脸照片认证
 * - 活体检测
 * - 认证徽章发放
 * - 认证状态查询
 */

import apiClient, { getAuthHeaders } from './apiClient'

// ==================== 类型定义 ====================

export type FaceVerificationStatus =
  | 'not_started'
  | 'in_progress'
  | 'submitted'
  | 'verified'
  | 'failed'
  | 'expired'

export type FaceVerificationMethod =
  | 'id_card_compare'
  | 'self_photo'
  | 'video_liveness'
  | 'ai_gesture'

export type VerificationBadgeType =
  | 'blue_star'
  | 'gold_star'
  | 'platinum_star'
  | 'diamond_star'

export interface FaceVerificationResponse {
  success: boolean
  message: string
  verification_id?: string
  status: FaceVerificationStatus
  similarity_score?: number
  liveness_score?: number
  badge_type?: VerificationBadgeType
}

export interface VerificationStatusResponse {
  user_id: string
  face_verified: boolean
  face_verification_id?: string
  face_verification_date?: string
  id_verified: boolean
  education_verified: boolean
  occupation_verified: boolean
  current_badge?: VerificationBadgeType
  badge_display_name?: string
  badge_display_icon?: string
  badge_display_color?: string
  trust_score: number
}

export interface VerificationRecordResponse {
  id: string
  user_id: string
  method: string
  status: FaceVerificationStatus
  similarity_score?: number
  liveness_score?: number
  is_passed: boolean
  failure_reason?: string
  retry_count: number
  submitted_at?: string
  completed_at?: string
}

export interface BadgeInfoResponse {
  badge_type: string
  icon: string
  color: string
  name: string
  description: string
  requirements: string[]
}

export interface VerificationMethod {
  type: string
  name: string
  description: string
  difficulty: string
  estimated_time: string
}

// ==================== API 函数 ====================

/**
 * 获取用户认证状态
 */
export async function getVerificationStatus(): Promise<VerificationStatusResponse> {
  const response = await apiClient.get('/api/face-verification/status')
  return response.data
}

/**
 * 开始人脸认证流程
 */
export async function startVerification(
  method: FaceVerificationMethod = 'id_card_compare'
): Promise<FaceVerificationResponse> {
  const response = await apiClient.post('/api/face-verification/start', {
    method,
  })
  return response.data
}

/**
 * 提交人脸照片进行认证
 */
export async function submitVerification(
  photoBase64: string,
  method: FaceVerificationMethod = 'id_card_compare',
  videoBase64?: string,
  gestureSequence?: string[]
): Promise<FaceVerificationResponse> {
  const response = await apiClient.post('/api/face-verification/submit', {
    photo_base64: photoBase64,
    method,
    video_base64: videoBase64,
    gesture_sequence: gestureSequence,
  })
  return response.data
}

/**
 * 重试人脸认证
 */
export async function retryVerification(): Promise<FaceVerificationResponse> {
  const response = await apiClient.post('/api/face-verification/retry')
  return response.data
}

/**
 * 获取用户认证记录
 */
export async function getVerificationRecord(): Promise<VerificationRecordResponse> {
  const response = await apiClient.get('/api/face-verification/record')
  return response.data
}

/**
 * 获取所有徽章类型说明
 */
export async function getAllBadges(): Promise<{ success: boolean; badges: BadgeInfoResponse[]; total: number }> {
  const response = await apiClient.get('/api/face-verification/badges')
  return response.data
}

/**
 * 获取单个徽章信息
 */
export async function getBadgeInfo(badgeType: string): Promise<BadgeInfoResponse> {
  const response = await apiClient.get(`/api/face-verification/badge/${badgeType}`)
  return response.data
}

/**
 * 检查用户是否已认证（公开接口）
 */
export async function checkUserVerified(userId: string): Promise<{ user_id: string; verified: boolean }> {
  const response = await apiClient.get(`/api/face-verification/check/${userId}`)
  return response.data
}

/**
 * 获取用户认证徽章（公开接口）
 */
export async function getUserBadge(userId: string): Promise<{
  user_id: string
  verified: boolean
  badge?: {
    type: string
    icon: string
    color: string
    name: string
  }
  trust_score?: number
}> {
  const response = await apiClient.get(`/api/face-verification/user/${userId}/badge`)
  return response.data
}

/**
 * 获取所有认证方式说明
 */
export async function getVerificationMethods(): Promise<{ success: boolean; methods: VerificationMethod[] }> {
  const response = await apiClient.get('/api/face-verification/methods')
  return response.data
}

// ==================== 默认导出 ====================

const faceVerificationApi = {
  getVerificationStatus,
  startVerification,
  submitVerification,
  retryVerification,
  getVerificationRecord,
  getAllBadges,
  getBadgeInfo,
  checkUserVerified,
  getUserBadge,
  getVerificationMethods,
}

export default faceVerificationApi