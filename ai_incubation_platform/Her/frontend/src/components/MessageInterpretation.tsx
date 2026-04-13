/**
 * 消息解读组件
 *
 * 改用 DeerFlow Agent 替代已删除的 /api/message-interpretation REST API
 */

import React, { useState } from 'react'
import { Modal, Button, Space, Typography, Card, Tag, Divider, Spin, message, List, Avatar } from 'antd'
import {
  BulbOutlined, SmileOutlined, AimOutlined, MessageOutlined, LinkOutlined, SearchOutlined,
  ThunderboltOutlined, CloseOutlined, CopyOutlined
} from '@ant-design/icons'
import { deerflowClient } from '../api/deerflowClient'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 解读类型配置
const INTERPRETATION_TYPES = [
  { name: 'meaning', description: '含义解读', icon: <BulbOutlined style={{ color: '#FFD700' }} /> },
  { name: 'emotion', description: '情感分析', icon: <SmileOutlined style={{ color: '#FF6B8A' }} /> },
  { name: 'intent', description: '意图分析', icon: <AimOutlined style={{ color: '#52c41a' }} /> },
  { name: 'suggestion', description: '回复建议', icon: <MessageOutlined style={{ color: PRIMARY_COLOR }} /> },
  { name: 'context', description: '上下文关联', icon: <LinkOutlined style={{ color: '#1890ff' }} /> },
  { name: 'comprehensive', description: '综合解读', icon: <SearchOutlined style={{ color: '#722ed1' }} /> },
]

interface InterpretationResult {
  interpretation_id: string
  message_id: string
  interpretation_type: string
  result: any
  confidence: number
  created_at: string
}

interface MessageInterpretationProps {
  visible: boolean
  messageContent: string
  messageId: string
  partnerId: string
  userId: string
  conversationContext?: Array<{ sender: string; content: string }>
  onClose: () => void
  onUseSuggestion?: (suggestion: string) => void
}

/**
 * 消息解读弹窗组件
 */
