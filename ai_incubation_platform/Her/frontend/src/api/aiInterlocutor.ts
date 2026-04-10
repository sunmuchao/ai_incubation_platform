// AI 预沟通 API 客户端
// P18: AI Interlocutor - 替你先聊 50 句，只聊有价值的后半段

import type {
  AIPreCommunicationSession,
  AIPreCommunicationMessage,
} from '../types'
import { authStorage } from '../utils/storage'

const API_BASE = '/api/ai/interlocutor'

// 获取认证头
const getAuthHeaders = () => {
  const token = authStorage.getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

/**
 * 启动 AI 预沟通会话
 */
export const startPreCommunication = async (
  targetUserId: string,
  targetRounds: number = 50
): Promise<AIPreCommunicationSession> => {
  const response = await fetch(`${API_BASE}/start`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      target_user_id: targetUserId,
      target_rounds: targetRounds,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '启动预沟通失败')
  }

  return response.json()
}

/**
 * 获取预沟通会话状态
 */
export const getPreCommunicationStatus = async (
  sessionId: string
): Promise<AIPreCommunicationSession> => {
  const response = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取会话状态失败')
  }

  return response.json()
}

/**
 * 获取我的预沟通会话列表
 */
export const getMyPreCommunicationSessions = async (
  statusFilter?: string
): Promise<AIPreCommunicationSession[]> => {
  const url = statusFilter
    ? `${API_BASE}/sessions?status_filter=${statusFilter}`
    : `${API_BASE}/sessions`

  const response = await fetch(url, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取会话列表失败')
  }

  return response.json()
}

/**
 * 获取预沟通对话历史
 */
export const getPreCommunicationMessages = async (
  sessionId: string,
  limit: number = 100
): Promise<AIPreCommunicationMessage[]> => {
  const response = await fetch(
    `${API_BASE}/session/${sessionId}/messages?limit=${limit}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取对话历史失败')
  }

  return response.json()
}

/**
 * 取消预沟通会话
 */
export const cancelPreCommunication = async (
  sessionId: string
): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${API_BASE}/session/${sessionId}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '取消会话失败')
  }

  return response.json()
}

/**
 * 获取推荐开启人工对话的会话列表
 */
export const getRecommendedSessions = async (): Promise<Array<{
  session_id: string
  partner_id: string
  partner_name: string
  compatibility_score: number
  recommendation_reason: string
  completed_at: string
}>> => {
  const response = await fetch(`${API_BASE}/recommendations`, {
    method: 'GET',
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取推荐会话失败')
  }

  return response.json()
}

// ============= 辅助函数 =============

/**
 * 计算匹配度等级
 */
export const getCompatibilityLevel = (score: number): string => {
  if (score >= 90) return '极高'
  if (score >= 80) return '很高'
  if (score >= 70) return '较高'
  if (score >= 60) return '中等'
  return '较低'
}

/**
 * 获取会话状态中文描述
 */
export const getSessionStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    pending: '等待开始',
    analyzing: '分析中',
    chatting: 'AI 对聊中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return texts[status] || status
}

/**
 * 获取推荐类型中文描述
 */
export const getRecommendationText = (recommendation: string): string => {
  const texts: Record<string, string> = {
    recommend: '建议开启对话',
    wait: '继续观察',
    silent: '不建议推送',
  }
  return texts[recommendation] || recommendation
}
