/**
 * Generative UI 增强版 - 支持四层洞察和动态可视化
 */
import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Typography, Alert, Space, Row, Col, Statistic } from 'antd'
import { Line, Pie, Bar, Area } from '@ant-design/plots'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  BulbOutlined,
  RobotOutlined,
} from '@ant-design/icons'

const { Text } = Typography

// 数据类型定义
interface GenerativeUIEnhancedProps {
  data: any[]
  schema?: any
  intent?: any
  suggestions?: string[]
  explanation?: string
  confidence?: number
  onQueryChange?: (query: string) => void
  thinkingSteps?: string[]
}

interface Insight {
  type: 'summary' | 'key_finding' | 'anomaly' | 'attribution' | 'prediction' | 'recommendation'
  title: string
  content: string
  value?: number
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: number
}

interface ChartConfig {
  type: 'table' | 'line' | 'bar' | 'pie' | 'area' | 'radar' | 'kpi'
  title?: string
  xField?: string
  yField?: string
  seriesField?: string
  colorField?: string
}

// 自动检测数据类型并生成图表配置
const detectChartType = (data: any[]): ChartConfig => {
  if (!data || data.length === 0) {
    return { type: 'table' }
  }

  const keys = Object.keys(data[0])

  // 检测时间序列数据
  const timeKeys = keys.filter(k =>
    k.toLowerCase().includes('date') ||
    k.toLowerCase().includes('time') ||
    k.toLowerCase().includes('created') ||
    k.toLowerCase().includes('year') ||
    k.toLowerCase().includes('month')
  )

  // 检测数值字段
  const numericKeys = keys.filter(k => typeof data[0][k] === 'number')

  // 检测分类字段
  const categoryKeys = keys.filter(k => typeof data[0][k] === 'string' && !timeKeys.includes(k))

  // 如果有时间字段和数值字段，使用面积图或折线图
  if (timeKeys.length > 0 && numericKeys.length > 0) {
    return {
      type: numericKeys.length > 1 ? 'area' : 'line',
      xField: timeKeys[0],
      yField: numericKeys[0],
    }
  }

  // 如果有分类字段和数值字段，使用柱状图或饼图
  if (categoryKeys.length > 0 && numericKeys.length > 0) {
    if (categoryKeys.length === 1 && numericKeys.length === 1 && data.length <= 10) {
      return {
        type: 'pie',
        colorField: categoryKeys[0],
        yField: numericKeys[0],
      }
    }
    return {
      type: 'bar',
      xField: categoryKeys[0],
      yField: numericKeys[0],
    }
  }

  // 默认使用表格
  return { type: 'table' }
}

// 根据意图生成洞察
const generateInsights = (data: any[]): Insight[] => {
  const insights: Insight[] = []

  if (!data || data.length === 0) return insights

  // 汇总洞察
  const numericKeys = Object.keys(data[0]).filter(k => typeof data[0][k] === 'number')
  if (numericKeys.length > 0) {
    const total = data.reduce((sum, item) => sum + (item[numericKeys[0]] || 0), 0)
    const avg = total / data.length

    insights.push({
      type: 'summary',
      title: '数据汇总',
      content: `共 ${data.length} 条记录，${numericKeys[0]} 总计 ${total.toFixed(2)}，平均值 ${avg.toFixed(2)}`,
      value: total,
    })
  }

  // 排序找出最大/最小值
  if (numericKeys.length > 0 && data.length > 1) {
    const sorted = [...data].sort((a, b) => (b[numericKeys[0]] || 0) - (a[numericKeys[0]] || 0))
    const maxItem = sorted[0]
    const minItem = sorted[sorted.length - 1]

    // 找出第一个非数值字段作为名称
    const nameKey = Object.keys(data[0]).find(k => typeof data[0][k] === 'string')

    if (nameKey) {
      insights.push({
        type: 'key_finding',
        title: '最高值',
        content: `${nameKey} 为 "${maxItem[nameKey]}" 的记录 ${numericKeys[0]} 最高`,
        value: maxItem[numericKeys[0]],
        trend: 'up',
      })

      if (data.length > 2) {
        insights.push({
          type: 'key_finding',
          title: '最低值',
          content: `${nameKey} 为 "${minItem[nameKey]}" 的记录 ${numericKeys[0]} 最低`,
          value: minItem[numericKeys[0]],
          trend: 'down',
        })
      }
    }
  }

  return insights
}

