// API 服务层 - 对接后端 AI Native 接口

import axios from 'axios'
import type {
  ConversationMatchRequest,
  ConversationMatchResponse,
  DailyRecommendResponse,
  RelationshipAnalysisRequest,
  RelationshipAnalysisResponse,
  TopicSuggestionRequest,
  TopicSuggestionResponse,
  CompatibilityAnalysis,
  MatchCandidate,
} from '../types'

const API_BASE_URL = 'http://localhost:8000'

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

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    throw error
  }
)

export const conversationMatchingApi = {
  /**
   * 对话式匹配 - 用户通过自然语言表达匹配需求
   */
  async match(request: ConversationMatchRequest): Promise<ConversationMatchResponse> {
    const response = await api.post('/api/conversation-matching/match', request)
    return response.data
  },

  /**
   * 每日自主推荐 - AI 主动分析用户状态，推送每日匹配
   */
  async dailyRecommend(): Promise<DailyRecommendResponse> {
    const response = await api.get('/api/conversation-matching/daily-recommend')
    return response.data
  },

  /**
   * 关系健康度分析
   */
  async analyzeRelationship(
    request: RelationshipAnalysisRequest
  ): Promise<RelationshipAnalysisResponse> {
    const response = await api.post('/api/conversation-matching/relationship/analyze', request)
    return response.data
  },

  /**
   * 获取关系状态
   */
  async getRelationshipStatus(matchId: string) {
    const response = await api.get(`/api/conversation-matching/relationship/${matchId}/status`)
    return response.data
  },

  /**
   * 智能话题推荐
   */
  async suggestTopics(request: TopicSuggestionRequest): Promise<TopicSuggestionResponse> {
    const response = await api.post('/api/conversation-matching/topics/suggest', request)
    return response.data
  },

  /**
   * 兼容性分析
   */
  async getCompatibility(targetUserId: string): Promise<CompatibilityAnalysis> {
    const response = await api.get(`/api/conversation-matching/compatibility/${targetUserId}`)
    return response.data
  },

  /**
   * 获取 AI 主动推送
   */
  async getAiPushRecommendations() {
    const response = await api.get('/api/conversation-matching/ai/push/recommendations')
    return response.data
  },
}

export const matchingApi = {
  /**
   * 获取推荐匹配列表
   */
  async getRecommendations(
    limit = 15,
    filters?: { age_min?: number; age_max?: number; distance?: number }
  ): Promise<MatchCandidate[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (filters?.age_min) params.append('age_min', filters.age_min.toString())
    if (filters?.age_max) params.append('age_max', filters.age_max.toString())
    if (filters?.distance) params.append('distance', filters.distance.toString())

    const response = await api.get(`/api/matching/recommend`, { params })
    return response.data
  },

  /**
   * 滑动操作
   */
  async swipe(targetUserId: string, action: 'like' | 'pass' | 'super_like') {
    const response = await api.post('/api/matching/swipe', {
      target_user_id: targetUserId,
      action,
    })
    return response.data
  },

  /**
   * 获取匹配列表
   */
  async getMatches(userId: string, limit = 10) {
    const response = await api.get(`/api/matching/${userId}/matches`, {
      params: { limit },
    })
    return response.data
  },
}

export const chatApi = {
  /**
   * 获取会话列表
   */
  async getConversations() {
    const response = await api.get('/api/chat/conversations')
    return response.data
  },

  /**
   * 获取聊天历史
   */
  async getChatHistory(otherUserId: string, limit = 50, offset = 0) {
    const response = await api.get(`/api/chat/history/${otherUserId}`, {
      params: { limit, offset },
    })
    return response.data
  },

  /**
   * 发送消息
   */
  async sendMessage(receiverId: string, content: string, messageType = 'text') {
    const response = await api.post('/api/chat/send', {
      receiver_id: receiverId,
      content,
      message_type: messageType,
    })
    return response.data
  },
}

export const userApi = {
  /**
   * 登录
   */
  async login(username: string, password: string) {
    const response = await api.post('/api/users/login', {
      username,
      password,
    })
    return response.data
  },

  /**
   * 注册
   */
  async register(userData: {
    username: string
    password: string
    name: string
    age: number
    gender: string
    location: string
    bio: string
    interests: string[]
  }) {
    const response = await api.post('/api/users/register', userData)
    return response.data
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser() {
    const response = await api.get('/api/users/me')
    return response.data
  },
}
