// SwipeMatchContainer - 滑动匹配容器组件
// 管理卡片堆栈、滑动逻辑和匹配流程

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import { message, Modal, Typography, Button, Tag, Empty, Spin } from 'antd'
import {
  HeartFilled,
  CloseOutlined,
  ThunderboltFilled,
  ReloadOutlined,
  MessageFilled,
  CheckCircleOutlined,
  UserOutlined,
  EnvironmentOutlined,
  StarFilled,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { MatchCandidate, SwipeAction, SwipeLimit } from '../types'
import { matchingApi, aiAwarenessApi } from '../api'
import { authStorage } from '../utils/storage'
import SwipeMatchCard from './SwipeMatchCard'
import './SwipeMatchContainer.less'

const { Text, Paragraph, Title } = Typography

// 滑动结果类型
interface SwipeActionResult {
  action: SwipeAction
  match: MatchCandidate
  isMatch: boolean
  timestamp: number
}

// 匹配成功弹窗数据
interface MatchNotification {
  matchedUser: MatchCandidate['user']
  compatibilityScore: number
  commonInterests: string[]
}

const SwipeMatchContainer: React.FC = () => {
  const { t } = useTranslation()
  // 状态
  const [candidates, setCandidates] = useState<MatchCandidate[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [swipeHistory, setSwipeHistory] = useState<SwipeActionResult[]>([])
  const [matchNotification, setMatchNotification] = useState<MatchNotification | null>(null)
  const [swipeLimits, setSwipeLimits] = useState<SwipeLimit | null>(null)
  const [showMatchDetails, setShowMatchDetails] = useState<MatchCandidate | null>(null)

  // 引用
  const containerRef = useRef<HTMLDivElement>(null)
  const swipeCountRef = useRef(0)

  // 用户 ID
  const userId = useMemo(() => authStorage.getUserId(), [])

  // 加载推荐列表
  const loadCandidates = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await matchingApi.getRecommendations(15)
      setCandidates(result)
      setCurrentIndex(0)
      setSwipeHistory([])

      // 加载滑动限制
      if (userId) {
        const limitsResponse = await matchingApi.getDailyLimits?.(userId) || {
          daily_likes: 50,
          daily_super_likes: 5,
          likes_used: swipeCountRef.current,
          super_likes_used: 0,
          likes_remaining: 50 - swipeCountRef.current,
          super_likes_remaining: 5,
          is_unlimited: false,
        }
        setSwipeLimits(limitsResponse as SwipeLimit)
      }
    } catch (error) {
      console.error('Failed to load candidates:', error)
      message.error(t('match.loadFailed'))
    } finally {
      setIsLoading(false)
    }
  }, [userId])

  // 初始化加载
  useEffect(() => {
    loadCandidates()
  }, [loadCandidates])

  // 当前活跃卡片
  const activeCandidate = useMemo(() => {
    return candidates[currentIndex] || null
  }, [candidates, currentIndex])

  // 剩余卡片数
  const remainingCount = useMemo(() => {
    return candidates.length - currentIndex
  }, [candidates.length, currentIndex])

  // 处理滑动
  const handleSwipe = useCallback(
    async (action: SwipeAction, match: MatchCandidate) => {
      // 记录滑动历史
      const result: SwipeActionResult = {
        action,
        match,
        isMatch: false,
        timestamp: Date.now(),
      }

      // 更新计数
      swipeCountRef.current += 1

      // 更新限制状态
      if (swipeLimits) {
        setSwipeLimits({
          ...swipeLimits,
          likes_used: swipeLimits.likes_used + (action === 'like' ? 1 : 0),
          super_likes_used: swipeLimits.super_likes_used + (action === 'super_like' ? 1 : 0),
          likes_remaining: swipeLimits.likes_remaining - (action === 'like' ? 1 : 0),
          super_likes_remaining: swipeLimits.super_likes_remaining - (action === 'super_like' ? 1 : 0),
        })
      }

      // 移动到下一张卡片
      setCurrentIndex((prev) => prev + 1)

      // 保存历史（用于回退功能）
      setSwipeHistory((prev) => [...prev, result])

      // 如果接近末尾，预加载更多
      if (remainingCount <= 3) {
        loadMoreCandidates()
      }
    },
    [swipeLimits, remainingCount]
  )

  // 处理滑动完成（匹配结果）
  const handleSwipeComplete = useCallback(
    (result: { action: SwipeAction; isMatch: boolean }) => {
      if (result.isMatch && activeCandidate) {
        // 显示匹配通知
        setMatchNotification({
          matchedUser: activeCandidate.user,
          compatibilityScore: activeCandidate.compatibility_score || activeCandidate.score || 0,
          commonInterests: activeCandidate.common_interests || [],
        })
      }
    },
    [activeCandidate]
  )

  // 预加载更多候选人
  const loadMoreCandidates = useCallback(async () => {
    try {
      const moreCandidates = await matchingApi.getRecommendations(10)
      setCandidates((prev) => [...prev.slice(currentIndex), ...moreCandidates])
    } catch (error) {
      console.error('Failed to load more candidates:', error)
    }
  }, [currentIndex])

  // 回退功能（Rewind）
  const handleRewind = useCallback(() => {
    if (swipeHistory.length === 0) {
      message.info(t('match.noUndo'))
      return
    }

    // 检查回退限制
    // 回退限制检查（会员回退次数待后续从 membershipApi 获取）

    const lastSwipe = swipeHistory[swipeHistory.length - 1]
    setCurrentIndex((prev) => prev - 1)
    setSwipeHistory((prev) => prev.slice(0, -1))

    // 更新计数
    swipeCountRef.current -= 1

    message.success(t('match.undoSuccess'))
  }, [swipeHistory])

  // 发起对话
  const handleStartChat = useCallback(() => {
    if (matchNotification) {
      // 跳转聊天页面（实际应使用路由 navigate('/chat')）
      message.info(t('match.goToChat'))
      setMatchNotification(null)
    }
  }, [matchNotification])

  // 渲染匹配成功弹窗
  const renderMatchModal = () => {
    if (!matchNotification) return null

    const { matchedUser, compatibilityScore, commonInterests } = matchNotification
    const scorePercent = Math.round(compatibilityScore * 100)

    return (
      <Modal
        open={true}
        closable={false}
        footer={null}
        className="match-success-modal"
        centered
        width={380}
      >
        <div className="match-modal-content">
          {/* 匹配动画 */}
          <div className="match-animation">
            <HeartFilled className="match-heart" />
          </div>

          {/* 匹配标题 */}
          <Title level={4} className="match-title">
            匹配成功！
          </Title>

          {/* 双头像 */}
          <div className="matched-avatars">
            <div className="avatar-wrapper">
              <Avatar size={80} src={matchedUser.avatar || matchedUser.avatar_url} icon={<UserOutlined />} />
              <Text className="avatar-name">你</Text>
            </div>
            <HeartFilled className="heart-connect" />
            <div className="avatar-wrapper">
              <Avatar size={80} src={matchedUser.avatar || matchedUser.avatar_url} icon={<UserOutlined />} />
              <Text className="avatar-name">{matchedUser.name}</Text>
            </div>
          </div>

          {/* 匹配度 */}
          <div className="match-score">
            <Tag color="pink" className="score-tag">
              匹配度 {scorePercent}%
            </Tag>
          </div>

          {/* 共同兴趣 */}
          {commonInterests.length > 0 && (
            <div className="common-interests">
              <Text type="secondary" className="interests-label">
                共同兴趣
              </Text>
              <div className="interests-list">
                {commonInterests.slice(0, 4).map((interest) => (
                  <Tag key={interest} className="interest-tag">
                    <StarFilled /> {interest}
                  </Tag>
                ))}
              </div>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="match-actions">
            <Button type="primary" size="large" icon={<MessageFilled />} onClick={handleStartChat} block>
              发起对话
            </Button>
            <Button size="large" onClick={() => setMatchNotification(null)} block>
              继续滑动
            </Button>
          </div>
        </div>
      </Modal>
    )
  }

  // 渲染详情弹窗
  const renderDetailsModal = () => {
    if (!showMatchDetails) return null

    const user = showMatchDetails.user
    const scorePercent = Math.round((showMatchDetails.compatibility_score || showMatchDetails.score || 0) * 100)

    return (
      <Modal
        open={true}
        onCancel={() => setShowMatchDetails(null)}
        footer={null}
        className="match-detail-modal"
        width={420}
      >
        {/* 头部 */}
        <div className="modal-profile-header">
          <Avatar size={80} src={user.avatar || user.avatar_url} icon={<UserOutlined />} />
          <div className="modal-user-info">
            <div className="user-name-row">
              <Text className="user-name">{user.name}</Text>
              {user.verified && <Tag color="blue" icon={<CheckCircleOutlined />}>已认证</Tag>}
            </div>
            <div className="user-location">
              <EnvironmentOutlined />
              <span>{user.location || '未知'}</span>
            </div>
          </div>
          <div className="modal-compatibility">
            <Text className="score">{scorePercent}%</Text>
            <Text className="label">匹配度</Text>
          </div>
        </div>

        {/* 内容 */}
        <div className="modal-content">
          {user.bio && (
            <div className="bio-section">
              <Text className="bio-text">{user.bio}</Text>
            </div>
          )}

          <div className="info-row">
            <div className="info-item">
              <Text className="info-label">年龄</Text>
              <Text className="info-value">{user.age}岁</Text>
            </div>
            <div className="info-item">
              <Text className="info-label">交友目的</Text>
              <Text className="info-value">{user.goal || '未填写'}</Text>
            </div>
          </div>

          {(user.interests?.length || 0) > 0 && (
            <div className="interests-section-modal">
              <Text className="section-label">兴趣爱好</Text>
              <div className="interests-wrap">
                {user.interests!.map((interest) => (
                  <span
                    key={interest}
                    className={`interest-tag ${(showMatchDetails.common_interests || []).includes(interest) ? 'common-tag' : ''}`}
                  >
                    {(showMatchDetails.common_interests || []).includes(interest) && (
                      <StarFilled style={{ marginRight: 4, fontSize: 10 }} />
                    )}
                    {interest}
                  </span>
                ))}
              </div>
            </div>
          )}

          {showMatchDetails.reasoning && (
            <div className="reasoning-section">
              <Text className="section-label">AI 推荐理由</Text>
              <Text className="reasoning-text">{showMatchDetails.reasoning}</Text>
            </div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="modal-actions">
          <Button
            size="large"
            className="pass-action"
            onClick={() => {
              handleSwipe('pass', showMatchDetails)
              setShowMatchDetails(null)
            }}
          >
            无感
          </Button>
          <Button
            size="large"
            type="primary"
            icon={<HeartFilled />}
            className="like-action"
            onClick={() => {
              handleSwipe('like', showMatchDetails)
              setShowMatchDetails(null)
            }}
          >
            喜欢
          </Button>
        </div>
      </Modal>
    )
  }

  // 渲染空状态
  const renderEmptyState = () => {
    return (
      <div className="swipe-empty-state">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂时没有更多推荐"
        >
          <Button icon={<ReloadOutlined />} onClick={loadCandidates}>
            重新加载
          </Button>
        </Empty>
      </div>
    )
  }

  // 渲染加载状态
  const renderLoadingState = () => {
    return (
      <div className="swipe-loading-state">
        <Spin size="large" tip="正在加载推荐...">
          <div style={{ padding: 50 }} />
        </Spin>
      </div>
    )
  }

  // 渲染滑动限制提示
  const renderLimitIndicator = () => {
    if (!swipeLimits) return null

    return (
      <div className="swipe-limits-indicator">
        <div className="limit-item likes">
          <HeartFilled />
          <Text>
            {swipeLimits.is_unlimited ? '无限' : `${swipeLimits.likes_remaining}/${swipeLimits.daily_likes}`}
          </Text>
        </div>
        <div className="limit-item super-likes">
          <ThunderboltFilled />
          <Text>
            {swipeLimits.super_likes_remaining}/{swipeLimits.daily_super_likes}
          </Text>
        </div>
      </div>
    )
  }

  // 渲染控制按钮
  const renderControlButtons = () => {
    return (
      <div className="swipe-control-buttons">
        <Button
          className="control-btn rewind-btn"
          shape="circle"
          size="large"
          icon={<ReloadOutlined />}
          onClick={handleRewind}
          disabled={swipeHistory.length === 0}
        />
        <Button
          className="control-btn pass-btn"
          shape="circle"
          size="large"
          icon={<CloseOutlined />}
          onClick={() => activeCandidate && handleSwipe('pass', activeCandidate)}
        />
        <Button
          className="control-btn super-like-btn"
          shape="circle"
          size="large"
          icon={<ThunderboltFilled />}
          onClick={() => activeCandidate && handleSwipe('super_like', activeCandidate)}
          disabled={!swipeLimits || swipeLimits.super_likes_remaining === 0}
        />
        <Button
          className="control-btn like-btn"
          shape="circle"
          size="large"
          icon={<HeartFilled />}
          onClick={() => activeCandidate && handleSwipe('like', activeCandidate)}
          disabled={!swipeLimits || swipeLimits.likes_remaining === 0}
        />
      </div>
    )
  }

  return (
    <div className="swipe-match-container" ref={containerRef}>
      {/* 顶部状态栏 */}
      <div className="swipe-header">
        <Text className="remaining-count">{remainingCount} 人待浏览</Text>
        {renderLimitIndicator()}
      </div>

      {/* 卡片区域 */}
      <div className="swipe-cards-area">
        {isLoading ? (
          renderLoadingState()
        ) : remainingCount === 0 ? (
          renderEmptyState()
        ) : (
          // 渲染卡片堆叠（最多显示 3 张）
          candidates.slice(currentIndex, currentIndex + 3).map((candidate, index) => (
            <SwipeMatchCard
              key={candidate.user.id}
              match={candidate}
              index={index}
              isActive={index === 0}
              onSwipe={handleSwipe}
              onSwipeComplete={handleSwipeComplete}
              onCardClick={() => setShowMatchDetails(candidate)}
              swipeLimits={
                swipeLimits
                  ? {
                      likesRemaining: swipeLimits.likes_remaining,
                      superLikesRemaining: swipeLimits.super_likes_remaining,
                    }
                  : undefined
              }
            />
          ))
        )}
      </div>

      {/* 底部控制按钮 */}
      {!isLoading && remainingCount > 0 && renderControlButtons()}

      {/* 弹窗 */}
      {renderMatchModal()}
      {renderDetailsModal()}
    </div>
  )
}

export default SwipeMatchContainer