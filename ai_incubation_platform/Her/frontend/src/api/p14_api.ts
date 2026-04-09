/**
 * P14 API 服务 - 实战演习
 * 包含：约会模拟沙盒、约会辅助、多代理协作
 */

import axios from 'axios'
import type {
  AIDateAvatar,
  CreateAIDateAvatarRequest,
  DateSimulation,
  StartSimulationRequest,
  SubmitSimulationTurnRequest,
  OutfitRecommendation,
  GetOutfitRecommendationRequest,
  VenueStrategy,
  GetVenueStrategyRequest,
  TopicKit,
  GetTopicKitRequest,
  MultiAgentSession,
} from '../types/p14_types'

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

// ==================== AI 分身 API ====================

export const avatarApi = {
  /**
   * 创建 AI 约会分身
   */
  async createAIDateAvatar(
    user_id: string,
    request: CreateAIDateAvatarRequest
  ): Promise<{ success: boolean; avatar: AIDateAvatar }> {
    const response = await api.post('/api/p14/avatar/create', {
      user_id,
      ...request,
    })
    return response.data
  },

  /**
   * 获取用户的 AI 分身列表
   */
  async getUserAvatars(user_id: string): Promise<{ success: boolean; avatars: AIDateAvatar[] }> {
    const response = await api.get(`/api/p14/avatar/list/${user_id}`)
    return response.data
  },

  /**
   * 获取 AI 分身详情
   */
  async getAvatarDetails(avatar_id: string): Promise<{ success: boolean; avatar: AIDateAvatar }> {
    const response = await api.get(`/api/p14/avatar/${avatar_id}`)
    return response.data
  },

  /**
   * 更新 AI 分身
   */
  async updateAvatar(
    avatar_id: string,
    updates: Partial<AIDateAvatar>
  ): Promise<{ success: boolean; avatar: AIDateAvatar }> {
    const response = await api.put(`/api/p14/avatar/${avatar_id}`, updates)
    return response.data
  },

  /**
   * 删除 AI 分身
   */
  async deleteAvatar(avatar_id: string): Promise<{ success: boolean }> {
    const response = await api.delete(`/api/p14/avatar/${avatar_id}`)
    return response.data
  },
}

// ==================== 约会模拟 API ====================

export const simulationApi = {
  /**
   * 开始约会模拟
   */
  async startSimulation(
    user_id: string,
    request: StartSimulationRequest
  ): Promise<{ success: boolean; simulation: DateSimulation }> {
    const response = await api.post('/api/p14/simulation/start', {
      user_id,
      ...request,
    })
    return response.data
  },

  /**
   * 提交模拟对话轮次
   */
  async submitSimulationTurn(
    request: SubmitSimulationTurnRequest
  ): Promise<{
    success: boolean
    simulation: DateSimulation
    turn_result: { feedback: string; score: number; suggestion: string }
  }> {
    const response = await api.post('/api/p14/simulation/submit-turn', request)
    return response.data
  },

  /**
   * 获取模拟详情
   */
  async getSimulationDetails(simulation_id: string): Promise<{ success: boolean; simulation: DateSimulation }> {
    const response = await api.get(`/api/p14/simulation/${simulation_id}`)
    return response.data
  },

  /**
   * 获取用户的模拟历史
   */
  async getUserSimulations(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ success: boolean; simulations: DateSimulation[] }> {
    const response = await api.get(`/api/p14/simulation/list/${user_id}`, {
      params: { status, limit },
    })
    return response.data
  },

  /**
   * 获取模拟反馈报告
   */
  async getSimulationFeedback(simulation_id: string): Promise<{
    success: boolean
    overall_score: number
    feedback: any[]
    ai_summary: string
    improvement_suggestions: string[]
  }> {
    const response = await api.get(`/api/p14/simulation/${simulation_id}/feedback`)
    return response.data
  },
}

// ==================== 穿搭推荐 API ====================

export const outfitApi = {
  /**
   * 获取穿搭推荐
   */
  async getOutfitRecommendation(
    user_id: string,
    request: GetOutfitRecommendationRequest
  ): Promise<{ success: boolean; recommendation: OutfitRecommendation }> {
    const response = await api.post('/api/p14/outfit/recommend', {
      user_id,
      ...request,
    })
    return response.data
  },

  /**
   * 获取穿搭推荐历史
   */
  async getUserOutfitHistory(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; recommendations: OutfitRecommendation[] }> {
    const response = await api.get(`/api/p14/outfit/history/${user_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 保存穿搭推荐
   */
  async saveOutfitRecommendation(
    user_id: string,
    recommendation: Omit<OutfitRecommendation, 'id' | 'created_at'>
  ): Promise<{ success: boolean; recommendation_id: string }> {
    const response = await api.post('/api/p14/outfit/save', {
      user_id,
      recommendation,
    })
    return response.data
  },
}

// ==================== 场所策略 API ====================

export const venueApi = {
  /**
   * 获取场所策略
   */
  async getVenueStrategy(
    request: GetVenueStrategyRequest
  ): Promise<{ success: boolean; strategy: VenueStrategy }> {
    const response = await api.post('/api/p14/venue/strategy', request)
    return response.data
  },

  /**
   * 获取场所列表
   */
  async getVenues(
    city: string,
    venue_type?: string,
    limit = 20
  ): Promise<{ success: boolean; venues: any[] }> {
    const response = await api.get('/api/p14/venue/list', {
      params: { city, venue_type, limit },
    })
    return response.data
  },
}

// ==================== 话题锦囊 API ====================

export const topicApi = {
  /**
   * 获取话题锦囊
   */
  async getTopicKit(
    user_id: string,
    request: GetTopicKitRequest
  ): Promise<{ success: boolean; topic_kit: TopicKit }> {
    const response = await api.post('/api/p14/topic/kit', {
      user_id,
      ...request,
    })
    return response.data
  },

  /**
   * 获取应急话题
   */
  async getEmergencyTopics(
    user_id: string,
    context: 'awkward_silence' | 'conversation_stuck' | 'need_deepening'
  ): Promise<{ success: boolean; topics: any[] }> {
    const response = await api.get(`/api/p14/topic/emergency/${user_id}`, {
      params: { context },
    })
    return response.data
  },

  /**
   * 获取个性化话题
   */
  async getPersonalizedTopics(
    user_id: string,
    target_user_id: string
  ): Promise<{ success: boolean; topics: any[] }> {
    const response = await api.get(`/api/p14/topic/personalized/${user_id}`, {
      params: { target_user_id },
    })
    return response.data
  },
}

// ==================== 多代理协作 API ====================

export const multiAgentApi = {
  /**
   * 启动多代理会话
   */
  async startMultiAgentSession(
    user_id: string,
    session_type: 'date_coaching' | 'relationship_analysis' | 'safety_review',
    session_data: any
  ): Promise<{ success: boolean; session: MultiAgentSession }> {
    const response = await api.post('/api/p14/agent/session/start', {
      user_id,
      session_type,
      session_data,
    })
    return response.data
  },

  /**
   * 获取多代理会话结果
   */
  async getMultiAgentSessionResult(
    session_id: string
  ): Promise<{ success: boolean; session: MultiAgentSession }> {
    const response = await api.get(`/api/p14/agent/session/${session_id}`)
    return response.data
  },

  /**
   * 获取用户的会话历史
   */
  async getUserAgentSessions(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; sessions: MultiAgentSession[] }> {
    const response = await api.get(`/api/p14/agent/session/list/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}
