/**
 * LearningConfirmationCard - AI 学习结果确认卡片
 *
 * 当 DeerFlow Agent 从对话中识别用户偏好时，
 * 展示此卡片让用户确认是否更新画像。
 *
 * 使用场景：
 * - Agent 发现用户新偏好："你喜欢户外运动吗？"
 * - Agent 推断用户性格："你可能是内向型"
 * - Agent 发现价值观："你重视家庭"
 *
 * 流程：
 * 1. DeerFlow 返回 learned_insights
 * 2. 前端渲染此卡片
 * 3. 用户点击确认/忽略
 * 4. 调用 API 更新画像（确认时）
 */

import React, { useState } from 'react'
import { Card, Button, List, Tag, Typography, Space, message } from 'antd'
import { CheckOutlined, CloseOutlined, BulbOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Text, Paragraph } = Typography

interface LearnedInsight {
  dimension: string
  content: string
  confidence: number
  source: string
  suggestion_type: 'add' | 'update' | 'infer'
  raw_evidence?: string
}

interface LearningConfirmationCardProps {
  insights: LearnedInsight[]
  hasHighConfidence: boolean
  suggestedActions: string[]
  message?: string
  onConfirm?: (confirmedInsights: LearnedInsight[]) => void
  onIgnore?: () => void
}

const LearningConfirmationCard: React.FC<LearningConfirmationCardProps> = ({
  insights,
  hasHighConfidence,
  suggestedActions,
  message,
  onConfirm,
  onIgnore,
}) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [selectedInsights, setSelectedInsights] = useState<Set<number>>(
    new Set(insights.map((_, i) => i)) // 默认全选
  )

  const handleConfirm = async () => {
    setLoading(true)
    try {
      const confirmed = insights.filter((_, i) => selectedInsights.has(i))
      if (onConfirm) {
        await onConfirm(confirmed)
        message.success(t('conversation.learningConfirmed'))
      }
    } catch (error) {
      message.error(t('conversation.learningFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleIgnore = () => {
    if (onIgnore) {
      onIgnore()
    }
  }

  const toggleInsight = (index: number) => {
    const newSelected = new Set(selectedInsights)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedInsights(newSelected)
  }

  // 维度中文名映射
  const dimensionNameMap: Record<string, string> = {
    interests: '兴趣爱好',
    personality: '性格特点',
    values: '价值观',
    relationship_goal: '关系目标',
    deal_breakers: '底线禁忌',
    lifestyle: '生活方式',
  }

  // 置信度颜色
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return 'green'
    if (confidence >= 0.7) return 'blue'
    return 'orange'
  }

  return (
    <Card
      className="learning-confirmation-card"
      style={{ marginBottom: 16, borderRadius: 12 }}
    >
      <div style={{ padding: 16 }}>
        {/* 标题 */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <BulbOutlined style={{ color: '#1890ff', marginRight: 8 }} />
          <Text strong style={{ fontSize: 16 }}>
            {message || t('conversation.learningTitle')}
          </Text>
        </div>

        {/* 高置信度提示 */}
        {hasHighConfidence && (
          <Tag color="green" style={{ marginBottom: 12 }}>
            {t('conversation.highConfidence')}
          </Tag>
        )}

        {/* 洞察列表 */}
        <List
          dataSource={insights}
          renderItem={(insight, index) => (
            <List.Item
              style={{
                cursor: 'pointer',
                background: selectedInsights.has(index) ? '#e6f7ff' : 'transparent',
                borderRadius: 8,
                padding: '8px 12px',
                marginBottom: 8,
              }}
              onClick={() => toggleInsight(index)}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Tag color={getConfidenceColor(insight.confidence)}>
                      {dimensionNameMap[insight.dimension] || insight.dimension}
                    </Tag>
                    <Text>{insight.content}</Text>
                  </Space>
                }
                description={
                  insight.raw_evidence && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      "{insight.raw_evidence.slice(0, 50)}..."
                    </Text>
                  )
                }
              />
              {selectedInsights.has(index) && (
                <CheckOutlined style={{ color: '#1890ff' }} />
              )}
            </List.Item>
          )}
        />

        {/* 建议操作 */}
        {suggestedActions.length > 0 && (
          <Paragraph type="secondary" style={{ marginTop: 12, fontSize: 12 }}>
            {suggestedActions.join('；')}
          </Paragraph>
        )}

        {/* 操作按钮 */}
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={handleIgnore} icon={<CloseOutlined />}>
            {t('conversation.ignore')}
          </Button>
          <Button
            type="primary"
            onClick={handleConfirm}
            loading={loading}
            icon={<CheckOutlined />}
            disabled={selectedInsights.size === 0}
          >
            {t('conversation.addToProfile')}
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default LearningConfirmationCard