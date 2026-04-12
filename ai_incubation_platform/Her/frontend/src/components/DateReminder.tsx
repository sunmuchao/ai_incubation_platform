/**
 * 约会提醒组件
 *
 * 提醒用户的约会安排：
 * - 创建约会计划
 * - 约会前提醒
 * - 约会准备建议
 */

import React, { useState, useEffect } from 'react'
import {
  Modal, Button, Space, Typography, Card, DatePicker, Input, Select,
  Tag, List, Avatar, message, Divider, Spin, Progress, Checkbox
} from 'antd'
import {
  CalendarOutlined, ClockCircleOutlined, EnvironmentOutlined,
  BulbOutlined, HeartOutlined, CheckCircleOutlined, PlusOutlined
} from '@ant-design/icons'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 时间预算选项
const TIME_BUDGET_OPTIONS = [
  { value: 'quick', label: '快速约会（1-2小时）', examples: '咖啡厅、公园散步' },
  { value: 'half_day', label: '半天约会（3-5小时）', examples: '看电影+用餐' },
  { value: 'full_day', label: '全天约会', examples: '郊游、主题乐园' },
]

// 活动类型选项
const ACTIVITY_OPTIONS = [
  '咖啡厅聊天',
  '餐厅用餐',
  '看电影',
  '公园散步',
  '博物馆参观',
  '户外运动',
  '音乐会',
  '其他',
]

interface DatePlan {
  plan_id: string
  partner_id: string
  date_time: string
  location: string
  activity: string
  notes?: string
  status: string
  time_until?: any
}

interface DateReminderProps {
  visible: boolean
  userId: string
  onClose: () => void
  onPlanCreated?: (plan: DatePlan) => void
}

/**
 * 约会提醒弹窗
 */
