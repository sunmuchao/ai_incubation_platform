/**
 * 匹配相关组件
 */
import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Avatar,
  List,
  Space,
  Empty
} from 'antd'
import { HeartOutlined } from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 匹配聚焦卡片 - 展示单个高匹配对象
 */
export const MatchSpotlight: React.FC<{ match: any; onAction?: (action: GenerativeAction) => void }> = ({
  match,
  onAction
}) => {
  return (
    <div className="match-spotlight-card">
      <div className="match-avatar-section">
        <Avatar size={120} src={match.avatar_url || '/default-avatar.png'} />
        <div className="match-score-badge">{Math.round(match.score * 100)}%</div>
      </div>
      <div className="match-info-section">
        <Title level={3}>{match.name}</Title>
        <Text type="secondary">{match.age}岁 · {match.location}</Text>
        <Paragraph className="match-reasoning">
          <HeartOutlined /> {match.reasoning}
        </Paragraph>
        <div className="common-interests">
          <Text strong>共同兴趣：</Text>
          <Space wrap>
            {match.common_interests?.map((interest: string, i: number) => (
              <Tag key={i} color="blue">{interest}</Tag>
            ))}
          </Space>
        </div>
      </div>
      <div className="match-actions">
        <Space>
          <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match })}>
            查看详细资料
          </Button>
          <Button onClick={() => onAction?.({ type: 'start_chat', match })}>
            开始聊天
          </Button>
        </Space>
      </div>
    </div>
  )
}

/**
 * 匹配卡片列表
 */
export const MatchCardList: React.FC<{ matches: any[]; onAction?: (action: GenerativeAction) => void }> = ({
  matches,
  onAction
}) => {
  return (
    <List
      grid={{ gutter: 16, column: 1 }}
      dataSource={matches}
      renderItem={(match) => (
        <List.Item>
          <Card className="match-list-item" hoverable>
            <Space>
              <Avatar src={match.avatar_url || '/default-avatar.png'} />
              <div className="match-list-info">
                <Text strong>{match.name}</Text>
                <br />
                <Text type="secondary">{match.age}岁 · {match.location}</Text>
              </div>
              <div className="match-list-score">
                <Tag color="red">{Math.round(match.score * 100)}%</Tag>
              </div>
              <Button type="link" onClick={() => onAction?.({ type: 'view_profile', match })}>
                查看
              </Button>
            </Space>
          </Card>
        </List.Item>
      )}
    />
  )
}

/**
 * 匹配轮播卡片
 */
export const MatchCarousel: React.FC<{ matches: any[]; onAction?: (action: GenerativeAction) => void }> = ({
  matches,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = matches[currentIndex]
  if (!current) return <Empty description="暂无匹配" />

  return (
    <div className="match-carousel">
      <Card className="match-carousel-card">
        <div className="match-carousel-content">
          <Avatar size={100} src={current.avatar_url || '/default-avatar.png'} />
          <div className="match-carousel-info">
            <Title level={4}>{current.name}</Title>
            <Text>{current.reasoning}</Text>
            <div className="match-interests">
              <Space wrap>
                {current.common_interests?.map((interest: string, i: number) => (
                  <Tag key={i} color="blue">{interest}</Tag>
                ))}
              </Space>
            </div>
          </div>
        </div>
        <div className="match-carousel-nav">
          <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
            上一个
          </Button>
          <Text>
            {currentIndex + 1} / {matches.length}
          </Text>
          <Button
            disabled={currentIndex === matches.length - 1}
            onClick={() => setCurrentIndex(i => i + 1)}
          >
            下一个
          </Button>
        </div>
        <div className="match-carousel-actions">
          <Space>
            <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match: current })}>
              查看详细资料
            </Button>
            <Button onClick={() => onAction?.({ type: 'start_chat', match: current })}>
              开始聊天
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}