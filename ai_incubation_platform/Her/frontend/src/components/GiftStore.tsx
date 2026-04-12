// GiftStore - 虚拟礼物商店组件
// 参考 Soul/探探的礼物打赏系统

import React, { useState, useCallback, useMemo, useEffect } from 'react'
import { Modal, Tabs, Card, Avatar, Typography, Button, Input, Space, Tag, Badge, message, Spin, Empty } from 'antd'
import {
  HeartFilled,
  GiftOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  UserOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons'
import type { User } from '../types'
import { giftApi } from '../api/giftApi'
import './GiftStore.less'

const { Text, Paragraph, Title } = Typography

interface Gift {
  id: string
  name: string
  type: string
  category: string
  price: number
  icon: string
  animation?: string
  description: string
  fullscreen: boolean
  is_popular: boolean
  is_new: boolean
}

interface GiftStoreProps {
  targetUser: User
  visible: boolean
  onClose: () => void
  onGiftSent?: (result: { success: boolean; giftName: string; totalPrice: number }) => void
}

const GiftStore: React.FC<GiftStoreProps> = ({
  targetUser,
  visible,
  onClose,
  onGiftSent,
}) => {
  const [loading, setLoading] = useState(true)
  const [gifts, setGifts] = useState<Gift[]>([])
  const [popularGifts, setPopularGifts] = useState<Gift[]>([])
  const [newGifts, setNewGifts] = useState<Gift[]>([])
  const [selectedGift, setSelectedGift] = useState<Gift | null>(null)
  const [giftCount, setGiftCount] = useState(1)
  const [messageText, setMessageText] = useState('')
  const [sending, setSending] = useState(false)
  const [activeCategory, setActiveCategory] = useState('all')

  // 加载礼物商店数据
  useEffect(() => {
    if (visible) {
      loadGiftStore()
    }
  }, [visible])

  const loadGiftStore = useCallback(async () => {
    setLoading(true)
    try {
      const store = await giftApi.getGiftStore()
      setGifts(store.gifts)
      setPopularGifts(store.popular_gifts)
      setNewGifts(store.new_gifts)
    } catch (error) {
      console.error('Failed to load gift store:', error)
      message.error('加载礼物商店失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // 分类过滤礼物
  const filteredGifts = useMemo(() => {
    if (activeCategory === 'all') {
      return gifts
    }
    if (activeCategory === 'popular') {
      return popularGifts
    }
    if (activeCategory === 'new') {
      return newGifts
    }
    if (activeCategory === 'free') {
      return gifts.filter((g) => g.price === 0)
    }
    return gifts.filter((g) => g.category === activeCategory)
  }, [gifts, popularGifts, newGifts, activeCategory])

  // 计算总价
  const totalPrice = useMemo(() => {
    if (!selectedGift) return 0
    return selectedGift.price * giftCount
  }, [selectedGift, giftCount])

  // 发送礼物
  const handleSendGift = useCallback(async () => {
    if (!selectedGift) {
      message.warning('请选择一个礼物')
      return
    }

    setSending(true)

    try {
      const result = await giftApi.sendGift({
        target_user_id: targetUser.id,
        gift_id: selectedGift.id,
        count: giftCount,
        message: messageText || undefined,
      })

      if (result.success) {
        message.success(`已发送 ${selectedGift.icon} ${selectedGift.name}`)
        setSelectedGift(null)
        setMessageText('')
        setGiftCount(1)
        onClose()

        onGiftSent?.({
          success: true,
          giftName: selectedGift.name,
          totalPrice: result.total_price,
        })
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error?.message || '发送失败')
    } finally {
      setSending(false)
    }
  }, [selectedGift, targetUser.id, giftCount, messageText, onClose, onGiftSent])

  // 渲染礼物卡片
  const renderGiftCard = (gift: Gift) => (
    <Card
      key={gift.id}
      className={`gift-card ${selectedGift?.id === gift.id ? 'selected' : ''} ${gift.price === 0 ? 'free' : ''}`}
      onClick={() => setSelectedGift(gift)}
      hoverable
    >
      <div className="gift-icon-wrapper">
        <Text className="gift-icon">{gift.icon}</Text>
        {gift.is_popular && <Badge count="热门" className="popular-badge" />}
        {gift.is_new && <Badge count="新品" className="new-badge" />}
      </div>
      <Text className="gift-name">{gift.name}</Text>
      <Text className="gift-price">
        {gift.price === 0 ? '免费' : `¥${gift.price}`}
      </Text>
    </Card>
  )

  // 渲染分类标签
  const renderCategoryTabs = () => (
    <Tabs
      activeKey={activeCategory}
      onChange={(key) => setActiveCategory(key)}
      className="gift-category-tabs"
      items={[
        { key: 'all', label: '全部' },
        { key: 'popular', label: '热门' },
        { key: 'new', label: '新品' },
        { key: 'free', label: '免费' },
        { key: 'love', label: '❤️ 爱情' },
        { key: 'food', label: '☕ 餐饮' },
        { key: 'festival', label: '🎆 节日' },
      ]}
    />
  )

  // 渲染发送确认区域
  const renderSendSection = () => (
    <div className="gift-send-section">
      {/* 目标用户信息 */}
      <div className="target-user-info">
        <Avatar src={targetUser.avatar || targetUser.avatar_url} icon={<UserOutlined />} />
        <Text className="user-name">{targetUser.name}</Text>
      </div>

      {/* 选中的礼物 */}
      {selectedGift && (
        <div className="selected-gift-preview">
          <Text className="preview-icon">{selectedGift.icon}</Text>
          <div className="preview-info">
            <Text className="preview-name">{selectedGift.name}</Text>
            <Text className="preview-desc">{selectedGift.description}</Text>
          </div>
          <div className="gift-count-control">
            <Button
              size="small"
              onClick={() => setGiftCount((c) => Math.max(1, c - 1))}
              disabled={giftCount <= 1}
            >
              -
            </Button>
            <Text className="count-display">{giftCount}</Text>
            <Button
              size="small"
              onClick={() => setGiftCount((c) => c + 1)}
            >
              +
            </Button>
          </div>
        </div>
      )}

      {/* 附带消息 */}
      <Input.TextArea
        value={messageText}
        onChange={(e) => setMessageText(e.target.value.slice(0, 50))}
        placeholder="写点什么让 TA 更开心..."
        maxLength={50}
        showCount
        rows={2}
        className="gift-message-input"
      />

      {/* 总价和发送按钮 */}
      <div className="gift-action-bar">
        <Text className="total-price">
          总计：{totalPrice === 0 ? '免费' : `¥${totalPrice.toFixed(2)}`}
        </Text>
        <Button
          type="primary"
          size="large"
          icon={<GiftOutlined />}
          loading={sending}
          disabled={!selectedGift}
          onClick={handleSendGift}
          className="send-gift-btn"
        >
          发送礼物
        </Button>
      </div>
    </div>
  )

  return (
    <Modal
      open={visible}
      onCancel={onClose}
      title={
        <div className="gift-modal-title">
          <GiftOutlined style={{ color: '#D4A59A' }} />
          <span>礼物商店</span>
        </div>
      }
      footer={null}
      width={600}
      className="gift-store-modal"
      centered
    >
      {loading ? (
        <div className="loading-container">
          <Spin size="large" tip="加载礼物商店..." />
        </div>
      ) : (
        <div className="gift-store-content">
          {/* 分类标签 */}
          {renderCategoryTabs()}

          {/* 礼物列表 */}
          <div className="gift-grid">
            {filteredGifts.length === 0 ? (
              <Empty description="暂无礼物" />
            ) : (
              filteredGifts.map(renderGiftCard)
            )}
          </div>

          {/* 发送确认区域 */}
          {renderSendSection()}
        </div>
      )}
    </Modal>
  )
}

export default GiftStore