// 基础类型定义

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  code?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// 用户相关
export interface User {
  id: string
  nickname: string
  avatar?: string
  phone?: string
  email?: string
  memberLevel?: MemberLevel
  points?: number
  createdAt: string
}

export interface UserProfile {
  id: string
  nickname: string
  avatar?: string
  phone?: string
  email?: string
  addresses: Address[]
  memberLevel: MemberLevel
  points: number
  coupons: Coupon[]
}

export interface Address {
  id: string
  userId: string
  name: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  isDefault: boolean
}

export interface MemberLevel {
  level: number
  name: string
  growthValue: number
  benefits: string[]
}

// 商品相关
export interface Product {
  id: number
  name: string
  description?: string
  price: number
  originalPrice?: number
  stock: number
  soldStock?: number
  lockedStock?: number
  category?: string
  imageUrl?: string
  images?: string[]
  status: 'active' | 'inactive' | 'sold_out'
  minGroupSize?: number
  maxGroupSize?: number
  createdAt: string
  updatedAt: string
}

export interface ProductCreate {
  name: string
  description?: string
  price: number
  originalPrice?: number
  stock: number
  category?: string
  imageUrl?: string
  minGroupSize?: number
  maxGroupSize?: number
}

// 团购相关
export interface GroupBuy {
  id: number
  productId: number
  product?: Product
  organizerId: string
  organizer?: User
  targetQuantity: number
  joinedCount: number
  status: 'open' | 'success' | 'failed' | 'expired'
  deadline: string
  createdAt: string
  members?: string[]
}

export interface GroupBuyCreate {
  productId: number
  organizerId: string
  targetQuantity: number
  deadlineHours?: number
}

export interface GroupPrediction {
  groupBuyId: number
  probability: number
  confidence: number
  factors: PredictionFactor[]
  prediction: 'likely' | 'unlikely' | 'uncertain'
  createdAt: string
}

export interface PredictionFactor {
  name: string
  value: number
  impact: 'positive' | 'negative' | 'neutral'
}

// 订单相关
export interface Order {
  id: number
  orderNo: string
  userId: string
  user?: User
  productId: number
  product?: Product
  groupBuyId?: number
  groupBuy?: GroupBuy
  quantity: number
  unitPrice: number
  totalAmount: number
  status: 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'refunded'
  address?: Address
  createdAt: string
  paidAt?: string
  shippedAt?: string
  completedAt?: string
}

export interface OrderCreate {
  productId: number
  quantity: number
  addressId: string
  groupBuyId?: number
  couponId?: string
}

// 购物车
export interface CartItem {
  id: string
  productId: number
  product?: Product
  quantity: number
  selected: boolean
  groupBuyId?: number
}

// 优惠券
export interface Coupon {
  id: number
  templateId: number
  templateName: string
  code: string
  type: 'discount' | 'fixed' | 'percentage'
  value: number
  minPurchase: number
  maxDiscount?: number
  status: 'unused' | 'used' | 'expired'
  validFrom: string
  validTo: string
  userId?: string
}

export interface CouponTemplate {
  id: number
  name: string
  type: 'discount' | 'fixed' | 'percentage'
  value: number
  minPurchase: number
  maxDiscount?: number
  totalCount: number
  issuedCount: number
  validFrom: string
  validTo: string
  status: 'active' | 'inactive'
}

// 团长相关
export interface OrganizerProfile {
  userId: string
  user?: User
  totalGroups: number
  successGroups: number
  totalOrders: number
  totalCommission: number
  availableCommission: number
  withdrawnCommission: number
  rating: number
  level: string
  status: 'active' | 'inactive'
}

export interface CommissionRecord {
  id: number
  organizerId: string
  groupBuyId: number
  orderId: number
  amount: number
  status: 'pending' | 'paid' | 'withdrawn'
  createdAt: string
  paidAt?: string
}

// 统计数据
export interface DashboardStats {
  totalUsers: number
  totalProducts: number
  totalGroups: number
  totalOrders: number
  totalSales: number
  successRate: number
  growthRate: number
}

export interface SalesReport {
  date: string
  sales: number
  orders: number
  users: number
}

// 通知
export interface Notification {
  id: number
  userId: string
  type: 'system' | 'order' | 'group' | 'promotion'
  title: string
  content: string
  isRead: boolean
  createdAt: string
  readAt?: string
}

// AI 推荐
export interface ProductRecommendation {
  productId: number
  product?: Product
  score: number
  reason: string
  factors: RecommendationFactor[]
}

export interface RecommendationFactor {
  name: string
  weight: number
  description: string
}

// 活动相关
export interface Campaign {
  id: number
  name: string
  type: 'flash_sale' | 'group_buy' | 'coupon' | 'newbie'
  status: 'pending' | 'active' | 'ended'
  startTime: string
  endTime: string
  description?: string
  rules: Record<string, any>
}

// 成就
export interface Achievement {
  id: number
  userId: string
  achievementId: number
  name: string
  description: string
  icon: string
  achievedAt: string
}

// 排行榜
export interface Leaderboard {
  type: 'order' | 'spending' | 'points' | 'invite'
  period: 'daily' | 'weekly' | 'monthly' | 'all'
  items: LeaderboardItem[]
}

export interface LeaderboardItem {
  rank: number
  userId: string
  user?: User
  value: number
  change: number
}

// 搜索和筛选
export interface ProductFilter {
  keyword?: string
  category?: string
  priceRange?: [number, number]
  status?: string
  sortBy?: 'created_at' | 'price' | 'sales' | 'stock'
  sortOrder?: 'asc' | 'desc'
  page?: number
  pageSize?: number
}

export interface OrderFilter {
  status?: string
  dateRange?: [string, string]
  keyword?: string
  page?: number
  pageSize?: number
}

// WebSocket 消息
export interface WebSocketMessage {
  type: 'notification' | 'order_update' | 'group_update' | 'price_update'
  data: any
  timestamp: string
}

// 主题和设置
export interface AppSettings {
  theme: 'light' | 'dark'
  language: 'zh' | 'en'
  notifications: boolean
  soundEnabled: boolean
}

// AI Native 对话类型
export * from './chat'
