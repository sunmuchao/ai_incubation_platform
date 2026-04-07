/**
 * Generative UI - 图表组件
 * 动态生成价格趋势、成团概率等可视化图表
 */
import React from 'react'
import { Card, Space, Tag, Typography } from 'antd'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface PriceHistoryChartProps {
  data: Array<{
    date: string
    price: number
    groupPrice?: number
  }>
  title?: string
}

export const PriceHistoryChart: React.FC<PriceHistoryChartProps> = ({
  data,
  title = '价格趋势',
}) => {
  return (
    <Card size="small" title={title} style={{ margin: '12px 0' }}>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#ff4d4f"
            name="原价"
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="groupPrice"
            stroke="#52c41a"
            name="成团价"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}

interface ProbabilityGaugeProps {
  probability: number
  label?: string
  showFactors?: boolean
  factors?: string[]
}

export const ProbabilityGauge: React.FC<ProbabilityGaugeProps> = ({
  probability,
  label = '成团概率',
  showFactors,
  factors,
}) => {
  const data = [
    { name: '成功', value: probability, color: '#52c41a' },
    { name: '失败', value: 100 - probability, color: '#f0f0f0' },
  ]

  const getLevelInfo = (p: number) => {
    if (p >= 80) return { text: '很高', color: '#52c41a' }
    if (p >= 50) return { text: '中等', color: '#1890ff' }
    if (p >= 20) return { text: '较低', color: '#faad14' }
    return { text: '很低', color: '#ff4d4f' }
  }

  const level = getLevelInfo(probability)

  return (
    <Card size="small" style={{ margin: '12px 0' }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">{label}</Text>
          <div style={{ fontSize: 36, fontWeight: 'bold', color: level.color, margin: '8px 0' }}>
            {probability}%
          </div>
          <Tag color={level.color}>{level.text}</Tag>
        </div>

        <ResponsiveContainer width="100%" height={150}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={60}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>

        {showFactors && factors && factors.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>影响因素：</Text>
            <div style={{ marginTop: 4 }}>
              {factors.map((factor, index) => (
                <Tag key={index} style={{ marginBottom: 4 }}>
                  {factor}
                </Tag>
              ))}
            </div>
          </div>
        )}
      </Space>
    </Card>
  )
}

interface DemandTrendChartProps {
  data: Array<{
    date: string
    demand: number
    predicted?: number
  }>
  title?: string
}

export const DemandTrendChart: React.FC<DemandTrendChartProps> = ({
  data,
  title = '需求趋势',
}) => {
  return (
    <Card size="small" title={title} style={{ margin: '12px 0' }}>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="demand" fill="#1890ff" name="实际需求" />
          <Bar dataKey="predicted" fill="#52c41a" name="预测需求" />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

interface ComparisonChartProps {
  data: Array<{
    name: string
    value1: number
    value2: number
  }>
  title?: string
  label1?: string
  label2?: string
  color1?: string
  color2?: string
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({
  data,
  title = '对比分析',
  label1 = 'A',
  label2 = 'B',
  color1 = '#1890ff',
  color2 = '#52c41a',
}) => {
  return (
    <Card size="small" title={title} style={{ margin: '12px 0' }}>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value1" fill={color1} name={label1} />
          <Bar dataKey="value2" fill={color2} name={label2} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

interface TrendIndicatorProps {
  value: number
  change: number
  label?: string
  showArrow?: boolean
}

export const TrendIndicator: React.FC<TrendIndicatorProps> = ({
  value,
  change,
  label = '趋势',
  showArrow = true,
}) => {
  const isUp = change >= 0

  return (
    <Card size="small" style={{ width: 150 }}>
      <div style={{ textAlign: 'center' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>{label}</Text>
        <div style={{ fontSize: 24, fontWeight: 'bold', margin: '8px 0' }}>
          {value}
        </div>
        {showArrow && (
          <div style={{
            color: isUp ? '#52c41a' : '#ff4d4f',
            fontSize: 14,
            fontWeight: 500,
          }}>
            {isUp ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            <span style={{ marginLeft: 4 }}>
              {isUp ? '+' : ''}{change}%
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}
