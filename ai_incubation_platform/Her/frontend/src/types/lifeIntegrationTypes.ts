/**
 * 生活融合类型定义
 * 包含：自主约会、情感纪念册、部落匹配、数字小家、见家长模拟、压力测试、成长计划、信任背书
 */

// ==================== 自主约会策划 ====================

export interface AutonomousDatePlan {
  id: string
  user_a_id: string
  user_b_id: string
  plan_status: 'draft' | 'pending_approval' | 'confirmed' | 'completed' | 'cancelled'
  proposed_date: string
  proposed_time: string
  venue: DateVenue
  activities: PlannedActivity[]
  budget_estimate: BudgetEstimate
  transportation: TransportationOption[]
  both_users_approved: boolean
  ai_reasoning: string
  created_at: string
  approved_at?: string
}

export interface DateVenue {
  id: string
  name: string
  address: string
  city: string
  latitude: number
  longitude: number
  venue_type: string
  rating: number
  price_level: number
  phone?: string
  website?: string
  image_url?: string
}

export interface PlannedActivity {
  sequence: number
  activity_name: string
  duration_minutes: number
  description: string
  location?: string
}

export interface BudgetEstimate {
  total_estimated: number
  per_person: number
  currency: string
  breakdown: BudgetBreakdown
}

export interface BudgetBreakdown {
  food_beverage: number
  activity: number
  transportation: number
  miscellaneous: number
}

export interface TransportationOption {
  type: 'driving' | 'public_transit' | 'rideshare' | 'walking'
  duration_minutes: number
  cost_estimate: number
  route_description: string
  parking_info?: string
}

export interface CreateDatePlanRequest {
  user_a_id: string
  user_b_id: string
  preferred_date?: string
  preferred_time?: string
  budget_range?: string
  activity_preferences?: string[]
  dietary_restrictions?: string[]
}

export interface ApproveDatePlanRequest {
  plan_id: string
  user_id: string
  approved: boolean
  feedback?: string
}

// ==================== 情感纪念册 ====================

