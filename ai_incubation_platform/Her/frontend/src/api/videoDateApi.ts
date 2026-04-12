/**
 * 视频约会 API 服务
 * 包含：视频通话 + WebSocket（合并后）
 */

import { apiClient } from './apiClient'

// ==================== 视频通话 API ====================

export const videoDateApi = {
  /**
   * 创建通话
   */
  async createCall(
    caller_id: string,
    receiver_id: string,
    call_type: 'video' | 'audio' = 'video'
  ): Promise<{ success: boolean; call_id: string }> {
    const response = await apiClient.post('/api/video-date/call/create', {
      caller_id,
      receiver_id,
      call_type,
    })
    return response.data
  },

  /**
   * 接受通话
   */
  async acceptCall(call_id: string): Promise<{ success: boolean }> {
    const response = await apiClient.post(`/api/video-date/call/${call_id}/accept`)
    return response.data
  },

  /**
   * 拒绝通话
   */
  async rejectCall(call_id: string, reason?: string): Promise<{ success: boolean }> {
    const response = await apiClient.post(`/api/video-date/call/${call_id}/reject`, {
      reason,
    })
    return response.data
  },

  /**
   * 结束通话
   */
  async endCall(call_id: string): Promise<{ success: boolean; duration?: number }> {
    const response = await apiClient.post(`/api/video-date/call/${call_id}/end`)
    return response.data
  },

  /**
   * 获取通话历史
   */
  async getCallHistory(
    user_id: string,
    limit = 20
  ): Promise<{ success: boolean; calls: any[] }> {
    const response = await apiClient.get(`/api/video-date/call/history/${user_id}`, {
      params: { limit },
    })
    return response.data
  },

  /**
   * 获取活跃通话
   */
  async getActiveCalls(user_id: string): Promise<{ success: boolean; calls: any[] }> {
    const response = await apiClient.get(`/api/video-date/call/active/${user_id}`)
    return response.data
  },

  /**
   * 获取通话统计
   */
  async getCallStats(user_id: string): Promise<{ success: boolean; stats: any }> {
    const response = await apiClient.get(`/api/video-date/call/stats/${user_id}`)
    return response.data
  },
}

// ==================== WebSocket 连接 ====================

export const videoDateWebSocket = {
  /**
   * 获取 WebSocket URL
   */
  getWebSocketUrl(user_id: string): string {
    const baseUrl = apiClient.defaults.baseURL || ''
    const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws'
    const wsHost = baseUrl.replace(/^https?:\/\//, '')
    return `${wsProtocol}://${wsHost}/api/video-date/ws/${user_id}`
  },

  /**
   * 创建 WebSocket 连接
   */
  createConnection(
    user_id: string,
    onMessage: (data: any) => void,
    onError?: (error: Event) => void,
    onClose?: (event: CloseEvent) => void
  ): WebSocket {
    const url = this.getWebSocketUrl(user_id)
    const ws = new WebSocket(url)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    if (onError) {
      ws.onerror = onError
    }

    if (onClose) {
      ws.onclose = onClose
    }

    return ws
  },
}