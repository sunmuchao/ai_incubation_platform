/**
 * Agent Skill 类型定义
 */

// Skill 元数据
export interface SkillMetadata {
  name: string
  description: string
  version: string
  priority: 'P0' | 'P1' | 'P2' | 'P19'
  category: string
  tags: string[]
  available: boolean
}

// Skill 输入/输出 Schema
export interface SkillSchema {
  type: string
  properties: Record<string, any>
  required?: string[]
}

// Skill 执行请求
export interface SkillExecuteRequest {
  skill_name: string
  params: Record<string, any>
  context?: Record<string, any>
}

// Skill 执行响应
export interface SkillExecuteResponse {
  success: boolean
  data?: {
    ai_message: string
    matches?: MatchCandidate[]
    generative_ui?: GenerativeUIConfig
    suggested_actions?: SkillAction[]
    [key: string]: any
  }
  error?: string
  ai_message?: string
}

// Generative UI 配置
export interface GenerativeUIConfig {
  component_type:
    | 'match_spotlight'
    | 'match_card_list'
    | 'match_carousel'
    | 'empty_state'
    | 'date_plan_carousel'
    | 'health_report'
    | 'gift_suggestions'
  props: Record<string, any>
}

// Skill 操作
export interface SkillAction {
  label: string
  action_type:
    | 'view_profile'
    | 'start_chat'
    | 'browse_more'
    | 'edit_profile'
    | 'browse_all'
    | 'adjust_preferences'
    | 'book_date'
    | 'buy_gift'
  params: Record<string, any>
}

// 匹配候选人
export interface MatchCandidate {
  user_id: string
  name: string
  age: number
  gender: string
  location: string
  avatar?: string
  avatar_url?: string
  score: number
  reasoning?: string
  common_interests?: string[]
  compatibility_analysis?: any
}

// P0 Skill 特定类型

// 匹配助手 Skill 参数
export interface MatchmakingSkillParams {
  user_intent: string
  hard_requirements?: string[]
  soft_preferences?: string[]
  context?: {
    user_id: string
    conversation_history?: string[]
    time_of_day?: string
  }
}

// 匹配助手 Skill 响应
export interface MatchmakingSkillResponse {
  ai_message: string
  matches: MatchCandidate[]
  generative_ui: GenerativeUIConfig
  suggested_actions: SkillAction[]
  skill_metadata: {
    name: string
    version: string
    execution_time_ms: number
    intent_type: string
  }
}

// AI 预沟通 Skill 参数
export interface PreCommunicationSkillParams {
  match_id: string
  action: 'start' | 'check_status' | 'get_report' | 'cancel'
  user_id?: string
  preferences?: {
    conversation_style?: 'friendly' | 'direct' | 'humorous'
    key_topics?: string[]
  }
}

// AI 预沟通 Skill 响应
export interface PreCommunicationSkillResponse {
  session_id?: string
  status?: string
  ai_message: string
  progress?: {
    message_count: number
    completion_percentage: number
    key_insights: string[]
  }
  match_report?: {
    compatibility_score: number
    key_insights: Array<{
      type: string
      content: string
      confidence: number
    }>
    conversation_highlights: string[]
    potential_concerns: string[]
  }
  recommendation?: 'proceed_to_chat' | 'not_recommended' | 'need_more_time'
}

// AI 感知 Skill 参数
export interface OmniscientInsightSkillParams {
  user_id: string
  query_type: 'overview' | 'patterns' | 'insights' | 'suggestions'
  time_range?: 'today' | 'week' | 'month'
}

// AI 感知 Skill 响应
export interface OmniscientInsightSkillResponse {
  ai_message: string
  emotional_state: 'enthusiastic' | 'engaged' | 'passive' | 'withdrawn'
  behavior_patterns: Array<{
    type: string
    description: string
    confidence: number
  }>
  active_insights: Array<{
    type: string
    severity: 'low' | 'medium' | 'high'
    description: string
    suggestion: string
  }>
  proactive_suggestions: Array<{
    type: string
    severity: string
    title: string
    content: string
    action: { type: string }
  }>
  trend_prediction: {
    match_probability: 'low' | 'medium' | 'high'
    relationship_prospect: string
    recommendation: string
  }
}

// P1 Skill 特定类型

// 关系教练 Skill 参数
export interface RelationshipCoachSkillParams {
  match_id: string
  action: 'health_check' | 'get_advice' | 'plan_date' | 'gift_suggestion'
  context?: {
    issue_type?: string
    occasion?: string
    budget?: number
  }
}

