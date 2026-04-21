/**
 * AI Native 主页面 - 纯对话式交互
 * 遵循 AI Native 原则：
 * 1. 对话优先 (Chat-first) - 无菜单，一切通过对话
 * 2. Generative UI - AI 动态生成所需界面
 * 3. AI 自主性 - AI 主动感知和推送
 * 4. 情境化交互 - 功能融入对话流
 */

import React, { useState, useEffect, useRef, lazy, Suspense } from 'react'
import { Layout, Typography, Space, Button, Avatar, notification, Drawer, message, Spin, Descriptions, Tag, Card, Form, Input, Divider } from 'antd'
import {
  UserOutlined,
  CommentOutlined,
  EditOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate } from '../types'
import ChatInterface from '../components/ChatInterface'
// 🚀 [性能优化] 懒加载大型组件，减少初始 bundle 大小
const ChatRoom = lazy(() => import('../components/ChatRoom'))
const MatchCard = lazy(() => import('../components/MatchCard'))
const FeaturesDrawer = lazy(() => import('../components/FeaturesDrawer'))
const PushNotifications = lazy(() => import('../components/PushNotifications'))
const AgentFloatingBall = lazy(() => import('../components/AgentFloatingBall'))
const SwipeMatchPage = lazy(() => import('./SwipeMatchPage'))
const WhoLikesMePage = lazy(() => import('./WhoLikesMePage'))
const ConfidenceManagementPage = lazy(() => import('./ConfidenceManagementPage'))
const FaceVerificationPage = lazy(() => import('./FaceVerificationPage'))
const YourTurnReminder = lazy(() => import('../components/YourTurnReminder'))
const FeatureGuideModal = lazy(() => import('../components/FeatureGuideModal')) // 🔧 [问题17方案B] 首次功能引导
// 🚀 [性能优化] FeaturesButton 需要立即渲染，直接导入
import { FeaturesButton } from '../components/FeaturesDrawer'
import type { Feature } from '../components/FeaturesDrawer'
import LanguageSwitcher from '../components/LanguageSwitcher'
import HerAvatar from '../assets/her-avatar.svg'
import { chatApi, conversationMatchingApi, userApi } from '../api'
import { useCurrentUserId } from '../hooks/useCurrentUserId'
import { authStorage, herStorage, guideStorage, conversationSummaryStorage } from '../utils/storage' // 🔧 [问题17方案B] 导入 guideStorage
import './HomePage.less'

const { Header, Content } = Layout
const { Text } = Typography
const UUID_REGEX = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i

const isInvalidDisplayName = (value?: string): boolean => {
  const name = (value || '').trim()
  if (!name) return true
  if (name === 'user-anonymous-dev') return true
  return UUID_REGEX.test(name)
}

const normalizeDisplayName = (...candidates: Array<string | undefined>): string => {
  for (const raw of candidates) {
    if (isInvalidDisplayName(raw)) continue
    return (raw || '').trim()
  }
  return 'TA'
}

// 聊天场景的快速入口选项
const CHAT_SCENE_QUICK_OPTIONS = [
  { label: '分析这位对象', trigger: '分析这位匹配对象' },
  { label: '约见面建议', trigger: '我想约见面，有什么建议' },
  { label: '聊天话题', trigger: '推荐一些聊天话题' },
]

interface HomePageProps {
  onLogout?: () => void
}