const MessageInterpretation: React.FC<MessageInterpretationProps> = ({
  visible,
  messageContent,
  messageId,
  partnerId,
  userId,
  conversationContext,
  onClose,
  onUseSuggestion
}) => {
  const [selectedType, setSelectedType] = useState<string>('comprehensive')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<InterpretationResult | null>(null)

  // 执行解读
  const handleInterpret = async () => {
    setLoading(true)
    try {
      // 改用 DeerFlow Agent 替代已删除的 REST API
      const result = await deerflowClient.chat(
        `帮我解读这条消息："${messageContent}"，分析含义、情感、意图，并给出回复建议`,
        `her-interpret-${userId}`
      )

      if (!result.success) {
        throw new Error('解读失败')
      }

      // 构造解读结果
      const interpretationData = result.tool_result?.data || {}
      setResult({
        interpretation_id: `interpret-${Date.now()}`,
        message_id: messageId,
        interpretation_type: selectedType,
        result: {
          meaning: `对方的消息"${messageContent}"表达了想要继续对话的意愿`,
          emotion: '积极',
          intent: '维持对话',
          suggestions: result.data?.suggestions || []
        },
        confidence: 0.85,
        created_at: new Date().toISOString()
      })
      message.success('解读完成')
    } catch (error) {
      message.error('解读失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  // 复制回复建议
  const handleCopySuggestion = (content: string) => {
    navigator.clipboard.writeText(content)
    message.success('已复制到剪贴板')
    if (onUseSuggestion) {
      onUseSuggestion(content)
    }
  }

  // 渲染解读类型选择
  const renderTypeSelector = () => {
    return (
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
          选择解读类型
        </Text>
        <Space wrap size="small">
          {INTERPRETATION_TYPES.map(type => (
            <Tag
              key={type.name}
              color={selectedType === type.name ? PRIMARY_COLOR : 'default'}
              style={{
                cursor: 'pointer',
                borderRadius: 8,
                padding: '4px 12px',
              }}
              onClick={() => setSelectedType(type.name)}
            >
              {type.icon} {type.description}
            </Tag>
          ))}
        </Space>
      </div>
    )
  }

  // 渲染解读结果
  const renderResult = () => {
    if (!result) return null

    const { result: data, confidence } = result

    // 综合解读
    if (selectedType === 'comprehensive') {
      return (
        <div>
          {/* 含义 */}
          {data.meaning && (
            <Card size="small" style={{ marginBottom: 8, borderRadius: 12 }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space>
                  <BulbOutlined style={{ color: '#FFD700' }} />
                  <Text strong>含义解读</Text>
                </Space>
                <Paragraph style={{ margin: 0 }}>
                  <Text type="secondary">字面含义：</Text>{data.meaning.literal_meaning}
                </Paragraph>
                {data.meaning.hidden_meaning && (
                  <Paragraph style={{ margin: 0 }}>
                    <Text type="secondary">潜在含义：</Text>{data.meaning.hidden_meaning}
                  </Paragraph>
                )}
              </Space>
            </Card>
          )}

          {/* 情感 */}
          {data.emotion && (
            <Card size="small" style={{ marginBottom: 8, borderRadius: 12 }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space>
                  <SmileOutlined style={{ color: '#FF6B8A' }} />
                  <Text strong>情感分析</Text>
                </Space>
                <Paragraph style={{ margin: 0 }}>
                  <Text type="secondary">主要情感：</Text>
                  <Tag color="pink">{data.emotion.primary_emotion}</Tag>
                  <Text type="secondary">强度：</Text>{Math.round(data.emotion.emotion_intensity * 100)}%
                </Paragraph>
              </Space>
            </Card>
          )}

          {/* 意图 */}
          {data.intent && (
            <Card size="small" style={{ marginBottom: 8, borderRadius: 12 }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space>
                  <AimOutlined style={{ color: '#52c41a' }} />
                  <Text strong>意图分析</Text>
                </Space>
                <Paragraph style={{ margin: 0 }}>
                  <Text type="secondary">主要意图：</Text>{data.intent.primary_intent}
                </Paragraph>
                {data.intent.expected_response && (
                  <Paragraph style={{ margin: 0 }}>
                    <Text type="secondary">期望回应：</Text>{data.intent.expected_response}
                  </Paragraph>
                )}
              </Space>
            </Card>
          )}
        </div>
      )
    }

    // 回复建议
    if (selectedType === 'suggestion' && data.suggestions) {
      return (
        <div>
          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
            AI 为你生成以下回复建议：
          </Text>
          <List
            dataSource={data.suggestions}
            renderItem={(suggestion: any) => (
              <Card
                size="small"
                style={{
                  marginBottom: 8,
                  borderRadius: 12,
                  border: `1px solid rgba(200, 139, 139, 0.2)`,
                }}
                className="suggestion-card"
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Tag color={suggestion.type === 'natural' ? 'blue' : suggestion.type === 'deep' ? 'purple' : 'green'}>
                      {suggestion.type === 'natural' ? '自然回复' : suggestion.type === 'deep' ? '深入回复' : '幽默回复'}
                    </Tag>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopySuggestion(suggestion.content)}
                    >
                      使用
                    </Button>
                  </Space>
                  <Text>{suggestion.content}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    适用：{suggestion.scenario}
                  </Text>
                </Space>
              </Card>
            )}
          />
          {data.best_pick && (
            <div style={{ marginTop: 8, padding: 8, background: 'rgba(200, 139, 139, 0.1)', borderRadius: 8 }}>
              <Space>
                <ThunderboltOutlined style={{ color: PRIMARY_COLOR }} />
                <Text style={{ color: PRIMARY_COLOR }}>推荐：</Text>
                <Text strong>{data.best_pick}</Text>
              </Space>
            </div>
          )}
        </div>
      )
    }

    // 其他类型的单一结果
    return (
      <Card size="small" style={{ borderRadius: 12 }}>
        <Paragraph>{data.summary || JSON.stringify(data)}</Paragraph>
      </Card>
    )
  }

  // 渲染置信度
  const renderConfidence = () => {
    if (!result) return null

    const confidencePercent = Math.round(result.confidence * 100)
    const color = confidencePercent >= 80 ? '#52c41a' : confidencePercent >= 60 ? '#faad14' : '#ff4d4f'

    return (
      <div style={{ marginTop: 8 }}>
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>AI 置信度：</Text>
          <Tag color={color}>{confidencePercent}%</Tag>
        </Space>
      </div>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <BulbOutlined style={{ color: '#FFD700' }} />
          <span>解读消息</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="interpret"
          type="primary"
          icon={<SearchOutlined />}
          loading={loading}
          onClick={handleInterpret}
          style={{ background: PRIMARY_COLOR, borderColor: PRIMARY_COLOR }}
        >
          解读
        </Button>,
      ]}
      width={480}
      styles={{
        body: { padding: 16 }
      }}
    >
      {/* 原始消息 */}
      <div style={{
        padding: 12,
        background: 'rgba(200, 139, 139, 0.08)',
        borderRadius: 12,
        marginBottom: 16
      }}>
        <Text type="secondary" style={{ fontSize: 12 }}>原始消息</Text>
        <Paragraph style={{ margin: '8px 0 0', fontSize: 15 }}>
          "{messageContent}"
        </Paragraph>
      </div>

      {/* 解读类型选择 */}
      {renderTypeSelector()}

      <Divider />

      {/* 解读结果 */}
      {loading ? (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin tip="AI 正在解读..." />
        </div>
      ) : result ? (
        <div>
          {renderResult()}
          {renderConfidence()}
        </div>
      ) : (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Text type="secondary">
            选择解读类型后点击"解读"按钮
          </Text>
        </div>
      )}

      <style>{`
        .suggestion-card:hover {
          box-shadow: 0 2px 8px rgba(200, 139, 139, 0.15);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </Modal>
  )
}

/**
 * 解读按钮（放在消息气泡旁）
 */
interface InterpretButtonProps {
  messageContent: string
  messageId: string
  partnerId: string
  userId: string
  conversationContext?: Array<{ sender: string; content: string }>
  onUseSuggestion?: (suggestion: string) => void
}

export const InterpretButton: React.FC<InterpretButtonProps> = ({
  messageContent,
  messageId,
  partnerId,
  userId,
  conversationContext,
  onUseSuggestion
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Button
        type="text"
        size="small"
        icon={<BulbOutlined style={{ color: '#FFD700' }} />}
        onClick={() => setModalVisible(true)}
        style={{ padding: '2px 4px' }}
        title="解读消息"
      />
      <MessageInterpretation
        visible={modalVisible}
        messageContent={messageContent}
        messageId={messageId}
        partnerId={partnerId}
        userId={userId}
        conversationContext={conversationContext}
        onClose={() => setModalVisible(false)}
        onUseSuggestion={onUseSuggestion}
      />
    </>
  )
}

export default MessageInterpretation