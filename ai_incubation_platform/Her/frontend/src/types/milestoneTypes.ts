/**
 * 关系里程碑类型定义
 */

// ==================== 里程碑类型 ====================

export interface Milestone {
  id: string
  user_id_1: string
  user_id_2: string
  milestone_type: MilestoneType
  title: string
  description: string
  milestone_date: string
  user_rating?: number
  user_note?: string
  celebration_suggested: boolean
  ai_analysis?: MilestoneAIAnalysis
  is_private: boolean
  created_at: string
}

export type MilestoneType =
  | 'first_match'           // 第一次匹配
  | 'first_chat'            // 第一次聊天
  | 'first_date'            // 第一次约会
  | 'first_video_call'      // 第一次视频通话
  | 'relationship_start'    // 开始交往
  | 'anniversary'           // 纪念日
  | 'moved_in_together'     // 同居
  | 'engaged'               // 订婚
  | 'married'               // 结婚
  | 'custom'                // 自定义

export interface MilestoneAIAnalysis {
  significance_score: number  // 重要性评分 0-1
  relationship_stage: string  // 关系阶段
  growth_indicators: string[] // 成长指标
  suggestions: string[]       // 建议
}

export interface MilestoneTimeline {
  milestones: Milestone[]
  relationship_duration_days: number
  milestone_count: number
  average_rating: number
}

export interface MilestoneStatistics {
  total_milestones: number
  by_type: Record<string, number>
  by_month: Record<string, number>
  relationship_score: number
  growth_trend: 'improving' | 'stable' | 'declining'
}

// ==================== 约会建议类型 ====================

export interface DateSuggestion {
  id: string
  user_id: string
  target_user_id?: string
  date_type: DateType
  venue: DateVenue
  suggested_activities: string[]
  estimated_duration: string
  price_range: string
  ai_reasoning: string
  compatibility_score: number
  status: 'pending' | 'accepted' | 'rejected' | 'countered' | 'completed'
  created_at: string
}

export type DateType =
  | 'coffee'          // 咖啡
  | 'dining'          // 用餐
  | 'movie'           // 电影
  | 'outdoor'         // 户外
  | 'culture'         // 文化
  | 'sports'          // 运动
  | 'entertainment'   // 娱乐
  | 'creative'        // 创意

export interface DateVenue {
  id: string
  name: string
  address: string
  city: string
  latitude: number
  longitude: number
  venue_type: string
  rating: number
  price_level: number  // 1-5
  tags: string[]
  suitable_for: string[]
  image_url?: string
}

export interface DateSuggestionRequest {
  date_type?: DateType
  city?: string
  budget_range?: string
  preferences?: Record<string, any>
}

// ==================== 双人互动游戏类型 ====================

export interface CoupleGame {
  id: string
  user_id_1: string
  user_id_2: string
  game_type: GameType
  game_config: GameConfig
  status: 'pending' | 'in_progress' | 'completed'
  current_round: number
  total_rounds: number
  player1_score?: number
  player2_score?: number
  insights?: GameInsights
  created_at: string
  started_at?: string
  completed_at?: string
}

export type GameType =
  | 'qna_mutual'        // 互相问答
  | 'values_quiz'       // 价值观测试
  | 'preference_match'  // 偏好匹配
  | 'personality_quiz'  // 性格测试
  | 'love_language'     // 爱之语测试

export interface GameConfig {
  difficulty: 'easy' | 'normal' | 'hard'
  question_count: number
  time_limit_seconds?: number
  custom_questions?: string[]
}

export interface GameRound {
  round_number: number
  question: string
  player1_answer?: string
  player2_answer?: string
  match_score?: number
  insight?: string
}

export interface GameInsights {
  compatibility_score: number
  similarity_areas: string[]
  difference_areas: string[]
  suggestions: string[]
  ai_summary: string
}

export interface CoupleGameCreateRequest {
  game_type: GameType
  difficulty?: 'easy' | 'normal' | 'hard'
  custom_config?: Partial<GameConfig>
}

// ==================== API 响应类型 ====================

export interface RecordMilestoneRequest {
  user_id_1: string
  user_id_2: string
  milestone_type: MilestoneType
  title: string
  description: string
  milestone_date?: string
  celebration_suggested?: boolean
  is_private?: boolean
}

export interface UpdateMilestoneRequest {
  title?: string
  description?: string
  user_rating?: number
  user_note?: string
}

export interface RespondToDateSuggestionRequest {
  action: 'accept' | 'reject' | 'counter'
  feedback?: string
  counter_suggestion?: string
}

export interface SubmitGameRoundRequest {
  game_id: string
  round_number: number
  answer: string
  user_id: string
}