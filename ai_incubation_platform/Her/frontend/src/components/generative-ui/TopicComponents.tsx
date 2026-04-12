/**
 * 话题建议与关系策展组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Collapse,
  List,
  Space,
  Divider,
  Descriptions,
  Progress
} from 'antd'
import {
  BookOutlined,
  MessageOutlined,
  HeartOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 话题工具包
 */
export const TopicKit: React.FC<{
  topics?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ topics, onAction }) => {
  return (
    <Card className="topic-kit-card" title={<><BookOutlined /> 话题工具包</>}>
      <Collapse
        items={(topics || []).map((topic, i) => ({
          key: i,
          label: (
            <Space>
              <Tag color="blue">{topic.category}</Tag>
              <Text>{topic.title}</Text>
            </Space>
          ),
          children: (
            <div className="topic-detail">
              <Paragraph>{topic.description}</Paragraph>
              <Space>
                <Button
                  size="small"
                  onClick={() => onAction?.({ type: 'use_topic', topic })}
                >
                  使用此话题
                </Button>
                <Button
                  size="small"
                  onClick={() => onAction?.({ type: 'save_topic', topic })}
                >
                  收藏
                </Button>
              </Space>
            </div>
          )
        }))}
      />
    </Card>
  )
}

/**
 * 话题建议
 */
export const TopicSuggestions: React.FC<{
  suggestions?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ suggestions, onAction }) => {
  return (
    <Card className="topic-suggestions-card" title={<><MessageOutlined /> 话题建议</>}>
      <List
        dataSource={suggestions}
        renderItem={(suggestion) => (
          <List.Item
            actions={[
              <Button
                key="use"
                type="link"
                size="small"
                onClick={() => onAction?.({ type: 'use_topic', suggestion })}
              >
                使用
              </Button>
            ]}
          >
            <List.Item.Meta
              title={suggestion.title}
              description={suggestion.description}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

/**
 * 关系策展人
 */
export const RelationshipCurator: React.FC<{ relationship?: any }> = ({ relationship }) => {
  if (!relationship) {
    return <Card className="relationship-curator-card"><Text type="secondary">暂无关系数据</Text></Card>
  }

  return (
    <Card className="relationship-curator-card" title={<><HeartOutlined /> 关系策展</>}>
      <Descriptions column={1} bordered>
        <Descriptions.Item label="关系阶段">{relationship.stage}</Descriptions.Item>
        <Descriptions.Item label="在一起天数">{relationship.days_together}</Descriptions.Item>
        <Descriptions.Item label="互动频率">{relationship.interaction_frequency}</Descriptions.Item>
        <Descriptions.Item label="匹配度">
          <Progress
            percent={Math.round((relationship.compatibility_score || 0) * 100)}
            strokeColor="#ff6b6b"
            format={null}
          />
        </Descriptions.Item>
      </Descriptions>

      <Divider />

      <Title level={5}>关系亮点</Title>
      <List
        size="small"
        dataSource={relationship.highlights || []}
        renderItem={(highlight: string) => (
          <List.Item>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            {highlight}
          </List.Item>
        )}
      />
    </Card>
  )
}