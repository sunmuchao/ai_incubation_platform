/**
 * 生活融合 API 服务
 * 包含：自主约会、情感纪念册、部落匹配、数字小家、见家长模拟、压力测试、成长计划、信任背书
 */

import { apiClient } from './apiClient'
import type {
  AutonomousDatePlan,
  CreateDatePlanRequest,
  ApproveDatePlanRequest,
  RelationshipAlbum,
  GenerateAlbumRequest,
  AddMemoryRequest,
  CoupleFootprint,
  LifestyleTribe,
  TribeCompatibilityAnalysis,
  AnalyzeTribeFitRequest,
  DigitalHome,
  CreateDigitalHomeRequest,
  CoupleGoal,
  CreateCoupleGoalRequest,
  GoalCheckinRequest,
  FamilyMeetingSimulation,
  StartFamilySimulationRequest,
  SubmitFamilyConversationTurnRequest,
  StressTest,
  StartStressTestRequest,
  SubmitStressResponseRequest,
  GrowthPlan,
  CreateGrowthPlanRequest,
  GrowthPlanCheckinRequest,
  TrustScore,
  TrustEndorsementRequest,
  VerifyClaimRequest,
  TrustScoreComparison,
} from '../types/lifeIntegrationTypes'

// ==================== P15: 自主约会 ====================

export const autonomousDatingApi = {
  /**
   * 创建自主约会计划
   */
  async createDatePlan(
    user_a_id: string,
    user_b_id: string,
    user_a_location: { lat: number; lon: number },
    user_b_location: { lat: number; lon: number },
    preferences: Record<string, any>
  ): Promise<{ success: boolean; plan_id: string }> {
    const response = await apiClient.post('/api/autonomous-dating/create', {
      user_a_id,
      user_b_id,
      user_a_lat: user_a_location.lat,
      user_a_lon: user_a_location.lon,
      user_b_lat: user_b_location.lat,
      user_b_lon: user_b_location.lon,
      preferences,
    })
    return response.data
  },

  /**
   * 获取约会计划详情
   */
  async getDatePlan(plan_id: string): Promise<{ success: boolean; plan: any }> {
    const response = await apiClient.get(`/api/autonomous-dating/${plan_id}`)
    return response.data
  },

  /**
   * 批准约会计划
   */
  async approveDatePlan(
    plan_id: string,
    user_id: string,
    modifications?: Record<string, any>
  ): Promise<{ success: boolean; plan: any }> {
    const response = await apiClient.post(`/api/autonomous-dating/${plan_id}/approve`, {
      user_id,
      modifications,
    })
    return response.data
  },

  /**
   * 取消约会计划
   */
  async cancelDatePlan(
    plan_id: string,
    user_id: string,
    reason?: string
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post(`/api/autonomous-dating/${plan_id}/cancel`, {
      user_id,
      reason,
    })
    return response.data
  },

  /**
   * 获取用户的约会计划列表
   */
  async getUserDatePlans(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ success: boolean; plans: any[] }> {
    const response = await apiClient.get(`/api/autonomous-dating/list/${user_id}`, {
      params: { status, limit },
    })
    return response.data
  },
}

// ==================== P15: 情感纪念册 ====================

