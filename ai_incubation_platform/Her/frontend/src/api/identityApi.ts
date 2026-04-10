/**
 * 身份认证 API
 */

import { apiClient } from './apiClient'

export interface VerificationStatus {
  is_verified: boolean
  status: string
  message?: string
  verification_type?: string
  badge?: string
  verified_at?: string
  expires_at?: string
  rejection_reason?: string
}

export const identityApi = {
  /**
   * 获取认证状态
   */
  async getVerificationStatus(): Promise<VerificationStatus> {
    const response = await apiClient.get('/api/auth/status')
    return response.data
  },

  /**
   * 提交实名认证
   */
  async submitVerification(data: {
    real_name: string
    id_number: string
    verification_type?: string
    id_front_url?: string
    id_back_url?: string
  }): Promise<any> {
    const response = await apiClient.post('/api/auth/verify-identity', data)
    return response.data
  },

  /**
   * 上传证件照片
   */
  async uploadIdPhoto(file: File, side: 'front' | 'back'): Promise<{ url: string }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('side', side)

    const response = await apiClient.post('/api/auth/upload-id-photo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * 提交人脸核身
   */
  async submitFaceVerify(data: {
    face_verify_url: string
    similarity_score: number
  }): Promise<any> {
    const response = await apiClient.post('/api/auth/face-verify', data)
    return response.data
  },

  /**
   * 上传人脸照片
   */
  async uploadFacePhoto(file: File): Promise<{ url: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/api/auth/upload-face-photo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

export default identityApi