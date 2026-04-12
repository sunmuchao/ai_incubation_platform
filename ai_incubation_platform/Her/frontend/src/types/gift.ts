// Gift Types - 虚拟礼物系统类型定义

export type GiftType = 'free' | 'basic' | 'standard' | 'premium' | 'special' | 'animated' | 'physical'

export type GiftCategory = 'love' | 'birthday' | 'funny' | 'food' | 'flower' | 'animal' | 'travel' | 'festival'

export interface Gift {
  id: string
  name: string
  type: GiftType
  category: GiftCategory
  price: number
  icon: string
  animation?: string
  description: string
  fullscreen: boolean
  is_popular: boolean
  is_new: boolean
}

export interface GiftTransaction {
  id: string
  sender_id: string
  receiver_id: string
  gift_id: string
  gift_name: string
  gift_icon: string
  gift_type: GiftType
  count: number
  price: number
  total_amount: number
  message?: string
  sent_at: string
  is_seen: boolean
  seen_at?: string
}

export interface GiftSendRequest {
  target_user_id: string
  gift_id: string
  count: number
  message?: string
}

export interface GiftSendResponse {
  success: boolean
  message: string
  gift_id: string
  gift_name: string
  total_price: number
  transaction_id?: string
}

export interface UserGiftStats {
  user_id: string
  total_received: number
  total_received_amount: number
  total_sent: number
  total_sent_amount: number
  most_received_gift?: string
  most_sent_gift?: string
  top_sender?: string
  top_receiver?: string
}

export interface GiftStoreResponse {
  categories: Array<{ id: string; name: string; icon: string }>
  gifts: Gift[]
  popular_gifts: Gift[]
  new_gifts: Gift[]
}