export const relationshipAlbumsApi = {
  /**
   * 创建情感纪念册
   */
  async createAlbum(
    user_a_id: string,
    user_b_id: string,
    title: string,
    album_type: 'moment' | 'journey' | 'milestone' = 'moment'
  ): Promise<{ success: boolean; album_id: string }> {
    const response = await apiClient.post('/api/relationship-albums/create', {
      user_a_id,
      user_b_id,
      title,
      album_type,
    })
    return response.data
  },

  /**
   * 获取纪念册详情
   */
  async getAlbum(album_id: string): Promise<{ success: boolean; album: any }> {
    const response = await apiClient.get(`/api/relationship-albums/${album_id}`)
    return response.data
  },

  /**
   * 获取用户的纪念册列表
   */
  async getUserAlbums(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; albums: any[] }> {
    const response = await apiClient.get(`/api/relationship-albums/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 添加记忆到纪念册
   */
  async addMemory(
    album_id: string,
    memory_type: string,
    memory_content: string,
    memory_date?: string
  ): Promise<{ success: boolean; memory_id: string }> {
    const response = await apiClient.post(`/api/relationship-albums/${album_id}/memory`, {
      memory_type,
      memory_content,
      memory_date,
    })
    return response.data
  },
}

// ==================== P16: 部落匹配 ====================

export const socialTribesApi = {
  /**
   * 检查部落兼容性
   */
  async checkTribeCompatibility(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; compatibility: any }> {
    const response = await apiClient.post('/api/social-tribes/compatibility', {
      user_a_id,
      user_b_id,
    })
    return response.data
  },

  /**
   * 获取用户的部落
   */
  async getUserTribes(user_id: string): Promise<{ success: boolean; tribes: any[] }> {
    const response = await apiClient.get(`/api/social-tribes/user/${user_id}`)
    return response.data
  },

  /**
   * 加入部落
   */
  async joinTribe(
    user_id: string,
    tribe_id: string
  ): Promise<{ success: boolean; membership_id: string }> {
    const response = await apiClient.post('/api/social-tribes/join', {
      user_id,
      tribe_id,
    })
    return response.data
  },

  /**
   * 获取所有部落列表
   */
  async getAllTribes(): Promise<{ success: boolean; tribes: any[] }> {
    const response = await apiClient.get('/api/social-tribes/list')
    return response.data
  },
}

// ==================== P16: 数字小家 ====================

export const digitalHomesApi = {
  /**
   * 创建数字小家
   */
  async createDigitalHome(
    user_a_id: string,
    user_b_id: string,
    home_name: string,
    theme?: string
  ): Promise<{ success: boolean; home_id: string }> {
    const response = await apiClient.post('/api/digital-homes/create', {
      user_a_id,
      user_b_id,
      home_name,
      theme,
    })
    return response.data
  },

  /**
   * 获取数字小家详情
   */
  async getDigitalHome(home_id: string): Promise<{ success: boolean; home: any }> {
    const response = await apiClient.get(`/api/digital-homes/${home_id}`)
    return response.data
  },

  /**
   * 获取用户的数字小家列表
   */
  async getUserDigitalHomes(user_id: string): Promise<{ success: boolean; homes: any[] }> {
    const response = await apiClient.get(`/api/digital-homes/list/${user_id}`)
    return response.data
  },

  /**
   * 创建共同目标
   */
  async createCoupleGoal(
    home_id: string,
    user_a_id: string,
    user_b_id: string,
    goal_title: string,
    goal_type: string,
    target_value: number,
    target_date: string
  ): Promise<{ success: boolean; goal_id: string }> {
    const response = await apiClient.post('/api/digital-homes/goal/create', {
      home_id,
      user_a_id,
      user_b_id,
      goal_title,
      goal_type,
      target_value,
      target_date,
    })
    return response.data
  },

  /**
   * 更新目标进度
   */
  async updateGoalProgress(
    goal_id: string,
    progress: number,
    user_id: string
  ): Promise<{ success: boolean; goal: any }> {
    const response = await apiClient.post(`/api/digital-homes/goal/${goal_id}/progress`, {
      progress,
      user_id,
    })
    return response.data
  },
}

// ==================== P16: 见家长模拟 ====================

export const familyMeetingApi = {
  /**
   * 创建虚拟角色
   */
  async createVirtualRole(
    user_id: string,
    role_name: string,
    role_type: 'parent' | 'elder' | 'relative',
    personality: string
  ): Promise<{ success: boolean; role_id: string }> {
    const response = await apiClient.post('/api/family-meeting-simulation/role/create', {
      user_id,
      role_name,
      role_type,
      personality,
    })
    return response.data
  },

  /**
   * 开始模拟
   */
  async startSimulation(
    user_id: string,
    role_ids: string[]
  ): Promise<{ success: boolean; simulation_id: string }> {
    const response = await apiClient.post('/api/family-meeting-simulation/start', {
      user_id,
      role_ids,
    })
    return response.data
  },

  /**
   * 添加模拟对话
   */
  async addSimulationMessage(
    simulation_id: string,
    role: 'user' | 'virtual',
    content: string
  ): Promise<{ success: boolean; feedback?: string }> {
    const response = await apiClient.post(`/api/family-meeting-simulation/${simulation_id}/message`, {
      role,
      content,
    })
    return response.data
  },

  /**
   * 完成模拟并获取反馈
   */
  async completeSimulation(
    simulation_id: string
  ): Promise<{ success: boolean; feedback: any }> {
    const response = await apiClient.post(`/api/family-meeting-simulation/${simulation_id}/complete`)
    return response.data
  },
}

// ==================== P17: 压力测试 ====================
// 注：已删除后端 REST API，改用 relationshipCoachSkill
// 请使用 skillClient.ts 中的 relationshipCoachSkill.healthCheck() 或 .getAdvice()

// ==================== P17: 成长计划 ====================

export const growthPlansApi = {
  /**
   * 创建成长计划
   */
  async createGrowthPlan(
    user_a_id: string,
    user_b_id: string,
    plan_name: string,
    growth_goals: any[]
  ): Promise<{ success: boolean; plan_id: string }> {
    const response = await apiClient.post('/api/growth-plans/plan/create', {
      user_a_id,
      user_b_id,
      plan_name,
      growth_goals,
    })
    return response.data
  },

  /**
   * 获取成长计划详情
   */
  async getGrowthPlan(plan_id: string): Promise<{ success: boolean; plan: any }> {
    const response = await apiClient.get(`/api/growth-plans/${plan_id}`)
    return response.data
  },

  /**
   * 更新成长计划进度
   */
  async updateGrowthProgress(
    plan_id: string,
    goal_id: string,
    progress: number,
    user_id: string
  ): Promise<{ success: boolean; plan: any }> {
    const response = await apiClient.post(`/api/growth-plans/${plan_id}/progress`, {
      goal_id,
      progress,
      user_id,
    })
    return response.data
  },

  /**
   * 获取用户的成长计划列表
   */
  async getUserGrowthPlans(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; plans: any[] }> {
    const response = await apiClient.get(`/api/growth-plans/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}

// ==================== P17: 信任背书 ====================

export const trustEndorsementsApi = {
  /**
   * 计算信任分
   */
  async calculateTrustScore(
    user_id: string
  ): Promise<{ success: boolean; trust_score: number; trust_level: string }> {
    const response = await apiClient.post('/api/trust-endorsements/score/calculate', {
      user_id,
    })
    return response.data
  },

  /**
   * 获取信任分详情
   */
  async getTrustScore(user_id: string): Promise<{ success: boolean; score: any }> {
    const response = await apiClient.get(`/api/trust-endorsements/score/${user_id}`)
    return response.data
  },

  /**
   * 添加信任背书
   */
  async addEndorsement(
    endorsed_user_id: string,
    endorser_user_id: string,
    endorsement_type: string,
    endorsement_text: string,
    relationship_context: string
  ): Promise<{ success: boolean; endorsement_id: string }> {
    const response = await apiClient.post('/api/trust-endorsements/endorse', {
      endorsed_user_id,
      endorser_user_id,
      endorsement_type,
      endorsement_text,
      relationship_context,
    })
    return response.data
  },

  /**
   * 获取用户的背书列表
   */
  async getUserEndorsements(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; endorsements: any[] }> {
    const response = await apiClient.get(`/api/trust-endorsements/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}