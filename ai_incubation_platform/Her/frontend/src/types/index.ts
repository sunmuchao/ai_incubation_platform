// AI Native 匹配类型定义

// ==================== 核心类型 ====================

export interface User {
  id: string
  name: string
  age: number
  gender: string
  location: string
  avatar?: string
  avatar_url?: string
  bio: string
  interests: string[]
  goal: string
  verified: boolean
}

// ==================== 滑动机制类型 ====================

export type SwipeDirection = 'left' | 'right' | 'up' | 'down'
export type SwipeAction = 'pass' | 'like' | 'super_like'

export interface SwipeResult {
  action: SwipeAction
  targetUserId: string
  timestamp: number
  isMatch?: boolean
}

export interface SwipeLimit {
  daily_likes: number
  daily_super_likes: number
  likes_used: number
  super_likes_used: number
  likes_remaining: number
  super_likes_remaining: number
  is_unlimited: boolean
}

export interface SwipeFeedbackOverlay {
  type: 'like' | 'pass' | 'super_like'
  visible: boolean
  opacity: number
}

export interface MatchCandidate {
  user: User
  compatibility_score: number
  score_breakdown: Record<string, number>
  common_interests: string[]
  reasoning: string
}

export interface ConversationMatchRequest {
  user_intent: string
  text?: string  // Skill 调用使用的字段
  context?: Record<string, any>
}

// AI Native 问题卡片类型（动态生成）
export interface QuestionOption {
  value: string
  label: string
  icon?: string
}

export interface QuestionCard {
  question: string
  subtitle?: string
  question_type: 'single_choice' | 'multiple_choice' | 'tags'
  options: QuestionOption[]
  dimension: string
  depth?: number  // 追问深度，0=首次提问，1+=追问
}

export interface ConversationMatchResponse {
  success: boolean
  message?: string
  matches?: MatchCandidate[]
  candidates?: MatchCandidate[]  // Skill 返回的候选列表
  suggestions?: string[]
  next_actions?: string[]
  ai_message?: string  // Skill 返回的 AI 消息
  // AI Native 用户画像收集
  question_card?: QuestionCard  // AI 生成的个人信息收集卡片
  need_profile_collection?: boolean  // 是否需要收集信息
}

// 流式响应类型
export interface StreamChunk {
  type: 'text' | 'match' | 'suggestion' | 'done'
  content?: string
  matches?: MatchCandidate[]
  suggestions?: string[]
  next_actions?: string[]
}

export interface DailyRecommendResponse {
  success: boolean
  recommendations?: MatchCandidate[]  // Skill 返回的推荐列表
  matches?: MatchCandidate[]  // 兼容旧名称
  message?: string
  ai_message?: string
}

export interface RelationshipAnalysisRequest {
  match_id: string
  analysis_type: 'health_check' | 'stage_progress' | 'issue_detection'
}

export interface RelationshipAnalysisResponse {
  success: boolean
  report?: {
    health_score: number
    current_stage: string
    interaction_summary: Record<string, any>
    potential_issues: Array<{ description: string; severity: string }>
    recommendations: string[]
  }
  health_score?: number  // Skill 返回的简化字段
  issues?: Array<{ type: string; severity: string; description: string }>
  recommendations?: string[]
  ai_summary?: string
}

// ==================== AI 预沟通类型 ====================

export interface AIPreCommunicationSession {
  session_id: string
  status: 'pending' | 'analyzing' | 'chatting' | 'completed' | 'cancelled'
  user_id_1: string
  user_id_2: string
  hard_check_passed: boolean
  hard_check_result?: HardCheckResult
  values_check_passed: boolean
  values_check_result?: ValuesCheckResult
  conversation_rounds: number
  target_rounds: number
  compatibility_score?: number
  compatibility_report?: CompatibilityReport
  extracted_insights?: ExtractedInsights
  recommendation?: 'recommend' | 'silent' | 'wait'
  recommendation_reason?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface HardCheckResult {
  passed: boolean
  reason?: string
  checks: {
    age_gap?: {
      passed: boolean
      details: string
    }
    relationship_type?: {
      passed: boolean
      details: string
    }
    children_view?: {
      passed: boolean
      details: string
    }
  }
}

export interface ValuesCheckResult {
  passed: boolean
  reason?: string
  probes: Array<{
    type: string
    detected: boolean
  }>
}

export interface CompatibilityReport {
  total_score: number
  max_score: number
  dimensions: {
    hard_indicators: { score: number; max: number }
    values: { score: number; max: number }
    conversation_depth: { score: number; max: number; rounds: number }
    information_quality: { score: number; max: number; insights_count: number }
  }
}

export interface ExtractedInsights {
  settlement_plan?: { detected: boolean; keyword: string; context: string }
  children_plan?: { detected: boolean; keyword: string; context: string }
  marriage_timeline?: { detected: boolean; keyword: string; context: string }
  career_priority?: { detected: boolean; keyword: string; context: string }
  pet_attitude?: { detected: boolean; keyword: string; context: string }
}

export interface AIPreCommunicationMessage {
  id: string
  session_id: string
  sender_agent: string
  content: string
  message_type: 'text' | 'question' | 'answer'
  topic_tag?: string
  round_number: number
  created_at: string
}

export interface TopicSuggestionRequest {
  match_id: string
  context: 'first_chat' | 'follow_up' | 'date_plan' | 'deep_connection'
}

export interface TopicSuggestionResponse {
  success: boolean
  topics: Array<{ topic: string; context: string; category: string }>
  conversation_tips?: string[]
  ai_message?: string
}

export interface CompatibilityAnalysis {
  success: boolean
  compatibility_score?: number
  analysis?: {
    overall_score: number
    dimension_analysis: Record<string, { score: number; description: string }>
    potential_conflicts: Array<{ description: string }>
  }
  ai_interpretation?: string
}

export interface ChatMessage {
  id: string
  sender_id: string
  receiver_id: string
  content: string
  message_type: 'text' | 'image' | 'emoji' | 'voice'
  created_at: string
  is_read: boolean
}

export interface AgentStatus {
  status: 'idle' | 'analyzing' | 'matching' | 'recommending' | 'pushing'
  progress: number
  message: string
  current_action?: string
}

// ==================== WebSocket 类型 ====================

export interface WebSocketMessage {
  type: 'match_updated' | 'new_message' | 'ai_push' | 'awareness_update' | 'typing'
  payload: unknown
  timestamp: string
  user_id?: string
}

export interface WebSocketStatus {
  connected: boolean
  reconnecting: boolean
  lastMessageTime?: string
  error?: string
}

export interface GenerativeCardData {
  type: 'match' | 'analysis' | 'suggestion' | 'notification'
  priority: 'high' | 'medium' | 'low'
  data: unknown
  ai_message: string
  actions: Array<{ label: string; action: string }>
}

// ==================== 功能模块类型导出 ====================

// 关系里程碑、约会建议、双人游戏
export type * from './milestoneTypes'

// 爱之语画像、关系趋势、预警响应
export type * from './loveLanguageTypes'

// 约会模拟、约会辅助
export type * from './dateSimulationTypes'

// 生活融合（自主约会、情感纪念册、部落匹配、数字小家、见家长模拟、压力测试、成长计划、信任背书）
export type * from './lifeIntegrationTypes'