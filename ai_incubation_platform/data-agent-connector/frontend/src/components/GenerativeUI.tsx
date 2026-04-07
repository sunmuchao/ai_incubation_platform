/**
 * Generative UI 组件 - 根据 AI 响应动态生成界面
 */
import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Typography, Alert, Space } from 'antd'
import { Line, Pie, Bar } from '@ant-design/plots'

const { Text } = Typography

// 数据类型定义
interface GenerativeUIProps {
  data: any[]
  schema?: any
  intent?: any
  suggestions?: string[]
  explanation?: string
  confidence?: number
  onQueryChange?: (query: string) => void
}

interface ChartConfig {
  type: 'table' | 'line' | 'bar' | 'pie'
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
    k.toLowerCase().includes('created')
  )

  // 检测数值字段
  const numericKeys = keys.filter(k => typeof data[0][k] === 'number')

  // 检测分类字段
  const categoryKeys = keys.filter(k => typeof data[0][k] === 'string' && !timeKeys.includes(k))

  // 如果有时间字段和数值字段，使用折线图
  if (timeKeys.length > 0 && numericKeys.length > 0) {
    return {
      type: 'line',
      xField: timeKeys[0],
      yField: numericKeys[0],
    }
  }

  // 如果有分类字段和数值字段，使用柱状图或饼图
  if (categoryKeys.length > 0 && numericKeys.length > 0) {
    if (categoryKeys.length === 1 && numericKeys.length === 1) {
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

// 根据意图生成标题
const generateTitle = (intent?: any): string => {
  if (!intent) return '查询结果'

  const intentType = intent.type || 'unknown'
  const tables = intent.tables?.join(', ') || '数据'

  const intentTitles: Record<string, string> = {
    simple_select: `${tables} 查询结果`,
    aggregation: `${tables} 统计汇总`,
    comparison: `${tables} 对比分析`,
    trend: `${tables} 趋势分析`,
    distribution: `${tables} 分布情况`,
    ranking: `${tables} 排行榜`,
    join: `${tables} 关联查询`,
  }

  return intentTitles[intentType] || '查询结果'
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
 * GenerativeUI 主组件
 */
export const GenerativeUI: React.FC<GenerativeUIProps> = ({
  data,
  intent,
  suggestions,
  explanation,
  confidence,
  onQueryChange,
}) => {
  const [chartConfig, setChartConfig] = useState<ChartConfig>({ type: 'table' })

  useEffect(() => {
    if (data && data.length > 0) {
      setChartConfig(detectChartType(data))
    }
  }, [data])

  const title = generateTitle(intent)

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
      height: 400,
    }
    return <Line {...config} />
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
      height: 400,
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
      height: 400,
    }
    return <Pie {...config} />
  }

  // 渲染图表
  const renderChart = () => {
    switch (chartConfig.type) {
      case 'line':
        return renderLineChart()
      case 'bar':
        return renderBarChart()
      case 'pie':
        return renderPieChart()
      default:
        return renderTable()
    }
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
      {/* 结果卡片 */}
      <Card
        title={
          <div className="flex items-center justify-between">
            <span>{title}</span>
            {confidence !== undefined && (
              <Tag color={getConfidenceColor(confidence)}>
                置信度：{getConfidenceText(confidence)} ({(confidence * 100).toFixed(1)}%)
              </Tag>
            )}
          </div>
        }
        size="small"
      >
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

        {/* 数据可视化 */}
        <div className="mt-4">
          {renderChart()}
        </div>
      </Card>

      {/* 建议卡片 */}
      {renderSuggestions()}
    </div>
  )
}

export default GenerativeUI
