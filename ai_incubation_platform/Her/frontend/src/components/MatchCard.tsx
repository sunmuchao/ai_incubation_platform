// MatchCard - 匹配对象卡片，温暖浪漫风格

import React, { useState, useCallback } from 'react'
import { Card, Avatar, Tag, Button, Space, Typography, Modal, Rate } from 'antd'
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
} from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { getMatchAvatarSrc } from '../utils/matchAvatar'
import { aiAwarenessApi } from '../api'
import { AIFeedback } from './AIFeedback'
import RoseButton from './RoseButton'
import VerificationBadge from './VerificationBadge'
import ConfidenceBadge from './ConfidenceBadge'
import { useCurrentUserId } from '../hooks/useCurrentUserId'
import { useMatchCompatibilityDisplay } from '../hooks/useMatchCompatibilityDisplay'
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

  // 使用统一的 userId hook
  const currentUserId = useCurrentUserId()

  const { compatibilityPercent, getCompatibilityColor, getCompatibilityText } =
    useMatchCompatibilityDisplay(match)

  const handleLike = useCallback(() => {
    setLiked(true)
    if (currentUserId && match.user?.id) {
      aiAwarenessApi.trackSwipe(currentUserId, match.user.id, 'like').catch(() => {})
    }
    setFeedbackAction('like')
    setFeedbackVisible(true)
    onLike?.()
  }, [currentUserId, match.user?.id, onLike])

  const handleSuperLike = useCallback(() => {
    if (currentUserId && match.user?.id) {
      aiAwarenessApi.trackSwipe(currentUserId, match.user.id, 'super_like').catch(() => {})
    }
    setFeedbackAction('super_like')
    setFeedbackVisible(true)
    onSuperLike?.()
  }, [currentUserId, match.user?.id, onSuperLike])

  const handlePass = useCallback(() => {
    if (currentUserId && match.user?.id) {
      aiAwarenessApi.trackSwipe(currentUserId, match.user.id, 'pass').catch(() => {})
    }
    setFeedbackAction('pass')
    setFeedbackVisible(true)
    onPass?.()
  }, [currentUserId, match.user?.id, onPass])

  const renderCompatibilityBadge = () => (
    <div className="compatibility-badge">
      <div
        className="compatibility-circle"
        style={{ background: `conic-gradient(${getCompatibilityColor(compatibilityPercent)} ${compatibilityPercent}%, #f5f5f5 ${compatibilityPercent}%)` }}
      >
        <div className="compatibility-inner">
          <Text strong style={{ fontSize: 14, color: getCompatibilityColor(compatibilityPercent) }}>
            {compatibilityPercent}%
          </Text>
        </div>
      </div>
      <Text className="compatibility-label">{getCompatibilityText(compatibilityPercent)}</Text>
    </div>
  )

  const renderActionButtons = () => (
    <div className="action-buttons">
      <Button
        className="action-btn pass-btn"
        shape="circle"
        size="large"
        icon={<CloseOutlined />}
        onClick={(e) => { e.stopPropagation(); handlePass() }}
      />
      {/* 玫瑰按钮 - 稀缺表达 */}
      <RoseButton
        targetUser={match.user}
        compatibilityScore={match.compatibility_score || match.score}
        size="large"
        showRemaining={false}
        onRoseSent={(result) => {
          if (result.success && result.isMatch) {
            setFeedbackAction('like')
            setFeedbackVisible(true)
          }
        }}
      />
      <Button
        className="action-btn super-like-btn"
        shape="circle"
        size="large"
        icon={<ThunderboltOutlined />}
        onClick={(e) => { e.stopPropagation(); handleSuperLike() }}
      />
      <Button
        className="action-btn like-btn"
        shape="circle"
        size="large"
        icon={liked ? <HeartFilled /> : <HeartOutlined />}
        type={liked ? 'primary' : 'default'}
        onClick={(e) => { e.stopPropagation(); handleLike() }}
      />
    </div>
  )

  const renderVectorHighlights = () => {
    const h = match.vector_match_highlights
    if (!h) return null

    const tags: string[] = []
    if (h.relationship_goal) tags.push(`关系目标：${h.relationship_goal}`)
    if (h.want_children) tags.push(`生育观：${h.want_children}`)
    if (h.spending_style) tags.push(`消费观：${h.spending_style}`)
    if (h.attachment_style) tags.push(`依恋：${h.attachment_style}`)
    if (h.conflict_style) tags.push(`冲突：${h.conflict_style}`)
    if (h.repair_willingness) tags.push(`修复意愿：${h.repair_willingness}`)

    if (tags.length === 0) return null

    return (
      <div className="interests-section" style={{ marginTop: 8 }}>
        <Text className="section-label">匹配依据</Text>
        <div className="interest-tags">
          {tags.slice(0, 3).map((item) => (
            <span key={item} className="interest-tag">{item}</span>
          ))}
        </div>
      </div>
    )
  }

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
              size={100}
              src={getMatchAvatarSrc(
                match.user?.name || '用户',
                match.user?.gender,
                match.user?.avatar,
                match.user?.avatar_url
              )}
              icon={<UserOutlined />}
              className="main-avatar"
            />
            {match.user?.verified && (
              <VerificationBadge verified size="small" className="verified-badge" />
            )}
            {/* v1.30: 置信度徽章 */}
            {match.user?.id && (
              <ConfidenceBadge
                userId={match.user.id}
                size="small"
                showTooltip={true}
                showPercent={false}
                className="confidence-badge-inline"
              />
            )}
          </div>
          {renderCompatibilityBadge()}
        </div>

        <div className="match-card-body">
          <div className="user-header">
            <Text className="user-name">{match.user?.name || '未命名'}</Text>
            <Text className="user-age">{match.user?.age || '?'}岁</Text>
          </div>

          <div className="user-location">
            <EnvironmentOutlined />
            <Text type="secondary">{match.user?.location || '未知'}</Text>
          </div>

          <Paragraph ellipsis={{ rows: 2 }} className="user-bio">
            {match.user?.bio || '这个人很神秘~'}
          </Paragraph>

          {(match.user?.interests?.length || 0) > 0 && (
            <div className="interests-section">
              <Text className="section-label">兴趣爱好</Text>
              <div className="interest-tags">
                {match.user!.interests!.slice(0, 4).map((interest) => (
                  <span key={interest} className="interest-tag">{interest}</span>
                ))}
                {(match.user?.interests?.length || 0) > 4 && (
                  <span className="interest-tag">+{(match.user!.interests!.length || 0) - 4}</span>
                )}
              </div>
            </div>
          )}

          {renderVectorHighlights()}
        </div>

        {isSwipeMode && renderActionButtons()}
      </Card>

      {/* 详情弹窗 - 简洁版 */}
      <Modal
        open={showDetails}
        onCancel={() => setShowDetails(false)}
        footer={null}
        width={420}
        className="match-detail-modal"
        closable={false}
      >
        {/* 头部信息 */}
        <div className="modal-profile-header">
          <Avatar
            size={72}
            src={getMatchAvatarSrc(
              match.user?.name || '用户',
              match.user?.gender,
              match.user?.avatar,
              match.user?.avatar_url
            )}
            icon={<UserOutlined />}
            className="modal-avatar"
          />
          <div className="modal-user-info">
            <div className="user-name-row">
              <Text className="user-name">{match.user?.name}</Text>
              {match.user?.verified && (
                <Tag color="blue" icon={<CheckCircleOutlined />}>已认证</Tag>
              )}
            </div>
            <div className="user-location">
              <EnvironmentOutlined />
              <span>{match.user?.location || '未知'}</span>
            </div>
          </div>
          <div className="modal-compatibility">
            <Text className="score">{compatibilityPercent}%</Text>
            <Text className="label">匹配度</Text>
          </div>
        </div>

        {/* 内容区 */}
        <div className="modal-content">
          {/* 个人简介 */}
          {match.user?.bio && (
            <div className="bio-section">
              <Text className="bio-text">{match.user.bio}</Text>
            </div>
          )}

          {/* 基本信息行 */}
          <div className="info-row">
            <div className="info-item">
              <Text className="info-label">年龄</Text>
              <Text className="info-value">{match.user?.age || '?'}岁</Text>
            </div>
            <div className="info-item">
              <Text className="info-label">交友目的</Text>
              <Text className="info-value">{match.user?.goal || '未填写'}</Text>
            </div>
          </div>

          {/* 兴趣标签 */}
          {(match.user?.interests?.length || 0) > 0 && (
            <div className="interests-section-modal">
              <Text className="section-label">兴趣爱好</Text>
              <div className="interests-wrap">
                {match.user!.interests!.map((interest) => (
                  <span
                    key={interest}
                    className={`interest-tag ${(match.common_interests || []).includes(interest) ? 'common-tag' : ''}`}
                  >
                    {(match.common_interests || []).includes(interest) && <StarFilled style={{ marginRight: 4, fontSize: 10 }} />}
                    {interest}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* AI 推荐理由 */}
          {match.reasoning && (
            <div className="reasoning-section">
              <Text className="section-label">AI 推荐理由</Text>
              <Text className="reasoning-text">{match.reasoning}</Text>
            </div>
          )}

          {renderVectorHighlights()}
        </div>

        {/* 操作按钮 */}
        <div className="modal-actions">
          <Button
            size="large"
            className="pass-action"
            onClick={() => { onPass?.(); setShowDetails(false) }}
          >
            无感
          </Button>
          <Button
            size="large"
            type="primary"
            icon={<MessageFilled />}
            className="message-action"
            onClick={() => { onMessage?.(); setShowDetails(false) }}
          >
            发起对话
          </Button>
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

export default React.memo(MatchCard, (prevProps, nextProps) => {
  return prevProps.match.user?.id === nextProps.match.user?.id &&
    prevProps.match.score === nextProps.match.score &&
    prevProps.match.compatibility_score === nextProps.match.compatibility_score
})