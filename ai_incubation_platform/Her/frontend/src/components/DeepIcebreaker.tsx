/**
 * 深度破冰话题组件
 *
 * 改用 DeerFlow Agent 替代已删除的 /api/deep-icebreaker REST API
 */

import React, { useState, useEffect } from 'react'
import {
  Modal, Button, Space, Typography, Card, Tag, List, Avatar, message,
  Divider, Spin, Progress, Tooltip, Badge, Radio
} from 'antd'
import {
  BulbOutlined, QuestionCircleOutlined, BookOutlined, CameraOutlined,
  SendOutlined, CopyOutlined, HeartOutlined, AimOutlined, StarOutlined
} from '@ant-design/icons'
import { deerflowClient } from '../api/deerflowClient'

const { Text, Title, Paragraph } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'

// 深度层级配置
const DEPTH_LEVELS = [
  { level: 1, name: '轻松开场', description: '简单的自我介绍', icon: '👋', color: '#52c41a' },
  { level: 2, name: '兴趣探索', description: '发现共同兴趣', icon: '🔍', color: '#1890ff' },
  { level: 3, name: '经历分享', description: '分享有趣经历', icon: '📖', color: '#722ed1' },
  { level: 4, name: '价值观交流', description: '深入想法和观念', icon: '💡', color: '#fa8c16' },
  { level: 5, name: '关系期望', description: '对未来关系的想法', icon: '❤️', color: '#eb2f96' },
]

// 话题类型配置
const TOPIC_TYPES = [
  { type: 'question', name: '提问式', icon: <QuestionCircleOutlined />, color: 'blue' },
  { type: 'story_share', name: '故事分享', icon: <BookOutlined />, color: 'green' },
  { type: 'game', name: '游戏互动', icon: <CameraOutlined />, color: 'purple' },
  { type: 'challenge', name: '挑战式', icon: <StarOutlined />, color: 'orange' },
  { type: 'reflection', name: '反思式', icon: <BulbOutlined />, color: 'pink' },
]

interface Topic {
  topic_content: string
  topic_type: string
  depth_level: number
  suitable_scenario?: string
  expected_effect?: string
  personalization_reason?: string
  confidence: number
}

interface DeepIcebreakerProps {
  visible: boolean
  userId: string
  partnerId: string
  userProfile: any
  partnerProfile: any
  conversationContext?: any[]
  onClose: () => void
  onUseTopic?: (topic: string) => void
}

/**
 * 深度破冰话题弹窗
 */
