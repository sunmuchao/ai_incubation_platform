// SwipeMatchPage - 滑动匹配页面
// Tinder 风式的卡片滑动浏览体验

import React, { useCallback, useMemo } from 'react'
import { Typography, Button, Space, Tag } from 'antd'
import { ArrowLeftOutlined, HeartFilled, StarFilled, CrownOutlined } from '@ant-design/icons'
import SwipeMatchContainer from '../components/SwipeMatchContainer'
import { authStorage } from '../utils/storage'
import './SwipeMatchPage.less'

const { Text, Title } = Typography

interface SwipeMatchPageProps {
  onBack?: () => void
}

const SwipeMatchPage: React.FC<SwipeMatchPageProps> = ({ onBack }) => {
  const handleBack = useCallback(() => {
    onBack?.()
  }, [onBack])

  const userId = useMemo(() => authStorage.getUserId() || 'user-anonymous', [])

  return (
    <div className="swipe-match-page">
      {/* 顶部导航 */}
      <div className="swipe-page-header">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={handleBack}
          className="back-btn"
        >
          返回
        </Button>
        <Title level={5} className="page-title">
          滑动匹配
        </Title>
        {/* 🚀 [改进] Header 只显示简单的次数数字 */}
        <Space size={4}>
          <HeartFilled style={{ fontSize: 14, color: '#C88B8B' }} />
          <Text style={{ fontSize: 12 }}>50</Text>
        </Space>
      </div>

      {/* 滑动说明 */}
      <div className="swipe-instructions">
        <Space split={<Text type="secondary">|</Text>}>
          <Text type="secondary">
            <span className="instruction-icon like">→</span> 右滑喜欢
          </Text>
          <Text type="secondary">
            <span className="instruction-icon pass">←</span> 左滑无感
          </Text>
          <Text type="secondary">
            <span className="instruction-icon super">↑</span> 上滑超级喜欢
          </Text>
        </Space>
      </div>

      {/* 滑动卡片容器 */}
      <div className="swipe-page-content">
        <SwipeMatchContainer />
      </div>

      {/* 🚀 [改进] 底部提示改为：剩余次数 + 引导 */}
      <div className="swipe-page-footer swipe-limit-footer">
        <div className="limit-display">
          <Space size={8}>
            {/* Likes */}
            <div className="limit-item likes">
              <HeartFilled style={{ color: '#C88B8B' }} />
              <Text>今日还可喜欢 <Text strong style={{ color: '#C88B8B' }}>45</Text> 次</Text>
            </div>
            {/* Super Likes */}
            <div className="limit-item super-likes">
              <StarFilled style={{ color: '#FFD700' }} />
              <Text>超级喜欢 <Text strong style={{ color: '#FFD700' }}>5</Text> 次</Text>
            </div>
          </Space>
        </div>
        {/* 会员升级引导 */}
        <Tag
          color="gold"
          style={{ cursor: 'pointer', borderRadius: 12 }}
          onClick={() => {
            window.dispatchEvent(new CustomEvent('trigger-feature', {
              detail: { feature: { action: 'membership' } }
            }))
          }}
        >
          <CrownOutlined style={{ marginRight: 4 }} />
          升级会员无限滑动
        </Tag>
      </div>
    </div>
  )
}

export default SwipeMatchPage