const DateReminder: React.FC<DateReminderProps> = ({
  visible,
  userId,
  onClose,
  onPlanCreated
}) => {
  const [loading, setLoading] = useState(false)
  const [upcomingDates, setUpcomingDates] = useState<DatePlan[]>([])
  const [showCreateForm, setShowCreateForm] = useState(false)

  // 创建表单状态
  const [partnerId, setPartnerId] = useState('')
  const [dateTime, setDateTime] = useState<any>(null)
  const [location, setLocation] = useState('')
  const [activity, setActivity] = useState('')
  const [notes, setNotes] = useState('')
  const [reminders, setReminders] = useState({
    one_day_before: true,
    three_hours_before: true,
    one_hour_before: true,
  })
  const [creating, setCreating] = useState(false)

  // 加载即将到来的约会
  useEffect(() => {
    if (visible) {
      loadUpcomingDates()
    }
  }, [visible])

  const loadUpcomingDates = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/date-reminder/upcoming/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setUpcomingDates(data.dates || [])
      }
    } catch (error) {
      // 静默失败
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePlan = async () => {
    if (!partnerId || !dateTime || !location || !activity) {
      message.warning('请填写完整的约会信息')
      return
    }

    setCreating(true)
    try {
      const response = await fetch(`/api/date-reminder/create?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          partner_id: partnerId,
          date_time: dateTime.toISOString(),
          location,
          activity,
          notes,
          reminder_settings: reminders
        })
      })

      if (response.ok) {
        const data = await response.json()
        message.success('约会计划已创建')
        setShowCreateForm(false)
        loadUpcomingDates()
        if (onPlanCreated) {
          onPlanCreated(data)
        }
      } else {
        message.error('创建失败')
      }
    } catch (error) {
      message.error('创建失败')
    } finally {
      setCreating(false)
    }
  }

  // 格式化时间显示
  const formatTimeUntil = (timeUntil: any) => {
    if (!timeUntil) return ''

    const { days, hours, minutes } = timeUntil
    if (days > 0) {
      return `${days}天${hours}小时后`
    }
    if (hours > 0) {
      return `${hours}小时${minutes}分钟后`
    }
    return `${minutes}分钟后`
  }

  // 渲染即将到来的约会
  const renderUpcomingDates = () => {
    if (loading) {
      return <Spin size="large" tip="加载约会..." />
    }

    if (upcomingDates.length === 0) {
      return (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <CalendarOutlined style={{ fontSize: 48, color: '#ccc' }} />
          <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>
            暂无即将到来的约会
          </Text>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setShowCreateForm(true)}
            style={{
              marginTop: 16,
              background: PRIMARY_COLOR,
              borderColor: PRIMARY_COLOR,
            }}
          >
            创建约会计划
          </Button>
        </div>
      )
    }

    return (
      <div>
        <List
          dataSource={upcomingDates}
          renderItem={(date) => (
            <Card
              size="small"
              style={{
                marginBottom: 8,
                borderRadius: 12,
              }}
            >
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space direction="vertical" size="small">
                  <Space>
                    <CalendarOutlined style={{ color: PRIMARY_COLOR }} />
                    <Text strong>{date.activity}</Text>
                    <Tag color={date.status === 'scheduled' ? 'blue' : 'green'}>
                      {date.status === 'scheduled' ? '待进行' : '已完成'}
                    </Tag>
                  </Space>

                  <Space size="small">
                    <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(date.date_time).toLocaleString('zh-CN')}
                    </Text>
                    <Tag style={{ fontSize: 10 }}>
                      {formatTimeUntil(date.time_until)}
                    </Tag>
                  </Space>

                  <Space size="small">
                    <EnvironmentOutlined style={{ color: '#999', fontSize: 12 }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {date.location}
                    </Text>
                  </Space>
                </Space>

                <Button
                  type="text"
                  icon={<BulbOutlined style={{ color: '#FFD700' }} />}
                  onClick={() => message.info('准备建议功能开发中...')}
                >
                  准备建议
                </Button>
              </Space>
            </Card>
          )}
        />

        <Button
          type="primary"
          block
          icon={<PlusOutlined />}
          onClick={() => setShowCreateForm(true)}
          style={{
            marginTop: 16,
            background: PRIMARY_COLOR,
            borderColor: PRIMARY_COLOR,
            borderRadius: 12
          }}
        >
          创建新约会
        </Button>
      </div>
    )
  }

  // 渲染创建表单
  const renderCreateForm = () => {
    return (
      <div>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* 对方 ID */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>对方 ID</Text>
            <Input
              placeholder="输入对方用户 ID"
              value={partnerId}
              onChange={(e) => setPartnerId(e.target.value)}
            />
          </div>

          {/* 约会时间 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>约会时间</Text>
            <DatePicker
              showTime
              style={{ width: '100%' }}
              value={dateTime}
              onChange={setDateTime}
              placeholder="选择约会时间"
            />
          </div>

          {/* 约会地点 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>约会地点</Text>
            <Input
              placeholder="输入约会地点"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>

          {/* 约会活动 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>约会活动</Text>
            <Select
              style={{ width: '100%' }}
              value={activity}
              onChange={setActivity}
              options={ACTIVITY_OPTIONS.map(a => ({ label: a, value: a }))}
              placeholder="选择活动类型"
            />
          </div>

          {/* 备注 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>备注（可选）</Text>
            <Input.TextArea
              placeholder="添加备注..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 4 }}
            />
          </div>

          {/* 提醒设置 */}
          <Card size="small" style={{ borderRadius: 12 }}>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>
              提醒设置
            </Text>
            <Space direction="vertical" size="small">
              <Checkbox
                checked={reminders.one_day_before}
                onChange={(e) => setReminders(prev => ({ ...prev, one_day_before: e.target.checked }))}
              >
                提前 24 小时提醒
              </Checkbox>
              <Checkbox
                checked={reminders.three_hours_before}
                onChange={(e) => setReminders(prev => ({ ...prev, three_hours_before: e.target.checked }))}
              >
                提前 3 小时提醒
              </Checkbox>
              <Checkbox
                checked={reminders.one_hour_before}
                onChange={(e) => setReminders(prev => ({ ...prev, one_hour_before: e.target.checked }))}
              >
                提前 1 小时提醒
              </Checkbox>
            </Space>
          </Card>

          {/* 操作按钮 */}
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Button onClick={() => setShowCreateForm(false)}>
              取消
            </Button>
            <Button
              type="primary"
              loading={creating}
              onClick={handleCreatePlan}
              style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR }}
            >
              创建计划
            </Button>
          </Space>
        </Space>
      </div>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <CalendarOutlined style={{ color: PRIMARY_COLOR }} />
          <span>约会提醒</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={500}
      styles={{ body: { padding: 16 } }}
    >
      {showCreateForm ? renderCreateForm() : renderUpcomingDates()}
    </Modal>
  )
}

/**
 * 约会提醒按钮
 */
export const DateReminderButton: React.FC<{
  userId: string
  onPlanCreated?: (plan: DatePlan) => void
}> = ({
  userId,
  onPlanCreated
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Button
        type="text"
        icon={<CalendarOutlined style={{ color: PRIMARY_COLOR }} />}
        onClick={() => setModalVisible(true)}
        title="约会提醒"
      />
      <DateReminder
        visible={modalVisible}
        userId={userId}
        onClose={() => setModalVisible(false)}
        onPlanCreated={onPlanCreated}
      />
    </>
  )
}

export default DateReminder