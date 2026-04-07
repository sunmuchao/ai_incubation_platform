/**
 * AI Native Chat 主界面组件
 * 对话式交互核心界面
 */
import React, { useState, useRef, useEffect, useCallback } from 'react'
import {
  Input,
  Button,
  Space,
  Avatar,
  Typography,
  Spin,
  Empty,
  Tooltip,
  Tag,
} from 'antd'
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import {
  sendChatMessage,
  clearSessionHistory,
} from '@/services/chatApi'
import type { ChatMessage, ChatSuggestion, AgentState, ChatData } from '@/types/chat'
import {
  ProductCarousel,
  GroupList,
  AgentStatus,
  ProbabilityGauge,
} from '@/components/GenerativeUI'
import { generateMessageId } from '@/utils/messageId'

const { Text, Paragraph } = Typography
const { TextArea } = Input

interface ChatInterfaceProps {
  initialCommunityId?: string
  onGroupCreated?: (groupData: any) => void
  onProductSelected?: (productData: any) => void
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  initialCommunityId,
  onGroupCreated,
  onProductSelected,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentState, setAgentState] = useState<AgentState>({ status: 'idle' })
  const [welcomeShown, setWelcomeShown] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = React.createRef<any>()

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // 显示欢迎消息
  useEffect(() => {
    if (!welcomeShown) {
      addSystemMessage(
        '你好！我是您的 AI 团购管家 🤖\n\n' +
        '我可以帮您：\n' +
        '🛒 智能选品 - "我想买点新鲜的水果"\n' +
        '📦 发起团购 - "帮我找个牛奶团购"\n' +
        '📊 查询进度 - "我的团购怎么样了"\n\n' +
        '请告诉我您的需求吧～',
        {
          suggestions: [
            { text: '我想买点水果', action: 'find_product' },
            { text: '帮我找个牛奶团购', action: 'create_group' },
            { text: '看看热门商品', action: 'find_product' },
          ],
        }
      )
      setWelcomeShown(true)
    }
  }, [welcomeShown])

  // 添加消息
  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateMessageId(),
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, newMessage])
    return newMessage
  }

  const addUserMessage = (content: string) => {
    return addMessage({
      role: 'user',
      content,
    })
  }

  const addSystemMessage = (
    content: string,
    extras?: Partial<ChatMessage>
  ) => {
    return addMessage({
      role: 'assistant',
      content,
      ...extras,
    })
  }

  // 处理发送消息
  const handleSendMessage = async (content?: string) => {
    const messageContent = content || inputValue.trim()
    if (!messageContent || isLoading) return

    // 添加用户消息
    addUserMessage(messageContent)
    setInputValue('')
    setIsLoading(true)
    setAgentState({ status: 'thinking' })

    try {
      // 获取对话历史（最近 10 条）
      const conversationHistory = messages.slice(-10).map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
      }))

      // 调用 API
      const response = await sendChatMessage(
        messageContent,
        sessionId,
        initialCommunityId,
        conversationHistory as ChatMessage[]
      )

      // 更新会话 ID
      if (!sessionId && response.session_id) {
        setSessionId(response.session_id)
      }

      // 更新 Agent 状态
      setAgentState({
        status: response.success ? 'completed' : 'failed',
        message: response.success ? undefined : response.message,
      })

      // 添加 AI 回复
      addSystemMessage(response.message, {
        suggestions: response.suggestions,
        action: response.action,
        data: response.data,
        confidence: response.confidence,
        trace_id: response.trace_id,
      })

      // 处理回调
      if (response.action === 'create_group' && response.data?.group) {
        onGroupCreated?.(response.data.group)
      } else if (response.action === 'find_product' && response.data?.products) {
        onProductSelected?.(response.data.products[0])
      }
    } catch (error: any) {
      console.error('发送消息失败:', error)
      addSystemMessage(
        '抱歉，处理您的请求时出现了问题，请稍后重试。',
        { confidence: 0 }
      )
      setAgentState({
        status: 'failed',
        message: error.message || '发送失败',
      })
    } finally {
      setIsLoading(false)
      setTimeout(() => setAgentState({ status: 'idle' }), 2000)
    }
  }

  // 处理建议点击
  const handleSuggestionClick = (suggestion: ChatSuggestion) => {
    handleSendMessage(suggestion.text)
  }

  // 清空对话
  const handleClearChat = async () => {
    if (sessionId) {
      await clearSessionHistory(sessionId)
    }
    setMessages([])
    setSessionId(undefined)
    setWelcomeShown(false)
  }

  // 渲染消息内容
  const renderMessageContent = (message: ChatMessage) => {
    // 渲染 Generative UI 组件
    if (message.data) {
      return <GenerativeContent data={message.data} />
    }
    return <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{message.content}</Paragraph>
  }

  // 渲染建议操作
  const renderSuggestions = (suggestions: ChatSuggestion[]) => {
    if (!suggestions || suggestions.length === 0) return null

    return (
      <Space wrap size="small" style={{ marginTop: 8 }}>
        {suggestions.map((suggestion, index) => (
          <Tag
            key={index}
            color="blue"
            style={{ cursor: 'pointer' }}
            onClick={() => handleSuggestionClick(suggestion)}
          >
            {suggestion.text}
          </Tag>
        ))}
      </Space>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 顶部工具栏 */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Space>
          <RobotOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <Text strong>AI 团购管家</Text>
          {sessionId && (
            <Tag color="green">会话中</Tag>
          )}
        </Space>
        <Space>
          <Tooltip title="清空对话">
            <Button
              type="text"
              icon={<DeleteOutlined />}
              onClick={handleClearChat}
            />
          </Tooltip>
        </Space>
      </div>

      {/* 消息列表 */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '16px',
          background: '#f5f5f5',
        }}
      >
        {/* Agent 状态 */}
        <AgentStatus state={agentState} />

        {/* 消息 */}
        {messages.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="开始与 AI 团购管家的对话吧～"
          />
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              style={{
                display: 'flex',
                marginBottom: 16,
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              {message.role !== 'user' && (
                <Avatar
                  icon={<RobotOutlined />}
                  style={{ marginRight: 8, background: '#1890ff' }}
                />
              )}
              <div
                style={{
                  maxWidth: '70%',
                  padding: '12px 16px',
                  borderRadius: 12,
                  background: message.role === 'user' ? '#1890ff' : '#fff',
                  color: message.role === 'user' ? '#fff' : '#333',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                }}
              >
                {renderMessageContent(message)}
                {message.suggestions && renderSuggestions(message.suggestions)}
                <div
                  style={{
                    fontSize: 11,
                    marginTop: 8,
                    opacity: 0.6,
                    textAlign: 'right',
                  }}
                >
                  {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
              {message.role === 'user' && (
                <Avatar
                  icon={<UserOutlined />}
                  style={{ marginLeft: 8, background: '#52c41a' }}
                />
              )}
            </div>
          ))
        )}

        {/* 加载中 */}
        {isLoading && (
          <div style={{ display: 'flex', marginBottom: 16 }}>
            <Avatar
              icon={<RobotOutlined />}
              style={{ marginRight: 8, background: '#1890ff' }}
            />
            <div
              style={{
                padding: '12px 16px',
                borderRadius: 12,
                background: '#fff',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              }}
            >
              <Spin tip="AI 正在思考..." size="small" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div
        style={{
          padding: '16px',
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
        }}
      >
        <TextArea
          ref={inputRef as any}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              handleSendMessage()
            }
          }}
          placeholder="告诉我您想买什么..."
          rows={2}
          disabled={isLoading}
          style={{ resize: 'none', marginBottom: 8 }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            按 Enter 发送，Shift + Enter 换行
          </Text>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => handleSendMessage()}
            loading={isLoading}
            disabled={!inputValue.trim()}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}

/**
 * 渲染 Generative UI 内容
 */
const GenerativeContent: React.FC<{ data: ChatData }> = ({ data }) => {
  const elements = []

  // 渲染商品
  if (data.products && data.products.length > 0) {
    elements.push(
      <div key="products" style={{ margin: '12px 0' }}>
        <ProductCarousel products={data.products} />
      </div>
    )
  }

  // 渲染单个团购
  if (data.group) {
    elements.push(
      <div key="group" style={{ margin: '12px 0' }}>
        <ProductCarousel products={[]} />
      </div>
    )
  }

  // 渲染团购列表
  if (data.groups && data.groups.length > 0) {
    elements.push(
      <div key="groups" style={{ margin: '12px 0' }}>
        <GroupList groups={data.groups} />
      </div>
    )
  }

  // 渲染概率
  if (data.prediction) {
    elements.push(
      <div key="prediction" style={{ margin: '12px 0' }}>
        <ProbabilityGauge
          probability={data.prediction.success_probability}
          factors={data.prediction.factors}
          showFactors
        />
      </div>
    )
  }

  return elements.length > 0 ? <>{elements}</> : null
}
