/**
 * 聊天消息通知组件
 *
 * 功能：
 * - 显示聊天消息未读数
 * - 点击显示"谁发了什么消息"列表
 * - 点击消息跳转到对应聊天室
 */

import React from 'react'
import { Badge, Drawer, List, Avatar, Typography, Button, Space, Empty, Spin } from 'antd'
import { BellOutlined, UserOutlined, MessageOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate } from '../types'
import './PushNotifications.less'

const { Text } = Typography

interface ConversationMessage {
  id: string
  user_id_1: string
  user_id_2: string
  last_message_preview?: string
  last_message_at?: string
  unread_count: number
}

interface PushNotificationsProps {
  unreadCount: number                    // 总未读消息数
  conversations?: ConversationMessage[]  // 会话列表
  matchesCache?: Record<string, MatchCandidate>  // 用户信息缓存
  onOpenChatRoom?: (partnerId: string, partnerName: string) => void  // 打开聊天室
}

const PushNotifications: React.FC<PushNotificationsProps> = ({
  unreadCount,
  conversations = [],
  matchesCache = {},
  onOpenChatRoom,
}) => {
  const { t } = useTranslation()
  const [visible, setVisible] = React.useState(false)
  const [loading, setLoading] = React.useState(false)

  // 从会话中获取当前用户 ID
  const currentUserId = React.useMemo(() => {
    const userInfoStr = localStorage.getItem('user_info')
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr)
        return userInfo.id || userInfo.username
      } catch {
        return 'user-anonymous-dev'
      }
    }
    return 'user-anonymous-dev'
  }, [])

  // 筛选有未读消息的会话
  const unreadConversations = React.useMemo(() => {
    return conversations.filter(conv => conv.unread_count > 0)
  }, [conversations])

  // 打开通知面板
  const handleOpenDrawer = () => {
    setVisible(true)
  }

  // 关闭通知面板
  const handleCloseDrawer = () => {
    setVisible(false)
  }

  // 点击消息，跳转到聊天室
  const handleConversationClick = (conv: ConversationMessage) => {
    // 获取对方 ID
    const partnerId = conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1
    // 从缓存获取对方信息
    const cachedMatch = matchesCache[partnerId]
    const partnerName = cachedMatch?.user?.name || partnerId

    // 调用回调打开聊天室
    onOpenChatRoom?.(partnerId, partnerName)
    handleCloseDrawer()
  }

  // 格式化时间
  const formatTime = (timestamp: string) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return t('time.justNow')
    if (diffMins < 60) return t('time.minutesAgo', { count: diffMins })
    if (diffHours < 24) return t('time.hoursAgo', { count: diffHours })
    if (diffDays < 7) return t('time.daysAgo', { count: diffDays })
    return date.toLocaleDateString('zh-CN')
  }

  return (
    <>
      <Badge count={unreadCount} offset={[-5, 5]}>
        <Button
          type="text"
          icon={<BellOutlined style={{ fontSize: 20 }} />}
          onClick={handleOpenDrawer}
          className="notification-btn"
          loading={loading}
        />
      </Badge>

      <Drawer
        title={
          <div className="drawer-title">
            <MessageOutlined />
            <Text strong>{t('notification.drawerTitle')}</Text>
            {unreadCount > 0 && (
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                {t('notification.unreadCount', { count: unreadCount })}
              </Text>
            )}
          </div>
        }
        placement="right"
        width={400}
        open={visible}
        onClose={handleCloseDrawer}
      >
        <div className="notification-list">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin tip={t('common.loading')} />
            </div>
          ) : unreadConversations.length === 0 ? (
            <Empty description={t('notification.noNewMessages')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={unreadConversations}
              renderItem={(conv) => {
                const partnerId = conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1
                const cachedMatch = matchesCache[partnerId]
                const partnerName = cachedMatch?.user?.name || partnerId
                const partnerAvatar = cachedMatch?.user?.avatar || cachedMatch?.user?.avatar_url

                return (
                  <List.Item
                    className="notification-item unread"
                    onClick={() => handleConversationClick(conv)}
                    style={{ cursor: 'pointer' }}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size={48}
                          src={partnerAvatar}
                          icon={<UserOutlined />}
                        />
                      }
                      title={
                        <div className="notification-title">
                          <Space>
                            <Text strong>{partnerName}</Text>
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {formatTime(conv.last_message_at || '')}
                            </Text>
                          </Space>
                        </div>
                      }
                      description={
                        <div className="notification-content">
                          <Text style={{ fontSize: 13 }}>
                            {conv.last_message_preview || t('conversation.sentMessage')}
                          </Text>
                          {conv.unread_count > 1 && (
                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                              ({conv.unread_count}条)
                            </Text>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )
              }}
            />
          )}
        </div>
      </Drawer>
    </>
  )
}

export default PushNotifications