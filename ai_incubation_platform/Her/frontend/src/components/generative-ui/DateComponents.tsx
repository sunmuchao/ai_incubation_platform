/**
 * 约会相关组件
 */
import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  List,
  Space,
  Rate,
  Empty,
  Descriptions
} from 'antd'
import { EnvironmentOutlined } from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 约会地点列表
 */
export const DateSpotList: React.FC<{ spots: any[] }> = ({ spots }) => {
  return (
    <List
      dataSource={spots}
      renderItem={(spot) => (
        <List.Item>
          <Card className="date-spot-card" size="small">
            <div className="date-spot-header">
              <Space>
                <EnvironmentOutlined style={{ color: '#1890ff' }} />
                <Title level={5}>{spot.name}</Title>
              </Space>
              <Rate disabled defaultValue={spot.rating} allowHalf />
            </div>
            <div className="date-spot-content">
              <Text type="secondary">{spot.type}</Text>
              <br />
              <Text>{spot.address}</Text>
              <br />
              <Space split={<span>|</span>}>
                <Tag color="green">{spot.price_range}</Tag>
                <Text>距中点{spot.distance_from_midpoint}m</Text>
              </Space>
            </div>
            <Paragraph className="date-spot-reason" type="secondary">
              推荐理由：{spot.reason}
            </Paragraph>
          </Card>
        </List.Item>
      )}
    />
  )
}

/**
 * 约会计划轮播
 */
export const DatePlanCarousel: React.FC<{ plans: any[]; onAction?: (action: GenerativeAction) => void }> = ({
  plans,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = plans[currentIndex]
  if (!current) return <Empty description="暂无约会计划" />

  return (
    <Card className="date-plan-carousel">
      <div className="date-plan-content">
        <Title level={4}>{current.title}</Title>
        <Paragraph>{current.description}</Paragraph>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="时间">{current.duration}</Descriptions.Item>
          <Descriptions.Item label="预算">¥{current.budget}</Descriptions.Item>
          <Descriptions.Item label="适合">{current.suitable_for}</Descriptions.Item>
          <Descriptions.Item label="评分">
            <Rate disabled defaultValue={current.rating} />
          </Descriptions.Item>
        </Descriptions>
      </div>
      <div className="date-plan-nav">
        <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
          上一个
        </Button>
        <Text>
          {currentIndex + 1} / {plans.length}
        </Text>
        <Button disabled={currentIndex === plans.length - 1} onClick={() => setCurrentIndex(i => i + 1)}>
          下一个
        </Button>
      </div>
      <div className="date-plan-actions">
        <Space>
          <Button type="primary" onClick={() => onAction?.({ type: 'book_date', plan: current })}>
            预订此约会
          </Button>
          <Button onClick={() => onAction?.({ type: 'save_plan', plan: current })}>收藏</Button>
        </Space>
      </div>
    </Card>
  )
}