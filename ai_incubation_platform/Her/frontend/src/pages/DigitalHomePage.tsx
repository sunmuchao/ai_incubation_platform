/**
 * P16 数字小家页面
 * 功能：
 * 1. 情侣空间展示
 * 2. 共同记忆收藏
 * 3. 关系成长追踪
 */

import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Avatar,
  Statistic,
  Progress,
  Timeline,
  Image,
  Button,
  Empty,
  Spin,
  Tag,
  Tooltip,
} from 'antd'
import AgentFloatingBall from '../components/AgentFloatingBall'
import {
  HomeOutlined,
  HeartOutlined,
  CalendarOutlined,
  PictureOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  FireOutlined,
  StarOutlined,
} from '@ant-design/icons'
import { milestoneApi } from '../api/p10_api'
import type { Milestone } from '../types/p10_types'
import './DigitalHomePage.less'

const { Text, Title, Paragraph } = Typography

const DIGITAL_HOME_STYLES = {
  container: {
    padding: '24px',
    minHeight: '100%',
    background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '32px',
    color: '#fff',
    textShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  coupleCard: {
    background: 'rgba(255,255,255,0.9)',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '24px',
    boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
  },
  statCard: {
    background: 'rgba(255,255,255,0.9)',
    borderRadius: '12px',
    padding: '16px',
    textAlign: 'center' as const,
  },
  milestoneCard: {
    background: 'rgba(255,255,255,0.9)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '16px',
  },
  avatarGroup: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '16px',
  },
  heartBetween: {
    fontSize: '24px',
    color: '#ff4d4f',
    margin: '0 16px',
    animation: 'heartbeat 1.5s ease-in-out infinite',
  },
}

interface DigitalHomePageProps {
  userId?: string
  partnerId?: string
}

