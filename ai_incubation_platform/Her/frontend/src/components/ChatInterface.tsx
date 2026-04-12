// AI Native Chat 组件 - 对话式交互核心

import React, { useState, useRef, useEffect, useMemo, useCallback, lazy, Suspense } from 'react'
import { Input, Button, Card, Avatar, Spin, Tag, Space, Typography, Divider } from 'antd'
import { UserOutlined, ThunderboltOutlined, HeartFilled, MessageOutlined, SendOutlined } from '@ant-design/icons'
import type { MatchCandidate, AIPreCommunicationSession } from '../types'
import { conversationMatchingApi, aiAwarenessApi } from '../api'
import { preCommunicationSkill, skillRegistry } from '../api/skillClient'
import { deerflowClient } from '../api/deerflowClient'
import { authStorage, registrationStorage } from '../utils/storage'
import profileApi from '../api/profileApi'
import HerAvatar from '../assets/her-avatar.svg'
import type { Feature } from './FeaturesDrawer'
import './ChatInterface.less'

// 辅助函数（从已删除的 aiInterlocutor.ts 迁移）
const getCompatibilityLevel = (score: number): string => {
  if (score >= 90) return '极高'
  if (score >= 80) return '很高'
  if (score >= 70) return '较高'
  if (score >= 60) return '中等'
  return '较低'
}

const getSessionStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    pending: '等待开始',
    analyzing: '分析中',
    chatting: 'AI 对聊中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return texts[status] || status
}

// 🚀 [性能优化] 懒加载大型组件，减少初始 bundle 大小
const MatchCard = lazy(() => import('./MatchCard'))
const FeatureCardRenderer = lazy(() => import('./FeatureCards').then(m => ({ default: m.FeatureCardRenderer })))
const ProfileQuestionCard = lazy(() => import('./ProfileQuestionCard'))
const PreCommunicationSessionCard = lazy(() => import('./PreCommunicationSessionCard'))
const PreCommunicationDialogCard = lazy(() => import('./PreCommunicationDialogCard'))

// 🚀 [性能优化] 内联骨架屏组件，避免静态导入破坏代码分割
const InlineFeatureCardSkeleton: React.FC = () => (
  <Card className="feature-card" style={{ marginBottom: 16 }}>
    <div style={{ padding: 16 }}>
      <div style={{ width: 100, height: 20, background: '#f0f0f0', borderRadius: 4, marginBottom: 12 }} />
      <div style={{ width: '100%', height: 14, background: '#f0f0f0', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '80%', height: 14, background: '#f0f0f0', borderRadius: 4 }} />
    </div>
  </Card>
)

// 🚀 [性能优化] 匹配卡片骨架屏
const InlineMatchCardSkeleton: React.FC = () => (
  <Card className="match-card" style={{ marginBottom: 16, borderRadius: 16 }}>
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ width: 48, height: 48, background: '#f0f0f0', borderRadius: 12 }} />
        <div style={{ marginLeft: 12 }}>
          <div style={{ width: 120, height: 16, background: '#f0f0f0', borderRadius: 4 }} />
          <div style={{ width: 80, height: 12, background: '#f0f0f0', borderRadius: 4, marginTop: 6 }} />
        </div>
      </div>
      <div style={{ width: '100%', height: 14, background: '#f0f0f0', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '70%', height: 14, background: '#f0f0f0', borderRadius: 4 }} />
    </div>
  </Card>
)

// 🚀 [性能优化] 问题卡片骨架屏
const InlineQuestionCardSkeleton: React.FC = () => (
  <Card style={{ marginBottom: 16, borderRadius: 12 }}>
    <div style={{ padding: 16 }}>
      <div style={{ width: '80%', height: 18, background: '#f0f0f0', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '60%', height: 12, background: '#f0f0f0', borderRadius: 4, marginBottom: 16 }} />
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ width: 80, height: 32, background: '#f0f0f0', borderRadius: 8 }} />
        <div style={{ width: 80, height: 32, background: '#f0f0f0', borderRadius: 8 }} />
        <div style={{ width: 80, height: 32, background: '#f0f0f0', borderRadius: 8 }} />
      </div>
    </div>
  </Card>
)

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
  generativeCard?: 'precommunication' | 'precommunication-dialog' | 'match' | 'analysis' | 'feature' | 'profile_question' | 'quick_start'  // Generative UI 卡片类型（新增 quick_start）
  generativeData?: unknown  // Generative UI 数据
  featureAction?: string  // 功能卡片类型
}