// 关系教练 Skill 响应
export interface RelationshipCoachSkillResponse {
  ai_message: string
  health_score?: number
  issues?: Array<{
    type: string
    severity: string
    description: string
  }>
  recommendations?: string[]
  date_plans?: DatePlan[]
  gift_suggestions?: GiftSuggestion[]
}

// 约会计划
export interface DatePlan {
  title: string
  type: string
  description: string
  duration: string
  location_suggestions: Array<{
    name: string
    address: string
    price_range: string
  }>
  conversation_starters?: string[]
  budget_estimate: string
  tips: string[]
  confidence_score: number
  best_time?: string
}

// 礼物建议
export interface GiftSuggestion {
  name: string
  description: string
  price_range: string
  suitability: number
  purchase_link?: string
}

// 约会策划 Skill 参数
export interface DatePlanningSkillParams {
  match_id: string
  preferences?: {
    date_type?: 'casual' | 'formal' | 'romantic' | 'adventurous' | 'cultural'
    budget_range?: 'low' | 'medium' | 'high'
    duration?: 'short' | 'medium' | 'long'
    time_preference?: 'morning' | 'afternoon' | 'evening' | 'any'
  }
  context?: {
    user_id?: string
    special_occasion?: string
  }
}

// 约会策划 Skill 响应
export interface DatePlanningSkillResponse {
  ai_message: string
  date_type: string
  plans: DatePlan[]
  generative_ui: GenerativeUIConfig
  booking_assistance: {
    requires_reservation: boolean
    booking_links: Array<{
      plan: string
      type: string
      suggestion: string
    }>
  }
}

// 自主触发结果
export interface AutonomousTriggerResult {
  triggered: boolean
  reason?: string
  should_push?: boolean
  push_message?: string
  result?: any
  [key: string]: any
}

// P19 Skills - 外部服务集成

// 账单分析 Skill 参数
export interface BillAnalysisSkillParams {
  user_id: string
  action: 'analyze' | 'get_profile' | 'compare_compatibility'
  target_user_id?: string
  time_range?: 'month' | 'quarter' | 'year'
}

// 消费画像
export interface ConsumptionProfile {
  level: string
  level_score: number
  frequency: string
  preferred_categories: string[]
  average_transaction: string
  spending_pattern: string
  price_sensitivity: string
}

// 消费兼容性
export interface ConsumptionCompatibility {
  consumption_match: number
  lifestyle_match: number
  aesthetic_match: number
  overall_match: number
}

// 账单分析 Skill 响应
export interface BillAnalysisSkillResponse {
  ai_message: string
  consumption_profile?: ConsumptionProfile
  compatibility?: ConsumptionCompatibility
  bill_features?: {
    total_transactions: number
    avg_monthly_spending: number
    category_distribution: Record<string, number>
  }
  analysis?: {
    user_1_level: string
    user_2_level: string
    key_differences: string[]
    key_similarities: string[]
  }
}

// 地理位置 Skill 参数
export interface GeoLocationSkillParams {
  user_id?: string
  action: 'analyze_trajectory' | 'get_hotzones' | 'check_compatibility' | 'recommend_date_spots'
  target_user_id?: string
  time_range?: 'week' | 'month' | 'quarter'
  date_type?: 'casual' | 'formal' | 'romantic'
}

// 地理轨迹分析
export interface TrajectoryAnalysis {
  hotzones: Array<{
    name: string
    address: string
    visit_frequency: number
    last_visit: string
  }>
  activity_radius: number
  preferred_areas: string[]
}

// 位置兼容性
export interface LocationCompatibility {
  distance_score: number
  hotzone_overlap: number
  midpoint: {
    lat: number
    lng: number
    address: string
  }
  overall_score: number
}

// 地理位置 Skill 响应
export interface GeoLocationSkillResponse {
  ai_message: string
  trajectory_analysis?: TrajectoryAnalysis
  compatibility?: LocationCompatibility
  date_spot_recommendations?: Array<{
    name: string
    type: string
    address: string
    distance_from_midpoint: number
    rating: number
    price_range: string
    reason: string
  }>
  suggested_dates?: Array<{
    date: string
    time: string
    location: string
  }>
}

// 礼物订购 Skill 参数
export interface GiftOrderingSkillParams {
  match_id: string
  action: 'get_suggestions' | 'compare_options' | 'place_order' | 'track_delivery' | 'get_occasion_reminder'
  occasion?: 'birthday' | 'anniversary' | 'valentines' | 'christmas' | 'surprise' | 'apology'
  budget_range?: 'under_100' | '100_300' | '300_500' | '500_1000' | 'above_1000'
  preferences?: Record<string, any>
  gift_id?: string
  order_id?: string
}

