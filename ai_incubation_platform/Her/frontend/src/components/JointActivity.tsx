/**
 * 共同活动推荐组件
 *
 * 改用 activityDirectorSkill 替代已删除的 /api/joint-activities REST API
 */

import React, { useState } from 'react'
import {
  Modal, Button, Space, Typography, Card, Tag, List, Select, Slider,
  Divider, message, Spin, Avatar, Tooltip, Radio
} from 'antd'
import {
  CompassOutlined, ClockCircleOutlined, DollarOutlined,
  HeartOutlined, EnvironmentOutlined, BulbOutlined,
  CheckCircleOutlined, CopyOutlined
} from '@ant-design/icons'
import { activityDirectorSkill } from '../api/skillClient'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 活动类型配置
const ACTIVITY_TYPES = [
  { type: 'outdoor', name: '户外活动', icon: '🌲', color: 'green' },
  { type: 'entertainment', name: '娱乐休闲', icon: '🎬', color: 'blue' },
  { type: 'food', name: '美食体验', icon: '🍽️', color: 'orange' },
  { type: 'culture', name: '文化艺术', icon: '🎨', color: 'purple' },
  { type: 'sports', name: '运动健身', icon: '💪', color: 'cyan' },
  { type: 'relax', name: '放松休闲', icon: '☕', color: 'pink' },
]

// 时间预算配置
const TIME_BUDGETS = [
  { value: 'quick', label: '快速活动（1-2小时）' },
  { value: 'half_day', label: '半天活动（3-5小时）' },
  { value: 'full_day', label: '全天活动' },
]

// 预算配置
const BUDGETS = [
  { value: 'free', label: '免费' },
  { value: 'low', label: '低预算（50元以下）' },
  { value: 'medium', label: '中等预算（50-200元）' },
  { value: 'high', label: '高预算（200元以上）' },
]

interface Activity {
  activity_name: string
  activity_type: string
  description: string
  suitability_reason: string
  specific_suggestions?: any
  difficulty_level: string
  expected_effect?: string
  estimated_duration?: string
  estimated_cost?: string
  confidence: number
}

interface JointActivityProps {
  visible: boolean
  userId: string
  userProfile: any
  partnerProfile: any
  onClose: () => void
  onSelectActivity?: (activity: Activity) => void
}

/**
 * 共同活动推荐弹窗
 */