const DeepIcebreaker: React.FC<DeepIcebreakerProps> = ({
  visible,
  userId,
  partnerId,
  userProfile,
  partnerProfile,
  conversationContext,
  onClose,
  onUseTopic
}) => {
  const [loading, setLoading] = useState(false)
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedDepth, setSelectedDepth] = useState(1)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [progression, setProgression] = useState<any>(null)

  // 加载话题
  useEffect(() => {
    if (visible) {
      loadTopics()
      loadProgression()
    }
  }, [visible, selectedDepth])

  const loadTopics = async () => {
    setLoading(true)
    try {
      // 改用 DeerFlow Agent 替代已删除的 REST API
      const userId = userProfile?.id || 'user-test-001'

      const result = await deerflowClient.chat(
        `帮我生成一些深度破冰话题，让我可以和匹配对象开启对话。当前对话深度级别：${selectedDepth}`,
        `her-icebreaker-${userId}`
      )

      if (result.success) {
        // Agent Native 架构：优先从 ai_message 解析 JSON
        const parsed = deerflowClient.parseToolResult(result)
        if (parsed?.type === 'topics' && parsed.data.topics?.length > 0) {
          setTopics(parsed.data.topics)
        } else if (result.tool_result?.data?.topics?.length > 0) {
          // 降级：从 tool_result.data 获取（兼容旧架构）
          setTopics(result.tool_result.data.topics)
        } else {
          // 如果没有结构化数据，从 AI 消息中解析
          setTopics([{ topic_content: result.ai_message, topic_type: 'question', depth_level: selectedDepth, confidence: 0.8 }])
        }
      } else {
        message.error(result.ai_message || '加载话题失败')
      }
    } catch (error) {
      message.error('加载话题失败')
    } finally {
      setLoading(false)
    }
  }

  const loadProgression = async () => {
    try {
      // 改用 DeerFlow Agent 替代已删除的 REST API
      const convLength = conversationContext?.length || 0
      const result = await deerflowClient.chat(
        `分析我和匹配对象的对话进展，当前对话长度：${convLength}`,
        `her-progression-${userProfile?.id || 'user-test'}`
      )
      if (result.success) {
        setProgression(result.tool_result?.data || { current_depth: 1, suggested_next: 2 })
      }
    } catch (error) {
      // 静默失败
    }
  }

  const handleUseTopic = (topic: Topic) => {
    if (onUseTopic) {
      onUseTopic(topic.topic_content)
    }
    message.success('话题已复制，可直接发送')
    navigator.clipboard.writeText(topic.topic_content)
  }

  // 渲染深度选择
  const renderDepthSelector = () => {
    return (
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
          选择话题深度
        </Text>
        <Radio.Group
          value={selectedDepth}
          onChange={(e) => setSelectedDepth(e.target.value)}
          style={{ width: '100%' }}
        >
          {DEPTH_LEVELS.map(level => (
            <Radio.Button
              key={level.level}
              value={level.level}
              style={{
                borderRadius: 8,
                margin: '4px 2px',
              }}
            >
              <Space size={4}>
                <span>{level.icon}</span>
                <span>{level.name}</span>
              </Space>
            </Radio.Button>
          ))}
        </Radio.Group>
      </div>
    )
  }

  // 渲染话题列表
  const renderTopics = () => {
    if (loading) {
      return <Spin size="large" tip="AI 正在生成话题..." />
    }

    if (topics.length === 0) {
      return (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Text type="secondary">暂无话题建议</Text>
        </div>
      )
    }

    // 过滤话题类型
    const filteredTopics = selectedType
      ? topics.filter(t => t.topic_type === selectedType)
      : topics

    return (
      <List
        dataSource={filteredTopics}
        renderItem={(topic) => (
          <Card
            size="small"
            style={{
              marginBottom: 8,
              borderRadius: 12,
              cursor: 'pointer',
            }}
            onClick={() => handleUseTopic(topic)}
            className="topic-card"
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {/* 话题类型和深度 */}
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Tag color={TOPIC_TYPES.find(t => t.type === topic.topic_type)?.color || 'default'}>
                  {TOPIC_TYPES.find(t => t.type === topic.topic_type)?.name || topic.topic_type}
                </Tag>
                <Badge
                  count={`${Math.round(topic.confidence * 100)}%`}
                  style={{
                    backgroundColor: topic.confidence >= 0.8 ? '#52c41a' : '#faad14'
                  }}
                />
              </Space>

              {/* 话题内容 */}
              <Paragraph style={{ fontSize: 14, margin: 0 }}>
                {topic.topic_content}
              </Paragraph>

              {/* 个性化原因 */}
              {topic.personalization_reason && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  💡 {topic.personalization_reason}
                </Text>
              )}

              {/* 预期效果 */}
              {topic.expected_effect && (
                <Tag style={{ fontSize: 10 }}>
                  预期：{topic.expected_effect}
                </Tag>
              )}
            </Space>
          </Card>
        )}
      />
    )
  }

  // 渲染话题类型过滤
  const renderTypeFilter = () => {
    return (
      <div style={{ marginBottom: 8 }}>
        <Space wrap size="small">
          <Tag
            color={selectedType === null ? PRIMARY_COLOR : 'default'}
            style={{ cursor: 'pointer', borderRadius: 8 }}
            onClick={() => setSelectedType(null)}
          >
            全部
          </Tag>
          {TOPIC_TYPES.map(type => (
            <Tag
              key={type.type}
              color={selectedType === type.type ? type.color : 'default'}
              style={{ cursor: 'pointer', borderRadius: 8 }}
              onClick={() => setSelectedType(type.type)}
            >
              {type.icon} {type.name}
            </Tag>
          ))}
        </Space>
      </div>
    )
  }

  // 渲染进度建议
  const renderProgression = () => {
    if (!progression) return null

    const currentLevel = DEPTH_LEVELS.find(l => l.level === progression.recommended_depth)

    return (
      <Card
        size="small"
        style={{
          marginBottom: 16,
          borderRadius: 12,
          background: 'rgba(200, 139, 139, 0.08)'
        }}
      >
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text strong style={{ fontSize: 12 }}>
            <AimOutlined style={{ color: PRIMARY_COLOR }} /> 当前建议深度
          </Text>

          <Progress
            percent={progression.recommended_depth * 20}
            strokeColor={currentLevel?.color || PRIMARY_COLOR}
            showInfo={false}
            size="small"
          />

          <Text style={{ color: currentLevel?.color || PRIMARY_COLOR }}>
            {currentLevel?.icon} {currentLevel?.name} - {progression.reason}
          </Text>
        </Space>
      </Card>
    )
  }

  return (
    <Modal
      title={
        <Space>
          <BulbOutlined style={{ color: '#FFD700' }} />
          <span>破冰话题推荐</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="regenerate" onClick={loadTopics}>
          重新生成
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={500}
      styles={{ body: { padding: 16 } }}
    >
      {/* 进度建议 */}
      {renderProgression()}

      {/* 深度选择 */}
      {renderDepthSelector()}

      <Divider />

      {/* 话题类型过滤 */}
      {renderTypeFilter()}

      {/* 话题列表 */}
      {renderTopics()}

      <style>{`
        .topic-card:hover {
          box-shadow: 0 2px 8px rgba(200, 139, 139, 0.15);
          transition: box-shadow 0.2s;
        }
      `}</style>
    </Modal>
  )
}

/**
 * 破冰话题按钮（放在聊天界面）
 */
export const IcebreakerButton: React.FC<{
  userId: string
  partnerId: string
  userProfile: any
  partnerProfile: any
  conversationContext?: any[]
  onUseTopic?: (topic: string) => void
}> = ({
  userId,
  partnerId,
  userProfile,
  partnerProfile,
  conversationContext,
  onUseTopic
}) => {
  const [modalVisible, setModalVisible] = useState(false)

  return (
    <>
      <Tooltip title="破冰话题">
        <Button
          type="text"
          icon={<BulbOutlined style={{ color: '#FFD700' }} />}
          onClick={() => setModalVisible(true)}
        />
      </Tooltip>
      <DeepIcebreaker
        visible={modalVisible}
        userId={userId}
        partnerId={partnerId}
        userProfile={userProfile}
        partnerProfile={partnerProfile}
        conversationContext={conversationContext}
        onClose={() => setModalVisible(false)}
        onUseTopic={onUseTopic}
      />
    </>
  )
}

export default DeepIcebreaker