// AI Native Chat 组件 - 对话式交互核心

import React, { useState, useRef, useEffect, useCallback, lazy, Suspense, useMemo, memo } from 'react'
import { Input, Button, Card, Avatar, Spin, Tag, Space, Typography, message as antdMessage, Drawer, Divider } from 'antd'
import { UserOutlined, ThunderboltOutlined, HeartFilled, SendOutlined, EnvironmentOutlined, MessageOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate, AIPreCommunicationSession } from '../types'
import { getFrontendCard, GENERATIVE_UI_SCHEMA } from '../types/generativeUI'
import { aiAwarenessApi } from '../api'
import { deerflowClient } from '../api/deerflowClient'
import { authStorage, registrationStorage, chatStorage } from '../utils/storage'
import type { UserInfo, StoredMessage } from '../utils/storage'
import profileApi from '../api/profileApi'
import { buildChatWebSocketUrl } from '../services/websocket'
import { formatChatReplyReadability } from '../utils/formatChatReplyReadability'
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

/**
 * 🚀 [新增] 从流式累积内容中提取纯文本
 * 过滤掉 JSON、工具调用描述等非自然语言内容
 *
 * Agent Native 架构：中间过程不应该暴露给用户
 * - 过滤 {"success": ...} 格式的 JSON
 * - 过滤 [GENERATIVE_UI] 标签
 * - 过滤工具调用描述（如 "调用 her_find_candidates"）
 * - 保留 AI 的自然语言输出（如"为你找到以下匹配对象"）
 */
const extractNaturalLanguageText = (content: string): string => {
  if (!content) return ''

  let cleanContent = content

  // 1. 移除工具返回的 JSON（{"success": true/false, ...}）
  const toolJsonRegex = /\{"success":\s*(true|false)[^}]*\}/g
  cleanContent = cleanContent.replace(toolJsonRegex, '')

  // 2. 移除 [GENERATIVE_UI] 标签及其内容
  const generativeUiRegex = /\[GENERATIVE_UI\][\s\S]*?\[\/GENERATIVE_UI\]/g
  cleanContent = cleanContent.replace(generativeUiRegex, '')

  // 3. 移除工具调用描述（常见模式）
  const toolCallPatterns = [
    /调用\s+\w+_?\w*\s+工具/g,  // "调用 her_find_candidates 工具"
    /正在调用\s+\w+/g,  // "正在调用 her_find_candidates"
    /工具返回：[\s\S]*?(?=\n\n|\n[A-Z])/g,  // "工具返回：..."
    /Tool\s+call:\s+\w+/gi,  // "Tool call: her_find_candidates"
  ]
  for (const pattern of toolCallPatterns) {
    cleanContent = cleanContent.replace(pattern, '')
  }

  // 4. 移除 markdown JSON 代码块
  const jsonBlockRegex = /```json[\s\S]*?```/g
  cleanContent = cleanContent.replace(jsonBlockRegex, '')

  // 5. 清理多余空行；只合并空格/制表符（不要用 \s，否则会吃掉模型输出的换行）
  cleanContent = cleanContent
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()

  // 6. 可读性：在总起句、列表等处补换行（与气泡内 white-space: pre-wrap 配合）
  cleanContent = formatChatReplyReadability(cleanContent)

  // 7. 如果清理后内容过短（< 10 字符），可能是纯 JSON，返回空
  if (cleanContent.length < 10) {
    return ''
  }

  return cleanContent
}

// 🚀 [性能优化] 懒加载大型组件，减少初始 bundle 大小
const MatchCard = lazy(() => import('./MatchCard'))
const MatchCardList = lazy(() => import('./generative-ui/MatchComponents').then(m => ({ default: m.MatchCardList })))
const FeatureCardRenderer = lazy(() => import('./FeatureCards').then(m => ({ default: m.FeatureCardRenderer })))
const ProfileQuestionCard = lazy(() => import('./ProfileQuestionCard'))
const PreCommunicationSessionCard = lazy(() => import('./PreCommunicationSessionCard'))
const PreCommunicationDialogCard = lazy(() => import('./PreCommunicationDialogCard'))
const UserProfileCard = lazy(() => import('./UserProfileCard'))
const MembershipSubscribeModal = lazy(() => import('./MembershipSubscribeModal'))
const ChatInitiationCard = lazy(() => import('./generative-ui/ChatComponents').then(m => ({ default: m.ChatInitiationCard })))

// 🚀 [性能优化] 导入公共骨架屏组件（从 skeletons.tsx 提取）
import { SkeletonComponents } from './skeletons'

// 🚀 [流式进度] 根据事件内容推断当前进度
const inferProgressStep = (event: any): string => {
  // 根据工具调用推断进度
  if (event.data?.tool_call?.name === 'her_find_candidates') {
    return '正在查询候选人...'
  }
  if (event.data?.tool_call?.name === 'her_get_profile') {
    return '正在获取用户信息...'
  }
  if (event.data?.tool_result?.candidates) {
    return '正在分析匹配度...'
  }
  if (event.data?.ai_content && event.data?.ai_content.length > 50) {
    return '正在生成推荐...'
  }
  // 默认进度文字
  return ''
}

const { Text, Paragraph, Title } = Typography

// 关系目标中英文映射
/** 从列表卡片/嵌套 user 归一化详情弹窗所需字段（推荐理由、共同点等） */
function normalizeMatchProfileForDetail(userData?: Record<string, any>) {
  if (!userData || typeof userData !== 'object') return null
  const nested = userData.user && typeof userData.user === 'object' ? userData.user : {}
  const rawReasons = userData.match_reasons ?? nested.match_reasons
  const match_reasons = Array.isArray(rawReasons)
    ? rawReasons.filter((x: unknown) => typeof x === 'string' && (x as string).trim()).map((x: string) => (x as string).trim())
    : []
  const reasoning =
    (typeof userData.reasoning === 'string' && userData.reasoning.trim()) ||
    (typeof userData.ai_reasoning === 'string' && userData.ai_reasoning.trim()) ||
    (typeof nested.reasoning === 'string' && nested.reasoning.trim()) ||
    ''
  const rawCommon = userData.common_interests ?? nested.common_interests
  const common_interests = Array.isArray(rawCommon)
    ? rawCommon.filter((x: unknown) => typeof x === 'string' && (x as string).trim()) as string[]
    : []
  const uid =
    userData.user_id ||
    nested.id ||
    nested.user_id ||
    userData.id ||
    ''
  let scoreRaw: unknown = userData.compatibility_score ?? userData.score ?? nested.compatibility_score
  if (typeof scoreRaw === 'string' && scoreRaw.trim()) {
    const p = parseFloat(scoreRaw)
    scoreRaw = Number.isNaN(p) ? undefined : p
  }
  let compatibility_score: number | undefined
  if (typeof scoreRaw === 'number' && !Number.isNaN(scoreRaw)) {
    compatibility_score = scoreRaw > 0 && scoreRaw <= 1 ? Math.round(scoreRaw * 100) : Math.round(scoreRaw)
  }
  return {
    userId: String(uid),
    name: userData.name || nested.name || '匿名用户',
    age: userData.age ?? nested.age ?? 0,
    location: userData.location || nested.location || '',
    avatar_url: userData.avatar_url || nested.avatar_url || nested.avatar,
    interests: (Array.isArray(userData.interests) ? userData.interests : nested.interests) || [],
    bio: userData.bio || nested.bio,
    relationship_goal: userData.relationship_goal || nested.relationship_goal || nested.goal,
    confidence_level: userData.confidence_level || nested.confidence_level,
    confidence_score: userData.confidence_score ?? nested.confidence_score,
    occupation: userData.occupation || nested.occupation,
    education: userData.education || nested.education,
    income: userData.income ?? nested.income,
    income_range: userData.income_range || nested.income_range,
    match_reasons,
    is_same_city: userData.is_same_city ?? nested.is_same_city,
    reasoning,
    common_interests,
    compatibility_score,
  }
}

const RELATIONSHIP_GOAL_MAP: Record<string, string> = {
  serious: '认真恋爱',
  marriage: '奔着结婚',
  dating: '轻松交友',
  casual: '随便聊聊',
}

