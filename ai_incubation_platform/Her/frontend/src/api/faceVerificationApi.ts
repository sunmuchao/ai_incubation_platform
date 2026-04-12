// Face Verification API - 人脸认证接口
// 参考 Tinder Blue Star 认证徽章

import apiClient from './apiClient'
import type {
  FaceVerificationStatus,
  VerificationBadgeType,
} from '../types/faceVerification'

export const faceVerificationApi = {
  /**
   * 获取用户认证状态
   */
  async getStatus(): Promise<{
    user_id: string
    face_verified: boolean
    face_verification_id?: string
    face_verification_date?: string
    id_verified: boolean
    education_verified: boolean
    occupation_verified: boolean
    current_badge?: string
    badge_display_name?: string
    badge_display_icon?: string
    badge_display_color?: string
    trust_score: number
  }> {
    const response = await apiClient.get('/api/face-verification/status')
    return response.data
  },

  /**
   * 开始人脸认证流程
   */
  async startVerification(method: string = 'id_card_compare'): Promise<{
    success: boolean
    message: string
    verification_id?: string
    status: string
  }> {
    const response = await apiClient.post('/api/face-verification/start', {
      method,
    })
    return response.data
  },

  /**
   * 提交人脸照片
   */
  async submitPhoto(request: {
    photo_base64: string
    method?: string
    video_base64?: string
    gesture_sequence?: string[]
  }): Promise<{
    success: boolean
    message: string
    verification_id?: string
    status: string
    similarity_score?: number
    liveness_score?: number
    badge_type?: string
  }> {
    const response = await apiClient.post('/api/face-verification/submit', request)
    return response.data
  },

  /**
   * 重试认证
   */
  async retryVerification(): Promise<{
    success: boolean
    message: string
    verification_id?: string
    status: string
  }> {
    const response = await apiClient.post('/api/face-verification/retry')
    return response.data
  },

  /**
   * 获取认证记录
   */
  async getRecord(): Promise<{
    id: string
    user_id: string
    method: string
    status: string
    similarity_score?: number
    liveness_score?: number
    is_passed: boolean
    failure_reason?: string
    retry_count: number
    submitted_at?: string
    completed_at?: string
  }> {
    const response = await apiClient.get('/api/face-verification/record')
    return response.data
  },

  /**
   * 获取所有徽章类型
   */
  async getBadges(): Promise<{
    success: boolean
    badges: Array<{
      badge_type: string
      icon: string
      color: string
      name: string
      description: string
      requirements: string[]
    }>
    total: number
  }> {
    const response = await apiClient.get('/api/face-verification/badges')
    return response.data
  },

  /**
   * 获取单个徽章信息
   */
  async getBadgeInfo(badgeType: string): Promise<{
    badge_type: string
    icon: string
    color: string
    name: string
    description: string
    requirements: string[]
  }> {
    const response = await apiClient.get(`/api/face-verification/badge/${badgeType}`)
    return response.data
  },

  /**
   * 检查用户是否已认证（公开接口）
   */
  async checkUserVerified(userId: string): Promise<{
    user_id: string
    verified: boolean
  }> {
    const response = await apiClient.get(`/api/face-verification/check/${userId}`)
    return response.data
  },

  /**
   * 获取用户徽章（公开接口）
   */
  async getUserBadge(userId: string): Promise<{
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
  },

  /**
   * 获取认证方式说明
   */
  async getMethods(): Promise<{
    success: boolean
    methods: Array<{
      type: string
      name: string
      description: string
      difficulty: string
      estimated_time: string
    }>
  }> {
    const response = await apiClient.get('/api/face-verification/methods')
    return response.data
  },
}

export default faceVerificationApi