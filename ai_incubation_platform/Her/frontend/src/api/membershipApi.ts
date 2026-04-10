/**
 * 会员订阅 API
 */

import { apiClient } from './apiClient'

export interface MembershipPlan {
  tier: string
  duration_months: number
  price: number
  original_price: number
  discount_rate: number
  features: string[]
  popular: boolean
}

export interface MembershipStatus {
  tier: string
  status: string
  is_active: boolean
  start_date?: string
  end_date?: string
  auto_renew: boolean
  features: string[]
  limits: Record<string, number>
}

export interface MembershipOrder {
  id: string
  user_id: string
  tier: string
  duration_months: number
  amount: number
  status: string
  payment_url?: string
  created_at: string
}

export const membershipApi = {
  /**
   * 获取会员计划列表
   */
  async getPlans(): Promise<MembershipPlan[]> {
    const response = await apiClient.get('/api/membership/plans')
    return response.data
  },

  /**
   * 获取当前会员状态
   */
  async getStatus(): Promise<MembershipStatus> {
    const response = await apiClient.get('/api/membership/status')
    return response.data
  },

  /**
   * 创建会员订单
   */
  async createOrder(data: {
    tier: string
    duration_months?: number
    payment_method?: string
    auto_renew?: boolean
    coupon_code?: string
  }): Promise<MembershipOrder> {
    const response = await apiClient.post('/api/membership/order', data)
    return response.data
  },

  /**
   * 获取订单详情
   */
  async getOrder(orderId: string): Promise<MembershipOrder> {
    const response = await apiClient.get(`/api/membership/order/${orderId}`)
    return response.data
  },

  /**
   * 取消会员
   */
  async cancelMembership(): Promise<void> {
    await apiClient.post('/api/membership/cancel')
  },

  /**
   * 检查功能权限
   */
  async checkFeature(feature: string): Promise<{ allowed: boolean; message: string }> {
    const response = await apiClient.post('/api/membership/check-feature', { feature })
    return response.data
  },

  /**
   * 获取会员权益列表
   */
  async getBenefits(): Promise<any[]> {
    const response = await apiClient.get('/api/membership/benefits')
    return response.data
  },
}

export default membershipApi