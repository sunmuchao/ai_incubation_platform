/**
 * Your Turn 提醒组件
 *
 * 参考 Hinge 的 Your Turn 机制：
 * - 显示待回复的对话列表
 * - 提醒用户回复，避免对话中断
 * - 支持忽略提醒
 */

import React, { useState, useEffect } from 'react'
import { Badge, Button, Card, List, Space, Typography, Empty, Spin, message } from 'antd'
import { CommentOutlined, ClockCircleOutlined, CloseOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { yourTurnApi } from '../api/yourTurnApi'

const { Text, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

interface PendingReminder {
  conversation_id: string
  partner_id: string
  partner_name?: string
  last_message_content: string
  last_message_time: string
  hours_waiting: number
  is_your_turn: boolean
}

interface YourTurnReminderProps {
  userId: string
  onOpenChat?: (partnerId: string, partnerName: string) => void
  maxDisplay?: number // 最大显示数量
}

/**
 * Your Turn 提醒列表组件
 */
export const YourTurnReminder: React.FC<YourTurnReminderProps> = ({
  userId,
  onOpenChat,
  maxDisplay = 5
}) => {
  const [reminders, setReminders] = useState<PendingReminder[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<{ pending_count: number; total_waiting_hours: number } | null>(null)

  // 加载待处理提醒
  useEffect(() => {
    loadReminders()
    // 每 5 分钟刷新一次
    const interval = setInterval(loadReminders, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userId])

  const loadReminders = async () => {
    try {
      setLoading(true)
      const [reminderList, statsData] = await Promise.all([
        yourTurnApi.getPendingReminders(userId),
        yourTurnApi.getReminderStats(userId)
      ])
      setReminders(reminderList.slice(0, maxDisplay))
      setStats(statsData)
    } catch (error) {
      console.error('Failed to load Your Turn reminders:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDismiss = async (conversationId: string) => {
    try {
      await yourTurnApi.dismissReminder(userId, conversationId)
      message.success('已忽略提醒')
      // 移除本地列表
      setReminders(prev => prev.filter(r => r.conversation_id !== conversationId))
      setStats(prev => prev ? { ...prev, pending_count: prev.pending_count - 1 } : null)
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleReply = async (reminder: PendingReminder) => {
    // 标记提醒已显示
    await yourTurnApi.markReminderShown(userId, reminder.conversation_id)

    // 打开聊天
    if (onOpenChat) {
      onOpenChat(reminder.partner_id, reminder.partner_name || 'TA')
    }

    // 移除本地列表
    setReminders(prev => prev.filter(r => r.conversation_id !== reminder.conversation_id))
  }

  const formatWaitingTime = (hours: number): string => {
    if (hours < 24) {
      return `${hours}小时`
    }
    const days = Math.floor(hours / 24)
    const remainingHours = hours % 24
    if (remainingHours === 0) {
      return `${days}天`
    }
    return `${days}天${remainingHours}小时`
  }

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="small" />
      </div>
    )
  }

  if (reminders.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无待回复消息"
        style={{ padding: 16 }}
      />
    )
  }

  return (
    <div className="your-turn-reminder">
      {/* 顶部统计 */}
      {stats && stats.pending_count > 0 && (
        <div style={{
          padding: '8px 16px',
          background: 'rgba(200, 139, 139, 0.1)',
          borderRadius: 8,
          marginBottom: 12
        }}>
          <Space>
            <Badge status="warning" />
            <Text style={{ color: PRIMARY_COLOR }}>
              {stats.pending_count} 个对话等待回复
            </Text>
            <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              最长 {formatWaitingTime(stats.total_waiting_hours)}
            </Text>
          </Space>
        </div>
      )}

      {/* 提醒列表 */}
      <List
        dataSource={reminders}
        renderItem={(reminder) => (
          <Card
            size="small"
            style={{
              marginBottom: 8,
              borderRadius: 12,
              border: `1px solid rgba(200, 139, 139, 0.2)`,
            }}
            className="reminder-card"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {/* 左侧：头像和消息 */}
              <div style={{ flex: 1 }}>
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Space>
                    <Text strong>{reminder.partner_name || 'TA'}</Text>
                    <Badge count="Your Turn" style={{
                      backgroundColor: PRIMARY_COLOR,
                      fontSize: 10,
                      height: 18,
                      lineHeight: '18px'
                    }} />
                  </Space>
                  <Paragraph
                    ellipsis={{ rows: 1 }}
                    style={{ fontSize: 13, color: '#666', margin: 0 }}
                  >
                    {reminder.last_message_content || '发来了一条消息'}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {formatWaitingTime(reminder.hours_waiting)}前
                  </Text>
                </Space>
              </div>

              {/* 右侧：操作按钮 */}
              <Space direction="vertical" size={4}>
                <Button
                  type="primary"
                  size="small"
                  icon={<CommentOutlined />}
                  onClick={() => handleReply(reminder)}
                  style={{
                    background: PRIMARY_COLOR,
                    borderColor: PRIMARY_COLOR,
                    borderRadius: 8,
                  }}
                >
                  回复
                </Button>
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={() => handleDismiss(reminder.conversation_id)}
                  style={{ color: '#999', fontSize: 12 }}
                >
                  忽略
                </Button>
              </Space>
            </div>
          </Card>
        )}
      />

      {/* 底部提示 */}
      <div style={{ padding: '8px 0', textAlign: 'center' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          💡 及时回复能让对话更流畅
        </Text>
      </div>

      <style>{`
        .your-turn-reminder .reminder-card:hover {
          box-shadow: 0 2px 8px rgba(200, 139, 139, 0.15);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </div>
  )
}

/**
 * Your Turn 指示器（放在 Header 或消息列表）
 */
interface YourTurnIndicatorProps {
  userId: string
  onClick?: () => void
}

export const YourTurnIndicator: React.FC<YourTurnIndicatorProps> = ({
  userId,
  onClick
}) => {
  const [count, setCount] = useState(0)

  useEffect(() => {
    loadCount()
    const interval = setInterval(loadCount, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userId])

  const loadCount = async () => {
    try {
      const stats = await yourTurnApi.getReminderStats(userId)
      setCount(stats.pending_count)
    } catch (error) {
      // 静默失败
    }
  }

  if (count === 0) {
    return null
  }

  return (
    <div
      onClick={onClick}
      style={{
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 12px',
        borderRadius: 12,
        background: 'rgba(200, 139, 139, 0.15)',
      }}
    >
      <CommentOutlined style={{ color: PRIMARY_COLOR, fontSize: 14 }} />
      <Text style={{ color: PRIMARY_COLOR, fontSize: 13 }}>
        Your Turn
      </Text>
      <Badge
        count={count}
        style={{
          backgroundColor: PRIMARY_COLOR,
          minWidth: 18,
          height: 18,
          lineHeight: '18px',
          fontSize: 10,
        }}
      />
      <ArrowRightOutlined style={{ color: '#999', fontSize: 12 }} />
    </div>
  )
}

export default YourTurnReminder