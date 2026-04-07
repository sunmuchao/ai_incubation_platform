// AI Native Chat 组件 - 对话式交互核心

import React, { useState, useRef, useEffect } from 'react'
import { Input, Button, Card, Avatar, Spin, Tag, Space, Typography, Divider } from 'antd'
import { SendOutlined, UserOutlined, RobotOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ConversationMatchResponse, MatchCandidate } from '../types'
import { conversationMatchingApi } from '../api'
import './ChatInterface.less'

const { Text, Paragraph } = Typography

interface Message {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  matches?: MatchCandidate[]
  suggestions?: string[]
  next_actions?: string[]
  timestamp: Date
}

interface ChatInterfaceProps {
  onMatchSelect?: (match: MatchCandidate) => void
  onViewMatches?: (matches: MatchCandidate[]) => void
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onMatchSelect, onViewMatches }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'ai',
      content:
        '你好！我是你的 AI 红娘助手 🌸\n\n我可以帮你：\n• 寻找理想的另一半\n• 分析你们的匹配度\n• 提供约会建议\n\n告诉我你想要什么样的对象吧~',
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await conversationMatchingApi.match({
        user_intent: inputValue,
      })

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: response.message,
        matches: response.matches,
        suggestions: response.suggestions,
        next_actions: response.next_actions,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: '抱歉，出现了一些问题，请稍后再试~',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickAction = (action: string) => {
    setInputValue(action)
  }

  const renderMessageContent = (message: Message) => {
    if (message.type === 'user') {
      return (
        <div className="user-message">
          <div className="message-bubble user-bubble">
            <Text>{message.content}</Text>
          </div>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
        </div>
      )
    }

    if (message.type === 'system') {
      return (
        <div className="system-message">
          <Text type="secondary">{message.content}</Text>
        </div>
      )
    }

    // AI 消息
    return (
      <div className="ai-message">
        <Avatar
          icon={<RobotOutlined />}
          style={{ backgroundColor: '#722ed1', marginRight: 8 }}
        />
        <div className="message-content">
          <div className="message-bubble ai-bubble">
            <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-line' }}>
              {message.content}
            </Paragraph>
          </div>

          {/* 匹配结果卡片 */}
          {message.matches && message.matches.length > 0 && (
            <div className="match-cards">
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                为你推荐 {message.matches.length} 位匹配对象
              </Text>
              <div className="match-cards-container">
                {message.matches.slice(0, 3).map((match, index) => (
                  <Card
                    key={index}
                    className="match-card"
                    hoverable
                    onClick={() => onMatchSelect?.(match)}
                    size="small"
                  >
                    <div className="match-card-content">
                      <div className="match-avatar">
                        <Avatar size={48} src={match.user.avatar_url} icon={<UserOutlined />} />
                        {match.user.verified && (
                          <Tag color="blue" style={{ position: 'absolute', top: -4, right: -4 }}>
                            ✓
                          </Tag>
                        )}
                      </div>
                      <div className="match-info">
                        <Text strong>{match.user.name}</Text>
                        <Text style={{ fontSize: 12 }}>
                          {match.user.age}岁 · {match.user.location}
                        </Text>
                        <div className="compatibility-score">
                          <Tag color="green">匹配度 {Math.round(match.compatibility_score * 100)}%</Tag>
                        </div>
                      </div>
                    </div>
                    {match.common_interests.length > 0 && (
                      <div className="common-interests">
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          共同兴趣：{match.common_interests.slice(0, 3).join('、')}
                        </Text>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* 建议操作 */}
          {message.next_actions && message.next_actions.length > 0 && (
            <div className="suggestion-chips">
              <Space wrap>
                {message.next_actions.map((action, index) => (
                  <Tag
                    key={index}
                    className="suggestion-chip"
                    onClick={() => handleQuickAction(action)}
                    icon={<ThunderboltOutlined />}
                  >
                    {action}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="chat-interface">
      {/* 消息列表 */}
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className="message-wrapper">
            {renderMessageContent(message)}
          </div>
        ))}
        {isLoading && (
          <div className="loading-indicator">
            <Spin size="small" />
            <Text type="secondary" style={{ marginLeft: 8 }}>
              AI 正在分析你的需求...
            </Text>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="input-area">
        <div className="quick-actions">
          <Tag
            bordered={false}
            onClick={() => handleQuickAction('帮我找对象')}
            className="quick-action-tag"
          >
            找对象
          </Tag>
          <Tag
            bordered={false}
            onClick={() => handleQuickAction('我想找喜欢旅行的女生')}
            className="quick-action-tag"
          >
            爱旅游
          </Tag>
          <Tag
            bordered={false}
            onClick={() => handleQuickAction('看看今天有什么推荐')}
            className="quick-action-tag"
          >
            今日推荐
          </Tag>
        </div>
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="描述你理想的对象..."
          prefix={<RobotOutlined />}
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
        />
      </div>
    </div>
  )
}

export default ChatInterface
