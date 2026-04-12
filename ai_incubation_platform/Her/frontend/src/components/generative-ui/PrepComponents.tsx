/**
 * 活动准备与约会助手组件
 */
import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Checkbox,
  List,
  Space,
  Descriptions,
  Row,
  Col,
  Rate,
  Divider
} from 'antd'
import {
  CheckSquareOutlined,
  ShoppingOutlined,
  CalendarOutlined,
  TrophyOutlined,
  EnvironmentOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 准备清单
 */
export const PrepChecklist: React.FC<{
  items?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ items, onAction }) => {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({})

  return (
    <Card className="prep-checklist-card" title={<><CheckSquareOutlined /> 准备清单</>}>
      <List
        dataSource={items || []}
        renderItem={(item, index) => (
          <List.Item>
            <Checkbox
              checked={checkedItems[index]}
              onChange={(e) =>
                setCheckedItems({ ...checkedItems, [index]: e.target.checked })
              }
            >
              <div className="checklist-item">
                <Text>{item.task}</Text>
                {item.priority === 'high' && <Tag color="red">重要</Tag>}
              </div>
            </Checkbox>
          </List.Item>
        )}
      />
      <Button
        type="primary"
        block
        onClick={() => onAction?.({ type: 'complete_prep', items: checkedItems })}
      >
        准备完成
      </Button>
    </Card>
  )
}

/**
 * 着装建议
 */
export const OutfitRecommendations: React.FC<{ outfits?: any[] }> = ({ outfits }) => {
  return (
    <Card className="outfit-recommendations" title={<><ShoppingOutlined /> 着装建议</>}>
      <Row gutter={[16, 16]}>
        {(outfits || []).map((outfit, i) => (
          <Col span={24} key={i}>
            <Card size="small">
              <div className="outfit-item">
                <Title level={5}>{outfit.name}</Title>
                <Paragraph type="secondary">{outfit.description}</Paragraph>
                <Tag color={outfit.occasion === 'formal' ? 'purple' : 'blue'}>
                  {outfit.occasion}
                </Tag>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  )
}

/**
 * 约会助手卡片
 */
export const DateAssistantCard: React.FC<{
  suggestion?: any
  onAction?: (action: GenerativeAction) => void
}> = ({ suggestion, onAction }) => {
  if (!suggestion) {
    return <Card className="date-assistant-card"><Text type="secondary">暂无约会建议</Text></Card>
  }

  return (
    <Card className="date-assistant-card">
      <div className="date-suggestion">
        <Title level={5}>{suggestion.title}</Title>
        <Paragraph>{suggestion.description}</Paragraph>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="最佳时间">{suggestion.best_time}</Descriptions.Item>
          <Descriptions.Item label="预计时长">{suggestion.duration}</Descriptions.Item>
        </Descriptions>
        <Space className="date-actions">
          <Button type="primary" onClick={() => onAction?.({ type: 'accept_suggestion', suggestion })}>
            接受建议
          </Button>
          <Button onClick={() => onAction?.({ type: 'dismiss_suggestion', suggestion })}>跳过</Button>
        </Space>
      </div>
    </Card>
  )
}

/**
 * 约会回顾
 */
export const DateReview: React.FC<{ review?: any }> = ({ review }) => {
  if (!review) {
    return <Card className="date-review-card"><Text type="secondary">暂无约会回顾</Text></Card>
  }

  return (
    <Card className="date-review-card" title={<><CalendarOutlined /> 约会回顾</>}>
      <div className="date-review-summary">
        <Title level={5}>{review.date_title}</Title>
        <Text type="secondary">{review.date}</Text>
        <Rate disabled defaultValue={review.rating} allowHalf className="date-review-rating" />
      </div>

      <Divider />

      <div className="date-review-details">
        <Title level={6}>亮点时刻</Title>
        <Paragraph>{review.highlight}</Paragraph>

        <Title level={6}>改进建议</Title>
        <Paragraph type="secondary">{review.suggestion}</Paragraph>
      </div>
    </Card>
  )
}

/**
 * 场地推荐
 */
export const VenueRecommendations: React.FC<{ venues?: any[] }> = ({ venues }) => {
  return (
    <Card className="venue-recommendations" title={<><EnvironmentOutlined /> 场地推荐</>}>
      <List
        dataSource={venues || []}
        renderItem={(venue) => (
          <List.Item>
            <List.Item.Meta
              title={venue.name}
              description={`${venue.type} · ${venue.price_range} · ${venue.distance}`}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

/**
 * 关系进展里程碑卡片
 */
export const MilestoneCard: React.FC<{
  type?: string
  status?: string
  icon?: string
  onAction?: (action: GenerativeAction) => void
}> = ({ type, status, icon = 'celebration', onAction }) => {
  if (!type) {
    return <Card className="milestone-card"><Text type="secondary">暂无里程碑记录</Text></Card>
  }

  return (
    <Card className="milestone-card" title={<><TrophyOutlined /> 关系里程碑</>}>
      <div className="milestone-result">
        <Title level={4}>已记录：{type}</Title>
        <Text type="secondary">{status === 'recorded' ? '继续用心经营你们的关系吧~' : ''}</Text>
        <Divider />
        <Space>
          <Button onClick={() => onAction?.({ type: 'view_timeline' })}>查看时间线</Button>
          <Button type="primary" onClick={() => onAction?.({ type: 'view_health' })}>
            查看健康度
          </Button>
        </Space>
      </div>
    </Card>
  )
}