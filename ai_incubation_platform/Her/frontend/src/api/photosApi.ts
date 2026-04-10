/**
 * 照片管理 API
 */

import { apiClient } from './apiClient'

export interface Photo {
  id: string
  user_id: string
  photo_url: string
  photo_type: string
  display_order: number
  moderation_status: string
  moderation_reason?: string
  ai_tags: string
  ai_quality_score?: number
  is_verified: boolean
  like_count: number
  view_count: number
  created_at: string
}

export const photosApi = {
  /**
   * 上传照片
   */
  async uploadPhoto(data: {
    photo_url: string
    photo_type?: string
    ai_tags?: string[]
    ai_quality_score?: number
  }): Promise<Photo> {
    const response = await apiClient.post('/api/photos/upload', data)
    return response.data
  },

  /**
   * 上传照片文件
   */
  async uploadPhotoFile(file: File, photoType: string = 'profile'): Promise<{
    id: string
    photo_url: string
    photo_type: string
  }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('photo_type', photoType)

    const response = await apiClient.post('/api/photos/upload-file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * 获取我的照片列表
   */
  async getMyPhotos(approvedOnly: boolean = false): Promise<Photo[]> {
    const response = await apiClient.get('/api/photos/my', {
      params: { approved_only: approvedOnly },
    })
    return response.data
  },

  /**
   * 获取用户照片列表
   */
  async getUserPhotos(userId: string): Promise<Photo[]> {
    const response = await apiClient.get(`/api/photos/user/${userId}`)
    return response.data
  },

  /**
   * 获取照片详情
   */
  async getPhoto(photoId: string): Promise<Photo> {
    const response = await apiClient.get(`/api/photos/${photoId}`)
    return response.data
  },

  /**
   * 删除照片
   */
  async deletePhoto(photoId: string): Promise<void> {
    await apiClient.delete(`/api/photos/${photoId}`)
  },

  /**
   * 更新照片排序
   */
  async updatePhotoOrder(photoIds: string[]): Promise<void> {
    await apiClient.put('/api/photos/order', { photo_ids: photoIds })
  },

  /**
   * 点赞照片
   */
  async likePhoto(photoId: string): Promise<void> {
    await apiClient.post(`/api/photos/${photoId}/like`)
  },

  /**
   * 获取已验证照片数量
   */
  async getVerifiedCount(): Promise<{ verified_count: number }> {
    const response = await apiClient.get('/api/photos/stats/verified-count')
    return response.data
  },

  /**
   * 获取头像 URL
   */
  async getAvatarUrl(userId?: string): Promise<{ avatar_url: string }> {
    const response = await apiClient.get('/api/photos/stats/avatar-url', {
      params: userId ? { user_id: userId } : {},
    })
    return response.data
  },
}

export default photosApi