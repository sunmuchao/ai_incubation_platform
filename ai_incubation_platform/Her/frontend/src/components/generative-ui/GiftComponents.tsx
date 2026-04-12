/**
 * 礼物相关组件
 */
import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Row,
  Col,
  Space,
  Empty
} from 'antd'
import { GiftOutlined } from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 礼物网格
 */
export const GiftGrid: React.FC<{ gifts: any[]; columns?: number; onAction?: (action: GenerativeAction) => void }> = ({
  gifts,
  columns = 3,
  onAction
}) => {
  return (
    <Row gutter={[16, 16]}>
      {gifts.map((gift, index) => (
        <Col key={index} xs={24} sm={columns === 3 ? 8 : 12}>
          <Card className="gift-card" hoverable>
            <div className="gift-image">
              <GiftOutlined style={{ fontSize: 48, color: '#ff69b4' }} />
            </div>
            <div className="gift-info">
              <Title level={5}>{gift.name}</Title>
              <Text type="secondary" className="gift-price">
                ¥{gift.price}
              </Text>
              <Paragraph className="gift-reason" ellipsis={{ rows: 2 }}>
                {gift.match_reason}
              </Paragraph>
            </div>
            <div className="gift-actions">
              <Space>
                <Button size="small" onClick={() => onAction?.({ type: 'compare_gift', gift })}>
                  比价
                </Button>
                <Button type="primary" size="small" onClick={() => onAction?.({ type: 'buy_gift', gift })}>
                  购买
                </Button>
              </Space>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  )
}

/**
 * 礼物轮播
 */
export const GiftCarousel: React.FC<{ gifts: any[]; onAction?: (action: GenerativeAction) => void }> = ({
  gifts,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = gifts[currentIndex]
  if (!current) return <Empty description="暂无礼物" />

  return (
    <Card className="gift-carousel-card">
      <div className="gift-carousel-content">
        <div className="gift-carousel-image">
          <GiftOutlined style={{ fontSize: 80, color: '#ff69b4' }} />
        </div>
        <div className="gift-carousel-info">
          <Title level={4}>{current.name}</Title>
          <Text type="secondary" className="gift-carousel-price">
            ¥{current.price}
          </Text>
          <Paragraph>{current.match_reason}</Paragraph>
        </div>
      </div>
      <div className="gift-carousel-nav">
        <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
          上一个
        </Button>
        <Text>
          {currentIndex + 1} / {gifts.length}
        </Text>
        <Button
          disabled={currentIndex === gifts.length - 1}
          onClick={() => setCurrentIndex(i => i + 1)}
        >
          下一个
        </Button>
      </div>
      <div className="gift-carousel-actions">
        <Button type="primary" block onClick={() => onAction?.({ type: 'buy_gift', gift: current })}>
          立即购买
        </Button>
      </div>
    </Card>
  )
}