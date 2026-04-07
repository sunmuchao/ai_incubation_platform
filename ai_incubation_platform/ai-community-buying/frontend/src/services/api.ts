import axios, { AxiosError, AxiosRequestConfig } from 'axios'
import type {
  ApiResponse,
  Product,
  GroupBuy,
  Order,
  User,
  Coupon,
  CouponTemplate,
  OrganizerProfile,
  CommissionRecord,
  Notification,
  DashboardStats,
  ProductFilter,
  OrderFilter,
  PaginatedResponse,
  GroupPrediction,
  Campaign,
  Achievement,
  Leaderboard,
  SalesReport,
} from '@/types'

// 创建 axios 实例
const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8005',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['X-Request-ID'] = generateRequestId()
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error: AxiosError<ApiResponse>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }

    if (error.response?.status === 500) {
      console.error('Server error:', error.response.data)
    }

    return Promise.reject({
      status: error.response?.status,
      message: (error.response?.data as ApiResponse)?.message || error.message,
      code: (error.response?.data as ApiResponse)?.code,
    })
  }
)

function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  return api(config)
}

// ============ 商品 API ============
export const productApi = {
  getList: (filter?: ProductFilter) => {
    const params = new URLSearchParams()
    if (filter?.keyword) params.append('keyword', filter.keyword)
    if (filter?.category) params.append('category', filter.category)
    if (filter?.status) params.append('status', filter.status)
    if (filter?.sortBy) params.append('sort_by', filter.sortBy)
    if (filter?.sortOrder) params.append('sort_order', filter.sortOrder)
    if (filter?.page) params.append('page', String(filter.page))
    if (filter?.pageSize) params.append('page_size', String(filter.pageSize))

    return request<PaginatedResponse<Product>>({
      url: '/api/products',
      method: 'GET',
      params,
    })
  },

  getById: (id: number) => {
    return request<Product>({
      url: `/api/products/${id}`,
      method: 'GET',
    })
  },

  create: (data: { name: string; price: number; stock: number; category?: string }) => {
    return request<Product>({
      url: '/api/products',
      method: 'POST',
      data,
    })
  },

  update: (id: number, data: Partial<Product>) => {
    return request<Product>({
      url: `/api/products/${id}`,
      method: 'PUT',
      data,
    })
  },

  delete: (id: number) => {
    return request<void>({
      url: `/api/products/${id}`,
      method: 'DELETE',
    })
  },

  getHot: (limit = 10) => {
    return request<Product[]>({
      url: '/api/recommendation/hot',
      method: 'GET',
      params: { limit },
    })
  },
}

// ============ 团购 API ============
export const groupBuyApi = {
  getList: (status?: string) => {
    const params = status ? { status } : {}
    return request<GroupBuy[]>({
      url: '/api/groups',
      method: 'GET',
      params,
    })
  },

  getById: (id: number) => {
    return request<GroupBuy>({
      url: `/api/groups/${id}`,
      method: 'GET',
    })
  },

  create: (data: { productId: number; targetQuantity: number; deadlineHours?: number; leaderId?: string }) => {
    return request<GroupBuy>({
      url: '/api/groups',
      method: 'POST',
      data,
    })
  },

  join: (id: number, userId: string) => {
    return request<GroupBuy>({
      url: `/api/groups/${id}/join`,
      method: 'POST',
      data: { user_id: userId },
    })
  },

  getPrediction: (id: number) => {
    return request<GroupPrediction>({
      url: `/api/ai/group-prediction/${id}`,
      method: 'GET',
    })
  },

  getBatchPredictions: () => {
    return request<GroupPrediction[]>({
      url: '/api/ai/group-predictions',
      method: 'GET',
    })
  },
}

// ============ 订单 API ============
export const orderApi = {
  getList: (filter?: OrderFilter) => {
    const params = new URLSearchParams()
    if (filter?.status) params.append('status', filter.status)
    if (filter?.keyword) params.append('keyword', filter.keyword)
    if (filter?.page) params.append('page', String(filter.page))
    if (filter?.pageSize) params.append('page_size', String(filter.pageSize))

    return request<PaginatedResponse<Order>>({
      url: '/api/orders',
      method: 'GET',
      params,
    })
  },

  getById: (id: number) => {
    return request<Order>({
      url: `/api/orders/${id}`,
      method: 'GET',
    })
  },

  create: (data: { productId: number; quantity: number; groupBuyId?: number }) => {
    return request<Order>({
      url: '/api/orders',
      method: 'POST',
      data,
    })
  },

  cancel: (id: number) => {
    return request<Order>({
      url: `/api/orders/${id}/cancel`,
      method: 'POST',
    })
  },
}

