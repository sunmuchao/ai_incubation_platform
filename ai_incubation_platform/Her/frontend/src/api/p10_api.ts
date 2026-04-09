/**
 * P10 API 服务 - 关系里程碑、约会建议、双人互动游戏
 */

import axios from 'axios'
import type {
  Milestone,
  MilestoneTimeline,
  MilestoneStatistics,
  RecordMilestoneRequest,
  UpdateMilestoneRequest,
  DateSuggestion,
  DateSuggestionRequest,
  RespondToDateSuggestionRequest,
  DateVenue,
  CoupleGame,
  CoupleGameCreateRequest,
  SubmitGameRoundRequest,
  GameInsights,
} from '../types/p10_types'

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

// ==================== 关系里程碑 API ====================

export const milestoneApi = {
  /**
   * 记录关系里程碑
   */
  async recordMilestone(request: RecordMilestoneRequest): Promise<{ milestone_id: string; status: string }> {
    const response = await api.post('/api/milestones/record', request)
    return response.data
  },

  /**
   * 获取关系里程碑时间线
   */
  async getMilestoneTimeline(
    user_id_1: string,
    user_id_2: string,
    include_private = false
  ): Promise<MilestoneTimeline> {
    const response = await api.get(`/api/milestones/timeline/${user_id_1}/${user_id_2}`, {
      params: { include_private },
    })
    return response.data
  },

  /**
   * 获取里程碑详情
   */
  async getMilestoneDetails(milestone_id: string): Promise<Milestone> {
    const response = await api.get(`/api/milestones/${milestone_id}`)
    return response.data
  },

  /**
   * 更新里程碑
   */
  async updateMilestone(
    milestone_id: string,
    request: UpdateMilestoneRequest
  ): Promise<{ milestone_id: string; status: string }> {
    const response = await api.put(`/api/milestones/${milestone_id}`, request)
    return response.data
  },

  /**
   * 庆祝里程碑
   */
  async celebrateMilestone(
    milestone_id: string,
    celebration_type: 'card' | 'gift' | 'activity' = 'card'
  ): Promise<{ milestone_id: string; celebration_type: string; status: string }> {
    const response = await api.post(`/api/milestones/${milestone_id}/celebrate`, null, {
      params: { celebration_type },
    })
    return response.data
  },

  /**
   * 获取里程碑统计
   */
  async getMilestoneStatistics(
    user_id_1: string,
    user_id_2: string
  ): Promise<MilestoneStatistics> {
    const response = await api.get(`/api/milestones/stats/${user_id_1}/${user_id_2}`)
    return response.data
  },

  /**
   * 生成关系洞察
   */
  async generateInsight(request: {
    user_id_1: string
    user_id_2: string
    insight_type: string
    title: string
    content: string
    action_suggestion?: string
    priority?: string
    expires_hours?: number
  }): Promise<{ insight_id: string; status: string }> {
    const response = await api.post('/api/milestones/insights/generate', request)
    return response.data
  },

  /**
   * 获取用户的关系洞察
   */
  async getUserInsights(
    user_id: string,
    unread_only = false,
    limit = 20
  ): Promise<{ insights: any[] }> {
    const response = await api.get(`/api/milestones/insights/${user_id}`, {
      params: { unread_only, limit },
    })
    return response.data
  },

  /**
   * 标记洞察为已读
   */
  async markInsightRead(
    insight_id: string,
    user_id: string
  ): Promise<{ status: string }> {
    const response = await api.post(`/api/milestones/insights/${insight_id}/read`, {
      user_id,
    })
    return response.data
  },
}

// ==================== 约会建议 API ====================

export const dateSuggestionApi = {
  /**
   * 生成约会建议
   */
  async generateDateSuggestion(
    user_id: string,
    target_user_id: string,
    date_type: string,
    preferences?: Record<string, any>
  ): Promise<{ suggestion_id: string; status: string; suggestion?: DateSuggestion }> {
    const response = await api.post('/api/date-suggestions/generate', {
      user_id,
      target_user_id,
      date_type,
      preferences,
    })
    return response.data
  },

  /**
   * 获取用户的约会建议列表
   */
  async getUserDateSuggestions(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ suggestions: DateSuggestion[] }> {
    const response = await api.get(`/api/date-suggestions/list/${user_id}`, {
      params: { status, limit },
    })
    return response.data
  },

  /**
   * 响应约会建议
   */
  async respondToDateSuggestion(
    suggestion_id: string,
    request: RespondToDateSuggestionRequest
  ): Promise<{ status: string; action: string }> {
    const response = await api.post(`/api/date-suggestions/${suggestion_id}/respond`, request)
    return response.data
  },

  /**
   * 获取约会地点推荐
   */
  async getDateVenues(
    city: string,
    venue_type?: string,
    price_level?: number,
    limit = 20
  ): Promise<{ venues: DateVenue[] }> {
    const response = await api.get('/api/date-suggestions/venues', {
      params: { city, venue_type, price_level, limit },
    })
    return response.data
  },

  /**
   * 添加约会地点
   */
  async addDateVenue(venue: Omit<DateVenue, 'id'>): Promise<{ venue_id: string; status: string }> {
    const response = await api.post('/api/date-suggestions/venues', venue)
    return response.data
  },
}

// ==================== 双人互动游戏 API ====================

export const coupleGameApi = {
  /**
   * 创建双人互动游戏
   */
  async createCoupleGame(
    user_id_1: string,
    user_id_2: string,
    game_type: string,
    game_config?: Record<string, any>,
    difficulty: 'easy' | 'normal' | 'hard' = 'normal'
  ): Promise<{ game_id: string; status: string; game: CoupleGame }> {
    const response = await api.post('/api/couple-games/create', {
      user_id_1,
      user_id_2,
      game_type,
      game_config,
      difficulty,
    })
    return response.data
  },

  /**
   * 获取用户参与的游戏列表
   */
  async getUserGames(
    user_id: string,
    status?: string,
    limit = 10
  ): Promise<{ games: CoupleGame[] }> {
    const response = await api.get(`/api/couple-games/list/${user_id}`, {
      params: { status, limit },
    })
    return response.data
  },

  /**
   * 获取游戏详情
   */
  async getGameDetails(game_id: string): Promise<{ game: CoupleGame }> {
    const response = await api.get(`/api/couple-games/${game_id}`)
    return response.data
  },

  /**
   * 开始游戏
   */
  async startGame(
    game_id: string,
    user_id: string
  ): Promise<{ status: string; game_id: string }> {
    const response = await api.post(`/api/couple-games/${game_id}/start`, { user_id })
    return response.data
  },

  /**
   * 提交游戏轮次回答
   */
  async submitGameRound(request: SubmitGameRoundRequest): Promise<{ status: string; round_result: any }> {
    const response = await api.post(`/api/couple-games/${request.game_id}/round`, request)
    return response.data
  },

  /**
   * 完成游戏并获取结果洞察
   */
  async completeGame(
    game_id: string,
    user_id: string
  ): Promise<{ status: string; game: CoupleGame; insights: GameInsights }> {
    const response = await api.post(`/api/couple-games/${game_id}/complete`, { user_id })
    return response.data
  },

  /**
   * 获取游戏结果洞察
   */
  async getGameInsights(game_id: string): Promise<{ insights: GameInsights }> {
    const response = await api.get(`/api/couple-games/${game_id}/insights`)
    return response.data
  },
}
