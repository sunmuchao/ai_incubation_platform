/**
 * WebSocket 服务 - 实时通信
 * 替代轮询，提供低延迟双向通信
 */

import type { WebSocketMessage, WebSocketStatus } from '../types'

type MessageHandler = (message: WebSocketMessage) => void

// 开发环境打印详细日志
const log = (...args: unknown[]) => { console.log('[WebSocket]', ...args) }
const error = (...args: unknown[]) => { console.error('[WebSocket]', ...args) }

class WebSocketService {
  private ws: WebSocket | null = null
  private userId: string | null = null
  private customUrl: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private heartbeatInterval: number | null = null
  private messageHandlers: Set<MessageHandler> = new Set()
  private statusHandlers: Set<(status: WebSocketStatus) => void> = new Set()
  private messageQueue: WebSocketMessage[] = []
  private status: WebSocketStatus = {
    connected: false,
    reconnecting: false,
  }

  connect(userId: string, customUrl?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      log('Already connected')
      return
    }

    this.userId = userId
    this.customUrl = customUrl || null
    const wsUrl = customUrl || this.buildDefaultUrl(userId)

    log('=== Connection Start ===')
    log('userId:', userId)
    log('WebSocket URL:', wsUrl)

    try {
      this.ws = new WebSocket(wsUrl)
      log('WebSocket instance created, readyState:', this.ws.readyState)

      this.ws.onopen = () => {
        log('=== Connected ===')
        log('Connection successful for user:', userId)
        this.reconnectAttempts = 0
        this.updateStatus({ connected: true, reconnecting: false })
        this.startHeartbeat()
        this.flushMessageQueue()
      }

      this.ws.onmessage = (event) => {
        log('=== Message Received ===')
        log('Raw data:', event.data)
        try {
          const rawMessage = JSON.parse(event.data)
          // 兼容两种消息格式：
          // 1. { type, payload } - 标准 WebSocketMessage 格式
          // 2. { type, sender_id, content, ... } - 后端直接发送的格式
          const message: WebSocketMessage = rawMessage.payload
            ? rawMessage
            : {
                type: rawMessage.type as WebSocketMessage['type'],
                payload: rawMessage,
                timestamp: rawMessage.timestamp || new Date().toISOString()
              }
          log('Parsed message type:', message.type)
          log('Parsed message payload:', message.payload)
          this.messageHandlers.forEach(handler => handler(message))
        } catch (e) {
          error('Failed to parse message:', e)
        }
      }

      this.ws.onclose = (event) => {
        log('=== Connection Closed ===')
        log('Code:', event.code, 'Reason:', event.reason || 'No reason provided')
        this.updateStatus({ connected: false })
        this.stopHeartbeat()
        this.attemptReconnect()
      }

      this.ws.onerror = (e) => {
        log('=== Connection Error ===')
        error('WebSocket error:', e)
        this.updateStatus({ connected: false, error: '连接失败' })
      }
    } catch (e) {
      error('Failed to create WebSocket connection:', e)
      this.updateStatus({ connected: false, error: '无法创建连接' })
    }
  }

  private buildDefaultUrl(userId: string): string {
    // 使用 Vite WebSocket 代理（配置在 vite.config.ts）
    // 代理配置：/api -> http://localhost:8002, ws: true
    // 通过相对路径让 Vite 代理处理 WebSocket 连接
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 开发和生产环境统一使用同源路径，由 Vite/Nginx 代理转发
    return `${protocol}//${window.location.host}/api/chat/ws/${userId}`
  }

  private attemptReconnect() {
    if (!this.userId) return

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      log('Max reconnect attempts reached')
      this.updateStatus({ connected: false, reconnecting: false })
      return
    }

    this.reconnectAttempts++
    this.updateStatus({ connected: false, reconnecting: true })

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (this.customUrl) {
        this.connect(this.userId!, this.customUrl)
      } else {
        this.connect(this.userId!)
      }
    }, delay)
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, 30000) // 30 秒心跳
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()
      this.ws.send(JSON.stringify(message))
    }
  }

  send(type: string, payload: WebSocketMessage['payload']) {
    const message = { type, payload, timestamp: new Date().toISOString() }

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // 队列缓存，等待连接后发送
      if (this.messageQueue.length < 50) {
        this.messageQueue.push(message)
      }
    }
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onStatusChange(handler: (status: WebSocketStatus) => void) {
    this.statusHandlers.add(handler)
    handler(this.status) // 立即触发一次当前状态
    return () => this.statusHandlers.delete(handler)
  }

  private updateStatus(newStatus: Partial<WebSocketStatus>) {
    this.status = { ...this.status, ...newStatus }
    this.statusHandlers.forEach(handler => handler(this.status))
  }

  disconnect() {
    this.stopHeartbeat()
    this.ws?.close()
    this.ws = null
    this.messageHandlers.clear()
    this.statusHandlers.clear()
    this.messageQueue = []
    this.updateStatus({ connected: false, reconnecting: false })
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// 单例模式
export const websocketService = new WebSocketService()
