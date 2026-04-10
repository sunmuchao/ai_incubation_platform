/**
 * AI Native 主页面 - 纯对话式交互
 * 遵循 AI Native 原则：
 * 1. 对话优先 (Chat-first) - 无菜单，一切通过对话
 * 2. Generative UI - AI 动态生成所需界面
 * 3. AI 自主性 - AI 主动感知和推送
 * 4. 情境化交互 - 功能融入对话流
 */

import React, { useState, useEffect, useRef } from 'react'
import { Layout, Typography, Space, Button, Avatar, notification, Drawer, message } from 'antd'
import {
  UserOutlined,
  CommentOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate } from '../types'
import ChatInterface from '../components/ChatInterface'
import ChatRoom from '../components/ChatRoom'
import MatchCard from '../components/MatchCard'
import PushNotifications from '../components/PushNotifications'
import AgentFloatingBall from '../components/AgentFloatingBall'
import { FeaturesDrawer, FeaturesButton, Feature } from '../components/FeaturesDrawer'
import LanguageSwitcher from '../components/LanguageSwitcher'
import HerAvatar from '../assets/her-avatar.svg'
import { chatApi, conversationMatchingApi } from '../api'
import './HomePage.less'

const { Header, Content } = Layout
const { Text } = Typography

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
  const userId = userInfo?.username || 'user-anonymous-dev'

  // 已通知的消息 ID 集合，避免重复弹窗
  const notifiedMessageIds = useRef<Set<string>>(new Set())

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
          const totalUnread = response.reduce((sum, conv) => sum + (conv.unread_count || 0), 0)

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
            const partnerId = conv.user_id_1 === userId ? conv.user_id_2 : conv.user_id_1
            const cachedMatch = matchesCacheRef.current[partnerId]
            const partnerName = cachedMatch?.user?.name || partnerId

            notification.info({
              message: '收到新消息',
              description: `${partnerName}: ${conv.last_message_preview || '发来了一条消息'}`,
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
                      avatar: undefined,
                      avatar_url: undefined,
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
    // 关闭详情弹窗
    setSelectedMatch(null)
  }

  const handleBackToChat = () => {
    setChatRoomMatch(null)
  }

  const handleChatInitialMatchConsumed = () => {
    setChatInitialMatch(null)
  }

  // 打开聊天室（从 ChatInterface 回调）
  const handleOpenChatRoom = (partnerId: string, partnerName: string) => {
    // 创建匹配对象
    const match: MatchCandidate = {
      user: {
        id: partnerId,
        name: partnerName,
        avatar: undefined,
        avatar_url: undefined,
      },
      compatibility_score: 0,
      score: 0,
    }
    setChatRoomMatch(match)
  }

  // 处理功能选择 - 在对话区生成功能卡片
  const handleFeatureSelect = (feature: Feature) => {
    message.info(`正在打开「${feature.name}」...`)

    // TODO: 触发 ChatInterface 生成对应的功能卡片
    // 这里可以通过事件或状态传递给 ChatInterface
    window.dispatchEvent(new CustomEvent('trigger-feature', {
      detail: { feature }
    }))
  }

  const renderView = () => {
    if (chatRoomMatch) {
      return (
        <div className="chat-room-view">
          <ChatRoom
            match={chatRoomMatch}
            onBack={handleBackToChat}
          />
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
            <PushNotifications
                unreadCount={unreadCount}
                conversations={conversations}
                matchesCache={matchesCache}
                onOpenChatRoom={handleOpenChatRoom}
              />
            {/* 聊天室模式下隐藏功能按钮，专注聊天 */}
            {!chatRoomMatch && <FeaturesButton onClick={() => setFeaturesDrawerOpen(true)} />}
            <Space>
              {userInfo && (
                <Text type="secondary" style={{ fontSize: 14 }}>
                  {userInfo.name || userInfo.username}
                </Text>
              )}
              <Button
                type="text"
                icon={<UserOutlined />}
                onClick={() => onLogout?.()}
                size="small"
                className="logout-btn"
              >
                {t('auth.logout')}
              </Button>
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
          <MatchCard
            match={selectedMatch}
            onLike={() => {}}
            onPass={() => {}}
            onSuperLike={() => {}}
            onMessage={() => handleStartChat(selectedMatch)}
          />
        </Drawer>
      )}

      {/* 功能抽屉 - 轻量级功能入口 */}
      <FeaturesDrawer
        open={featuresDrawerOpen}
        onClose={() => setFeaturesDrawerOpen(false)}
        onFeatureSelect={handleFeatureSelect}
      />

      {/* PWA 安装提示 - 临时禁用，方便调试 */}
      {/* <PWAInstallPrompt /> */}

      {/* 悬浮球 - 快速对话入口（只在聊天室模式显示，沉浸式聊天不显示数字） */}
      {chatRoomMatch && (
        <AgentFloatingBall
          visible={true}
          hasNewMessage={hasNewMessage}
          chatContext={{
            partnerId: chatRoomMatch.user?.id || '',
            partnerName: chatRoomMatch.user?.name || 'TA',
          }}
        />
      )}
    </Layout>
  )
}

export default HomePage
