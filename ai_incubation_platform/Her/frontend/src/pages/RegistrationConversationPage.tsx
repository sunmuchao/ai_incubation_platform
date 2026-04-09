/**
 * AI Native 注册对话页面
 *
 * Her 主导对话流程，通过自然对话了解用户
 * 无固定阶段，像朋友一样聊天
 */

import React, { useState, useEffect, useRef } from 'react'
import { Card, Input, Button, Typography, Space, Avatar, Divider, Tag, Spin, Alert, Progress } from 'antd'
import {
  HeartOutlined,
  HeartFilled,
  SendOutlined,
  UserOutlined,
  CheckCircleOutlined,
  FastForwardOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import { registrationConversationApi, userApi } from '../api'
import HerAvatar from '../assets/her-avatar.svg'
import './RegistrationConversationPage.less'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

interface CollectedDimension {
  name: string
  confidence: number
  data: string
}

const RegistrationConversationPage: React.FC<{
  onComplete?: () => void
}> = ({ onComplete }) => {
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [userMessage, setUserMessage] = useState('')
  const [aiMessage, setAiMessage] = useState('')
  const [isCompleted, setIsCompleted] = useState(false)
  const [understandingLevel, setUnderstandingLevel] = useState(0)
  const [collectedDimensions, setCollectedDimensions] = useState<CollectedDimension[]>([])
  const [conversationCount, setConversationCount] = useState(0)
  const [currentUser, setCurrentUser] = useState<any>(null)
  const [conversationHistory, setConversationHistory] = useState<Array<{
    type: 'ai' | 'user'
    message: string
    timestamp: Date
  }>>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    initConversation()
  }, [])

  // 布局诊断日志
  useEffect(() => {
    const checkLayout = () => {
      const card = document.querySelector('.conversation-card') as HTMLElement
      const chatArea = document.querySelector('.chat-scroll-area') as HTMLElement
      const messages = document.querySelector('.messages-wrapper') as HTMLElement
      const input = document.querySelector('.input-section') as HTMLElement

      const cardExceeds = (card?.scrollHeight || 0) > (card?.clientHeight || 0)
      const messagesOverflowing = (messages?.scrollHeight || 0) > (messages?.clientHeight || 0)
      const inputInViewport = (input?.getBoundingClientRect()?.bottom || 0) <= window.innerHeight

      console.log('[Layout Check]', {
        card: { clientHeight: card?.clientHeight, scrollHeight: card?.scrollHeight, exceeds: cardExceeds },
        chatArea: { clientHeight: chatArea?.clientHeight, scrollHeight: chatArea?.scrollHeight },
        messages: { clientHeight: messages?.clientHeight, scrollHeight: messages?.scrollHeight, overflowing: messagesOverflowing },
        input: { inViewport: inputInViewport, top: input?.getBoundingClientRect()?.top },
        viewport: window.innerHeight
      })
    }

    setTimeout(checkLayout, 100)
    setTimeout(checkLayout, 500)
    setTimeout(checkLayout, 1000)
  }, [conversationHistory])

  useEffect(() => {
    console.log('[RegistrationPage] conversationHistory changed, count:', conversationHistory.length)
    scrollToBottom()
  }, [conversationHistory])

  const scrollToBottom = () => {
    // 直接设置 messages-wrapper 的 scrollTop，避免 scrollIntoView 导致父容器滚动
    const messagesWrapper = document.querySelector('.messages-wrapper') as HTMLElement
    if (messagesWrapper) {
      messagesWrapper.scrollTop = messagesWrapper.scrollHeight
    }
  }

  const initConversation = async () => {
    try {
      setLoading(true)
      // 从 localStorage 获取用户信息
      const storedUser = localStorage.getItem('user_info')
      let user = null

      if (storedUser) {
        user = JSON.parse(storedUser)
        setCurrentUser(user)
        console.log('Using user from localStorage:', user)
      }

      if (!user) {
        console.error('No user information available')
        setAiMessage('无法获取用户信息，请重新登录')
        setLoading(false)
        return
      }

      // 开始对话
      const userId = user.id || user.username
      const userName = user.name || user.username || '用户'

      const response = await registrationConversationApi.startConversation(userId, userName)

      setAiMessage(`你好，我是 Her 🤍 让我慢慢了解你吧～`)
      setUnderstandingLevel(response.understanding_level)
      setCollectedDimensions(response.collected_dimensions || [])

      setConversationHistory([
        {
          type: 'ai',
          message: response.ai_message,
          timestamp: new Date(),
        },
      ])
    } catch (error: unknown) {
      console.error('Failed to init conversation:', error)
      const errorMsg = error instanceof Error ? error.message : '初始化对话失败'
      setAiMessage(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!userMessage.trim() || !currentUser) return

    const message = userMessage.trim()
    setUserMessage('')
    setSending(true)

    try {
      // 添加用户消息到历史
      setConversationHistory((prev) => [
        ...prev,
        {
          type: 'user',
          message,
          timestamp: new Date(),
        },
      ])

      // 发送消息到后端
      const userId = currentUser.id || currentUser.username
      const response = await registrationConversationApi.sendMessage(userId, message)

      // 更新状态
      setAiMessage(response.ai_message)
      setIsCompleted(response.is_completed)
      setUnderstandingLevel(response.understanding_level)
      setCollectedDimensions(response.collected_dimensions || [])
      setConversationCount(response.conversation_count)

      // 添加 AI 回复到历史
      setConversationHistory((prev) => [
        ...prev,
        {
          type: 'ai',
          message: response.ai_message,
          timestamp: new Date(),
        },
      ])

      // 如果对话完成，延迟后自动跳转
      if (response.is_completed) {
        setTimeout(() => {
          onComplete?.()
        }, 3000)
      }
    } catch (error: unknown) {
      console.error('Failed to send message:', error)
      const errorMsg = error instanceof Error ? error.message : '抱歉，出现了一些问题，请稍后再试～'
      setAiMessage(errorMsg)
    } finally {
      setSending(false)
    }
  }

  const handleSkip = async () => {
    if (!currentUser) return
    try {
      const userId = currentUser.id || currentUser.username
      await registrationConversationApi.completeConversation(userId)
      onComplete?.()
    } catch (error: unknown) {
      console.error('Failed to skip conversation:', error)
      onComplete?.()
    }
  }

  const renderProgressBar = () => {
    const progress = Math.round(understandingLevel * 100)

    return (
      <div className="progress-section">
        <div className="progress-header">
          <div className="progress-title">
            <HeartOutlined />
            <Text type="secondary">Her 的了解</Text>
          </div>
          <Text strong>{progress}%</Text>
        </div>
        <Progress
          percent={progress}
          showInfo={false}
          strokeColor={{
            '0%': '#D4A59A',
            '50%': '#C88B8B',
            '100%': '#F4E4E1',
          }}
          size="small"
        />
        {collectedDimensions.length > 0 && (
          <div className="collected-dimensions">
            <Text type="secondary" style={{ fontSize: 12 }}>已了解：</Text>
            <Space wrap size="small">
              {collectedDimensions.map((dim, index) => (
                <Tag
                  key={index}
                  color="green"
                  icon={<CheckCircleOutlined />}
                  style={{ fontSize: 11 }}
                >
                  {dim.name}
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="registration-conversation-page">
        <div className="loading-container">
          <Spin size="large" tip="Her 正在准备..." />
          <Text type="secondary" style={{ marginTop: 16 }}>
            让我先了解一下你吧～
          </Text>
        </div>
      </div>
    )
  }

  return (
    <div className="registration-conversation-page">
      <Card className="conversation-card" bordered={false}>
        <div className="card-content-wrapper">
          {/* 顶部固定区域 - 头部和进度条 */}
          <div className="top-section">
            <div className="conversation-header">
              <div className="header-left">
                <Avatar size={32} src={HerAvatar} style={{ backgroundColor: '#fff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>Her</Title>
                </div>
              </div>
              <Button
                type="text"
                icon={<FastForwardOutlined />}
                onClick={handleSkip}
                className="skip-button"
                disabled={isCompleted}
              >
                跳过
              </Button>
            </div>

            {renderProgressBar()}
          </div>

          <Divider className="conversation-divider" />

          {isCompleted ? (
            <div className="completed-view">
              <div className="completed-icon">
                <Avatar size={80} style={{ backgroundColor: '#52c41a' }} icon={<CheckCircleOutlined />} />
              </div>
              <Title level={2} className="completed-title">
                对话完成 🎉
              </Title>
              <Paragraph className="completed-subtitle">
                {aiMessage}
              </Paragraph>

              <div className="summary-card-wrapper">
                <Card className="summary-card" bordered={false} title="Her 已了解的">
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {collectedDimensions.map((dim, index) => (
                      <div key={index} className="dimension-item">
                        <Tag color="blue">{dim.name}</Tag>
                        <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                          {dim.data?.substring(0, 50) || '已记录'}
                          {dim.data && dim.data.length > 50 ? '...' : ''}
                        </Text>
                      </div>
                    ))}
                  </Space>
                </Card>
              </div>

              <Space size="large" className="completed-actions">
                <Button type="default" size="large" onClick={onComplete}>
                  稍后再说
                </Button>
                <Button type="primary" size="large" icon={<HeartOutlined />} onClick={onComplete}>
                  开始探索
                </Button>
              </Space>
            </div>
          ) : (
            <>
              {/* 聊天滚动区域 - 唯一可滚动的部分 */}
              <div className="chat-scroll-area">
                <div className="messages-wrapper">
                  {conversationHistory.map((msg, index) => (
                    <div
                      key={index}
                      className={`message-row ${msg.type === 'user' ? 'user-message' : 'ai-message'}`}
                    >
                      <Avatar
                        className="message-avatar"
                        src={msg.type === 'ai' ? HerAvatar : currentUser?.avatar_url}
                        icon={msg.type === 'ai' ? undefined : <UserOutlined />}
                        style={{
                          backgroundColor: msg.type === 'ai' ? '#fff' : '#C88B8B',
                        }}
                      />
                      <div className={`message-bubble ${msg.type}`}>
                        <Text>{msg.message}</Text>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {sending && (
                  <div className="sending-indicator">
                    <Spin size="small" />
                    <Text type="secondary" style={{ marginLeft: 8 }}>AI 思考中...</Text>
                  </div>
                )}
              </div>

              {/* 底部固定输入区域 */}
              <div className="input-section">
                <Alert
                  message="像和朋友聊天一样，真诚回答就好～"
                  type="info"
                  showIcon
                  style={{ marginBottom: 12, fontSize: 12 }}
                />
                <Space.Compact style={{ width: '100%' }}>
                  <TextArea
                    value={userMessage}
                    onChange={(e) => setUserMessage(e.target.value)}
                    onPressEnter={(e) => {
                      if (!e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder="输入你的回复..."
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    disabled={sending || isCompleted}
                  />
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSendMessage}
                    loading={sending}
                    style={{ width: 80 }}
                    disabled={isCompleted}
                  >
                    发送
                  </Button>
                </Space.Compact>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  )
}

export default RegistrationConversationPage
