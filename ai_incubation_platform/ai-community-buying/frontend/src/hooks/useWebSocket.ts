import { useEffect, useRef, useCallback } from 'react'
import { useNotificationStore } from '@/stores'
import type { WebSocketMessage } from '@/types'

interface UseWebSocketOptions {
  url?: string
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `ws://localhost:8005/ws`,
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const addNotification = useNotificationStore((state) => state.addNotification)

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket(url)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        reconnectAttemptsRef.current = 0
        onConnect?.()
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          switch (message.type) {
            case 'notification':
              addNotification({
                id: Date.now(),
                userId: '',
                type: 'system',
                title: message.data.title || '新通知',
                content: message.data.content || '',
                isRead: false,
                createdAt: message.timestamp,
              })
              break
            case 'order_update':
              addNotification({
                id: Date.now(),
                userId: '',
                type: 'order',
                title: '订单状态更新',
                content: `订单 ${message.data.orderNo} 状态已更新为 ${message.data.status}`,
                isRead: false,
                createdAt: message.timestamp,
              })
              break
            case 'group_update':
              addNotification({
                id: Date.now(),
                userId: '',
                type: 'group',
                title: '团购状态更新',
                content: `团购 #${message.data.groupId} 状态已更新为 ${message.data.status}`,
                isRead: false,
                createdAt: message.timestamp,
              })
              break
            case 'price_update':
              addNotification({
                id: Date.now(),
                userId: '',
                type: 'promotion',
                title: '价格更新',
                content: `商品 ${message.data.productName} 价格已调整为 ¥${message.data.newPrice}`,
                isRead: false,
                createdAt: message.timestamp,
              })
              break
            default:
              console.log('Unknown message type:', message.type)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        onDisconnect?.()

        // 尝试重连
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          console.log(`Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval)
        } else {
          console.log('Max reconnect attempts reached')
        }
      }
    } catch (e) {
      console.error('Failed to create WebSocket connection:', e)
    }
  }, [url, onConnect, onDisconnect, onError, maxReconnectAttempts, reconnectInterval, addNotification])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    connect,
    disconnect,
    sendMessage,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  }
}
