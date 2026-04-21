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
import { getCurrentUserId } from '../hooks/useCurrentUserId'
import './PushNotifications.less'

const { Text } = Typography
const MAX_RECENT_CONVERSATIONS = 30
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

interface ConversationMessage {
  id: string
  user_id_1: string
  user_id_2: string
  last_message_preview?: string
  last_message_at?: string
  partner_id?: string
  partner_name?: string
  partner_avatar_url?: string
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
    return getCurrentUserId()
  }, [])

  // 微信式：按最近消息时间排序，未读/已读都提供快速入口
  const sortedConversations = React.useMemo(() => {
    return [...conversations]
      .filter((conv) => {
        const partnerId = conv.partner_id || (conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1)
        // 过滤脏数据/占位会话：匿名用户、自己和自己、无最近消息时间
        if (!partnerId || partnerId === 'user-anonymous-dev' || partnerId === currentUserId) {
          return false
        }
        if (!conv.last_message_at) {
          return false
        }
        return true
      })
      .sort((a, b) => {
        const ta = new Date(a.last_message_at || 0).getTime()
        const tb = new Date(b.last_message_at || 0).getTime()
        return tb - ta
      })
      .slice(0, MAX_RECENT_CONVERSATIONS)
  }, [conversations])

  const unreadConversations = React.useMemo(() => {
    return sortedConversations.filter(conv => conv.unread_count > 0)
  }, [sortedConversations])

  const readConversations = React.useMemo(() => {
    return sortedConversations.filter(conv => conv.unread_count <= 0)
  }, [sortedConversations])

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
    const partnerId = conv.partner_id || (conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1)
    // 从缓存获取对方信息
    const cachedMatch = matchesCache[partnerId]
    const partnerName = normalizeDisplayName(
      conv.partner_name,
      cachedMatch?.user?.name,
      partnerId
    )

    // 预清零：点击会话后先本地更新未读状态，避免等待轮询导致的“已读仍显示未读”
    window.dispatchEvent(new CustomEvent('conversation-read', {
      detail: { partnerId }
    }))

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
              <Spin tip={t('common.loading')}>
                <div style={{ padding: 20 }} />
              </Spin>
            </div>
          ) : sortedConversations.length === 0 ? (
            <Empty description={t('notification.noNewMessages')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <>
              {unreadConversations.length > 0 && (
                <div className="notification-section">
                  <Text className="notification-section-title">未读消息</Text>
                  <List
                    dataSource={unreadConversations}
                    renderItem={(conv) => {
                      const partnerId = conv.partner_id || (conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1)
                      const cachedMatch = matchesCache[partnerId]
                      const partnerName = normalizeDisplayName(
                        conv.partner_name,
                        cachedMatch?.user?.name,
                        partnerId
                      )
                      const partnerAvatar = conv.partner_avatar_url || cachedMatch?.user?.avatar || cachedMatch?.user?.avatar_url

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
                </div>
              )}

              {readConversations.length > 0 && (
                <div className="notification-section">
                  <Text className="notification-section-title">最近聊天</Text>
                  <List
                    dataSource={readConversations}
                    renderItem={(conv) => {
                      const partnerId = conv.partner_id || (conv.user_id_1 === currentUserId ? conv.user_id_2 : conv.user_id_1)
                      const cachedMatch = matchesCache[partnerId]
                      const partnerName = normalizeDisplayName(
                        conv.partner_name,
                        cachedMatch?.user?.name,
                        partnerId
                      )
                      const partnerAvatar = conv.partner_avatar_url || cachedMatch?.user?.avatar || cachedMatch?.user?.avatar_url

                      return (
                        <List.Item
                          className="notification-item"
                          onClick={() => handleConversationClick(conv)}
                          style={{ cursor: 'pointer' }}
                        >
                          <List.Item.Meta
                            avatar={<Avatar size={48} src={partnerAvatar} icon={<UserOutlined />} />}
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
                              </div>
                            }
                          />
                        </List.Item>
                      )
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </Drawer>
    </>
  )
}

export default PushNotifications