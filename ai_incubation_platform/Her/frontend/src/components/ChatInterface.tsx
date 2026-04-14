// AI Native Chat 组件 - 对话式交互核心

import React, { useState, useRef, useEffect, useCallback, lazy, Suspense } from 'react'
import { Input, Button, Card, Avatar, Spin, Tag, Space, Typography } from 'antd'
import { UserOutlined, ThunderboltOutlined, HeartFilled, SendOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate, AIPreCommunicationSession } from '../types'
import { getFrontendCard, GENERATIVE_UI_SCHEMA } from '../types/generativeUI'
import { aiAwarenessApi } from '../api'
import { deerflowClient } from '../api/deerflowClient'
import { authStorage, registrationStorage } from '../utils/storage'
import type { UserInfo } from '../utils/storage'
import profileApi from '../api/profileApi'
import HerAvatar from '../assets/her-avatar.svg'
import type { Feature } from './FeaturesDrawer'
import './ChatInterface.less'

// 辅助函数（从已删除的 aiInterlocutor.ts 迁移）
const getCompatibilityLevel = (score: number, t: (key: string) => string): string => {
  if (score >= 90) return t('conversation.compatibilityLevel.veryHigh')
  if (score >= 80) return t('conversation.compatibilityLevel.high')
  if (score >= 70) return t('conversation.compatibilityLevel.mediumHigh')
  if (score >= 60) return t('conversation.compatibilityLevel.medium')
  return t('conversation.compatibilityLevel.low')
}

const getSessionStatusText = (status: string, t: (key: string) => string): string => {
  const statusMap: Record<string, string> = {
    pending: t('conversation.sessionStatus.pending'),
    analyzing: t('conversation.sessionStatus.analyzing'),
    chatting: t('conversation.sessionStatus.chatting'),
    completed: t('conversation.sessionStatus.completed'),
    cancelled: t('conversation.sessionStatus.cancelled'),
  }
  return statusMap[status] || status
}

// 🚀 [性能优化] 懒加载大型组件，减少初始 bundle 大小
const MatchCard = lazy(() => import('./MatchCard'))
const MatchCardList = lazy(() => import('./generative-ui/MatchComponents').then(m => ({ default: m.MatchCardList })))
const FeatureCardRenderer = lazy(() => import('./FeatureCards').then(m => ({ default: m.FeatureCardRenderer })))
const ProfileQuestionCard = lazy(() => import('./ProfileQuestionCard'))
const PreCommunicationSessionCard = lazy(() => import('./PreCommunicationSessionCard'))
const PreCommunicationDialogCard = lazy(() => import('./PreCommunicationDialogCard'))
const UserProfileCard = lazy(() => import('./UserProfileCard'))

// 🚀 [性能优化] 导入公共骨架屏组件（从 skeletons.tsx 提取）
import { SkeletonComponents } from './skeletons'

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
  generativeCard?: 'precommunication' | 'precommunication-dialog' | 'match' | 'analysis' | 'feature' | 'profile_question' | 'quick_start' | 'learning_confirmation' | 'user_profile'
  generativeData?: unknown
  featureAction?: string
}

// 最大消息数量限制，防止内存泄漏
const MAX_MESSAGES = 50

// 检查是否是新用户（需要信息收集）
// SelfProfile 收集：用户本身是什么样的
// 判断逻辑：
// 1. 如果必填字段不完整 → 需要收集
// 2. 如果 QuickStart 流程未完成 → 需要收集（注册后需要走 QuickStart）
//
// 必填字段：
// - 注册表单：姓名、年龄、性别、所在地
// - QuickStart：学历、职业、收入、房产（重要匹配字段）
const isNewUserNeedsInfo = (): boolean => {
  const user = authStorage.getUser()

  // 必填字段：姓名、年龄、性别、所在地
  // 可选字段：职业、收入、房产、学历（用户可跳过）
  const hasRequiredInfo = user?.name && user?.age && user?.gender && user?.location

  // 如果必填字段不完整，需要收集
  if (!hasRequiredInfo) {
    return true
  }

  // 如果 QuickStart 流程未完成，需要收集（注册后的新用户）
  // registrationStorage.isCompleted() 只有在 QuickStart 完成后才返回 true
  if (!registrationStorage.isCompleted()) {
    return true
  }

  // 已有完整信息且完成了 QuickStart，不需要收集
  return false
}

// 获取缺失的信息字段
// QuickStart 需要收集的字段：
// 1. 注册表单的基础字段（必填）
// 2. 重要匹配字段（无法行为推断，必须问卷）
// 3. 一票否决维度（最高优先级）
/**
 * 检查用户对象是否包含所有必填字段
 * 🔧 [新增] 用于 handleQuickStartAnswer 直接检查 updatedUser，避免 localStorage 读取时序问题
 */
