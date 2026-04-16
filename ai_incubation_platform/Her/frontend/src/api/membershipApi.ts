/**
 * 会员订阅 API
 *
 * 对接后端 /api/membership 端点
 */

import apiClient from './apiClient'

// ==================== 类型定义 ====================

export interface MembershipPlan {
  tier: string
  duration_months: number
  price: number
  original_price: number
  discount_rate: number
  features: string[]
  popular: boolean
}

export interface MembershipBenefit {
  feature: string
  name: string
  description: string
  icon: string
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

export interface CreateOrderRequest {
  tier: string
  duration_months: number
  payment_method: 'wechat' | 'alipay'
  auto_renew?: boolean
  coupon_code?: string
}

export interface DailyUsage {
  daily_likes: number
  daily_super_likes: number
  likes_used: number
  super_likes_used: number
  likes_remaining: number
  super_likes_remaining: number
  rewinds_used: number
  rewinds_remaining: number
  boosts_used: number
  boosts_remaining: number
  is_unlimited: boolean
}

// ==================== API ====================

export const membershipApi = {
  /**
   * 获取所有会员计划
   */
  async getPlans(): Promise<MembershipPlan[]> {
    const response = await apiClient.get('/api/membership/plans')
    return response.data
  },

  /**
   * 获取会员权益说明
   */
  async getBenefits(): Promise<MembershipBenefit[]> {
    const response = await apiClient.get('/api/membership/benefits')
    return response.data
  },

  /**
   * 获取当前用户的会员状态
   */
  async getStatus(): Promise<MembershipStatus> {
    const response = await apiClient.get('/api/membership/status')
    return response.data
  },

  /**
   * 创建会员订单
   */
  async createOrder(request: CreateOrderRequest): Promise<MembershipOrder> {
    const response = await apiClient.post('/api/membership/order', request)
    return response.data
  },

  /**
   * 获取用户每日使用情况
   */
  async getDailyUsage(userId: string): Promise<DailyUsage> {
    const response = await apiClient.get(`/api/membership/usage/${userId}/daily`)
    return response.data
  },

  /**
   * 检查功能权限
   */
  async checkFeatureAccess(feature: string): Promise<{ allowed: boolean; message: string }> {
    const response = await apiClient.post('/api/membership/check-feature', { feature })
    return response.data
  },

  /**
   * 取消自动续费
   */
  async cancelSubscription(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post('/api/membership/cancel-subscription')
    return response.data
  },

  /**
   * 对比不同会员等级的权益
   */
  async compareTiers(): Promise<{
    features: Array<{ feature: string; availability: Record<string, boolean> }>
    tiers: string[]
    pricing: Record<string, Record<string, number>>
  }> {
    const response = await apiClient.get('/api/membership/compare')
    return response.data
  },
}

export default membershipApi