/**
 * 从 Agent/工具返回的多种结构里解析目标用户 ID。
 * 后端 get_db_user 使用 `id`；部分工具另含 `user_id`；仅传 user_profile 时 ID 只在嵌套对象上。
 *
 * 🔧 [修复] 增加调试日志，记录数据结构和提取过程
 */
function pickTargetUserIdFromGenerativeData(data: any): string {
  if (!data || typeof data !== 'object') {
    console.warn('[pickTargetUserId] 数据无效:', data)
    return ''
  }

  // 🔧 [调试] 记录数据结构
  console.log('[pickTargetUserId] 数据结构:', {
    hasSelectedUser: !!data.selected_user,
    hasUserProfile: !!data.user_profile,
    hasTargetProfile: !!data.target_profile,
    hasUserId: !!data.user_id,
    hasId: !!data.id,
    topLevelKeys: Object.keys(data).slice(0, 10),
  })

  const sel = data.selected_user
  const prof = data.user_profile
  const tgt = data.target_profile

  // 🔧 [修复] 扩展字段检查顺序，优先检查更常见的字段
  const raw =
    sel?.user_id ?? sel?.id ??
    prof?.user_id ?? prof?.id ??
    tgt?.user_id ?? tgt?.id ??
    data.user_id ?? data.id  // 🔧 [新增] 检查顶层 id 字段

  console.log('[pickTargetUserId] 提取结果:', raw)

  if (raw == null || raw === '') {
    console.warn('[pickTargetUserId] 无法提取 user_id，数据:', JSON.stringify(data).slice(0, 200))
    return ''
  }
  const s = String(raw).trim()
  return s === 'undefined' || s === 'null' ? '' : s
}

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
  generativeCard?: 'precommunication' | 'precommunication-dialog' | 'match' | 'analysis' | 'feature' | 'profile_question' | 'quick_start' | 'learning_confirmation' | 'user_profile' | 'chat_initiation' | 'compatibility'
  generativeData?: unknown
  featureAction?: string
}

// 🚀 [性能优化] memoized 消息包装组件，避免未变化消息重渲染
interface MessageWrapperProps {
  message: Message
  renderContent: (message: Message) => React.ReactNode
}

const MessageWrapper = memo(({ message, renderContent }: MessageWrapperProps) => {
  return (
    <div className="message-wrapper">
      {renderContent(message)}
    </div>
  )
}, (prevProps, nextProps) => {
  // 自定义比较函数：只比较关键属性
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.generativeCard === nextProps.message.generativeCard &&
    prevProps.message.generativeData === nextProps.message.generativeData &&
    prevProps.renderContent === nextProps.renderContent
  )
})

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
 * 检查用户对象是否包含所有 QuickStart 必填字段
 * 🔧 [修复] 只检查 QUICKSTART_REQUIRED_FIELDS（6 个核心字段），而非全部字段
 * QuickStart 阶段只收集：name, age, gender, location, want_children, spending_style
 * 其他字段（height, education, occupation 等）在后续对话中延迟收集
 */
const checkUserFieldsComplete = (user: UserInfo | null | undefined): boolean => {
  if (!user) return false

  // ===== QuickStart 核心必填字段（6 个）=====
  // 注册表单收集：name, age, gender, location
  if (!user.name) return false
  if (!user.age) return false
  if (!user.gender) return false
  if (!user.location) return false

  // 一票否决维度（QuickStart 必须收集）
  if (!user.want_children) return false
  if (!user.spending_style) return false

  // ===== 延迟收集的字段不检查 =====
  // 这些字段在后续对话中触发收集：
  // - height, education, occupation, income, housing, has_car
  // - family_importance, work_life_balance, migration_willingness, accept_remote, sleep_type

  return true
}

// 🎯 [改进] 字段收集策略：核心字段优先，其他字段延迟收集
// 核心字段：注册必须，影响基本匹配
// 延迟字段：可在后续对话中触发收集

// QuickStart 字段分组
const QUICKSTART_FIELD_GROUPS = {
  // 第一组：核心必填（必须先收集）
  core: {
    name: '核心信息',
    fields: ['name', 'age', 'gender', 'location'],
  },
  // 第二组：一票否决维度（重要，但可以稍后）
  veto: {
    name: '重要偏好',
    fields: ['want_children', 'spending_style'],
  },
  // 第三组：基础属性（可延迟）
  attributes: {
    name: '个人属性',
    fields: ['height', 'education', 'occupation', 'income', 'housing', 'has_car'],
  },
  // 第四组：生活方式（最不重要，可延迟）
  lifestyle: {
    name: '生活方式',
    fields: ['family_importance', 'work_life_balance', 'accept_remote', 'sleep_type'],
  },
  // 第五组：迁移相关（最可延迟，等用户表达异地意向时再问）
  migration: {
    name: '迁移意愿',
    fields: ['migration_willingness'],
    delayed: true,  // 标记为延迟收集
  },
}

// 🎯 [新增] QuickStart 阶段只收集这些字段（精简流程）
const QUICKSTART_REQUIRED_FIELDS = [
  // 核心信息
  'name', 'age', 'gender', 'location',
  // 一票否决（重要）
  'want_children', 'spending_style',
]

// 🎯 [新增] 延迟收集的字段（后续触发）
const DELAYED_FIELDS = [
  'height', 'education', 'occupation', 'income', 'housing', 'has_car',
  'family_importance', 'work_life_balance', 'accept_remote', 'sleep_type',
  'migration_willingness',
]

/**
 * 🎯 [改进] 获取缺失字段（QuickStart 阶段只返回核心字段）
 * 分为：当前必须收集 + 延迟收集
 */
const getMissingInfoFields = (): { required: string[], delayed: string[], all: string[] } => {
  const user = authStorage.getUser()
  const required: string[] = []
  const delayed: string[] = []

  // ===== QuickStart 必须收集的核心字段 =====
  if (!user?.name) required.push('name')
  if (!user?.age) required.push('age')
  if (!user?.gender) required.push('gender')
  if (!user?.location) required.push('location')

  // ===== 一票否决维度（QuickStart 也需要）=====
  if (!user?.want_children) required.push('want_children')
  if (!user?.spending_style) required.push('spending_style')

  // ===== 延迟收集的字段 =====
  if (!user?.height) delayed.push('height')
  if (!user?.education) delayed.push('education')
  if (!user?.occupation) delayed.push('occupation')
  if (!user?.income) delayed.push('income')
  if (!user?.housing) delayed.push('housing')
  if (!user?.has_car && user?.has_car !== false) delayed.push('has_car')
  if (!user?.family_importance && user?.family_importance !== 0) delayed.push('family_importance')
  if (!user?.work_life_balance) delayed.push('work_life_balance')
  if (!user?.migration_willingness && user?.migration_willingness !== 0) delayed.push('migration_willingness')
  if (!user?.accept_remote && user?.accept_remote !== false) delayed.push('accept_remote')
  if (!user?.sleep_type) delayed.push('sleep_type')

  return {
    required,      // QuickStart 必须收集
    delayed,       // 延迟收集
    all: [...required, ...delayed],  // 所有缺失字段
  }
}

/**
 * 🎯 [兼容] 保留原函数用于其他逻辑
 */
