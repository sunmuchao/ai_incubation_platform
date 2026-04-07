/**
 * AI Chat 组件 - Bento Grid 风格重构
 * 对话式数据查询主界面
 */
import React, { useState, useRef, useEffect } from 'react'
import { Button, Space, Typography, Spin, Avatar, Tooltip, Alert, Input } from 'antd'
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ReloadOutlined,
  CopyOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { GenerativeUI } from './GenerativeUI'
import { queryService } from '../services/queryService'
import { connectorService } from '../services/connectorService'

const { Text, Title } = Typography
const { TextArea } = Input

// 消息类型
type MessageType = 'user' | 'ai' | 'system' | 'error'

// 消息接口
interface ChatMessage {
  id: string
  type: MessageType
  content: string
  timestamp: Date
  data?: any[]
  schema?: any
  intent?: any
  confidence?: number
  sql?: string
  suggestions?: string[]
  explanation?: string
  isLoading?: boolean
  thinkingSteps?: string[]
}

// 快捷查询建议
const QUICK_SUGGESTIONS = [
  '查看当前有哪些数据源',
  '显示所有表结构',
  '查询最新的数据',
  '统计总数和平均值',
  '分析数据趋势',
]

// Agent 状态
interface AgentState {
  status: 'idle' | 'thinking' | 'executing' | 'completed' | 'error'
  currentStep: string
  progress: number
  thoughts: string[]
}

/**
 * AI Chat 主组件 - Bento Grid 版本
 */
interface AIChatProps {
  onQueryChange?: (query: string) => void
}

