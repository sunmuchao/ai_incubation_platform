/**
 * Generative UI - Agent 状态可视化组件
 * 显示 AI 团购管家的工作状态
 */
import React from 'react'
import { Card, Steps, Progress, Alert, Tag, Space, Typography, Button } from 'antd'
import {
  RobotOutlined,
  SearchOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  BellOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import type { AgentState } from '@/types/chat'

const { Text, Paragraph } = Typography

interface AgentStatusProps {
  state: AgentState
}

export const AgentStatus: React.FC<AgentStatusProps> = ({ state }) => {
  if (state.status === 'idle' || state.status === 'completed') {
    return null
  }

  const getStatusConfig = () => {
    switch (state.status) {
      case 'thinking':
        return {
          icon: <RobotOutlined spin />,
          title: 'AI 正在理解您的需求',
          description: '分析您的输入，识别购买意图...',
          color: 'blue',
        }
      case 'executing':
        return {
          icon: <SyncOutlined spin />,
          title: `正在执行：${state.currentAction || '处理中'}`,
          description: state.message || '请稍候...',
          color: 'green',
        }
      case 'waiting':
        return {
          icon: <BellOutlined />,
          title: '等待确认',
          description: state.message || '请确认是否继续',
          color: 'orange',
        }
      case 'failed':
        return {
          icon: <ThunderboltOutlined />,
          title: '执行失败',
          description: state.message || '抱歉，处理您的请求时出现了问题',
          color: 'red',
        }
      default:
        return {
          icon: <RobotOutlined />,
          title: '处理中',
          description: '请稍候...',
          color: 'blue',
        }
    }
  }

  const config = getStatusConfig()

  return (
    <Card
      size="small"
      style={{
        margin: '12px 0',
        borderLeft: `4px solid ${
          state.status === 'failed' ? '#ff4d4f' :
          state.status === 'waiting' ? '#faad14' : '#1890ff'
        }`,
      }}
    >
      <Space size="large" style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <Space>
            <span style={{ fontSize: 24, color: `var(--ant-${config.color})` }}>
              {config.icon}
            </span>
            <div>
              <Text strong style={{ fontSize: 14 }}>{config.title}</Text>
              {config.description && (
                <Paragraph
                  type="secondary"
                  style={{ margin: 0, fontSize: 12 }}
                >
                  {config.description}
                </Paragraph>
              )}
            </div>
          </Space>
        </div>
        {state.progress !== undefined && state.progress > 0 && (
          <div style={{ width: 100 }}>
            <Progress
              type="circle"
              percent={state.progress}
              size={40}
              strokeColor={config.color === 'red' ? '#ff4d4f' : '#1890ff'}
            />
          </div>
        )}
      </Space>

      {/* 工作流步骤指示器 */}
      {state.status === 'executing' && (
        <Steps
          size="small"
          current={
            state.currentAction?.includes('选品') ? 0 :
            state.currentAction?.includes('创建') ? 1 :
            state.currentAction?.includes('邀请') ? 2 : 0
          }
          items={[
            {
              title: '智能选品',
              icon: <SearchOutlined />,
              description: '分析需求',
            },
            {
              title: '创建团购',
              icon: <ThunderboltOutlined />,
              description: '设置参数',
            },
            {
              title: '邀请成员',
              icon: <TeamOutlined />,
              description: '精准推送',
            },
          ]}
          style={{ marginTop: 16 }}
        />
      )}
    </Card>
  )
}

/**
 * Agent 思考过程展示组件
 */
interface AgentThoughtProps {
  thoughts: string[]
  isVisible: boolean
}

export const AgentThought: React.FC<AgentThoughtProps> = ({ thoughts, isVisible }) => {
  if (!isVisible || thoughts.length === 0) {
    return null
  }

  return (
    <Card
      size="small"
      style={{
        margin: '8px 0',
        background: 'linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%)',
        border: '1px solid #b7eb8f',
      }}
    >
      <div style={{ marginBottom: 8 }}>
        <Tag color="green" icon={<RobotOutlined />}>AI 思考过程</Tag>
      </div>
      {thoughts.map((thought, index) => (
        <div
          key={index}
          style={{
            padding: '8px 12px',
            background: '#fff',
            borderRadius: 4,
            marginBottom: 8,
            fontSize: 13,
            color: '#333',
            borderLeft: '3px solid #52c41a',
          }}
        >
          {thought}
        </div>
      ))}
    </Card>
  )
}

/**
 * 主动推送通知卡片
 */
interface PushNotificationCardProps {
  title: string
  content: string
  type?: 'info' | 'success' | 'warning' | 'urgent'
  icon?: React.ReactNode
  actionText?: string
  onAction?: () => void
  onDismiss?: () => void
}

export const PushNotificationCard: React.FC<PushNotificationCardProps> = ({
  title,
  content,
  type = 'info',
  icon,
  actionText,
  onAction,
  onDismiss,
}) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'success':
        return { color: '#52c41a', bg: '#f6ffed', border: '#b7eb8f' }
      case 'warning':
        return { color: '#faad14', bg: '#fffbe6', border: '#ffe58f' }
      case 'urgent':
        return { color: '#ff4d4f', bg: '#fff1f0', border: '#ffa39e' }
      default:
        return { color: '#1890ff', bg: '#e6f7ff', border: '#91d5ff' }
    }
  }

  const config = getTypeConfig()

  return (
    <Alert
      message={
        <Space>
          {icon || <BellOutlined style={{ color: config.color }} />}
          <span style={{ color: config.color, fontWeight: 500 }}>{title}</span>
        </Space>
      }
      description={content}
      type={type === 'urgent' ? 'error' : type === 'warning' ? 'warning' : 'info'}
      showIcon={false}
      style={{
        margin: '8px 0',
        background: config.bg,
        border: `1px solid ${config.border}`,
      }}
      action={
        actionText ? (
          <Button size="small" type="primary" onClick={onAction}>
            {actionText}
          </Button>
        ) : (
          <Button size="small" onClick={onDismiss}>知道了</Button>
        )
      }
    />
  )
}