const getMissingInfoFieldsLegacy = (): string[] => {
  const result = getMissingInfoFields()
  return result.all
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

  // 🔧 [状态持久化] 从 localStorage 加载消息，避免页面切换时丢失
  const [messages, setMessages] = useState<Message[]>(() => {
    const userId = authStorage.getUserId()
    const storedMessages = chatStorage.getMessages(userId)

    // 如果有存储的消息，恢复（转换 timestamp 格式）
    if (storedMessages.length > 0) {
      return storedMessages.map(msg => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })) as Message[]
    }

    // 没有存储的消息，使用欢迎消息
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
  const [loadingStep, setLoadingStep] = useState<string>('')  // 动态进度提示
  const [showMatchSkeleton, setShowMatchSkeleton] = useState(false)  // 骨架屏预览
  const [streamingMessage, setStreamingMessage] = useState<string>('')  // 流式输出内容
  const [quickTags, setQuickTags] = useState<QuickTag[]>([])  // 动态快捷标签
  const [progressStepIndex, setProgressStepIndex] = useState<number>(0)  // 🚀 [场景3方案3] 当前进度步骤索引（0-查询/1-分析/2-推荐）

  // 用户详情弹窗状态
  const [userDetailVisible, setUserDetailVisible] = useState(false)
  const [selectedUserDetail, setSelectedUserDetail] = useState<{
    userId: string
    name: string
    age: number
    location: string
    avatar_url?: string
    interests?: string[]
    bio?: string
    relationship_goal?: string
    confidence_level?: string
    confidence_score?: number
    occupation?: string
    education?: string
    income?: number
    income_range?: string
    match_reasons?: string[]
    is_same_city?: boolean
    /** Agent / 工具给出的自然语言推荐理由 */
    reasoning?: string
    /** 与当前用户的共同兴趣（若后端提供） */
    common_interests?: string[]
    /** 匹配度 0–100（已归一化） */
    compatibility_score?: number
  } | null>(null)

  // 打开用户详情弹窗
  const handleViewUserProfile = useCallback((userId: string, userData?: any) => {
    const normalized = normalizeMatchProfileForDetail(userData)
    const resolvedId = (normalized?.userId || userId || '').trim()
    if (!resolvedId || resolvedId === 'undefined' || resolvedId === 'null') {
      console.warn('[handleViewUserProfile] userId 无效:', userId, 'userData:', userData)
      antdMessage.warning('无法获取用户信息，请稍后重试')
      return
    }

    if (normalized) {
      setSelectedUserDetail({
        userId: resolvedId,
        name: normalized.name,
        age: normalized.age,
        location: normalized.location,
        avatar_url: normalized.avatar_url,
        interests: normalized.interests,
        bio: normalized.bio,
        relationship_goal: normalized.relationship_goal,
        confidence_level: normalized.confidence_level,
        confidence_score: normalized.confidence_score,
        occupation: normalized.occupation,
        education: normalized.education,
        income: normalized.income,
        income_range: normalized.income_range,
        match_reasons: normalized.match_reasons,
        is_same_city: normalized.is_same_city,
        reasoning: normalized.reasoning,
        common_interests: normalized.common_interests,
        compatibility_score: normalized.compatibility_score,
      })
    } else {
      setSelectedUserDetail({
        userId: resolvedId,
        name: userData?.name || '匿名用户',
        age: userData?.age || 0,
        location: userData?.location || '',
        avatar_url: userData?.avatar_url,
        interests: userData?.interests || [],
        bio: userData?.bio,
        relationship_goal: userData?.relationship_goal,
        confidence_level: userData?.confidence_level,
        confidence_score: userData?.confidence_score,
        occupation: userData?.occupation,
        education: userData?.education,
        income: userData?.income,
        income_range: userData?.income_range,
        match_reasons: userData?.match_reasons || [],
        is_same_city: userData?.is_same_city,
      })
    }
    setUserDetailVisible(true)
  }, [])

  // 关闭用户详情弹窗
  const handleCloseUserDetail = useCallback(() => {
    setUserDetailVisible(false)
    setSelectedUserDetail(null)
  }, [])

  // thread_id 用于 DeerFlow 对话上下文持久化
  const [threadId, setThreadId] = useState<string>(() => {
    const userId = authStorage.getUserId()
    return `her-${userId}-${Date.now()}`
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  /** 异步推荐理由轮询：同一 query_request_id 只跑一轮，完成后清定时器并可用 sessionStorage 命中即停 */
  const asyncReasonPollRef = useRef<
    Map<string, { phase: 'polling' | 'done'; timeoutId?: ReturnType<typeof window.setTimeout> }>
  >(new Map())

  useEffect(() => {
    return () => {
      asyncReasonPollRef.current.forEach((v) => {
        if (v.timeoutId) window.clearTimeout(v.timeoutId)
      })
      asyncReasonPollRef.current.clear()
    }
  }, [])

  // 新用户信息收集状态
  const [collectingStep, setCollectingStep] = useState<number>(() => {
    if (!isNewUser) return -1  // 不需要收集
    const { required } = getMissingInfoFields()  // 🎯 [改进] 只检查核心字段
    return required.length > 0 ? 0 : -1  // 0 表示开始收集
  })

  // 会员订阅 Modal 状态
  const [membershipModalOpen, setMembershipModalOpen] = useState(false)

  // 🔧 [状态持久化] 消息变化时保存到 localStorage
  useEffect(() => {
    const userId = authStorage.getUserId()
    // 转换为 StoredMessage 格式（timestamp 转为 string）
    const toStore: StoredMessage[] = messages.map(msg => ({
      ...msg,
      timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : String(msg.timestamp),
    }))
    chatStorage.setMessages(userId, toStore)
  }, [messages])

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
   * 🎯 [改进] 流程设计：
   * 1. 如果核心字段不完整 → 收集缺失的核心字段（SelfProfile 核心）
   * 2. 如果核心字段完整 → 显示引导消息，让用户开始匹配
   * 3. 延迟字段在后续对话中触发收集
   *
   * 🎯 [改进] QuickStart 阶段只收集 6 个核心字段：
   * - name, age, gender, location（基础信息）
   * - want_children, spending_style（一票否决）
   */
  // 🚀 [性能优化] 使用 useCallback，依赖 collectingStep（其他 state setter 是稳定的）
  const handleQuickStartStep = useCallback(async (userInput: string) => {
    const user = authStorage.getUser()
    const { required, delayed } = getMissingInfoFields()  // 🎯 [改进] 分离核心和延迟字段

    // ===== 场景1：核心字段不完整，需要收集 =====
    if (required.length > 0) {
      // 根据缺失字段生成对应的问题卡片
      const nextMissing = required[collectingStep]  // 🎯 [改进] 只遍历核心字段
      if (nextMissing && collectingStep >= 0) {
        // 🎯 [新增] 计算进度信息
        const groupInfo = getFieldGroupInfo(nextMissing)
        const progressInfo = {
          current: collectingStep + 1,
          total: required.length,
          group: groupInfo?.group,
        }

        // 生成问题卡片（带进度信息）
        const questionCard = generateQuickStartQuestionCard(nextMissing, progressInfo)

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
   * 🎯 [改进] 根据缺失字段生成问题卡片（带进度信息）
   *
   * SelfProfile 收集（用户本身是什么样的）
   *
   * 数据来源分类：
   * - 注册表单：姓名、年龄、性别、所在地
   * - QuickStart 核心：生育意愿、消费观念（一票否决）
   * - QuickStart 延迟：身高、学历、职业、收入、房产、车、价值观等
   *
   * 🎯 [改进] QuickStart 阶段只收集核心字段（6 个），其他字段延迟收集
   */
  const generateQuickStartQuestionCard = (field: string, progressInfo?: {
    current: number
    total: number
    group?: string
  }): {
    question: string
    subtitle?: string  // 问题副标题（解释重要性）
    question_type: 'single_choice' | 'input' | 'tags'
    options: { value: string; label: string; icon?: string }[]
    dimension: string
    optional?: boolean  // 标记是否为可选字段
    veto_dimension?: boolean  // 标记是否为一票否决维度
    progress?: { current: number; total: number; group?: string }  // 🎯 [新增] 进度信息
    showQuickFill?: boolean  // 🎯 [新增] 是否显示快速填表按钮
  } => {
    // 🎯 [新增] 基础返回结构（包含进度信息）
    const baseReturn = {
      progress: progressInfo,
      showQuickFill: progressInfo && progressInfo.current >= 2 && progressInfo.total > 4,  // 第2个问题后显示快速填表
    }
    switch (field) {
      // ===== 注册表单基础字段 =====
      case 'name':
        return {
          ...baseReturn,
          question: t('conversation.qsName'),
          question_type: 'input',
          options: [],
          dimension: 'name',
          optional: false,
        }
      case 'age':
        return {
          ...baseReturn,
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
          ...baseReturn,
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
          ...baseReturn,
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

      // ===== QuickStart 属性字段（延迟收集）=====
      case 'height':
        return {
          ...baseReturn,
          question: t('conversation.qsHeight'),
          question_type: 'input',
          options: [],
          dimension: 'height',
          optional: true,  // 🎯 [改进] 延迟收集，标记为可选
        }
      case 'occupation':
        return {
          ...baseReturn,
          question: t('conversation.qsOccupation'),
          question_type: 'input',
          options: [],
          dimension: 'occupation',
          optional: true,
        }
      case 'income':
        return {
          ...baseReturn,
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
          optional: true,
        }
      case 'education':
        return {
          ...baseReturn,
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
          optional: true,
        }
      case 'housing':
        return {
          ...baseReturn,
          question: t('conversation.qsHousing'),
          question_type: 'single_choice',
          options: [
            { value: 'own', label: t('conversation.qsHousingOption.own') },
            { value: 'rent', label: t('conversation.qsHousingOption.rent') },
            { value: 'with_parents', label: t('conversation.qsHousingOption.with_parents') },
          ],
          dimension: 'housing',
          optional: true,
        }
      case 'has_car':
        return {
          ...baseReturn,
          question: t('conversation.qsHasCar'),
          question_type: 'single_choice',
          options: [
            { value: 'yes', label: t('conversation.qsHasCarOption.yes'), icon: '🚗' },
            { value: 'no', label: t('conversation.qsHasCarOption.no'), icon: '🚶' },
          ],
          dimension: 'has_car',
          optional: true,
        }

      // ===== 一票否决维度（最高优先级）=====
      case 'want_children':
        return {
          ...baseReturn,
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
          ...baseReturn,
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

      // ===== 核心价值观维度（延迟收集）=====
      case 'family_importance':
        return {
          ...baseReturn,
          question: t('conversation.qsFamilyImportance'),
          question_type: 'single_choice',
          options: [
            { value: 'very_high', label: t('conversation.qsFamilyImportanceOption.very_high'), icon: '👨‍👩‍👧‍👦' },
            { value: 'high', label: t('conversation.qsFamilyImportanceOption.high'), icon: '🏠' },
            { value: 'medium', label: t('conversation.qsFamilyImportanceOption.medium'), icon: '🏡' },
            { value: 'low', label: t('conversation.qsFamilyImportanceOption.low'), icon: '🌱' },
          ],
          dimension: 'family_importance',
          optional: true,  // 🎯 [改进] 延迟收集
        }
      case 'work_life_balance':
        return {
          ...baseReturn,
          question: t('conversation.qsWorkLifeBalance'),
          question_type: 'single_choice',
          options: [
            { value: 'work_first', label: t('conversation.qsWorkLifeBalanceOption.work_first'), icon: '💼' },
            { value: 'balance', label: t('conversation.qsWorkLifeBalanceOption.balance'), icon: '⚖️' },
            { value: 'life_first', label: t('conversation.qsWorkLifeBalanceOption.life_first'), icon: '🌴' },
          ],
          dimension: 'work_life_balance',
          optional: true,
        }

      // ===== 迁移能力维度（最可延迟，等用户表达异地意向时再问）=====
      case 'migration_willingness':
        return {
          ...baseReturn,
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
          optional: true,  // 🎯 [改进] 最可延迟
        }
      case 'accept_remote':
        return {
          ...baseReturn,
          question: t('conversation.qsAcceptRemote'),
          question_type: 'single_choice',
          options: [
            { value: 'yes', label: t('conversation.qsAcceptRemoteOption.yes'), icon: '❤️' },
            { value: 'conditional', label: t('conversation.qsAcceptRemoteOption.conditional'), icon: '🤝' },
            { value: 'no', label: t('conversation.qsAcceptRemoteOption.no'), icon: '📍' },
          ],
          dimension: 'accept_remote',
          optional: true,  // 🎯 [改进] 延迟收集
        }

      // ===== 生活方式维度（延迟收集）=====
      case 'sleep_type':
        return {
          ...baseReturn,
          question: t('conversation.qsSleepType'),
          question_type: 'single_choice',
          options: [
            { value: 'early', label: t('conversation.qsSleepTypeOption.early'), icon: '🌅' },
            { value: 'normal', label: t('conversation.qsSleepTypeOption.normal'), icon: '☀️' },
            { value: 'late', label: t('conversation.qsSleepTypeOption.late'), icon: '🌙' },
          ],
          dimension: 'sleep_type',
          optional: true,  // 🎯 [改进] 延迟收集
        }

      // ===== 默认 =====
      default:
        return {
          ...baseReturn,
          question: t('conversation.qsMoreInfo'),
          question_type: 'input',
          options: [],
          dimension: field,
          optional: true,
        }
    }
  }

  /**
   * 🎯 [新增] 获取字段所属分组信息
   */
  const getFieldGroupInfo = (field: string): { group: string; groupIndex: number; totalInGroup: number } | undefined => {
    for (const [groupKey, groupConfig] of Object.entries(QUICKSTART_FIELD_GROUPS)) {
      if (groupConfig.fields.includes(field)) {
        // 计算分组索引
        const groups = Object.keys(QUICKSTART_FIELD_GROUPS)
        const groupIndex = groups.indexOf(groupKey) + 1
        return {
          group: groupConfig.name,
          groupIndex,
          totalInGroup: groupConfig.fields.length,
        }
      }
    }
    return undefined
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

      // 🔑 [性能优化] 异步同步用户画像到 DeerFlow Memory
      // 不阻塞界面显示，后台慢慢同步
      // her_tools 直接从数据库查用户信息，不依赖 Memory 同步完成
      deerflowClient.syncMemory()
        .then(() => console.log('[QuickStart] 用户画像已同步到 DeerFlow Memory'))
        .catch(error => console.error('[QuickStart] DeerFlow Memory 同步失败:', error))
      // 不等待，立即继续显示界面

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
      const { required: stillRequired } = getMissingInfoFields()  // 🎯 [改进] 只获取核心字段
      const nextField = stillRequired[0]

      console.log(`[QuickStart] 继续收集，剩余核心字段: ${stillRequired.join(', ')}`)

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

        // 🎯 [新增] 计算进度信息
        const groupInfo = getFieldGroupInfo(nextField)
        const progressInfo = {
          current: stillRequired.length,  // 剩余字段数
          total: QUICKSTART_REQUIRED_FIELDS.length,  // 总核心字段数
          group: groupInfo?.group,
        }

        // 直接生成下一个问题卡片（带进度信息）
        setTimeout(() => {
          const questionCard = generateQuickStartQuestionCard(nextField, progressInfo)
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
    setStreamingMessage('')  // 清空流式内容

    // 检测是否为匹配请求，显示骨架屏预览
    const matchKeywords = ['找对象', '推荐', '看看', '匹配', '候选人', 'today', '今天']
    const isMatchRequest = matchKeywords.some(k => contentToSend.includes(k))
    if (isMatchRequest) {
      setShowMatchSkeleton(true)
    }

    // 动态进度提示：让用户感知系统正在执行
    const loadingSteps = [
      '正在理解你的需求...',
      '正在查询候选人...',
      '正在分析匹配度...',
      '正在生成推荐...',
    ]

    // 启动进度动画（每隔 800ms 更换提示文字）
    let stepIndex = 0
    setLoadingStep(loadingSteps[stepIndex])
    const stepInterval = setInterval(() => {
      stepIndex = (stepIndex + 1) % loadingSteps.length
      setLoadingStep(loadingSteps[stepIndex])
    }, 800)

    // 追踪聊天消息行为
    const userId = authStorage.getUserId()
    if (userId) {
      aiAwarenessApi.trackChatMessage(userId, 'system', contentToSend.length).catch(() => {})
    }

    try {
      // 2. 使用流式 API（方案 3：流式输出）
      // 预先添加一个空的 AI 消息占位，用于流式填充内容
      const streamingMessageId = `ai-streaming-${Date.now()}`
      const streamingMessagePlaceholder: Message = {
        id: streamingMessageId,
        type: 'ai',
        content: '',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, streamingMessagePlaceholder])

      // 🚀 [性能优化] 流式节流：减少 setMessages 调用频率
      let accumulatedContent = ''
      let lastUpdateTime = 0
      const UPDATE_INTERVAL = 500  // 每 500ms 更新一次 UI（大幅减少重渲染）

      // 调用 DeerFlow 流式 API
      await deerflowClient.stream(contentToSend, `her-chat-${userId || 'anonymous'}`, (event) => {
        // 处理流式事件
        if (event.type === 'messages-tuple') {
          // 🔧 [修复] 流式过程中不显示中间文本（JSON等），只保持加载状态
          // Agent Native 架构：中间过程不应该暴露给用户
          // AI 的思考过程、工具调用描述等会在气泡里先显示，然后才变成卡片
          // 修复方案：累积内容但不立即显示，等 generative_ui 事件后再渲染

          // 过滤掉工具返回的原始 JSON（以 {"success" 开头）
          const delta = event.data?.content || ''
          if (delta.startsWith('{"success') || delta.startsWith('{"error')) {
            console.log('[Stream] Filtered tool result:', delta.substring(0, 50))
            return  // 跳过工具返回的 JSON
          }

          // 累积内容，但不更新 UI（保持加载状态）
          accumulatedContent += delta
          console.log('[Stream] Accumulated (hidden):', delta.substring(0, 30))

          // 🚀 [改进] 流式过程中保持进度提示，不显示中间 JSON
          // UI 显示 loadingStep（如"正在分析匹配度..."），而不是原始文本
          const inferredStep = inferProgressStep(event)
          if (inferredStep) {
            setLoadingStep(inferredStep)
            // 🚀 [场景3方案3] 根据进度文字更新进度步骤索引
            if (inferredStep.includes('查询候选人')) {
              setProgressStepIndex(0)
            } else if (inferredStep.includes('分析匹配度') || inferredStep.includes('获取用户')) {
              setProgressStepIndex(1)
            } else if (inferredStep.includes('生成推荐')) {
              setProgressStepIndex(2)
            }
          }

          // 🚀 [关键] 不更新消息气泡内容，避免显示中间 JSON
          // setStreamingMessage 和 setMessages 保持不变，只显示加载状态
        } else if (event.type === 'custom') {
          // 自定义事件（如 generative_ui）
          // 🚀 [关键修复] 收到 generative_ui 时，立即关闭骨架屏并渲染卡片
          if (event.data?.generative_ui) {
            // 🔧 [关键] 关闭骨架屏，显示卡片
            setShowMatchSkeleton(false)
            setIsLoading(false)  // 同时关闭加载状态

            // 提取 AI 的文字描述（如果有）
            // accumulatedContent 可能包含 AI 的自然语言输出（如"为你找到以下匹配对象"）
            const aiTextContent = extractNaturalLanguageText(accumulatedContent)

            setMessages(prev => {
              const idx = prev.findIndex(m => m.id === streamingMessageId)
              if (idx !== -1) {
                const newMessages = [...prev]
                newMessages[idx] = {
                  ...newMessages[idx],
                  // 🔧 [新增] 显示 AI 的文字描述（如果有）
                  content: aiTextContent || '',
                  generativeCard: mapComponentTypeToGenerativeCard(event.data.generative_ui.component_type),
                  generativeData: event.data.generative_ui.props,
                }
                return newMessages
              }
              return prev
            })
            pollAsyncMatchReasons(streamingMessageId, event.data.generative_ui?.props?.query_request_id)
            console.log('[Stream] Rendered generative_ui:', event.data.generative_ui.component_type)
          }

          // 进度更新事件（直接设置）
          if (event.data?.progress_step) {
            setLoadingStep(event.data.progress_step)
          }
        } else if (event.type === 'end') {
          // 流式结束：从原文解析卡片，展示文案走 extractNaturalLanguageText（含换行可读性修复）
          const raw = accumulatedContent || event.data?.ai_message || ''

          const tagRegex = /\[GENERATIVE_UI\]\s*([\s\S]*?)\s*\[\/GENERATIVE_UI\]/g
          const cards: any[] = []
          let match
          while ((match = tagRegex.exec(raw)) !== null) {
            try {
              const cardJson = JSON.parse(match[1].trim())
              cards.push({
                component_type: cardJson.component_type || 'UserProfileCard',
                props: cardJson.props || cardJson,
              })
            } catch (e) {
              console.warn('[Stream] Failed to parse GENERATIVE_UI:', match[1], e)
            }
          }

          const displayText = extractNaturalLanguageText(raw)

          // 更新消息
          setMessages(prev => {
            const idx = prev.findIndex(m => m.id === streamingMessageId)
            if (idx !== -1) {
              const newMessages = [...prev]
              // 使用第一个卡片作为 generativeCard
              const firstCard = cards[0]
              newMessages[idx] = {
                ...newMessages[idx],
                content: displayText || raw.trim(),
                generativeCard: firstCard
                  ? mapComponentTypeToGenerativeCard(firstCard.component_type)
                  : undefined,
                generativeData: firstCard?.props,
                suggestions: event.data?.suggested_actions?.map((s: any) => s.label),
                next_actions: event.data?.suggested_actions?.map((s: any) => s.action),
              }
              return newMessages
            }
            return prev
          })
          const firstCard = cards[0]
          pollAsyncMatchReasons(streamingMessageId, firstCard?.props?.query_request_id)

          // 🚀 [新增] 如果有多个卡片，添加额外消息
          if (cards.length > 1) {
            cards.slice(1).forEach((card, index) => {
              setTimeout(() => {
                const cardMessage: Message = {
                  id: `ai-card-${Date.now()}-${index}`,
                  type: 'ai',
                  content: '',
                  timestamp: new Date(),
                  generativeCard: mapComponentTypeToGenerativeCard(card.component_type),
                  generativeData: card.props,
                }
                setMessages(prev => [...prev, cardMessage])
              }, 100 * index)
            })
          }
        }
      })

    } catch (error) {
      console.error('Chat error:', error)
      // 流式失败，降级到非流式 API
      try {
        const result = await deerflowClient.chat(contentToSend, `her-chat-${userId || 'anonymous'}`)

        // 🚀 [修复] 解析 [GENERATIVE_UI] 标签
        const parsedUI = deerflowClient.parseGenerativeUITags(result)
        const parsedResult = deerflowClient.parseToolResult(result)

        // 如果解析出 GENERATIVE_UI 卡片，渲染第一个卡片
        const firstCard = parsedUI.generative_ui_cards[0]

        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          type: 'ai',
          content: extractNaturalLanguageText(
            parsedUI.natural_message || result.ai_message || '',
          ),
          timestamp: new Date(),
          generativeCard: firstCard
            ? mapComponentTypeToGenerativeCard(firstCard.component_type)
            : result.generative_ui
              ? mapComponentTypeToGenerativeCard(result.generative_ui.component_type)
            : undefined,
          generativeData: firstCard?.props || result.generative_ui?.props,
          matches: parsedResult?.type === 'matches' ? parsedResult.data.matches : undefined,
          suggestions: result.suggested_actions?.map((s) => s.label),
          next_actions: result.suggested_actions?.map((s) => s.action),
        }
        addAIMessage(aiMessage)

        // 🚀 [新增] 如果有多个 GENERATIVE_UI 卡片，添加额外的消息
        if (parsedUI.generative_ui_cards.length > 1) {
          parsedUI.generative_ui_cards.slice(1).forEach((card, index) => {
            const cardMessage: Message = {
              id: `ai-card-${Date.now()}-${index}`,
              type: 'ai',
              content: '',
              timestamp: new Date(),
              generativeCard: mapComponentTypeToGenerativeCard(card.component_type),
              generativeData: card.props,
            }
            addAIMessage(cardMessage)
          })
        }
      } catch (fallbackError) {
        addErrorMessage(t('conversation.sorryError'))
      }
    } finally {
      // 清除进度动画
      clearInterval(stepInterval)
      setIsLoading(false)
      setLoadingStep('')
      setShowMatchSkeleton(false)
      setStreamingMessage('')
      // 🚀 [场景3方案3] 重置进度步骤索引
      setProgressStepIndex(0)
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
        content: extractNaturalLanguageText(
          response.ai_message || '为你找到以下匹配对象~',
        ),
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

  const pollAsyncMatchReasons = useCallback((messageId: string, queryRequestId?: string) => {
    const reqId = (queryRequestId || '').trim()
    if (!reqId) return

    const bucket = asyncReasonPollRef.current.get(reqId)
    if (bucket?.phase === 'done') return
    if (bucket?.phase === 'polling') return

    const maxAttempts = 10
    const pollIntervalMs = 1200
    const cacheKey = `her_match_reasons:${reqId}`

    const finishDone = () => {
      const cur = asyncReasonPollRef.current.get(reqId)
      if (cur?.timeoutId) window.clearTimeout(cur.timeoutId)
      asyncReasonPollRef.current.set(reqId, { phase: 'done' })
    }

    const applyReasonsMap = (reasonsByUserId: Record<string, string[]>) => {
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === messageId)
        if (idx === -1) return prev
        const current = prev[idx]
        const data =
          current.generativeData && typeof current.generativeData === 'object'
            ? { ...current.generativeData }
            : null
        if (!data) return prev
        const rows = Array.isArray(data.matches)
          ? [...data.matches]
          : Array.isArray(data.candidates)
            ? [...data.candidates]
            : null
        if (!rows) return prev

        let changed = false
        const mergedRows = rows.map((row: any) => {
          if (!row || typeof row !== 'object') return row
          const uid = String(row.user_id || row.id || row?.user?.id || row?.user?.user_id || '')
          if (!uid) return row
          const reasons = reasonsByUserId[uid]
          if (!Array.isArray(reasons) || reasons.length === 0) return row
          changed = true
          return {
            ...row,
            match_reasons: reasons,
          }
        })
        if (!changed) return prev

        if (Array.isArray(data.matches)) {
          data.matches = mergedRows
        } else if (Array.isArray(data.candidates)) {
          data.candidates = mergedRows
        }
        const next = [...prev]
        next[idx] = {
          ...current,
          generativeData: data,
        }
        return next
      })
    }

    try {
      const raw = sessionStorage.getItem(cacheKey)
      if (raw) {
        const parsed = JSON.parse(raw) as { reasons_by_user_id?: Record<string, string[]> }
        const cached = parsed?.reasons_by_user_id
        if (cached && typeof cached === 'object' && Object.keys(cached).length > 0) {
          finishDone()
          applyReasonsMap(cached)
          return
        }
      }
    } catch {
      /* ignore */
    }

    asyncReasonPollRef.current.set(reqId, { phase: 'polling' })

    const scheduleNext = (attempt: number) => {
      const cur = asyncReasonPollRef.current.get(reqId)
      if (cur?.timeoutId) window.clearTimeout(cur.timeoutId)
      const tid = window.setTimeout(() => {
        runPoll(attempt + 1)
      }, pollIntervalMs)
      asyncReasonPollRef.current.set(reqId, { phase: 'polling', timeoutId: tid })
    }

    const runPoll = async (attempt: number) => {
      if (asyncReasonPollRef.current.get(reqId)?.phase === 'done') return

      const status = await deerflowClient.getMatchReasonsStatus(reqId)

      if (status.status === 'completed' && status.reasons_by_user_id) {
        const map = status.reasons_by_user_id
        applyReasonsMap(map)
        try {
          sessionStorage.setItem(
            cacheKey,
            JSON.stringify({ reasons_by_user_id: map, updated_at: Date.now() }),
          )
        } catch {
          /* ignore */
        }
        finishDone()
        return
      }

      if (status.status === 'pending' && attempt < maxAttempts) {
        scheduleNext(attempt)
        return
      }

      if (status.status === 'not_found' && attempt < maxAttempts) {
        scheduleNext(attempt)
        return
      }

      finishDone()
    }

    runPoll(1)
  }, [])

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

  /**
   * 🚀 [新增] 处理匹配筛选回调
   * 篮选点击 → 调用 DeerFlow API → 重新查询 → 返回新的精选结果
   *
   * @param messageId - 当前匹配卡片消息的 ID（用于替换数据）
   * @param filters - 篮选条件（地区、年龄、关系目标）
   */
  const handleMatchFilter = useCallback(async (
    messageId: string,
    filters: { location?: string; ageRange?: string; relationshipGoal?: string }
  ) => {
    const userId = authStorage.getUserId()

    // 构建筛选消息
    let filterMessage = '筛选候选人：'
    if (filters.location) {
      filterMessage += ` 地区=${filters.location}`
    }
    if (filters.ageRange) {
      filterMessage += ` 年龄=${filters.ageRange}`
    }
    if (filters.relationshipGoal) {
      filterMessage += ` 目标=${filters.relationshipGoal}`
    }

    console.log('[handleMatchFilter] 篮选条件:', filterMessage)

    // 调用 DeerFlow stream API（带筛选条件）
    await deerflowClient.stream(filterMessage, `her-chat-${userId || 'anonymous'}`, (event) => {
      if (event.type === 'custom' && event.data?.generative_ui) {
        // 收到 generative_ui 时，替换当前消息的数据
        setMessages(prev => {
          const idx = prev.findIndex(m => m.id === messageId)
          if (idx !== -1) {
            const newMessages = [...prev]
            newMessages[idx] = {
              ...newMessages[idx],
              generativeData: event.data.generative_ui.props,
            }
            return newMessages
          }
          return prev
        })
        pollAsyncMatchReasons(messageId, event.data.generative_ui?.props?.query_request_id)
        console.log('[handleMatchFilter] 已更新匹配数据:', event.data.generative_ui.component_type)
      }
    })
  }, [pollAsyncMatchReasons])

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

    // 校验 partnerId
    if (!partnerId) {
      antdMessage.warning('无法获取用户信息，请稍后重试')
      return
    }

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

  // 🚀 [新增] 监听悬浮球快速对话事件
  useEffect(() => {
    const handleQuickChatEvent = (event: CustomEvent<{ message: string }>) => {
      const { message: quickMessage } = event.detail
      // 自动发送消息给 Her
      handleSend(quickMessage)
    }

    window.addEventListener('her-quick-chat', handleQuickChatEvent as EventListener)

    return () => {
      window.removeEventListener('her-quick-chat', handleQuickChatEvent as EventListener)
    }
  }, [])

  // 🚀 [主动性重构 v2] WebSocket 连接 - 接收 Agent 主动消息
  useEffect(() => {
    const userId = authStorage.getUserId()
    if (!userId) return

    // 建立 WebSocket 连接（须走 /api/chat/ws，与 Vite /api 代理及后端 chat 路由一致）
    const wsUrl = buildChatWebSocketUrl(userId)
    let ws: WebSocket | null = null
    let reconnectTimer: NodeJS.Timeout | null = null

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          console.log('[WebSocket] 连接成功，可以接收 Agent 主动消息')
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)

            if (data.type === 'agent_message' && data.data?.is_proactive) {
              // 收到 Agent 主动推送的消息，添加到对话界面
              console.log('[WebSocket] 收到 Agent 主动消息:', data.data.content)

              const proactiveMessage: Message = {
                id: `ai-proactive-${Date.now()}`,
                type: 'ai',
                content: data.data.content,
                timestamp: new Date(),
              }
              setMessages(prev => [...prev, proactiveMessage])

              // 发送确认
              if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                  type: 'ack',
                  message_id: proactiveMessage.id,
                }))
              }
            } else if (data.type === 'pong') {
              // 心跳响应，保持连接
              console.log('[WebSocket] 心跳响应')
            }
          } catch (e) {
            console.warn('[WebSocket] 解析消息失败:', e)
          }
        }

        ws.onerror = (error) => {
          console.warn('[WebSocket] 连接错误:', error)
        }

        ws.onclose = () => {
          console.log('[WebSocket] 连接关闭，5秒后尝试重连')
          // 5秒后重连
          reconnectTimer = setTimeout(connectWebSocket, 5000)
        }
      } catch (e) {
        console.warn('[WebSocket] 创建连接失败:', e)
      }
    }

    // 开始连接
    connectWebSocket()

    // 心跳保活（每30秒发送 ping）
    const pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    // 清理函数
    return () => {
      if (ws) {
        ws.close()
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
      }
      clearInterval(pingInterval)
    }
  }, []) // userId 通过 authStorage.getUserId() 获取，不需要作为依赖

  // 渲染消息内容 - 使用 useMemo 缓存渲染结果
  const renderMessageContent = useCallback((message: Message) => {
    if (message.type === 'user') {
      return (
        <div className="user-message">
          <div className="message-bubble user-bubble">
            <Text style={{ whiteSpace: 'pre-wrap' }}>{message.content}</Text>
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
            <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>
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
          {/* 🚀 [改进 v2] 篮选改为实时查询（而非前端过滤已有数据） */}
          {/* Agent Native：支持 candidates（工具返回）和 matches（兼容旧版）两种字段名 */}
          {message.generativeCard === 'match' && message.generativeData && (
            <div className="generative-ui-container match-card-container">
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <MatchCardList
                  // 字段名兼容：后端/工具常用 candidates，旧版用 matches
                  matches={(message.generativeData as any).matches ?? (message.generativeData as any).candidates ?? []}
                  // 🚀 [改进 v2] 不再传入 all_candidates，筛选改为实时查询
                  userPreferences={(message.generativeData as any).user_preferences || {}}
                  filterOptions={(message.generativeData as any).filter_options || {}}
                  onAction={(action) => {
                    if (action.type === 'view_profile') {
                      // 查看用户详情
                      const userData = action.match
                      handleViewUserProfile(userData.user_id, userData)
                    } else if (action.type === 'start_chat') {
                      // 开始聊天
                      const match = action.match
                      const partnerId = match.user_id || match.user?.id || ''
                      const partnerName = match.name || match.user?.name || 'TA'
                      if (!partnerId) {
                        antdMessage.warning('无法获取用户信息，请稍后重试')
                        return
                      }
                      onOpenChatRoom?.(partnerId, partnerName)
                    }
                  }}
                  onFilterChange={(filters) => {
                    // 🚀 [改进 v2] 篮选触发实时查询
                    handleMatchFilter(message.id, filters)
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
                      // 功能卡片动作处理
                      if (action === 'upgrade_membership') {
                        setMembershipModalOpen(true)
                      } else if (action === 'start_face_verification') {
                        // 触发人脸认证页面
                        window.dispatchEvent(new CustomEvent('trigger-face-verification'))
                      } else if (action === 'start_verify') {
                        // TODO: 身份认证流程
                        antdMessage.info('身份认证功能开发中')
                      } else if (action === 'go_match') {
                        // 触发滑动匹配页面
                        window.dispatchEvent(new CustomEvent('trigger-go-match'))
                      } else {
                        console.log('Feature card action:', action, data)
                      }
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
                        content: formatChatReplyReadability(result.ai_message),
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
                  subtitle={(message.generativeData as any).subtitle}
                  questionType={(message.generativeData as any).question_type}
                  options={(message.generativeData as any).options}
                  dimension={(message.generativeData as any).dimension}
                  depth={0}
                  optional={(message.generativeData as any).optional || false}
                  veto_dimension={(message.generativeData as any).veto_dimension || false}
                  // 🎯 [新增] 进度信息
                  progress={(message.generativeData as any).progress}
                  // 🎯 [新增] 快速填表入口
                  showQuickFill={(message.generativeData as any).showQuickFill || false}
                  onQuickFill={() => {
                    // 🎯 [新增] 快速填表：跳过剩余可选字段，直接进入匹配
                    console.log('[QuickStart] 用户选择快速填表')
                    // 标记注册完成
                    registrationStorage.markCompleted()
                    // 显示引导消息
                    setMessages(prev => {
                      // 移除当前问题卡片
                      const filtered = prev.filter(m => m.id !== message.id)
                      // 添加引导消息
                      const guideMessage: Message = {
                        id: `ai-guide-${Date.now()}`,
                        type: 'ai',
                        content: '好的，我们直接开始吧！你可以说"帮我找对象"开始匹配~',
                        timestamp: new Date(),
                        next_actions: ['帮我找对象'],
                      }
                      return [...filtered, guideMessage]
                    })
                    setIsLoading(false)
                  }}
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
          {/* Agent Native：后端返回 selected_user/user_profile，需要展开字段 */}
          {message.generativeCard === 'user_profile' && message.generativeData && (
            <div className="generative-ui-container">
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <UserProfileCard
                  // 字段映射：selected_user / user_profile / 顶层 props 兼容（见 pickTargetUserIdFromGenerativeData）
                  user_id={pickTargetUserIdFromGenerativeData(message.generativeData)}
                  name={(message.generativeData as any)?.selected_user?.name || (message.generativeData as any)?.user_profile?.name || (message.generativeData as any)?.name || '匿名用户'}
                  age={(message.generativeData as any)?.selected_user?.age ?? (message.generativeData as any)?.user_profile?.age ?? (message.generativeData as any)?.age ?? 0}
                  location={(message.generativeData as any)?.selected_user?.location || (message.generativeData as any)?.user_profile?.location || (message.generativeData as any)?.location || ''}
                  confidence_icon={(message.generativeData as any)?.selected_user?.confidence_icon || (message.generativeData as any)?.user_profile?.confidence_icon || (message.generativeData as any)?.confidence_icon}
                  confidence_level={(message.generativeData as any)?.selected_user?.confidence_level || (message.generativeData as any)?.user_profile?.confidence_level || (message.generativeData as any)?.confidence_level}
                  confidence_score={(message.generativeData as any)?.selected_user?.confidence_score ?? (message.generativeData as any)?.user_profile?.confidence_score ?? (message.generativeData as any)?.confidence_score}
                  occupation={(message.generativeData as any)?.selected_user?.occupation || (message.generativeData as any)?.user_profile?.occupation || (message.generativeData as any)?.occupation}
                  interests={(message.generativeData as any)?.selected_user?.interests || (message.generativeData as any)?.user_profile?.interests || (message.generativeData as any)?.interests || []}
                  bio={(message.generativeData as any)?.selected_user?.bio || (message.generativeData as any)?.user_profile?.bio || (message.generativeData as any)?.bio}
                  relationship_goal={(message.generativeData as any)?.selected_user?.relationship_goal || (message.generativeData as any)?.user_profile?.relationship_goal || (message.generativeData as any)?.relationship_goal}
                  avatar_url={(message.generativeData as any)?.selected_user?.avatar_url || (message.generativeData as any)?.user_profile?.avatar_url || (message.generativeData as any)?.avatar_url}
                  // 🔧 [修复] 自动生成默认 actions，让按钮显示
                  actions={[
                    {
                      label: '发起对话',
                      action: 'start_chat',
                      target_user_id: pickTargetUserIdFromGenerativeData(message.generativeData),
                    },
                    {
                      label: '查看详情',
                      action: 'view_profile',
                      target_user_id: pickTargetUserIdFromGenerativeData(message.generativeData),
                    },
                  ]}
                  onStartChat={(userId: string) => {
                    // 开始对话 - 跳转到聊天室
                    const resolvedId = userId || pickTargetUserIdFromGenerativeData(message.generativeData)
                    if (!resolvedId) {
                      antdMessage.warning('无法获取用户信息，请稍后重试')
                      return
                    }
                    const userName =
                      (message.generativeData as any)?.selected_user?.name ||
                      (message.generativeData as any)?.user_profile?.name ||
                      (message.generativeData as any)?.name ||
                      'TA'
                    onOpenChatRoom?.(resolvedId, userName)
                  }}
                  onViewProfile={(userId: string) => {
                    // 查看详情 - 打开用户详情弹窗
                    const userData = message.generativeData as any
                    const resolvedId = userId || pickTargetUserIdFromGenerativeData(userData)
                    handleViewUserProfile(resolvedId, userData?.selected_user || userData?.user_profile || userData)
                  }}
                />
              </Suspense>
            </div>
          )}

          {/* 聊天发起卡片 - ChatInitiationCard */}
          {message.generativeCard === 'chat_initiation' && message.generativeData && (
            <div className="generative-ui-container">
              <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>}>
                <ChatInitiationCard
                  target_user_id={(message.generativeData as any)?.target_user_id}
                  target_user_name={(message.generativeData as any)?.target_user_name}
                  target_user_avatar={(message.generativeData as any)?.target_user_avatar}
                  context={(message.generativeData as any)?.context}
                  compatibility_score={(message.generativeData as any)?.compatibility_score}
                  onAction={(action) => {
                    if (action.type === 'start_chat') {
                      // 发起聊天 - 跳转到聊天室
                      const userId = (action as any).target_user_id
                      const userName = (action as any).target_user_name || 'TA'
                      if (!userId) {
                        antdMessage.warning('无法获取用户信息，请稍后重试')
                        return
                      }
                      onOpenChatRoom?.(userId, userName)
                    } else if (action.type === 'view_profile') {
                      // 查看详情 - 可以跳转到用户详情页
                      console.log(`[ChatInitiationCard] 查看用户详情: ${(action as any).target_user_id}`)
                    }
                  }}
                />
              </Suspense>
            </div>
          )}

          {/* 匹配结果卡片（遗留逻辑，兼容旧版 message.matches） */}
          {/* Agent Native：只渲染卡片，不显示默认文字（文字由 Agent 自主生成） */}
          {message.matches && message.matches.length > 0 && (
            <div className="match-cards">
              {/* 移除默认的"找到 X 位候选人"文字，让 Agent 决定输出内容 */}
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
                            if (!partnerId) {
                              antdMessage.warning('无法获取用户信息，请稍后重试')
                              return
                            }
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
  }, [onMatchSelect, handleQuickAction, handleQuickStartAnswer, HerAvatar, onOpenChatRoom, handleMatchFilter])

  return (
    <div className="chat-interface">
      {/* 消息列表 */}
      <div className="messages-container">
        {messages.map((message) => (
          <MessageWrapper key={message.id} message={message} renderContent={renderMessageContent} />
        ))}
        {isLoading && !showMatchSkeleton && (
          <div className="loading-indicator">
            <Spin size="small" />
            <Text type="secondary" style={{ marginLeft: 8 }}>
              {loadingStep || t('conversation.herThinking')}
            </Text>
            {/* 动态进度动画效果 */}
            <span className="loading-dots">
              <span>.</span><span>.</span><span>.</span>
            </span>
          </div>
        )}

        {/* 骨架屏预览：匹配卡片占位 + 动态进度 */}
        {showMatchSkeleton && (
          <div className="match-skeleton-preview">
            <div className="skeleton-preview-title">
              <Spin size="small" style={{ marginRight: 8 }} />
              <Text type="secondary">
                {loadingStep || '正在为你精选匹配对象...'}
              </Text>
              {/* 🚀 [改进] 动态进度数字 */}
              <span className="skeleton-progress-dots">
                <span>.</span><span>.</span><span>.</span>
              </span>
            </div>
            {/* 🚀 [改进] 显示当前进度阶段（动态状态：已完成/进行中/等待中） */}
            <div className="skeleton-progress-steps">
              {/* 🚀 [场景3方案3] 进度可视化：根据 progressStepIndex 显示状态 */}
              {[
                { icon: '🔍', label: '查询候选人', step: 0 },
                { icon: '📊', label: '分析匹配度', step: 1 },
                { icon: '✨', label: '精选推荐', step: 2 },
              ].map((step, idx) => (
                <div
                  key={idx}
                  className={`progress-step ${
                    idx < progressStepIndex ? 'completed' :
                    idx === progressStepIndex ? 'active' :
                    'pending'
                  }`}
                >
                  <span className="step-icon">
                    {idx < progressStepIndex ? '✅' : step.icon}
                  </span>
                  <span className="step-label">{step.label}</span>
                  {/* 🚀 [场景3方案3] 进行中显示动画 */}
                  {idx === progressStepIndex && (
                    <span className="step-loading">
                      <Spin size="small" />
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="skeleton-cards-container">
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton-match-card">
                  <div className="skeleton-avatar">
                    <Spin size="small" />
                  </div>
                  <div className="skeleton-info">
                    <div className="skeleton-name"></div>
                    <div className="skeleton-meta"></div>
                    <div className="skeleton-tags"></div>
                  </div>
                </div>
              ))}
            </div>
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

      {/* 会员订阅 Modal */}
      <Suspense fallback={null}>
        <MembershipSubscribeModal
          open={membershipModalOpen}
          onClose={() => setMembershipModalOpen(false)}
          onSuccess={() => {
            setMembershipModalOpen(false)
            antdMessage.success('会员订阅成功！')
          }}
        />
      </Suspense>

      {/* 推荐详情：与列表卡片区分，优先展示「为什么推荐」 */}
      <Drawer
        title="推荐详情"
        placement="right"
        width={400}
        open={userDetailVisible}
        onClose={handleCloseUserDetail}
        styles={{ body: { padding: 16 } }}
      >
        {selectedUserDetail && (
          <div className="user-detail-content">
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <Avatar
                size={80}
                src={selectedUserDetail.avatar_url}
                icon={<UserOutlined />}
                style={{ marginBottom: 8 }}
              />
              <Title level={4} style={{ marginBottom: 4 }}>
                {selectedUserDetail.name} · {selectedUserDetail.age}岁
              </Title>
              <Space size={4} wrap>
                <EnvironmentOutlined />
                <Text type="secondary">{selectedUserDetail.location}</Text>
                {typeof selectedUserDetail.compatibility_score === 'number' && (
                  <Tag color="magenta">匹配度 {selectedUserDetail.compatibility_score}%</Tag>
                )}
                {typeof selectedUserDetail.confidence_score === 'number' && (() => {
                  const c = selectedUserDetail.confidence_score!
                  const pct = c > 0 && c <= 1 ? Math.round(c * 100) : Math.min(100, Math.round(c))
                  return <Tag>资料可信度 {pct}%</Tag>
                })()}
              </Space>
            </div>

            <div
              style={{
                marginBottom: 16,
                padding: 12,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(200,139,139,0.12) 0%, rgba(255,182,193,0.15) 100%)',
                border: '1px solid rgba(200,139,139,0.35)',
              }}
            >
              <Text strong style={{ display: 'block', marginBottom: 8, color: '#8b4a4a' }}>
                为什么推荐 TA
              </Text>
              {selectedUserDetail.reasoning ? (
                <Paragraph style={{ marginBottom: 8, color: '#5c4a4a', whiteSpace: 'pre-wrap' }}>
                  {selectedUserDetail.reasoning}
                </Paragraph>
              ) : null}
              {selectedUserDetail.match_reasons && selectedUserDetail.match_reasons.length > 0 ? (
                <Space wrap size={4}>
                  {selectedUserDetail.match_reasons.map((reason, index) => (
                    <Tag key={index} color="pink" style={{ borderRadius: 4 }}>
                      {reason}
                    </Tag>
                  ))}
                </Space>
              ) : null}
              {selectedUserDetail.common_interests && selectedUserDetail.common_interests.length > 0 ? (
                <div style={{ marginTop: 10 }}>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    共同点（兴趣）
                  </Text>
                  <Space wrap size={4}>
                    {selectedUserDetail.common_interests.map((interest, index) => (
                      <Tag key={`c-${index}`} color="blue">
                        {interest}
                      </Tag>
                    ))}
                  </Space>
                </div>
              ) : null}
              {!selectedUserDetail.reasoning &&
                (!selectedUserDetail.match_reasons || selectedUserDetail.match_reasons.length === 0) &&
                (!selectedUserDetail.common_interests || selectedUserDetail.common_interests.length === 0) && (
                <Text type="secondary" style={{ fontSize: 13 }}>
                  当前推荐综合了你的资料与偏好；若希望看到更具体的理由，可以在对话里多说说你的择偶侧重点（例如城市、兴趣、相处方式）。
                </Text>
              )}
            </div>

            <Divider style={{ margin: '12px 0' }} />

            {selectedUserDetail.is_same_city && (
              <div style={{ marginBottom: 12 }}>
                <Tag color="green" icon={<EnvironmentOutlined />}>
                  同城用户
                </Tag>
              </div>
            )}

            {selectedUserDetail.occupation && (
              <div style={{ marginBottom: 12 }}>
                <Text strong>职业：</Text>
                <Text>{selectedUserDetail.occupation}</Text>
              </div>
            )}

            {selectedUserDetail.relationship_goal && (
              <div style={{ marginBottom: 12 }}>
                <Text strong>关系目标：</Text>
                <Tag color="pink">
                  {RELATIONSHIP_GOAL_MAP[selectedUserDetail.relationship_goal] || selectedUserDetail.relationship_goal}
                </Tag>
              </div>
            )}

            {selectedUserDetail.interests && selectedUserDetail.interests.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text strong style={{ marginBottom: 4, display: 'block' }}>
                  TA 的兴趣爱好
                </Text>
                <Space wrap size={4}>
                  {selectedUserDetail.interests.map((interest, index) => (
                    <Tag key={index} color="blue">{interest}</Tag>
                  ))}
                </Space>
              </div>
            )}

            {selectedUserDetail.bio && (
              <div style={{ marginBottom: 12 }}>
                <Text strong style={{ marginBottom: 4, display: 'block' }}>
                  简介
                </Text>
                <Paragraph style={{ color: '#666' }}>
                  {selectedUserDetail.bio}
                </Paragraph>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default ChatInterface
