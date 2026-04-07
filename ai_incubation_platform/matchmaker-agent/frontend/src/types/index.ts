// AI Native 匹配类型定义

export interface User {
  id: string
  name: string
  age: number
  gender: string
  location: string
  avatar_url: string
  bio: string
  interests: string[]
  goal: string
  verified: boolean
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
  context?: Record<string, any>
}

export interface ConversationMatchResponse {
  success: boolean
  message: string
  matches?: MatchCandidate[]
  suggestions?: string[]
  next_actions?: string[]
}

export interface DailyRecommendResponse extends ConversationMatchResponse {}

export interface RelationshipAnalysisRequest {
  match_id: string
  analysis_type: 'health_check' | 'stage_progress' | 'issue_detection'
}

export interface RelationshipAnalysisResponse {
  success: boolean
  report: {
    health_score: number
    current_stage: string
    interaction_summary: Record<string, any>
    potential_issues: Array<{ description: string; severity: string }>
    recommendations: string[]
  }
  ai_summary: string
  recommendations: string[]
}

export interface TopicSuggestionRequest {
  match_id: string
  context: 'first_chat' | 'follow_up' | 'date_plan' | 'deep_connection'
}

export interface TopicSuggestionResponse {
  success: boolean
  topics: Array<{ topic: string; context: string; category: string }>
  conversation_tips: string[]
  ai_message: string
}

export interface CompatibilityAnalysis {
  success: boolean
  analysis: {
    overall_score: number
    dimension_analysis: Record<string, { score: number; description: string }>
    potential_conflicts: Array<{ description: string }>
  }
  ai_interpretation: string
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

export interface GenerativeCardData {
  type: 'match' | 'analysis' | 'suggestion' | 'notification'
  priority: 'high' | 'medium' | 'low'
  data: any
  ai_message: string
  actions: Array<{ label: string; action: string }>
}
