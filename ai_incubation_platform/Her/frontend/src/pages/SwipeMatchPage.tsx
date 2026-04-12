// SwipeMatchPage - 滑动匹配页面
// Tinder 风式的卡片滑动浏览体验

import React, { useCallback, useMemo } from 'react'
import { Typography, Button, Space } from 'antd'
import { ArrowLeftOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import SwipeMatchContainer from '../components/SwipeMatchContainer'
import { DailyLimitBadge } from '../components/DailyLimitIndicator'
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
        {/* 每日限制显示 */}
        <DailyLimitBadge userId={userId} />
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

      {/* 底部提示 */}
      <div className="swipe-page-footer">
        <Text type="secondary" className="footer-tip">
          滑动开始匹配，发现有趣的灵魂 ✨
        </Text>
      </div>
    </div>
  )
}

export default SwipeMatchPage