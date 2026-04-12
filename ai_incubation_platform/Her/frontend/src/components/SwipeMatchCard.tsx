// SwipeMatchCard - Tinder 风格滑动卡片组件
// 支持手势滑动：左滑 Pass / 右滑 Like / 上滑 SuperLike

import React, { useRef, useState, useCallback, useEffect, useMemo } from 'react'
import { Avatar, Tag, Typography } from 'antd'
import {
  CheckCircleOutlined,
  UserOutlined,
  EnvironmentOutlined,
  StarFilled,
  HeartFilled,
  CloseOutlined,
  ThunderboltFilled,
} from '@ant-design/icons'
import type { MatchCandidate, SwipeAction } from '../types'
import { aiAwarenessApi, matchingApi } from '../api'
import RoseButton from './RoseButton'
import VerificationBadge from './VerificationBadge'
import { authStorage } from '../utils/storage'
import './SwipeMatchCard.less'

const { Text, Paragraph } = Typography

// 滑动阈值配置
const SWIPE_THRESHOLD = {
  distance: 100, // 最小滑动距离触发动作
  velocity: 0.3, // 最小速度触发动作
  angle: 30, // 角度阈值区分上滑和左右滑
}

// 动画配置
const ANIMATION_CONFIG = {
  exitDuration: 300, // 滑出动画时长
  returnDuration: 200, // 返回动画时长
  maxRotation: 20, // 最大旋转角度
  maxOpacity: 0.8, // 最大反馈透明度
}

interface SwipeMatchCardProps {
  match: MatchCandidate
  index: number // 卡片堆叠层级
  onSwipe?: (action: SwipeAction, match: MatchCandidate) => void
  onSwipeComplete?: (result: { action: SwipeAction; isMatch: boolean }) => void
  onCardClick?: () => void
  isActive?: boolean // 是否为当前活跃卡片（最上层）
  swipeLimits?: {
    likesRemaining: number
    superLikesRemaining: number
  }
}