const checkUserFieldsComplete = (user: UserInfo | null | undefined): boolean => {
  if (!user) return false

  // ===== 注册表单收集的基础字段 =====
  if (!user.name) return false
  if (!user.age) return false
  if (!user.gender) return false
  if (!user.location) return false

  // ===== QuickStart 收集的属性字段 =====
  if (!user.height) return false
  if (!user.education) return false
  if (!user.occupation) return false
  if (!user.income) return false
  if (!user.housing) return false
  if (!user.has_car && user.has_car !== false) return false  // 注意：has_car 可以是 false

  // ===== 一票否决维度 =====
  if (!user.want_children) return false
  if (!user.spending_style) return false

  // ===== 核心价值观维度 =====
  if (!user.family_importance && user.family_importance !== 0) return false
  if (!user.work_life_balance) return false

  // ===== 迁移能力维度 =====
  if (!user.migration_willingness && user.migration_willingness !== 0) return false
  if (!user.accept_remote && user.accept_remote !== false) return false

  // ===== 生活方式维度 =====
  if (!user.sleep_type) return false

  return true
}

const getMissingInfoFields = (): string[] => {
  const user = authStorage.getUser()
  const missing: string[] = []

  // ===== 注册表单收集的基础字段 =====
  if (!user?.name) missing.push('name')
  if (!user?.age) missing.push('age')
  if (!user?.gender) missing.push('gender')
  if (!user?.location) missing.push('location')

  // ===== QuickStart 收集的属性字段 =====
  if (!user?.height) missing.push('height')       // 身高 (v11)
  if (!user?.education) missing.push('education')
  if (!user?.occupation) missing.push('occupation')
  if (!user?.income) missing.push('income')
  if (!user?.housing) missing.push('housing')
  if (!user?.has_car && user?.has_car !== false) missing.push('has_car')     // 是否有车 (v15)

  // ===== 一票否决维度（最高优先级）=====
  if (!user?.want_children) missing.push('want_children')   // v17 🔴
  if (!user?.spending_style) missing.push('spending_style') // v27 🔴

  // ===== 核心价值观维度 =====
  if (!user?.family_importance && user?.family_importance !== 0) missing.push('family_importance')  // v16
  if (!user?.work_life_balance) missing.push('work_life_balance')  // v23

  // ===== 迁移能力维度 =====
  if (!user?.migration_willingness && user?.migration_willingness !== 0) missing.push('migration_willingness')  // v160
  if (!user?.accept_remote && user?.accept_remote !== false) missing.push('accept_remote')  // v163

  // ===== 生活方式维度 =====
  if (!user?.sleep_type) missing.push('sleep_type')  // v88

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
  const { t } = useTranslation()
  // 判断是否是新用户，决定欢迎消息内容
  const isNewUser = isNewUserNeedsInfo()

  const [messages, setMessages] = useState<Message[]>(() => {
    if (isNewUser) {
      // 新用户：主动发起信息收集对话
      return [{
        id: 'welcome-new-user',
        type: 'ai',
        content: t('conversation.welcomeNew'),
        timestamp: new Date(),
        next_actions: [t('conversation.startChat')],
      }]
    } else {
      // 已有完整信息的用户：标准欢迎消息
      return [{
        id: 'welcome',
        type: 'ai',
        content: t('conversation.welcomeUser'),
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
          { label: t('home.todayMatches'), trigger: '看看今天有什么推荐' }
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
   *
   * 流程设计：
   * 1. 如果必填字段不完整 → 收集缺失字段（SelfProfile）
   * 2. 如果必填字段完整但 QuickStart 未完成 → 显示引导消息，让用户描述想找的对象（DesireProfile）
   * 3. 如果必填字段完整且 QuickStart 已完成 → 不应该触发这个流程
   */
  // 🚀 [性能优化] 使用 useCallback，依赖 collectingStep（其他 state setter 是稳定的）
  const handleQuickStartStep = useCallback(async (userInput: string) => {
    const user = authStorage.getUser()
    const missingFields = getMissingInfoFields()

    // ===== 场景1：必填字段不完整，需要收集 =====
    if (missingFields.length > 0) {
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

    // ===== 场景2：必填字段完整，但 QuickStart 未完成 → 显示引导消息 =====
    // 此时 SelfProfile 已有（注册表单收集），但 DesireProfile 未收集
    // 需要让用户描述想找的对象
    if (!registrationStorage.isCompleted()) {
      setCollectingStep(-1)
      registrationStorage.markCompleted()

      // 构建用户画像摘要
      const profileSummary = `${user?.name || ''}${user?.age ? `，${user.age}岁` : ''}${user?.gender ? `，${user.gender === 'male' ? '男' : '女'}` : ''}${user?.location ? `，在${user.location}` : ''}`

      // 显示引导消息：让用户描述想找的对象
      const guideMessage: Message = {
        id: `ai-guide-${Date.now()}`,
        type: 'ai',
        content: t('conversation.readyToMatch') + '\n\n' + t('conversation.profileSummary', { info: profileSummary }),
        timestamp: new Date(),
        next_actions: [t('conversation.startMatching')],
      }
      setMessages(prev => [...prev, guideMessage])
      setIsLoading(false)
      return true
    }

    // ===== 场景3：必填字段完整且 QuickStart 已完成 =====
    // 不应该触发这个流程，isNewUserNeedsInfo() 应该返回 false
    setIsLoading(false)
    return false
  }, [collectingStep])

  /**
   * 根据缺失字段生成问题卡片
   *
   * SelfProfile 收集（用户本身是什么样的）
   *
   * 数据来源分类：
   * - 注册表单：姓名、年龄、性别、所在地
   * - QuickStart 属性：身高、学历、职业、收入、房产、车
   * - QuickStart 一票否决：生育意愿、消费观念
   * - QuickStart 价值观：家庭重要度、工作生活平衡
   * - QuickStart 迁移能力：迁移意愿、异地接受度
   * - QuickStart 生活方式：作息类型
   *
   * 这些字段无法通过用户行为推断，必须主动收集
   */
  const generateQuickStartQuestionCard = (field: string): {
    question: string
    subtitle?: string  // 问题副标题（解释重要性）
    question_type: 'single_choice' | 'input' | 'tags'
    options: { value: string; label: string; icon?: string }[]
    dimension: string
    optional?: boolean  // 标记是否为可选字段
    veto_dimension?: boolean  // 标记是否为一票否决维度
  } => {
    switch (field) {
      // ===== 注册表单基础字段 =====
      case 'name':
        return {
          question: t('conversation.qsName'),
          question_type: 'input',
          options: [],
          dimension: 'name',
          optional: false,
        }
      case 'age':
        return {
          question: t('conversation.qsAge'),
          question_type: 'single_choice',
          options: [
            { value: '18-22', label: t('conversation.qsAgeRange.18-22'), icon: '🌱' },
            { value: '23-26', label: t('conversation.qsAgeRange.23-26'), icon: '🌿' },
            { value: '27-30', label: t('conversation.qsAgeRange.27-30'), icon: '🌳' },
            { value: '31-35', label: t('conversation.qsAgeRange.31-35'), icon: '🌲' },
            { value: '36-40', label: t('conversation.qsAgeRange.36-40'), icon: '🎄' },
            { value: '40+', label: t('conversation.qsAgeRange.40+'), icon: '⛰️' },
          ],
          dimension: 'age',
          optional: false,
        }
      case 'gender':
        return {
          question: t('conversation.qsGender'),
          question_type: 'single_choice',
          options: [
            { value: 'male', label: t('conversation.qsGenderOption.male'), icon: '👨' },
            { value: 'female', label: t('conversation.qsGenderOption.female'), icon: '👩' },
          ],
          dimension: 'gender',
          optional: false,
        }
      case 'location':
        return {
          question: t('conversation.qsLocation'),
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
            { value: '苏州', label: '苏州' },
            { value: '西安', label: '西安' },
            { value: '重庆', label: '重庆' },
            { value: '天津', label: '天津' },
          ],
          dimension: 'location',
          optional: false,
        }

      // ===== QuickStart 属性字段 =====
      case 'height':
        return {
          question: t('conversation.qsHeight'),
          question_type: 'input',
          options: [],
          dimension: 'height',
          optional: false,
        }
      case 'occupation':
        return {
          question: t('conversation.qsOccupation'),
          question_type: 'input',
          options: [],
          dimension: 'occupation',
          optional: false,
        }
      case 'income':
        return {
          question: t('conversation.qsIncome'),
          question_type: 'single_choice',
          options: [
            { value: '0-10', label: t('conversation.qsIncomeRange.0-10') },
            { value: '10-20', label: t('conversation.qsIncomeRange.10-20') },
            { value: '20-30', label: t('conversation.qsIncomeRange.20-30') },
            { value: '30-50', label: t('conversation.qsIncomeRange.30-50') },
            { value: '50+', label: t('conversation.qsIncomeRange.50+') },
          ],
          dimension: 'income',
          optional: false,
        }
      case 'education':
        return {
          question: t('conversation.qsEducation'),
          question_type: 'single_choice',
          options: [
            { value: 'high_school', label: t('conversation.qsEducationOption.high_school') },
            { value: 'college', label: t('conversation.qsEducationOption.college') },
            { value: 'bachelor', label: t('conversation.qsEducationOption.bachelor') },
            { value: 'master', label: t('conversation.qsEducationOption.master') },
            { value: 'phd', label: t('conversation.qsEducationOption.phd') },
          ],
          dimension: 'education',
          optional: false,
        }
      case 'housing':
        return {
          question: t('conversation.qsHousing'),
          question_type: 'single_choice',
          options: [
            { value: 'own', label: t('conversation.qsHousingOption.own') },
            { value: 'rent', label: t('conversation.qsHousingOption.rent') },
            { value: 'with_parents', label: t('conversation.qsHousingOption.with_parents') },
          ],
          dimension: 'housing',
          optional: false,
        }
      case 'has_car':
        return {
          question: t('conversation.qsHasCar'),
          question_type: 'single_choice',
          options: [
            { value: 'yes', label: t('conversation.qsHasCarOption.yes'), icon: '🚗' },
            { value: 'no', label: t('conversation.qsHasCarOption.no'), icon: '🚶' },
          ],
          dimension: 'has_car',
          optional: false,
        }

      // ===== 一票否决维度（最高优先级）=====
      case 'want_children':
        return {
          question: t('conversation.qsWantChildren'),
          subtitle: t('conversation.qsWantChildrenHint'),  // 提示一票否决重要性
          question_type: 'single_choice',
          options: [
            { value: 'want', label: t('conversation.qsWantChildrenOption.want'), icon: '👶' },
            { value: 'not_want', label: t('conversation.qsWantChildrenOption.not_want'), icon: '🙅' },
            { value: 'uncertain', label: t('conversation.qsWantChildrenOption.uncertain'), icon: '🤔' },
          ],
          dimension: 'want_children',
          optional: false,
          veto_dimension: true,  // 标记为一票否决维度
        }
      case 'spending_style':
        return {
          question: t('conversation.qsSpendingStyle'),
          subtitle: t('conversation.qsSpendingStyleHint'),
          question_type: 'single_choice',
          options: [
            { value: 'frugal', label: t('conversation.qsSpendingStyleOption.frugal'), icon: '💰' },
            { value: 'balanced', label: t('conversation.qsSpendingStyleOption.balanced'), icon: '⚖️' },
            { value: 'enjoy', label: t('conversation.qsSpendingStyleOption.enjoy'), icon: '🎁' },
          ],
          dimension: 'spending_style',
          optional: false,
          veto_dimension: true,
        }

      // ===== 核心价值观维度 =====
      case 'family_importance':
        return {
          question: t('conversation.qsFamilyImportance'),
          question_type: 'single_choice',
          options: [
            { value: 'very_high', label: t('conversation.qsFamilyImportanceOption.very_high'), icon: '👨‍👩‍👧‍👦' },
            { value: 'high', label: t('conversation.qsFamilyImportanceOption.high'), icon: '🏠' },
            { value: 'medium', label: t('conversation.qsFamilyImportanceOption.medium'), icon: '🏡' },
            { value: 'low', label: t('conversation.qsFamilyImportanceOption.low'), icon: '🌱' },
          ],
          dimension: 'family_importance',
          optional: false,
        }
      case 'work_life_balance':
        return {
          question: t('conversation.qsWorkLifeBalance'),
          question_type: 'single_choice',
          options: [
            { value: 'work_first', label: t('conversation.qsWorkLifeBalanceOption.work_first'), icon: '💼' },
            { value: 'balance', label: t('conversation.qsWorkLifeBalanceOption.balance'), icon: '⚖️' },
            { value: 'life_first', label: t('conversation.qsWorkLifeBalanceOption.life_first'), icon: '🌴' },
          ],
          dimension: 'work_life_balance',
          optional: false,
        }

      // ===== 迁移能力维度 =====
      case 'migration_willingness':
        return {
          question: t('conversation.qsMigrationWillingness'),
          subtitle: t('conversation.qsMigrationWillingnessHint'),
          question_type: 'single_choice',
          options: [
            { value: 'very_high', label: t('conversation.qsMigrationWillingnessOption.very_high'), icon: '✈️' },
            { value: 'high', label: t('conversation.qsMigrationWillingnessOption.high'), icon: '🚄' },
            { value: 'medium', label: t('conversation.qsMigrationWillingnessOption.medium'), icon: '🚗' },
            { value: 'low', label: t('conversation.qsMigrationWillingnessOption.low'), icon: '🏠' },
          ],
          dimension: 'migration_willingness',
          optional: false,
        }
      case 'accept_remote':
        return {
          question: t('conversation.qsAcceptRemote'),
          question_type: 'single_choice',
          options: [
            { value: 'yes', label: t('conversation.qsAcceptRemoteOption.yes'), icon: '❤️' },
            { value: 'conditional', label: t('conversation.qsAcceptRemoteOption.conditional'), icon: '🤝' },
            { value: 'no', label: t('conversation.qsAcceptRemoteOption.no'), icon: '📍' },
          ],
          dimension: 'accept_remote',
          optional: false,
        }

      // ===== 生活方式维度 =====
      case 'sleep_type':
        return {
          question: t('conversation.qsSleepType'),
          question_type: 'single_choice',
          options: [
            { value: 'early', label: t('conversation.qsSleepTypeOption.early'), icon: '🌅' },
            { value: 'normal', label: t('conversation.qsSleepTypeOption.normal'), icon: '☀️' },
            { value: 'late', label: t('conversation.qsSleepTypeOption.late'), icon: '🌙' },
          ],
          dimension: 'sleep_type',
          optional: false,
        }

      // ===== 默认 =====
      default:
        return {
          question: t('conversation.qsMoreInfo'),
          question_type: 'input',
          options: [],
          dimension: field,
          optional: true,
        }
    }
  }

  /**
   * 处理 QuickStart 问题回答
   *
   * 流程：
   * 1. 解析用户答案
   * 2. 写入 localStorage（临时缓存）
   * 3. 调用 profileApi.submitAnswer 写入 UserProfileDB（持久化）
   * 4. 进入下一步或完成流程
   */
  // 🚀 [性能优化] 使用 useCallback，依赖 collectingStep
  const handleQuickStartAnswer = useCallback(async (dimension: string, value: string | string[]) => {
    // 1. 解析用户答案，更新本地缓存
    const user = authStorage.getUser()
    const updatedUser = { ...user }

    // 用于提交到后端的值
    let submitValue: any = value

    switch (dimension) {
      // ===== 注册表单基础字段 =====
      case 'name':
        updatedUser.name = value as string
        submitValue = value
        break
      case 'age':
        // 解析年龄范围，取中间值
        if (typeof value === 'string') {
          const range = value.split('-')
          if (range.length === 2) {
            updatedUser.age = Math.round((parseInt(range[0]) + parseInt(range[1])) / 2)
            submitValue = updatedUser.age
          } else if (value === '40+') {
            updatedUser.age = 42
            submitValue = 42
          }
        }
        break
      case 'gender':
        updatedUser.gender = value as string
        submitValue = value
        break
      case 'location':
        updatedUser.location = typeof value === 'string' ? value : value[0]
        submitValue = updatedUser.location
        break

      // ===== QuickStart 属性字段 =====
      case 'height':
        // 身高（cm）
        updatedUser.height = parseInt(value as string)
        submitValue = updatedUser.height
        break
      case 'occupation':
        updatedUser.occupation = value as string
        submitValue = value
        break
      case 'income':
        // 解析收入范围，取中间值（单位：万元）
        if (typeof value === 'string') {
          const range = value.split('-')
          if (range.length === 2) {
            updatedUser.income = Math.round((parseInt(range[0]) + parseInt(range[1])) / 2)
            submitValue = updatedUser.income
          } else if (value === '50+') {
            updatedUser.income = 60
            submitValue = 60
          }
        }
        break
      case 'education':
        updatedUser.education = value as string
        submitValue = value
        break
      case 'housing':
        updatedUser.housing = value as string
        submitValue = value
        break
      case 'has_car':
        updatedUser.has_car = value === 'yes'
        submitValue = updatedUser.has_car
        break

      // ===== 一票否决维度 =====
      case 'want_children':
        updatedUser.want_children = value as string
        submitValue = value
        break
      case 'spending_style':
        updatedUser.spending_style = value as string
        submitValue = value
        break

      // ===== 核心价值观维度 =====
      case 'family_importance':
        // 转换为数值 (very_high=1.0, high=0.75, medium=0.5, low=0.25)
        const familyMap: Record<string, number> = {
          'very_high': 1.0,
          'high': 0.75,
          'medium': 0.5,
          'low': 0.25,
        }
        updatedUser.family_importance = familyMap[value as string] || 0.5
        submitValue = updatedUser.family_importance
        break
      case 'work_life_balance':
        updatedUser.work_life_balance = value as string
        submitValue = value
        break

      // ===== 迁移能力维度 =====
      case 'migration_willingness':
        // 转换为数值 (very_high=1.0, high=0.75, medium=0.5, low=0.25)
        const migrationMap: Record<string, number> = {
          'very_high': 1.0,
          'high': 0.75,
          'medium': 0.5,
          'low': 0.25,
        }
        updatedUser.migration_willingness = migrationMap[value as string] || 0.5
        submitValue = updatedUser.migration_willingness
        break
      case 'accept_remote':
        updatedUser.accept_remote = value === 'yes' || value === 'conditional'
        submitValue = value
        break

      // ===== 生活方式维度 =====
      case 'sleep_type':
        updatedUser.sleep_type = value as string
        submitValue = value
        break

      // ===== 其他 =====
      case 'relationship_goal':
        updatedUser.relationship_goal = value as string
        submitValue = value
        break
    }

    // 2. 保存到 localStorage（临时缓存）
    authStorage.setUser(updatedUser as any)

    // 3. 调用 profileApi 写入后端 UserProfileDB（持久化）
    // 🔧 性能优化：异步执行，不阻塞 UI
    // 前端已经知道下一步该做什么，不需要等后端 LLM 判断
    // 🔧 [修复] 必须传递 user_id，否则数据会保存到错误的用户（user-anonymous-dev）
    const userId = authStorage.getUserId()
    profileApi.submitAnswer({
      dimension: dimension,
      answer: submitValue,
      depth: 0,
      user_id: userId,  // ✅ 关键修复：传递正确的用户 ID
    })
      .then(() => console.log(`[QuickStart] 已写入画像: ${dimension} = ${submitValue}`))
      .catch(error => console.error(`[QuickStart] 写入画像失败: ${dimension}`, error))
      // 不阻断流程，继续进行

    // 4. 检查必填字段是否完成
    // 🔧 [修复] 使用 updatedUser 对象直接检查，而不是重新从 localStorage 读取
    // 因为 setUser 和 getUser 虽然都是同步，但在某些边缘情况下可能存在时序问题
    const requiredFieldsComplete = checkUserFieldsComplete(updatedUser as UserInfo)

    console.log(`[QuickStart] 字段完成检查: dimension=${dimension}, complete=${requiredFieldsComplete}`)

    if (requiredFieldsComplete) {
      // 必填字段完成，显示引导消息让用户描述想找的对象
      setCollectingStep(-1)
      registrationStorage.markCompleted()

      // 🔑 关键：同步用户画像到 DeerFlow Memory
      // 这样 her_tools 的 get_current_user_id() 才能提取到正确的 user_id
      try {
        await deerflowClient.syncMemory()
        console.log('[QuickStart] 用户画像已同步到 DeerFlow Memory')
      } catch (error) {
        console.error('[QuickStart] DeerFlow Memory 同步失败:', error)
        // 不阻断流程
      }

      // 构建用户画像摘要
      const profileSummary = `${updatedUser.name || ''}${updatedUser.age ? `，${updatedUser.age}岁` : ''}${updatedUser.gender ? `，${updatedUser.gender === 'male' ? '男' : '女'}` : ''}${updatedUser.location ? `，在${updatedUser.location}` : ''}${updatedUser.occupation ? `，${updatedUser.occupation}` : ''}`

      // 显示引导消息（不再自动调用匹配 API）
      const guideMessage: Message = {
        id: `ai-guide-${Date.now()}`,
        type: 'ai',
        content: t('conversation.readyToMatch') + '\n\n' + t('conversation.profileSummary', { info: profileSummary }),
        timestamp: new Date(),
        next_actions: [t('conversation.startMatching')],
      }
      setMessages(prev => [...prev, guideMessage])
      setIsLoading(false)
      return true
    } else {
      // 还有缺失字段，继续下一步
      // 🔧 [修复] 重新计算缺失字段，取第一个作为下一个问题
      // 不能用 collectingStep + 1 索引，因为 missingFields 列表会随着填写而缩短
      const stillMissing = getMissingInfoFields()
      const nextField = stillMissing[0]

      console.log(`[QuickStart] 继续收集，剩余缺失字段: ${stillMissing.join(', ')}`)

      if (nextField) {
        // 🔧 关闭 loading 状态，让用户可以继续操作
        setIsLoading(false)

        // 添加过渡消息
        const transitionMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: t('conversation.gotIt'),
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, transitionMessage])

        // 直接生成下一个问题卡片，而不是依赖 collectingStep 索引
        setTimeout(() => {
          const questionCard = generateQuickStartQuestionCard(nextField)
          const aiMessage: Message = {
            id: `ai-${Date.now()}`,
            type: 'ai',
            content: '',
            generativeCard: 'quick_start',
            generativeData: questionCard,
            timestamp: new Date(),
          }
          setMessages(prev => [...prev, aiMessage])
        }, 500)
      }
    }
  }, [t])

  // 新用户首次进入时，自动触发信息收集流程
  useEffect(() => {
    if (collectingStep === 0 && isNewUser) {
      // 用户点击"开始"后，展示第一个问题
      // 这里我们等待用户的第一次交互
    }
  }, [])

  /**
   * handleSend - 通过 Her 顾问服务（ConversationMatchService）处理
   *
   * 正确架构设计：
   * ┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
   * │ 用户消息    │ --> │ ConversationMatch    │ --> │ HerAdvisor  │
   * └─────────────┘     │    Service           │     │    Service  │
   *                     └──────────────────────┘     └─────────────┘
   *                              │
   *                       [意图分析]
   *                        ↓       ↓       ↓       ↓
   *                   [匹配请求] [偏好更新] [咨询] [一般对话]
   *                        ↓       ↓       ↓       ↓
   *                   执行匹配   更新画像   回答问题   普通对话
   *
   * ConversationMatchService 负责：
   * - 意图理解（IntentAnalyzer）
   * - 画像获取/更新（UserProfileService）
   * - 认知偏差识别（CognitiveBiasDetector）
   * - 匹配执行（HerAdvisorService）
   * - 主动建议（ProactiveSuggestionGenerator）
   *
   * 这是正确的路径！不要跳过这个 API 直接调用 DeerFlow！
   *
   * @param message - 可选，直接传入要发送的消息内容（用于快捷标签一键发送）
   */
  const handleSend = async (message?: string) => {
    // 如果传入 message 参数，直接使用；否则使用 inputValue 状态值
    const contentToSend = message ?? inputValue

    if (!contentToSend.trim() || isLoading) {
      return
    }

    // 1. 添加用户消息
    addUserMessage(contentToSend)
    setInputValue('')
    setIsLoading(true)

    // 追踪聊天消息行为
    const userId = authStorage.getUserId()
    if (userId) {
      aiAwarenessApi.trackChatMessage(userId, 'system', contentToSend.length).catch(() => {})
    }

    try {
      // 2. 调用 DeerFlow Agent（AI Native 架构：Agent 作为决策引擎）
      // Agent 会读取 SOUL.md 中的规则，正确处理匹配请求
      const result = await deerflowClient.chat(contentToSend, `her-chat-${userId || 'anonymous'}`)

      // 3. 解析 Agent 返回的结构化数据
      const parsedResult = deerflowClient.parseToolResult(result)

      // 4. 添加 AI 消息（Agent 自然语言回复 + Generative UI）
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: result.ai_message,
        timestamp: new Date(),
        // 🎯 [Generative UI] 从 Agent 返回的 generative_ui 映射到前端组件
        generativeCard: result.generative_ui
          ? mapComponentTypeToGenerativeCard(result.generative_ui.component_type)
          : undefined,
        generativeData: result.generative_ui?.props,
        // 从 Agent 返回的结构化数据中提取匹配结果（兼容旧逻辑）
        matches: parsedResult?.type === 'matches' ? parsedResult.data.matches : undefined,
        suggestions: result.suggested_actions?.map((s) => s.label),
        next_actions: result.suggested_actions?.map((s) => s.action),
      }

      addAIMessage(aiMessage)

    } catch (error) {
      console.error('Chat error:', error)
      addErrorMessage(t('conversation.sorryError'))
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * 异步加载匹配结果
   */
  const loadMatchesAsync = async () => {
    try {
      setIsLoading(true)
      const userId = authStorage.getUserId()
      const response = await deerflowClient.chat('帮我找对象', `her-match-${userId || 'anonymous'}`)

      // 解析 Agent 返回的结构化数据
      const parsedResult = deerflowClient.parseToolResult(response)

      const matchMessage: Message = {
        id: `ai-match-${Date.now()}`,
        type: 'ai',
        content: response.ai_message || '为你找到以下匹配对象~',
        matches: parsedResult?.type === 'matches' ? parsedResult.data.matches : undefined,
        timestamp: new Date(),
      }
      addAIMessage(matchMessage)
    } catch (error) {
      console.error('Async match loading failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * 判断 AI 消息是否需要信息收集兜底
   *
   * 当 DeerFlow Agent 返回纯文本但暗示需要收集信息时，
   * 主动调用 Her API 获取结构化问题卡片
   */
  const _needsProfileCollection = (aiMessage: string): boolean => {
    const indicators = [
      '了解一些基本信息',
      '先了解一下',
      '需要先了解',
      '告诉我几个关键信息',
      '收集一些信息',
      '了解你的需求',
    ]
    return indicators.some(indicator => aiMessage.includes(indicator))
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
  // 使用统一的 GENERATIVE_UI_SCHEMA 映射（与后端 generative_ui_schema.py 同步）
  const mapComponentTypeToGenerativeCard = (componentType: string): Message['generativeCard'] | undefined => {
    const frontendCard = getFrontendCard(componentType)
    // 如果 frontend_card 为 null（SimpleResponse），返回 undefined
    // 如果 frontend_card 不存在（未注册），返回 undefined 并打印警告
    if (frontendCard === null) {
      return undefined
    }
    if (!frontendCard && componentType !== 'SimpleResponse' && componentType !== 'AIResponseCard') {
      console.warn(`[GenerativeUI] 未知的 component_type: ${componentType}，请在 generativeUI.ts 中注册`)
    }
    return frontendCard as Message['generativeCard'] | undefined
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 🚀 [性能优化] 使用 useCallback 防止每次渲染重新创建函数
  const handleQuickAction = useCallback((action: string) => {
    // 🎯 [AI Native] 特殊意图拦截：流程入口不走 DeerFlow，直接触发本地流程
    // 这样可以避免 DeerFlow 把"开始"当成普通消息处理，导致交互断裂
    const specialActions = [
      t('conversation.startChat'),  // "开始"
      '开始',
      'start',
      'Start',
    ]

    if (specialActions.includes(action)) {
      // 直接触发信息收集流程
      setIsLoading(true)
      handleQuickStartStep('')
      return
    }

    // 普通意图：发送给 DeerFlow 处理
    handleSend(action)
  }, [handleSend, handleQuickStartStep, t])

  // 查看预沟通对话消息（由 PreCommunicationSessionCard 组件调用）
  const handleViewPreCommunicationMessages = async (sessionId: string) => {
    try {
      setIsLoading(true)
      // 使用 DeerFlow Agent 获取预沟通对话历史
      const userId = authStorage.getUserId()
      const result = await deerflowClient.chat(
        `查看预沟通会话 ${sessionId} 的对话历史`,
        `her-precomm-${userId}`
      )

      if (!result.success) {
        throw new Error(result.ai_message || '获取对话历史失败')
      }

      const messages = result.tool_result?.data?.messages || []

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
        content: t('conversation.connectionFailed'),
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
      content: t('conversation.connectingTo', { name: partnerName }),
      timestamp: new Date(),
      suggestions: [t('conversation.openChatRoom')],
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

          {/* Generative UI: 匹配卡片列表 */}
          {message.generativeCard === 'match' && message.generativeData && (
            <div className="generative-ui-container match-card-container">
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <MatchCardList
                  matches={(message.generativeData as any).matches || []}
                  onAction={(action) => {
                    if (action.type === 'view_profile') {
                      // TODO: 跳转到用户详情页
                      console.log('View profile:', action.match)
                    } else if (action.type === 'start_chat') {
                      // TODO: 开始聊天
                      console.log('Start chat:', action.match)
                    }
                  }}
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
              <Suspense fallback={<SkeletonComponents.featureCard />}>
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
              <Suspense fallback={<SkeletonComponents.questionCard />}>
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
                  // 🔧 [修复] 必须传递 user_id，否则数据会保存到错误的用户
                  const userId = authStorage.getUserId()
                  const result = await profileApi.submitAnswer({
                    dimension,
                    answer: value,
                    depth,
                    user_id: userId,  // ✅ 关键修复：传递正确的用户 ID
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
              <Suspense fallback={<SkeletonComponents.questionCard />}>
                <ProfileQuestionCard
                  question={(message.generativeData as any).question}
                  questionType={(message.generativeData as any).question_type}
                  options={(message.generativeData as any).options}
                  dimension={(message.generativeData as any).dimension}
                  depth={0}
                  optional={(message.generativeData as any).optional || false}
                  onAnswer={async (dimension, value) => {
                    // 处理 QuickStart 回答
                    await handleQuickStartAnswer(dimension, value)
                  }}
                  onSkip={async (dimension) => {
                    // 处理跳过：直接进入下一步
                    console.log(`[QuickStart] 用户跳过了: ${dimension}`)
                    // 移除当前问题卡片，继续下一个问题
                    setMessages(prev => prev.filter(m => m.id !== message.id))
                    // 触发下一个问题
                    setTimeout(() => {
                      handleQuickStartStep('')
                    }, 300)
                  }}
                />
              </Suspense>
            </div>
          )}

          {/* 用户详情卡片 - UserProfileCard */}
          {message.generativeCard === 'user_profile' && message.generativeData && (
            <div className="generative-ui-container">
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <UserProfileCard
                  {...(message.generativeData as any)}
                  onStartChat={(userId: string) => {
                    // 开始对话 - 跳转到聊天室
                    const userName = (message.generativeData as any)?.name || 'TA'
                    onOpenChatRoom?.(userId, userName)
                  }}
                  onViewProfile={(userId: string) => {
                    // 查看详情 - 可以跳转到用户详情页
                    console.log(`[UserProfileCard] 查看用户详情: ${userId}`)
                    // 可以添加导航逻辑
                  }}
                />
              </Suspense>
            </div>
          )}

          {/* 匹配结果卡片 */}
          {message.matches && message.matches.length > 0 && (
            <div className="match-cards">
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                {t('conversation.foundMatches', { count: message.matches.length })}
              </Text>
              <div className="match-cards-container">
                {message.matches.slice(0, 3).map((match, index) => {
                  // 使用稳定的 key 避免不必要的重新渲染
                  const matchKey = match.user?.id || match.user_id || `match-${index}`
                  return (
                    <div key={matchKey} className="match-card-wrapper">
                      {/* 🚀 [性能优化] Suspense 包裹懒加载的 MatchCard */}
                      <Suspense fallback={<SkeletonComponents.matchCard />}>
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
  }, [onMatchSelect, handleQuickAction, handleQuickStartAnswer, HerAvatar, onOpenChatRoom])

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
              {t('conversation.herThinking')}
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
          placeholder={t('conversation.inputPlaceholder')}
          prefix={<HeartFilled style={{ color: '#FF8FAB' }} />}
          suffix={
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => handleSend()}
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
