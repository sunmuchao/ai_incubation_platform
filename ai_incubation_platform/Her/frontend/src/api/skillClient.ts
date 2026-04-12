/**
 * Agent Skill 客户端
 *
 * 提供统一的 Skill 执行接口
 */

import type {
  SkillMetadata,
  SkillExecuteRequest,
  SkillExecuteResponse,
  AutonomousTriggerResult,
  MatchmakingSkillParams,
  MatchmakingSkillResponse,
  PreCommunicationSkillParams,
  PreCommunicationSkillResponse,
  OmniscientInsightSkillParams,
  OmniscientInsightSkillResponse,
  RelationshipCoachSkillParams,
  RelationshipCoachSkillResponse,
  DatePlanningSkillParams,
  DatePlanningSkillResponse,
  BillAnalysisSkillParams,
  BillAnalysisSkillResponse,
  // 注：GeoLocation, GiftOrdering, RelationshipProgress 已删除，改用 REST API
  ChatAssistantSkillParams,
  ChatAssistantSkillResponse,
  SafetyGuardianEmergencyParams,
  SafetyGuardianEmergencyResponse,
  ConversationMatchmakerSkillParams,
  ConversationMatchmakerSkillResponse,
  ProfileCollectionSkillParams,
  ProfileCollectionSkillResponse,
} from '../types/skill'
import { authStorage } from '../utils/storage'

const API_BASE_URL = ''

// 获取认证头
const getAuthHeaders = (): Record<string, string> => {
  const token = authStorage.getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

// 获取当前用户 ID
const getCurrentUserId = (): string => {
  return authStorage.getUserId()
}

/**
 * Skill 注册表客户端
 */
export const skillRegistry = {
  /**
   * 获取所有可用 Skill 列表
   */
  async listSkills(): Promise<SkillMetadata[]> {
    const response = await fetch(`${API_BASE_URL}/api/skills/list`, {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to list skills')
    }

    const data = await response.json()
    return data.skills || []
  },

  /**
   * 获取 Skill 详细信息
   */
  async getSkillInfo(name: string): Promise<SkillMetadata> {
    const response = await fetch(`${API_BASE_URL}/api/skills/${name}/info`, {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error(`Skill not found: ${name}`)
    }

    const data = await response.json()
    return data.skill
  },

  /**
   * 执行 Skill
   */
  async execute(name: string, params: Record<string, any>): Promise<SkillExecuteResponse> {
    const request: SkillExecuteRequest = {
      skill_name: name,
      params,
      context: {
        user_id: getCurrentUserId()
      }
    }

    const response = await fetch(`${API_BASE_URL}/api/skills/${name}/execute`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error(`Skill execution failed: ${name}`)
    }

    return response.json()
  },

  /**
   * 触发自主行为
   */
  async triggerAutonomous(
    name: string,
    triggerType: string,
    userId: string,
    context?: Record<string, any>
  ): Promise<AutonomousTriggerResult> {
    const response = await fetch(`${API_BASE_URL}/api/skills/autonomous/trigger`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        skill_name: name,
        trigger_type: triggerType,
        user_id: userId,
        context
      })
    })

    if (!response.ok) {
      throw new Error(`Autonomous trigger failed: ${name}`)
    }

    return response.json()
  },

  /**
   * 触发情境感知
   */
  async triggerContext(
    name: string,
    triggerType: string,
    userId: string,
    context?: Record<string, any>
  ): Promise<AutonomousTriggerResult> {
    const response = await fetch(`${API_BASE_URL}/api/skills/context/trigger`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        skill_name: name,
        trigger_type: triggerType,
        user_id: userId,
        context
      })
    })

    if (!response.ok) {
      throw new Error(`Context trigger failed: ${name}`)
    }

    return response.json()
  }
}

/**
 * P0 Skills - 核心 AI Native 能力
 */

// 匹配助手 Skill
export const matchmakingSkill = {
  /**
   * 执行匹配
   */
  async execute(params: MatchmakingSkillParams): Promise<MatchmakingSkillResponse> {
    const result = await skillRegistry.execute('matchmaking_assistant', params)
    if (!result.success) {
      throw new Error(result.error || 'Matchmaking failed')
    }
    return result.data as MatchmakingSkillResponse
  },

  /**
   * 每日推荐触发
   */
  async triggerDaily(userId: string) {
    return skillRegistry.triggerAutonomous('matchmaking_assistant', 'daily', userId)
  },

  /**
   * 高质量匹配触发
   */
  async triggerQualityMatch(userId: string) {
    return skillRegistry.triggerAutonomous('matchmaking_assistant', 'quality_match', userId)
  }
}