const DigitalHomePage: React.FC<DigitalHomePageProps> = ({ userId, partnerId }) => {
  const [loading, setLoading] = useState(false)
  const [milestones, setMilestones] = useState<Milestone[]>([])
  const [relationshipDays, setRelationshipDays] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const [hasNewMessage, setHasNewMessage] = useState(false)

  const currentUserId = userId || localStorage.getItem('user_info')?.username || 'anonymous'
  const currentPartnerId = partnerId || 'user_002' // TODO: 从关系状态获取

  useEffect(() => {
    loadMilestones()
  }, [])

  const loadMilestones = async () => {
    setLoading(true)
    try {
      const result = await milestoneApi.getMilestoneTimeline(
        currentUserId,
        currentPartnerId,
        false
      )
      setMilestones(result.milestones || [])
      setRelationshipDays(result.relationship_duration_days || 0)
    } catch (error) {
      console.error('Failed to load milestones:', error)
    } finally {
      setLoading(false)
    }
  }

  const getMilestoneIcon = (type: string) => {
    const iconMap: Record<string, string> = {
      first_match: '🎉',
      first_chat: '💬',
      first_date: '🍽️',
      first_video_call: '📹',
      relationship_start: '💕',
      anniversary: '🎊',
    }
    return iconMap[type] || '📌'
  }

  const getMilestoneTitle = (type: string) => {
    const titleMap: Record<string, string> = {
      first_match: '第一次匹配',
      first_chat: '第一次聊天',
      first_date: '第一次约会',
      first_video_call: '第一次视频通话',
      relationship_start: '开始交往',
      anniversary: '纪念日',
    }
    return titleMap[type] || type
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px' }}>
        <Spin size="large" tip="加载数字小家..." />
      </div>
    )
  }

  return (
    <div style={DIGITAL_HOME_STYLES.container}>
      <div style={DIGITAL_HOME_STYLES.header}>
        <Title style={{ color: '#fff', marginBottom: 8 }}>
          <HomeOutlined /> 我们的数字小家
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.9)', fontSize: '16px' }}>
          记录每一个美好瞬间，见证关系的成长
        </Text>
      </div>

      {/* 情侣空间卡片 */}
      <Card style={DIGITAL_HOME_STYLES.coupleCard}>
        <div style={DIGITAL_HOME_STYLES.avatarGroup}>
          <Avatar
            size={80}
            src="https://api.dicebear.com/7.x/avataaars.svg?seed=user1"
            style={{ backgroundColor: '#1890ff' }}
          />
          <span style={DIGITAL_HOME_STYLES.heartBetween}>
            <HeartOutlined />
          </span>
          <Avatar
            size={80}
            src="https://api.dicebear.com/7.x/avataaars.svg?seed=user2"
            style={{ backgroundColor: '#ff4d4f' }}
          />
        </div>

        <Title level={4} style={{ textAlign: 'center', marginBottom: 24 }}>
          我们已经在一起 {relationshipDays} 天了
        </Title>

        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <div style={DIGITAL_HOME_STYLES.statCard}>
              <Statistic
                title="里程碑"
                value={milestones.length}
                suffix="个"
                valueStyle={{ color: '#1890ff' }}
              />
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={DIGITAL_HOME_STYLES.statCard}>
              <Statistic
                title="默契度"
                value={85}
                suffix="%"
                valueStyle={{ color: '#52c41a' }}
              />
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={DIGITAL_HOME_STYLES.statCard}>
              <Statistic
                title="共同兴趣"
                value={12}
                suffix="个"
                valueStyle={{ color: '#faad14' }}
              />
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div style={DIGITAL_HOME_STYLES.statCard}>
              <Statistic
                title="关系温度"
                value={92}
                suffix="°C"
                valueStyle={{ color: '#ff4d4f' }}
              />
            </div>
          </Col>
        </Row>
      </Card>

      {/* 关系进度 */}
      <Card style={{ marginBottom: '24px', background: 'rgba(255,255,255,0.9)' }}>
        <Title level={5}>
          <FireOutlined /> 关系成长进度
        </Title>
        <div style={{ marginTop: '16px' }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text>相识阶段</Text>
              <Text type="success">已完成</Text>
            </div>
            <Progress percent={100} strokeColor="#52c41a" />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text>了解阶段</Text>
              <Text type="success">已完成</Text>
            </div>
            <Progress percent={100} strokeColor="#52c41a" />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text>交往期</Text>
              <Text>{Math.min(relationshipDays, 90)}/90 天</Text>
            </div>
            <Progress
              percent={Math.min((relationshipDays / 90) * 100, 100)}
              strokeColor="#1890ff"
            />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <Text>稳定期</Text>
              <Text type="secondary">进行中</Text>
            </div>
            <Progress
              percent={Math.max(0, ((relationshipDays - 90) / 180) * 100)}
              strokeColor="#722ed1"
            />
          </div>
        </div>
      </Card>

      {/* 里程碑时间线 */}
      <Card style={{ background: 'rgba(255,255,255,0.9)' }}>
        <Title level={5}>
          <CalendarOutlined /> 我们的里程碑
        </Title>
        {milestones.length > 0 ? (
          <Timeline
            style={{ marginTop: '24px' }}
            items={milestones.map((milestone) => ({
              key: milestone.id,
              color: 'red',
              dot: getMilestoneIcon(milestone.milestone_type),
              children: (
                <div>
                  <Text strong>{getMilestoneTitle(milestone.milestone_type)}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {new Date(milestone.milestone_date).toLocaleDateString()}
                  </Text>
                  {milestone.description && (
                    <Paragraph ellipsis={{ rows: 2 }} style={{ marginTop: '8px' }}>
                      {milestone.description}
                    </Paragraph>
                  )}
                </div>
              ),
            }))}
          />
        ) : (
          <Empty description="暂无里程碑记录" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button type="primary">记录第一个里程碑</Button>
          </Empty>
        )}
      </Card>

      {/* 照片墙占位 */}
      <Card style={{ marginTop: '24px', background: 'rgba(255,255,255,0.9)' }}>
        <Title level={5}>
          <PictureOutlined /> 我们的回忆
        </Title>
        <Empty description="照片墙开发中..." />
      </Card>

      {/* 悬浮球 - 快速对话入口 */}
      <AgentFloatingBall
        visible={true}
        unreadCount={unreadCount}
        hasNewMessage={hasNewMessage}
      />
    </div>
  )
}

export default DigitalHomePage
