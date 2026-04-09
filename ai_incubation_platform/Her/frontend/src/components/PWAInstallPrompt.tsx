/**
 * PWA 安装提示组件
 * 引导用户将 App 安装到主屏幕
 */

import React, { useState, useEffect } from 'react'
import { Modal, Button, Space, Typography } from 'antd'
import {
  AppstoreAddOutlined,
  ShareAltOutlined,
  PlusOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import './PWAInstallPrompt.less'

const { Title, Text } = Typography

interface PWAInstallPromptProps {
  onInstall?: () => void
  onDismiss?: () => void
}

const PWAInstallPrompt: React.FC<PWAInstallPromptProps> = ({ onInstall, onDismiss }) => {
  const [visible, setVisible] = useState(false)
  const [isIOS, setIsIOS] = useState(false)
  const [isStandalone, setIsStandalone] = useState(false)

  useEffect(() => {
    // 检测是否为 iOS 设备
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream
    setIsIOS(ios)

    // 检测是否已安装（standalone 模式）
    const standalone = window.matchMedia('(display-mode: standalone)').matches
    setIsStandalone(standalone)

    // 检查是否已Dismiss过
    const dismissed = localStorage.getItem('pwa-install-dismissed')
    const dismissedAt = dismissed ? parseInt(dismissed) : 0
    const daysSinceDismissal = (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24)

    // 已安装或 7 天内手动关闭过则不显示
    if (standalone || daysSinceDismissal < 7) {
      return
    }

    // 延迟 3 秒后显示
    const timer = setTimeout(() => {
      setVisible(true)
    }, 3000)

    return () => clearTimeout(timer)
  }, [])

  const handleInstall = () => {
    setVisible(false)
    onInstall?.()
  }

  const handleDismiss = () => {
    setVisible(false)
    localStorage.setItem('pwa-install-dismissed', Date.now().toString())
    onDismiss?.()
  }

  // 已经是 standalone 模式，不显示
  if (isStandalone) {
    return null
  }

  return (
    <Modal
      open={visible}
      footer={null}
      closable={false}
      className="pwa-install-modal"
      width={320}
    >
      <div className="pwa-install-content">
        <div className="pwa-install-header">
          <AppstoreAddOutlined className="install-icon" />
          <Title level={4} style={{ margin: 0 }}>
            安装 Her App
          </Title>
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={handleDismiss}
            className="close-btn"
          />
        </div>

        <div className="pwa-install-body">
          <Text className="install-description">
            将 Her 安装到您的主屏幕，享受更流畅的体验
          </Text>

          {isIOS ? (
            // iOS 安装指南
            <div className="ios-install-guide">
              <div className="install-step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <Text>点击底部的</Text>
                  <ShareAltOutlined className="share-icon" />
                  <Text>分享按钮</Text>
                </div>
              </div>

              <div className="install-step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <Text>选择「</Text>
                  <Text strong>添加到主屏幕</Text>
                  <Text>」</Text>
                </div>
              </div>

              <div className="install-illustration">
                <div className="illustration-box">
                  <ShareAltOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <Text className="illustration-text">分享</Text>
                </div>
                <div className="arrow">↓</div>
                <div className="illustration-box">
                  <PlusOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                  <Text className="illustration-text">添加到主屏幕</Text>
                </div>
              </div>
            </div>
          ) : (
            // Android/其他平台
            <div className="android-install-guide">
              <Button type="primary" block onClick={handleInstall}>
                立即安装
              </Button>
            </div>
          )}
        </div>

        <div className="pwa-install-footer">
          <Space.Compact block>
            <Button
              size="small"
              onClick={handleInstall}
              type="primary"
              icon={<PlusOutlined />}
            >
              安装
            </Button>
            <Button
              size="small"
              onClick={handleDismiss}
              ghost
            >
              暂时不用
            </Button>
          </Space.Compact>
        </div>
      </div>
    </Modal>
  )
}

export default PWAInstallPrompt