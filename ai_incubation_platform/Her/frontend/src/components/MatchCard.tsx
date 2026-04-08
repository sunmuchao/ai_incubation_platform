// Generative UI - 动态生成匹配卡片 - 性能优化版

import React, { useState, useMemo, useCallback } from 'react'
import { Card, Avatar, Tag, Button, Space, Typography, Progress, Modal, Rate, Divider } from 'antd'
import {
  HeartOutlined,
  HeartFilled,
  StarFilled,
  CheckCircleOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  MessageFilled,
  UserOutlined,
  EnvironmentOutlined,
  GiftOutlined,
} from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { aiAwarenessApi } from '../api'
import { AIFeedback } from './AIFeedback'
import './MatchCard.less'

const { Text, Paragraph } = Typography

interface MatchCardProps {
  match: MatchCandidate
  onLike?: () => void
  onPass?: () => void
  onSuperLike?: () => void
  onMessage?: () => void
  isSwipeMode?: boolean
}

const MatchCard: React.FC<MatchCardProps> = ({
  match,
  onLike,
  onPass,
  onSuperLike,
  onMessage,
  isSwipeMode = false,
}) => {
  const [showDetails, setShowDetails] = useState(false)
  const [liked, setLiked] = useState(false)
  const [feedbackAction, setFeedbackAction] = useState<'like' | 'pass' | 'super_like' | null>(null)
  const [feedbackVisible, setFeedbackVisible] = useState(false)

  // 获取当前用户 ID - 使用 useCallback 稳定引用
  const getCurrentUserId = useCallback(() => {
    const userStr = localStorage.getItem('user_info')
    if (userStr) {
      try {
        const user = JSON.parse(userStr)
        return user.username || 'anonymous'
      } catch {
        return 'anonymous'
      }
    }
    return 'anonymous'
  }, [])

  // 防御性处理：确保兼容性分数有效 - 使用 useMemo 缓存计算结果
  const compatibilityPercent = useMemo(() => {
    return match.score || match.compatibility_score
      ? Math.round((match.score || match.compatibility_score) * 100)
      : 0
  }, [match.score, match.compatibility_score])

  const getCompatibilityColor = useCallback((score: number) => {
    if (score >= 85) return '#52c41a'
    if (score >= 70) return '#faad14'
    return '#ff4d4f'
  }, [])

  const getCompatibilityText = useCallback((score: number) => {
    if (score >= 90) return '天作之合'
    if (score >= 80) return '非常匹配'
    if (score >= 70) return '比较匹配'
    if (score >= 60) return '有一定缘分'
    return '需要磨合'
  }, [])

  const handleLike = useCallback(() => {
    setLiked(true)
    // 追踪滑动行为
    const userId = getCurrentUserId()
    if (userId && match.user?.id) {
      aiAwarenessApi.trackSwipe(userId, match.user.id, 'like').catch(() => {})
    }
    // 显示 AI 反馈
    setFeedbackAction('like')
    setFeedbackVisible(true)
    onLike?.()
  }, [getCurrentUserId, match.user?.id, onLike])

  const handleSuperLike = useCallback(() => {
    // 追踪超级喜欢行为
    const userId = getCurrentUserId()
    if (userId && match.user?.id) {
      aiAwarenessApi.trackSwipe(userId, match.user.id, 'super_like').catch(() => {})
    }
    // 显示 AI 反馈
    setFeedbackAction('super_like')
    setFeedbackVisible(true)
    onSuperLike?.()
  }, [getCurrentUserId, match.user?.id, onSuperLike])

  const handlePass = useCallback(() => {
    // 追踪跳过行为
    const userId = getCurrentUserId()
    if (userId && match.user?.id) {
      aiAwarenessApi.trackSwipe(userId, match.user.id, 'pass').catch(() => {})
    }
    // 显示 AI 反馈
    setFeedbackAction('pass')
    setFeedbackVisible(true)
    onPass?.()
  }, [getCurrentUserId, match.user?.id, onPass])

  const renderCompatibilityBadge = () => (
    <div className="compatibility-badge" style={{ borderColor: getCompatibilityColor(compatibilityPercent) }}>
      <div
        className="compatibility-circle"
        style={{ background: `conic-gradient(${getCompatibilityColor(compatibilityPercent)} ${compatibilityPercent}%, #f0f0f0 ${compatibilityPercent}%)` }}
      >
        <div className="compatibility-inner">
          <Text strong style={{ fontSize: 16, color: getCompatibilityColor(compatibilityPercent) }}>
            {compatibilityPercent}%
          </Text>
        </div>
      </div>
      <Text style={{ fontSize: 11, marginTop: 4, textAlign: 'center' }}>
        {getCompatibilityText(compatibilityPercent)}
      </Text>
    </div>
  )

  const renderActionButtons = () => (
    <div className="action-buttons">
      <Button
        className="action-btn pass-btn"
        shape="circle"
        size="large"
        icon={<CloseOutlined />}
        onClick={(e) => {
          e.stopPropagation()
          handlePass()
        }}
      />
      <Button
        className="action-btn super-like-btn"
        shape="circle"
        size="large"
        icon={<ThunderboltOutlined />}
        onClick={(e) => {
          e.stopPropagation()
          handleSuperLike()
        }}
      />
      <Button
        className="action-btn like-btn"
        shape="circle"
        size="large"
        icon={liked ? <HeartFilled /> : <HeartOutlined />}
        type={liked ? 'primary' : 'default'}
        onClick={(e) => {
          e.stopPropagation()
          handleLike()
        }}
      />
    </div>
  )

  return (
    <>
      <Card
        className={`match-card ${isSwipeMode ? 'swipe-mode' : ''}`}
        onClick={() => setShowDetails(true)}
        hoverable
      >
        <div className="match-card-header">
          <div className="avatar-container">
            <Avatar
              size={120}
              src={match.user?.avatar || match.user?.avatar_url}
              icon={<UserOutlined />}
              className="main-avatar"
            />
            {match.user?.verified && (
              <Tag
                color="blue"
                className="verified-badge"
                icon={<CheckCircleOutlined />}
              >
                已认证
              </Tag>
            )}
          </div>
          {renderCompatibilityBadge()}
        </div>

        <div className="match-card-body">
          <div className="user-header">
            <Text strong className="user-name">
              {match.user?.name || '未命名'}, {match.user?.age || '?'}
            </Text>
            {match.user?.gender && (
              <Tag color="purple" style={{ marginLeft: 8 }}>
                {match.user.gender}
              </Tag>
            )}
          </div>

          <div className="user-location">
            <EnvironmentOutlined />
            <Text type="secondary">{match.user?.location || '未知地区'}</Text>
          </div>

          <Paragraph
            ellipsis={{ rows: 2 }}
            className="user-bio"
          >
            {match.user?.bio || '这个人很神秘，没有写个人介绍~'}
          </Paragraph>

          <div className="interests-section">
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
              兴趣爱好
            </Text>
            <Space wrap>
              {(match.interests || []).slice(0, 5).map((interest, index) => (
                <Tag key={interest} color="blue">
                  {interest}
                </Tag>
              ))}
              {(match.interests || []).length > 5 && (
                <Tag>+{(match.interests || []).length - 5}</Tag>
              )}
            </Space>
          </div>

          {(match.common_interests || []).length > 0 && (
            <div className="common-interests-section">
              <Text strong style={{ color: '#722ed1', fontSize: 13 }}>
                ✨ 你们的共同兴趣
              </Text>
              <Space wrap style={{ marginTop: 8 }}>
                {(match.common_interests || []).map((interest) => (
                  <Tag key={interest} color="green" icon={<StarFilled />}>
                    {interest}
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          {match.reasoning && (
            <div className="matching-reason">
              <Text type="secondary" style={{ fontSize: 12 }}>
                AI 匹配理由
              </Text>
              <Paragraph
                ellipsis={{ rows: 3 }}
                style={{ fontSize: 13, marginTop: 4 }}
              >
                {match.reasoning}
              </Paragraph>
            </div>
          )}
        </div>

        {isSwipeMode && renderActionButtons()}
      </Card>

      {/* 详情弹窗 - Generative UI 动态内容 */}
      <Modal
        title={
          <div className="modal-header">
            <Avatar src={match.user?.avatar || match.user?.avatar_url} size={40} icon={<UserOutlined />} />
            <div>
              <Text strong style={{ fontSize: 16 }}>
                {match.user?.name}
              </Text>
              <div>
                <Tag color="green">{compatibilityPercent}% 匹配</Tag>
              </div>
            </div>
          </div>
        }
        open={showDetails}
        onCancel={() => setShowDetails(false)}
        footer={
          <Space size="large">
            <Button
              size="large"
              icon={<CloseOutlined />}
              onClick={() => {
                onPass?.()
                setShowDetails(false)
              }}
            >
              无感
            </Button>
            <Button
              size="large"
              type="primary"
              icon={<MessageFilled />}
              onClick={() => {
                onMessage?.()
                setShowDetails(false)
              }}
            >
              发起对话
            </Button>
          </Space>
        }
        width={520}
      >
        <div className="modal-content">
          <Divider orientation="left">关于 TA</Divider>
          <Paragraph>{match.user?.bio || '这个人很神秘~'}</Paragraph>

          <Divider orientation="left">详细信息</Divider>
          <div className="detail-grid">
            <div className="detail-item">
              <Text type="secondary">年龄</Text>
              <Text strong>{match.user?.age}岁</Text>
            </div>
            <div className="detail-item">
              <Text type="secondary">所在地</Text>
              <Text strong>{match.user?.location}</Text>
            </div>
            <div className="detail-item">
              <Text type="secondary">交友目的</Text>
              <Text strong>{match.user?.goal || '未填写'}</Text>
            </div>
            <div className="detail-item">
              <Text type="secondary">认证状态</Text>
              {match.user?.verified ? (
                <Tag color="blue" icon={<CheckCircleOutlined />}>已认证</Tag>
              ) : (
                <Tag>未认证</Tag>
              )}
            </div>
          </div>

          <Divider orientation="left">兴趣爱好</Divider>
          <Space wrap>
            {match.user?.interests?.map((interest) => (
              <Tag key={interest} color="blue" icon={<GiftOutlined />}>
                {interest}
              </Tag>
            ))}
          </Space>

          {(match.common_interests || []).length > 0 && (
            <>
              <Divider orientation="left">共同兴趣</Divider>
              <Space wrap>
                {(match.common_interests || []).map((interest) => (
                  <Tag key={interest} color="green" icon={<StarFilled />}>
                    {interest}
                  </Tag>
                ))}
              </Space>
            </>
          )}

          <Divider orientation="left">匹配度分析</Divider>
          <div className="compatibility-details">
            <div className="compatibility-row">
              <Text>综合匹配度</Text>
              <Progress
                percent={compatibilityPercent}
                strokeColor={getCompatibilityColor(compatibilityPercent)}
                showInfo={false}
                size="small"
              />
            </div>
            {Object.entries(match.score_breakdown || {}).slice(0, 4).map(([key, value]) => (
              <div key={key} className="compatibility-row">
                <Text type="secondary">{key}</Text>
                <Progress
                  percent={Math.round(value * 100)}
                  strokeColor={getCompatibilityColor(Math.round(value * 100))}
                  showInfo={false}
                  size="small"
                />
              </div>
            ))}
          </div>

          {match.reasoning && (
            <>
              <Divider orientation="left">AI 推荐理由</Divider>
              <Paragraph className="ai-reasoning">{match.reasoning}</Paragraph>
            </>
          )}
        </div>
      </Modal>

      {/* AI 感知反馈 */}
      <AIFeedback
        action={feedbackAction}
        visible={feedbackVisible}
        onClose={() => setFeedbackVisible(false)}
      />
    </>
  )
}

// 使用 React.memo 优化组件重渲染
export default React.memo(MatchCard, (prevProps, nextProps) => {
  // 只有当 match 的 id 或分数变化时才重新渲染
  return prevProps.match.user?.id === nextProps.match.user?.id &&
    prevProps.match.score === nextProps.match.score &&
    prevProps.match.compatibility_score === nextProps.match.compatibility_score
})
