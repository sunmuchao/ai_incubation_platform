/**
 * 聊天室组件 - 真实的两人聊天界面
 *
 * 功能:
 * - 发送/接收消息
 * - 消息历史记录
 * - 已读/未读状态
 */

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Input, Button, Avatar, Typography, Space, Empty, Tooltip } from 'antd'
import { SendOutlined, LeftOutlined, PictureOutlined, SmileOutlined, MoreOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { chatApi } from '../api'
import { websocketService } from '../services/websocket'
import './ChatRoom.less'

const { Text } = Typography

interface Message {
  id: string
  sender_id: string
  receiver_id: string
  message_type: 'text' | 'image' | 'emoji' | 'voice' | 'system'
  content: string
  is_read: boolean
  created_at: string
  status?: 'sent' | 'delivered' | 'read' | 'failed'
}

interface ChatRoomProps {
  match?: MatchCandidate | null
  partnerId?: string
  partnerName?: string
  partnerAvatar?: string
  onBack?: () => void
}

const ChatRoom: React.FC<ChatRoomProps> = ({
  match,
  partnerId,
  partnerName,
  partnerAvatar,
  onBack
}) => {
  // 从 match 对象获取对方信息
  const actualPartnerId = partnerId || match?.user?.id
  const actualPartnerName = partnerName || match?.user?.name || 'TA'
  const actualPartnerAvatar = partnerAvatar || match?.user?.avatar || match?.user?.avatar_url

  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [isPartnerOnline, setIsPartnerOnline] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const currentUserId = localStorage.getItem('user_info')
    ? JSON.parse(localStorage.getItem('user_info') || '{}')?.username
    : 'user-anonymous-dev'

  // 连接 WebSocket 接收实时消息
  useEffect(() => {
    if (!currentUserId) return

    // 连接 WebSocket
    websocketService.connect(currentUserId)

    // 订阅新消息
    const unsubscribe = websocketService.onMessage((message) => {
      if (message.type === 'new_message' && message.payload) {
        const payload = message.payload as any
        // 只添加来自当前聊天对象的消息
        if (payload.sender_id === actualPartnerId) {
          setMessages(prev => {
            // 避免重复添加
            const exists = prev.some(m => m.id === payload.id)
            if (exists) return prev
            // 转换后端消息格式为前端 Message 类型
            const newMessage: Message = {
              id: payload.id || `ws-${Date.now()}`,
              sender_id: payload.sender_id,
              receiver_id: payload.receiver_id || actualPartnerId,
              message_type: payload.message_type || 'text',
              content: payload.content,
              is_read: payload.is_read || false,
              created_at: payload.created_at || payload.timestamp || new Date().toISOString(),
              status: 'delivered'
            }
            return [...prev, newMessage]
          })
        }
      }
    })

    return () => {
      unsubscribe()
    }
  }, [currentUserId, actualPartnerId])

  // 滚动到底部 - 优化性能
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  // 使用防抖的滚动策略
  const scrollToBottomDebounced = useMemo(() => {
    let timeoutId: NodeJS.Timeout | null = null
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(() => {
        scrollToBottom()
        timeoutId = null
      }, 50)
    }
  }, [])

  useEffect(() => {
    scrollToBottomDebounced()
  }, [messages])

  // 加载历史消息
  useEffect(() => {
    if (actualPartnerId) {
      loadHistoryMessages()
    }
  }, [actualPartnerId])

  const loadHistoryMessages = async () => {
    if (!actualPartnerId) return

    try {
      // 使用新的 REST API 加载消息历史
      const history = await chatApi.getHistory(actualPartnerId)

      if (Array.isArray(history)) {
        setMessages(history.map((msg) => ({
          id: msg.id,
          sender_id: msg.sender_id,
          receiver_id: msg.receiver_id,
          message_type: msg.message_type || 'text',
          content: msg.content,
          is_read: msg.is_read,
          created_at: msg.created_at,
          status: msg.status
        })))
      }
    } catch (error) {
      // 加载失败时也继续，可以发送新消息
    }
  }

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading || !actualPartnerId) {
      return
    }

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      sender_id: currentUserId,
      receiver_id: actualPartnerId,
      message_type: 'text',
      content: inputValue,
      is_read: true,
      created_at: new Date().toISOString(),
      status: 'sent'
    }

    // 立即显示消息 (乐观更新)
    setMessages(prev => [...prev, userMessage])
    const messageContent = inputValue
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await chatApi.sendMessage({
        receiver_id: actualPartnerId,
        content: messageContent,
        message_type: 'text'
      })

      // 更新为实际的消息 ID
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id
          ? { ...msg, id: response.id, created_at: response.created_at }
          : msg
      ))

    } catch (error) {
      // 标记发送失败
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id ? { ...msg, status: 'failed' } : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }

  // 模拟对方回复 (开发环境)
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 处理输入状态
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  // 按日期分组消息 - 使用 useMemo 缓存分组结果
  const groupedMessages = useMemo(() => {
    const grouped: { [key: string]: Message[] } = {}

    messages.forEach(msg => {
      const date = new Date(msg.created_at).toLocaleDateString('zh-CN', {
        month: 'long',
        day: 'numeric'
      })

      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(msg)
    })

    return grouped
  }, [messages])

  // 使用 useCallback 缓存渲染函数
  const renderDateSeparator = useCallback((date: string) => {
    return (
      <div key={`sep-${date}`} className="date-separator">
        <Text type="secondary">{date}</Text>
      </div>
    )
  }, [])

  const renderMessageBubble = useCallback((message: Message) => {
    const isMe = message.sender_id === currentUserId
    const timestamp = new Date(message.created_at).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })

    return (
      <div key={message.id} className={`message-item ${isMe ? 'message-me' : 'message-other'}`}>
        {!isMe && (
          <Avatar
            src={actualPartnerAvatar}
            size={36}
            className="message-avatar"
          />
        )}

        <div className="message-content-wrapper">
          <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-other'}`}>
            <Text className="message-text">{message.content}</Text>
          </div>

          <div className="message-meta">
            <Text className="message-time">{timestamp}</Text>
            {isMe && (
              <Text className={`message-status ${message.status}`}>
                {message.status === 'read' && '已读'}
                {message.status === 'delivered' && '已送达'}
                {message.status === 'sent' && '已发送'}
                {message.status === 'failed' && '发送失败'}
              </Text>
            )}
          </div>
        </div>

        {isMe && (
          <Avatar
            size={36}
            className="message-avatar"
            style={{ backgroundColor: '#1890ff' }}
          >
            我
          </Avatar>
        )}
      </div>
    )
  }, [currentUserId, actualPartnerAvatar])

  return (
    <div className="chat-room">
      {/* 顶部导航栏 */}
      <div className="chat-room-header">
        <div className="header-left">
          {onBack && (
            <Button
              type="text"
              icon={<LeftOutlined />}
              onClick={onBack}
              className="back-button"
            />
          )}
          <Avatar src={actualPartnerAvatar} size={40} className="partner-avatar" />
          <div className="partner-info">
            <Text strong className="partner-name">{actualPartnerName}</Text>
          </div>
        </div>

        <div className="header-right">
          <Tooltip title="更多">
            <Button type="text" icon={<MoreOutlined />} />
          </Tooltip>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="chat-room-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <Text type="secondary">
                  还没有消息，发送第一条消息开始聊天吧~
                </Text>
              }
            />
          </div>
        ) : (
          Object.entries(groupedMessages).map(([date, dateMessages]) => (
            <React.Fragment key={date}>
              {renderDateSeparator(date)}
              {dateMessages.map(renderMessageBubble)}
            </React.Fragment>
          ))
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-room-input-area">
        <div className="input-tools">
          <Space>
            <Tooltip title="图片">
              <Button type="text" icon={<PictureOutlined />} />
            </Tooltip>
            <Tooltip title="表情">
              <Button type="text" icon={<SmileOutlined />} />
            </Tooltip>
          </Space>
        </div>

        <div className="input-wrapper">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="输入消息..."
            suffix={
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                size="small"
              />
            }
            size="large"
            className="chat-input"
          />
        </div>
      </div>
    </div>
  )
}

export default ChatRoom
