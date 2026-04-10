/**
 * Skeleton 骨架屏组件
 * 用于列表加载时的占位显示，遵循 Apple/Linear 极简美学
 */

import React from 'react'
import './Skeleton.less'

// ==================== 类型定义 ====================

interface SkeletonProps {
  /** 骨架屏类型 */
  variant?: 'text' | 'circular' | 'rectangular' | 'card' | 'avatar' | 'button'
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 是否显示动画 */
  animation?: boolean
  /** 自定义类名 */
  className?: string
  /** 自定义样式 */
  style?: React.CSSProperties
}

interface SkeletonTextProps {
  /** 行数 */
  lines?: number
  /** 最后一行宽度百分比 */
  lastLineWidth?: number | string
  /** 是否显示动画 */
  animation?: boolean
  /** 自定义类名 */
  className?: string
}

interface SkeletonCardProps {
  /** 是否显示头像 */
  showAvatar?: boolean
  /** 是否显示操作按钮 */
  showActions?: boolean
  /** 内容行数 */
  contentLines?: number
  /** 是否显示动画 */
  animation?: boolean
  /** 自定义类名 */
  className?: string
}

interface SkeletonListProps {
  /** 列表项数量 */
  count?: number
  /** 列表项类型 */
  itemVariant?: 'card' | 'list-item' | 'message'
  /** 是否显示动画 */
  animation?: boolean
  /** 自定义类名 */
  className?: string
}

// ==================== 基础骨架屏组件 ====================

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  animation = true,
  className = '',
  style = {},
}) => {
  const getVariantStyles = (): React.CSSProperties => {
    const baseStyles: React.CSSProperties = {
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
    }

    switch (variant) {
      case 'circular':
        return { ...baseStyles, borderRadius: '50%' }
      case 'rectangular':
        return { ...baseStyles, borderRadius: 8 }
      case 'card':
        return { ...baseStyles, borderRadius: 16, height: height || 120 }
      case 'avatar':
        return { ...baseStyles, borderRadius: 12, width: width || 48, height: height || 48 }
      case 'button':
        return { ...baseStyles, borderRadius: 16, width: width || 80, height: height || 36 }
      case 'text':
      default:
        return { ...baseStyles, borderRadius: 4, height: height || 14 }
    }
  }

  return (
    <div
      className={`skeleton-base ${animation ? 'skeleton-animated' : ''} ${className}`}
      style={{ ...getVariantStyles(), ...style }}
    />
  )
}

// ==================== 文本骨架屏 ====================

export const SkeletonText: React.FC<SkeletonTextProps> = ({
  lines = 3,
  lastLineWidth = '60%',
  animation = true,
  className = '',
}) => {
  return (
    <div className={`skeleton-text-wrapper ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`skeleton-base skeleton-text ${animation ? 'skeleton-animated' : ''}`}
          style={{
            width: index === lines - 1 ? lastLineWidth : '100%',
            marginBottom: index < lines - 1 ? 8 : 0,
          }}
        />
      ))}
    </div>
  )
}

// ==================== 卡片骨架屏 ====================

export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  showAvatar = true,
  showActions = false,
  contentLines = 2,
  animation = true,
  className = '',
}) => {
  return (
    <div className={`skeleton-card-wrapper ${className}`}>
      {/* 头部区域 */}
      <div className="skeleton-card-header">
        {showAvatar && (
          <Skeleton variant="avatar" animation={animation} />
        )}
        <div className="skeleton-card-header-content">
          <Skeleton variant="text" width="40%" height={16} animation={animation} />
          <Skeleton variant="text" width="60%" height={12} animation={animation} style={{ marginTop: 6 }} />
        </div>
      </div>

      {/* 内容区域 */}
      <div className="skeleton-card-content">
        <SkeletonText lines={contentLines} animation={animation} />
      </div>

      {/* 操作区域 */}
      {showActions && (
        <div className="skeleton-card-actions">
          <Skeleton variant="button" width={60} animation={animation} />
          <Skeleton variant="button" width={60} animation={animation} />
        </div>
      )}
    </div>
  )
}

// ==================== 消息骨架屏 ====================

export const SkeletonMessage: React.FC<{ animation?: boolean; isUser?: boolean }> = ({
  animation = true,
  isUser = false,
}) => {
  return (
    <div className={`skeleton-message-wrapper ${isUser ? 'skeleton-message-user' : ''}`}>
      {!isUser && (
        <Skeleton variant="circular" width={32} height={32} animation={animation} />
      )}
      <div className="skeleton-message-bubble">
        <SkeletonText lines={2} lastLineWidth="40%" animation={animation} />
      </div>
    </div>
  )
}

// ==================== 列表骨架屏 ====================

export const SkeletonList: React.FC<SkeletonListProps> = ({
  count = 3,
  itemVariant = 'card',
  animation = true,
  className = '',
}) => {
  const renderItem = () => {
    switch (itemVariant) {
      case 'message':
        return <SkeletonMessage animation={animation} />
      case 'list-item':
        return (
          <div className="skeleton-list-item">
            <Skeleton variant="avatar" animation={animation} />
            <div className="skeleton-list-item-content">
              <Skeleton variant="text" width="50%" height={14} animation={animation} />
              <Skeleton variant="text" width="80%" height={12} animation={animation} style={{ marginTop: 6 }} />
            </div>
          </div>
        )
      case 'card':
      default:
        return <SkeletonCard animation={animation} />
    }
  }

  return (
    <div className={`skeleton-list-wrapper ${className}`}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton-list-item-wrapper">
          {renderItem()}
        </div>
      ))}
    </div>
  )
}

// ==================== 匹配卡片骨架屏 ====================

export const SkeletonMatchCard: React.FC<{ animation?: boolean }> = ({ animation = true }) => {
  return (
    <div className="skeleton-match-card">
      {/* 头部区域 */}
      <div className="skeleton-match-card-header">
        <div className="skeleton-match-avatar-section">
          <Skeleton variant="avatar" width={80} height={80} animation={animation} />
        </div>
        <div className="skeleton-match-score-section">
          <Skeleton variant="circular" width={52} height={52} animation={animation} />
        </div>
      </div>

      {/* 内容区域 */}
      <div className="skeleton-match-card-body">
        <div className="skeleton-match-user-info">
          <Skeleton variant="text" width="60%" height={18} animation={animation} />
          <Skeleton variant="text" width="40%" height={12} animation={animation} style={{ marginTop: 6 }} />
        </div>
        <SkeletonText lines={2} animation={animation} />
        <div className="skeleton-match-tags">
          <Skeleton variant="rectangular" width={60} height={24} animation={animation} />
          <Skeleton variant="rectangular" width={70} height={24} animation={animation} />
          <Skeleton variant="rectangular" width={55} height={24} animation={animation} />
        </div>
      </div>
    </div>
  )
}

export default Skeleton