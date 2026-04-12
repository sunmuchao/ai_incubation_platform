/**
 * AI 预沟通对话历史卡片组件
 * 从 ChatInterface 提取，用于渲染预沟通对话消息列表
 */

import React from 'react'
import { Card, Space, Tag, Typography, Timeline, Empty } from 'antd'
import { HeartFilled } from '@ant-design/icons'
import './PreCommunicationDialogCard.less'

const { Text, Paragraph } = Typography

interface PreCommunicationDialogMessage {
  id: string
  sender_agent: string
  content: string
  topic_tag?: string
  round_number: number
  message_type?: string
}

interface PreCommunicationDialogCardProps {
  messages: PreCommunicationDialogMessage[]
}

// 🚀 [性能优化] 使用 memo 防止不必要的重渲染
export const PreCommunicationDialogCard: React.FC<PreCommunicationDialogCardProps> = React.memo(({
  messages,
}) => {
  if (!messages || messages.length === 0) {
    return (
      <Card className="generative-card" size="small">
        <Empty description="暂无对话内容" />
      </Card>
    )
  }

  return (
    <div className="generative-dialog-container">
      <Timeline
        items={messages.map((msg) => ({
          key: msg.id,
          color: msg.sender_agent.includes('agent_1') ? 'blue' : 'purple',
          dot: <HeartFilled style={{ color: '#FF8FAB' }} />,
          children: (
            <Card size="small" style={{ marginBottom: 8 }}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div>
                  <Tag color={msg.sender_agent.includes('agent_1') ? 'blue' : 'purple'}>
                    {msg.sender_agent.includes('agent_1') ? 'AI 替身 A' : 'AI 替身 B'}
                  </Tag>
                  <Tag>{msg.message_type || 'text'}</Tag>
                  {msg.topic_tag && <Tag>{msg.topic_tag}</Tag>}
                  <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                    第{msg.round_number}轮
                  </Text>
                </div>
                <Paragraph style={{ margin: 0, fontSize: 13 }}>{msg.content}</Paragraph>
              </Space>
            </Card>
          ),
        }))}
      />
    </div>
  )
})

export default PreCommunicationDialogCard