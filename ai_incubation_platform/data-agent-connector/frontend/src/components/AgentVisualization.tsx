/**
 * Agent 可视化组件 - Bento Grid 风格重构
 * 显示数据接入 Agent 状态和 RAG 检索过程
 */
import React, { useState, useEffect } from 'react'
import { Badge, Spin } from 'antd'
import {
  RobotOutlined,
  DatabaseOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  TrophyOutlined,
} from '@ant-design/icons'

// Agent 节点
interface AgentNode {
  id: string
  name: string
  type: 'connector' | 'rag' | 'analyzer' | 'generator'
  status: 'active' | 'inactive' | 'processing' | 'error'
  lastActivity?: Date
  metrics?: {
    queriesProcessed?: number
    avgLatency?: number
    successRate?: number
  }
}

// RAG 检索步骤
interface RagStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  duration?: number
  result?: any
}

interface AgentVisualizationProps {
  currentQuery?: string
  showDetails?: boolean
}

/**
 * Agent 可视化组件 - Bento Grid 版本
 */
export const AgentVisualization: React.FC<AgentVisualizationProps> = ({
  currentQuery,
  showDetails = true,
}) => {
  const [activeAgents, setActiveAgents] = useState<AgentNode[]>([])
  const [ragSteps, setRagSteps] = useState<RagStep[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  // 模拟 Agent 状态
  useEffect(() => {
    const defaultAgents: AgentNode[] = [
      {
        id: 'connector-agent',
        name: '数据接入',
        type: 'connector',
        status: 'active',
        lastActivity: new Date(),
        metrics: { queriesProcessed: 128, avgLatency: 45, successRate: 98.5 },
      },
      {
        id: 'rag-agent',
        name: 'RAG 检索',
        type: 'rag',
        status: 'active',
        lastActivity: new Date(),
        metrics: { queriesProcessed: 256, avgLatency: 120, successRate: 96.2 },
      },
      {
        id: 'lineage-agent',
        name: '血缘分析',
        type: 'analyzer',
        status: 'active',
        lastActivity: new Date(),
        metrics: { queriesProcessed: 64, avgLatency: 200, successRate: 99.1 },
      },
      {
        id: 'generator-agent',
        name: 'SQL 生成',
        type: 'generator',
        status: 'active',
        lastActivity: new Date(),
        metrics: { queriesProcessed: 512, avgLatency: 80, successRate: 94.8 },
      },
    ]

    setActiveAgents(defaultAgents)

    const defaultRagSteps: RagStep[] = [
      {
        id: 'parse',
        name: '查询解析',
        description: '解析用户查询意图',
        status: 'pending',
      },
      {
        id: 'retrieve',
        name: '向量检索',
        description: '从向量库检索文档',
        status: 'pending',
      },
      {
        id: 'rerank',
        name: '结果重排',
        description: '相关性排序',
        status: 'pending',
      },
      {
        id: 'generate',
        name: '答案生成',
        description: '基于检索结果生成',
        status: 'pending',
      },
    ]

    setRagSteps(defaultRagSteps)
  }, [])

  // 模拟处理查询
  useEffect(() => {
    if (currentQuery) {
      simulateQueryProcess()
    }
  }, [currentQuery])

  const simulateQueryProcess = async () => {
    setIsProcessing(true)
    const steps = [...ragSteps]

    // 步骤 1: 查询解析
    steps[0].status = 'processing'
    setRagSteps([...steps])
    await sleep(500)
    steps[0].status = 'completed'
    steps[0].duration = 120
    setRagSteps([...steps])

    // 步骤 2: 向量检索
    steps[1].status = 'processing'
    setRagSteps([...steps])
    await sleep(800)
    steps[1].status = 'completed'
    steps[1].duration = 350
    steps[1].result = { documentsFound: 5 }
    setRagSteps([...steps])

    // 步骤 3: 结果重排
    steps[2].status = 'processing'
    setRagSteps([...steps])
    await sleep(400)
    steps[2].status = 'completed'
    steps[2].duration = 180
    setRagSteps([...steps])

    // 步骤 4: 答案生成
    steps[3].status = 'processing'
    setRagSteps([...steps])
    await sleep(600)
    steps[3].status = 'completed'
    steps[3].duration = 250
    setRagSteps([...steps])

    setIsProcessing(false)
  }

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

  // 获取 Agent 类型图标
  const getAgentIcon = (type: string) => {
    switch (type) {
      case 'connector': return <DatabaseOutlined />
      case 'rag': return <SearchOutlined />
      case 'analyzer': return <EyeOutlined />
      case 'generator': return <ThunderboltOutlined />
      default: return <RobotOutlined />
    }
  }

  // 获取 Agent 卡片样式
  const getAgentCardStyle = (status: string) => {
    const baseStyle = "p-3 rounded-linear border transition-all duration-200 cursor-pointer"
    switch (status) {
      case 'active':
        return `${baseStyle} bg-emerald-50/50 border-emerald-100 hover:border-emerald-200 hover:shadow-linear`
      case 'processing':
        return `${baseStyle} bg-indigo-50/50 border-indigo-100 hover:border-indigo-200 hover:shadow-linear`
      case 'error':
        return `${baseStyle} bg-red-50/50 border-red-100 hover:border-red-200 hover:shadow-linear`
      default:
        return `${baseStyle} bg-slate-50 border-slate-200 hover:border-slate-300`
    }
  }

  // 获取步骤状态
  const getStepStatus = (step: RagStep) => {
    switch (step.status) {
      case 'completed':
        return { icon: <CheckCircleOutlined className="text-emerald-500" />, label: '完成' }
      case 'processing':
        return { icon: <SyncOutlined spin className="text-indigo-500" />, label: '进行中' }
      case 'error':
        return { icon: <CheckCircleOutlined className="text-red-500" />, label: '错误' }
      default:
        return { icon: <div className="w-4 h-4 rounded-full border-2 border-slate-300" />, label: '等待' }
    }
  }

  // 计算整体进度
  const completedSteps = ragSteps.filter(s => s.status === 'completed').length
  const overallProgress = (completedSteps / ragSteps.length) * 100

  return (
    <div className="space-y-4">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
            <RobotOutlined className="text-white text-sm" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">Agent 集群</h3>
            <p className="text-xs text-slate-500">{activeAgents.filter(a => a.status === 'active').length} 活跃 / {activeAgents.length} 总计</p>
          </div>
        </div>
        <Badge
          count={
            <span className="text-xs">{activeAgents.filter(a => a.status === 'active').length}</span>
          }
          style={{ backgroundColor: '#10b981' }}
        />
      </div>

      {/* Agent 卡片网格 */}
      <div className="grid grid-cols-2 gap-2">
        {activeAgents.map((agent) => (
          <div
            key={agent.id}
            className={getAgentCardStyle(agent.status)}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`text-base ${
                agent.status === 'active' ? 'text-emerald-600' :
                agent.status === 'processing' ? 'text-indigo-600' :
                agent.status === 'error' ? 'text-red-600' : 'text-slate-400'
              }`}>
                {getAgentIcon(agent.type)}
              </span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                agent.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                agent.status === 'processing' ? 'bg-indigo-100 text-indigo-700' :
                agent.status === 'error' ? 'bg-red-100 text-red-700' :
                'bg-slate-100 text-slate-600'
              }`}>
                {agent.status === 'active' ? '活跃' :
                 agent.status === 'processing' ? '运行' :
                 agent.status === 'error' ? '错误' : '空闲'}
              </span>
            </div>
            <div className="font-medium text-xs text-slate-700 mb-2 truncate">
              {agent.name}
            </div>
            {agent.metrics && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">查询</span>
                  <span className="text-slate-600 font-medium">{agent.metrics.queriesProcessed}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">延迟</span>
                  <span className="text-slate-600 font-medium">{agent.metrics.avgLatency}ms</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">成功率</span>
                  <span className="text-emerald-600 font-medium">{agent.metrics.successRate}%</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* RAG 检索过程 */}
      {showDetails && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <SearchOutlined className="text-indigo-500" />
              <span className="font-semibold text-slate-700 text-sm">RAG 检索</span>
              {isProcessing && <Spin size="small" className="text-indigo-500" />}
            </div>
            <span className="text-xs text-slate-500">{Math.round(overallProgress)}%</span>
          </div>

          {/* 当前查询 */}
          {currentQuery && (
            <div className="mb-3 p-2.5 bg-indigo-50 rounded-linear border border-indigo-100">
              <div className="flex items-start space-x-2">
                <TrophyOutlined className="text-indigo-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs text-indigo-900 font-medium">当前查询</p>
                  <p className="text-xs text-indigo-700 mt-0.5 truncate">{currentQuery}</p>
                </div>
              </div>
            </div>
          )}

          {/* 步骤进度 */}
          <div className="space-y-2">
            {ragSteps.map((step) => {
              const status = getStepStatus(step)
              return (
                <div
                  key={step.id}
                  className={`flex items-center p-2 rounded-linear transition-colors ${
                    step.status === 'processing' ? 'bg-indigo-50' :
                    step.status === 'completed' ? 'bg-emerald-50/30' :
                    'bg-transparent'
                  }`}
                >
                  <div className="w-6 h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center mr-3 flex-shrink-0">
                    {status.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700">{step.name}</span>
                      <span className={`text-xs ${
                        step.status === 'completed' ? 'text-emerald-600' :
                        step.status === 'processing' ? 'text-indigo-600' :
                        'text-slate-400'
                      }`}>
                        {status.label}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="text-xs text-slate-400 truncate">{step.description}</span>
                      {step.duration && (
                        <span className="text-xs text-slate-500 ml-2">{step.duration}ms</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 性能指标汇总 */}
      <div className="mt-4 pt-4 border-t border-slate-100">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-2 rounded-linear bg-slate-50">
            <div className="text-lg font-bold text-emerald-600">
              {activeAgents.reduce((acc, a) => acc + (a.metrics?.queriesProcessed || 0), 0)}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">总查询</div>
          </div>
          <div className="text-center p-2 rounded-linear bg-slate-50">
            <div className="text-lg font-bold text-indigo-600">
              {Math.round(activeAgents.reduce((acc, a) => acc + (a.metrics?.avgLatency || 0), 0) / activeAgents.length)}ms
            </div>
            <div className="text-xs text-slate-500 mt-0.5">平均延迟</div>
          </div>
          <div className="text-center p-2 rounded-linear bg-slate-50">
            <div className="text-lg font-bold text-violet-600">
              {(activeAgents.reduce((acc, a) => acc + (a.metrics?.successRate || 0), 0) / activeAgents.length).toFixed(1)}%
            </div>
            <div className="text-xs text-slate-500 mt-0.5">成功率</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AgentVisualization