const SwipeMatchCard: React.FC<SwipeMatchCardProps> = ({
  match,
  index,
  onSwipe,
  onSwipeComplete,
  onCardClick,
  isActive = true,
  swipeLimits,
}) => {
  const cardRef = useRef<HTMLDivElement>(null)

  // 状态
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [rotation, setRotation] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [swipeDirection, setSwipeDirection] = useState<SwipeAction | null>(null)
  const [isExiting, setIsExiting] = useState(false)
  const [feedbackVisible, setFeedbackVisible] = useState(false)

  // 用户 ID
  const getCurrentUserId = useCallback(() => authStorage.getUserId(), [])

  // 兼容性分数
  const compatibilityPercent = useMemo(() => {
    return match.score || match.compatibility_score
      ? Math.round((match.score || match.compatibility_score) * 100)
      : 0
  }, [match.score, match.compatibility_score])

  // 计算滑动反馈样式
  const getFeedbackStyle = useCallback(() => {
    if (!isDragging || !swipeDirection) return {}

    const opacity = Math.min(Math.abs(position.x) / SWIPE_THRESHOLD.distance, ANIMATION_CONFIG.maxOpacity)

    if (swipeDirection === 'like') {
      return {
        borderColor: `rgba(82, 196, 26, ${opacity})`,
        boxShadow: `0 0 ${20 * opacity}px rgba(82, 196, 26, ${opacity * 0.3})`,
      }
    } else if (swipeDirection === 'super_like') {
      return {
        borderColor: `rgba(212, 165, 154, ${opacity})`,
        boxShadow: `0 0 ${20 * opacity}px rgba(212, 165, 154, ${opacity * 0.3})`,
      }
    } else if (swipeDirection === 'pass') {
      return {
        borderColor: `rgba(255, 120, 117, ${opacity})`,
        boxShadow: `0 0 ${20 * opacity}px rgba(255, 120, 117, ${opacity * 0.3})`,
      }
    }
    return {}
  }, [isDragging, swipeDirection, position.x])

  // 判断滑动方向
  const determineSwipeAction = useCallback(
    (deltaX: number, deltaY: number): SwipeAction | null => {
      const absX = Math.abs(deltaX)
      const absY = Math.abs(deltaY)

      // 上滑检测（SuperLike）- 需要足够大的向上距离且角度足够垂直
      if (deltaY < -SWIPE_THRESHOLD.distance && absY > absX * 2) {
        // 检查 SuperLike 限制
        if (swipeLimits?.superLikesRemaining === 0) {
          return null // SuperLike 用完了，不触发
        }
        return 'super_like'
      }

      // 左滑（Pass）或右滑（Like）
      if (absX > SWIPE_THRESHOLD.distance) {
        if (deltaX > 0) {
          // 检查 Like 限制
          if (swipeLimits?.likesRemaining === 0) {
            return null // Like 用完了，不触发
          }
          return 'like'
        }
        return 'pass'
      }

      return null
    },
    [swipeLimits]
  )

  // 处理滑动开始
  const handleDragStart = useCallback(
    (clientX: number, clientY: number) => {
      if (!isActive || isExiting) return
      setIsDragging(true)
      setPosition({ x: 0, y: 0 })
      setRotation(0)
    },
    [isActive, isExiting]
  )

  // 处理滑动移动
  const handleDragMove = useCallback(
    (clientX: number, clientY: number, startX: number, startY: number) => {
      if (!isDragging || !isActive) return

      const deltaX = clientX - startX
      const deltaY = clientY - startY

      setPosition({ x: deltaX, y: deltaY })

      // 计算旋转角度（基于水平位移）
      const rotationAngle = Math.min(
        Math.max((deltaX / 300) * ANIMATION_CONFIG.maxRotation, -ANIMATION_CONFIG.maxRotation),
        ANIMATION_CONFIG.maxRotation
      )
      setRotation(rotationAngle)

      // 判断当前滑动方向
      const action = determineSwipeAction(deltaX, deltaY)
      setSwipeDirection(action)
      setFeedbackVisible(action !== null)
    },
    [isDragging, isActive, determineSwipeAction]
  )

  // 处理滑动结束
  const handleDragEnd = useCallback(
    (clientX: number, clientY: number, startX: number, startY: number, velocity: number) => {
      if (!isDragging || !isActive) return

      setIsDragging(false)

      const deltaX = clientX - startX
      const deltaY = clientY - startY

      // 判断是否触发滑动动作
      const action = determineSwipeAction(deltaX, deltaY)
      const shouldTrigger =
        action &&
        (Math.abs(deltaX) > SWIPE_THRESHOLD.distance ||
          Math.abs(deltaY) > SWIPE_THRESHOLD.distance ||
          velocity > SWIPE_THRESHOLD.velocity)

      if (shouldTrigger && action) {
        // 执行滑动动作
        performSwipeAction(action)
      } else {
        // 返回原位
        setPosition({ x: 0, y: 0 })
        setRotation(0)
        setSwipeDirection(null)
        setFeedbackVisible(false)
      }
    },
    [isDragging, isActive, determineSwipeAction]
  )

  // 执行滑动动作
  const performSwipeAction = useCallback(
    async (action: SwipeAction) => {
      setIsExiting(true)

      // 计算滑出方向
      const exitX = action === 'like' ? 500 : action === 'pass' ? -500 : 0
      const exitY = action === 'super_like' ? -500 : 0
      const exitRotation =
        action === 'like' ? ANIMATION_CONFIG.maxRotation : action === 'pass' ? -ANIMATION_CONFIG.maxRotation : 0

      setPosition({ x: exitX, y: exitY })
      setRotation(exitRotation)

      // 延迟后触发回调
      setTimeout(async () => {
        const userId = getCurrentUserId()
        if (userId && match.user?.id) {
          // 记录行为追踪
          aiAwarenessApi.trackSwipe(userId, match.user.id, action).catch(() => {})

          // 调用匹配 API
          try {
            const result = await matchingApi.swipe(match.user.id, action)
            onSwipeComplete?.({
              action,
              isMatch: result?.is_match || false,
            })
          } catch (error) {
            console.error('Swipe API error:', error)
          }
        }

        onSwipe?.(action, match)
      }, ANIMATION_CONFIG.exitDuration)
    },
    [getCurrentUserId, match, onSwipe, onSwipeComplete]
  )

  // 触摸事件处理
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null)

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0]
      touchStartRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() }
      handleDragStart(touch.clientX, touch.clientY)
    },
    [handleDragStart]
  )

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!touchStartRef.current) return
      const touch = e.touches[0]
      handleDragMove(touch.clientX, touch.clientY, touchStartRef.current.x, touchStartRef.current.y)
    },
    [handleDragMove]
  )

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!touchStartRef.current) return
      const touch = e.changedTouches[0]
      const timeDelta = Date.now() - touchStartRef.current.time
      const deltaX = touch.clientX - touchStartRef.current.x
      const velocity = Math.abs(deltaX) / timeDelta
      handleDragEnd(
        touch.clientX,
        touch.clientY,
        touchStartRef.current.x,
        touchStartRef.current.y,
        velocity
      )
      touchStartRef.current = null
    },
    [handleDragEnd]
  )

  // 鼠标事件处理（桌面端）
  const mouseStartRef = useRef<{ x: number; y: number; time: number } | null>(null)

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return // 只响应左键
      mouseStartRef.current = { x: e.clientX, y: e.clientY, time: Date.now() }
      handleDragStart(e.clientX, e.clientY)
      e.preventDefault()
    },
    [handleDragStart]
  )

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!mouseStartRef.current || !isDragging) return
      handleDragMove(e.clientX, e.clientY, mouseStartRef.current.x, mouseStartRef.current.y)
    },
    [isDragging, handleDragMove]
  )

  const handleMouseUp = useCallback(
    (e: MouseEvent) => {
      if (!mouseStartRef.current) return
      const timeDelta = Date.now() - mouseStartRef.current.time
      const deltaX = e.clientX - mouseStartRef.current.x
      const velocity = Math.abs(deltaX) / timeDelta
      handleDragEnd(
        e.clientX,
        e.clientY,
        mouseStartRef.current.x,
        mouseStartRef.current.y,
        velocity
      )
      mouseStartRef.current = null
    },
    [handleDragEnd]
  )

  // 全局鼠标事件监听
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  // 渲染反馈覆盖层
  const renderFeedbackOverlay = () => {
    if (!feedbackVisible || !swipeDirection) return null

    let icon = null
    let color = ''
    let text = ''

    switch (swipeDirection) {
      case 'like':
        icon = <HeartFilled style={{ fontSize: 64 }} />
        color = '#52c41a'
        text = 'LIKE'
        break
      case 'pass':
        icon = <CloseOutlined style={{ fontSize: 64 }} />
        color = '#ff7875'
        text = 'PASS'
        break
      case 'super_like':
        icon = <ThunderboltFilled style={{ fontSize: 64 }} />
        color = '#D4A59A'
        text = 'SUPER LIKE'
        break
    }

    const opacity = Math.min(Math.abs(position.x || position.y) / SWIPE_THRESHOLD.distance, 1)

    return (
      <div className="swipe-feedback-overlay" style={{ opacity }}>
        <div className="feedback-icon" style={{ color }}>
          {icon}
        </div>
        <div className="feedback-text" style={{ color }}>
          {text}
        </div>
      </div>
    )
  }

  // 渲染限制提示
  const renderLimitWarning = () => {
    if (!swipeLimits) return null

    if (swipeDirection === 'like' && swipeLimits.likesRemaining === 0) {
      return (
        <div className="limit-warning">
          <Text type="warning">今日喜欢次数已用完</Text>
        </div>
      )
    }

    if (swipeDirection === 'super_like' && swipeLimits.superLikesRemaining === 0) {
      return (
        <div className="limit-warning">
          <Text type="warning">今日超级喜欢次数已用完</Text>
        </div>
      )
    }

    return null
  }

  // 卡片样式
  const cardStyle: React.CSSProperties = {
    transform: `translate(${position.x}px, ${position.y}px) rotate(${rotation}deg)`,
    transition: isDragging ? 'none' : `all ${ANIMATION_CONFIG.returnDuration}ms ease-out`,
    zIndex: 100 - index,
    opacity: isExiting ? 0 : 1 - index * 0.1,
    scale: `${1 - index * 0.05}`,
    ...getFeedbackStyle(),
  }

  // 兼容性颜色
  const getCompatibilityColor = (score: number) => {
    if (score >= 85) return '#95de64'
    if (score >= 70) return '#D4A59A'
    return '#faad14'
  }

  return (
    <div
      ref={cardRef}
      className={`swipe-match-card ${isActive ? 'active' : ''} ${isExiting ? 'exiting' : ''}`}
      style={cardStyle}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onMouseDown={handleMouseDown}
      onClick={() => {
        if (!isDragging && !isExiting && onCardClick) {
          onCardClick()
        }
      }}
    >
      {/* 滑动反馈层 */}
      {renderFeedbackOverlay()}
      {renderLimitWarning()}

      {/* 卡片内容 */}
      <div className="swipe-card-content">
        {/* 头部：头像 + 兼容度 */}
        <div className="swipe-card-header">
          <div className="avatar-container">
            <Avatar
              size={120}
              src={match.user?.avatar || match.user?.avatar_url}
              icon={<UserOutlined />}
              className="swipe-avatar"
            />
            {match.user?.verified && (
              <VerificationBadge verified size="small" className="verified-badge" />
            )}
          </div>

          <div className="compatibility-badge">
            <div
              className="compatibility-circle"
              style={{
                background: `conic-gradient(${getCompatibilityColor(compatibilityPercent)} ${compatibilityPercent}%, #f5f5f5 ${compatibilityPercent}%)`,
              }}
            >
              <div className="compatibility-inner">
                <Text strong style={{ fontSize: 16, color: getCompatibilityColor(compatibilityPercent) }}>
                  {compatibilityPercent}%
                </Text>
              </div>
            </div>
          </div>
        </div>

        {/* 基本信息 */}
        <div className="swipe-card-body">
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

          {/* 兴趣标签 */}
          {(match.user?.interests?.length || 0) > 0 && (
            <div className="interests-section">
              <div className="interest-tags">
                {match.user!.interests!.slice(0, 4).map((interest) => (
                  <span key={interest} className="interest-tag">
                    {(match.common_interests || []).includes(interest) && (
                      <StarFilled style={{ marginRight: 4, fontSize: 10 }} />
                    )}
                    {interest}
                  </span>
                ))}
                {(match.user?.interests?.length || 0) > 4 && (
                  <span className="interest-tag more">+{(match.user!.interests!.length || 0) - 4}</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 滑动指示器（底部） */}
      <div className="swipe-indicators">
        <div className="indicator pass-indicator">
          <CloseOutlined />
        </div>
        {/* 玫瑰按钮 */}
        <RoseButton
          targetUser={match.user}
          compatibilityScore={match.compatibility_score || match.score || 0}
          size="default"
          showRemaining={false}
          disabled={!isActive}
        />
        <div className="indicator super-like-indicator">
          <ThunderboltFilled />
        </div>
        <div className="indicator like-indicator">
          <HeartFilled />
        </div>
      </div>
    </div>
  )
}

export default React.memo(SwipeMatchCard, (prevProps, nextProps) => {
  return (
    prevProps.match.user?.id === nextProps.match.user?.id &&
    prevProps.index === nextProps.index &&
    prevProps.isActive === nextProps.isActive &&
    prevProps.swipeLimits?.likesRemaining === nextProps.swipeLimits?.likesRemaining &&
    prevProps.swipeLimits?.superLikesRemaining === nextProps.swipeLimits?.superLikesRemaining
  )
})