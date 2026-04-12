// Rose Types - 玫瑰表达系统类型定义

export type RoseSource = 'free_monthly' | 'membership_standard' | 'membership_premium' | 'purchased' | 'gift'

export type RoseStatus = 'available' | 'sent' | 'expired' | 'matched'

export interface RoseBalance {
  user_id: string
  available_count: number
  sent_count: number
  monthly_allocation: number
  next_refresh_date: string
  purchase_available: boolean
}

export interface RoseTransaction {
  id: string
  sender_id: string
  receiver_id: string
  rose_source: RoseSource
  rose_id?: string
  status: RoseStatus
  is_seen: boolean
  message?: string
  compatibility_score?: number
  sent_at: string
  seen_at?: string
  expires_at?: string
  in_standout: boolean
  standout_expires_at?: string
}

export interface RoseSendRequest {
  target_user_id: string
  message?: string
  rose_source?: RoseSource
}

export interface RoseSendResponse {
  success: boolean
  message: string
  roses_remaining: number
  transaction_id?: string
  is_match?: boolean
}

export interface StandoutProfile {
  user_id: string
  user_data: {
    name: string
    age: number
    avatar_url?: string
    location: string
    bio: string
    interests: string[]
  }
  rose_received_at: string
  rose_count: number
  latest_message?: string
  compatibility_score: number
  standout_expires_at: string
  is_liked: boolean
  is_passed: boolean
}

export interface StandoutListResponse {
  profiles: StandoutProfile[]
  total_count: number
  unread_count: number
}

export interface RosePackage {
  type: string
  count: number
  price: number
  original_price: number
  discount?: string
  price_per_rose: number
}

export interface RosePurchaseRequest {
  package_type: string
  payment_method: string
}

export interface RosePurchaseResponse {
  success: boolean
  message: string
  purchase_id?: string
  payment_url?: string
  rose_count: number
}