/**
 * P10 约会建议页面 - AI Native Generative UI
 * 功能：
 * 1. 生成约会建议
 * 2. 约会地点推荐
 * 3. 约会策划
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Typography,
  Spin,
  Empty,
  Row,
  Col,
  Tag,
  Rate,
  Modal,
  Form,
  Select,
  Input,
  InputNumber,
  message,
  Statistic,
  Timeline,
  Divider,
} from 'antd'
import AgentFloatingBall from '../components/AgentFloatingBall'
import {
  GiftOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  HeartOutlined,
  CheckOutlined,
  CloseOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { DateSuggestion, DateVenue, DateType } from '../types/milestoneTypes'
import { dateSuggestionApi } from '../api/milestoneApi'
import { authStorage } from '../utils/storage'
import './DateSuggestionsPage.less'

const { Text, Title, Paragraph } = Typography
const { TextArea } = Input

interface DateSuggestionsPageProps {
  userId?: string
}

const DATE_TYPES: { value: DateType; label: string; icon: string }[] = [
  { value: 'coffee', label: '咖啡聊天', icon: '☕' },
  { value: 'dining', label: '美食用餐', icon: '🍽️' },
  { value: 'movie', label: '电影观影', icon: '🎬' },
  { value: 'outdoor', label: '户外活动', icon: '🌳' },
  { value: 'culture', label: '文化艺术', icon: '🎨' },
  { value: 'sports', label: '运动健身', icon: '⚽' },
  { value: 'entertainment', label: '娱乐休闲', icon: '🎮' },
  { value: 'creative', label: '创意手工', icon: '🎭' },
]

const DATE_SUGGESTIONS_PAGE_STYLES = {
  container: {
    padding: '24px',
    minHeight: '100%',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '32px',
    color: '#fff',
  },
  card: {
    marginBottom: '16px',
    borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    transition: 'all 0.3s ease',
  },
  suggestionHeader: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '16px',
  },
  venueInfo: {
    background: '#f5f5f5',
    padding: '12px',
    borderRadius: '8px',
    marginTop: '12px',
  },
  actionButtons: {
    marginTop: '16px',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
  },
}

const DateSuggestionsPage: React.FC<DateSuggestionsPageProps> = ({ userId }) => {
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<DateSuggestion[]>([])
  const [venues, setVenues] = useState<DateVenue[]>([])
  const [selectedSuggestion, setSelectedSuggestion] = useState<DateSuggestion | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [generateForm] = Form.useForm()
  const [unreadCount, setUnreadCount] = useState(0)
  const [hasNewMessage, setHasNewMessage] = useState(false)

  const currentUserId = userId || authStorage.getUserId()

  useEffect(() => {
    loadSuggestions()
  }, [])

  const loadSuggestions = async () => {
    setLoading(true)
    try {
      const result = await dateSuggestionApi.getUserDateSuggestions(currentUserId, undefined, 10)
      setSuggestions(result.suggestions || [])
    } catch (error) {
      console.error('Failed to load date suggestions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateSuggestion = async (values: any) => {
    try {
      setLoading(true)
      const result = await dateSuggestionApi.generateDateSuggestion(
        currentUserId,
        values.target_user_id,
        values.date_type,
        {
          city: values.city,
          budget_range: values.budget_range,
        }
      )
      message.success('约会建议生成成功！')
      setModalVisible(false)
      generateForm.resetFields()
      if (result.suggestion) {
        setSuggestions([result.suggestion, ...suggestions])
      }
    } catch (error) {
      console.error('Failed to generate date suggestion:', error)
      message.error('生成约会建议失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleRespondToSuggestion = async (suggestionId: string, action: 'accept' | 'reject') => {
    try {
      setLoading(true)
      await dateSuggestionApi.respondToDateSuggestion(suggestionId, { action })
      message.success(action === 'accept' ? '已接受约会邀请' : '已拒绝约会邀请')
      loadSuggestions()
    } catch (error) {
      console.error('Failed to respond to suggestion:', error)
      message.error('操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'orange',
      accepted: 'green',
      rejected: 'red',
      completed: 'blue',
    }
    return colorMap[status] || 'default'
  }

  const getStatusText = (status: string) => {
    const textMap: Record<string, string> = {
      pending: '待响应',
      accepted: '已接受',
      rejected: '已拒绝',
      completed: '已完成',
    }
    return textMap[status] || status
  }

  const renderSuggestionCard = (suggestion: DateSuggestion) => (
    <Card
      key={suggestion.id}
      style={DATE_SUGGESTIONS_PAGE_STYLES.card}
      hoverable
      actions={[
        suggestion.status === 'pending' && (
          <Button
            key="accept"
            type="primary"
            icon={<CheckOutlined />}
            onClick={() => handleRespondToSuggestion(suggestion.id, 'accept')}
          >
            接受
          </Button>
        ),
        suggestion.status === 'pending' && (
          <Button
            key="reject"
            danger
            icon={<CloseOutlined />}
            onClick={() => handleRespondToSuggestion(suggestion.id, 'reject')}
          >
            拒绝
          </Button>
        ),
      ].filter(Boolean)}
    >
      <div style={DATE_SUGGESTIONS_PAGE_STYLES.suggestionHeader}>
        <div style={{ fontSize: '32px', marginRight: '12px' }}>
          {DATE_TYPES.find((t) => t.value === suggestion.date_type)?.icon || '📅'}
        </div>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            {DATE_TYPES.find((t) => t.value === suggestion.date_type)?.label || suggestion.date_type}
          </Title>
          <Tag color={getStatusColor(suggestion.status)}>{getStatusText(suggestion.status)}</Tag>
        </div>
      </div>

      <Paragraph ellipsis={{ rows: 2 }}>
        {suggestion.ai_reasoning || 'AI 为你推荐这个约会地点～'}
      </Paragraph>

      {suggestion.venue && (
        <div style={DATE_SUGGESTIONS_PAGE_STYLES.venueInfo}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div>
              <EnvironmentOutlined /> <strong>{suggestion.venue.name}</strong>
            </div>
            <div>
              <Text type="secondary">{suggestion.venue.address}</Text>
            </div>
            <Row gutter={16}>
              <Col>
                <Rate defaultValue={suggestion.venue.rating} disabled />
              </Col>
              <Col>
                <DollarOutlined /> {suggestion.venue.price_level}
              </Col>
            </Row>
          </Space>
        </div>
      )}

      <Divider />

      <Row gutter={16}>
        <Col>
          <Statistic
            title="兼容性评分"
            value={suggestion.compatibility_score}
            precision={1}
            suffix="/ 10"
          />
        </Col>
        <Col>
          <Statistic
            title="预计时长"
            value={suggestion.estimated_duration || '2 小时'}
          />
        </Col>
      </Row>

      {suggestion.suggested_activities && suggestion.suggested_activities.length > 0 && (
        <>
          <Divider orientation="left">推荐活动</Divider>
          <Timeline
            items={suggestion.suggested_activities.map((activity, index) => ({
              key: index,
              color: 'blue',
              children: activity,
            }))}
          />
        </>
      )}
    </Card>
  )

  return (
    <div style={DATE_SUGGESTIONS_PAGE_STYLES.container}>
      <div style={DATE_SUGGESTIONS_PAGE_STYLES.header}>
        <Title style={{ color: '#fff', marginBottom: 8 }}>
          <GiftOutlined /> 约会建议
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
          AI 为你策划每一次浪漫相遇
        </Text>
      </div>

      <div style={{ marginBottom: '24px', textAlign: 'center' }}>
        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
          style={{ background: '#fff', color: '#667eea', border: 'none' }}
        >
          生成约会建议
        </Button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px' }}>
          <Spin size="large" tip="加载约会建议..." />
        </div>
      ) : suggestions.length > 0 ? (
        <Row gutter={16}>
          {suggestions.map((suggestion) => (
            <Col xs={24} md={12} lg={8} key={suggestion.id}>
              {renderSuggestionCard(suggestion)}
            </Col>
          ))}
        </Row>
      ) : (
        <Empty
          description="暂无约会建议"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => setModalVisible(true)}>
            生成第一个约会建议
          </Button>
        </Empty>
      )}

      {/* 生成约会建议弹窗 */}
      <Modal
        title="生成约会建议"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={generateForm}
          layout="vertical"
          onFinish={handleGenerateSuggestion}
        >
          <Form.Item
            name="target_user_id"
            label="约会对象"
            rules={[{ required: true, message: '请选择约会对象' }]}
          >
            <Select placeholder="选择你想邀请的人">
              {/* TODO: 加载匹配对象列表 */}
              <Select.Option value="user_001">示例用户</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="date_type"
            label="约会类型"
            rules={[{ required: true, message: '请选择约会类型' }]}
          >
            <Select placeholder="选择约会类型">
              {DATE_TYPES.map((type) => (
                <Select.Option key={type.value} value={type.value}>
                  {type.icon} {type.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="city"
            label="城市"
            initialValue="上海市"
          >
            <Select placeholder="选择城市">
              <Select.Option value="上海市">上海市</Select.Option>
              <Select.Option value="北京市">北京市</Select.Option>
              <Select.Option value="广州市">广州市</Select.Option>
              <Select.Option value="深圳市">深圳市</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="budget_range"
            label="预算范围 (元)"
          >
            <InputNumber.Range placeholder={[0, 1000]} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading} icon={<ThunderboltOutlined />}>
                生成建议
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 悬浮球 - 快速对话入口 */}
      <AgentFloatingBall
        visible={true}
        unreadCount={unreadCount}
        hasNewMessage={hasNewMessage}
      />
    </div>
  )
}

export default DateSuggestionsPage
