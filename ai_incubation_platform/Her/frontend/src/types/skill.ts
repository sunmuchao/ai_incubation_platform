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
    matches?: SkillMatchCandidate[]
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

// Skill 专用匹配候选人（与 index.ts 的 MatchCandidate 结构不同）
export interface SkillMatchCandidate {
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
  matches: SkillMatchCandidate[]
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
  success?: boolean  // Skill 执行结果
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
    date_type?: 'casual' | 'formal' | 'romantic' | 'adventurous' | 'cultural' | 'first_date'
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

// 聊天助手 Skill
export interface ChatAssistantSkillParams {
  operation: 'send_message' | 'get_conversations' | 'get_history' | 'mark_read' | 'get_suggestions' | 'get_unread_count' | 'check_pending_replies'
  user_id: string
  receiver_id?: string
  content?: string
  message_type?: 'text' | 'image' | 'emoji' | 'voice'
  conversation_id?: string
  message_id?: string
  other_user_id?: string
  limit?: number
}

// Skill 专用聊天消息（简化版）
export interface SkillChatMessage {
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
    messages?: SkillChatMessage[]
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

// 礼物推荐 Skill
export interface GiftSuggestionSkillParams {
  user_id: string
  partner_id: string
  occasion: 'birthday' | 'anniversary' | 'daily' | 'thank_you' | 'apology' | 'celebration'
  budget?: number
  action: 'recommend' | 'get_popular' | 'get_by_interest'
}

export interface GiftRecommendation {
  gift_id: string
  name: string
  price: number
  icon: string
  reason: string
  suitability_score: number
  occasion_match?: boolean
  tags?: string[]
}

export interface GiftSuggestionSkillResponse {
  success: boolean
  ai_message: string
  recommendations: GiftRecommendation[]
  budget_analysis?: {
    min_price: number
    max_price: number
    recommended_budget: number
  }
  generative_ui?: {
    component_type: 'GiftRecommendCarousel' | 'empty_state'
    props: {
      gifts?: GiftRecommendation[]
      show_purchase_button?: boolean
      show_reason?: boolean
      message?: string
    }
  }
}
