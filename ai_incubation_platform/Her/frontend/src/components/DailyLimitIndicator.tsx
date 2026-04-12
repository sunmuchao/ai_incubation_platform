/**
 * Daily Limit Indicator 组件
 *
 * 显示每日滑动限制：
 * - Likes 剩余数量
 * - Super Likes 剩余数量
 * - 会员无限滑动标识
 */

import React, { useState, useEffect } from 'react'
import { Progress, Space, Typography, Badge, Tooltip, Button } from 'antd'
import {
  HeartOutlined, StarFilled, CrownOutlined, ReloadOutlined
} from '@ant-design/icons'
import { matchingApi } from '../api'
import { herStorage } from '../utils/storage'

const { Text } = Typography

// 主题色
const PRIMARY_COLOR = '#C88B8B'
const GOLD_COLOR = '#FFD700'

interface DailyLimitIndicatorProps {
  userId: string
  compact?: boolean  // 紧凑模式（放在 Header）
  showSuperLike?: boolean  // 是否显示 Super Like
  onRefresh?: () => void
}

interface DailyLimits {
  daily_likes: number
  daily_super_likes: number
  likes_used: number
  super_likes_used: number
  likes_remaining: number
  super_likes_remaining: number
  is_unlimited: boolean
}

/**
 * Daily Limit Indicator 组件
 */
export const DailyLimitIndicator: React.FC<DailyLimitIndicatorProps> = ({
  userId,
  compact = false,
  showSuperLike = true,
  onRefresh
}) => {
  const [limits, setLimits] = useState<DailyLimits | null>(null)
  const [loading, setLoading] = useState(true)

  // 加载限制数据
  useEffect(() => {
    loadLimits()
    // 每 5 分钟刷新一次
    const interval = setInterval(loadLimits, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [userId])

  const loadLimits = async () => {
    try {
      setLoading(true)
      const data = await matchingApi.getDailyLimits(userId)
      setLimits(data)
    } catch (error) {
      // 静默失败
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    loadLimits()
    if (onRefresh) {
      onRefresh()
    }
  }

  // 加载状态
  if (loading && !limits) {
    return (
      <div style={{ padding: compact ? 4 : 8 }}>
        <ReloadOutlined spin style={{ color: '#999' }} />
      </div>
    )
  }

  // 无数据
  if (!limits) {
    return null
  }

  // 会员无限模式
  if (limits.is_unlimited) {
    if (compact) {
      return (
        <Tooltip title="会员无限滑动">
          <Badge count="∞" style={{ backgroundColor: GOLD_COLOR }}>
            <CrownOutlined style={{ fontSize: 16, color: GOLD_COLOR }} />
          </Badge>
        </Tooltip>
      )
    }

    return (
      <div className="daily-limit-unlimited" style={{
        padding: 12,
        borderRadius: 12,
        background: `linear-gradient(135deg, ${GOLD_COLOR}20 0%, ${PRIMARY_COLOR}20 100%)`,
      }}>
        <Space>
          <CrownOutlined style={{ fontSize: 20, color: GOLD_COLOR }} />
          <Text strong style={{ color: GOLD_COLOR }}>会员特权</Text>
          <Text style={{ fontSize: 16, color: GOLD_COLOR }}>∞</Text>
          <Text style={{ color: GOLD_COLOR }}>无限滑动</Text>
        </Space>
      </div>
    )
  }

  // 非会员限制模式
  if (compact) {
    return (
      <Space size="small">
        {/* Likes 剩余 */}
        <Tooltip title={`Likes 剩余 ${limits.likes_remaining}/${limits.daily_likes}`}>
          <Space size={2}>
            <HeartOutlined style={{ fontSize: 14, color: PRIMARY_COLOR }} />
            <Text style={{ fontSize: 12, color: limits.likes_remaining <= 5 ? '#ff4d4f' : PRIMARY_COLOR }}>
              {limits.likes_remaining}
            </Text>
          </Space>
        </Tooltip>

        {/* Super Likes 剩余 */}
        {showSuperLike && (
          <Tooltip title={`Super Likes 剩余 ${limits.super_likes_remaining}/${limits.daily_super_likes}`}>
            <Space size={2}>
              <StarFilled style={{ fontSize: 14, color: GOLD_COLOR }} />
              <Text style={{ fontSize: 12, color: GOLD_COLOR }}>
                {limits.super_likes_remaining}
              </Text>
            </Space>
          </Tooltip>
        )}
      </Space>
    )
  }

  // 完整模式
  return (
    <div className="daily-limit-indicator" style={{
      padding: 16,
      borderRadius: 12,
      background: 'rgba(200, 139, 139, 0.08)',
    }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Likes 进度 */}
        <div>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <HeartOutlined style={{ color: PRIMARY_COLOR }} />
              <Text strong>Likes</Text>
            </Space>
            <Space>
              <Text type="secondary">{limits.likes_remaining} 剩余</Text>
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
              />
            </Space>
          </Space>
          <Progress
            percent={(limits.likes_remaining / limits.daily_likes) * 100}
            strokeColor={limits.likes_remaining <= 5 ? '#ff4d4f' : PRIMARY_COLOR}
            trailColor="rgba(200, 139, 139, 0.2)"
            showInfo={false}
            size="small"
            style={{ marginTop: 8 }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            今日已用 {limits.likes_used}/{limits.daily_likes}
          </Text>
        </div>

        {/* Super Likes 进度 */}
        {showSuperLike && (
          <div>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <StarFilled style={{ color: GOLD_COLOR }} />
                <Text strong>Super Likes</Text>
              </Space>
              <Text type="secondary">{limits.super_likes_remaining} 剩余</Text>
            </Space>
            <Progress
              percent={(limits.super_likes_remaining / limits.daily_super_likes) * 100}
              strokeColor={GOLD_COLOR}
              trailColor="rgba(255, 215, 0, 0.2)"
              showInfo={false}
              size="small"
              style={{ marginTop: 8 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              今日已用 {limits.super_likes_used}/{limits.daily_super_likes}
            </Text>
          </div>
        )}

        {/* 会员引导 */}
        {limits.likes_remaining <= 5 && (
          <div style={{
            padding: 8,
            borderRadius: 8,
            background: `rgba(255, 215, 0, 0.1)`,
            textAlign: 'center'
          }}>
            <Space>
              <CrownOutlined style={{ color: GOLD_COLOR }} />
              <Text style={{ fontSize: 12 }}>
                Likes 即用完？
              </Text>
              <Text
                style={{ fontSize: 12, color: GOLD_COLOR, cursor: 'pointer' }}
                onClick={() => {
                  herStorage.set('show_membership', 'true')
                  window.dispatchEvent(new CustomEvent('trigger-feature', {
                    detail: { feature: { action: 'membership' } }
                  }))
                }}
              >
                升级会员无限滑动
              </Text>
            </Space>
          </div>
        )}
      </Space>
    </div>
  )
}

/**
 * Compact Daily Limit Badge（放在 SwipeMatchPage Header）
 */
export const DailyLimitBadge: React.FC<{ userId: string }> = ({ userId }) => {
  return <DailyLimitIndicator userId={userId} compact showSuperLike />
}

export default DailyLimitIndicator