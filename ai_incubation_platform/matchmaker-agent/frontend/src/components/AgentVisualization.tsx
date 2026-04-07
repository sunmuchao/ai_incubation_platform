// Agent 状态可视化组件

import React from 'react'
import { Card, Progress, Avatar, Typography, Spin, Tag, Timeline, Alert } from 'antd'
import {
  RobotOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  BellOutlined,
} from '@ant-design/icons'
import type { AgentStatus } from '../../types'
import './AgentVisualization.less'

const { Text, Paragraph } = Typography

interface AgentVisualizationProps {
  status: AgentStatus
  visible?: boolean
}

const AgentVisualization: React.FC<AgentVisualizationProps> = ({ status, visible = true }) => {
  if (!visible) return null

  const getStatusIcon = () => {
    switch (status.status) {
      case 'analyzing':
        return <SearchOutlined spin />
      case 'matching':
        return <HeartOutlined />
      case 'recommending':
        return <ThunderboltOutlined />
      case 'pushing':
        return <BellOutlined />
      default:
        return <RobotOutlined />
    }
  }

  const getStatusColor = () => {
    switch (status.status) {
      case 'analyzing':
        return '#1890ff'
      case 'matching':
        return '#f5222d'
      case 'recommending':
        return '#722ed1'
      case 'pushing':
        return '#faad14'
      default:
        return '#8c8c8c'
    }
  }

  const getStatusText = () => {
    const statusTexts: Record<string, string> = {
      idle: 'AI 红娘待命中',
      analyzing: '正在分析你的偏好...',
      matching: '正在寻找匹配对象...',
      recommending: '正在生成推荐...',
      pushing: '正在推送匹配结果...',
    }
    return statusTexts[status.status] || '处理中...'
  }

  const getActivityTimeline = () => {
    const activities: Array<{ icon: React.ReactNode; text: string; color: string }> = []

    if (status.status === 'analyzing' || status.status === 'matching' ||
        status.status === 'recommending' || status.status === 'pushing') {
      activities.push({
        icon: <SearchOutlined />,
        text: '分析用户偏好',
        color: status.status === 'analyzing' ? '#1890ff' : '#52c41a',
      })
    }

    if (status.status === 'matching' || status.status === 'recommending' || status.status === 'pushing') {
      activities.push({
        icon: <HeartOutlined />,
        text: '扫描候选池',
        color: status.status === 'matching' ? '#f5222d' : '#52c41a',
      })
    }

    if (status.status === 'recommending' || status.status === 'pushing') {
      activities.push({
        icon: <ThunderboltOutlined />,
        text: '深度兼容性分析',
        color: status.status === 'recommending' ? '#722ed1' : '#52c41a',
      })
    }

    if (status.status === 'pushing') {
      activities.push({
        icon: <BellOutlined />,
        text: '生成推荐结果',
        color: '#faad14',
      })
    }

    return activities
  }

  return (
    <Card className="agent-visualization-card">
      <div className="agent-header">
        <Avatar
          size={64}
          icon={getStatusIcon()}
          style={{ backgroundColor: getStatusColor() }}
          className="agent-avatar"
        />
        <div className="agent-status-info">
          <Text strong className="agent-title">
            AI 红娘 Agent
          </Text>
          <div className="agent-status-badge">
            <Spin size="small" spinning={status.status !== 'idle'}>
              <Tag color={getStatusColor()}>{getStatusText()}</Tag>
            </Spin>
          </div>
        </div>
      </div>

      <div className="agent-progress">
        <Progress
          percent={status.progress}
          strokeColor={getStatusColor()}
          trailColor="#f0f0f0"
          showInfo={false}
          size="small"
        />
        {status.current_action && (
          <Text type="secondary" className="agent-action-text">
            {status.current_action}
          </Text>
        )}
      </div>

      {status.status !== 'idle' && (
        <div className="agent-activity">
          <Timeline
            items={getActivityTimeline().map((item) => ({
              color: item.color,
              children: (
                <Text style={{ color: item.color === '#52c41a' ? '#8c8c8c' : item.color }}>
                  {item.text}
                </Text>
              ),
              dot: item.icon,
            }))}
            pending={status.status !== 'idle' ? '正在处理...' : null}
            pendingDot={<Spin size="small" />}
          />
        </div>
      )}

      {status.status === 'idle' && (
        <Alert
          message="AI 红娘已就绪"
          description="告诉我你的需求，我开始为你寻找合适的对象~"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
        />
      )}
    </Card>
  )
}

export default AgentVisualization