const HomePage: React.FC<HomePageProps> = ({ onLogout }) => {
  const { t } = useTranslation()
  const [selectedMatch, setSelectedMatch] = useState<MatchCandidate | null>(null)
  const [chatInitialMatch, setChatInitialMatch] = useState<MatchCandidate | null>(null)
  const [chatRoomMatch, setChatRoomMatch] = useState<MatchCandidate | null>(null)
  const [userInfo, setUserInfo] = useState<{ username?: string; name?: string } | null>(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const [conversations, setConversations] = useState<any[]>([])  // 会话列表
  const [lastMessageTime, setLastMessageTime] = useState<Record<string, string>>({})
  const [matchesCache, setMatchesCache] = useState<Record<string, MatchCandidate>>({})
  const [hasNewMessage, setHasNewMessage] = useState(false)
  const [featuresDrawerOpen, setFeaturesDrawerOpen] = useState(false) // 功能抽屉状态
  const [showSwipeMatch, setShowSwipeMatch] = useState(false) // 滑动匹配页面状态
  const [showWhoLikesMe, setShowWhoLikesMe] = useState(false) // Who Likes Me 页面状态
  const [showConfidence, setShowConfidence] = useState(false) // 置信度管理页面状态
  const [showFaceVerification, setShowFaceVerification] = useState(false) // 人脸认证页面状态
  // 🔧 [问题16方案A] 首次进入聊天室时，默认唤醒 Her（不休眠）
  // 让用户能立刻看到悬浮球，知道 Her 正在旁观
  const [herSleeping, setHerSleeping] = useState(() => {
    // 🔧 [修复] 读取用户的休眠偏好，新用户默认唤醒
    // 只有用户主动休眠后才隐藏悬浮球
    return herStorage.isSleepingInChat()
  })
  // 🔧 [问题17方案B] 首次功能引导弹窗状态
  // 新用户首次进入时显示，告知用户如何使用 Her
  const [showFeatureGuide, setShowFeatureGuide] = useState(() => {
    // 检查是否已显示过引导弹窗
    return !guideStorage.isFeatureGuideShown()
  })

  // 🚀 [改进点5] 悬浮球 Her 的上下文（包含最近消息）
  // 从 ChatRoom 接收上下文更新事件
  const [floatingBallContext, setFloatingBallContext] = useState<{
    partnerId: string
    partnerName: string
    partnerAvatar?: string
    recentMessages?: Array<{
      content: string
      sender: 'user' | 'partner'
      timestamp: Date
    }>
  } | null>(null)
  const [profileDrawerOpen, setProfileDrawerOpen] = useState(false)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileEditMode, setProfileEditMode] = useState(false)
  const [profileData, setProfileData] = useState<Record<string, any> | null>(null)
  const [profileForm] = Form.useForm()

  const userId = useCurrentUserId()

  // 用户信息展示：以本地认证信息为单一来源，避免 Header 丢失昵称
  useEffect(() => {
    const currentUser = authStorage.getUser()
    if (!currentUser) return

    setUserInfo({
      username: currentUser.username,
      name: currentUser.name,
    })
    setProfileData(currentUser)
  }, [])

  const loadMyProfile = async (options?: { background?: boolean }) => {
    const shouldShowBlockingLoading = !options?.background
    if (shouldShowBlockingLoading) {
      setProfileLoading(true)
    }
    try {
      const me = await userApi.getCurrentUser()
      if (me) {
        setProfileData(me)
        setUserInfo({
          username: me.username,
          name: me.name,
        })
        authStorage.setUser({
          ...(authStorage.getUser() || {}),
          ...me,
        })
      }
    } catch (error) {
      // 保留本地兜底，不阻塞抽屉展示
    } finally {
      if (shouldShowBlockingLoading) {
        setProfileLoading(false)
      }
    }
  }

  const handleOpenProfile = () => {
    setProfileDrawerOpen(true)
    setProfileEditMode(false)
    // 已有本地资料时先秒开抽屉，再后台刷新，避免弱网下点击后长时间转圈
    loadMyProfile({ background: !!profileData })
  }

  const handleEnterProfileEdit = () => {
    setProfileEditMode(true)
    profileForm.setFieldsValue({
      name: profileData?.name || '',
      location: profileData?.location || '',
      bio: profileData?.bio || '',
      interests: Array.isArray(profileData?.interests) ? profileData.interests.join('，') : '',
    })
  }

  const handleCancelProfileEdit = () => {
    setProfileEditMode(false)
    profileForm.resetFields()
  }

  const handleSaveProfile = async () => {
    try {
      const values = await profileForm.validateFields()
      const currentUserId = profileData?.id || authStorage.getUserId()
      if (!currentUserId || currentUserId === 'anonymous') {
        message.error('当前用户身份无效，无法保存')
        return
      }

      const interests = String(values.interests || '')
        .split(/[，,]/)
        .map((item) => item.trim())
        .filter(Boolean)

      const payload = {
        name: values.name?.trim() || undefined,
        location: values.location?.trim() || undefined,
        bio: values.bio?.trim() || undefined,
        interests,
      }

      setProfileSaving(true)
      const updated = await userApi.updateCurrentUser(currentUserId, payload)
      setProfileData(updated)
      setUserInfo({
        username: updated?.username || userInfo?.username,
        name: updated?.name || userInfo?.name,
      })
      authStorage.setUser({
        ...(authStorage.getUser() || {}),
        ...updated,
      })
      setProfileEditMode(false)
      message.success('资料已更新')
    } catch (error) {
      if ((error as any)?.errorFields) return
      message.error('保存失败，请稍后重试')
    } finally {
      setProfileSaving(false)
    }
  }

  // 微信式：先展示本地会话摘要，再后台增量刷新
  useEffect(() => {
    const cached = conversationSummaryStorage.getConversations(userId)
    if (cached.length > 0) {
      setConversations(cached)
      const unread = cached.reduce((sum, conv) => sum + (conv.unread_count || 0), 0)
      setUnreadCount(unread)
    }
  }, [userId])

  // 已通知的消息 ID 集合，避免重复弹窗
  const notifiedMessageIds = useRef<Set<string>>(new Set())

  // 当前聊天对象 ID（ref 用于轮询逻辑中检查，避免给正在聊天的人发送通知）
  const chatRoomPartnerIdRef = useRef<string | null>(null)

  // 布局检查 - 组件挂载时记录
  useEffect(() => {
    return () => {}
  }, [])

  // 获取匹配列表缓存
  useEffect(() => {
    const fetchMatches = async () => {
      try {
        const matches = await conversationMatchingApi.getAiPushRecommendations()
        if (matches && matches.matches) {
          const cache: Record<string, MatchCandidate> = {}
          matches.matches.forEach((m: MatchCandidate) => {
            if (m.user?.id) {
              cache[m.user.id] = m
            }
          })
          setMatchesCache(cache)
          matchesCacheRef.current = cache  // 同步更新 ref
        }
      } catch (error) {
        // 静默失败
      }
    }
    fetchMatches()
  }, [])

  // 轮询未读消息数 - 移除 matchesCache 依赖，使用 ref 缓存避免重复渲染
  const matchesCacheRef = useRef<Record<string, MatchCandidate>>({})

  useEffect(() => {
    let mounted = true
    let checkInterval: NodeJS.Timeout

    const checkUnreadMessages = async () => {
      try {
        const response = await chatApi.getConversations()

        if (Array.isArray(response)) {
          // 🔧 [修复] 计算未读数时排除当前聊天对象（用户正在聊天不需要通知）
          const totalUnread = response.reduce((sum, conv) => {
            const partnerId = conv.user_id_1 === userId ? conv.user_id_2 : conv.user_id_1
            // 如果正在跟这个人聊天，不计入未读
            if (chatRoomPartnerIdRef.current === partnerId) {
              return sum
            }
            return sum + (conv.unread_count || 0)
          }, 0)

          // 有新消息时，设置状态
          if (totalUnread > 0 && mounted) {
            setHasNewMessage(true)
          }

          // 检测新消息通知
          const newConversations = response.filter(
            conv => {
              const isNotNotified = !notifiedMessageIds.current.has(conv.id)
              const isNewMessage = !lastMessageTime[conv.id] || conv.last_message_at > lastMessageTime[conv.id]
              return conv.last_message_at && isNotNotified && isNewMessage
            }
          )

          if (newConversations.length > 0) {
            // 静默处理，不打印日志
          }

          newConversations.forEach(conv => {
            const partnerId = conv.partner_id || (conv.user_id_1 === userId ? conv.user_id_2 : conv.user_id_1)
            if (!partnerId || partnerId === 'user-anonymous-dev' || partnerId === userId) {
              return
            }

            // 🔧 [修复] 如果用户正在聊天室中，跳过所有通知弹窗（避免打扰聊天体验）
            // 无论消息来自当前聊天对象还是其他人，都不弹窗
            if (chatRoomPartnerIdRef.current !== null) {
              return
            }

            const cachedMatch = matchesCacheRef.current[partnerId]
            const partnerName = normalizeDisplayName(conv.partner_name, cachedMatch?.user?.name, partnerId)

            notification.info({
              message: t('conversation.newMessageNotify'),
              description: `${partnerName}: ${conv.last_message_preview || t('conversation.sentMessage')}`,
              icon: <CommentOutlined style={{ color: '#1890ff' }} />,
              duration: 5,
              placement: 'topRight',
              onClick: () => {
                if (cachedMatch) {
                  handleStartChat(cachedMatch)
                } else {
                  const mockMatch: MatchCandidate = {
                    user: {
                      id: partnerId,
                      name: partnerName,
                      avatar: conv.partner_avatar_url || undefined,
                      avatar_url: conv.partner_avatar_url || undefined,
                    },
                    compatibility_score: 0,
                    score: 0,
                  }
                  handleStartChat(mockMatch)
                }
              },
            })

            notifiedMessageIds.current.add(conv.id)
          })

          // 更新最后消息时间
          const newLastMessageTime: Record<string, string> = {}
          response.forEach(conv => {
            if (conv.last_message_at) {
              newLastMessageTime[conv.id] = conv.last_message_at
            }
          })

          if (mounted) {
            setUnreadCount(totalUnread)
            setConversations(response)  // 保存会话列表
            setLastMessageTime(newLastMessageTime)
            conversationSummaryStorage.setConversations(userId, response)
          }
        }
      } catch (error: unknown) {
        // 静默失败
      }
    }

    checkUnreadMessages()
    checkInterval = setInterval(checkUnreadMessages, 10000) // 10 秒一次，减少请求频率

    return () => {
      mounted = false
      if (checkInterval) {
        clearInterval(checkInterval)
      }
    }
  }, [userId])  // 移除 matchesCache 依赖


  const handleMatchSelect = (match: MatchCandidate) => {
    setSelectedMatch(match)
  }

  const handleCloseMatchDetail = () => {
    setSelectedMatch(null)
  }

  const handleStartChat = (match: MatchCandidate) => {
    // 设置为聊天室模式
    setChatRoomMatch(match)
    chatRoomPartnerIdRef.current = match.user?.id || null  // 记录当前聊天对象
    // 关闭详情弹窗
    setSelectedMatch(null)
  }

  const handleBackToChat = () => {
    setChatRoomMatch(null)
    chatRoomPartnerIdRef.current = null  // 清除当前聊天对象
  }

  const handleChatInitialMatchConsumed = () => {
    setChatInitialMatch(null)
  }

  // 打开聊天室（从 ChatInterface 回调）
  const handleOpenChatRoom = (partnerId: string, partnerName: string) => {
    const cachedMatch = matchesCacheRef.current[partnerId] || matchesCache[partnerId]
    const resolvedName = normalizeDisplayName(partnerName, cachedMatch?.user?.name, partnerId)
    // 创建匹配对象
    const match: MatchCandidate = {
      user: {
        id: partnerId,
        name: resolvedName,
        avatar: undefined,
        avatar_url: undefined,
      },
      compatibility_score: 0,
      score: 0,
    }
    setChatRoomMatch(match)
    chatRoomPartnerIdRef.current = partnerId  // 记录当前聊天对象，避免通知打扰
  }

  // 🚀 [新增] 快速对话回调 - 从悬浮球发送消息给 Her
  const handleQuickChat = (message: string) => {
    // 关闭 ChatRoom，返回 ChatInterface
    setChatRoomMatch(null)
    chatRoomPartnerIdRef.current = null  // 清除当前聊天对象
    // 触发自定义事件，让 ChatInterface 接收消息
    window.dispatchEvent(new CustomEvent('her-quick-chat', { detail: { message } }))
  }

  // 处理功能选择 - 在对话区生成功能卡片或切换页面
  const handleFeatureSelect = (feature: Feature) => {
    // 滑动匹配功能 - 直接显示滑动页面
    if (feature.action === 'swipe') {
      setShowSwipeMatch(true)
      return
    }

    // Who Likes Me 功能 - 直接显示页面
    if (feature.action === 'who_likes_me') {
      setShowWhoLikesMe(true)
      return
    }

    // 置信度管理功能 - 直接显示页面
    if (feature.action === 'confidence') {
      setShowConfidence(true)
      return
    }

    // 人脸认证功能 - 直接显示页面
    if (feature.action === 'face_verification') {
      setShowFaceVerification(true)
      return
    }

    // Your Turn 功能 - 触发 ChatInterface 显示 YourTurnReminder
    if (feature.action === 'your_turn') {
      window.dispatchEvent(new CustomEvent('trigger-feature', {
        detail: { feature }
      }))
      return
    }

    message.info(t('home.openingFeature', { name: feature.name }))

    // 其他功能触发 ChatInterface 生成对应的功能卡片
    window.dispatchEvent(new CustomEvent('trigger-feature', {
      detail: { feature }
    }))
  }

  // 从滑动匹配页面返回
  const handleBackFromSwipe = () => {
    setShowSwipeMatch(false)
  }

  // 从 Who Likes Me 页面返回
  const handleBackFromWhoLikesMe = () => {
    setShowWhoLikesMe(false)
  }

  // 从置信度管理页面返回
  const handleBackFromConfidence = () => {
    setShowConfidence(false)
  }

  // 从人脸认证页面返回
  const handleBackFromFaceVerification = () => {
    setShowFaceVerification(false)
  }

  // 🔧 [问题17方案B] 关闭功能引导弹窗
  const handleCloseFeatureGuide = () => {
    setShowFeatureGuide(false)
    // 标记已显示，下次不再弹出
    guideStorage.markFeatureGuideShown()
  }

  // 监听来自 ChatInterface 的事件
  useEffect(() => {
    const handleGoMatch = () => {
      setShowSwipeMatch(true)
    }

    const handleFaceVerification = () => {
      setShowFaceVerification(true)
    }

    // 🚀 [改进点5] 监听来自 ChatRoom 的上下文更新事件
    const handleHerContextUpdate = (e: CustomEvent) => {
      setFloatingBallContext(e.detail)
    }

    const handleConversationRead = (e: CustomEvent<{ partnerId?: string }>) => {
      const partnerId = e.detail?.partnerId
      if (!partnerId) return

      setConversations((prev) => {
        const next = prev.map((conv: any) => {
          const convPartnerId = conv.partner_id || (conv.user_id_1 === userId ? conv.user_id_2 : conv.user_id_1)
          if (convPartnerId === partnerId) {
            return { ...conv, unread_count: 0 }
          }
          return conv
        })
        const unread = next.reduce((sum: number, conv: any) => sum + (conv.unread_count || 0), 0)
        setUnreadCount(unread)
        conversationSummaryStorage.setConversations(userId, next)
        return next
      })
    }

    window.addEventListener('trigger-go-match', handleGoMatch)
    window.addEventListener('trigger-face-verification', handleFaceVerification)
    window.addEventListener('her-context-update', handleHerContextUpdate as EventListener)
    window.addEventListener('conversation-read', handleConversationRead as EventListener)

    return () => {
      window.removeEventListener('trigger-go-match', handleGoMatch)
      window.removeEventListener('trigger-face-verification', handleFaceVerification)
      window.removeEventListener('her-context-update', handleHerContextUpdate as EventListener)
      window.removeEventListener('conversation-read', handleConversationRead as EventListener)
    }
  }, [userId])

  const renderView = () => {
    // 滑动匹配页面
    if (showSwipeMatch) {
      return (
        <div className="swipe-match-view">
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" tip={t('home.loadingSwipeMatch')}><div style={{ padding: 50 }} /></Spin></div>}>
            <SwipeMatchPage onBack={handleBackFromSwipe} />
          </Suspense>
        </div>
      )
    }

    // Who Likes Me 页面
    if (showWhoLikesMe) {
      return (
        <div className="who-likes-me-view">
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" tip={t('home.loadingWhoLikesMe')}><div style={{ padding: 50 }} /></Spin></div>}>
            <WhoLikesMePage
              userId={userId}
              onMatch={(_matchId, matchData) => {
                // 匹配成功后打开聊天
                if (matchData?.targetUserId) {
                  handleOpenChatRoom(matchData.targetUserId, t('home.newMatch'))
                }
                setShowWhoLikesMe(false)
              }}
            />
          </Suspense>
        </div>
      )
    }

    // 置信度管理页面
    if (showConfidence) {
      return (
        <div className="confidence-view">
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" tip="加载置信度数据..."><div style={{ padding: 50 }} /></Spin></div>}>
            <ConfidenceManagementPage onBack={handleBackFromConfidence} />
          </Suspense>
        </div>
      )
    }

    // 人脸认证页面
    if (showFaceVerification) {
      return (
        <div className="face-verification-view">
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" tip="加载认证数据..."><div style={{ padding: 50 }} /></Spin></div>}>
            <FaceVerificationPage
              onBack={handleBackFromFaceVerification}
              onComplete={(badge) => {
                message.success('人脸认证成功！')
                setShowFaceVerification(false)
              }}
            />
          </Suspense>
        </div>
      )
    }

    if (chatRoomMatch) {
      return (
        <div className="chat-room-view">
          {/* 🚀 [性能优化] Suspense 包裹懒加载的 ChatRoom */}
          <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><Spin size="large" tip={t('home.loadingChatRoom')}><div style={{ padding: 50 }} /></Spin></div>}>
            <ChatRoom
              match={chatRoomMatch}
              onBack={handleBackToChat}
              herSleeping={herSleeping}
              onHerSleepChange={setHerSleeping}
            />
          </Suspense>
        </div>
      )
    }

    // 默认显示 AI 对话界面 - 所有功能通过对话调用
    return (
      <div className="chat-view">
        <ChatInterface
          onMatchSelect={handleMatchSelect}
          onOpenChatRoom={handleOpenChatRoom}  // 新增：打开聊天室回调
          initialMatch={chatInitialMatch}
          onInitialMatchConsumed={handleChatInitialMatchConsumed}
        />
      </div>
    )
  }

  return (
    <Layout className="home-layout">
      {/* 顶部栏 - 极简设计 */}
      <Header className="home-header">
        <div className="header-left">
          <Space>
            <Avatar
              size={36}
              src={HerAvatar}
              style={{ backgroundColor: '#fff', padding: 4 }}
            />
            <Text strong style={{ color: '#4A4040', fontSize: 18, letterSpacing: '2px' }}>{t('app.name')}</Text>
          </Space>
        </div>
        <div className="header-right">
          <Space size="middle">
            {/* 语言切换 */}
            <LanguageSwitcher trigger="icon" size="small" />
            {/* 🚀 [性能优化] Suspense 包裹懒加载的 PushNotifications */}
            <Suspense fallback={<Spin size="small" />}>
              <PushNotifications
                unreadCount={unreadCount}
                conversations={conversations}
                matchesCache={matchesCache}
                onOpenChatRoom={handleOpenChatRoom}
              />
            </Suspense>
            {/* 聊天室或滑动匹配模式下隐藏功能按钮，专注当前体验 */}
              {!chatRoomMatch && !showSwipeMatch && !showWhoLikesMe && !showConfidence && !showFaceVerification && <FeaturesButton onClick={() => setFeaturesDrawerOpen(true)} />}
            <Space>
              <button
                type="button"
                className="profile-entry"
                onClick={handleOpenProfile}
                aria-label={t('home.myProfile')}
              >
                <Avatar size={28} icon={<UserOutlined />} className="profile-entry-avatar" />
                {userInfo && (
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    {userInfo.name || userInfo.username}
                  </Text>
                )}
              </button>
            </Space>
          </Space>
        </div>
      </Header>

      {/* 主内容区 - 只有对话界面 */}
      <Content className="home-content">
        <div className="content-wrapper">{renderView()}</div>
      </Content>

      {/* 匹配详情 Drawer */}
      {selectedMatch && (
        <Drawer
          title={t('match.title')}
          placement="right"
          width={400}
          open={!!selectedMatch}
          onClose={handleCloseMatchDetail}
        >
          {/* 🚀 [性能优化] Suspense 包裹懒加载的 MatchCard */}
          <Suspense fallback={<div style={{ padding: 24, textAlign: 'center' }}><Spin size="large" /></div>}>
            <MatchCard
              match={selectedMatch}
              onLike={() => {}}
              onPass={() => {}}
              onSuperLike={() => {}}
              onMessage={() => handleStartChat(selectedMatch)}
            />
          </Suspense>
        </Drawer>
      )}

      {/* 功能抽屉 - 轻量级功能入口 */}
      <Suspense fallback={null}>
        <FeaturesDrawer
          open={featuresDrawerOpen}
          onClose={() => setFeaturesDrawerOpen(false)}
          onFeatureSelect={handleFeatureSelect}
        />
      </Suspense>

      <Drawer
        title={t('home.myProfile')}
        placement="right"
        width={380}
        className="profile-drawer"
        open={profileDrawerOpen}
        onClose={() => {
          setProfileDrawerOpen(false)
          setProfileEditMode(false)
        }}
      >
        {profileLoading ? (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <Spin size="large" />
          </div>
        ) : (
          <>
            <Card bordered={false} className="profile-summary-card">
              <Space align="center">
                <Avatar size={56} icon={<UserOutlined />} className="profile-summary-avatar" />
                <div className="profile-summary-meta">
                  <div className="profile-summary-name">{profileData?.name || profileData?.username || '未设置昵称'}</div>
                  <Text type="secondary" className="profile-summary-username">@{profileData?.username || '-'}</Text>
                </div>
              </Space>
              <Divider style={{ margin: '12px 0' }} />
              <Space className="profile-summary-actions">
                {!profileEditMode ? (
                  <Button icon={<EditOutlined />} onClick={handleEnterProfileEdit} className="profile-edit-btn">
                    编辑资料
                  </Button>
                ) : (
                  <>
                    <Button onClick={handleCancelProfileEdit} className="profile-cancel-btn">取消</Button>
                    <Button type="primary" icon={<SaveOutlined />} loading={profileSaving} onClick={handleSaveProfile} className="profile-save-btn">
                      保存
                    </Button>
                  </>
                )}
              </Space>
            </Card>

            {profileEditMode ? (
              <Form form={profileForm} layout="vertical">
                <Form.Item
                  label={t('auth.name')}
                  name="name"
                  rules={[{ required: true, message: '请输入昵称' }]}
                >
                  <Input placeholder="请输入昵称" maxLength={32} />
                </Form.Item>
                <Form.Item label={t('profile.location')} name="location">
                  <Input placeholder="例如：上海" maxLength={64} />
                </Form.Item>
                <Form.Item label={t('profile.bio')} name="bio">
                  <Input.TextArea rows={4} placeholder="写点自我介绍" maxLength={300} showCount />
                </Form.Item>
                <Form.Item label={t('profile.interests')} name="interests">
                  <Input.TextArea rows={3} placeholder="用逗号分隔，例如：旅行，美食，电影" maxLength={200} />
                </Form.Item>
              </Form>
            ) : (
              <Descriptions column={1} size="small" bordered className="profile-details">
                <Descriptions.Item label={t('auth.username')}>
                  {profileData?.username || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('auth.name')}>
                  {profileData?.name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('auth.email')}>
                  {profileData?.email || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('profile.age')}>
                  {profileData?.age ?? '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('profile.gender')}>
                  {profileData?.gender || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('profile.location')}>
                  {profileData?.location || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('profile.bio')}>
                  {profileData?.bio || '-'}
                </Descriptions.Item>
                <Descriptions.Item label={t('profile.interests')}>
                  {Array.isArray(profileData?.interests) && profileData.interests.length > 0
                    ? profileData.interests.map((interest: string) => <Tag key={interest} className="profile-interest-tag">{interest}</Tag>)
                    : '-'}
                </Descriptions.Item>
              </Descriptions>
            )}

            <div style={{ marginTop: 16 }}>
              <Button
                block
                danger
                icon={<UserOutlined />}
                className="profile-logout-btn"
                onClick={() => {
                  setProfileDrawerOpen(false)
                  onLogout?.()
                }}
              >
                {t('auth.logout')}
              </Button>
            </div>
          </>
        )}
      </Drawer>

      {/* PWA 安装提示 - 临时禁用，方便调试 */}
      {/* <PWAInstallPrompt /> */}

      {/* 🚀 [场景5方案2优化] 悬浮球 - 只在非主对话界面显示 */}
      {/* 主对话界面已有 ChatInterface，悬浮球只在聊天室、滑动匹配页等场景显示 */}
      {!herSleeping && (chatRoomMatch || showSwipeMatch || showConfidence || showFaceVerification) && (
        <Suspense fallback={null}>
          <AgentFloatingBall
            visible={true}
            hasNewMessage={hasNewMessage}
            chatContext={floatingBallContext || (chatRoomMatch ? {
              partnerId: chatRoomMatch.user?.id || '',
              partnerName: chatRoomMatch.user?.name || 'TA',
            } : null)}
            quickOptions={chatRoomMatch ? CHAT_SCENE_QUICK_OPTIONS : undefined}
            // 根据当前页面状态推断场景
            scene={
              chatRoomMatch ? 'chat' :
              showSwipeMatch ? 'swipe' :
              showConfidence || showFaceVerification ? 'profile' :
              'home'
            }
            onQuickChat={handleQuickChat}
          />
        </Suspense>
      )}

      {/* 🔧 [问题17方案B] 首次功能引导弹窗 - 新用户首次进入时显示 */}
      {showFeatureGuide && (
        <Suspense fallback={null}>
          <FeatureGuideModal
            open={showFeatureGuide}
            onClose={handleCloseFeatureGuide}
          />
        </Suspense>
      )}
    </Layout>
  )
}

export default HomePage
