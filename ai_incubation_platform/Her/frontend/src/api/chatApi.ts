/**
 * 聊天 API 服务
 * 包含：聊天核心功能 + 快聊 + 对话分析（合并后）
 */

import { apiClient } from './apiClient'

// ==================== 聊天核心 API ====================

export const chatApi = {
  /**
   * 获取会话列表
   */
  async getConversations() {
    const response = await apiClient.get('/api/chat/conversations')
    return response.data
  },

  /**
   * 获取聊天历史
   */
  async getHistory(otherUserId: string, limit = 50, offset = 0) {
    const response = await apiClient.get(`/api/chat/history/${otherUserId}`, {
      params: { limit, offset },
    })
    return response.data
  },

  /**
   * 发送消息
   */
  async sendMessage(data: { receiver_id: string; content: string; message_type?: string }) {
    const response = await apiClient.post('/api/chat/send', data)
    return response.data
  },

  /**
   * 模拟回复 (开发环境)
   */
  async simulateReply(conversationId: string, userMessage: string) {
    const response = await apiClient.post('/api/chat/simulate-reply', {}, {
      params: {
        conversation_id: conversationId,
        user_message: userMessage,
      },
    })
    return response.data
  },

  /**
   * 标记消息已读
   */
  async markMessageRead(messageId: string) {
    const response = await apiClient.post(`/api/chat/read/message/${messageId}`)
    return response.data
  },

  /**
   * 标记整个会话已读
   */
  async markConversationRead(partnerId: string) {
    const response = await apiClient.post('/api/chat/read/conversation', {
      partner_id: partnerId,
    })
    return response.data
  },
}

// ==================== 快聊 API（合并自 quick_chat）====================

export const quickChatApi = {
  /**
   * 快速提问
   */
  async quickAsk(
    question: string,
    context?: Record<string, any>
  ): Promise<{ success: boolean; answer: string }> {
    const response = await apiClient.post('/api/chat/quick-ask', {
      question,
      context,
    })
    return response.data
  },

  /**
   * 智能回复建议
   */
  async suggestReply(
    conversation_id: string,
    last_message: string,
    tone?: 'casual' | 'formal' | 'romantic' | 'humorous'
  ): Promise<{ success: boolean; suggestions: string[] }> {
    const response = await apiClient.post('/api/chat/suggest-reply', {
      conversation_id,
      last_message,
      tone,
    })
    return response.data
  },

  /**
   * 反馈回复建议
   */
  async feedbackSuggestion(
    suggestion_id: string,
    feedback: 'good' | 'neutral' | 'bad'
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post('/api/chat/suggestion-feedback', {
      suggestion_id,
      feedback,
    })
    return response.data
  },

  /**
   * 获取快速标签
   */
  async getQuickTags(
    user_id: string
  ): Promise<{ success: boolean; tags: string[] }> {
    const response = await apiClient.get(`/api/chat/quick-tags/${user_id}`)
    return response.data
  },
}

// ==================== 对话分析 API（合并自 conversations）====================

export const conversationAnalysisApi = {
  /**
   * 分析消息
   */
  async analyzeMessage(
    message_id: string,
    analysis_type: 'sentiment' | 'intent' | 'topic' = 'sentiment'
  ): Promise<{ success: boolean; analysis: any }> {
    const response = await apiClient.get(`/api/chat/analyze-message/${message_id}`, {
      params: { analysis_type },
    })
    return response.data
  },

  /**
   * 保存对话并分析
   */
  async saveWithAnalysis(
    conversation_id: string,
    messages: any[]
  ): Promise<{ success: boolean; saved: boolean; analysis: any }> {
    const response = await apiClient.post('/api/chat/save-with-analysis', {
      conversation_id,
      messages,
    })
    return response.data
  },

  /**
   * 获取话题画像
   */
  async getTopicProfile(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; profile: any }> {
    const response = await apiClient.get(`/api/chat/topic-profile/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 获取画像建议
   */
  async getProfileSuggestions(
    user_id: string
  ): Promise<{ success: boolean; suggestions: any[] }> {
    const response = await apiClient.get(`/api/chat/profile-suggestions/${user_id}`)
    return response.data
  },
}