export const AIChat: React.FC<AIChatProps> = ({ onQueryChange }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      type: 'system',
      content: '欢迎使用 Data-Agent Connector！我是您的 AI 数据助手，可以通过自然语言查询和分析数据。\n\n您可以这样问我：\n• "用户表有哪些字段？"\n• "查询最近 30 天的订单数据"\n• "统计每个产品的销售总量"\n• "对比各部门的绩效表现"',
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [selectedConnector, setSelectedConnector] = useState<string>('')
  const [connectors, setConnectors] = useState<any[]>([])
  const [agentState, setAgentState] = useState<AgentState>({
    status: 'idle',
    currentStep: '',
    progress: 0,
    thoughts: [],
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 加载连接器列表
  useEffect(() => {
    loadConnectors()
  }, [])

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadConnectors = async () => {
    try {
      const data = await connectorService.getActiveConnectors()
      setConnectors(data)
      if (data.length > 0 && !selectedConnector) {
        setSelectedConnector(data[0].name)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  // 处理发送消息
  const handleSendMessage = async (content?: string) => {
    const messageContent = content || inputValue.trim()
    if (!messageContent || isProcessing) return

    onQueryChange?.(messageContent)

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: messageContent,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsProcessing(true)

    setAgentState({
      status: 'thinking',
      currentStep: '理解查询意图...',
      progress: 10,
      thoughts: ['接收用户查询', '分析语义...'],
    })

    try {
      if (messageContent.includes('数据源') || messageContent.includes('connector')) {
        await handleConnectorQuery()
        return
      }

      if (messageContent.includes('表结构') || messageContent.includes('schema') || messageContent.includes('字段')) {
        await handleSchemaQuery()
        return
      }

      await handleAIQuery(messageContent)
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'error',
        content: error.message || '查询失败，请稍后重试',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
      setAgentState({
        status: 'error',
        currentStep: '查询失败',
        progress: 0,
        thoughts: [],
      })
    } finally {
      setIsProcessing(false)
    }
  }

  // 处理连接器查询
  const handleConnectorQuery = async () => {
    setAgentState((prev) => ({
      ...prev,
      status: 'executing',
      currentStep: '获取数据源列表...',
      progress: 50,
      thoughts: [...prev.thoughts, '查询数据源列表'],
    }))

    try {
      const data = await connectorService.getActiveConnectors()
      setAgentState((prev) => ({
        ...prev,
        status: 'completed',
        currentStep: '完成',
        progress: 100,
        thoughts: [...prev.thoughts, '获取成功，生成结果'],
      }))

      const formattedContent = data.length > 0
        ? `当前有 **${data.length}** 个活跃数据源：\n\n${data
            .map((c, i) => `${i + 1}. **${c.name}** (${c.connector_type})`)
            .join('\n')}`
        : '当前没有活跃的数据源'

      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: formattedContent,
        timestamp: new Date(),
        data,
        confidence: 1.0,
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error: any) {
      throw error
    }
  }

  // 处理 Schema 查询
  const handleSchemaQuery = async () => {
    if (!selectedConnector) {
      throw new Error('请先选择数据源')
    }

    setAgentState((prev) => ({
      ...prev,
      status: 'executing',
      currentStep: '获取表结构...',
      progress: 50,
      thoughts: [...prev.thoughts, `获取 ${selectedConnector} 的 Schema`],
    }))

    try {
      const schema = await connectorService.getConnectorSchema(selectedConnector)
      setAgentState((prev) => ({
        ...prev,
        status: 'completed',
        currentStep: '完成',
        progress: 100,
        thoughts: [...prev.thoughts, 'Schema 获取成功'],
      }))

      const tables = schema?.tables || []
      const formattedContent = tables.length > 0
        ? `**${selectedConnector}** 共有 **${tables.length}** 张表：\n\n${tables
            .map((t: any, i: number) => `${i + 1}. **${t.name}** (${t.columns?.length || 0} 列)`)
            .join('\n')}`
        : '暂无表结构信息'

      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        type: 'ai',
        content: formattedContent,
        timestamp: new Date(),
        data: tables,
        schema,
        confidence: 1.0,
      }
      setMessages((prev) => [...prev, aiMessage])
    } catch (error: any) {
      throw error
    }
  }

  // 处理 AI 查询
  const handleAIQuery = async (message: string) => {
    const connectorName = selectedConnector

    if (!connectorName) {
      throw new Error('请先选择数据源')
    }

    setAgentState((prev) => ({
      ...prev,
      status: 'executing',
      currentStep: 'AI 正在分析查询...',
      progress: 30,
      thoughts: [...prev.thoughts, 'NL2SQL 转换中...'],
    }))

    const result = await queryService.aiQuery(connectorName, message, {
      use_llm: true,
      use_enhanced: true,
      enable_self_correction: true,
    })

    setAgentState((prev) => ({
      ...prev,
      status: 'completed',
      currentStep: '完成',
      progress: 100,
      thoughts: [...prev.thoughts, `SQL 生成完成 (置信度：${(result.confidence * 100).toFixed(0)}%)`],
    }))

    const aiMessage: ChatMessage = {
      id: `ai-${Date.now()}`,
      type: 'ai',
      content: result.success
        ? `查询完成，共返回 **${result.data?.length || 0}** 条记录`
        : `查询未成功：${result.validation?.message || '未知错误'}`,
      timestamp: new Date(),
      data: result.data,
      schema: null,
      intent: result.intent,
      confidence: result.confidence,
      sql: result.sql,
      suggestions: result.suggestions,
      explanation: result.explanation,
      thinkingSteps: [
        `理解问题：${message}`,
        `识别实体：时间=${result.intent?.time_range || '未指定'}, 指标=${result.intent?.metrics?.join(', ') || '未指定'}`,
        `查找数据源：${connectorName}`,
        `构建查询：${result.sql?.substring(0, 50) || 'N/A'}...`,
        `生成洞察：${result.data?.length || 0} 条记录`,
      ],
    }
    setMessages((prev) => [...prev, aiMessage])
  }

  // 复制 SQL
  const copySQL = (sql: string) => {
    navigator.clipboard.writeText(sql)
  }

  // 渲染消息
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === 'user'
    const isSystem = message.type === 'system'
    const isError = message.type === 'error'

    if (isSystem) {
      return (
        <div key={message.id} className="flex justify-center my-4">
          <Alert
            message={message.content}
            type="info"
            showIcon
            className="max-w-2xl rounded-linear"
          />
        </div>
      )
    }

    if (isError) {
      return (
        <div key={message.id} className="flex justify-start my-4">
          <Alert
            message={message.content}
            type="error"
            showIcon
            className="max-w-2xl rounded-linear"
          />
        </div>
      )
    }

    return (
      <div
        key={message.id}
        className={`flex my-4 ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        <div className={`flex items-start max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <Avatar
            icon={isUser ? <UserOutlined /> : <RobotOutlined />}
            size={40}
            className={`${
              isUser
                ? 'bg-gradient-to-br from-indigo-400 to-indigo-600 ml-2'
                : 'bg-gradient-to-br from-emerald-400 to-emerald-600 mr-2'
            } shadow-linear-sm`}
          />
          <div
            className={`
              rounded-linear-lg p-4 shadow-linear-sm flex-1
              ${
                isUser
                  ? 'chat-bubble-user'
                  : 'chat-bubble-ai'
              }
            `}
          >
            <div className="flex items-center justify-between mb-2">
              <Text strong className={isUser ? 'text-white/90' : 'text-slate-700'}>
                {isUser ? '您' : 'AI 助手'}
              </Text>
              <Text className={isUser ? 'text-white/70' : 'text-slate-400'} style={{ fontSize: 12 }}>
                {message.timestamp.toLocaleTimeString()}
              </Text>
            </div>

            {/* 消息内容 */}
            <div
              className={`text-sm ${isUser ? 'text-white' : 'text-slate-700'}`}
              style={{ whiteSpace: 'pre-wrap' }}
            >
              {message.content.split('**').map((part, i) =>
                i % 2 === 1 ? <strong key={i}>{part}</strong> : part
              )}
            </div>

            {/* SQL 展示 */}
            {message.sql && (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1">
                  <Text className={isUser ? 'text-white/80' : 'text-slate-500'} style={{ fontSize: 12 }}>
                    生成的 SQL:
                  </Text>
                  <Tooltip title="复制 SQL">
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => copySQL(message.sql!)}
                      className={isUser ? 'text-white/80 hover:text-white' : ''}
                    />
                  </Tooltip>
                </div>
                <pre className={`p-2 rounded text-xs overflow-auto max-h-32 ${
                  isUser ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'
                }`}>
                  {message.sql}
                </pre>
              </div>
            )}

            {/* 置信度 */}
            {message.confidence !== undefined && !isUser && (
              <div className="mt-2">
                <span className={`
                  inline-flex items-center px-2 py-1 rounded text-xs font-medium
                  ${
                    message.confidence >= 0.8
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                      : 'bg-amber-50 text-amber-700 border border-amber-100'
                  }
                `}>
                  <FireOutlined className="mr-1" />
                  置信度：{(message.confidence * 100).toFixed(1)}%
                </span>
              </div>
            )}

            {/* Generative UI - 数据可视化 */}
            {!isUser && message.data && message.data.length > 0 && (
              <div className={`mt-4 ${isUser ? 'border-t border-white/20 pt-3' : 'border-t border-slate-100 pt-3'}`}>
                <GenerativeUI
                  data={message.data}
                  schema={message.schema}
                  intent={message.intent}
                  suggestions={message.suggestions}
                  explanation={message.explanation}
                  confidence={message.confidence}
                  onQueryChange={(query) => handleSendMessage(query)}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // 渲染 Agent 状态
  const renderAgentStatus = () => {
    if (agentState.status === 'idle') return null

    return (
      <div className="mb-4 p-3 rounded-linear border border-slate-200 bg-gradient-to-br from-indigo-50 to-white">
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div className="flex items-center justify-between">
            <Text strong className="text-slate-700 text-sm">Agent 状态:</Text>
            <span className={`
              text-xs px-2 py-1 rounded-full font-medium
              ${
                agentState.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                agentState.status === 'error' ? 'bg-red-100 text-red-700' :
                agentState.status === 'executing' ? 'bg-indigo-100 text-indigo-700' :
                'bg-amber-100 text-amber-700'
              }
            `}>
              {
                agentState.status === 'thinking' ? '思考中' :
                agentState.status === 'executing' ? '执行中' :
                agentState.status === 'completed' ? '已完成' :
                agentState.status === 'error' ? '出错' : '等待中'
              }
            </span>
          </div>

          {/* 进度条 */}
          <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${agentState.progress}%` }}
            />
          </div>

          {/* 当前步骤 */}
          <Text className="text-slate-500 text-xs">{agentState.currentStep}</Text>

          {/* 思考过程 */}
          {agentState.thoughts.length > 0 && (
            <div className="mt-1 p-2 bg-white rounded border border-slate-100">
              <ul className="text-xs text-slate-500 space-y-1">
                {agentState.thoughts.map((thought, i) => (
                  <li key={i} className="flex items-center">
                    <span className="w-1 h-1 rounded-full bg-indigo-400 mr-2" />
                    {thought}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Space>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between mb-3 px-4 py-3 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-linear">
            <RobotOutlined className="text-white" />
          </div>
          <Title level={4} style={{ margin: 0 }} className="text-slate-800">
            AI 数据助手
          </Title>
        </div>
        <div className="flex items-center space-x-2">
          {connectors.length > 0 && (
            <select
              value={selectedConnector}
              onChange={(e) => setSelectedConnector(e.target.value)}
              className="input-linear text-sm py-1.5"
            >
              {connectors.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={loadConnectors}
            disabled={isProcessing}
            className="btn-linear"
            size="small"
          >
            刷新
          </Button>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 bg-slate-50/50">
        {renderAgentStatus()}
        {messages.map(renderMessage)}
        {isProcessing && agentState.status !== 'completed' && (
          <div className="flex justify-start my-4">
            <Avatar
              icon={<RobotOutlined />}
              size={40}
              className="bg-gradient-to-br from-emerald-400 to-emerald-600 mr-2 shadow-linear-sm"
            />
            <div className="bg-white border border-slate-200 rounded-linear-lg p-4 shadow-linear-sm">
              <Spin tip="AI 思考中..." className="text-indigo-500" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="p-4 bg-white border-t border-slate-100">
        {/* 快捷建议 */}
        <div className="mb-3">
          <div className="flex flex-wrap gap-1.5">
            {QUICK_SUGGESTIONS.map((suggestion, index) => (
              <button
                key={index}
                className="
                  tag-linear
                  hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700
                  transition-colors duration-200
                "
                onClick={() => handleSendMessage(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        {/* 输入框 */}
        <div className="flex items-center space-x-2">
          <TextArea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleSendMessage()
              }
            }}
            placeholder="请输入您的问题... (Shift+Enter 换行)"
            autoSize={{ minRows: 2, maxRows: 4 }}
            disabled={isProcessing}
            className="input-linear flex-1 resize-none"
          />
          <Button
            type="primary"
            size="large"
            icon={isProcessing ? <ReloadOutlined /> : <SendOutlined />}
            onClick={() => isProcessing ? null : handleSendMessage()}
            disabled={!inputValue.trim() || !selectedConnector}
            loading={isProcessing}
            className="btn-linear-primary"
          >
            发送
          </Button>
        </div>

        {/* 提示信息 */}
        {!selectedConnector && (
          <Alert
            message="请先选择一个数据源"
            type="warning"
            showIcon
            className="mt-2 rounded-linear"
            style={{ fontSize: 12 }}
          />
        )}
      </div>
    </div>
  )
}

export default AIChat
