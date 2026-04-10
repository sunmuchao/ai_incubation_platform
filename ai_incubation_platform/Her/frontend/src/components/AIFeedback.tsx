/**
 * AI 感知反馈组件
 * 显示 AI 正在学习用户偏好的实时反馈
 */

import React, { useEffect, useState } from 'react'
import { Tag, Typography, Progress } from 'antd'
import { HeartOutlined, HeartFilled, ThunderboltOutlined, CloseOutlined } from '@ant-design/icons'
import './AIFeedback.less'

const { Text } = Typography

interface AIFeedbackProps {
  action?: 'like' | 'pass' | 'super_like' | null
  visible: boolean
  onClose?: () => void
}

/**
 * AI 感知反馈提示
 * 当用户执行滑动操作时显示，告知用户 AI 正在学习其偏好
 */
export const AIFeedback: React.FC<AIFeedbackProps> = ({ action, visible, onClose }) => {
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!action || !visible) return

    // 设置反馈消息
    const messages = {
      like: 'AI 记住了你的喜好 ✓',
      pass: '已跳过，继续为你推荐更合适的',
      super_like: 'AI 感受到你的强烈喜欢！⚡',
    }

    setMessage(messages[action] || '')
    setProgress(0)

    // 进度条动画
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setTimeout(() => onClose?.(), 500) // 完成后关闭
          return 100
        }
        return prev + 10
      })
    }, 100)

    return () => clearInterval(interval)
  }, [action, visible, onClose])

  if (!visible || !action) return null

  const getIcon = () => {
    switch (action) {
      case 'like':
        return <HeartOutlined />
      case 'pass':
        return <CloseOutlined />
      case 'super_like':
        return <ThunderboltOutlined />
      default:
        return <HeartFilled />
    }
  }

  const getColor = () => {
    switch (action) {
      case 'like':
        return '#ff4d4f'
      case 'pass':
        return '#999'
      case 'super_like':
        return '#faad14'
      default:
        return '#1890ff'
    }
  }

  return (
    <div className="ai-feedback-container">
      <div className="ai-feedback-toast">
        <div className="ai-feedback-icon" style={{ color: getColor() }}>
          {getIcon()}
        </div>
        <div className="ai-feedback-content">
          <div className="ai-feedback-header">
            <HeartFilled className="ai-icon" style={{ color: '#FF8FAB' }} />
            <Text strong>AI 学习反馈</Text>
          </div>
          <Text className="ai-feedback-message">{message}</Text>
          <Progress
            percent={progress}
            showInfo={false}
            strokeColor={getColor()}
            size="small"
          />
        </div>
      </div>
    </div>
  )
}

/**
 * AI 偏好更新提示
 * 显示 AI 根据用户行为更新的偏好标签
 */
interface AIPreferenceUpdateProps {
  preferences: string[]
  visible: boolean
}

export const AIPreferenceUpdate: React.FC<AIPreferenceUpdateProps> = ({ preferences, visible }) => {
  if (!visible || preferences.length === 0) return null

  return (
    <div className="ai-preference-update">
      <div className="ai-preference-header">
        <HeartFilled className="ai-icon" style={{ color: '#FF8FAB' }} />
        <Text strong>AI 发现你的偏好</Text>
      </div>
      <div className="ai-preference-tags">
        {preferences.map((pref, index) => (
          <Tag key={index} color="#C88B8B" icon={<ThunderboltOutlined />}>
            {pref}
          </Tag>
        ))}
      </div>
    </div>
  )
}

export default AIFeedback
