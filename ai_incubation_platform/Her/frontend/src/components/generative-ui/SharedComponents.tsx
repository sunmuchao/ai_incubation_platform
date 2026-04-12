/**
 * 共享组件 - 空状态、消费画像等
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Space,
  Empty,
  Progress
} from 'antd'
import {
  LineChartOutlined,
  FireOutlined,
  HeartOutlined,
  CloudOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 空状态
 */
export const EmptyState: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div className="empty-state">
      <Empty description={message} />
    </div>
  )
}

/**
 * 消费画像展示
 */
export const ConsumptionProfile: React.FC<{ profile: any }> = ({ profile }) => {
  return (
    <Card className="consumption-profile-card" title={<><LineChartOutlined /> 消费画像</>}>
      <div className="profile-header">
        <Tag color="gold" className="profile-level-tag">
          {profile.level}
        </Tag>
      </div>
      <Row gutter={[16, 16]} className="profile-stats">
        <Col span={12}>
          <Statistic
            label="消费频率"
            value={profile.frequency}
            suffix={profile.frequency === '高频' ? '🔥' : ''}
          />
        </Col>
        <Col span={12}>
          <Statistic label="平均客单" value={profile.average_transaction} />
        </Col>
        <Col span={12}>
          <Statistic label="消费模式" value={profile.spending_pattern} />
        </Col>
        <Col span={12}>
          <Statistic label="价格敏感度" value={profile.price_sensitivity} />
        </Col>
      </Row>
      <div className="profile-categories">
        <Text strong>偏好类别：</Text>
        <Space wrap className="category-tags">
          {profile.preferred_categories?.map((cat: string, i: number) => (
            <Tag key={i} color="blue">
              {cat}
            </Tag>
          ))}
        </Space>
      </div>
    </Card>
  )
}

/**
 * 健康报告
 */
export const HealthReport: React.FC<{ report: any }> = ({ report }) => {
  const healthScore = report.health_score || 0
  const isGood = healthScore >= 0.8

  return (
    <Card
      className="health-report-card"
      title={
        <Space>
          {isGood ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : (
            <WarningOutlined style={{ color: '#faad14' }} />
          )}
          关系健康报告
        </Space>
      }
    >
      <div className="health-score-display">
        <Statistic
          value={Math.round(healthScore * 100)}
          suffix="分"
          valueStyle={{ color: isGood ? '#52c41a' : '#faad14' }}
        />
        <Text type={isGood ? 'success' : 'warning'}>
          {isGood ? '关系非常健康！' : '需要关注'}
        </Text>
      </div>
    </Card>
  )
}

/**
 * 关系天气
 */
export const RelationshipWeather: React.FC<{ weather: string; score: number }> = ({
  weather,
  score
}) => {
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

// 从 antd 导入 CheckCircleOutlined, WarningOutlined, ThunderboltOutlined
import { CheckCircleOutlined, WarningOutlined, ThunderboltOutlined } from '@ant-design/icons'