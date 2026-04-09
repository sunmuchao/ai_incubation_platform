// AI 主动推送通知组件

import React, { useState, useEffect } from 'react'
import { Badge, Drawer, List, Avatar, Typography, Button, Space, Tag, Empty, Spin } from 'antd'
import { ThunderboltOutlined, HeartOutlined, StarOutlined, RobotOutlined, UserOutlined, BellOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { conversationMatchingApi } from '../api'
import './PushNotifications.less'

const { Text, Paragraph } = Typography

// 最大通知数量限制，防止内存泄漏
const MAX_NOTIFICATIONS = 20

interface PushNotification {
  id: string
  type: 'match' | 'update' | 'suggestion'
  title: string
  message: string
  match?: MatchCandidate
  timestamp: Date
  read: boolean
}

interface PushNotificationsProps {
  onNotificationClick?: (notification: PushNotification) => void
  onMatchSelect?: (match: MatchCandidate) => void
}

const PushNotifications: React.FC<PushNotificationsProps> = ({
  onNotificationClick,
  onMatchSelect,
}) => {
  const [visible, setVisible] = useState(false)
  const [loading, setLoading] = useState(false)
  const [notifications, setNotifications] = useState<PushNotification[]>([])
  const [hasNewPush, setHasNewPush] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // 定期检查 AI 推送
  useEffect(() => {
    checkAiPush()
    const interval = setInterval(checkAiPush, 60000)
    return () => clearInterval(interval)
  }, [])

  const checkAiPush = async () => {
    try {
      const response = await conversationMatchingApi.getAiPushRecommendations()
      if (response.has_push && response.matches && response.matches.length > 0 && response.matches[0]?.user) {
        const newNotification: PushNotification = {
          id: `push-${Date.now()}`,
          type: 'match',
          title: 'AI 为你推荐新对象',
          message: response.message,
          match: response.matches[0],
          timestamp: new Date(response.pushed_at),
          read: false,
        }

        setNotifications((prev) => {
          const exists = prev.some((n) => n.match?.user?.id === response.matches?.[0]?.user?.id)
          if (exists) return prev

          setHasNewPush(true)
          const newNotifications = [newNotification, ...prev]
          // 限制通知数量，移除最旧的通知
          if (newNotifications.length > MAX_NOTIFICATIONS) {
            return newNotifications.slice(0, MAX_NOTIFICATIONS)
          }
          return newNotifications
        })

        // 更新未读数
        setUnreadCount(prev => prev + 1)
      }
    } catch (error: unknown) {
      const isUnauthorized = error instanceof Error &&
        'response' in error &&
        (error as any).response?.status === 401
      if (!isUnauthorized) {
        console.error('Failed to check AI push:', error)
      }
    }
  }

  const handleOpenDrawer = async () => {
    setLoading(true)
    try {
      // 打开时从后端获取最新推送
      const response = await conversationMatchingApi.getAiPushRecommendations()
      if (response.has_push && response.matches && response.matches.length > 0) {
        // 将后端返回的匹配转换为通知
        const newNotifications: PushNotification[] = response.matches.map((match: MatchCandidate, index: number) => ({
          id: `push-${match.user?.id || index}`,
          type: 'match',
          title: 'AI 推荐',
          message: match.reasoning || `与${match.user?.name}匹配度${Math.round((match.score || match.compatibility_score || 0) * 100)}%`,
          match: match,
          timestamp: new Date(),
          read: true, // 打开后标记为已读
        }))
        setNotifications(newNotifications)
      }
    } catch (error) {
      console.error('Failed to fetch AI push:', error)
    } finally {
      setLoading(false)
    }
    setVisible(true)
    setHasNewPush(false)
    setUnreadCount(0)
  }

  const handleCloseDrawer = () => {
    setVisible(false)
  }

  const handleNotificationClick = (notification: PushNotification) => {
    onNotificationClick?.(notification)
    if (notification.match && onMatchSelect) {
      onMatchSelect(notification.match)
    }
    handleCloseDrawer()
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'match':
        return <HeartOutlined />
      case 'update':
        return <ThunderboltOutlined />
      case 'suggestion':
        return <StarOutlined />
      default:
        return <BellOutlined />
    }
  }

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'match':
        return '#f5222d'
      case 'update':
        return '#1890ff'
      case 'suggestion':
        return '#faad14'
      default:
        return '#8c8c8c'
    }
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
            <RobotOutlined />
            <Text strong>AI 推送通知</Text>
          </div>
        }
        placement="right"
        width={400}
        open={visible}
        onClose={handleCloseDrawer}
        footer={
          <Button block onClick={() => setNotifications([])}>
            清空所有通知
          </Button>
        }
      >
        <div className="notification-list">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin tip="加载中..." />
            </div>
          ) : notifications.length === 0 ? (
            <Empty description="暂无新通知" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={notifications}
              renderItem={(item) => (
                <List.Item
                  className={`notification-item ${!item.read ? 'unread' : ''}`}
                  onClick={() => handleNotificationClick(item)}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={getNotificationIcon(item.type)}
                        style={{ backgroundColor: getNotificationColor(item.type) }}
                      />
                    }
                    title={
                      <div className="notification-title">
                        <Text strong>{item.title}</Text>
                        {!item.read && <Tag color="red">新</Tag>}
                      </div>
                    }
                    description={
                      <div className="notification-content">
                        <Text type="secondary" style={{ fontSize: 13 }}>
                          {item.message}
                        </Text>
                        {item.match && (
                          <div className="notification-match-preview">
                            <Avatar
                              size={24}
                              src={item.match.user?.avatar || item.match.user?.avatar_url}
                              icon={<UserOutlined />}
                            />
                            <Text style={{ fontSize: 12 }}>
                              {item.match.user?.name} ·{' '}
                              {Math.round((item.match.score || item.match.compatibility_score || 0) * 100)}% 匹配
                            </Text>
                          </div>
                        )}
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {item.timestamp.toLocaleString('zh-CN')}
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </div>
      </Drawer>
    </>
  )
}

export default PushNotifications