// AI 预沟通 Skill
export const preCommunicationSkill = {
  /**
   * 启动预沟通
   */
  async start(matchId: string, preferences?: any): Promise<PreCommunicationSkillResponse> {
    const result = await skillRegistry.execute('pre_communication', {
      match_id: matchId,
      action: 'start',
      preferences
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to start pre-communication')
    }
    return result.data as PreCommunicationSkillResponse
  },

  /**
   * 检查状态
   */
  async checkStatus(matchId: string): Promise<PreCommunicationSkillResponse> {
    const result = await skillRegistry.execute('pre_communication', {
      match_id: matchId,
      action: 'check_status'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to check status')
    }
    return result.data as PreCommunicationSkillResponse
  },

  /**
   * 获取报告
   */
  async getReport(matchId: string): Promise<PreCommunicationSkillResponse> {
    const result = await skillRegistry.execute('pre_communication', {
      match_id: matchId,
      action: 'get_report'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get report')
    }
    return result.data as PreCommunicationSkillResponse
  },

  /**
   * 取消预沟通
   */
  async cancel(matchId: string): Promise<PreCommunicationSkillResponse> {
    const result = await skillRegistry.execute('pre_communication', {
      match_id: matchId,
      action: 'cancel'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to cancel')
    }
    return result.data as PreCommunicationSkillResponse
  }
}

// AI 感知 Skill
export const omniscientInsightSkill = {
  /**
   * 获取总览
   */
  async getOverview(userId: string, timeRange: 'week' | 'month' = 'week'): Promise<OmniscientInsightSkillResponse> {
    const result = await skillRegistry.execute('omniscient_insight', {
      user_id: userId,
      query_type: 'overview',
      time_range: timeRange
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get overview')
    }
    return result.data as OmniscientInsightSkillResponse
  },

  /**
   * 获取行为模式
   */
  async getPatterns(userId: string): Promise<OmniscientInsightSkillResponse> {
    const result = await skillRegistry.execute('omniscient_insight', {
      user_id: userId,
      query_type: 'patterns'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get patterns')
    }
    return result.data as OmniscientInsightSkillResponse
  },

  /**
   * 获取洞察
   */
  async getInsights(userId: string): Promise<OmniscientInsightSkillResponse> {
    const result = await skillRegistry.execute('omniscient_insight', {
      user_id: userId,
      query_type: 'insights'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get insights')
    }
    return result.data as OmniscientInsightSkillResponse
  },

  /**
   * 获取建议
   */
  async getSuggestions(userId: string): Promise<OmniscientInsightSkillResponse> {
    const result = await skillRegistry.execute('omniscient_insight', {
      user_id: userId,
      query_type: 'suggestions'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get suggestions')
    }
    return result.data as OmniscientInsightSkillResponse
  }
}

/**
 * P1 Skills - 增强 AI 自主性
 */

// 关系教练 Skill
export const relationshipCoachSkill = {
  /**
   * 健康检查
   */
  async healthCheck(matchId: string): Promise<RelationshipCoachSkillResponse> {
    const result = await skillRegistry.execute('relationship_coach', {
      match_id: matchId,
      action: 'health_check'
    })
    if (!result.success) {
      throw new Error(result.error || 'Health check failed')
    }
    return result.data as RelationshipCoachSkillResponse
  },

  /**
   * 获取建议
   */
  async getAdvice(matchId: string, issueType?: string): Promise<RelationshipCoachSkillResponse> {
    const result = await skillRegistry.execute('relationship_coach', {
      match_id: matchId,
      action: 'get_advice',
      context: { issue_type: issueType }
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get advice')
    }
    return result.data as RelationshipCoachSkillResponse
  },

  /**
   * 策划约会
   */
  async planDate(matchId: string, preferences?: any): Promise<RelationshipCoachSkillResponse> {
    const result = await skillRegistry.execute('relationship_coach', {
      match_id: matchId,
      action: 'plan_date',
      context: preferences
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to plan date')
    }
    return result.data as RelationshipCoachSkillResponse
  }
}

// 约会策划 Skill
export const datePlanningSkill = {
  /**
   * 执行约会策划
   */
  async execute(params: DatePlanningSkillParams): Promise<DatePlanningSkillResponse> {
    const result = await skillRegistry.execute('date_planning', params)
    if (!result.success) {
      throw new Error(result.error || 'Date planning failed')
    }
    return result.data as DatePlanningSkillResponse
  },

  /**
   * 首次约会策划
   */
  async planFirstDate(matchId: string): Promise<DatePlanningSkillResponse> {
    return this.execute({
      match_id: matchId,
      preferences: { date_type: 'first_date' }
    })
  },

  /**
   * 浪漫约会策划
   */
  async planRomanticDate(matchId: string): Promise<DatePlanningSkillResponse> {
    return this.execute({
      match_id: matchId,
      preferences: { date_type: 'romantic' }
    })
  }
}

/**
 * P19 Skills - 外部服务集成
 */

// 账单分析 Skill
export const billAnalysisSkill = {
  /**
   * 分析账单
   */
  async analyze(userId: string, timeRange: 'month' | 'quarter' | 'year' = 'quarter'): Promise<BillAnalysisSkillResponse> {
    const result = await skillRegistry.execute('bill_analysis', {
      user_id: userId,
      action: 'analyze',
      time_range: timeRange
    })
    if (!result.success) {
      throw new Error(result.error || 'Bill analysis failed')
    }
    return result.data as BillAnalysisSkillResponse
  },

  /**
   * 获取消费画像
   */
  async getProfile(userId: string): Promise<BillAnalysisSkillResponse> {
    const result = await skillRegistry.execute('bill_analysis', {
      user_id: userId,
      action: 'get_profile'
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to get profile')
    }
    return result.data as BillAnalysisSkillResponse
  },

  /**
   * 比较消费兼容性
   */
  async compareCompatibility(userId: string, targetUserId: string): Promise<BillAnalysisSkillResponse> {
    const result = await skillRegistry.execute('bill_analysis', {
      user_id: userId,
      action: 'compare_compatibility',
      target_user_id: targetUserId
    })
    if (!result.success) {
      throw new Error(result.error || 'Failed to compare compatibility')
    }
    return result.data as BillAnalysisSkillResponse
  }
}

// ==================== 新增 Skills (AI Native) ====================

// 聊天助手 Skill
// AI Native 特性：对话式交互、Generative UI、自主触发（未读提醒、回复建议）
export const chatAssistantSkill = {
  /**
   * 发送消息
   * AI Native: 自动优化消息内容（敏感信息过滤）
   */
  async sendMessage(
    user_id: string,
    receiver_id: string,
    content: string,
    message_type: 'text' | 'image' | 'emoji' | 'voice' = 'text'
  ): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'send_message',
      user_id,
      receiver_id,
      content,
      message_type
    })
    if (!result.success) {
      throw new Error(result.error || '发送消息失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 获取会话列表
   * AI Native: 智能排序（重要对话置顶）
   */
  async getConversations(user_id: string): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'get_conversations',
      user_id
    })
    if (!result.success) {
      throw new Error(result.error || '获取会话列表失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 获取聊天历史
   * AI Native: 智能摘要长对话
   */
  async getHistory(
    user_id: string,
    other_user_id: string,
    limit: number = 20
  ): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'get_history',
      user_id,
      other_user_id,
      limit
    })
    if (!result.success) {
      throw new Error(result.error || '获取聊天历史失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 获取聊天建议
   * AI Native: 基于兴趣和地理位置生成个性化建议
   */
  async getSuggestions(user_id: string, other_user_id: string): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'get_suggestions',
      user_id,
      other_user_id
    })
    if (!result.success) {
      throw new Error(result.error || '获取聊天建议失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 获取未读消息数
   * AI Native: 智能分级（重要消息优先提醒）
   */
  async getUnreadCount(user_id: string): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'get_unread_count',
      user_id
    })
    if (!result.success) {
      throw new Error(result.error || '获取未读消息数失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 标记已读
   */
  async markRead(
    user_id: string,
    message_id?: string,
    conversation_id?: string
  ): Promise<ChatAssistantSkillResponse> {
    const result = await skillRegistry.execute('chat_assistant', {
      operation: 'mark_read',
      user_id,
      message_id,
      conversation_id
    })
    if (!result.success) {
      throw new Error(result.error || '标记已读失败')
    }
    return result.data as ChatAssistantSkillResponse
  },

  /**
   * 自主触发：未读消息提醒
   * AI Native: 主动感知并推送
   */
  async triggerUnreadReminder(user_id: string) {
    return skillRegistry.triggerAutonomous('chat_assistant', 'unread_reminder', user_id)
  },

  /**
   * 自主触发：回复建议
   * AI Native: 检测到对方消息后主动提供建议
   */
  async triggerReplySuggestion(user_id: string, context?: { last_message?: string }) {
    return skillRegistry.triggerAutonomous('chat_assistant', 'reply_suggestion', user_id, context)
  },

  /**
   * 自主触发：长时间未聊天提醒
   * AI Native: 感知关系状态主动建议
   */
  async triggerInactiveReminder(user_id: string, other_user_id?: string) {
    return skillRegistry.triggerAutonomous('chat_assistant', 'inactive_reminder', user_id, {
      other_user_id
    })
  }
}

// 安全守护 Skill - 紧急求助
// AI Native 特性：自主触发（危险检测）、Generative UI（紧急面板）、分级响应
export const safetyGuardianSkill = {
  /**
   * 触发紧急求助
   * AI Native: 自动通知联系人 + 位置共享 + 分级响应
   */
  async triggerEmergency(
    user_id: string,
    emergency_type: 'general' | 'medical' | 'danger' | 'harassment' = 'general',
    location_data?: {
      latitude: number
      longitude: number
      address?: string
    },
    note?: string
  ): Promise<SafetyGuardianEmergencyResponse> {
    const result = await skillRegistry.execute('safety_guardian', {
      operation: 'trigger_emergency',
      user_id,
      emergency_type,
      location_data,
      note
    })
    if (!result.success) {
      throw new Error(result.error || '触发紧急求助失败')
    }
    return result.data as SafetyGuardianEmergencyResponse
  },

  /**
   * 通知紧急联系人
   * AI Native: 智能选择联系人 + 自动生成求助消息
   */
  async notifyEmergencyContact(
    user_id: string,
    contact_index: number = 0,
    location_data?: {
      latitude: number
      longitude: number
    },
    message?: string
  ): Promise<SafetyGuardianEmergencyResponse> {
    const result = await skillRegistry.execute('safety_guardian', {
      operation: 'notify_emergency_contact',
      user_id,
      contact_index,
      location_data,
      message
    })
    if (!result.success) {
      throw new Error(result.error || '通知紧急联系人失败')
    }
    return result.data as SafetyGuardianEmergencyResponse
  },

  /**
   * 自主触发：危险检测
   * AI Native: 基于位置和行为的主动危险识别
   */
  async triggerDangerDetection(user_id: string, context?: { location?: string; time?: string }) {
    return skillRegistry.triggerAutonomous('safety_guardian', 'danger_detection', user_id, context)
  },

  /**
   * 自主触发：安全签到提醒
   * AI Native: 定时确认用户安全状态
   */
  async triggerSafetyCheckin(user_id: string) {
    return skillRegistry.triggerAutonomous('safety_guardian', 'safety_checkin', user_id)
  }
}

// ==================== 对话式匹配 Skill ====================
// AI Native 特性：意图驱动匹配、自主推荐、话题建议
export const conversationMatchmakerSkill = {
  /**
   * 意图匹配 - 通过自然语言表达匹配需求
   */
  async matchByIntent(userId: string, intentText: string): Promise<ConversationMatchmakerSkillResponse> {
    const result = await skillRegistry.execute('conversation_matchmaker', {
      user_id: userId,
      action: 'match_by_intent',
      intent_text: intentText
    })
    if (!result.success) {
      throw new Error(result.error || '意图匹配失败')
    }
    return result.data as ConversationMatchmakerSkillResponse
  },

  /**
   * 每日推荐 - AI 主动分析用户状态，推送每日匹配
   */
  async getDailyRecommend(userId: string): Promise<ConversationMatchmakerSkillResponse> {
    const result = await skillRegistry.execute('conversation_matchmaker', {
      user_id: userId,
      action: 'get_daily_recommend'
    })
    if (!result.success) {
      throw new Error(result.error || '获取每日推荐失败')
    }
    return result.data as ConversationMatchmakerSkillResponse
  },

  /**
   * 话题建议 - 智能推荐聊天话题
   */
  async suggestTopics(userId: string, matchId: string): Promise<ConversationMatchmakerSkillResponse> {
    const result = await skillRegistry.execute('conversation_matchmaker', {
      user_id: userId,
      action: 'suggest_topics',
      match_id: matchId
    })
    if (!result.success) {
      throw new Error(result.error || '获取话题建议失败')
    }
    return result.data as ConversationMatchmakerSkillResponse
  },

  /**
   * 兼容性分析 - 分析两个用户的匹配度
   */
  async analyzeCompatibility(userId: string, targetUserId: string): Promise<ConversationMatchmakerSkillResponse> {
    const result = await skillRegistry.execute('conversation_matchmaker', {
      user_id: userId,
      action: 'analyze_compatibility',
      target_user_id: targetUserId
    })
    if (!result.success) {
      throw new Error(result.error || '兼容性分析失败')
    }
    return result.data as ConversationMatchmakerSkillResponse
  },

  /**
   * 自主触发：每日匹配推送
   */
  async triggerDailyMatch(userId: string) {
    return skillRegistry.triggerAutonomous('conversation_matchmaker', 'daily_match', userId)
  }
}

// ==================== 画像收集 Skill ====================
// AI Native 特性：对话式收集、智能追问、画像补全
export const profileCollectionSkill = {
  /**
   * 开始会话 - 启动画像收集对话
   */
  async startSession(userId: string): Promise<ProfileCollectionSkillResponse> {
    const result = await skillRegistry.execute('profile_collection', {
      user_id: userId,
      action: 'start_session'
    })
    if (!result.success) {
      throw new Error(result.error || '启动会话失败')
    }
    return result.data as ProfileCollectionSkillResponse
  },

  /**
   * 发送消息 - 向 AI 发送对话消息
   */
  async sendMessage(sessionId: string, userId: string, message: string): Promise<ProfileCollectionSkillResponse> {
    const result = await skillRegistry.execute('profile_collection', {
      user_id: userId,
      action: 'send_message',
      session_id: sessionId,
      message
    })
    if (!result.success) {
      throw new Error(result.error || '发送消息失败')
    }
    return result.data as ProfileCollectionSkillResponse
  },

  /**
   * 获取进度 - 查看画像收集进度
   */
  async getProgress(userId: string): Promise<ProfileCollectionSkillResponse> {
    const result = await skillRegistry.execute('profile_collection', {
      user_id: userId,
      action: 'get_progress'
    })
    if (!result.success) {
      throw new Error(result.error || '获取进度失败')
    }
    return result.data as ProfileCollectionSkillResponse
  },

  /**
   * 完成会话 - 结束画像收集并生成完整画像
   */
  async completeSession(userId: string): Promise<ProfileCollectionSkillResponse> {
    const result = await skillRegistry.execute('profile_collection', {
      user_id: userId,
      action: 'complete_session'
    })
    if (!result.success) {
      throw new Error(result.error || '完成会话失败')
    }
    return result.data as ProfileCollectionSkillResponse
  }
}

// 导出所有 Skills
export const skills = {
  // P0
  matchmaking: matchmakingSkill,
  preCommunication: preCommunicationSkill,
  omniscientInsight: omniscientInsightSkill,
  // P1
  relationshipCoach: relationshipCoachSkill,
  datePlanning: datePlanningSkill,
  // P19
  billAnalysis: billAnalysisSkill,
  // 注：geoLocation, giftOrdering, relationshipProgress 已删除，改用 REST API
  // 新增 Skills
  chatAssistant: chatAssistantSkill,
  safetyGuardian: safetyGuardianSkill,
  // AI Native 对话式能力
  conversationMatchmaker: conversationMatchmakerSkill,
  profileCollection: profileCollectionSkill,
}

export default skillRegistry
