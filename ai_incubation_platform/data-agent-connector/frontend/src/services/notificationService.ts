/**
 * 通知服务 - 主动推送数据变更和血缘关系变更提醒
 */
import { notification as antdNotification } from 'antd'
import {
  BellOutlined,
  DatabaseOutlined,
  LineChartOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import React from 'react'

// 通知类型
export type NotificationType = 'data_change' | 'lineage_change' | 'system' | 'alert' | 'success'

// 通知接口
export interface AppNotification {
  id: string
  type: NotificationType
  title: string
  message: string
  timestamp: Date
  read: boolean
  data?: any
}

// 通知回调
type NotificationCallback = (notification: AppNotification) => void

// 图标组件类型
type IconComponent = React.ReactNode

class NotificationService {
  private notifications: AppNotification[] = []
  private callbacks: NotificationCallback[] = []
  private websocket: WebSocket | null = null
  private connected: boolean = false

  /**
   * 初始化通知服务
   */
  async initialize(websocketUrl?: string): Promise<void> {
    // 从本地存储加载未读通知
    const stored = localStorage.getItem('dac_notifications')
    if (stored) {
      try {
        this.notifications = JSON.parse(stored).map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp),
        }))
      } catch (e) {
        console.error('Failed to load notifications from storage')
      }
    }

    // 连接 WebSocket (如果提供 URL)
    if (websocketUrl) {
      this.connectWebSocket(websocketUrl)
    }

    // 轮询通知 (每 30 秒)
    this.startPolling()
  }

  /**
   * 连接 WebSocket
   */
  private connectWebSocket(url: string): void {
    try {
      this.websocket = new WebSocket(url)

      this.websocket.onopen = () => {
        this.connected = true
        console.log('Notification WebSocket connected')
      }

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleIncomingNotification(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message')
        }
      }

      this.websocket.onclose = () => {
        this.connected = false
        console.log('Notification WebSocket disconnected')
        // 尝试重连
        setTimeout(() => this.connectWebSocket(url), 5000)
      }

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (e) {
      console.error('Failed to connect WebSocket:', e)
    }
  }

  /**
   * 开始轮询通知
   */
  private startPolling(): void {
    setInterval(async () => {
      if (!this.connected) {
        // TODO: 从 API 获取新通知
        // await this.fetchNotifications()
      }
    }, 30000)
  }

  /**
   * 处理接收到的通知
   */
  private handleIncomingNotification(data: any): void {
    const notif: AppNotification = {
      id: data.id || `notif-${Date.now()}`,
      type: data.type || 'system',
      title: data.title,
      message: data.message,
      timestamp: new Date(),
      read: false,
      data: data.data,
    }

    this.addNotification(notif)
  }

  /**
   * 添加通知
   */
  addNotification(notification: AppNotification): void {
    this.notifications.unshift(notification)

    // 限制存储数量
    if (this.notifications.length > 50) {
      this.notifications = this.notifications.slice(0, 50)
    }

    // 保存到本地存储
    this.saveToStorage()

    // 触发回调
    this.callbacks.forEach(callback => callback(notification))

    // 显示系统通知
    this.showSystemNotification(notification)
  }

  /**
   * 获取图标
   */
  private getIcon(type: NotificationType): IconComponent {
    const icons: Record<NotificationType, IconComponent> = {
      data_change: React.createElement(DatabaseOutlined, { className: 'text-blue-500' }),
      lineage_change: React.createElement(LineChartOutlined, { className: 'text-purple-500' }),
      system: React.createElement(BellOutlined, { className: 'text-gray-500' }),
      alert: React.createElement(WarningOutlined, { className: 'text-red-500' }),
      success: React.createElement(CheckCircleOutlined, { className: 'text-green-500' }),
    }
    return icons[type]
  }

  /**
   * 获取通知类型
   */
  private getNotificationType(type: NotificationType): 'success' | 'info' | 'warning' | 'error' {
    const typeMap: Record<NotificationType, 'success' | 'info' | 'warning' | 'error'> = {
      data_change: 'info',
      lineage_change: 'info',
      system: 'info',
      alert: 'warning',
      success: 'success',
    }
    return typeMap[type]
  }

  /**
   * 显示系统通知
   */
  private showSystemNotification(notif: AppNotification): void {
    antdNotification.open({
      message: notif.title,
      description: notif.message,
      icon: this.getIcon(notif.type),
      type: this.getNotificationType(notif.type),
      duration: 5,
    })
  }

  /**
   * 保存到本地存储
   */
  private saveToStorage(): void {
    try {
      localStorage.setItem('dac_notifications', JSON.stringify(this.notifications))
    } catch (e) {
      console.error('Failed to save notifications to storage')
    }
  }

  /**
   * 获取所有通知
   */
  getNotifications(): AppNotification[] {
    return this.notifications
  }

  /**
   * 获取未读通知
   */
  getUnreadNotifications(): AppNotification[] {
    return this.notifications.filter(n => !n.read)
  }

  /**
   * 标记通知为已读
   */
  markAsRead(id: string): void {
    const notification = this.notifications.find(n => n.id === id)
    if (notification) {
      notification.read = true
      this.saveToStorage()
    }
  }

  /**
   * 标记所有通知为已读
   */
  markAllAsRead(): void {
    this.notifications.forEach(n => n.read = true)
    this.saveToStorage()
  }

  /**
   * 清除通知
   */
  clearNotifications(): void {
    this.notifications = []
    this.saveToStorage()
  }

  /**
   * 注册通知回调
   */
  onNotification(callback: NotificationCallback): void {
    this.callbacks.push(callback)
  }

  /**
   * 移除通知回调
   */
  offNotification(callback: NotificationCallback): void {
    const index = this.callbacks.indexOf(callback)
    if (index > -1) {
      this.callbacks.splice(index, 1)
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.websocket) {
      this.websocket.close()
      this.websocket = null
    }
    this.connected = false
  }
}

// 导出单例
export const notificationService = new NotificationService()
