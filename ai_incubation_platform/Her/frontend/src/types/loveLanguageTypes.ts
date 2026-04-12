/**
 * 爱之语画像类型定义
 */

// ==================== 爱之语画像类型 ====================

export type LoveLanguageType =
  | 'words_of_affirmation'   // 肯定的言辞
  | 'quality_time'           // 精心时刻
  | 'receiving_gifts'        // 接受礼物
  | 'acts_of_service'        // 服务的行动
  | 'physical_touch'         // 身体的接触

export interface LoveLanguageProfile {
  id: string
  user_id: string
  primary_love_language: LoveLanguageType
  secondary_love_language?: LoveLanguageType
  language_scores: Record<LoveLanguageType, number>
  ai_analysis: string
  relationship_history: LoveLanguageRelationship[]
  created_at: string
  updated_at: string
}

export interface LoveLanguageRelationship {
  partner_id: string
  compatibility_score: number
  love_language_match: boolean
  notes?: string
}

export interface LoveLanguageDescription {
  type: LoveLanguageType
  name: string
  description: string
  characteristics: string[]
  tips: string[]
}

// ==================== 关系趋势预测类型 ====================

export interface RelationshipTrendPrediction {
  id: string
  user_a_id: string
  user_b_id: string
  prediction_period: string
  trend_data: TrendDataPoint[]
  current_stage: RelationshipStage
  predicted_stage?: RelationshipStage
  emotional_temperature: number  // 0-100
  stability_score: number        // 0-1
  growth_indicators: string[]
  risk_factors: RiskFactor[]
  recommendations: string[]
  ai_summary: string
  created_at: string
}

export interface TrendDataPoint {
  date: string
  emotional_temperature: number
  interaction_frequency: number
  quality_score: number
  milestone_events?: string[]
}

export type RelationshipStage =
  | 'stranger'         // 陌生人
  | 'acquaintance'     // 认识
  | 'friend'           // 朋友
  | 'close_friend'     // 好友
  | 'dating'           // 约会中
  | 'exclusive'        // 专一交往
  | 'committed'        // 承诺关系
  | 'engaged'          // 订婚
  | 'married'          // 结婚

export interface RiskFactor {
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  trigger_conditions: string[]
  mitigation_suggestions: string[]
}

// ==================== 预警分级响应类型 ====================

export interface EmotionWarning {
  id: string
  user_id: string
  warning_level: WarningLevel
  warning_type: string
  description: string
  trigger_event: string
  suggested_response: string
  is_resolved: boolean
  resolved_at?: string
  created_at: string
}

export type WarningLevel =
  | 'low'       // 温和提醒
  | 'medium'    // 建议沟通技巧
  | 'high'      // 主动干预
  | 'critical'  // 紧急干预

export interface WarningResponseStrategy {
  id: string
  warning_level: WarningLevel
  response_type: string
  title: string
  description: string
  suggested_actions: string[]
  communication_tips: string[]
  escalation_path?: string
}

export interface WarningResponseRecord {
  id: string
  warning_id: string
  strategy_id: string
  recipient_user_id: string
  response_content: string
  delivery_method: 'push_notification' | 'in_app_message' | 'email'
  is_delivered: boolean
  is_read: boolean
  feedback?: 'helpful' | 'neutral' | 'unhelpful'
  emotion_change?: number  // -1 to 1
  relationship_improvement?: number  // 0 to 1
  created_at: string
}

// ==================== 综合分析类型 ====================

export interface ComprehensiveRelationshipAnalysis {
  user_a_love_language: LoveLanguageProfile | null
  user_b_love_language: LoveLanguageProfile | null
  love_language_compatibility: LoveLanguageCompatibility | null
  relationship_trend: RelationshipTrendPrediction
  overall_health_score: number
  ai_summary: string
  action_recommendations: ActionRecommendation[]
}

export interface LoveLanguageCompatibility {
  compatibility_score: number
  description: string
  user_a_primary: LoveLanguageType
  user_b_primary: LoveLanguageType
  strengths: string[]
  challenges: string[]
  suggestions: Suggestion[]
}

export interface Suggestion {
  type: 'understanding' | 'communication' | 'action' | 'growth'
  description: string
  priority: 'high' | 'medium' | 'low'
}

export interface ActionRecommendation {
  type: 'immediate' | 'short_term' | 'long_term'
  title: string
  description: string
  expected_impact: string
  difficulty: 'easy' | 'medium' | 'hard'
}

// ==================== API 请求类型 ====================

export interface AnalyzeLoveLanguageRequest {
  user_id: string
}

export interface PredictRelationshipTrendRequest {
  user_a_id: string
  user_b_id: string
  prediction_period: '7d' | '14d' | '30d'
}

export interface GetWarningResponseStrategyRequest {
  warning_level: WarningLevel
  context?: Record<string, any>
}

export interface ExecuteWarningResponseRequest {
  warning_id: string
  strategy_id: string
  recipient_user_id: string
  response_content: string
  delivery_method: 'push_notification' | 'in_app_message' | 'email'
}

export interface SubmitWarningResponseFeedbackRequest {
  record_id: string
  feedback: 'helpful' | 'neutral' | 'unhelpful'
  emotion_change?: number
  relationship_improvement?: number
}

export interface ComprehensiveAnalysisRequest {
  user_a_id: string
  user_b_id: string
}