// Gift API - 虚拟礼物接口
// 参考 Soul/探探的礼物系统

import apiClient from './apiClient'
import type { Gift, GiftTransaction, UserGiftStats } from '../types/gift'

export const giftApi = {
  /**
   * 获取礼物商店
   */
  async getGiftStore(): Promise<{
    categories: Array<{ id: string; name: string; icon: string }>
    gifts: Gift[]
    popular_gifts: Gift[]
    new_gifts: Gift[]
  }> {
    const response = await apiClient.get('/api/gift/store')
    return response.data
  },

  /**
   * 获取单个礼物信息
   */
  async getGift(giftId: string): Promise<Gift> {
    const response = await apiClient.get(`/api/gift/${giftId}`)
    return response.data
  },

  /**
   * 发送礼物
   */
  async sendGift(request: {
    target_user_id: string
    gift_id: string
    count: number
    message?: string
  }): Promise<{
    success: boolean
    message: string
    gift_id: string
    gift_name: string
    total_price: number
    transaction_id?: string
  }> {
    const response = await apiClient.post('/api/gift/send', request)
    return response.data
  },

  /**
   * 获取收到的礼物列表
   */
  async getReceivedGifts(limit: number = 20): Promise<Array<{
    id: string
    sender_id: string
    sender_name?: string
    sender_avatar?: string
    gift_id: string
    gift_name: string
    gift_icon: string
    gift_type: string
    count: number
    price: number
    total_amount: number
    message?: string
    sent_at: string
    is_seen: boolean
  }>> {
    const response = await apiClient.get('/api/gift/received', {
      params: { limit },
    })
    return response.data
  },

  /**
   * 获取发送的礼物列表
   */
  async getSentGifts(limit: number = 20): Promise<Array<{
    id: string
    sender_id: string
    sender_name?: string
    sender_avatar?: string
    gift_id: string
    gift_name: string
    gift_icon: string
    gift_type: string
    count: number
    price: number
    total_amount: number
    message?: string
    sent_at: string
    is_seen: boolean
  }>> {
    const response = await apiClient.get('/api/gift/sent', {
      params: { limit },
    })
    return response.data
  },

  /**
   * 获取用户礼物统计
   */
  async getStats(): Promise<UserGiftStats & { unseen_count: number }> {
    const response = await apiClient.get('/api/gift/stats')
    return response.data
  },

  /**
   * 标记礼物已查看
   */
  async markGiftSeen(transactionId: string): Promise<{
    success: boolean
    message: string
  }> {
    const response = await apiClient.post(`/api/gift/${transactionId}/seen`)
    return response.data
  },

  /**
   * 获取未查看礼物数量
   */
  async getUnseenCount(): Promise<{ unseen_count: number }> {
    const response = await apiClient.get('/api/gift/unseen-count')
    return response.data
  },
}

export default giftApi