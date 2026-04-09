// AI Native Chat 组件 - 对话式交互核心

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Input, Button, Card, Avatar, Spin, Tag, Space, Typography, Divider, Progress, Empty, Timeline } from 'antd'
import { UserOutlined, ThunderboltOutlined, HeartFilled, CheckCircleOutlined, CloseCircleOutlined, MessageOutlined, SendOutlined } from '@ant-design/icons'
import type { MatchCandidate, AIPreCommunicationSession } from '../types'
import { conversationMatchingApi, aiAwarenessApi } from '../api'
import {
  getMyPreCommunicationSessions,
  startPreCommunication,
  getPreCommunicationMessages,
  getCompatibilityLevel,
  getSessionStatusText,
} from '../api/aiInterlocutor'
import HerAvatar from '../assets/her-avatar.svg'
import MatchCard from './MatchCard'
import { FeatureCardRenderer } from './FeatureCards'
import ProfileQuestionCard from './ProfileQuestionCard'
import type { Feature } from './FeaturesDrawer'
import { authStorage } from '../utils/storage'
import profileApi from '../api/profileApi'
import './ChatInterface.less'

const { Text, Paragraph } = Typography

interface QuickTag {
  label: string
  trigger: string
}

interface Message {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  matches?: MatchCandidate[]
  suggestions?: string[]
  next_actions?: string[]
  timestamp: Date
  generativeCard?: 'precommunication' | 'precommunication-dialog' | 'match' | 'analysis' | 'feature' | 'profile_question'  // Generative UI 卡片类型
  generativeData?: unknown  // Generative UI 数据
  featureAction?: string  // 功能卡片类型
}

// 最大消息数量限制，防止内存泄漏
const MAX_MESSAGES = 50

interface ChatInterfaceProps {
  onMatchSelect?: (match: MatchCandidate) => void
  onViewMatches?: (matches: MatchCandidate[]) => void
  onOpenChatRoom?: (partnerId: string, partnerName: string) => void  // 打开聊天室
  initialMatch?: MatchCandidate | null  // 新增：从外部传入的初始匹配对象
  onInitialMatchConsumed?: () => void  // 新增：初始匹配对象被使用后的回调
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  onMatchSelect,
  onViewMatches,
  onOpenChatRoom,  // 新增：打开聊天室回调
  initialMatch,
  onInitialMatchConsumed
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'ai',
      content:
        '你好，我是 Her 🤍\n\n我相信，每个人都有属于自己的那个人。\n\n我可以帮你：\n• 遇见懂你的 TA\n• 读懂你们的关系信号\n• 策划只属于你们的浪漫\n\n和我说说吧，你期待怎样的相遇？',
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [quickTags, setQuickTags] = useState<QuickTag[]>([])  // 动态快捷标签
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 获取动态快捷标签
  useEffect(() => {
    const fetchQuickTags = async () => {
      try {
        const token = authStorage.getToken()
        const response = await fetch('/api/quick_chat/tags', {
          headers: {
            'Authorization': `Bearer ${token || ''}`,
          },
        })
        if (response.ok) {
          const data = await response.json()
          setQuickTags(data.tags || [])
        }
      } catch (error) {
        // 静默失败，使用默认标签
        setQuickTags([
          { label: '今日推荐', trigger: '看看今天有什么推荐' }
        ])
      }
    }
    fetchQuickTags()
  }, [])

  // 组件挂载检查 - 添加清理函数
  useEffect(() => {
    // 检查 chat-interface 是否有异常的 scrollTop
    const checkLayout = () => {
      const chatInterface = document.querySelector('.chat-interface') as HTMLElement
      if (chatInterface && chatInterface.scrollTop > 0) {
        // 静默处理
      }
    }
    const timeoutId = setTimeout(checkLayout, 200)

    // 清理函数
    return () => {
      clearTimeout(timeoutId)
    }
  }, [])

