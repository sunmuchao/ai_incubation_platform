/**
 * P10 关系里程碑组件 - AI Native Generative UI
 */

import React, { useState, useEffect } from 'react'
import { Card, Timeline, Tag, Button, Space, Typography, Progress, Rate, Modal, Empty, Spin } from 'antd'
import {
  HeartOutlined,
  HeartFilled,
  CalendarOutlined,
  StarFilled,
  GiftOutlined,
  TrophyOutlined,
  HistoryOutlined,
  PlusOutlined,
  MessageOutlined,
  CompassOutlined,
  LikeOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import type { Milestone, MilestoneTimeline, MilestoneStatistics } from '../types/milestoneTypes'
import { milestoneApi } from '../api/milestoneApi'
import './RelationshipTimeline.less'

const { Text, Paragraph, Title } = Typography

interface RelationshipTimelineProps {
  userId1: string
  userId2: string
  onComplete?: () => void
}

interface MilestoneCardProps {
  milestone: Milestone
  onCelebrate?: (milestoneId: string) => void
}

// 里程碑卡片组件
const MilestoneCard: React.FC<MilestoneCardProps> = ({ milestone, onCelebrate }) => {
  const [showDetails, setShowDetails] = useState(false)

  const getMilestoneIcon = (type: string) => {
    const iconMap: Record<string, JSX.Element> = {
      first_match: <HeartOutlined />,
      first_chat: <MessageOutlined />,
      first_date: <CompassOutlined />,
      relationship_start: <HeartFilled />,
      anniversary: <StarFilled />,
      engaged: <LikeOutlined />,
      married: <UserAddOutlined />,
    }
    return iconMap[type] || <HistoryOutlined />
  }

  const getMilestoneColor = (type: string) => {
    const colorMap: Record<string, string> = {
      first_match: '#ff4d4f',
      first_chat: '#1890ff',
      first_date: '#faad14',
      relationship_start: '#eb2f96',
      anniversary: '#722ed1',
      engaged: '#fa8c16',
      married: '#f5222d',
    }
    return colorMap[type] || '#1890ff'
  }

  return (
    <>
      <Card
        className="milestone-card"
        hoverable
        onClick={() => setShowDetails(true)}
      >
        <div className="milestone-card-header">
          <div
            className="milestone-icon"
            style={{ backgroundColor: getMilestoneColor(milestone.milestone_type) }}
          >
            {getMilestoneIcon(milestone.milestone_type)}
          </div>
          <div className="milestone-info">
            <Text strong className="milestone-title">{milestone.title}</Text>
            <Text type="secondary" className="milestone-date">
              {new Date(milestone.milestone_date).toLocaleDateString()}
            </Text>
          </div>
        </div>

        <Paragraph
          ellipsis={{ rows: 2 }}
          className="milestone-description"
        >
          {milestone.description}
        </Paragraph>

        {milestone.user_rating && (
          <div className="milestone-rating">
            <Rate disabled value={milestone.user_rating} />
          </div>
        )}

        {milestone.celebration_suggested && !milestone.user_rating && (
          <Button
            type="primary"
            size="small"
            icon={<GiftOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onCelebrate?.(milestone.id)
            }}
          >
            庆祝
          </Button>
        )}
      </Card>

      <Modal
        title={milestone.title}
        open={showDetails}
        onCancel={() => setShowDetails(false)}
        footer={null}
        width={520}
      >
        <div className="milestone-modal-content">
          <div className="milestone-detail-section">
            <Text type="secondary">发生时间</Text>
            <Text strong>{new Date(milestone.milestone_date).toLocaleString()}</Text>
          </div>

          <div className="milestone-detail-section">
            <Text type="secondary">描述</Text>
            <Paragraph>{milestone.description}</Paragraph>
          </div>

          {milestone.ai_analysis && (
            <div className="milestone-detail-section">
              <Text type="secondary">AI 分析</Text>
              <Card size="small" className="ai-analysis-card">
                <div className="ai-significance">
                  <Text strong>重要性评分：</Text>
                  <Progress
                    percent={Math.round(milestone.ai_analysis.significance_score * 100)}
                    size="small"
                    strokeColor="#722ed1"
                  />
                </div>
                <div className="ai-stage">
                  <Text strong>关系阶段：</Text>
                  <Tag color="purple">{milestone.ai_analysis.relationship_stage}</Tag>
                </div>
                {milestone.ai_analysis.suggestions.length > 0 && (
                  <div className="ai-suggestions">
                    <Text strong>AI 建议：</Text>
                    <ul>
                      {milestone.ai_analysis.suggestions.map((suggestion, index) => (
                        <li key={index}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            </div>
          )}

          {milestone.user_note && (
            <div className="milestone-detail-section">
              <Text type="secondary">个人备注</Text>
              <Paragraph className="user-note">{milestone.user_note}</Paragraph>
            </div>
          )}
        </div>
      </Modal>
    </>
  )
}

// 关系时间线组件
const RelationshipTimeline: React.FC<RelationshipTimelineProps> = ({
  userId1,
  userId2,
  onComplete,
}) => {
  const [loading, setLoading] = useState(false)
  const [timeline, setTimeline] = useState<MilestoneTimeline | null>(null)
  const [statistics, setStatistics] = useState<MilestoneStatistics | null>(null)
  const [selectedMilestone, setSelectedMilestone] = useState<Milestone | null>(null)

  useEffect(() => {
    loadTimeline()
    loadStatistics()
  }, [userId1, userId2])

  const loadTimeline = async () => {
    setLoading(true)
    try {
      const data = await milestoneApi.getMilestoneTimeline(userId1, userId2)
      setTimeline(data)
    } catch (error) {
      console.error('Failed to load timeline:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const data = await milestoneApi.getMilestoneStatistics(userId1, userId2)
      setStatistics(data)
    } catch (error) {
      console.error('Failed to load statistics:', error)
    }
  }

  const handleCelebrate = async (milestoneId: string) => {
    try {
      await milestoneApi.celebrateMilestone(milestoneId, 'card')
      loadTimeline()
      onComplete?.()
    } catch (error) {
      console.error('Failed to celebrate milestone:', error)
    }
  }

  const getTimelineColor = (milestoneType: string) => {
    const colorMap: Record<string, string> = {
      first_match: '#ff4d4f',
      first_chat: '#1890ff',
      first_date: '#faad14',
      relationship_start: '#eb2f96',
      anniversary: '#722ed1',
      engaged: '#fa8c16',
      married: '#f5222d',
    }
    return colorMap[milestoneType] || '#1890ff'
  }

  if (loading) {
    return (
      <div className="timeline-loading">
        <Spin size="large" tip="加载关系时间线..." />
      </div>
    )
  }

  if (!timeline || timeline.milestones.length === 0) {
    return (
      <div className="timeline-empty">
        <Empty description="暂无里程碑记录" />
        <Button type="primary" icon={<PlusOutlined />}>
          记录第一个里程碑
        </Button>
      </div>
    )
  }

  return (
    <div className="relationship-timeline">
      {statistics && (
        <div className="timeline-statistics">
          <Card size="small" className="stats-card">
            <Space size="large">
              <div className="stat-item">
                <TrophyOutlined />
                <Text strong>{statistics.total_milestones}</Text>
                <Text type="secondary">里程碑</Text>
              </div>
              <div className="stat-item">
                <CalendarOutlined />
                <Text strong>{statistics.relationship_duration_days}</Text>
                <Text type="secondary">天</Text>
              </div>
              <div className="stat-item">
                <StarFilled />
                <Text strong>{statistics.average_rating.toFixed(1)}</Text>
                <Text type="secondary">平均评分</Text>
              </div>
            </Space>
          </Card>
        </div>
      )}

      <Timeline className="milestone-timeline">
        {timeline.milestones.map((milestone) => (
          <Timeline.Item
            key={milestone.id}
            color={getTimelineColor(milestone.milestone_type)}
          >
            <MilestoneCard
              milestone={milestone}
              onCelebrate={handleCelebrate}
            />
          </Timeline.Item>
        ))}
      </Timeline>
    </div>
  )
}

export default RelationshipTimeline
