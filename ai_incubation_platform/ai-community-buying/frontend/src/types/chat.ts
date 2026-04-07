/**
 * AI Native 对话式交互类型定义
 */

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  suggestions?: ChatSuggestion[]
  action?: ChatActionType
  data?: ChatData
  confidence?: number
  trace_id?: string
}

export interface ChatSuggestion {
  text: string
  action?: ChatActionType
  params?: Record<string, any>
}

export type ChatActionType =
  | 'create_group'
  | 'find_product'
  | 'check_status'
  | 'view_detail'
  | 'invite'
  | 'general_chat'

export interface ChatData {
  // 商品数据
  products?: ProductData[]
  // 团购数据
  group?: GroupData
  groups?: GroupData[]
  // 预测数据
  prediction?: PredictionData
  // 其他附加数据
  [key: string]: any
}

export interface ProductData {
  id: number | string
  name: string
  price: number
  group_price?: number
  image?: string
  category?: string
  description?: string
  reason?: string
  success_probability?: number
  stock?: number
  sales?: number
}

export interface GroupData {
  id: number | string
  product_name: string
  product_id?: number
  group_price: number
  min_participants: number
  current_participants?: number
  deadline: string
  status?: string
  leader_id?: string
  estimated_complete_time?: string
}

export interface PredictionData {
  success_probability: number
  confidence: 'high' | 'medium' | 'low'
  factors?: string[]
  estimated_complete_time?: string
}

export interface ChatRequest {
  user_id: string
  message: string
  session_id?: string
  community_id?: string
  conversation_history?: Array<{
    role: string
    content: string
    timestamp?: string
  }>
}

export interface ChatResponse {
  success: boolean
  message: string
  session_id: string
  suggestions: ChatSuggestion[]
  action?: ChatActionType
  data?: ChatData
  confidence: number
  trace_id?: string
}

export interface SessionInfo {
  session_id: string
  user_id: string
  created_at: string
  last_active_at: string
  message_count: number
  current_intent?: string
  slot_values: Record<string, any>
}

export interface AgentState {
  status: 'idle' | 'thinking' | 'executing' | 'waiting' | 'completed' | 'failed'
  currentAction?: string
  progress?: number
  message?: string
}