export interface RelationshipAlbum {
  id: string
  user_a_id: string
  user_b_id: string
  album_title: string
  album_description: string
  cover_image_url?: string
  memories: Memory[]
  milestones_highlighted: MilestoneHighlight[]
  ai_summary: string
  emotional_journey: EmotionalJourneyPoint[]
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface Memory {
  id: string
  memory_type: 'conversation' | 'photo' | 'video' | 'voice' | 'location' | 'milestone'
  title: string
  description: string
  content_url?: string
  thumbnail_url?: string
  date: string
  location?: string
  tags: string[]
  ai_caption?: string
  emotional_weight: number  // 0-1
}

export interface MilestoneHighlight {
  milestone_id: string
  milestone_type: string
  title: string
  date: string
  significance: string
  celebration_suggestion?: string
}

export interface EmotionalJourneyPoint {
  date: string
  emotional_temperature: number
  key_event?: string
  milestone?: string
}

export interface SweetMoment {
  id: string
  album_id: string
  quote: string
  context: string
  conversation_snippet?: string
  date: string
  tags: string[]
  ai_interpretation: string
}

export interface CoupleFootprint {
  id: string
  user_a_id: string
  user_b_id: string
  location_name: string
  location_address: string
  latitude: number
  longitude: number
  visit_date: string
  activity_type: string
  memory_description: string
  photo_urls?: string[]
  rating?: number
  notes?: string
}

export interface GenerateAlbumRequest {
  user_a_id: string
  user_b_id: string
  album_theme?: string
  date_range?: {
    start_date: string
    end_date: string
  }
  include_memories?: Memory['memory_type'][]
  ai_style?: 'romantic' | 'minimalist' | 'vibrant' | 'nostalgic'
}

export interface AddMemoryRequest {
  album_id: string
  memory_type: Memory['memory_type']
  title: string
  description: string
  content_url?: string
  date: string
  tags?: string[]
}

// ==================== 部落匹配 ====================

export interface LifestyleTribe {
  id: string
  tribe_name: string
  tribe_description: string
  lifestyle_tags: string[]
  member_count: number
  tribe_characteristics: TribeCharacteristic[]
  compatibility_factors: string[]
  icon_url?: string
}

export interface TribeCharacteristic {
  category: 'schedule' | 'diet' | 'fitness' | 'social' | 'values'
  description: string
  importance: number  // 0-1
}

export interface UserTribeMembership {
  id: string
  user_id: string
  tribe_id: string
  membership_status: 'pending' | 'active' | 'inactive'
  fit_score: number  // 0-1
  ai_analysis: string
  joined_at: string
}

export interface TribeCompatibilityAnalysis {
  user_a_tribes: LifestyleTribe[]
  user_b_tribes: LifestyleTribe[]
  common_tribes: LifestyleTribe[]
  compatibility_score: number
  lifestyle_alignment: LifestyleAlignment[]
  potential_conflicts: string[]
  integration_suggestions: string[]
  ai_summary: string
}

export interface LifestyleAlignment {
  category: string
  alignment_score: number
  description: string
  examples: string[]
}

export interface AnalyzeTribeFitRequest {
  user_id: string
  lifestyle_data: {
    schedule: string
    diet_preferences: string[]
    fitness_level: string
    social_preference: 'introvert' | 'extrovert' | 'ambivert'
    values: string[]
  }
}

// ==================== 数字小家 ====================

export interface DigitalHome {
  id: string
  user_a_id: string
  user_b_id: string
  home_name: string
  home_description: string
  theme: HomeTheme
  shared_spaces: SharedSpace[]
  current_goals: CoupleGoal[]
  completed_goals: CoupleGoal[]
  shared_calendar: CalendarEvent[]
  memories_count: number
  goals_completion_rate: number
  created_at: string
  updated_at: string
}

export type HomeTheme =
  | 'cozy'
  | 'modern'
  | 'nature'
  | 'minimalist'
  | 'vibrant'
  | 'romantic'

export interface SharedSpace {
  space_id: string
  space_name: string
  space_type: 'photo_wall' | 'memory_corner' | 'goal_board' | 'chat_nook' | 'planner'
  content_count: number
  last_activity: string
}

export interface CoupleGoal {
  id: string
  home_id: string
  goal_title: string
  goal_description: string
  goal_category: GoalCategory
  target_date?: string
  progress: number  // 0-100
  status: 'active' | 'completed' | 'paused' | 'abandoned'
  checkins: GoalCheckin[]
  ai_encouragement?: string
  created_at: string
}

export type GoalCategory =
  | 'health'
  | 'finance'
  | 'relationship'
  | 'career'
  | 'learning'
  | 'travel'
  | 'family'

export interface GoalCheckin {
  id: string
  goal_id: string
  user_id: string
  checkin_date: string
  progress_update: number
  notes?: string
  mood?: string
  encouragement_given?: boolean
}

export interface CreateDigitalHomeRequest {
  user_a_id: string
  user_b_id: string
  home_name: string
  theme?: HomeTheme
}

export interface CreateCoupleGoalRequest {
  home_id: string
  goal_title: string
  goal_description: string
  goal_category: GoalCategory
  target_date?: string
  initial_checkin?: {
    notes?: string
    mood?: string
  }
}

export interface GoalCheckinRequest {
  goal_id: string
  user_id: string
  progress?: number
  notes?: string
  mood?: string
}

export interface CalendarEvent {
  id: string
  home_id: string
  event_title: string
  event_type: 'date' | 'reminder' | 'milestone' | 'custom'
  event_date: string
  event_time?: string
  description?: string
  related_to_goal?: string
  notified: boolean
}

// ==================== 见家长模拟 ====================

export interface FamilyMeetingSimulation {
  id: string
  user_id: string
  virtual_family_member: VirtualFamilyMember
  scenario_config: FamilyScenarioConfig
  conversation_history: FamilyConversationTurn[]
  performance_metrics: FamilyMeetingMetrics
  ai_feedback: FamilyMeetingFeedback
  status: 'not_started' | 'in_progress' | 'completed'
  created_at: string
  completed_at?: string
}

export interface VirtualFamilyMember {
  member_type: 'father' | 'mother' | 'grandparent' | 'sibling'
  personality_traits: string[]
  values: string[]
  concerns: string[]
  conversation_style: 'strict' | 'gentle' | 'curious' | 'reserved'
  background: string
}

export interface FamilyScenarioConfig {
  difficulty: 'easy' | 'medium' | 'hard'
  setting: 'first_meeting' | 'casual_visit' | 'formal_dinner' | 'holiday_gathering'
  duration_minutes: number
  focus_areas: string[]
  custom_context?: string
}

export interface FamilyConversationTurn {
  turn_number: number
  speaker: 'user' | 'family_member'
  content: string
  family_member_reaction?: string
  impression_score?: number
  ai_feedback?: string
}

export interface FamilyMeetingMetrics {
  overall_impression: number  // 0-100
  respect_score: number
  communication_score: number
  authenticity_score: number
  cultural_sensitivity_score: number
  conflict_handling_score: number
}

export interface FamilyMeetingFeedback {
  strengths: string[]
  areas_for_improvement: string[]
  specific_suggestions: FamilySuggestion[]
  cultural_tips: string[]
  conversation_starters: string[]
  topics_to_avoid: string[]
  ai_summary: string
}

export interface FamilySuggestion {
  situation: string
  recommended_approach: string
  example_phrase: string
  reasoning: string
}

export interface StartFamilySimulationRequest {
  virtual_family_member: Omit<VirtualFamilyMember, 'member_type'> & { member_type: VirtualFamilyMember['member_type'] }
  scenario_config: Partial<FamilyScenarioConfig>
}

export interface SubmitFamilyConversationTurnRequest {
  simulation_id: string
  user_response: string
}

// ==================== 压力测试 ====================

export interface StressTest {
  id: string
  user_a_id: string
  user_b_id: string
  scenario: StressScenario
  user_a_responses: StressResponse[]
  user_b_responses: StressResponse[]
  compatibility_analysis: StressCompatibilityAnalysis
  overall_compatibility_score: number
  ai_insights: string[]
  recommendations: string[]
  status: 'not_started' | 'in_progress' | 'completed'
  created_at: string
  completed_at?: string
}

export interface StressScenario {
  scenario_id: string
  scenario_type: 'financial_crisis' | 'career_setback' | 'family_emergency' | 'health_issue' | 'long_distance' | 'conflict'
  scenario_title: string
  scenario_description: string
  difficulty: 'easy' | 'medium' | 'hard'
  questions: StressQuestion[]
}

export interface StressQuestion {
  question_id: string
  question_text: string
  question_type: 'open_ended' | 'multiple_choice' | 'scenario_response'
  options?: string[]
  assesses: string[]
}

export interface StressResponse {
  question_id: string
  user_id: string
  response_text: string
  selected_option?: string
  ai_analysis: StressResponseAnalysis
}

export interface StressResponseAnalysis {
  coping_style: string
  emotional_regulation: number  // 0-100
  problem_solving_approach: string
  support_seeking_tendency: number  // 0-1
  stress_triggers: string[]
}

export interface StressCompatibilityAnalysis {
  coping_compatibility: number  // 0-1
  communication_under_stress: number  // 0-1
  mutual_support_potential: number  // 0-1
  conflict_resolution_alignment: number  // 0-1
  strengths_as_couple: string[]
  growth_areas: string[]
  ai_summary: string
}

export interface StartStressTestRequest {
  user_a_id: string
  user_b_id: string
  scenario_type: StressScenario['scenario_type']
}

export interface SubmitStressResponseRequest {
  test_id: string
  question_id: string
  response_text: string
  selected_option?: string
}

// ==================== 成长计划 ====================

export interface GrowthPlan {
  id: string
  user_a_id: string
  user_b_id: string
  plan_name: string
  plan_description: string
  growth_areas: GrowthArea[]
  shared_goals: GrowthGoal[]
  individual_goals: {
    user_a: GrowthGoal[]
    user_b: GrowthGoal[]
  }
  progress_tracking: ProgressTracking
  resource_recommendations: GrowthResource[]
  milestone_celebrations: string[]
  ai_coach_insights: string[]
  created_at: string
  updated_at: string
}

export interface GrowthArea {
  area_id: string
  area_name: string
  area_description: string
  current_level: number  // 0-100
  target_level: number
  priority: 'high' | 'medium' | 'low'
  action_items: string[]
}

export interface GrowthGoal {
  goal_id: string
  goal_title: string
  goal_description: string
  category: GrowthGoalCategory
  target_date?: string
  progress: number  // 0-100
  milestones: GoalMilestone[]
  status: 'active' | 'completed' | 'paused'
}

export type GrowthGoalCategory =
  | 'communication'
  | 'intimacy'
  | 'trust'
  | 'conflict_resolution'
  | 'shared_values'
  | 'future_planning'
  | 'personal_development'

export interface GoalMilestone {
  milestone_id: string
  milestone_description: string
  completed: boolean
  completed_at?: string
  notes?: string
}

export interface ProgressTracking {
  last_checkin: string
  checkin_frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly'
  overall_progress: number  // 0-100
  recent_achievements: string[]
  upcoming_milestones: string[]
}

export interface GrowthResource {
  resource_id: string
  resource_type: 'article' | 'video' | 'book' | 'course' | 'exercise' | 'podcast'
  title: string
  description: string
  url?: string
  estimated_time: string
  relevance_score: number
  related_to_area: string
}

export interface CreateGrowthPlanRequest {
  user_a_id: string
  user_b_id: string
  plan_name: string
  focus_areas?: string[]
  initial_goals?: Array<{
    title: string
    description: string
    category: GrowthGoalCategory
  }>
}

export interface GrowthPlanCheckinRequest {
  plan_id: string
  user_id: string
  progress_updates?: Array<{
    goal_id: string
    progress: number
    notes?: string
  }>
  achievements?: string[]
  challenges?: string[]
}

// ==================== 信任背书 ====================

export interface TrustScore {
  id: string
  user_id: string
  overall_trust_score: number  // 0-100
  score_breakdown: TrustScoreBreakdown
  trust_history: TrustHistoryItem[]
  endorsements: TrustEndorsement[]
  verified_claims: VerifiedClaim[]
  ai_assessment: string
  last_calculated: string
}

export interface TrustScoreBreakdown {
  reliability: number  // 0-100
  honesty: number  // 0-100
  consistency: number  // 0-100
  responsiveness: number  // 0-100
  respect: number  // 0-100
}

export interface TrustHistoryItem {
  id: string
  event_type: 'positive' | 'negative' | 'neutral'
  event_description: string
  impact_score: number  // -10 to 10
  date: string
}

export interface TrustEndorsement {
  id: string
  endorser_id: string
  endorser_name: string
  relationship: string
  endorsement_text: string
  endorsement_category: TrustEndorsementCategory
  credibility_score: number
  date: string
}

export type TrustEndorsementCategory =
  | 'reliability'
  | 'honesty'
  | 'kindness'
  | 'communication'
  | 'respect'
  | 'general'

export interface VerifiedClaim {
  claim_id: string
  claim_type: ClaimType
  claim_description: string
  verification_method: string
  verified_at: string
  verification_source?: string
}

export type ClaimType =
  | 'identity_verified'
  | 'employment_verified'
  | 'education_verified'
  | 'background_check_passed'
  | 'phone_verified'
  | 'email_verified'
  | 'social_media_linked'
  | 'reference_checked'

export interface TrustEndorsementRequest {
  endorser_id: string
  target_user_id: string
  endorsement_text: string
  endorsement_category: TrustEndorsementCategory
  relationship_context?: string
}

export interface VerifyClaimRequest {
  user_id: string
  claim_type: ClaimType
  verification_data: Record<string, any>
}

export interface TrustScoreComparison {
  user_a_trust: TrustScore
  user_b_trust: TrustScore
  compatibility_analysis: TrustCompatibilityAnalysis
  ai_summary: string
}

export interface TrustCompatibilityAnalysis {
  trust_alignment: number  // 0-1
  mutual_trust_level: 'low' | 'medium' | 'high'
  trust_building_suggestions: string[]
  potential_concerns: string[]
}