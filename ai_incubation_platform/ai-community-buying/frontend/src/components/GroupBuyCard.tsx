/**
 * Bento Grid 风格团购卡片 - Linear 风格设计
 */
import React, { useState, useEffect } from 'react'
import {
  TeamOutlined,
  ClockCircleOutlined,
  FireOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'

interface Product {
  id: number
  name: string
  imageUrl?: string
  price: number
}

interface GroupBuy {
  id: number
  product?: Product
  targetQuantity: number
  joinedCount: number
  deadline: string
  status: 'open' | 'success' | 'failed' | 'expired'
  groupPrice?: number
  successProbability?: number
  isUrgent?: boolean
  factors?: string[]
}

interface GroupCardProps {
  groupBuy: GroupBuy
  onJoin?: (groupBuy: GroupBuy) => void
  onShare?: (groupBuy: GroupBuy) => void
  compact?: boolean
}

export const GroupBuyCard: React.FC<GroupCardProps> = ({
  groupBuy,
  onJoin,
  onShare,
  compact = false,
}) => {
  const [hovered, setHovered] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)

  const progress = Math.round((groupBuy.joinedCount / groupBuy.targetQuantity) * 100)
  const isCompleted = groupBuy.status === 'success' || progress >= 100
  const isUrgent = !isCompleted && timeLeft > 0 && timeLeft < 3600000 // 1 小时内

  // 倒计时
  useEffect(() => {
    const updateTimer = () => {
      const deadline = new Date(groupBuy.deadline).getTime()
      const now = Date.now()
      const left = deadline - now
      setTimeLeft(Math.max(0, left))
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [groupBuy.deadline])

  const formatTimeLeft = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60))
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((ms % (1000 * 60)) / 1000)

    if (hours > 24) {
      return `${Math.floor(hours / 24)}天 ${hours % 24}小时`
    } else if (hours > 0) {
      return `${hours}小时 ${minutes}分`
    } else if (minutes > 0) {
      return `${minutes}分 ${seconds}秒`
    } else {
      return '即将截止'
    }
  }

  const getProbabilityColor = (prob: number) => {
    if (prob > 80) return 'var(--color-success)'
    if (prob > 50) return 'var(--color-warning)'
    return 'var(--color-error)'
  }

  const getProbabilityText = (prob: number) => {
    if (prob > 80) return '很高'
    if (prob > 50) return '中等'
    return '较低'
  }

  const statusConfig: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
    open: { color: 'var(--color-primary)', text: '进行中', icon: <FireOutlined /> },
    success: { color: 'var(--color-success)', text: '已成团', icon: <CheckCircleOutlined /> },
    failed: { color: 'var(--color-error)', text: '已失败', icon: <ExclamationCircleOutlined /> },
    expired: { color: 'var(--color-text-tertiary)', text: '已过期', icon: <ClockCircleOutlined /> },
  }

  const status = statusConfig[groupBuy.status] || statusConfig.open

  return (
    <div
      className="bento-card"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: hovered ? 'translateY(-2px)' : 'none',
        boxShadow: hovered
          ? 'var(--shadow-bento-hover)'
          : 'var(--shadow-bento)',
        borderLeft: `3px solid ${
          isCompleted ? 'var(--color-success)' : isUrgent ? 'var(--color-accent)' : 'var(--color-primary)'
        }`,
      }}
    >
      {/* 头部 - 状态和标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span
              className="tag"
              style={{
                background: status.color === 'var(--color-success)'
                  ? 'var(--color-success-light)'
                  : status.color === 'var(--color-error)'
                  ? 'var(--color-error-light)'
                  : status.color === 'var(--color-primary)'
                  ? 'var(--color-info-light)'
                  : 'var(--color-bg-tertiary)',
                color: status.color,
              }}
            >
              {status.icon}
              <span style={{ marginLeft: 4 }}>{status.text}</span>
            </span>
            {isUrgent && (
              <span
                className="tag"
                style={{
                  background: 'var(--color-accent-light)',
                  color: 'var(--color-accent)',
                  animation: 'pulse 2s infinite',
                }}
              >
                <ExclamationCircleOutlined /> 即将截止
              </span>
            )}
          </div>
          <h3
            style={{
              fontSize: compact ? 14 : 15,
              fontWeight: 600,
              color: 'var(--color-text-primary)',
              margin: 0,
              lineHeight: 1.4,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: compact ? 'nowrap' : 'normal',
              display: '-webkit-box',
              WebkitLineClamp: compact ? 1 : 2,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {groupBuy.product?.name || `团购 #${groupBuy.id}`}
          </h3>
        </div>

        {/* 商品缩略图 */}
        {groupBuy.product?.imageUrl && (
          <div
            style={{
              width: 60,
              height: 60,
              borderRadius: 'var(--radius-bento-sm)',
              overflow: 'hidden',
              flexShrink: 0,
              marginLeft: 12,
            }}
          >
            <img
              src={groupBuy.product.imageUrl}
              alt={groupBuy.product.name}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </div>
        )}
      </div>

      {/* 进度条 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
            参团进度
          </span>
          <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 500 }}>
            {groupBuy.joinedCount} / {groupBuy.targetQuantity} 人
          </span>
        </div>
        <div
          style={{
            height: 8,
            background: 'var(--color-bg-tertiary)',
            borderRadius: 4,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              background: `linear-gradient(90deg,
                ${progress > 80 ? 'var(--color-success)' :
                 progress > 50 ? 'var(--color-primary)' : 'var(--color-warning)'} 0%,
                ${progress > 80 ? 'var(--color-success-light)' :
                 progress > 50 ? 'var(--color-info-light)' : 'var(--color-warning-light)'} 100%
              )`,
              borderRadius: 4,
              transition: 'width 0.5s ease',
            }}
          />
        </div>
      </div>

      {/* 成团概率 */}
      {groupBuy.successProbability && !compact && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              成团概率
            </span>
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: getProbabilityColor(groupBuy.successProbability),
              }}
            >
              {groupBuy.successProbability}% - {getProbabilityText(groupBuy.successProbability)}
            </span>
          </div>
          <div
            style={{
              height: 4,
              background: 'var(--color-bg-tertiary)',
              borderRadius: 2,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${groupBuy.successProbability}%`,
                background: getProbabilityColor(groupBuy.successProbability),
                borderRadius: 2,
                transition: 'width 0.5s ease',
              }}
            />
          </div>
        </div>
      )}

      {/* 底部信息 */}
      <div
        style={{
          marginTop: 'auto',
          paddingTop: 12,
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {/* 倒计时 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ClockCircleOutlined
            style={{
              color: isUrgent ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
              fontSize: 14,
            }}
          />
          <span
            style={{
              fontSize: 12,
              color: isUrgent ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              fontWeight: isUrgent ? 500 : 400,
            }}
          >
            {formatTimeLeft(timeLeft)}
          </span>
        </div>

        {/* 团购价格 */}
        {groupBuy.groupPrice && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              color: 'var(--color-accent)',
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            <ThunderboltOutlined style={{ fontSize: 12 }} />
            ¥{groupBuy.groupPrice.toFixed(2)}
          </div>
        )}
      </div>

      {/* 影响因素 */}
      {groupBuy.factors && groupBuy.factors.length > 0 && !compact && (
        <div
          style={{
            marginTop: 12,
            padding: '8px 12px',
            background: 'var(--color-bg-tertiary)',
            borderRadius: 'var(--radius-bento-sm)',
            fontSize: 12,
            color: 'var(--color-text-secondary)',
          }}
        >
          <ExclamationCircleOutlined style={{ marginRight: 6 }} />
          {groupBuy.factors.slice(0, 2).join(' · ')}
        </div>
      )}

      {/* 操作按钮 */}
      <div
        style={{
          marginTop: 12,
          display: 'flex',
          gap: 8,
          opacity: hovered || compact ? 1 : 0,
          transform: hovered || compact ? 'translateY(0)' : 'translateY(4px)',
          transition: 'all 0.2s ease',
        }}
      >
        <button
          className="btn-primary"
          style={{ flex: 1 }}
          onClick={(e) => {
            e.stopPropagation()
            onJoin?.(groupBuy)
          }}
          disabled={isCompleted || groupBuy.status === 'failed' || groupBuy.status === 'expired'}
        >
          <TeamOutlined /> {isCompleted ? '已成团' : '立即参团'}
        </button>
        {!compact && (
          <button
            className="btn-secondary"
            style={{ flex: 1 }}
            onClick={(e) => {
              e.stopPropagation()
              onShare?.(groupBuy)
            }}
            disabled={isCompleted || groupBuy.status === 'failed' || groupBuy.status === 'expired'}
          >
            <FireOutlined /> 邀请好友
          </button>
        )}
      </div>
    </div>
  )
}