// ============ 用户 API ============
export const userApi = {
  getProfile: () => {
    return request<User>({
      url: '/api/user/profile',
      method: 'GET',
    })
  },

  updateProfile: (data: Partial<User>) => {
    return request<User>({
      url: '/api/user/profile',
      method: 'PUT',
      data,
    })
  },
}

// ============ 优惠券 API ============
export const couponApi = {
  getTemplates: () => {
    return request<CouponTemplate[]>({
      url: '/api/coupons/templates',
      method: 'GET',
    })
  },

  claim: (templateId: number) => {
    return request<Coupon>({
      url: '/api/coupons/claim',
      method: 'POST',
      data: { template_id: templateId },
    })
  },

  getUserCoupons: (userId: string) => {
    return request<Coupon[]>({
      url: `/api/coupons/users/${userId}`,
      method: 'GET',
    })
  },
}

// ============ 团长 API ============
export const organizerApi = {
  getProfile: (userId: string) => {
    return request<OrganizerProfile>({
      url: `/api/commission/organizers/${userId}`,
      method: 'GET',
    })
  },

  getRanking: () => {
    return request<OrganizerProfile[]>({
      url: '/api/commission/organizers',
      method: 'GET',
    })
  },

  getCommissionRecords: (userId: string) => {
    return request<CommissionRecord[]>({
      url: `/api/commission/organizers/${userId}/records`,
      method: 'GET',
    })
  },

  withdraw: (amount: number) => {
    return request<void>({
      url: '/api/commission/withdraw',
      method: 'POST',
      data: { amount },
    })
  },
}

// ============ 通知 API ============
export const notificationApi = {
  getList: (userId: string, unreadOnly = false) => {
    return request<Notification[]>({
      url: '/api/notifications',
      method: 'GET',
      params: { user_id: userId, unread_only: unreadOnly },
    })
  },

  markAsRead: (ids: number[]) => {
    return request<void>({
      url: '/api/notifications/mark-read',
      method: 'POST',
      data: { notification_ids: ids },
    })
  },

  markAllAsRead: () => {
    return request<void>({
      url: '/api/notifications/mark-all-read',
      method: 'POST',
    })
  },
}

// ============ 数据统计 API ============
export const analyticsApi = {
  getDashboardStats: () => {
    return request<DashboardStats>({
      url: '/api/analytics/dashboard',
      method: 'GET',
    })
  },

  getSalesReport: (startDate: string, endDate: string) => {
    return request<SalesReport[]>({
      url: '/api/analytics/sales-reports',
      method: 'GET',
      params: { start_date: startDate, end_date: endDate },
    })
  },
}

// ============ 活动 API ============
export const campaignApi = {
  getList: (status?: string) => {
    return request<Campaign[]>({
      url: '/api/p3/campaigns',
      method: 'GET',
      params: { status },
    })
  },

  create: (data: Partial<Campaign>) => {
    return request<Campaign>({
      url: '/api/p3/campaigns',
      method: 'POST',
      data,
    })
  },
}

// ============ 成就 API ============
export const achievementApi = {
  getUserAchievements: (userId: string) => {
    return request<Achievement[]>({
      url: '/api/p7/achievements',
      method: 'GET',
      params: { user_id: userId },
    })
  },
}

// ============ 排行榜 API ============
export const leaderboardApi = {
  get: (type: string, period: string) => {
    return request<Leaderboard>({
      url: '/api/p7/leaderboards',
      method: 'GET',
      params: { type, period },
    })
  },
}

// ============ AI 工具 API ============
export const aiToolsApi = {
  getProductSelection: (historicalSales: any[]) => {
    return request<any>({
      url: '/api/tools/product-selection',
      method: 'POST',
      data: { historical_sales: historicalSales },
    })
  },

  getStockAlert: (threshold = 10) => {
    return request<any[]>({
      url: '/api/tools/stock-alert',
      method: 'GET',
      params: { threshold },
    })
  },

  getDynamicPrice: (productId: number, communityId: string) => {
    return request<any>({
      url: `/api/dynamic-pricing/calculate/${productId}/${communityId}`,
      method: 'GET',
    })
  },
}

export { api }
