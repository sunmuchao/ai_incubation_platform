// VerificationBadge - 认证徽章组件
// 参考 Tinder Blue Star 认证徽章

import React, { useMemo } from 'react'
import { Tag, Tooltip, Badge as AntBadge } from 'antd'
import {
  CheckCircleOutlined,
  StarFilled,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import './VerificationBadge.less'

// 徽章类型配置
const BADGE_CONFIG = {
  blue_star: {
    icon: '⭐',
    color: '#1890ff',
    name: '蓝星认证',
    description: '已完成人脸认证',
  },
  gold_star: {
    icon: '🌟',
    color: '#faad14',
    name: '金星认证',
    description: '身份证+人脸双重认证',
  },
  platinum_star: {
    icon: '✨',
    color: '#95de64',
    name: '铂金星认证',
    description: '实名+人脸+学历认证',
  },
  diamond_star: {
    icon: '💎',
    color: '#D4A59A',
    name: '钻石星认证',
    description: '全方位身份认证',
  },
}

interface VerificationBadgeProps {
  badgeType?: string // blue_star, gold_star, platinum_star, diamond_star
  verified?: boolean // 简化的认证状态
  size?: 'small' | 'default' | 'large'
  showTooltip?: boolean // 是否显示详情提示
  showText?: boolean // 是否显示文字
  className?: string
}

const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  badgeType,
  verified,
  size = 'default',
  showTooltip = true,
  showText = false,
  className,
}) => {
  // 获取徽章配置
  const config = useMemo(() => {
    if (badgeType && BADGE_CONFIG[badgeType]) {
      return BADGE_CONFIG[badgeType]
    }
    // 默认蓝星认证
    if (verified) {
      return BADGE_CONFIG.blue_star
    }
    return null
  }, [badgeType, verified])

  // 未认证
  if (!config) {
    return null
  }

  // 尺寸样式映射
  const sizeStyles = useMemo(() => {
    switch (size) {
      case 'small':
        return {
          fontSize: 12,
          padding: '2px 6px',
        }
      case 'large':
        return {
          fontSize: 16,
          padding: '4px 10px',
        }
      default:
        return {
          fontSize: 14,
          padding: '3px 8px',
        }
    }
  }, [size])

  // 渲染徽章内容
  const renderBadgeContent = () => (
    <Tag
      className={`verification-badge ${className || ''}`}
      style={{
        backgroundColor: `${config.color}15`,
        borderColor: `${config.color}40`,
        color: config.color,
        fontSize: sizeStyles.fontSize,
        padding: sizeStyles.padding,
        borderRadius: size === 'small' ? 4 : 8,
      }}
    >
      <span className="badge-icon">{config.icon}</span>
      {showText && <span className="badge-text">{config.name}</span>}
    </Tag>
  )

  // 带提示的徽章
  if (showTooltip) {
    return (
      <Tooltip
        title={
          <div className="badge-tooltip">
            <div className="tooltip-header">
              <span className="tooltip-icon">{config.icon}</span>
              <span className="tooltip-name">{config.name}</span>
            </div>
            <div className="tooltip-desc">{config.description}</div>
          </div>
        }
        placement="top"
      >
        {renderBadgeContent()}
      </Tooltip>
    )
  }

  return renderBadgeContent()
}

// 简化版认证标记（仅显示图标）
export const VerifiedMark: React.FC<{
  verified?: boolean
  badgeType?: string
  size?: number
}> = ({ verified, badgeType, size = 14 }) => {
  if (!verified && !badgeType) return null

  const config = badgeType ? BADGE_CONFIG[badgeType] : BADGE_CONFIG.blue_star

  return (
    <AntBadge
      count={
        <span
          className="verified-mark"
          style={{
            fontSize: size,
            color: config.color,
          }}
        >
          {config.icon}
        </span>
      }
      offset={[-5, 5]}
    >
      <span />
    </AntBadge>
  )
}

// 认证状态图标（用于头像角落）
export const VerifiedIcon: React.FC<{
  verified?: boolean
  badgeType?: string
}> = ({ verified, badgeType }) => {
  if (!verified && !badgeType) return null

  const config = badgeType ? BADGE_CONFIG[badgeType] : BADGE_CONFIG.blue_star

  return (
    <div className="verified-icon-wrapper">
      <span className="verified-icon" style={{ color: config.color }}>
        {config.icon}
      </span>
    </div>
  )
}

export default VerificationBadge