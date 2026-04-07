/**
 * AI 对话式 API 服务
 */
import axios from 'axios'
import type {
  ChatRequest,
  ChatResponse,
  SessionInfo,
} from '@/types/chat'

// 创建 axios 实例
const chatApi = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8005',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
chatApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  const userId = localStorage.getItem('user_id') || 'guest_user'

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  config.headers['X-User-ID'] = userId
  config.headers['X-Request-ID'] = generateRequestId()

  return config
})

// 响应拦截器
chatApi.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

function generateRequestId(): string {
  return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 发送对话消息
 */
export const sendChatMessage = async (
  message: string,
  sessionId?: string,
  communityId?: string,
  conversationHistory?: Array<{
    role: string
    content: string
    timestamp?: string
  }>
): Promise<ChatResponse> => {
  const userId = localStorage.getItem('user_id') || 'guest_user'

  const request: ChatRequest = {
    user_id: userId,
    message,
    session_id: sessionId,
    community_id: communityId,
    conversation_history: conversationHistory,
  }

  const response = await chatApi.post('/api/chat', request)
  return response as unknown as ChatResponse
}

/**
 * 快捷发起团购
 */
export const quickStartGroup = async (
  communityId?: string
): Promise<ChatResponse> => {
  const userId = localStorage.getItem('user_id') || 'guest_user'

  const response = await chatApi.post('/api/chat/quick-start', {
    user_id: userId,
    community_id: communityId,
  })

  return response as unknown as ChatResponse
}

/**
 * 清空会话历史
 */
export const clearSessionHistory = async (sessionId: string): Promise<void> => {
  await chatApi.post(`/api/chat/sessions/${sessionId}/clear`)
}

/**
 * 删除会话
 */
export const deleteSession = async (sessionId: string): Promise<void> => {
  await chatApi.delete(`/api/chat/sessions/${sessionId}`)
}

/**
 * 获取用户对话历史
 */
export const getUserChatHistory = async (
  userId: string,
  limit: number = 10
): Promise<SessionInfo[]> => {
  const response = await chatApi.get(`/api/chat/history/${userId}`, {
    params: { limit },
  })
  return response.data as unknown as SessionInfo[]
}

/**
 * 获取工具列表
 */
export const getAvailableTools = async (): Promise<any[]> => {
  const response = await chatApi.get('/tools')
  return response.data?.tools || []
}

export default chatApi
