/**
 * Your Turn API 客户端
 */

import apiClient from './apiClient'
import { devStorage } from '../utils/storage'

export interface PendingReminder {
  conversation_id: string
  partner_id: string
  partner_name?: string
  last_message_content: string
  last_message_time: string
  hours_waiting: number
  is_your_turn: boolean
}

export interface ReminderStats {
  pending_count: number
  total_waiting_hours: number
  oldest_waiting_hours: number
}

export const yourTurnApi = {
  /**
   * 获取待处理提醒列表
   */
  async getPendingReminders(userId: string): Promise<PendingReminder[]> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/your-turn/pending/${testUserId}`)
    return response.data
  },

  /**
   * 获取提醒统计
   */
  async getReminderStats(userId: string): Promise<ReminderStats> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/your-turn/stats/${testUserId}`)
    return response.data
  },

  /**
   * 标记提醒已显示
   */
  async markReminderShown(userId: string, conversationId: string): Promise<void> {
    const testUserId = devStorage.getTestUserId() || userId
    await apiClient.post(`/api/your-turn/shown?user_id=${testUserId}&conversation_id=${conversationId}`)
  },

  /**
   * 忽略提醒
   */
  async dismissReminder(userId: string, conversationId: string): Promise<void> {
    const testUserId = devStorage.getTestUserId() || userId
    await apiClient.post(`/api/your-turn/dismiss?user_id=${testUserId}`, {
      conversation_id: conversationId
    })
  },

  /**
   * 判断是否应该显示提醒
   */
  async shouldShowReminder(userId: string, conversationId: string): Promise<{
    should_show: boolean
    reminder: PendingReminder | null
  }> {
    const testUserId = devStorage.getTestUserId() || userId
    const response = await apiClient.get(`/api/your-turn/should-show/${testUserId}/${conversationId}`)
    return response.data
  }
}