  // 监听功能触发事件
  useEffect(() => {
    const handleFeatureTrigger = (event: CustomEvent<{ feature: Feature }>) => {
      const { feature } = event.detail

      // 添加 AI 消息
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: `好的，我来帮你打开「${feature.name}」~`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, aiMessage])

      // 添加功能卡片
      setTimeout(() => {
        const cardMessage: Message = {
          id: `card-${Date.now()}`,
          type: 'ai',
          content: '',
          timestamp: new Date(),
          generativeCard: 'feature',
          featureAction: feature.action,
        }
        setMessages(prev => [...prev, cardMessage])
      }, 300)
    }

    window.addEventListener('trigger-feature', handleFeatureTrigger as EventListener)

    return () => {
      window.removeEventListener('trigger-feature', handleFeatureTrigger as EventListener)
    }
  }, [])

  // 监听场景推送功能卡片事件
  useEffect(() => {
    const handleFeaturePush = (event: CustomEvent<{
      feature: string
      message: string
      priority: string
    }>) => {
      const { feature, message } = event.detail

      // 添加 AI 消息
      const aiMessage: Message = {
        id: `ai-push-${Date.now()}`,
        type: 'ai',
        content: message,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, aiMessage])

      // 添加功能卡片
      setTimeout(() => {
        const cardMessage: Message = {
          id: `card-push-${Date.now()}`,
          type: 'ai',
          content: '',
          timestamp: new Date(),
          generativeCard: 'feature',
          featureAction: feature,
        }
        setMessages(prev => [...prev, cardMessage])
      }, 300)
    }

    window.addEventListener('push-feature-card', handleFeaturePush as EventListener)

    return () => {
      window.removeEventListener('push-feature-card', handleFeaturePush as EventListener)
    }
  }, [])

  // 处理从外部传入的初始匹配对象
  useEffect(() => {
    if (initialMatch) {
      const matchName = initialMatch.user?.name || 'TA'

      // 添加系统消息，提示用户已选中该匹配
      const systemMessage: Message = {
        id: `system-${Date.now()}`,
        type: 'system',
        content: `你选择了 "${matchName}"，现在可以开始和 TA 聊天了~`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, systemMessage])

      // 添加 AI 助手消息，提供破冰建议
      const aiSuggestionMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: generateIcebreakerSuggestion(initialMatch),
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, aiSuggestionMessage])

      // 通知父组件初始匹配对象已被使用
      onInitialMatchConsumed?.()
    }
  }, [initialMatch?.user?.id])

  // 生成破冰建议消息
  const generateIcebreakerSuggestion = (match: MatchCandidate): string => {
    const userName = match.user?.name || 'TA'
    const interests = match.user?.interests || []
    const bio = match.user?.bio || ''
    const location = match.user?.location || ''

    // 从兴趣生成破冰话题
    const interestTopics: Record<string, string> = {
      '旅行': `你也喜欢旅行吗？去过最难忘的地方是哪里？`,
      '音乐': `你平时喜欢听什么类型的音乐？有推荐吗？`,
      '电影': `最近看了什么好看的电影吗？`,
      '美食': `你是哪里人？有什么家乡美食推荐吗？`,
      '阅读': `最近在读什么书？有推荐的吗？`,
      '健身': `你平时喜欢什么运动？`,
      '摄影': `你喜欢拍什么类型的照片？`,
      '宠物': `你喜欢什么小动物？有养宠物吗？`,
      '游戏': `你平时玩什么游戏？有空可以一起~`,
    }

    let suggestion = `💡 和${userName}的破冰建议：\n\n`

    // 从兴趣中提取话题
    const matchedInterest = interests.find(i => interestTopics[i])
    if (matchedInterest) {
      suggestion += `"${interestTopics[matchedInterest]}"\n\n`
    }

    // 从个人简介中提取话题
    if (bio && bio.length > 10) {
      suggestion += `或者从 TA 的简介入手：\n"${bio.slice(0, 50)}${bio.length > 50 ? '...' : ''}"\n\n`
    }

    // 地区话题
    if (location) {
      suggestion += `也可以聊聊：\n"${location}是个好地方！有什么当地人爱去的地方推荐吗？"\n\n`
    }

    suggestion += `💬 在下方输入框输入你想说的话，开始聊天吧！`

    return suggestion
  }

  const scrollToBottom = useCallback(() => {
    const messagesContainer = document.querySelector('.messages-container') as HTMLElement
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight
    }
  }, [])

  // 滚动到底部 - 添加清理函数防止内存泄漏
  useEffect(() => {
    scrollToBottom()
    return () => {}
  }, [messages, scrollToBottom])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) {
      return
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => {
      const newMessages = [...prev, userMessage]
      // 限制消息数量，移除最旧的消息
      if (newMessages.length > MAX_MESSAGES) {
        return newMessages.slice(newMessages.length - MAX_MESSAGES)
      }
      return newMessages
    })
    const userInput = inputValue
    setInputValue('')
    setIsLoading(true)

    // 追踪聊天消息行为
    const userId = authStorage.getUserId()
    if (userId) {
      aiAwarenessApi.trackChatMessage(userId, 'system', userInput.length).catch(() => {})
    }

    // 1. 检测简单对话（打招呼、感谢等）
    const simpleResponse = getSimpleResponse(userInput)
    if (simpleResponse) {
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: simpleResponse,
        timestamp: new Date(),
      }
      setMessages((prev) => {
        const newMessages = [...prev, aiMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
      setIsLoading(false)
      return
    }

    // 2. 检测特定意图（AI 预沟通、关系分析等）
    const intentResponse = detectUserIntent(userInput)
    if (intentResponse) {
      // 如果有 Generative UI 卡片，不需要再添加消息（loadPreCommunicationSessions 会添加）
      if (intentResponse.generativeCard) {
        return
      }
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: intentResponse.content,
        timestamp: new Date(),
      }
      setMessages((prev) => {
        const newMessages = [...prev, aiMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
      setIsLoading(false)
      return
    }

    // 3. 调用后端 API 处理一般对话
    try {
      const response = await conversationMatchingApi.match({
        user_intent: userInput,
      })

      // 检查是否需要收集用户信息（AI Native 设计）
      if (response.need_profile_collection && response.question_card) {
        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: response.message,
          timestamp: new Date(),
        }
        setMessages((prev) => {
          const newMessages = [...prev, aiMessage]
          if (newMessages.length > MAX_MESSAGES) {
            return newMessages.slice(newMessages.length - MAX_MESSAGES)
          }
          return newMessages
        })

        // 添加问题卡片
        setTimeout(() => {
          const questionMessage: Message = {
            id: `question-${Date.now()}`,
            type: 'ai',
            content: '',
            generativeCard: 'profile_question',
            generativeData: response.question_card,
            timestamp: new Date(),
          }
          setMessages((prev) => [...prev, questionMessage])
        }, 300)

        setIsLoading(false)
        return
      }

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: response.message,
        matches: response.matches,
        suggestions: response.suggestions,
        next_actions: response.next_actions,
        timestamp: new Date(),
      }

      setMessages((prev) => {
        const newMessages = [...prev, aiMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: '抱歉，出现了一些问题，请稍后再试~',
        timestamp: new Date(),
      }
      setMessages((prev) => {
        const newMessages = [...prev, errorMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 检测简单对话并返回回复
  const getSimpleResponse = (input: string): string | null => {
    const inputLower = input.toLowerCase().trim()

    // 打招呼
    if (/^(你好|hi|hello|早上好|中午好|晚上好 | 嗨|哈喽|hey)/.test(inputLower)) {
      return `你好呀 🤍 我是 Her，你的情感伴侣~

我可以帮你：
• 💕 读懂你和 TA 的匹配度
• 💬 给你最懂你的破冰建议
• 🎯 遇见为你挑选的人

说说看，今天想聊什么？`
    }

    // 感谢
    if (/(谢谢|thank|thx)/.test(inputLower)) {
      return `能帮到你，我很开心 🤍`
    }

    // 再见
    if (/(再见|bye|拜拜 | 回见)/.test(inputLower)) {
      return `下次见。愿你可以遇见属于自己的那份懂得 🤍`
    }

    return null
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleQuickAction = (action: string) => {
    // 直接使用 action 填充输入框
    setInputValue(action)
  }

  // 检测用户意图并返回相应回复
  // 注意：这里只处理特殊的本地 UI 交互（如预沟通会话列表）
  // 真正的意图识别交给后端 AI skill 系统处理
  const detectUserIntent = (input: string): { content: string; generativeCard?: Message['generativeCard']; generativeData?: unknown } | null => {
    const inputLower = input.toLowerCase().trim()

    // 预沟通相关 - 启动命令
    if (inputLower.includes('启动') && (inputLower.includes('预沟通') || inputLower.includes('ai 替身'))) {
      // 触发 Generative UI 渲染预沟通会话列表
      loadPreCommunicationSessions()
      return {
        content: `正在为你加载预沟通会话...`,
        generativeCard: 'precommunication',
      }
    }

    // 预沟通相关 - 介绍（不拦截，让后端 AI 回复）
    // 注释掉硬编码回复，改为调用后端 API
    // if (inputLower.includes('预沟通') || inputLower.includes('ai 替身') || inputLower.includes('代聊')) { ... }

    // 关系分析相关（不拦截，让后端 AI 回复）
    // 注释掉硬编码回复，改为调用后端 API
    // if (inputLower.includes('关系') || inputLower.includes('进展') || inputLower.includes('分析')) { ... }

    // 约会建议（不拦截，让后端 AI 回复）
    // 注释掉硬编码回复，改为调用后端 API
    // 这样 AI 可以根据上下文判断用户是要约会建议还是要找对象
    // if (inputLower.includes('约会') || inputLower.includes('去哪里') || inputLower.includes('推荐')) { ... }

    // 没有找到本地特殊意图，返回 null 让后端 AI skill 处理
    return null
  }

  // 加载 AI 预沟通会话列表
  const loadPreCommunicationSessions = async () => {
    try {
      const sessions = await getMyPreCommunicationSessions()

      // 添加 AI 消息，包含 Generative UI 卡片
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: `找到 ${sessions.length} 个 AI 预沟通会话：`,
        generativeCard: 'precommunication',
        generativeData: sessions,
        timestamp: new Date(),
      }
      setMessages(prev => {
        const newMessages = [...prev, aiMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
      setIsLoading(false)
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: '加载预沟通会话失败，请稍后再试~',
        timestamp: new Date(),
      }
      setMessages(prev => {
        const newMessages = [...prev, errorMessage]
        if (newMessages.length > MAX_MESSAGES) {
          return newMessages.slice(newMessages.length - MAX_MESSAGES)
        }
        return newMessages
      })
      setIsLoading(false)
    }
  }

  // 渲染 AI 预沟通会话卡片（Generative UI）
  const renderPreCommunicationSessions = (sessions: unknown) => {
    const typedSessions = sessions as AIPreCommunicationSession[]

    if (!typedSessions || typedSessions.length === 0) {
      return (
        <Card className="generative-card" size="small">
          <Empty description="暂无 AI 预沟通会话" />
        </Card>
      )
    }

    return (
      <div className="generative-card-container">
        <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
          AI 预沟通会话列表
        </Text>
        <div className="generative-cards-grid">
          {sessions.slice(0, 5).map((session, index) => {
            const isCompleted = session.status === 'completed'
            const isRecommended = session.recommendation === 'recommend'
            const progress = (session.conversation_rounds / session.target_rounds) * 100

            return (
              <Card
                key={session.session_id}
                className="generative-card precomm-card"
                size="small"
                hoverable
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {/* 状态标签 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Tag color={getSessionStatusColor(session.status)}>
                      {getSessionStatusText(session.status)}
                    </Tag>
                    {isCompleted && isRecommended && (
                      <Tag color="green">推荐</Tag>
                    )}
                  </div>

                  {/* 进度条 */}
                  {session.status === 'chatting' && (
                    <div>
                      <Progress
                        percent={Math.round(progress)}
                        size="small"
                        strokeColor={{
                          '0%': '#108ee9',
                          '100%': '#87d068',
                        }}
                      />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {session.conversation_rounds}/{session.target_rounds} 轮
                      </Text>
                    </div>
                  )}

                  {/* 硬指标校验 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {session.hard_check_passed ? (
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    )}
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      硬指标{session.hard_check_passed ? '通过' : '未通过'}
                    </Text>
                  </div>

                  {/* 价值观探测 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <HeartOutlined style={{ color: session.values_check_passed ? '#52c41a' : '#ff4d4f' }} />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      价值观{session.values_check_passed ? '通过' : '未通过'}
                    </Text>
                  </div>

                  {/* 匹配度 */}
                  {isCompleted && session.compatibility_score && (
                    <div>
                      <Divider style={{ margin: '4px 0' }} />
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Text strong style={{ fontSize: 18, color: getScoreColor(session.compatibility_score) }}>
                          {Math.round(session.compatibility_score)}%
                        </Text>
                        <Tag color={getScoreColor(session.compatibility_score)}>
                          {getCompatibilityLevel(session.compatibility_score)}
                        </Tag>
                      </div>
                    </div>
                  )}

                  {/* 操作按钮 */}
                  <Space wrap size="small">
                    <Button
                      size="small"
                      icon={<MessageOutlined />}
                      onClick={() => handleViewPreCommunicationMessages(session.session_id)}
                      disabled={session.conversation_rounds === 0}
                    >
                      查看对话
                    </Button>
                    {isCompleted && isRecommended && (
                      <Button
                        type="primary"
                        size="small"
                        icon={<ThunderboltOutlined />}
                        onClick={() => handleStartChatFromSession(session)}
                      >
                        开始聊天
                      </Button>
                    )}
                  </Space>
                </Space>
              </Card>
            )
          })}
        </div>
      </div>
    )
  }

  // 获取状态颜色
  const getSessionStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      pending: 'default',
      analyzing: 'blue',
      chatting: 'green',
      completed: 'purple',
      cancelled: 'red',
    }
    return colors[status] || 'default'
  }

  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'green'
    if (score >= 70) return 'blue'
    if (score >= 60) return 'orange'
    return 'red'
  }

  const getSessionStatusText = (status: string): string => {
    const texts: Record<string, string> = {
      pending: '等待中',
      analyzing: '分析中',
      chatting: '对话中',
      completed: '已完成',
      cancelled: '已取消',
    }
    return texts[status] || status
  }

  const getCompatibilityLevel = (score: number): string => {
    if (score >= 90) return '极匹配'
    if (score >= 85) return '很匹配'
    if (score >= 75) return '较匹配'
    if (score >= 60) return '一般'
    return '待观察'
  }

  // 查看预沟通对话消息
  const handleViewPreCommunicationMessages = async (sessionId: string) => {
    try {
      setIsLoading(true)
      const messages = await getPreCommunicationMessages(sessionId)

      // 添加 AI 消息，包含对话消息列表
      const aiMessage: Message = {
        id: `ai-dialog-${Date.now()}`,
        type: 'ai',
        content: `AI 预沟通对话历史（共 ${messages.length} 条）：`,
        generativeCard: 'precommunication-dialog',
        generativeData: messages,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: '加载对话历史失败，请稍后再试~',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // 从会话开始聊天
  const handleStartChatFromSession = (session: AIPreCommunicationSession) => {
    const userId = authStorage.getUserId()
    const partnerId = session.user_id_1 === userId ? session.user_id_2 : session.user_id_1
    const partnerName = session.user_b_id === userId ? session.user_a_name : session.user_b_name || 'TA'

    // 调用回调打开聊天室
    if (onOpenChatRoom) {
      onOpenChatRoom(partnerId, partnerName)
      return
    }

    // 如果没有回调，显示提示
    const systemMessage: Message = {
      id: `system-${Date.now()}`,
      type: 'system',
      content: `正在连接到 ${partnerName}...`,
      timestamp: new Date(),
      suggestions: ['打开聊天室'],
    }
    setMessages(prev => [...prev, systemMessage])
  }

  // 渲染 AI 预沟通对话历史（Generative UI）
  const renderPreCommunicationDialog = (messages: unknown) => {
    const typedMessages = messages as Array<{ id: string; sender_agent: string; content: string; topic_tag?: string; round_number: number; message_type?: string }>

    if (!typedMessages || typedMessages.length === 0) {
      return (
        <Card className="generative-card" size="small">
          <Empty description="暂无对话内容" />
        </Card>
      )
    }

    return (
      <div className="generative-dialog-container">
        <Timeline
          items={typedMessages.map((msg, idx) => {
            return {
              key: msg.id,
              color: msg.sender_agent.includes('agent_1') ? 'blue' : 'purple',
              dot: <HeartFilled style={{ color: '#FF8FAB' }} />,
              children: (
                <Card size="small" style={{ marginBottom: 8 }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div>
                      <Tag color={msg.sender_agent.includes('agent_1') ? 'blue' : 'purple'}>
                        {msg.sender_agent.includes('agent_1') ? 'AI 替身 A' : 'AI 替身 B'}
                      </Tag>
                      <Tag>{msg.message_type || 'text'}</Tag>
                      {msg.topic_tag && <Tag>{msg.topic_tag}</Tag>}
                      <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                        第{msg.round_number}轮
                      </Text>
                    </div>
                    <Paragraph style={{ margin: 0, fontSize: 13 }}>{msg.content}</Paragraph>
                  </Space>
                </Card>
              ),
            }
          })}
        />
      </div>
    )
  }

  // 渲染消息内容 - 使用 useMemo 缓存渲染结果
  const renderMessageContent = useCallback((message: Message) => {
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
          src={HerAvatar}
          style={{ backgroundColor: '#fff', marginRight: 8, padding: 4 }}
        />
        <div className="message-content">
          <div className="message-bubble ai-bubble">
            <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-line' }}>
              {message.content}
            </Paragraph>
          </div>

          {/* Generative UI: AI 预沟通会话卡片 */}
          {message.generativeCard === 'precommunication' && message.generativeData && (
            <div className="generative-ui-container">
              {renderPreCommunicationSessions(message.generativeData)}
            </div>
          )}

          {/* Generative UI: AI 预沟通对话历史 */}
          {message.generativeCard === 'precommunication-dialog' && message.generativeData && (
            <div className="generative-ui-container">
              {renderPreCommunicationDialog(message.generativeData)}
            </div>
          )}

          {/* Generative UI: 功能卡片 */}
          {message.generativeCard === 'feature' && message.featureAction && (
            <div className="generative-ui-container feature-card-container">
              <FeatureCardRenderer
                featureAction={message.featureAction}
                data={message.generativeData}
                onAction={(action, data) => {
                  console.log('Feature action:', action, data)
                  // TODO: 调用对应的 API
                }}
              />
            </div>
          )}

          {/* Generative UI: AI 问题卡片 */}
          {message.generativeCard === 'profile_question' && message.generativeData && (
            <div className="generative-ui-container">
              <ProfileQuestionCard
                question={(message.generativeData as any).question}
                subtitle={(message.generativeData as any).subtitle}
                questionType={(message.generativeData as any).question_type}
                options={(message.generativeData as any).options}
                dimension={(message.generativeData as any).dimension}
                depth={(message.generativeData as any).depth || 0}
                onAnswer={async (dimension, value, depth) => {
                  // 用户选择后，自动发送为消息
                  const answerText = Array.isArray(value)
                    ? value.join('、')
                    : value

                  // 添加用户回答消息
                  const userMessage: Message = {
                    id: `user-${Date.now()}`,
                    type: 'user',
                    content: answerText,
                    timestamp: new Date(),
                  }
                  setMessages(prev => [...prev, userMessage])

                  // 调用 API 保存用户偏好
                  try {
                    const result = await profileApi.submitAnswer({
                      dimension,
                      answer: value,
                      depth,
                    })

                    // 添加 AI 确认回复
                    const aiMessage: Message = {
                      id: `ai-${Date.now()}`,
                      type: 'ai',
                      content: result.ai_message,
                      timestamp: new Date(),
                    }
                    setMessages(prev => [...prev, aiMessage])

                    // 如果有下一个问题，添加问题卡片
                    if (result.has_more_questions && result.next_question) {
                      setTimeout(() => {
                        const questionMessage: Message = {
                          id: `question-${Date.now()}`,
                          type: 'ai',
                          content: '',
                          generativeCard: 'profile_question',
                          generativeData: result.next_question,
                          timestamp: new Date(),
                        }
                        setMessages(prev => [...prev, questionMessage])
                      }, 500)
                    }
                  } catch (error) {
                    console.error('Failed to submit profile answer:', error)
                  }
                }}
              />
            </div>
          )}

          {/* 匹配结果卡片 */}
          {message.matches && message.matches.length > 0 && (
            <div className="match-cards">
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                为你推荐 {message.matches.length} 位匹配对象
              </Text>
              <div className="match-cards-container">
                {message.matches.slice(0, 3).map((match, index) => {
                  // 使用稳定的 key 避免不必要的重新渲染
                  const matchKey = match.user?.id || match.user_id || `match-${index}`
                  return (
                    <div key={matchKey} className="match-card-wrapper">
                      <MatchCard
                        match={match}
                        onLike={() => onMatchSelect?.(match)}
                        onPass={() => {}}
                        onMessage={() => {
                          // 发起对话 - 直接进入聊天室，而不是打开匹配详情
                          const partnerId = match.user?.id || match.user_id || ''
                          const partnerName = match.user?.name || 'TA'
                          onOpenChatRoom?.(partnerId, partnerName)
                        }}
                        isSwipeMode={false}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 建议操作 */}
          {message.next_actions && message.next_actions.length > 0 && (
            <div className="suggestion-chips">
              <Space wrap>
                {message.next_actions.map((action, index) => (
                  <Tag
                    key={action} // 使用 action 文本作为 key 更稳定
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
  }, [onMatchSelect, handleQuickAction, renderPreCommunicationSessions, renderPreCommunicationDialog, HerAvatar])

  return (
    <div className="chat-interface">
      {/* 消息列表 */}
      <div className="messages-container">
        {messages.map((message, idx) => (
          <div key={message.id} className="message-wrapper">
            {renderMessageContent(message)}
          </div>
        ))}
        {isLoading && (
          <div className="loading-indicator">
            <Spin size="small" />
            <Text type="secondary" style={{ marginLeft: 8 }}>
              Her 正在想...
            </Text>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="input-area">
        {/* 动态快捷标签 */}
        {quickTags.length > 0 && (
          <div className="quick-actions">
            {quickTags.map((tag, index) => (
              <Tag
                key={index}
                bordered={false}
                onClick={() => setInputValue(tag.trigger)}
                className="quick-action-tag"
              >
                {tag.label}
              </Tag>
            ))}
          </div>
        )}
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="告诉我你想要什么，或者随便聊聊~"
          prefix={<HeartFilled style={{ color: '#FF8FAB' }} />}
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
