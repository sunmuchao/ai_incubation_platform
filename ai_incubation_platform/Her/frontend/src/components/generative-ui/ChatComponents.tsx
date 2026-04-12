/**
 * 聊天助手相关组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  List,
  Avatar,
  Space,
  Divider,
  Empty,
  Result,
  Badge
} from 'antd'
import {
  MessageOutlined,
  ClockCircleOutlined,
  HeartFilled,
  CheckCircleOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 消息发送状态
 */
export const MessageSent: React.FC<{
  message_id?: string
  status?: string
  onAction?: (action: GenerativeAction) => void
}> = ({ message_id, status = 'sent', onAction }) => {
  return (
    <Card className="message-sent-card">
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title="消息已发送"
        subTitle={status === 'sent' ? '对方将尽快收到您的消息' : status}
        extra={
          <Button type="primary" onClick={() => onAction?.({ type: 'view_conversation' })}>
            查看会话
          </Button>
        }
      />
    </Card>
  )
}

/**
 * 会话列表
 */
export const ConversationList: React.FC<{
  conversations?: any[]
  show_unread?: boolean
  onAction?: (action: GenerativeAction) => void
}> = ({ conversations, show_unread, onAction }) => {
  if (!conversations || conversations.length === 0) {
    return <Empty description="暂无会话" />
  }

  return (
    <Card className="conversation-list-card" title={<><MessageOutlined /> 会话列表</>}>
      <List
        dataSource={conversations}
        renderItem={(conversation) => (
          <List.Item
            className="conversation-item"
            actions={[
              <Button
                key="chat"
                type="link"
                onClick={() => onAction?.({ type: 'open_chat', conversation })}
              >
                进入聊天
              </Button>
            ]}
          >
            <List.Item.Meta
              avatar={
                <Avatar
                  src={conversation.avatar}
                  style={{
                    backgroundColor: conversation.unread_count > 0 ? '#1890ff' : '#d9d9d9'
                  }}
                />
              }
              title={
                <Space>
                  <Text strong>{conversation.partner_name || '未知用户'}</Text>
                  {show_unread && conversation.unread_count > 0 && (
                    <Tag color="red">{conversation.unread_count} 条未读</Tag>
                  )}
                </Space>
              }
              description={
                <div className="conversation-preview">
                  <Text type="secondary" ellipsis>{conversation.last_message_preview}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {conversation.last_message_at}
                  </Text>
                </div>
              }
            />
          </List.Item>
        )}
      />

      <Divider />

      <Button type="primary" block onClick={() => onAction?.({ type: 'start_new_chat' })}>
        开始新对话
      </Button>
    </Card>
  )
}

/**
 * 聊天历史
 */
export const ChatHistory: React.FC<{
  messages?: any[]
  show_sender?: boolean
  onAction?: (action: GenerativeAction) => void
}> = ({ messages, show_sender, onAction }) => {
  if (!messages || messages.length === 0) {
    return <Empty description="暂无聊天历史" />
  }

  return (
    <Card className="chat-history-card" title={<><ClockCircleOutlined /> 聊天历史</>}>
      <div className="messages-container">
        {messages.map((message: any, index: number) => (
          <div
            key={message.id || index}
            className={`message-item ${message.sender_id === 'me' ? 'message-me' : 'message-other'}`}
          >
            {show_sender && (
              <Avatar
                size="small"
                src={message.avatar}
                className="message-avatar"
              />
            )}
            <div className="message-content">
              <div className="message-bubble">{message.content}</div>
              <div className="message-meta">
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {message.created_at}
                </Text>
                {message.is_read && (
                  <CheckCircleOutlined style={{ fontSize: 12, color: '#1890ff' }} />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <Divider />

      <Button type="primary" block onClick={() => onAction?.({ type: 'send_message' })}>
        发送消息
      </Button>
    </Card>
  )
}

/**
 * 聊天建议卡片
 */
export const SuggestionCards: React.FC<{
  suggestions?: any[]
  show_reason?: boolean
  onAction?: (action: GenerativeAction) => void
}> = ({ suggestions, show_reason, onAction }) => {
  if (!suggestions || suggestions.length === 0) {
    return <Empty description="暂无聊天建议" />
  }

  return (
    <Card className="suggestion-cards-card" title={<><HeartFilled style={{ color: '#FF8FAB' }} /> 聊天建议</>}>
      <List
        dataSource={suggestions}
        renderItem={(suggestion: any, index: number) => (
          <List.Item>
            <Card
              size="small"
              className="suggestion-card"
              hoverable
              onClick={() => onAction?.({ type: 'use_suggestion', suggestion })}
            >
              <div className="suggestion-content">
                <Tag color={suggestion.type === 'icebreaker' ? 'blue' : 'green'}>
                  {suggestion.type === 'icebreaker' ? '破冰' : '话题'}
                </Tag>
                <Paragraph style={{ margin: '8px 0' }}>{suggestion.content}</Paragraph>
                {show_reason && suggestion.reason && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    💡 {suggestion.reason}
                  </Text>
                )}
              </div>
            </Card>
          </List.Item>
        )}
      />

      <Divider />

      <Space>
        <Button onClick={() => onAction?.({ type: 'refresh_suggestions' })}>刷新建议</Button>
        <Button type="primary" onClick={() => onAction?.({ type: 'use_suggestion' })}>
          使用建议
        </Button>
      </Space>
    </Card>
  )
}

/**
 * 未读消息徽章
 */
export const UnreadBadge: React.FC<{
  count?: number
  onAction?: (action: GenerativeAction) => void
}> = ({ count = 0, onAction }) => {
  if (count === 0) {
    return (
      <Card className="unread-badge-card">
        <Result
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title="没有未读消息"
          subTitle="所有消息都已处理"
        />
      </Card>
    )
  }

  return (
    <Card className="unread-badge-card">
      <div className="unread-display">
        <Badge count={count} offset={[-10, -10]} style={{ backgroundColor: '#ff4d4f' }}>
          <MessageOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        </Badge>
      </div>
      <Title level={4} style={{ textAlign: 'center', marginTop: 16 }}>
        你有 {count} 条未读消息
      </Title>
      <Paragraph type="secondary" style={{ textAlign: 'center' }}>
        及时回复可以增进关系哦~
      </Paragraph>
      <Button type="primary" block onClick={() => onAction?.({ type: 'view_messages' })}>
        查看消息
      </Button>
    </Card>
  )
}