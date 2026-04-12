/**
 * 约会模拟类型定义
 */

// ==================== AI 分身类型 ====================

export interface AIDateAvatar {
  id: string
  user_id: string
  avatar_name: string
  personality_traits: PersonalityTrait[]
  conversation_style: ConversationStyle
  appearance_config: AppearanceConfig
  scenario_preferences: ScenarioType[]
  skill_levels: SkillLevels
  created_at: string
  updated_at: string
}

export interface PersonalityTrait {
  trait: string
  intensity: number  // 0-1
}

export type ConversationStyle =
  | 'humorous'      // 幽默型
  | 'gentle'        // 温柔型
  | 'direct'        // 直接型
  | 'thoughtful'    // 思考型
  | 'playful'       // 活泼型

export interface AppearanceConfig {
  age_range: string
  style_tags: string[]
  preferred_attire: string[]
}

export interface SkillLevels {
  active_listening: number  // 0-100
  empathy: number
  humor: number
  depth: number
  conflict_resolution: number
}

export interface CreateAIDateAvatarRequest {
  avatar_name: string
  personality_traits: PersonalityTrait[]
  conversation_style: ConversationStyle
  target_user_profile?: Record<string, any>
}

// ==================== 约会模拟类型 ====================

export interface DateSimulation {
  id: string
  user_id: string
  avatar_id: string
  scenario_type: ScenarioType
  scenario_config: ScenarioConfig
  status: 'not_started' | 'in_progress' | 'completed'
  current_stage: string
  conversation_history: ConversationTurn[]
  feedback_records: SimulationFeedback[]
  overall_score?: number
  ai_summary?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export type ScenarioType =
  | 'first_coffee'        // 第一次咖啡约会
  | 'first_dinner'        // 第一次晚餐
  | 'casual_walk'         // 散步聊天
  | 'movie_date'          // 电影约会
  | 'activity_date'       // 活动约会
  | 'difficult_topic'     // 困难话题讨论
  | 'conflict_resolution' // 冲突解决
  | 'deep_conversation'   // 深度对话

export interface ScenarioConfig {
  difficulty: 'easy' | 'medium' | 'hard'
  duration_minutes: number
  focus_areas: string[]
  custom_context?: string
}

export interface ConversationTurn {
  turn_number: number
  speaker: 'user' | 'ai'
  content: string
  emotion_detected?: string
  suggested_alternatives?: string[]
  score?: number
  feedback?: string
}

export interface SimulationFeedback {
  turn_number: number
  category: FeedbackCategory
  score: number
  comment: string
  suggestion: string
}

export type FeedbackCategory =
  | 'active_listening'
  | 'empathy'
  | 'humor'
  | 'respect'
  | 'authenticity'
  | 'engagement'
  | 'boundaries'

export interface StartSimulationRequest {
  avatar_id: string
  scenario_type: ScenarioType
  scenario_config?: Partial<ScenarioConfig>
}

export interface SubmitSimulationTurnRequest {
  simulation_id: string
  user_response: string
}

// ==================== 穿搭推荐类型 ====================

export interface OutfitRecommendation {
  id: string
  user_id: string
  scenario_type: ScenarioType
  weather_condition: WeatherCondition
  venue_type: string
  time_of_day: string
  outfit_items: OutfitItem[]
  style_description: string
  comfort_level: number  // 0-100
  appropriateness_score: number  // 0-100
  ai_reasoning: string
  created_at: string
}

export interface OutfitItem {
  category: 'top' | 'bottom' | 'shoes' | 'accessories' | 'outerwear'
  item_name: string
  color: string
  style: string
  image_url?: string
}

export interface WeatherCondition {
  temperature: number
  condition: 'sunny' | 'cloudy' | 'rainy' | 'snowy' | 'windy'
  humidity: number
  uv_index: number
}

export interface GetOutfitRecommendationRequest {
  scenario_type: ScenarioType
  venue_name?: string
  date_time: string
  user_preferences?: Record<string, any>
}

// ==================== 场所策略类型 ====================

export interface VenueStrategy {
  id: string
  venue_id: string
  venue_name: string
  venue_type: string
  atmosphere: string
  best_seating: string
  conversation_topics: TopicSuggestion[]
  etiquette_tips: string[]
  red_flags_to_watch: string[]
  exit_strategies: string[]
  ai_tips: string[]
}

export interface TopicSuggestion {
  category: 'icebreaker' | 'light' | 'deep' | 'fun' | 'values'
  topic: string
  follow_up_questions: string[]
  timing_suggestion: string
}

export interface GetVenueStrategyRequest {
  venue_id?: string
  venue_name: string
  date_type: ScenarioType
}

// ==================== 话题锦囊类型 ====================

export interface TopicKit {
  id: string
  user_id: string
  scenario_type: ScenarioType
  relationship_stage: RelationshipStage
  topic_categories: TopicCategory[]
  emergency_topics: TopicSuggestion[]
  personalized_topics: TopicSuggestion[]
  ai_recommendations: string[]
  created_at: string
}

export interface TopicCategory {
  category: string
  description: string
  topics: TopicSuggestion[]
  best_timing: string
}

export type RelationshipStage =
  | 'first_meeting'
  | 'getting_to_know'
  | 'dating'
  | 'exclusive'
  | 'committed'

export interface GetTopicKitRequest {
  scenario_type: ScenarioType
  relationship_stage: RelationshipStage
  conversation_context?: 'first_chat' | 'follow_up' | 'stuck' | 'deepening'
}

// ==================== 多代理协作类型 ====================

export interface MultiAgentSession {
  id: string
  user_id: string
  session_type: 'date_coaching' | 'relationship_analysis' | 'safety_review'
  participating_agents: AgentInfo[]
  session_data: SessionData
  combined_insights: AgentInsight[]
  action_recommendations: string[]
  created_at: string
}

export interface AgentInfo {
  agent_type: 'matchmaker' | 'coach' | 'security'
  agent_name: string
  role_description: string
  confidence_score: number
}

export interface SessionData {
  context: string
  user_concerns: string[]
  goals: string[]
}

export interface AgentInsight {
  agent_type: AgentType
  insight: string
  confidence: number
  evidence: string[]
  recommendation: string
}

export type AgentType = 'matchmaker' | 'coach' | 'security'