// 礼物推荐
export interface GiftSuggestion {
  gift_id: string
  name: string
  description: string
  price: number
  platform: string
  image_url: string
  match_reason: string
  urgency_score: number
}

// 场合信息
export interface OccasionInfo {
  occasion_type: string
  date: string
  days_remaining: number
}

// 订单信息
export interface OrderInfo {
  order_id: string
  status: string
  estimated_delivery: string
  total_amount?: number
  created_at?: string
}

// 礼物订购 Skill 响应
export interface GiftOrderingSkillResponse {
  ai_message: string
  gift_suggestions?: GiftSuggestion[]
  occasion_info?: OccasionInfo
  order_info?: OrderInfo
  tracking_info?: {
    order_id: string
    status: string
    tracking_number: string
    carrier: string
    estimated_delivery: string
    updates: Array<{ time: string; info: string }>
  }
  comparisons?: Array<{
    platform: string
    price: number
    shipping: number
    free_shipping: boolean
    delivery_days: number
  }>
  generative_ui?: GenerativeUIConfig
}

// Skill 注册表
export interface SkillRegistry {
  listSkills(): Promise<SkillMetadata[]>
  getSkillInfo(name: string): Promise<SkillMetadata>
  execute(name: string, params: Record<string, any>): Promise<SkillExecuteResponse>
  triggerAutonomous(
    name: string,
    triggerType: string,
    userId: string,
    context?: Record<string, any>
  ): Promise<AutonomousTriggerResult>
}

// ==================== 新增 Skill 类型定义 ====================

// P3 - 关系进展追踪 Skill
export interface RelationshipProgressSkillParams {
  operation: 'record' | 'timeline' | 'health_score' | 'visualize' | 'analyze'
  user_id_1: string
  user_id_2: string
  progress_type?: string
  description?: string
  progress_score?: number
  related_data?: Record<string, any>
}

export interface RelationshipProgressData {
  progress_id?: string
  progress_type?: string
  progress_type_label?: string
  current_stage?: string
  current_stage_label?: string
  health_score?: number
  health_level?: string
  timeline?: any[]
  milestones?: any[]
  suggestions?: string[]
  status?: string
}

export interface RelationshipProgressSkillResponse {
  ai_message: string
  relationship_data: RelationshipProgressData
  generative_ui?: GenerativeUIConfig
  suggested_actions?: SkillAction[]
  skill_metadata?: {
    name: string
    version: string
    execution_time_ms: number
    operation: string
  }
}

// 聊天助手 Skill
export interface ChatAssistantSkillParams {
  operation: 'send_message' | 'get_conversations' | 'get_history' | 'mark_read' | 'get_suggestions' | 'get_unread_count'
  user_id: string
  receiver_id?: string
  content?: string
  message_type?: 'text' | 'image' | 'emoji' | 'voice'
  conversation_id?: string
  message_id?: string
  other_user_id?: string
  limit?: number
}

export interface ChatMessage {
  id: string
  sender_id: string
  content: string
  message_type: string
  is_read: boolean
  created_at: string
}

export interface Conversation {
  id: string
  partner_id: string
  last_message_at: string
  last_message_preview: string
  unread_count: number
}

export interface ChatSuggestion {
  type: 'topic' | 'icebreaker'
  content: string
  reason: string
}

export interface ChatAssistantSkillResponse {
  ai_message: string
  chat_data: {
    message_id?: string
    conversation_id?: string
    messages?: ChatMessage[]
    conversations?: Conversation[]
    unread_count?: number
    suggestions?: ChatSuggestion[]
    status?: string
    total?: number
  }
  generative_ui?: GenerativeUIConfig
  suggested_actions?: SkillAction[]
  skill_metadata?: {
    name: string
    version: string
    execution_time_ms: number
    operation: string
  }
}

// 安全守护 Skill - 紧急求助
export interface SafetyGuardianEmergencyParams {
  user_id: string
  emergency_type?: 'general' | 'medical' | 'danger' | 'harassment'
  location_data?: {
    latitude: number
    longitude: number
    address?: string
  }
  note?: string
  contact_index?: number
  share_location?: boolean
  session_id?: string
  message?: string
}

export interface EmergencyContact {
  name: string
  phone: string
  relationship: string
  notified: boolean
}

export interface SafetyGuardianEmergencyResponse {
  ai_message: string
  emergency_data: {
    emergency_id?: string
    emergency_type: string
    status: string
    contacts_notified?: EmergencyContact[]
    location_shared?: boolean
    created_at?: string
  }
  generative_ui?: GenerativeUIConfig
  suggested_actions?: SkillAction[]
}
