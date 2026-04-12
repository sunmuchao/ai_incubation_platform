// Rose API - 玫瑰表达接口
// 参考 Hinge 的玫瑰机制

import apiClient from './apiClient'
import type {
  RoseBalance,
  RoseSendRequest,
  RoseSendResponse,
  StandoutProfile,
  RosePackage,
} from '../types/rose'

export const roseApi = {
  /**
   * 获取玫瑰余额
   */
  async getBalance(): Promise<{
    available_count: number
    sent_count: number
    monthly_allocation: number
    next_refresh_date: string
    purchase_available: boolean
  }> {
    const response = await apiClient.get('/api/rose/balance')
    return response.data
  },

  /**
   * 发送玫瑰
   */
  async sendRose(request: {
    target_user_id: string
    message?: string
  }): Promise<{
    success: boolean
    message: string
    roses_remaining: number
    transaction_id?: string
    is_match?: boolean
  }> {
    const response = await apiClient.post('/api/rose/send', request)
    return response.data
  },

  /**
   * 获取 Standout 列表（收到玫瑰的用户）
   */
  async getStandoutList(): Promise<{
    profiles: StandoutProfile[]
    total_count: number
    unread_count: number
  }> {
    const response = await apiClient.get('/api/rose/standout')
    return response.data
  },

  /**
   * 回应 Standout 用户
   */
  async respondToStandout(
    standoutUserId: string,
    action: 'like' | 'pass'
  ): Promise<{
    success: boolean
    message: string
  }> {
    const response = await apiClient.post('/api/rose/standout/respond', {
      standout_user_id: standoutUserId,
      action,
    })
    return response.data
  },

  /**
   * 获取玫瑰购买套餐
   */
  async getPackages(): Promise<RosePackage[]> {
    const response = await apiClient.get('/api/rose/packages')
    return response.data
  },

  /**
   * 购买玫瑰
   */
  async purchaseRose(packageType: string, paymentMethod: string = 'wechat'): Promise<{
    success: boolean
    message: string
    purchase_id?: string
    payment_url?: string
    rose_count: number
  }> {
    const response = await apiClient.post('/api/rose/purchase', {
      package_type: packageType,
      payment_method: paymentMethod,
    })
    return response.data
  },

  /**
   * 完成购买
   */
  async completePurchase(purchaseId: string): Promise<{
    success: boolean
    message: string
    roses_added: number
    total_available: number
  }> {
    const response = await apiClient.post(`/api/rose/purchase/${purchaseId}/complete`)
    return response.data
  },

  /**
   * 获取玫瑰交易记录
   */
  async getTransactions(limit: number = 20): Promise<{
    transactions: Array<{
      id: string
      direction: 'sent' | 'received'
      target_user_id: string
      rose_source: string
      status: string
      message?: string
      compatibility_score?: number
      is_seen: boolean
      sent_at: string
      seen_at?: string
    }>
    total: number
  }> {
    const response = await apiClient.get('/api/rose/transactions', {
      params: { limit },
    })
    return response.data
  },
}

export default roseApi