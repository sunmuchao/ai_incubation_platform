/**
 * 快速对话面板 - 嵌入悬浮球的迷你对话界面
 *
 * 功能：
 * - 与 Her 快速对话
 * - 支持传入当前聊天上下文，让 Her 理解"她/他"指代的是谁
 */

import React, { useState, useEffect, useRef } from 'react'
import { Input, Button, Avatar, Typography, Empty, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import HerAvatar from '../assets/her-avatar.svg'
import { chatApi } from '../api'
import './QuickChatPanel.less'

const { Text } = Typography

interface Message {
  id: string
  sender_id: string
  receiver_id: string
  content: string
  created_at: string
}

interface ChatContext {
  partnerId: string
  partnerName: string
  recentMessages: Message[] // 最近聊天记录
}

interface QuickChatPanelProps {
  chatContext?: ChatContext | null // 当前聊天上下文（可选）
  onClose?: () => void
}

interface QuickChatResponse {
  answer: string
  suggestions: string[]
  analysis: {
    partnerMood: string
    responseDelay: string
    riskLevel: string
  }
}

const QuickChatPanel: React.FC<QuickChatPanelProps> = ({ chatContext, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [herTyping, setHerTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const currentUserId = localStorage.getItem('user_info')
    ? JSON.parse(localStorage.getItem('user_info') || '{}')?.username
    : 'user-anonymous-dev'

  const herUserId = 'her-ai-assistant'

  // 滚动到底部
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 加载与 Her 的对话历史
  useEffect(() => {
    loadHistoryMessages()
  }, [])

  const loadHistoryMessages = async () => {
    try {
      const history = await chatApi.getHistory(herUserId)
      if (Array.isArray(history)) {
        setMessages(history.slice(-10)) // 只显示最近 10 条
      }
    } catch (error) {
      // 静默失败
    }
  }

  // 发送消息 - 调用真实 AI 接口
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) {
      return
    }

    const question = inputValue
    setInputValue('')
    setIsLoading(true)
    setHerTyping(true)

    // 立即显示用户消息
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      sender_id: currentUserId,
      receiver_id: herUserId,
      content: question,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])

    try {
      // 准备聊天上下文
      const recentMessages = (chatContext?.recentMessages || []).map((msg) => ({
        senderId: msg.sender_id === currentUserId ? 'me' : 'her',
        content: msg.content,
        timestamp: msg.created_at,
      }))

      // 调用快速对话 API
      const response = await fetch('/api/quick_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          question: question,
          partnerId: chatContext?.partnerId || '',
          partnerName: chatContext?.partnerName || 'TA',
          recentMessages: recentMessages,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '请求失败')
      }

      const data: QuickChatResponse = await response.json()

      // 显示 AI 回复
      const aiReply: Message = {
        id: `ai-${Date.now()}`,
        sender_id: herUserId,
        receiver_id: currentUserId,
        content: data.answer + (data.suggestions.length > 0
          ? `\n\n💡 建议：${data.suggestions.join('；')}`
          : ''),
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, aiReply])

    } catch (error) {
      console.error('QuickChat error:', error)
      message.error(error instanceof Error ? error.message : 'AI 思考失败，请稍后再试')

      // 显示错误消息
      const errorReply: Message = {
        id: `error-${Date.now()}`,
        sender_id: herUserId,
        receiver_id: currentUserId,
        content: '抱歉，我刚才走神了，你能再说一遍吗？😊',
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorReply])
    } finally {
      setIsLoading(false)
      setHerTyping(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="quick-chat-panel">
      {/* 消息列表 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                和 Her 说些什么吧~
              </Text>
            }
          />
        ) : (
          messages.map((msg) => {
            const isMe = msg.sender_id === currentUserId
            return (
              <div key={msg.id} className={`message-item ${isMe ? 'message-me' : 'message-other'}`}>
                {!isMe && (
                  <Avatar
                    src={HerAvatar}
                    size={32}
                    className="message-avatar"
                    style={{ backgroundColor: '#fff', padding: 2 }}
                  />
                )}
                <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-other'}`}>
                  <Text className="message-text">{msg.content}</Text>
                </div>
              </div>
            )
          })
        )}
        {herTyping && (
          <div className="message-item message-other">
            <Avatar
              src={HerAvatar}
              size={32}
              className="message-avatar"
              style={{ backgroundColor: '#fff', padding: 2 }}
            />
            <div className="message-bubble bubble-other typing">
              <Text type="secondary">Her 正在输入...</Text>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <Input
          value={inputValue}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder={chatContext ? `问 Her 关于${chatContext.partnerName}的事...` : "跟 Her 说些什么..."}
          suffix={
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              size="small"
            />
          }
          size="small"
          className="chat-input"
        />
      </div>
    </div>
  )
}

export default QuickChatPanel