const JointActivity: React.FC<JointActivityProps> = ({
  visible,
  userId,
  userProfile,
  partnerProfile,
  onClose,
  onSelectActivity
}) => {
  const [loading, setLoading] = useState(false)
  const [activities, setActivities] = useState<Activity[]>([])
  const [location, setLocation] = useState(userProfile?.location || '')
  const [timeBudget, setTimeBudget] = useState('half_day')
  const [budgetPreference, setBudgetPreference] = useState('medium')
  const [relationshipStage, setRelationshipStage] = useState('dating')
  const [selectedType, setSelectedType] = useState<string | null>(null)

  // 生成推荐
  const handleGenerate = async () => {
    if (!location) {
      message.warning('请输入地理位置')
      return
    }

    setLoading(true)
    try {
      // 改用 Skill 替代已删除的 REST API
      const userId = userProfile?.id || 'user-test-001'
      const partnerId = partnerProfile?.id || 'partner-test-001'

      const result = await activityDirectorSkill.recommendActivity(
        userId,
        partnerId,
        {
          activity_type: selectedType,
          location: location,
          budget: budgetPreference === 'low' ? 100 : budgetPreference === 'high' ? 500 : 300
        }
      )

      if (result.success) {
        setActivities(result.activities || [])
        message.success('已生成推荐')
      } else {
        message.error(result.ai_message || '生成失败')
      }
    } catch (error) {
      message.error('生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectActivity = (activity: Activity) => {
    if (onSelectActivity) {
      onSelectActivity(activity)
    }
    message.success(`已选择：${activity.activity_name}`)
  }

  // 渲染配置区域
  const renderConfig = () => {
    return (
      <Card size="small" style={{ marginBottom: 16, borderRadius: 12 }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {/* 地理位置 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <EnvironmentOutlined /> 地理位置城市
            </Text>
            <Select
              style={{ width: '100%' }}
              value={location}
              onChange={setLocation}
              placeholder="输入城市名称"
              options={[
                { label: '北京', value: '北京' },
                { label: '上海', value: '上海' },
                { label: '广州', value: '广州' },
                { label: '深圳', value: '深圳' },
                { label: '杭州', value: '杭州' },
              ]}
            />
          </div>

          {/* 时间预算 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined /> 时间预算
            </Text>
            <Select
              style={{ width: '100%' }}
              value={timeBudget}
              onChange={setTimeBudget}
              options={TIME_BUDGETS}
            />
          </div>

          {/* 预算偏好 */}
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <DollarOutlined /> 预算偏好
            </Text>
            <Select
              style={{ width: '100%' }}
              value={budgetPreference}
              onChange={setBudgetPreference}
              options={BUDGETS}
            />
          </div>

          {/* 生成按钮 */}
          <Button
            type="primary"
            block
            icon={<BulbOutlined />}
            loading={loading}
            onClick={handleGenerate}
            style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR }}
          >
            AI 生成推荐
          </Button>
        </Space>
      </Card>
    )
  }

  // 渲染活动列表
  const renderActivities = () => {
    if (loading) {
      return <Spin size="large" tip="AI 正在生成..." />
    }

    if (activities.length === 0) {
      return (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <CompassOutlined style={{ fontSize: 48, color: '#ccc' }} />
          <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>
            配置偏好后点击生成
          </Text>
        </div>
      )
    }

    // 过滤活动类型
    const filteredActivities = selectedType
      ? activities.filter(a => a.activity_type === selectedType)
      : activities

    return (
      <div>
        {/* 类型过滤 */}
        <Space wrap size="small" style={{ marginBottom: 8 }}>
          <Tag
            color={selectedType === null ? PRIMARY_COLOR : 'default'}
            style={{ cursor: 'pointer' }}
            onClick={() => setSelectedType(null)}
          >
            全部
          </Tag>
          {ACTIVITY_TYPES.map(type => (
            <Tag
              key={type.type}
              color={selectedType === type.type ? type.color : 'default'}
              style={{ cursor: 'pointer' }}
              onClick={() => setSelectedType(type.type)}
            >
              {type.icon} {type.name}
            </Tag>
          ))}
        </Space>

        {/* 活动列表 */}
        <List
          dataSource={filteredActivities}
          renderItem={(activity) => (
            <Card
              size="small"
              style={{
                marginBottom: 8,
                borderRadius: 12,
                cursor: 'pointer',
              }}
              onClick={() => handleSelectActivity(activity)}
              className="activity-card"
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {/* 活动名称 */}
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>{activity.activity_name}</Text>
                  <Tag color={ACTIVITY_TYPES.find(t => t.type === activity.activity_type)?.color || 'default'}>
                    {ACTIVITY_TYPES.find(t => t.type === activity.activity_type)?.name || activity.activity_type}
                  </Tag>
                </Space>

                {/* 描述 */}
                <Text>{activity.description}</Text>

                {/* 适合原因 */}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  💡 {activity.suitability_reason}
                </Text>

                {/* 详情 */}
                <Space size="small">
                  {activity.estimated_duration && (
                    <Tag style={{ fontSize: 10 }}>
                      <ClockCircleOutlined /> {activity.estimated_duration}
                    </Tag>
                  )}
                  {activity.estimated_cost && (
                    <Tag style={{ fontSize: 10 }}>
                      <DollarOutlined /> {activity.estimated_cost}
                    </Tag>
                  )}
                  <Tag color={activity.difficulty_level === 'easy' ? 'green' : 'orange'} style={{ fontSize: 10 }}>
                    {activity.difficulty_level === 'easy' ? '适合初次约会' : '适合熟悉后'}
                  </Tag>
                </Space>

                {/* 置信度 */}
                <Progress
                  percent={Math.round(activity.confidence * 100)}
                  strokeColor={PRIMARY_COLOR}
                  showInfo={false}
                  size="small"
                />
              </Space>
            </Card>
          )}
        />
      </div>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <CompassOutlined style={{ color: PRIMARY_COLOR }} />
          <span>共同活动推荐</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="regenerate" onClick={handleGenerate} loading={loading}>
          重新生成
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={500}
      styles={{ body: { padding: 16 } }}
    >
      {/* 配置区域 */}
      {renderConfig()}

      <Divider />

      {/* 活动列表 */}
      {renderActivities()}

      <style>{`
        .activity-card:hover {
          box-shadow: 0 2px 8px rgba(200, 139, 139, 0.15);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </Modal>
  )
}

/**
 * 活动推荐按钮
 */
export const ActivityButton: React.FC<{
  userId: string
  userProfile: any
  partnerProfile: any
  onSelectActivity?: (activity: Activity) => void
}> = ({
  userId,
  userProfile,
  partnerProfile,
  onSelectActivity
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Button
        type="text"
        icon={<CompassOutlined style={{ color: PRIMARY_COLOR }} />}
        onClick={() => setModalVisible(true)}
        title="活动推荐"
      />
      <JointActivity
        visible={modalVisible}
        userId={userId}
        userProfile={userProfile}
        partnerProfile={partnerProfile}
        onClose={() => setModalVisible(false)}
        onSelectActivity={onSelectActivity}
      />
    </>
  )
}

export default JointActivity