// 最大消息数量限制，防止内存泄漏
const MAX_MESSAGES = 50

// 检查是否是新用户（需要信息收集）
const isNewUserNeedsInfo = (): boolean => {
  const user = authStorage.getUser()
  // 如果用户信息不完整（缺少年龄、性别、所在地、关系目标中的任意一个）
  const hasRequiredInfo = user?.age && user?.gender && user?.location && user?.relationship_goal
  return !hasRequiredInfo
}

// 获取缺失的信息字段
const getMissingInfoFields = (): string[] => {
  const user = authStorage.getUser()
  const missing: string[] = []
  if (!user?.age) missing.push('age')
  if (!user?.gender) missing.push('gender')
  if (!user?.location) missing.push('location')
  if (!user?.relationship_goal) missing.push('relationship_goal')
  return missing
}

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
  // 判断是否是新用户，决定欢迎消息内容
  const isNewUser = isNewUserNeedsInfo()

  const [messages, setMessages] = useState<Message[]>(() => {
    if (isNewUser) {
      // 新用户：主动发起信息收集对话
      return [{
        id: 'welcome-new-user',
        type: 'ai',
        content: '你好！我是 Her 🤍\n\n我来帮你找到合适的人。\n\n先告诉我几个关键信息，马上给你推荐~',
        timestamp: new Date(),
        next_actions: ['开始'],
      }]
    } else {
      // 已有完整信息的用户：标准欢迎消息
      return [{
        id: 'welcome',
        type: 'ai',
        content:
          '你好，我是 Her 🤍\n\n我相信，每个人都有属于自己的那个人。\n\n我可以帮你：\n• 遇见懂你的 TA\n• 读懂你们的关系信号\n• 策划只属于你们的浪漫\n\n和我说说吧，你期待怎样的相遇？',
        timestamp: new Date(),
      }]
    }
  })
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [quickTags, setQuickTags] = useState<QuickTag[]>([])  // 动态快捷标签
  const [threadId, setThreadId] = useState<string>(() => {
    // 初始化 thread_id，用于 DeerFlow 对话上下文持久化
    const userId = authStorage.getUserId()
    return `her-${userId}-${Date.now()}`
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 新用户信息收集状态
  const [collectingStep, setCollectingStep] = useState<number>(() => {
    if (!isNewUser) return -1  // 不需要收集
    const missing = getMissingInfoFields()
    return missing.length > 0 ? 0 : -1  // 0 表示开始收集
  })

  // 获取动态快捷标签
  useEffect(() => {
    const fetchQuickTags = async () => {
      try {
        const token = authStorage.getToken()
        const response = await fetch('/api/chat/tags', {
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

  // ==================== 新用户信息收集流程 ====================

  /**
   * 处理新用户信息收集
   * 在对话中逐步收集：年龄、性别、所在地、关系目标
   * 收集完成后立即展示推荐
   */
  const handleQuickStartStep = async (userInput: string) => {
    const user = authStorage.getUser()
    const missingFields = getMissingInfoFields()

    // 如果用户信息已完整，直接进行匹配
    if (missingFields.length === 0) {
      // 标记收集完成
      setCollectingStep(-1)
      registrationStorage.markCompleted()

      // 调用匹配 API
      try {
        const response = await conversationMatchingApi.match({
          user_intent: '帮我找对象',
        })

        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: response.message || '好的，我这有几个觉得合适的，你先看看~',
          matches: response.matches,
          timestamp: new Date(),
        }
        setMessages(prev => {
          const newMessages = [...prev, aiMessage]
          if (newMessages.length > MAX_MESSAGES) {
            return newMessages.slice(newMessages.length - MAX_MESSAGES)
          }
          return newMessages
        })
      } catch (error) {
        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: '好的，信息收集完成了！你可以在对话中说"帮我找对象"开始匹配~',
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, aiMessage])
      }
      setIsLoading(false)
      return true
    }

    // 根据缺失字段生成对应的问题卡片
    const nextMissing = missingFields[collectingStep]
    if (nextMissing && collectingStep >= 0) {
      // 生成问题卡片
      const questionCard = generateQuickStartQuestionCard(nextMissing)

      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: '',
        generativeCard: 'quick_start',
        generativeData: questionCard,
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
      return true
    }

    return false
  }

  /**
   * 根据缺失字段生成问题卡片
   */
  const generateQuickStartQuestionCard = (field: string): {
    question: string
    question_type: 'single_choice' | 'input' | 'tags'
    options: { value: string; label: string; icon?: string }[]
    dimension: string
  } => {
    switch (field) {
      case 'age':
        return {
          question: '你多大啦？',
          question_type: 'single_choice',
          options: [
            { value: '18-22', label: '18-22岁', icon: '🌱' },
            { value: '23-26', label: '23-26岁', icon: '🌿' },
            { value: '27-30', label: '27-30岁', icon: '🌳' },
            { value: '31-35', label: '31-35岁', icon: '🌲' },
            { value: '36-40', label: '36-40岁', icon: '🎄' },
            { value: '40+', label: '40岁以上', icon: '⛰️' },
          ],
          dimension: 'age',
        }
      case 'gender':
        return {
          question: '你是男生还是女生？',
          question_type: 'single_choice',
          options: [
            { value: 'male', label: '男生', icon: '👨' },
            { value: 'female', label: '女生', icon: '👩' },
          ],
          dimension: 'gender',
        }
      case 'location':
        return {
          question: '你在哪个城市？',
          question_type: 'tags',
          options: [
            { value: '北京', label: '北京' },
            { value: '上海', label: '上海' },
            { value: '广州', label: '广州' },
            { value: '深圳', label: '深圳' },
            { value: '杭州', label: '杭州' },
            { value: '成都', label: '成都' },
            { value: '武汉', label: '武汉' },
            { value: '南京', label: '南京' },
          ],
          dimension: 'location',
        }
      case 'relationship_goal':
        return {
          question: '想找什么样的关系？',
          question_type: 'single_choice',
          options: [
            { value: 'serious', label: '认真恋爱', icon: '💕' },
            { value: 'marriage', label: '奔着结婚', icon: '💍' },
            { value: 'dating', label: '轻松交友', icon: '☕' },
            { value: 'casual', label: '随便聊聊', icon: '💭' },
          ],
          dimension: 'relationship_goal',
        }
      default:
        return {
          question: '请告诉我更多信息',
          question_type: 'input',
          options: [],
          dimension: field,
        }
    }
  }

  /**
   * 处理 QuickStart 问题回答
   */
  const handleQuickStartAnswer = async (dimension: string, value: string | string[]) => {
    // 更新用户信息
    const user = authStorage.getUser()
    const updatedUser = { ...user }

    switch (dimension) {
      case 'age':
        // 解析年龄范围，取中间值
        if (typeof value === 'string') {
          const range = value.split('-')
          if (range.length === 2) {
            updatedUser.age = Math.round((parseInt(range[0]) + parseInt(range[1])) / 2)
          } else if (value === '40+') {
            updatedUser.age = 42
          }
        }
        break
      case 'gender':
        updatedUser.gender = value as string
        break
      case 'location':
        updatedUser.location = typeof value === 'string' ? value : value[0]
        break
      case 'relationship_goal':
        updatedUser.relationship_goal = value as string
        break
    }

    // 保存更新后的用户信息
    authStorage.setUser(updatedUser as any)

    // 进入下一步
    const newStep = collectingStep + 1
    const remainingMissing = getMissingInfoFields()

    if (remainingMissing.length === 0) {
      // 所有信息收集完成
      setCollectingStep(-1)
      registrationStorage.markCompleted()

      // 添加确认消息
      const confirmMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: `好的，记下了！\n\n${updatedUser.age ? `年龄：${updatedUser.age}岁` : ''}\n${updatedUser.gender ? `性别：${updatedUser.gender === 'male' ? '男' : '女'}` : ''}\n${updatedUser.location ? `所在地：${updatedUser.location}` : ''}\n${updatedUser.relationship_goal ? `关系目标：${updatedUser.relationship_goal === 'serious' ? '认真恋爱' : updatedUser.relationship_goal === 'marriage' ? '奔着结婚' : updatedUser.relationship_goal === 'dating' ? '轻松交友' : '随便聊聊'}` : ''}\n\n我来帮你找合适的对象~`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, confirmMessage])

      // 立即调用匹配 API
      setIsLoading(true)
      try {
        const response = await conversationMatchingApi.match({
          user_intent: '帮我找对象',
        })

        const matchMessage: Message = {
          id: `ai-match-${Date.now()}`,
          type: 'ai',
          content: response.message || '好的，我这有几个觉得合适的，你先看看~',
          matches: response.matches,
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, matchMessage])
      } catch (error) {
        const fallbackMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: '信息收集完成！你可以直接说"帮我找对象"开始匹配~',
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, fallbackMessage])
      } finally {
        setIsLoading(false)
      }
    } else {
      // 还有缺失字段，继续下一步
      setCollectingStep(newStep)

      // 添加过渡消息
      const transitionMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: '好的，记下了~',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, transitionMessage])

      // 触发下一个问题
      setTimeout(() => {
        handleQuickStartStep('')
      }, 500)
    }
  }

  // 新用户首次进入时，自动触发信息收集流程
  useEffect(() => {
    if (collectingStep === 0 && isNewUser) {
      // 用户点击"开始"后，展示第一个问题
      // 这里我们等待用户的第一次交互
    }
  }, [])

  /**
   * 简化后的 handleSend - 统一通过 DeerFlow Agent 处理
   *
   * 设计原则（AI Native）：
   * - DeerFlow 是 Agent 运行时，负责意图识别、工具编排、状态管理
   * - Her 只提供业务 Tools（匹配、关系分析、约会策划等）
   * - IntentRouter 中间件层已移除（DeerFlow 已具备此能力）
   * - Generative UI 由 DeerFlow 决定，前端只渲染
   */
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) {
      return
    }

    const userInput = inputValue

    // 1. 添加用户消息
    addUserMessage(userInput)
    setInputValue('')
    setIsLoading(true)

    // 追踪聊天消息行为
    const userId = authStorage.getUserId()
    if (userId) {
      aiAwarenessApi.trackChatMessage(userId, 'system', userInput.length).catch(() => {})
    }

    // 2. 调用 DeerFlow Agent（AI Native 架构：Agent 是核心决策引擎）
    try {
      const result = await deerflowClient.chat(userInput, threadId)

      // 3. 添加 AI 消息
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: result.ai_message,
        timestamp: new Date(),
        generativeCard: mapComponentTypeToGenerativeCard(result.generative_ui?.component_type),
        generativeData: result.generative_ui?.props,
        suggestions: result.suggested_actions?.map((a: any) => a.label),
        next_actions: result.suggested_actions?.map((a: any) => a.action),
      }

      addAIMessage(aiMessage)

      // 4. 如果 DeerFlow 未使用，显示提示
      if (!result.deerflow_used) {
        console.warn('DeerFlow not available, using fallback response')
      }

    } catch (error) {
      console.error('DeerFlow chat error:', error)
      addErrorMessage('抱歉，出现了一些问题，请稍后再试~')
    } finally {
      setIsLoading(false)
    }
  }

  // 辅助函数：添加用户消息
  const addUserMessage = (content: string) => {
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => {
      const newMessages = [...prev, userMessage]
      if (newMessages.length > MAX_MESSAGES) {
        return newMessages.slice(newMessages.length - MAX_MESSAGES)
      }
      return newMessages
    })
  }

  // 辅助函数：添加 AI 消息
  const addAIMessage = (message: Message) => {
    setMessages(prev => {
      const newMessages = [...prev, message]
      if (newMessages.length > MAX_MESSAGES) {
        return newMessages.slice(newMessages.length - MAX_MESSAGES)
      }
      return newMessages
    })
  }

  // 辅助函数：添加错误消息
  const addErrorMessage = (content: string) => {
    const errorMessage: Message = {
      id: `error-${Date.now()}`,
      type: 'system',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => {
      const newMessages = [...prev, errorMessage]
      if (newMessages.length > MAX_MESSAGES) {
        return newMessages.slice(newMessages.length - MAX_MESSAGES)
      }
      return newMessages
    })
  }

  // 辅助函数：将后端 component_type 映射为前端 generativeCard
  // 支持 DeerFlow 返回的多种 Generative UI 类型
  const mapComponentTypeToGenerativeCard = (componentType: string): Message['generativeCard'] | undefined => {
    const mapping: Record<string, Message['generativeCard'] | undefined> = {
      // 匹配相关
      'MatchCardList': 'match',
      'MatchCardList': 'match',
      // 预沟通
      'PreCommunicationPanel': 'precommunication',
      'PreCommunicationDialog': 'precommunication-dialog',
      // 信息收集
      'ProfileQuestionCard': 'profile_question',
      // 约会相关
      'DateSuggestionCard': 'feature',
      'DatePlanCard': 'feature',
      // 分析相关
      'RelationshipReportCard': 'analysis',
      'CompatibilityChart': 'analysis',
      'RelationshipHealthCard': 'analysis',
      // 功能展示
      'CapabilityCard': 'feature',
      'TopicsCard': 'feature',
      'IcebreakerCard': 'feature',
      // 简单响应
      'SimpleResponse': undefined,
      'AIResponseCard': undefined,
    }
    return mapping[componentType]
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

  // 查看预沟通对话消息（由 PreCommunicationSessionCard 组件调用）
  const handleViewPreCommunicationMessages = async (sessionId: string) => {
    try {
      setIsLoading(true)
      // 注：pre_communication skill 的 get_messages action 已支持
      const result = await skillRegistry.execute('pre_communication', {
        match_id: sessionId,
        action: 'get_messages'
      })

      if (!result.success) {
        throw new Error(result.error || '获取对话历史失败')
      }

      const messages = result.data?.messages || []

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
              {/* 🚀 [性能优化] Suspense 包裹懒加载的 PreCommunicationSessionCard */}
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <PreCommunicationSessionCard
                  sessions={message.generativeData as AIPreCommunicationSession[]}
                  onViewMessages={handleViewPreCommunicationMessages}
                  onStartChat={handleStartChatFromSession}
                />
              </Suspense>
            </div>
          )}

          {/* Generative UI: AI 预沟通对话历史 */}
          {message.generativeCard === 'precommunication-dialog' && message.generativeData && (
            <div className="generative-ui-container">
              {/* 🚀 [性能优化] Suspense 包裹懒加载的 PreCommunicationDialogCard */}
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <PreCommunicationDialogCard
                  messages={message.generativeData as Array<{ id: string; sender_agent: string; content: string; topic_tag?: string; round_number: number; message_type?: string }>}
                />
              </Suspense>
            </div>
          )}

          {/* Generative UI: 功能卡片 */}
          {message.generativeCard === 'feature' && message.featureAction && (
            <div className="generative-ui-container feature-card-container">
              {/* 🚀 [性能优化] Suspense 包裹懒加载组件，骨架屏作为 fallback */}
              <Suspense fallback={<InlineFeatureCardSkeleton />}>
                <FeatureCardRenderer
                  featureAction={message.featureAction}
                  data={message.generativeData}
                  onAction={(action, data) => {
                    // 功能卡片动作处理（具体 API 调用根据 action 类型分发）
                  }}
                />
              </Suspense>
            </div>
          )}

          {/* Generative UI: AI 问题卡片 */}
          {message.generativeCard === 'profile_question' && message.generativeData && (
            <div className="generative-ui-container">
              {/* 🚀 [性能优化] Suspense 包裹懒加载的 ProfileQuestionCard */}
              <Suspense fallback={<InlineQuestionCardSkeleton />}>
                <ProfileQuestionCard
                  question={(message.generativeData as any).question}
                  subtitle={(message.generativeData as any).subtitle}
                  questionType={(message.generativeData as any).question_type}
                  options={(message.generativeData as any).options}
                  dimension={(message.generativeData as any).dimension}
                  depth={(message.generativeData as any).depth || 0}
                  onAnswer={async (dimension, value, depth) => {
                  // 🎯 AI Native 设计：用户选择静默处理，不产生冗余对话消息
                  // 点击选项即代表选择，无需在对话区"表演"选择过程

                  // 调用 API 保存用户偏好
                  // 错误会抛给 ProfileQuestionCard 处理显示
                  const result = await profileApi.submitAnswer({
                    dimension,
                    answer: value,
                    depth,
                  })

                  // 如果有下一个问题，直接替换当前卡片（不添加新消息）
                  if (result.has_more_questions && result.next_question) {
                    // 找到当前问题卡片消息并替换
                    setMessages(prev => {
                      const lastQuestionIdx = prev.findIndex(
                        m => m.generativeCard === 'profile_question' && m.id === message.id
                      )
                      if (lastQuestionIdx !== -1) {
                        const newMessages = [...prev]
                        newMessages[lastQuestionIdx] = {
                          ...newMessages[lastQuestionIdx],
                          generativeData: result.next_question,
                        }
                        return newMessages
                      }
                      // 如果没找到当前卡片，追加新的
                      return [...prev, {
                        id: `question-${Date.now()}`,
                        type: 'ai',
                        content: '',
                        generativeCard: 'profile_question',
                        generativeData: result.next_question,
                        timestamp: new Date(),
                      }]
                    })
                  } else {
                    // 没有更多问题，移除当前问题卡片，显示完成提示或匹配结果
                    setMessages(prev => prev.filter(m => m.id !== message.id))

                    // 可选：添加简洁的完成提示
                    if (result.ai_message && !result.ai_message.includes('收到')) {
                      const completionMessage: Message = {
                        id: `ai-${Date.now()}`,
                        type: 'ai',
                        content: result.ai_message,
                        timestamp: new Date(),
                      }
                      setMessages(prev => [...prev, completionMessage])
                    }
                  }
                }}
                />
              </Suspense>
            </div>
          )}

          {/* Generative UI: QuickStart 信息收集卡片 */}
          {message.generativeCard === 'quick_start' && message.generativeData && (
            <div className="generative-ui-container">
              <Suspense fallback={<InlineQuestionCardSkeleton />}>
                <ProfileQuestionCard
                  question={(message.generativeData as any).question}
                  questionType={(message.generativeData as any).question_type}
                  options={(message.generativeData as any).options}
                  dimension={(message.generativeData as any).dimension}
                  depth={0}
                  onAnswer={async (dimension, value) => {
                    // 处理 QuickStart 回答
                    await handleQuickStartAnswer(dimension, value)
                  }}
                />
              </Suspense>
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
                      {/* 🚀 [性能优化] Suspense 包裹懒加载的 MatchCard */}
                      <Suspense fallback={<InlineMatchCardSkeleton />}>
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
                      </Suspense>
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
  }, [onMatchSelect, handleQuickAction, handleQuickStartAnswer, HerAvatar])

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
