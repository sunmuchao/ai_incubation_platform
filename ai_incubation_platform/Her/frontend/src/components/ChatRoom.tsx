/**
 * 聊天室组件 - 真实的两人聊天界面
 *
 * 功能:
 * - 发送/接收消息
 * - 消息历史记录
 * - 已读/未读状态
 */

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Input, Button, Avatar, Typography, Space, Empty, Tooltip, message, Tag } from 'antd'
import { SendOutlined, LeftOutlined, PictureOutlined, SmileOutlined, MoreOutlined, RobotOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { chatApi } from '../api'
import { chatAssistantSkill } from '../api/skillClient'
import { websocketService } from '../services/websocket'
import GenerativeUIRenderer from './GenerativeUI'
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
  const [showAiSuggestions, setShowAiSuggestions] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<Array<{ id: string; style: string; content: string }>>([])
  const [isGeneratingSuggestion, setIsGeneratingSuggestion] = useState(false)
  const [aiSuggestionUi, setAiSuggestionUi] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)

  // 获取当前用户 ID
  const currentUserId = useMemo(() => {
    const userInfoStr = localStorage.getItem('user_info')
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr)
        return userInfo.id || userInfo.username
      } catch {
        return 'user-anonymous-dev'
      }
    }
    return 'user-anonymous-dev'
  }, [])

  // 连接 WebSocket 接收实时消息
  useEffect(() => {
    if (!currentUserId) {
      console.log('[ChatRoom] Skip WebSocket connection - no currentUserId')
      return
    }

    console.log('[ChatRoom] === useEffect Start ===')
    console.log('[ChatRoom] currentUserId:', currentUserId)
    console.log('[ChatRoom] actualPartnerId:', actualPartnerId)

    // 连接 WebSocket - 使用路径参数方式，与后端 /api/chat/ws/{user_id} 匹配
    websocketService.connect(currentUserId)

    console.log('[ChatRoom] WebSocket connection initiated')

    // 订阅新消息
    const unsubscribe = websocketService.onMessage((message) => {
      console.log('[ChatRoom] === onMessage Callback ===')
      console.log('[ChatRoom] message.type:', message.type)
      console.log('[ChatRoom] message.payload:', message.payload)

      if (message.type === 'new_message' && message.payload) {
        const payload = message.payload as any
        console.log('[ChatRoom] payload.sender_id:', payload.sender_id)
        console.log('[ChatRoom] actualPartnerId:', actualPartnerId)
        console.log('[ChatRoom] sender matches partner:', payload.sender_id === actualPartnerId)

        // 只添加来自当前聊天对象的消息
        if (payload.sender_id === actualPartnerId) {
          console.log('[ChatRoom] Adding message to state')
          setMessages(prev => {
            // 避免重复添加
            const exists = prev.some(m => m.id === payload.id)
            console.log('[ChatRoom] Message exists:', exists)
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
            console.log('[ChatRoom] New message created:', newMessage.id)
            return [...prev, newMessage]
          })
        } else {
          console.log('[ChatRoom] Skipping message - sender_id does not match actualPartnerId')
        }
      }
    })

    console.log('[ChatRoom] Message subscription registered')

    return () => {
      console.log('[ChatRoom] Cleanup - unsubscribing from messages')
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
    let timeoutId: ReturnType<typeof setTimeout> | null = null
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

  // 发送消息 - 使用 chatAssistant Skill
  const handleSend = useCallback(async () => {
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
      // 使用 chatAssistant Skill 发送消息（AI Native 方式）
      const result = await chatAssistantSkill.sendMessage(
        currentUserId,
        actualPartnerId,
        messageContent,
        'text'
      )

      // 更新为实际的消息 ID 和 Generative UI
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id
          ? { ...msg, id: result.chat_data?.message_id || msg.id }
          : msg
      ))

      // 如果有 AI 生成的 UI，显示出来
      if (result.generative_ui) {
        setAiSuggestionUi(result.generative_ui)
      }

      // 发送成功后，轮询获取对方回复（最多轮询 5 次，每次间隔 1 秒）
      console.log('[ChatRoom] Starting reply polling...')
      for (let i = 0; i < 5; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        try {
          const history = await chatApi.getHistory(actualPartnerId)
          const latestMessage = history[history.length - 1]
          if (latestMessage && latestMessage.sender_id === actualPartnerId) {
            console.log('[ChatRoom] Reply received via polling:', latestMessage.content)
            setMessages(prev => {
              const exists = prev.some(m => m.id === latestMessage.id)
              if (exists) return prev
              return [...prev, {
                id: latestMessage.id,
                sender_id: latestMessage.sender_id,
                receiver_id: latestMessage.receiver_id,
                message_type: latestMessage.message_type || 'text',
                content: latestMessage.content,
                is_read: latestMessage.is_read,
                created_at: latestMessage.created_at,
                status: 'delivered'
              }]
            })
            break
          }
        } catch (e) {
          console.warn('[ChatRoom] Polling failed:', e)
        }
      }

    } catch (error) {
      // 标记发送失败
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id ? { ...msg, status: 'failed' } : msg
      ))
      message.error('发送失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }, [inputValue, isLoading, actualPartnerId, currentUserId, setMessages, setInputValue, setIsLoading, setAiSuggestionUi])

  // 模拟对方回复 (开发环境)
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 处理输入状态
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  // 生成 AI 回复建议 - 使用 chatAssistant Skill
  const handleGenerateAiSuggestion = useCallback(async () => {
    if (messages.length === 0) return

    const lastMessage = messages[messages.length - 1]

    // 只有当最后一条是对方发的消息时才生成建议
    if (lastMessage.sender_id === currentUserId) {
      message.info('等待对方回复再生成建议吧~')
      return
    }

    setIsGeneratingSuggestion(true)
    setShowAiSuggestions(true)

    try {
      // 使用 chatAssistant Skill 获取聊天建议
      const result = await chatAssistantSkill.getSuggestions(currentUserId, actualPartnerId)

      // 从 Skill 响应中提取建议
      const suggestions = result.chat_data?.suggestions?.map((s: any, index: number) => ({
        id: `suggestion-${index}`,
        style: s.type === 'icebreaker' ? '破冰' : '话题',
        content: s.content || ''
      })) || []

      setAiSuggestions(suggestions)

      // 如果有 Generative UI，也渲染出来
      if (result.generative_ui) {
        setAiSuggestionUi(result.generative_ui)
      }

      if (suggestions.length === 0) {
        message.warning('AI 暂时没想到好的回复，换个方式试试？')
      }
    } catch (error) {
      console.error('AI 建议生成失败:', error)
      message.error(error instanceof Error ? error.message : 'AI 思考失败，请稍后再试')
    } finally {
      setIsGeneratingSuggestion(false)
    }
  }, [messages, currentUserId, actualPartnerId])

  // 记录 AI 建议反馈
  const recordAiFeedback = useCallback(async (
    suggestionId: string,
    feedbackType: string,
    suggestionContent: string,
    suggestionStyle: string,
    userActualReply?: string
  ) => {
    try {
      await fetch('/api/quick_chat/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          partnerId: actualPartnerId,
          suggestionId,
          feedbackType,
          suggestionContent,
          suggestionStyle,
          userActualReply: userActualReply || null,
        }),
      })
      console.log('[ChatRoom] Feedback recorded:', { suggestionId, feedbackType })
    } catch (error) {
      console.error('[ChatRoom] Record feedback failed:', error)
      // 不阻断用户操作，静默失败
    }
  }, [actualPartnerId])

  // 选择 AI 建议并发送
  const handleSelectAiSuggestion = useCallback(async (suggestion: { id: string; style: string; content: string }) => {
    const content = suggestion.content || ''

    // 记录反馈 - 采纳建议
    recordAiFeedback(
      suggestion.id,
      'adopted',
      content,
      suggestion.style,
      content
    )

    setInputValue(content)
    setShowAiSuggestions(false)
    setAiSuggestions([])

    // 延迟一点发送，让用户看到输入框内容变化
    setTimeout(() => {
      handleSend()
    }, 100)
  }, [recordAiFeedback, handleSend])

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

      {/* AI 回复建议面板 */}
      {showAiSuggestions && aiSuggestions.length > 0 && (
        <div className="ai-suggestion-panel">
          <div className="ai-suggestion-header">
            <RobotOutlined /> <Text strong>AI 建议回复</Text>
            <Button
              type="text"
              size="small"
              onClick={() => setShowAiSuggestions(false)}
            >
              收起
            </Button>
          </div>
          {aiSuggestions.map((suggestion: { id: string; style: string; content: string }, index: number) => (
            <Button
              key={index}
              className="suggestion-item"
              onClick={() => handleSelectAiSuggestion(suggestion)}
              block
            >
              <div className="suggestion-content">
                <Tag color="blue" className="suggestion-style">{suggestion.style}</Tag>
                <Text>{suggestion.content}</Text>
              </div>
            </Button>
          ))}
          <Button
            size="small"
            className="regenerate-btn"
            onClick={handleGenerateAiSuggestion}
            loading={isGeneratingSuggestion}
          >
            换一批
          </Button>
        </div>
      )}

      {/* Generative UI 渲染区域 - AI Native 动态生成的界面 */}
      {aiSuggestionUi && (
        <div className="generative-ui-section">
          <GenerativeUIRenderer
            uiConfig={aiSuggestionUi}
            onAction={(action) => {
              message.info(`AI 操作：${action.type}`)
              // 处理 AI 建议的操作
              if (action.type === 'send_message') {
                handleGenerateAiSuggestion()
              } else if (action.type === 'use_suggestion') {
                // 使用建议
              }
            }}
          />
        </div>
      )}

      {/* 输入区域 */}
      <div className="chat-room-input-area">
        {/* AI 帮我回按钮 */}
        {messages.length > 0 && messages[messages.length - 1].sender_id !== currentUserId && (
          <div className="ai-suggestion-trigger">
            <Button
              size="small"
              icon={<RobotOutlined />}
              onClick={handleGenerateAiSuggestion}
              loading={isGeneratingSuggestion}
              type="primary"
              ghost
            >
              AI 帮我回
            </Button>
          </div>
        )}

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
            onKeyDown={handleKeyPress}
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
