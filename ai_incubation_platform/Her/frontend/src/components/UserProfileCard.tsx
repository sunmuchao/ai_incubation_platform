// UserProfileCard - 用户详情卡片，用于展示选中候选人信息

import React, { useMemo } from 'react'
import { Card, Avatar, Tag, Button, Space, Typography, Divider } from 'antd'
import {
  MessageOutlined,
  UserOutlined,
  EnvironmentOutlined,
  HeartOutlined,
  CheckCircleOutlined,
  BookOutlined,
  DollarOutlined,
} from '@ant-design/icons'
import ConfidenceBadge from './ConfidenceBadge'
import './MatchCard.less'

const { Text, Title, Paragraph } = Typography

// 关系目标中英文映射
const RELATIONSHIP_GOAL_MAP: Record<string, string> = {
  serious: '认真恋爱',
  marriage: '奔着结婚',
  dating: '轻松交友',
  casual: '随便聊聊',
}

// 🚀 [改进] 学历中英文映射
const EDUCATION_MAP: Record<string, string> = {
  high_school: '高中',
  college: '大专',
  bachelor: '本科',
  master: '硕士',
  phd: '博士',
}

interface UserProfileCardProps {
  user_id: string
  name: string
  age: number
  location: string
  confidence_icon?: string
  confidence_level?: string
  confidence_score?: number
  occupation?: string
  interests?: string[]
  bio?: string
  relationship_goal?: string
  avatar_url?: string
  // 🚀 [改进] 新增字段
  education?: string  // 学历
  income?: number  // 收入（万元）
  income_range?: string  // 收入范围描述
  actions?: Array<{
    label: string
    action: string
    target_user_id: string
  }>
  onStartChat?: (userId: string) => void
  onViewProfile?: (userId: string) => void
}

const UserProfileCard: React.FC<UserProfileCardProps> = ({
  user_id,
  name,
  age,
  location,
  confidence_icon = '✓',
  confidence_level = 'medium',
  confidence_score = 40,
  occupation,
  interests = [],
  bio,
  relationship_goal,
  avatar_url,
  // 🚀 [改进] 新增字段
  education,
  income,
  income_range,
  actions = [],
  onStartChat,
  onViewProfile,
}) => {
  // 置信度颜色
  const confidenceColor = useMemo(() => {
    switch (confidence_level) {
      case 'very_high':
        return '#FFD700' // 金色
      case 'high':
        return '#52c41a' // 绿色
      case 'medium':
        return '#1890ff' // 蓝色
      case 'low':
        return '#faad14' // 橙色
      default:
        return '#1890ff'
    }
  }, [confidence_level])

  // 处理按钮点击（actions.target_user_id 可能未填全，回退到卡片级 user_id）
  const handleAction = (action: string, targetUserId: string) => {
    const id = targetUserId || user_id
    if (action === 'start_chat' && onStartChat) {
      onStartChat(id)
    } else if (action === 'view_profile' && onViewProfile) {
      onViewProfile(id)
    }
  }

  return (
    <Card
      className="user-profile-card"
      style={{
        maxWidth: 400,
        borderRadius: 16,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      }}
    >
      {/* 头部和基本信息 */}
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <Avatar
          size={80}
          src={avatar_url}
          icon={<UserOutlined />}
          style={{ marginBottom: 8 }}
        />
        <Title level={4} style={{ marginBottom: 4 }}>
          {name} · {age}岁
        </Title>
        <Space size={4}>
          <EnvironmentOutlined />
          <Text type="secondary">{location}</Text>
        </Space>

        {/* 置信度标识 */}
        <div style={{ marginTop: 8 }}>
          <ConfidenceBadge
            level={confidence_level}
            score={confidence_score}
            icon={confidence_icon}
          />
        </div>
      </div>

      <Divider />

      {/* 🚀 [改进] 基础信息（职业、学历、收入） */}
      <div style={{ marginBottom: 12 }}>
        {/* 职业 */}
        {occupation && (
          <div style={{ marginBottom: 8 }}>
            <Text strong>职业：</Text>
            <Text>{occupation}</Text>
          </div>
        )}
        {/* 学历 */}
        {education && (
          <div style={{ marginBottom: 8 }}>
            <BookOutlined style={{ marginRight: 4, color: '#1890ff' }} />
            <Text strong>学历：</Text>
            <Tag color="geekblue">{EDUCATION_MAP[education] || education}</Tag>
          </div>
        )}
        {/* 收入 */}
        {(income_range || income) && (
          <div style={{ marginBottom: 8 }}>
            <DollarOutlined style={{ marginRight: 4, color: '#52c41a' }} />
            <Text strong>收入：</Text>
            <Tag color="green">{income_range || (income ? `${income}万/年` : '未填写')}</Tag>
          </div>
        )}
      </div>

      {/* 关系目标 */}
      {relationship_goal && (
        <div style={{ marginBottom: 12 }}>
          <Text strong>关系目标：</Text>
          <Tag color="pink">{RELATIONSHIP_GOAL_MAP[relationship_goal] || relationship_goal}</Tag>
        </div>
      )}

      {/* 兴趣爱好 */}
      {interests.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ marginBottom: 4, display: 'block' }}>
            兴趣爱好：
          </Text>
          <Space wrap size={4}>
            {interests.map((interest, index) => (
              <Tag key={index} color="blue">
                {interest}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* 简介 */}
      {bio && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ marginBottom: 4, display: 'block' }}>
            简介：
          </Text>
          <Paragraph
            ellipsis={{ rows: 2, expandable: true }}
            style={{ color: '#666' }}
          >
            {bio}
          </Paragraph>
        </div>
      )}

      <Divider />

      {/* 操作按钮 */}
      <Space style={{ width: '100%', justifyContent: 'center' }} size="middle">
        {actions.map((action, index) => (
          <Button
            key={index}
            type={action.action === 'start_chat' ? 'primary' : 'default'}
            icon={action.action === 'start_chat' ? <MessageOutlined /> : <UserOutlined />}
            onClick={() => handleAction(action.action, action.target_user_id)}
            style={{
              borderRadius: 8,
              minWidth: 120,
            }}
          >
            {action.label}
          </Button>
        ))}
      </Space>
    </Card>
  )
}

export default UserProfileCard