/**
 * AI Native 渐进式画像收集页面
 *
 * 设计原则：
 * 1. 对话优先：通过自然对话收集信息，而非表单
 * 2. AI 主动引导：AI 主动发起话题，而非等待用户
 * 3. Generative UI：根据对话内容动态生成交互组件
 * 4. 透明推断：展示 AI 推断结果，用户可验证修改
 * 5. 渐进式完整度：实时显示画像完整度变化
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Card, Button, Typography, Space, Avatar, Tag, Spin, Progress, Tooltip, Modal, Input, message } from 'antd'
import {
  HeartOutlined,
  SendOutlined,
  UserOutlined,
  CheckCircleOutlined,
  EditOutlined,
  GamepadOutlined,
  WechatOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  QuestionCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { authStorage } from '../utils/storage'
import HerAvatar from '../assets/her-avatar.svg'
import './ProgressiveProfilePage.less'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

// ========== 类型定义 ==========

interface ProfileDimension {
  index: number
  name: string
  value: number
  confidence: number
  source: 'registration' | 'chat_inference' | 'game_test' | 'wechat'
  canEdit: boolean
}

interface ProfileStatus {
  completeness_ratio: number
  recommended_strategy: 'cold_start' | 'basic' | 'vector' | 'precise'
  strategy_reason: string
  critical_dimensions_filled: boolean
  missing_critical: string[]
  category_completeness: Record<string, number>
  can_use_precise_match: boolean
  suggested_actions: string[]
}

interface ConversationMessage {
  id: string
  type: 'ai' | 'user' | 'system'
  content: string
  timestamp: Date
  // Generative UI 组件
  ui_component?: {
    type: 'quick_replies' | 'dimension_card' | 'game_invite' | 'wechat_auth' | 'profile_summary'
    data: any
  }
}

interface QuickReply {
  text: string
  value: string
  icon?: string
}

// ========== 主组件 ==========

const ProgressiveProfilePage: React.FC<{
  onComplete?: () => void
}> = ({ onComplete }) => {
  // 状态
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [userInput, setUserInput] = useState('')
  const [currentUser, setCurrentUser] = useState<any>(null)

  // AI Native 核心状态
  const [profileStatus, setProfileStatus] = useState<ProfileStatus | null>(null)
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([])
  const [inferredDimensions, setInferredDimensions] = useState<ProfileDimension[]>([])

  // UI 状态
  const [showDimensionModal, setShowDimensionModal] = useState(false)
  const [editingDimension, setEditingDimension] = useState<ProfileDimension | null>(null)
  const [showGameInvite, setShowGameInvite] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)

  // ========== 初始化 ==========

  useEffect(() => {
    initPage()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [conversationHistory])

  const initPage = async () => {
    try {
      setLoading(true)
      const user = authStorage.getUser()
      if (!user) {
        setLoading(false)
        return
      }
      setCurrentUser(user)

      // 获取画像状态
      const status = await fetchProfileStatus(user.id || user.username)
      setProfileStatus(status)

      // AI 主动发起对话（根据画像状态决定开场白）
      const openingMessage = await generateOpeningMessage(status)
      setConversationHistory([openingMessage])

    } catch (error) {
      console.error('Init page error:', error)
    } finally {
      setLoading(false)
    }
  }

  // ========== AI Native 核心逻辑 ==========

  /**
   * AI 生成开场白
   *
   * 根据画像状态，AI 主动决定如何引导用户
   */
  const generateOpeningMessage = async (status: ProfileStatus): Promise<ConversationMessage> => {
    const userId = currentUser?.id || currentUser?.username || 'anonymous'

    // 调用后端 AI 生成开场白
    try {
      const response = await fetch(`/api/progressive-profile/ai-opening/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_status: status })
      })
      const data = await response.json()

      return {
        id: `msg-${Date.now()}`,
        type: 'ai',
        content: data.message,
        timestamp: new Date(),
        ui_component: data.ui_component
      }
    } catch (error) {
      // 降级：基于规则的开场白
      return generateFallbackOpening(status)
    }
  }

  /**
   * 降级开场白（当 AI 不可用时）
   */
  const generateFallbackOpening = (status: ProfileStatus): ConversationMessage => {
    let content = ''
    let uiComponent: any = undefined

    if (status.completeness_ratio < 0.2) {
      content = `Hi！我是 Her，很高兴认识你~ 让我先了解一下你吧。你最想找什么样的关系呢？`
      uiComponent = {
        type: 'quick_replies',
        data: {
          options: [
            { text: '认真恋爱 💕', value: 'serious' },
            { text: '轻松约会 ☕', value: 'casual' },
            { text: '交朋友 🤝', value: 'friendship' },
            { text: '奔着结婚 💍', value: 'marriage' },
          ]
        }
      }
    } else if (!status.critical_dimensions_filled) {
      content = `我注意到还有一些重要信息需要了解。关于孩子，你是怎么想的呢？`
      uiComponent = {
        type: 'quick_replies',
        data: {
          options: [
            { text: '想要孩子 👶', value: 'want' },
            { text: '不想要 🚫', value: 'not_want' },
            { text: '看情况 🤔', value: 'maybe' },
          ]
        }
      }
    } else if (status.completeness_ratio < 0.5) {
      content = `想更精准地帮你找到合适的人吗？玩个小游戏吧，只需要3分钟~`
      uiComponent = {
        type: 'game_invite',
        data: {
          game_type: 'personality',
          reward: '解锁精准匹配'
        }
      }
    } else {
      content = `我已经了解你不少了！现在可以给你推荐了，或者继续聊聊让我更懂你？`
      uiComponent = {
        type: 'quick_replies',
        data: {
          options: [
            { text: '开始匹配 🎯', value: 'start_match' },
            { text: '继续聊 💬', value: 'continue_chat' },
          ]
        }
      }
    }

    return {
      id: `msg-${Date.now()}`,
      type: 'ai',
      content,
      timestamp: new Date(),
      ui_component: uiComponent
    }
  }

  /**
   * 处理用户输入
   *
   * AI 分析用户回复，推断画像维度
   */
  const handleUserInput = async (input: string) => {
    if (!input.trim() || sending) return

    const userId = currentUser?.id || currentUser?.username
    setSending(true)

    // 添加用户消息
    const userMessage: ConversationMessage = {
      id: `msg-user-${Date.now()}`,
      type: 'user',
      content: input,
      timestamp: new Date()
    }
    setConversationHistory(prev => [...prev, userMessage])

    try {
      // 调用 AI 分析
      const response = await fetch('/api/progressive-profile/ai-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: input,
          conversation_history: conversationHistory.map(m => ({
            role: m.type === 'user' ? 'user' : 'assistant',
            content: m.content
          }))
        })
      })
      const data = await response.json()

      // 更新推断的维度
      if (data.inferred_dimensions) {
        setInferredDimensions(prev => {
          const merged = [...prev]
          for (const dim of data.inferred_dimensions) {
            const existing = merged.find(d => d.index === dim.index)
            if (existing) {
              existing.value = dim.value
              existing.confidence = dim.confidence
              existing.source = dim.source
            } else {
              merged.push(dim)
            }
          }
          return merged
        })
      }

      // 更新画像状态
      if (data.profile_status) {
        setProfileStatus(data.profile_status)
      }

      // 添加 AI 回复
      const aiMessage: ConversationMessage = {
        id: `msg-ai-${Date.now()}`,
        type: 'ai',
        content: data.message,
        timestamp: new Date(),
        ui_component: data.ui_component
      }
      setConversationHistory(prev => [...prev, aiMessage])

    } catch (error) {
      console.error('Chat error:', error)
      // 添加错误提示
      setConversationHistory(prev => [...prev, {
        id: `msg-error-${Date.now()}`,
        type: 'system',
        content: '网络不太稳定，请稍后再试~',
        timestamp: new Date()
      }])
    } finally {
      setSending(false)
      setUserInput('')
    }
  }

  /**
   * 处理快速回复
   */
  const handleQuickReply = (reply: QuickReply) => {
    handleUserInput(reply.value)
  }

  /**
   * 开始游戏测试
   */
  const handleStartGame = async (gameType: string) => {
    const userId = currentUser?.id || currentUser?.username
    try {
      const response = await fetch(`/api/progressive-profile/game-test/start?user_id=${userId}&test_type=${gameType}`, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.success) {
        // 跳转到游戏页面或显示游戏组件
        message.info(`开始${data.data.test_name}！`)
        // 游戏组件渲染（当前为 placeholder，后续可集成 StressTest 等游戏化测试）
      }
    } catch (error) {
      console.error('Start game error:', error)
    }
  }

  /**
   * 微信授权
   */
  const handleWechatAuth = async () => {
    // 微信授权流程（需集成 wechatApi 或调用原生 SDK）
    message.info('正在跳转微信授权...')
  }

  /**
   * 编辑维度值
   */
  const handleEditDimension = (dimension: ProfileDimension) => {
    setEditingDimension(dimension)
    setShowDimensionModal(true)
  }

  /**
   * 保存维度修改
   */
  const handleSaveDimension = async (dimension: ProfileDimension, newValue: number) => {
    const userId = currentUser?.id || currentUser?.username
    try {
      await fetch('/api/progressive-profile/dimension/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          dimension_index: dimension.index,
          value: newValue
        })
      })

      // 更新本地状态
      setInferredDimensions(prev => prev.map(d =>
        d.index === dimension.index ? { ...d, value: newValue } : d
      ))

      message.success('已更新')
      setShowDimensionModal(false)
    } catch (error) {
      message.error('更新失败')
    }
  }

  // ========== 渲染函数 ==========

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * 渲染消息内容
   */
  const renderMessage = (msg: ConversationMessage) => {
    return (
      <div key={msg.id} className={`message-wrapper ${msg.type}`}>
        {msg.type === 'ai' && (
          <Avatar size={36} src={HerAvatar} className="message-avatar" />
        )}
        <div className="message-content">
          <div className="message-bubble">
            <Text>{msg.content}</Text>
          </div>
          {/* Generative UI 组件 */}
          {msg.ui_component && renderUIComponent(msg.ui_component)}
        </div>
        {msg.type === 'user' && (
          <Avatar size={36} icon={<UserOutlined />} className="message-avatar user" />
        )}
      </div>
    )
  }

  /**
   * 渲染 Generative UI 组件
   */
  const renderUIComponent = (component: ConversationMessage['ui_component']) => {
    if (!component) return null

    switch (component.type) {
      case 'quick_replies':
        return (
          <div className="quick-replies">
            <Space wrap>
              {component.data.options.map((option: QuickReply, idx: number) => (
                <Button
                  key={idx}
                  type="default"
                  size="small"
                  onClick={() => handleQuickReply(option)}
                >
                  {option.text}
                </Button>
              ))}
            </Space>
          </div>
        )

      case 'game_invite':
        return (
          <Card size="small" className="game-invite-card">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>🎮 {component.data.game_type === 'personality' ? '恋爱人格测试' : '价值观测试'}</Text>
              <Text type="secondary">只需3分钟，解锁{component.data.reward}</Text>
              <Button type="primary" block onClick={() => handleStartGame(component.data.game_type)}>
                开始测试
              </Button>
            </Space>
          </Card>
        )

      case 'wechat_auth':
        return (
          <Card size="small" className="wechat-auth-card">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <WechatOutlined style={{ color: '#07C160', fontSize: 20 }} />
                <Text strong>微信授权</Text>
              </Space>
              <Text type="secondary">授权微信信息，让我更了解你</Text>
              <Button type="primary" block onClick={handleWechatAuth}>
                授权微信
              </Button>
            </Space>
          </Card>
        )

      case 'dimension_card':
        return (
          <Card size="small" className="dimension-card">
            <Text type="secondary">我了解到：</Text>
            <Space wrap style={{ marginTop: 8 }}>
              {component.data.dimensions.map((dim: any, idx: number) => (
                <Tag key={idx} color="green" icon={<CheckCircleOutlined />}>
                  {dim.name}
                  <Tooltip title="点击修改">
                    <EditOutlined
                      style={{ marginLeft: 4, cursor: 'pointer' }}
                      onClick={() => handleEditDimension(dim)}
                    />
                  </Tooltip>
                </Tag>
              ))}
            </Space>
          </Card>
        )

      default:
        return null
    }
  }

  /**
   * 渲染画像完整度面板
   */
  const renderCompletenessPanel = () => {
    if (!profileStatus) return null

    const { completeness_ratio, recommended_strategy, missing_critical } = profileStatus

    return (
      <div className="completeness-panel">
        <div className="completeness-header">
          <HeartOutlined style={{ color: '#D4A59A' }} />
          <Text type="secondary">Her 的了解</Text>
          <Text strong style={{ marginLeft: 'auto' }}>{Math.round(completeness_ratio * 100)}%</Text>
        </div>

        <Progress
          percent={Math.round(completeness_ratio * 100)}
          showInfo={false}
          strokeColor={{
            '0%': '#D4A59A',
            '50%': '#C88B8B',
            '100%': '#F4E4E1',
          }}
          size="small"
        />

        {/* 推断维度标签 */}
        {inferredDimensions.length > 0 && (
          <div className="inferred-dimensions">
            <Text type="secondary" style={{ fontSize: 12 }}>已了解：</Text>
            <Space wrap size={4}>
              {inferredDimensions.slice(0, 5).map((dim, idx) => (
                <Tag
                  key={idx}
                  color="green"
                  icon={<CheckCircleOutlined />}
                  style={{ fontSize: 11 }}
                >
                  {dim.name}
                </Tag>
              ))}
              {inferredDimensions.length > 5 && (
                <Tag style={{ fontSize: 11 }}>+{inferredDimensions.length - 5}</Tag>
              )}
            </Space>
          </div>
        )}

        {/* 匹配策略指示 */}
        <div className="strategy-indicator">
          <Tooltip title={profileStatus.strategy_reason}>
            <Tag color={
              recommended_strategy === 'precise' ? 'green' :
              recommended_strategy === 'vector' ? 'blue' :
              recommended_strategy === 'basic' ? 'orange' : 'default'
            }>
              {recommended_strategy === 'precise' && '🎯 精准匹配'}
              {recommended_strategy === 'vector' && '📊 向量匹配'}
              {recommended_strategy === 'basic' && '📝 基础匹配'}
              {recommended_strategy === 'cold_start' && '🔍 探索模式'}
            </Tag>
          </Tooltip>
        </div>
      </div>
    )
  }

  /**
   * 渲染快捷入口
   */
  const renderQuickActions = () => {
    if (!profileStatus) return null

    const actions = []

    // 游戏测试入口
    if (profileStatus.completeness_ratio < 0.5) {
      actions.push(
        <Button
          key="game"
          type="dashed"
          icon={<GamepadOutlined />}
          onClick={() => setShowGameInvite(true)}
        >
          人格测试
        </Button>
      )
    }

    // 微信授权入口
    actions.push(
      <Button
        key="wechat"
        type="dashed"
        icon={<WechatOutlined />}
        onClick={handleWechatAuth}
      >
        微信授权
      </Button>
    )

    return (
      <div className="quick-actions">
        <Space>{actions}</Space>
      </div>
    )
  }

  // ========== 主渲染 ==========

  if (loading) {
    return (
      <div className="progressive-profile-page">
        <div className="loading-container">
          <Spin size="large" tip="Her 正在准备..." />
        </div>
      </div>
    )
  }

  return (
    <div className="progressive-profile-page">
      {/* 顶部：画像完整度面板 */}
      {renderCompletenessPanel()}

      {/* 中间：对话区域 */}
      <div className="conversation-area">
        <div className="messages-container">
          {conversationHistory.map(renderMessage)}
          {sending && (
            <div className="message-wrapper ai">
              <Avatar size={36} src={HerAvatar} className="message-avatar" />
              <div className="message-bubble typing">
                <Spin size="small" />
                <Text type="secondary" style={{ marginLeft: 8 }}>思考中...</Text>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 底部：输入区域 */}
      <div className="input-area">
        {renderQuickActions()}
        <div className="input-wrapper">
          <TextArea
            ref={inputRef}
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleUserInput(userInput)
              }
            }}
            placeholder="和我说说..."
            autoSize={{ minRows: 1, maxRows: 3 }}
            disabled={sending}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => handleUserInput(userInput)}
            loading={sending}
          />
        </div>
      </div>

      {/* 维度编辑弹窗 */}
      <Modal
        open={showDimensionModal}
        onCancel={() => setShowDimensionModal(false)}
        title="修改偏好"
        footer={null}
      >
        {editingDimension && (
          <DimensionEditor
            dimension={editingDimension}
            onSave={handleSaveDimension}
            onCancel={() => setShowDimensionModal(false)}
          />
        )}
      </Modal>

      {/* 游戏邀请弹窗 */}
      <Modal
        open={showGameInvite}
        onCancel={() => setShowGameInvite(false)}
        title="🎮 人格测试"
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>通过简单的选择题，让我更精准地了解你的性格特点~</Text>
          <Text type="secondary">只需3分钟，完成后解锁精准匹配功能！</Text>
          <Button type="primary" block onClick={() => handleStartGame('personality')}>
            开始测试
          </Button>
        </Space>
      </Modal>
    </div>
  )
}

// ========== 子组件 ==========

/**
 * 维度编辑器
 */
const DimensionEditor: React.FC<{
  dimension: ProfileDimension
  onSave: (dim: ProfileDimension, value: number) => void
  onCancel: () => void
}> = ({ dimension, onSave, onCancel }) => {
  const [value, setValue] = useState(dimension.value)

  return (
    <div className="dimension-editor">
      <Text strong>{dimension.name}</Text>
      <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
        置信度: {Math.round(dimension.confidence * 100)}%
      </Text>
      <div className="value-slider">
        <Text>低</Text>
        <input
          type="range"
          min="0"
          max="100"
          value={value * 100}
          onChange={(e) => setValue(Number(e.target.value) / 100)}
        />
        <Text>高</Text>
      </div>
      <Space style={{ marginTop: 16 }}>
        <Button onClick={onCancel}>取消</Button>
        <Button type="primary" onClick={() => onSave(dimension, value)}>
          保存
        </Button>
      </Space>
    </div>
  )
}

export default ProgressiveProfilePage