/**
 * AI 预沟通会话卡片组件
 * 从 ChatInterface 提取，用于渲染预沟通会话列表
 */

import React from 'react'
import { Card, Space, Tag, Progress, Divider, Button, Typography, Empty } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  HeartOutlined,
  MessageOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { AIPreCommunicationSession } from '../types'
import './PreCommunicationSessionCard.less'

const { Text } = Typography

interface PreCommunicationSessionCardProps {
  sessions: AIPreCommunicationSession[]
  onViewMessages: (sessionId: string) => void
  onStartChat: (session: AIPreCommunicationSession) => void
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const PreCommunicationSessionCard: React.FC<PreCommunicationSessionCardProps> = React.memo(({
  sessions,
  onViewMessages,
  onStartChat,
}) => {
  const { t } = useTranslation()

  // 辅助函数（从已删除的 aiInterlocutor.ts 迁移）
  const getCompatibilityLevel = (score: number): string => {
    if (score >= 90) return t('conversation.compatibilityLevel.veryHigh')
    if (score >= 80) return t('conversation.compatibilityLevel.high')
    if (score >= 70) return t('conversation.compatibilityLevel.mediumHigh')
    if (score >= 60) return t('conversation.compatibilityLevel.medium')
    return t('conversation.compatibilityLevel.low')
  }

  // 获取状态颜色
  const getSessionStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      pending: 'default',
      analyzing: 'blue',
      chatting: 'green',
      completed: 'purple',
      cancelled: 'red',
    }
    return colors[status] || 'default'
  }

  // 获取状态文本
  const getSessionStatusText = (status: string): string => {
    const texts: Record<string, string> = {
      pending: t('conversation.sessionStatus.pending'),
      analyzing: t('conversation.sessionStatus.analyzing'),
      chatting: t('conversation.sessionStatus.chatting'),
      completed: t('conversation.sessionStatus.completed'),
      cancelled: t('conversation.sessionStatus.cancelled'),
    }
    return texts[status] || status
  }

  // 获取分数颜色
  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'green'
    if (score >= 70) return 'blue'
    if (score >= 60) return 'orange'
    return 'red'
  }

  if (!sessions || sessions.length === 0) {
    return (
      <Card className="generative-card" size="small">
        <Empty description={t('common.noData')} />
      </Card>
    )
  }

  return (
    <div className="generative-card-container precomm-container">
      <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
        {t('precomm.sessionList')}
      </Text>
      <div className="generative-cards-grid">
        {sessions.slice(0, 5).map((session) => {
          const isCompleted = session.status === 'completed'
          const isRecommended = session.recommendation === 'recommend'
          const progress = (session.conversation_rounds / session.target_rounds) * 100

          return (
            <Card
              key={session.session_id}
              className="generative-card precomm-card"
              size="small"
              hoverable
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {/* 状态标签 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Tag color={getSessionStatusColor(session.status)}>
                    {getSessionStatusText(session.status)}
                  </Tag>
                  {isCompleted && isRecommended && (
                    <Tag color="green">推荐</Tag>
                  )}
                </div>

                {/* 进度条 */}
                {session.status === 'chatting' && (
                  <div>
                    <Progress
                      percent={Math.round(progress)}
                      size="small"
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {session.conversation_rounds}/{session.target_rounds} 轮
                    </Text>
                  </div>
                )}

                {/* 硬指标校验 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  {session.hard_check_passed ? (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  )}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {t('precomm.hardCheck', { status: session.hard_check_passed ? t('precomm.passed') : t('precomm.notPassed') })}
                  </Text>
                </div>

                {/* 价值观探测 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <HeartOutlined style={{ color: session.values_check_passed ? '#52c41a' : '#ff4d4f' }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {t('precomm.valuesCheck', { status: session.values_check_passed ? t('precomm.passed') : t('precomm.notPassed') })}
                  </Text>
                </div>

                {/* 匹配度 */}
                {isCompleted && session.compatibility_score && (
                  <div>
                    <Divider style={{ margin: '4px 0' }} />
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Text strong style={{ fontSize: 18, color: getScoreColor(session.compatibility_score) }}>
                        {Math.round(session.compatibility_score)}%
                      </Text>
                      <Tag color={getScoreColor(session.compatibility_score)}>
                        {getCompatibilityLevel(session.compatibility_score)}
                      </Tag>
                    </div>
                  </div>
                )}

                {/* 操作按钮 */}
                <Space wrap size="small">
                  <Button
                    size="small"
                    icon={<MessageOutlined />}
                    onClick={() => onViewMessages(session.session_id)}
                    disabled={session.conversation_rounds === 0}
                  >
                    {t('precomm.viewChat')}
                  </Button>
                  {isCompleted && isRecommended && (
                    <Button
                      type="primary"
                      size="small"
                      icon={<ThunderboltOutlined />}
                      onClick={() => onStartChat(session)}
                    >
                      {t('precomm.startChat')}
                    </Button>
                  )}
                </Space>
              </Space>
            </Card>
          )
        })}
      </div>
    </div>
  )
})

export default PreCommunicationSessionCard