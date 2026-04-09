/**
 * P15-P17 API 服务
 * P15: 虚实结合 - 自主约会策划、情感纪念册
 * P16: 圈子融合 - 部落匹配、数字小家、见家长模拟
 * P17: 终极共振 - 压力测试、成长计划、信任背书
 */

import axios from 'axios'
import type {
  // P15
  AutonomousDatePlan,
  CreateDatePlanRequest,
  ApproveDatePlanRequest,
  RelationshipAlbum,
  GenerateAlbumRequest,
  AddMemoryRequest,
  CoupleFootprint,
  // P16
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
  // P17
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
} from '../types/p15_p16_p17_types'

const API_BASE_URL = ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ==================== P15: 虚实结合 ====================

// --- 自主约会策划 API ---
export const datePlanApi = {
  /**
   * 创建自主约会计划
   */
  async createDatePlan(
    request: CreateDatePlanRequest
  ): Promise<{ success: boolean; plan: AutonomousDatePlan }> {
    const response = await api.post('/api/p15/date-plan/create', request)
    return response.data
  },

  /**
   * 获取约会计划详情
   */
  async getDatePlan(plan_id: string): Promise<{ success: boolean; plan: AutonomousDatePlan }> {
    const response = await api.get(`/api/p15/date-plan/${plan_id}`)
    return response.data
  },

  /**
   * 批准约会计划
   */
  async approveDatePlan(
    request: ApproveDatePlanRequest
  ): Promise<{ success: boolean; plan: AutonomousDatePlan }> {
    const response = await api.post('/api/p15/date-plan/approve', request)
    return response.data
  },

  /**
   * 获取用户的约会计划列表
   */
  async getUserDatePlans(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ success: boolean; plans: AutonomousDatePlan[] }> {
    const response = await api.get(`/api/p15/date-plan/list/${user_id}`, {
      params: { status, limit },
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
    const response = await api.post('/api/p15/date-plan/cancel', {
      plan_id,
      user_id,
      reason,
    })
    return response.data
  },
}

// --- 情感纪念册 API ---
export const albumApi = {
  /**
   * 生成情感纪念册
   */
  async generateAlbum(
    request: GenerateAlbumRequest
  ): Promise<{ success: boolean; album: RelationshipAlbum }> {
    const response = await api.post('/api/p15/album/generate', request)
    return response.data
  },

  /**
   * 获取纪念册详情
   */
  async getAlbum(album_id: string): Promise<{ success: boolean; album: RelationshipAlbum }> {
    const response = await api.get(`/api/p15/album/${album_id}`)
    return response.data
  },

  /**
   * 获取用户的纪念册列表
   */
  async getUserAlbums(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; albums: RelationshipAlbum[] }> {
    const response = await api.get(`/api/p15/album/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 添加记忆到纪念册
   */
  async addMemory(
    request: AddMemoryRequest
  ): Promise<{ success: boolean; memory_id: string }> {
    const response = await api.post('/api/p15/album/memory/add', request)
    return response.data
  },

  /**
   * 获取共同足迹
   */
  async getCoupleFootprints(
    user_a_id: string,
    user_b_id: string,
    limit = 20
  ): Promise<{ success: boolean; footprints: CoupleFootprint[] }> {
    const response = await api.get(`/api/p15/album/footprints/${user_a_id}/${user_b_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 添加共同足迹
   */
  async addCoupleFootprint(
    user_a_id: string,
    user_b_id: string,
    footprint: Omit<CoupleFootprint, 'id'>
  ): Promise<{ success: boolean; footprint_id: string }> {
    const response = await api.post('/api/p15/album/footprints/add', {
      user_a_id,
      user_b_id,
      footprint,
    })
    return response.data
  },
}

// ==================== P16: 圈子融合 ====================

// --- 部落匹配 API ---
export const tribeApi = {
  /**
   * 分析用户部落适配度
   */
  async analyzeTribeFit(
    user_id: string,
    lifestyle_data: AnalyzeTribeFitRequest['lifestyle_data']
  ): Promise<{ success: boolean; tribes: LifestyleTribe[]; fit_scores: any[] }> {
    const response = await api.post('/api/p16/tribe/analyze-fit', {
      user_id,
      lifestyle_data,
    })
    return response.data
  },

  /**
   * 获取用户的部落成员关系
   */
  async getUserTribes(user_id: string): Promise<{ success: boolean; memberships: any[] }> {
    const response = await api.get(`/api/p16/tribe/memberships/${user_id}`)
    return response.data
  },

  /**
   * 获取部落兼容性分析
   */
  async getTribeCompatibility(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; compatibility: TribeCompatibilityAnalysis }> {
    const response = await api.get(`/api/p16/tribe/compatibility/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 获取所有部落列表
   */
  async getAllTribes(): Promise<{ success: boolean; tribes: LifestyleTribe[] }> {
    const response = await api.get('/api/p16/tribe/list')
    return response.data
  },

  /**
   * 加入部落
   */
  async joinTribe(
    user_id: string,
    tribe_id: string
  ): Promise<{ success: boolean; membership_id: string }> {
    const response = await api.post('/api/p16/tribe/join', { user_id, tribe_id })
    return response.data
  },
}

// --- 数字小家 API ---
export const digitalHomeApi = {
  /**
   * 创建数字小家
   */
  async createDigitalHome(
    request: CreateDigitalHomeRequest
  ): Promise<{ success: boolean; home: DigitalHome }> {
    const response = await api.post('/api/p16/digital-home/create', request)
    return response.data
  },

  /**
   * 获取数字小家详情
   */
  async getDigitalHome(home_id: string): Promise<{ success: boolean; home: DigitalHome }> {
    const response = await api.get(`/api/p16/digital-home/${home_id}`)
    return response.data
  },

  /**
   * 获取用户的数字小家
   */
  async getUserDigitalHomes(user_id: string): Promise<{ success: boolean; homes: DigitalHome[] }> {
    const response = await api.get(`/api/p16/digital-home/list/${user_id}`)
    return response.data
  },

  /**
   * 创建共同目标
   */
  async createCoupleGoal(
    request: CreateCoupleGoalRequest
  ): Promise<{ success: boolean; goal: CoupleGoal }> {
    const response = await api.post('/api/p16/digital-home/goal/create', request)
    return response.data
  },

  /**
   * 目标打卡
   */
  async goalCheckin(
    request: GoalCheckinRequest
  ): Promise<{ success: boolean; goal: CoupleGoal }> {
    const response = await api.post('/api/p16/digital-home/goal/checkin', request)
    return response.data
  },

  /**
   * 获取目标详情
   */
  async getGoalDetails(goal_id: string): Promise<{ success: boolean; goal: CoupleGoal }> {
    const response = await api.get(`/api/p16/digital-home/goal/${goal_id}`)
    return response.data
  },

  /**
   * 更新目标
   */
  async updateGoal(
    goal_id: string,
    updates: Partial<CoupleGoal>
  ): Promise<{ success: boolean; goal: CoupleGoal }> {
    const response = await api.put(`/api/p16/digital-home/goal/${goal_id}`, updates)
    return response.data
  },
}

// --- 见家长模拟 API ---
export const familySimApi = {
  /**
   * 开始见家长模拟
   */
  async startFamilySimulation(
    user_id: string,
    request: StartFamilySimulationRequest
  ): Promise<{ success: boolean; simulation: FamilyMeetingSimulation }> {
    const response = await api.post('/api/p16/family-sim/start', {
      user_id,
      ...request,
    })
    return response.data
  },

  /**
   * 提交对话轮次
   */
  async submitFamilyConversationTurn(
    request: SubmitFamilyConversationTurnRequest
  ): Promise<{
    success: boolean
    simulation: FamilyMeetingSimulation
    turn_result: { impression_score: number; feedback: string }
  }> {
    const response = await api.post('/api/p16/family-sim/submit-turn', request)
    return response.data
  },

  /**
   * 获取模拟详情
   */
  async getFamilySimulationDetails(
    simulation_id: string
  ): Promise<{ success: boolean; simulation: FamilyMeetingSimulation }> {
    const response = await api.get(`/api/p16/family-sim/${simulation_id}`)
    return response.data
  },

  /**
   * 获取模拟反馈报告
   */
  async getFamilySimulationFeedback(
    simulation_id: string
  ): Promise<{
    success: boolean
    metrics: any
    feedback: any
    ai_summary: string
  }> {
    const response = await api.get(`/api/p16/family-sim/${simulation_id}/feedback`)
    return response.data
  },

  /**
   * 获取用户的模拟历史
   */
  async getUserFamilySimulations(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; simulations: FamilyMeetingSimulation[] }> {
    const response = await api.get(`/api/p16/family-sim/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}

// ==================== P17: 终极共振 ====================

// --- 压力测试 API ---
export const stressTestApi = {
  /**
   * 开始压力测试
   */
  async startStressTest(
    user_a_id: string,
    user_b_id: string,
    scenario_type: string
  ): Promise<{ success: boolean; test: StressTest }> {
    const response = await api.post('/api/p17/stress-test/start', {
      user_a_id,
      user_b_id,
      scenario_type,
    })
    return response.data
  },

  /**
   * 提交压力测试回答
   */
  async submitStressResponse(
    request: SubmitStressResponseRequest
  ): Promise<{ success: boolean; test: StressTest }> {
    const response = await api.post('/api/p17/stress-test/submit', request)
    return response.data
  },

  /**
   * 获取压力测试详情
   */
  async getStressTestDetails(test_id: string): Promise<{ success: boolean; test: StressTest }> {
    const response = await api.get(`/api/p17/stress-test/${test_id}`)
    return response.data
  },

  /**
   * 获取压力测试结果
   */
  async getStressTestResults(
    test_id: string
  ): Promise<{
    success: boolean
    compatibility_analysis: any
    recommendations: string[]
    ai_summary: string
  }> {
    const response = await api.get(`/api/p17/stress-test/${test_id}/results`)
    return response.data
  },

  /**
   * 获取用户的压力测试历史
   */
  async getUserStressTests(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; tests: StressTest[] }> {
    const response = await api.get(`/api/p17/stress-test/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}

// --- 成长计划 API ---
export const growthPlanApi = {
  /**
   * 创建成长计划
   */
  async createGrowthPlan(
    request: CreateGrowthPlanRequest
  ): Promise<{ success: boolean; plan: GrowthPlan }> {
    const response = await api.post('/api/p17/growth-plan/create', request)
    return response.data
  },

  /**
   * 获取成长计划详情
   */
  async getGrowthPlan(plan_id: string): Promise<{ success: boolean; plan: GrowthPlan }> {
    const response = await api.get(`/api/p17/growth-plan/${plan_id}`)
    return response.data
  },

  /**
   * 获取用户的成长计划
   */
  async getUserGrowthPlans(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ success: boolean; plans: GrowthPlan[] }> {
    const response = await api.get(`/api/p17/growth-plan/list/${user_id}`, {
      params: { status, limit },
    })
    return response.data
  },

  /**
   * 成长计划打卡
   */
  async growthPlanCheckin(
    request: GrowthPlanCheckinRequest
  ): Promise<{ success: boolean; plan: GrowthPlan }> {
    const response = await api.post('/api/p17/growth-plan/checkin', request)
    return response.data
  },

  /**
   * 获取成长资源推荐
   */
  async getGrowthResources(
    plan_id: string,
    category?: string
  ): Promise<{ success: boolean; resources: any[] }> {
    const response = await api.get(`/api/p17/growth-plan/${plan_id}/resources`, {
      params: { category },
    })
    return response.data
  },

  /**
   * 更新成长计划
   */
  async updateGrowthPlan(
    plan_id: string,
    updates: Partial<GrowthPlan>
  ): Promise<{ success: boolean; plan: GrowthPlan }> {
    const response = await api.put(`/api/p17/growth-plan/${plan_id}`, updates)
    return response.data
  },
}

// --- 信任背书 API ---
export const trustApi = {
  /**
   * 获取用户信任分
   */
  async getUserTrustScore(user_id: string): Promise<{ success: boolean; trust_score: TrustScore }> {
    const response = await api.get(`/api/p17/trust/score/${user_id}`)
    return response.data
  },

  /**
   * 提交信任背书
   */
  async submitTrustEndorsement(
    request: TrustEndorsementRequest
  ): Promise<{ success: boolean; endorsement_id: string }> {
    const response = await api.post('/api/p17/trust/endorse', request)
    return response.data
  },

  /**
   * 获取用户的背书列表
   */
  async getUserEndorsements(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; endorsements: any[] }> {
    const response = await api.get(`/api/p17/trust/endorsements/${user_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 验证声明
   */
  async verifyClaim(
    request: VerifyClaimRequest
  ): Promise<{ success: boolean; claim_id: string }> {
    const response = await api.post('/api/p17/trust/verify', request)
    return response.data
  },

  /**
   * 获取信任分对比
   */
  async getTrustScoreComparison(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; comparison: TrustScoreComparison }> {
    const response = await api.get(`/api/p17/trust/compare/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 获取用户的验证声明列表
   */
  async getUserVerifiedClaims(user_id: string): Promise<{ success: boolean; claims: any[] }> {
    const response = await api.get(`/api/p17/trust/claims/${user_id}`)
    return response.data
  },
}
