// RoseButton - 玫瑰表达按钮组件
// 参考 Hinge 的玫瑰机制：稀缺表达，优先展示

import React, { useState, useCallback, useMemo } from 'react'
import { Button, Tooltip, Modal, Typography, Input, message, Badge, Spin } from 'antd'
import { HeartFilled, RoseIcon as RoseOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { roseApi } from '../api/roseApi'
import './RoseButton.less'

const { Text, Paragraph } = Typography

// 自定义玫瑰图标（Ant Design 没有 RoseIcon）
const RoseIcon: React.FC<{ style?: React.CSSProperties }> = ({ style }) => (
  <svg viewBox="0 0 24 24" style={style || { width: 16, height: 16 }}>
    <path
      fill="currentColor"
      d="M12 2C9.5 2 7.5 4 7.5 6.5C7.5 7.5 8 8.5 9 9.5C8 10.5 7.5 11.5 7.5 12.5C7.5 15 9.5 17 12 17C14.5 17 16.5 15 16.5 12.5C16.5 11.5 16 10.5 15 9.5C16 8.5 16.5 7.5 16.5 6.5C16.5 4 14.5 2 12 2M12 4C13.5 4 14.5 5 14.5 6.5C14.5 7 14 8 12 9C10 8 9.5 7 9.5 6.5C9.5 5 10.5 4 12 4M12 15C10.5 15 9.5 14 9.5 12.5C9.5 12 10 11 12 10C14 11 14.5 12 14.5 12.5C14.5 14 13.5 15 12 15M12 21L8 17H16L12 21Z"
    />
  </svg>
)

interface RoseButtonProps {
  targetUser: MatchCandidate['user']
  compatibilityScore?: number
  disabled?: boolean
  onRoseSent?: (result: { success: boolean; rosesRemaining: number; isMatch: boolean }) => void
  size?: 'small' | 'default' | 'large'
  showRemaining?: boolean // 是否显示剩余玫瑰数
}

const RoseButton: React.FC<RoseButtonProps> = ({
  targetUser,
  compatibilityScore = 0,
  disabled = false,
  onRoseSent,
  size = 'default',
  showRemaining = true,
}) => {
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [messageText, setMessageText] = useState('')
  const [roseBalance, setRoseBalance] = useState<{
    available_count: number
    monthly_allocation: number
    next_refresh_date: string
  } | null>(null)

  // 加载玫瑰余额
  const loadBalance = useCallback(async () => {
    try {
      const balance = await roseApi.getBalance()
      setRoseBalance(balance)
    } catch (error) {
      console.error('Failed to load rose balance:', error)
    }
  }, [])

  // 组件挂载时加载余额
  React.useEffect(() => {
    loadBalance()
  }, [loadBalance])

  // 是否可以发送玫瑰
  const canSendRose = useMemo(() => {
    if (disabled) return false
    if (!roseBalance) return false
    return roseBalance.available_count > 0
  }, [disabled, roseBalance])

  // 处理发送玫瑰
  const handleSendRose = useCallback(async () => {
    if (!canSendRose) {
      message.warning('没有可用的玫瑰')
      return
    }

    setLoading(true)

    try {
      const result = await roseApi.sendRose({
        target_user_id: targetUser.id,
        message: messageText || undefined,
      })

      if (result.success) {
        // 更新余额
        setRoseBalance((prev) =>
          prev ? { ...prev, available_count: result.roses_remaining } : null
        )

        // 关闭弹窗
        setShowModal(false)
        setMessageText('')

        // 显示成功提示
        if (result.is_match) {
          message.success('匹配成功！你们互送了玫瑰')
        } else {
          message.success('玫瑰已发送，TA 将在 Standout 中看到你')
        }

        // 回调
        onRoseSent?.({
          success: true,
          rosesRemaining: result.roses_remaining,
          isMatch: result.is_match || false,
        })
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error?.message || '发送失败')
    } finally {
      setLoading(false)
    }
  }, [canSendRose, targetUser.id, messageText, onRoseSent])

  // 渲染发送玫瑰弹窗
  const renderSendModal = () => (
    <Modal
      open={showModal}
      onCancel={() => setShowModal(false)}
      title={
        <div className="rose-modal-title">
          <RoseIcon style={{ width: 24, height: 24, color: '#D4A59A' }} />
          <span>发送玫瑰给 {targetUser.name}</span>
        </div>
      }
      footer={[
        <Button key="cancel" onClick={() => setShowModal(false)}>
          取消
        </Button>,
        <Button
          key="send"
          type="primary"
          loading={loading}
          onClick={handleSendRose}
          disabled={!canSendRose}
          className="rose-send-btn"
        >
          发送玫瑰
        </Button>,
      ]}
      className="rose-send-modal"
      width={400}
    >
      <div className="rose-modal-content">
        {/* 用户信息 */}
        <div className="target-user-info">
          <Text strong>{targetUser.name}</Text>
          <Text type="secondary">，{targetUser.age}岁</Text>
          {compatibilityScore > 0 && (
            <Badge
              count={`${Math.round(compatibilityScore * 100)}% 匹配`}
              style={{ backgroundColor: '#D4A59A', marginLeft: 8 }}
            />
          )}
        </div>

        {/* 玫瑰说明 */}
        <Paragraph className="rose-description">
          <RoseIcon style={{ width: 14, height: 14, marginRight: 4 }} />
          玫瑰是一种稀缺的表达方式。发送后，你的资料会出现在 TA 的
          <Text strong> Standout</Text> 列表中，优先被看到。
        </Paragraph>

        {/* 附带消息 */}
        <div className="rose-message-input">
          <Text className="input-label">附带消息（可选）</Text>
          <Input.TextArea
            value={messageText}
            onChange={(e) => setMessageText(e.target.value.slice(0, 100))}
            placeholder="写点什么让 TA 更容易注意到你..."
            maxLength={100}
            showCount
            rows={3}
          />
        </div>

        {/* 余额提示 */}
        {roseBalance && (
          <div className="rose-balance-tip">
            <Text type="secondary">
              本月剩余 {roseBalance.available_count} 个玫瑰
              {roseBalance.available_count === 0 && (
                <Button type="link" size="small" onClick={() => message.info('购买功能即将开放')}>
                  购买更多
                </Button>
              )}
            </Text>
          </div>
        )}
      </div>
    </Modal>
  )

  // 渲染玫瑰按钮
  return (
    <>
      <Tooltip
        title={
          canSendRose
            ? `发送玫瑰（剩余 ${roseBalance?.available_count || 0} 个）`
            : roseBalance?.available_count === 0
              ? '本月玫瑰已用完，请等待下月刷新或购买'
              : '发送玫瑰表达特别的喜欢'
        }
      >
        <Button
          className={`rose-button ${canSendRose ? 'has-rose' : 'no-rose'}`}
          icon={<RoseIcon style={{ width: size === 'large' ? 20 : 16, height: size === 'large' ? 20 : 16 }} />}
          size={size}
          disabled={!canSendRose || disabled}
          onClick={() => setShowModal(true)}
          loading={loading}
        >
          {showRemaining && roseBalance && (
            <span className="rose-count">{roseBalance.available_count}</span>
          )}
        </Button>
      </Tooltip>

      {/* 发送弹窗 */}
      {renderSendModal()}
    </>
  )
}

export default RoseButton