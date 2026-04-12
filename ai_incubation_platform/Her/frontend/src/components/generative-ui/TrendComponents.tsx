/**
 * 关系趋势与冲突调解组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Progress,
  Empty
} from 'antd'
import {
  LineChartOutlined,
  FireOutlined,
  CloudOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  MessageOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

/**
 * 关系趋势图表
 */
export const RelationshipTrendChart: React.FC<{ data?: any[] }> = ({ data }) => {
  return (
    <Card className="relationship-trend-chart" title={<><LineChartOutlined /> 关系趋势</>}>
      <div className="trend-placeholder">
        <LineChartOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        <Text>关系趋势图表区域</Text>
        <Paragraph type="secondary">需集成图表库 (如 Recharts/AntV)</Paragraph>
        {data && data.length > 0 && (
          <Text type="secondary">数据点：{data.length} 个</Text>
        )}
      </div>
    </Card>
  )
}

/**
 * 关系天气
 */
export const RelationshipWeather: React.FC<{
  weather?: string
  score?: number
}> = ({ weather = 'sunny', score = 0.8 }) => {
  const weatherIcon = {
    sunny: <FireOutlined style={{ fontSize: 32, color: '#faad14' }} />,
    cloudy: <CloudOutlined style={{ fontSize: 32, color: '#8c8c8c' }} />,
    rainy: <ThunderboltOutlined style={{ fontSize: 32, color: '#1890ff' }} />,
    stormy: <WarningOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />
  }

  return (
    <Card className="relationship-weather-card">
      <div className="weather-display">
        <div className="weather-icon">
          {weatherIcon[weather as keyof typeof weatherIcon]}
        </div>
        <Title level={4}>{weather}</Title>
        <Progress
          type="circle"
          percent={Math.round(score * 100)}
          size={80}
          format={(percent: number) => `${percent}分`}
        />
      </div>
    </Card>
  )
}

/**
 * 冲突计量器
 */
export const ConflictMeter: React.FC<{ level?: number }> = ({ level = 0 }) => {
  const getColor = (lvl: number) => {
    if (lvl < 0.3) return '#52c41a'
    if (lvl < 0.6) return '#faad14'
    return '#ff4d4f'
  }

  const getStatus = (lvl: number) => {
    if (lvl < 0.3) return '和谐'
    if (lvl < 0.6) return '中等'
    return '紧张'
  }

  return (
    <Card className="conflict-meter-card">
      <div className="meter-display">
        <Title level={5}>冲突程度</Title>
        <Progress
          type="dashboard"
          percent={Math.round(level * 100)}
          strokeColor={getColor(level)}
        />
        <Text type={level < 0.3 ? 'success' : level < 0.6 ? 'warning' : 'danger'}>
          {getStatus(level)}
        </Text>
      </div>
    </Card>
  )
}

/**
 * 调解空状态
 */
export const MediationEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="mediation-empty-card">
      <Empty
        image={<MessageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '无需调解'}
      />
    </Card>
  )
}