/**
 * Who Likes Me API 客户端
 *
 * 参考 Tinder Gold 功能
 */

import apiClient from './apiClient'
import { devStorage } from '../utils/storage'

export interface LikeUser {
  user_id: string
  name: string
  avatar?: string
  avatar_blurred?: string
  liked_at: string
  compatibility_score?: number
  is_blurred: boolean
  blur_level?: string
}

export interface WhoLikesMeResponse {
  total_count: number
  has_more: boolean
  is_member: boolean
  likes: LikeUser[]
  free_preview_count: number
}

export interface LikeBackResponse {
  success: boolean
  message: string
  matched: boolean
  match_id?: string
}

export const whoLikesMeApi = {
  /**
   * 获取喜欢我的用户列表
   */
  async getWhoLikesMe(
    userId: string,
    limit: number = 20,
    offset: number = 0,
    sortBy: 'time' | 'compatibility' = 'time'
  ): Promise<WhoLikesMeResponse> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/who-likes-me/${testUserId}`, {
      params: { limit, offset, sort_by: sortBy }
    })
    return response.data
  },

  /**
   * 获取喜欢数量（用于徽章）
   */
  async getLikesCount(userId: string): Promise<{ count: number }> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/who-likes-me/count/${testUserId}`)
    return response.data
  },

  /**
   * 回喜欢（会员功能）
   */
  async likeBack(userId: string, targetUserId: string): Promise<LikeBackResponse> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.post(`/api/who-likes-me/like-back?user_id=${testUserId}`, {
      target_user_id: targetUserId
    })
    return response.data
  },

  /**
   * 获取新喜欢数量
   */
  async getNewLikesCount(userId: string, since: string): Promise<{ new_count: number }> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/who-likes-me/new-count/${testUserId}`, {
      params: { since }
    })
    return response.data
  }
}