// 置信度颜色
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'green'
  if (confidence >= 0.6) return 'orange'
  return 'red'
}

// 置信度文本
const getConfidenceText = (confidence: number): string => {
  if (confidence >= 0.9) return '极高'
  if (confidence >= 0.8) return '高'
  if (confidence >= 0.7) return '较高'
  if (confidence >= 0.6) return '中等'
  if (confidence >= 0.4) return '较低'
  return '低'
}

// 饼图颜色
const PIE_COLORS = [
  '#1890ff', '#2fc25b', '#facc14', '#fa8c16', '#f04864',
  '#722ed1', '#13c2c2', '#eb2f96', '#52c41a', '#1890ff'
]

/**
 * GenerativeUIEnhanced 主组件
 */
export const GenerativeUIEnhanced: React.FC<GenerativeUIEnhancedProps> = ({
  data,
  suggestions,
  explanation,
  confidence,
  onQueryChange,
  thinkingSteps,
}) => {
  const [chartConfig, setChartConfig] = useState<ChartConfig>({ type: 'table' })
  const [insights, setInsights] = useState<Insight[]>([])

  useEffect(() => {
    if (data && data.length > 0) {
      setChartConfig(detectChartType(data))
      setInsights(generateInsights(data))
    }
  }, [data])

  // 渲染 KPI 卡片
  const renderKpiCards = () => {
    if (!data || data.length === 0) return null

    const numericKeys = Object.keys(data[0]).filter(k => typeof data[0][k] === 'number')
    if (numericKeys.length === 0) return null

    const total = data.reduce((sum, item) => sum + (item[numericKeys[0]] || 0), 0)
    const avg = total / data.length
    const max = Math.max(...data.map(item => item[numericKeys[0]] || 0))
    const min = Math.min(...data.map(item => item[numericKeys[0]] || 0))

    return (
      <Row gutter={16} className="mb-4">
        <Col span={6}>
          <Card size="small">
            <Statistic
              title={numericKeys[0]}
              value={total}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ArrowUpOutlined />}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>总计</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="平均值"
              value={avg}
              precision={2}
              valueStyle={{ color: '#2fc25b' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="最大值"
              value={max}
              precision={2}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<ArrowUpOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="最小值"
              value={min}
              precision={2}
              valueStyle={{ color: '#f04864' }}
              prefix={<ArrowDownOutlined />}
            />
          </Card>
        </Col>
      </Row>
    )
  }

  // 渲染洞察卡片
  const renderInsights = () => {
    if (insights.length === 0) return null

    return (
      <Card
        title={
          <div className="flex items-center">
            <BulbOutlined className="mr-2 text-yellow-500" />
            AI 洞察
          </div>
        }
        size="small"
        className="mb-4"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {insights.map((insight, index) => (
            <div
              key={index}
              className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
            >
              {insight.type === 'key_finding' && (
                <CheckCircleOutlined className={insight.trend === 'up' ? 'text-green-500' : 'text-red-500'} />
              )}
              {insight.type === 'anomaly' && (
                <WarningOutlined className="text-orange-500" />
              )}
              {insight.type === 'summary' && (
                <CheckCircleOutlined className="text-blue-500" />
              )}
              <div className="flex-1">
                <Text strong>{insight.title}: </Text>
                <Text>{insight.content}</Text>
                {insight.value !== undefined && (
                  <Tag color="blue" className="ml-2">{insight.value.toFixed(2)}</Tag>
                )}
              </div>
            </div>
          ))}
        </Space>
      </Card>
    )
  }

  // 渲染表格
  const renderTable = () => {
    if (!data || data.length === 0) {
      return (
        <div className="flex justify-center items-center py-12 text-gray-400">
          暂无数据
        </div>
      )
    }

    const columns = Object.keys(data[0]).map((key) => ({
      title: key,
      dataIndex: key,
      key,
      ellipsis: true,
      render: (val: any) => {
        if (val === null) return <span className="text-gray-400">NULL</span>
        if (typeof val === 'object') return JSON.stringify(val)
        if (typeof val === 'number') return val.toFixed(2)
        return String(val)
      },
    }))

    return (
      <Table
        columns={columns}
        dataSource={data}
        rowKey={(_, index) => `row-${index}`}
        pagination={{ pageSize: 20, showSizeChanger: true, showQuickJumper: true }}
        scroll={{ x: 'max-content' }}
        size="small"
      />
    )
  }

  // 渲染折线图
  const renderLineChart = () => {
    if (!data || data.length === 0) return null
    const config = {
      data,
      xField: chartConfig.xField,
      yField: chartConfig.yField,
      point: { size: 5, shape: 'circle' },
      label: {
        style: { fill: '#aaa' } as const,
      },
      tooltip: {
        showMarkers: false,
      },
      smooth: true,
      height: 350,
    }
    return <Line {...config} />
  }

  // 渲染面积图
  const renderAreaChart = () => {
    if (!data || data.length === 0) return null
    const config = {
      data,
      xField: chartConfig.xField,
      yField: chartConfig.yField,
      startOnZero: false,
      smooth: true,
      areaStyle: {
        fill: 'l(270) 0:#1890ff 1:#1890ff55',
      },
      height: 350,
    }
    return <Area {...config} />
  }

  // 渲染柱状图
  const renderBarChart = () => {
    if (!data || data.length === 0) return null
    const config = {
      data,
      xField: chartConfig.xField,
      yField: chartConfig.yField,
      legend: { position: 'top' as const },
      label: {
        position: 'middle' as const,
        style: {
          fill: '#FFFFFF',
          opacity: 0.6,
        },
      },
      height: 350,
    }
    return <Bar {...config} />
  }

  // 渲染饼图
  const renderPieChart = () => {
    if (!data || data.length === 0) return null
    const config = {
      appendPadding: 10,
      data,
      angleField: chartConfig.yField || 'value',
      colorField: chartConfig.colorField || 'name',
      radius: 0.8,
      label: {
        type: 'outer' as const,
        content: '{name} {percentage}',
      },
      interactions: [
        { type: 'element-active' },
      ],
      color: PIE_COLORS,
      height: 350,
    }
    return <Pie {...config} />
  }

  // 渲染图表
  const renderChart = () => {
    switch (chartConfig.type) {
      case 'line':
        return renderLineChart()
      case 'area':
        return renderAreaChart()
      case 'bar':
        return renderBarChart()
      case 'pie':
        return renderPieChart()
      default:
        return renderTable()
    }
  }

  // 渲染思考过程
  const renderThinkingProcess = () => {
    if (!thinkingSteps || thinkingSteps.length === 0) return null

    return (
      <Card
        title={
          <div className="flex items-center">
            <RobotOutlined className="mr-2" />
            AI 思考过程
          </div>
        }
        size="small"
        className="mb-4"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {thinkingSteps.map((step, index) => (
            <div key={index} className="flex items-center space-x-2 text-sm">
              <Tag color="blue">{index + 1}</Tag>
              <Text>{step}</Text>
            </div>
          ))}
        </Space>
      </Card>
    )
  }

  // 渲染建议
  const renderSuggestions = () => {
    if (!suggestions || suggestions.length === 0) return null

    return (
      <Card title="AI 建议" size="small" className="mt-4">
        <Space direction="vertical" style={{ width: '100%' }}>
          {suggestions.map((suggestion: string, index: number) => (
            <div
              key={index}
              className="cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors"
              onClick={() => onQueryChange?.(suggestion)}
            >
              <Text type="secondary">{suggestion}</Text>
            </div>
          ))}
        </Space>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* 置信度标签 */}
      {confidence !== undefined && (
        <div className="flex justify-end">
          <Tag color={getConfidenceColor(confidence)}>
            置信度：{getConfidenceText(confidence)} ({(confidence * 100).toFixed(1)}%)
          </Tag>
        </div>
      )}

      {/* 结果解释 */}
      {explanation && (
        <Alert
          message="AI 解释"
          description={explanation}
          type="info"
          showIcon
          className="mb-4"
        />
      )}

      {/* 思考过程 */}
      {renderThinkingProcess()}

      {/* KPI 卡片 */}
      {renderKpiCards()}

      {/* 洞察卡片 */}
      {renderInsights()}

      {/* 数据可视化 */}
      <Card title="数据可视化" size="small">
        {renderChart()}
      </Card>

      {/* 建议卡片 */}
      {renderSuggestions()}
    </div>
  )
}

export default GenerativeUIEnhanced
