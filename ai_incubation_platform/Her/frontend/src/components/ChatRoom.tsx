/**
 * 聊天室组件 - 真实的两人聊天界面
 *
 * 功能:
 * - 发送/接收消息
 * - 消息历史记录
 * - 已读/未读状态
 */

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Input, Button, Avatar, Typography, Space, Empty, Tooltip, message, Tag, Modal, Dropdown, Badge } from 'antd'
import { SendOutlined, LeftOutlined, PictureOutlined, SmileOutlined, MoreOutlined, EyeInvisibleOutlined, EyeOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { chatApi, yourTurnApi } from '../api'
import { websocketService } from '../services/websocket'
import { authStorage, herStorage } from '../utils/storage'
import { isIOS, optimizeIOSScroll, optimizeIOSInput } from '../utils/iosUtils'
import type { MenuProps } from 'antd'
import './ChatRoom.less'

const { Text } = Typography

interface Message {
  id: string
  sender_id: string
  receiver_id: string
  message_type: 'text' | 'image' | 'emoji' | 'voice' | 'system'
  content: string
  is_read: boolean
  created_at: string
  status?: 'sent' | 'delivered' | 'read' | 'failed'
}

interface ChatRoomProps {
  match?: MatchCandidate | null
  partnerId?: string
  partnerName?: string
  partnerAvatar?: string
  onBack?: () => void
  herSleeping?: boolean // Her 是否处于休眠状态
  onHerSleepChange?: (sleeping: boolean) => void // 休眠状态变更回调
}

const ChatRoom: React.FC<ChatRoomProps> = ({
  match,
  partnerId,
  partnerName,
  partnerAvatar,
  onBack,
  herSleeping = false,
  onHerSleepChange,
}) => {
  // 从 match 对象获取对方信息
  const actualPartnerId = partnerId || match?.user?.id
  const actualPartnerName = partnerName || match?.user?.name || 'TA'
  const actualPartnerAvatar = partnerAvatar || match?.user?.avatar || match?.user?.avatar_url

  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isYourTurn, setIsYourTurn] = useState(false) // Your Turn 提醒状态
  const [yourTurnReminder, setYourTurnReminder] = useState<any>(null) // 提醒详情

  // Her 休眠状态（本地状态，同步到父组件）
  const [herSleepingLocal, setHerSleepingLocal] = useState(herSleeping)

  // 图片和表情功能状态
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [showImageUpload, setShowImageUpload] = useState(false)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploadingImage, setIsUploadingImage] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // iOS 特定优化
  useEffect(() => {
    if (isIOS()) {
      // 优化消息列表滚动
      if (messagesContainerRef.current) {
        optimizeIOSScroll(messagesContainerRef.current)
      }

      // 优化输入框
      if (inputRef.current && inputRef.current.input) {
        optimizeIOSInput(inputRef.current.input)
      }
    }
  }, [])

  // 获取当前用户 ID - 必须在其他 useCallback 之前定义
  const currentUserId = useMemo(() => {
    const user = authStorage.getUser()
    return user?.id || user?.username || 'user-anonymous-dev'
  }, [])

  // 常用表情列表
  const EMOJI_LIST = [
    '😀', '😃', '😄', '😁', '😊', '☺️', '😇', '🙂', '🙃', '😉',
    '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😜',
    '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐',
    '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪',
    '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶',
    '🥴', '😵', '🤯', '🤠', '🥳', '😎', '🤓', '🧐', '😕', '😟',
    '🙁', '☹️', '😮', '😯', '😲', '😳', '🥺', '😦', '😧', '😨',
    '😰', '😥', '😢', '😭', '😱', '😖', '😣', '😞', '😓', '😩',
    '👍', '👎', '👏', '🙌', '🤝', '🙏', '💪', '❤️', '💔', '💕',
    '💖', '💗', '💙', '💚', '💛', '🧡', '💜', '🖤', '💯', '💢'
  ]

  // 图片上传处理
  const handleImageClick = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }, [])

  const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // 验证文件类型
      if (!file.type.startsWith('image/')) {
        message.error('请选择图片文件')
        return
      }
      // 验证文件大小 (最大 5MB)
      if (file.size > 5 * 1024 * 1024) {
        message.error('图片大小不能超过 5MB')
        return
      }
      setSelectedFile(file)
      // 预览图片
      const reader = new FileReader()
      reader.onload = (event) => {
        setImagePreview(event.target?.result as string)
        setShowImageUpload(true)
      }
      reader.readAsDataURL(file)
    }
    // 清空 input，允许重复选择同一文件
    e.target.value = ''
  }, [])

  const handleImageSend = useCallback(async () => {
    if (!selectedFile || !actualPartnerId || isUploadingImage) return

    setIsUploadingImage(true)
    setShowImageUpload(false)
    setImagePreview(null)

    try {
      // 1. 先上传图片到照片服务
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('photo_type', 'chat')

      const token = authStorage.getToken()
      const uploadResponse = await fetch('/api/photos/upload-file', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      })

      if (!uploadResponse.ok) {
        // 如果后端不支持文件上传，使用本地预览作为临时方案
        const tempImageUrl = imagePreview || ''
        await chatApi.sendMessage({
          receiver_id: actualPartnerId,
          content: tempImageUrl,
          message_type: 'image'
        })
        message.warning('图片已发送（临时预览模式）')
        setSelectedFile(null)
        setIsUploadingImage(false)
        return
      }

      const uploadResult = await uploadResponse.json()
      const imageUrl = uploadResult.photo_url || uploadResult.url

      // 2. 发送图片消息
      const result = await chatApi.sendMessage({
        receiver_id: actualPartnerId,
        content: imageUrl,
        message_type: 'image'
      })

      // 添加到消息列表
      const imageMessage: Message = {
        id: result.id || `img-${Date.now()}`,
        sender_id: currentUserId,
        receiver_id: actualPartnerId,
        message_type: 'image',
        content: imageUrl,
        is_read: true,
        created_at: new Date().toISOString(),
        status: 'sent'
      }
      setMessages(prev => [...prev, imageMessage])

      message.success('图片已发送')
    } catch (error) {
      console.error('图片上传失败:', error)
      message.error('图片上传失败，请稍后重试')
    } finally {
      setSelectedFile(null)
      setIsUploadingImage(false)
    }
  }, [selectedFile, actualPartnerId, isUploadingImage, imagePreview, currentUserId])

  // 表情选择处理
  const handleEmojiClick = useCallback(() => {
    setShowEmojiPicker(prev => !prev)
  }, [])

  const handleEmojiSelect = useCallback(async (emoji: string) => {
    setShowEmojiPicker(false)

    if (!actualPartnerId) return

    try {
      // 发送表情消息
      const result = await chatApi.sendMessage({
        receiver_id: actualPartnerId,
        content: emoji,
        message_type: 'emoji'
      })

      // 添加到消息列表
      const emojiMessage: Message = {
        id: result.id || `emoji-${Date.now()}`,
        sender_id: currentUserId,
        receiver_id: actualPartnerId,
        message_type: 'emoji',
        content: emoji,
        is_read: true,
        created_at: new Date().toISOString(),
        status: 'sent'
      }
      setMessages(prev => [...prev, emojiMessage])
    } catch (error) {
      console.error('表情发送失败:', error)
      message.error('表情发送失败')
    }
  }, [actualPartnerId, currentUserId])

  // 使用 ref 追踪当前聊天对象（确保消息处理器使用最新值）
  const actualPartnerIdRef = useRef(actualPartnerId)
  actualPartnerIdRef.current = actualPartnerId

  // WebSocket 连接状态追踪（避免 Strict Mode 重复连接）
  const wsConnectedRef = useRef(false)

  // 连接 WebSocket 接收实时消息
  useEffect(() => {
    if (!currentUserId) {
      console.log('[ChatRoom] Skip WebSocket connection - no currentUserId')
      return
    }

    // 避免重复连接（React Strict Mode 会导致 useEffect 执行两次）
    if (wsConnectedRef.current) {
      console.log('[ChatRoom] WebSocket already connected, skip re-connection')
      return
    }

    console.log('[ChatRoom] === useEffect Start ===')
    console.log('[ChatRoom] currentUserId:', currentUserId)
    console.log('[ChatRoom] actualPartnerId:', actualPartnerIdRef.current)

    // 标记已连接
    wsConnectedRef.current = true

    // 连接 WebSocket - 使用路径参数方式，与后端 /api/chat/ws/{user_id} 匹配
    websocketService.connect(currentUserId)

    console.log('[ChatRoom] WebSocket connection initiated')

    // 订阅新消息（使用 ref 确保获取最新的 partnerId）
    const unsubscribe = websocketService.onMessage((message) => {
      const currentPartnerId = actualPartnerIdRef.current
      console.log('[ChatRoom] === onMessage Callback ===')
      console.log('[ChatRoom] message.type:', message.type)
      console.log('[ChatRoom] message.payload:', message.payload)
      console.log('[ChatRoom] currentPartnerId (from ref):', currentPartnerId)

      if (message.type === 'new_message' && message.payload) {
        const payload = message.payload as any
        console.log('[ChatRoom] payload.sender_id:', payload.sender_id)
        console.log('[ChatRoom] sender matches partner:', payload.sender_id === currentPartnerId)

        // 只添加来自当前聊天对象的消息
        if (payload.sender_id === currentPartnerId) {
          console.log('[ChatRoom] Adding message to state')
          setMessages(prev => {
            // 避免重复添加
            const exists = prev.some(m => m.id === payload.id)
            console.log('[ChatRoom] Message exists:', exists)
            if (exists) return prev
            // 转换后端消息格式为前端 Message 类型
            const newMessage: Message = {
              id: payload.id || `ws-${Date.now()}`,
              sender_id: payload.sender_id,
              receiver_id: payload.receiver_id || currentPartnerId,
              message_type: payload.message_type || 'text',
              content: payload.content,
              is_read: payload.is_read || false,
              created_at: payload.created_at || payload.timestamp || new Date().toISOString(),
              status: 'delivered'
            }
            console.log('[ChatRoom] New message created:', newMessage.id)
            return [...prev, newMessage]
          })
        } else {
          console.log('[ChatRoom] Skipping message - sender_id does not match currentPartnerId')
        }
      }
    })

    console.log('[ChatRoom] Message subscription registered')

    return () => {
      // 仅在组件真正卸载时断开连接（不清理订阅，让 WebSocket 服务保持连接）
      console.log('[ChatRoom] Cleanup - keeping WebSocket connection alive')
      // 注意：不调用 unsubscribe() 和 disconnect()，避免 Strict Mode 问题
      // WebSocket 服务是单例，会保持连接直到用户离开页面
    }
  }, [currentUserId]) // 只依赖 currentUserId，不依赖 actualPartnerId（避免切换聊天对象时重连）

  // 滚动到底部 - 优化性能
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }

  // 使用防抖的滚动策略
  const scrollToBottomDebounced = useMemo(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(() => {
        scrollToBottom()
        timeoutId = null
      }, 50)
    }
  }, [])

  useEffect(() => {
    scrollToBottomDebounced()
  }, [messages])

  // 加载历史消息
  useEffect(() => {
    if (actualPartnerId) {
      loadHistoryMessages()
    }
  }, [actualPartnerId])

  const loadHistoryMessages = async () => {
    if (!actualPartnerId) return

    try {
      // 使用新的 REST API 加载消息历史
      const history = await chatApi.getHistory(actualPartnerId)

      if (Array.isArray(history)) {
        setMessages(history.map((msg) => ({
          id: msg.id,
          sender_id: msg.sender_id,
          receiver_id: msg.receiver_id,
          message_type: msg.message_type || 'text',
          content: msg.content,
          is_read: msg.is_read,
          created_at: msg.created_at,
          status: msg.status
        })))
      }

      // 检查 Your Turn 提醒
      if (currentUserId) {
        try {
          const conversationId = `${currentUserId}-${actualPartnerId}`
          const yourTurnResult = await yourTurnApi.shouldShowReminder(currentUserId, conversationId)
          if (yourTurnResult.should_show) {
            setIsYourTurn(true)
            setYourTurnReminder(yourTurnResult.reminder)
            // 标记提醒已显示
            await yourTurnApi.markReminderShown(currentUserId, conversationId)
          }
        } catch (error) {
          // 静默失败
        }
      }
    } catch (error) {
      // 加载失败时也继续，可以发送新消息
    }
  }

  // 发送消息 - 使用 REST API
  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isLoading || !actualPartnerId) {
      return
    }

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      sender_id: currentUserId,
      receiver_id: actualPartnerId,
      message_type: 'text',
      content: inputValue,
      is_read: true,
      created_at: new Date().toISOString(),
      status: 'sent'
    }

    // 立即显示消息 (乐观更新)
    setMessages(prev => [...prev, userMessage])
    const messageContent = inputValue
    setInputValue('')
    setIsLoading(true)

    try {
      // 使用 REST API 发送消息
      const result = await chatApi.sendMessage({
        receiver_id: actualPartnerId,
        content: messageContent,
        message_type: 'text'
      })

      // 更新为实际的消息 ID
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id
          ? { ...msg, id: result.id || msg.id, status: 'delivered' }
          : msg
      ))

      // 清除 Your Turn 提醒状态（用户已回复）
      setIsYourTurn(false)
      setYourTurnReminder(null)

      // 后端会在开发环境自动触发模拟 Agent 回复
      // 通过 WebSocket 推送回复，无需轮询

    } catch (error) {
      // 标记发送失败
      setMessages(prev => prev.map(msg =>
        msg.id === userMessage.id ? { ...msg, status: 'failed' } : msg
      ))
      message.error('发送失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }, [inputValue, isLoading, actualPartnerId, currentUserId])

  // 模拟对方回复 (开发环境)
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 处理输入状态
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  // 按日期分组消息 - 使用 useMemo 缓存分组结果
  const groupedMessages = useMemo(() => {
    const grouped: { [key: string]: Message[] } = {}

    messages.forEach(msg => {
      const date = new Date(msg.created_at).toLocaleDateString('zh-CN', {
        month: 'long',
        day: 'numeric'
      })

      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(msg)
    })

    return grouped
  }, [messages])

  // 使用 useCallback 缓存渲染函数
  const renderDateSeparator = useCallback((date: string) => {
    return (
      <div key={`sep-${date}`} className="date-separator">
        <Text type="secondary">{date}</Text>
      </div>
    )
  }, [])

  const renderMessageBubble = useCallback((message: Message) => {
    const isMe = message.sender_id === currentUserId
    const timestamp = new Date(message.created_at).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })

    // 图片消息渲染
    if (message.message_type === 'image') {
      return (
        <div key={message.id} className={`message-item ${isMe ? 'message-me' : 'message-other'}`}>
          {!isMe && (
            <Avatar
              src={actualPartnerAvatar}
              size={36}
              className="message-avatar"
            />
          )}

          <div className="message-content-wrapper">
            <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-other'} message-image`}>
              <img src={message.content} alt="图片消息" style={{ maxWidth: '200px', borderRadius: '8px' }} />
            </div>

            <div className="message-meta">
              <Text className="message-time">{timestamp}</Text>
            </div>
          </div>

          {isMe && (
            <Avatar
              size={36}
              className="message-avatar"
              style={{ backgroundColor: '#1890ff' }}
            >
              我
            </Avatar>
          )}
        </div>
      )
    }

    // 表情消息渲染（单独表情放大显示）
    if (message.message_type === 'emoji') {
      return (
        <div key={message.id} className={`message-item ${isMe ? 'message-me' : 'message-other'}`}>
          {!isMe && (
            <Avatar
              src={actualPartnerAvatar}
              size={36}
              className="message-avatar"
            />
          )}

          <div className="message-content-wrapper">
            <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-other'} emoji-bubble`}>
              <Text className="emoji-text" style={{ fontSize: '32px' }}>{message.content}</Text>
            </div>

            <div className="message-meta">
              <Text className="message-time">{timestamp}</Text>
            </div>
          </div>

          {isMe && (
            <Avatar
              size={36}
              className="message-avatar"
              style={{ backgroundColor: '#1890ff' }}
            >
              我
            </Avatar>
          )}
        </div>
      )
    }

    // 文本消息渲染
    return (
      <div key={message.id} className={`message-item ${isMe ? 'message-me' : 'message-other'}`}>
        {!isMe && (
          <Avatar
            src={actualPartnerAvatar}
            size={36}
            className="message-avatar"
          />
        )}

        <div className="message-content-wrapper">
          <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-other'}`}>
            <Text className="message-text">{message.content}</Text>
          </div>

          <div className="message-meta">
            <Text className="message-time">{timestamp}</Text>
            {isMe && (
              <Text className={`message-status ${message.status}`}>
                {message.status === 'read' && '已读'}
                {message.status === 'delivered' && '已送达'}
                {message.status === 'sent' && '已发送'}
                {message.status === 'failed' && '发送失败'}
              </Text>
            )}
          </div>
        </div>

        {isMe && (
          <Avatar
            size={36}
            className="message-avatar"
            style={{ backgroundColor: '#1890ff' }}
          >
            我
          </Avatar>
        )}
      </div>
    )
  }, [currentUserId, actualPartnerAvatar])

  return (
    <div className="chat-room">
      {/* 顶部导航栏 */}
      <div className="chat-room-header">
        <div className="header-left">
          {onBack && (
            <Button
              type="text"
              icon={<LeftOutlined />}
              onClick={onBack}
              className="back-button"
            />
          )}
          <Avatar src={actualPartnerAvatar} size={40} className="partner-avatar" />
          <div className="partner-info">
            <Text strong className="partner-name">{actualPartnerName}</Text>
            {/* Your Turn 提醒 */}
            {isYourTurn && (
              <Badge
                count="Your Turn"
                style={{
                  backgroundColor: '#C88B8B',
                  fontSize: 10,
                  height: 18,
                  lineHeight: '18px',
                  marginLeft: 8,
                }}
              />
            )}
          </div>
        </div>

        <div className="header-right">
          {/* 更多菜单 - 包含休眠/唤醒 Her 选项 */}
          <Dropdown
            menu={{
              items: [
                {
                  key: 'her-sleep',
                  label: herSleepingLocal ? '唤醒 Her' : '让 Her 休眠',
                  icon: herSleepingLocal ? <EyeOutlined /> : <EyeInvisibleOutlined />,
                  onClick: () => {
                    const newSleeping = !herSleepingLocal
                    setHerSleepingLocal(newSleeping)
                    herStorage.setSleepingInChat(newSleeping)
                    onHerSleepChange?.(newSleeping)
                    message.info(newSleeping ? 'Her 已休眠，专注你们的聊天吧' : 'Her 已唤醒')
                  },
                },
              ],
            }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Tooltip title="更多">
              <Button type="text" icon={<MoreOutlined />} />
            </Tooltip>
          </Dropdown>
        </div>
      </div>

      {/* Her 休眠提示条 */}
      {herSleepingLocal && (
        <div className="her-sleeping-bar">
          <Text type="secondary" style={{ fontSize: 12 }}>
            Her 已休眠
          </Text>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setHerSleepingLocal(false)
              herStorage.setSleepingInChat(false)
              onHerSleepChange?.(false)
            }}
            style={{ fontSize: 12, padding: '0 4px' }}
          >
            唤醒
          </Button>
        </div>
      )}

      {/* 消息列表 */}
      <div className="chat-room-messages" ref={messagesContainerRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <Text type="secondary">
                  还没有消息，发送第一条消息开始聊天吧~
                </Text>
              }
            />
          </div>
        ) : (
          Object.entries(groupedMessages).map(([date, dateMessages]) => (
            <React.Fragment key={date}>
              {renderDateSeparator(date)}
              {dateMessages.map(renderMessageBubble)}
            </React.Fragment>
          ))
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-room-input-area">
        {/* 表情选择面板 */}
        {showEmojiPicker && (
          <div className="emoji-picker-panel">
            <div className="emoji-picker-header">
              <Text strong>选择表情</Text>
              <Button type="text" size="small" onClick={() => setShowEmojiPicker(false)}>
                收起
              </Button>
            </div>
            <div className="emoji-grid">
              {EMOJI_LIST.map((emoji, index) => (
                <Button
                  key={index}
                  type="text"
                  className="emoji-item"
                  onClick={() => handleEmojiSelect(emoji)}
                >
                  {emoji}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* 图片上传预览弹窗 */}
        <Modal
          title="发送图片"
          open={showImageUpload}
          onCancel={() => {
            setShowImageUpload(false)
            setImagePreview(null)
            setSelectedFile(null)
          }}
          footer={[
            <Button key="cancel" onClick={() => {
              setShowImageUpload(false)
              setImagePreview(null)
              setSelectedFile(null)
            }}>
              取消
            </Button>,
            <Button key="send" type="primary" loading={isUploadingImage} onClick={handleImageSend}>
              发送
            </Button>,
          ]}
        >
          {imagePreview && (
            <div style={{ textAlign: 'center' }}>
              <img src={imagePreview} alt="预览" style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: '8px' }} />
            </div>
          )}
        </Modal>

        {/* 隐藏的文件选择 input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleImageSelect}
        />

        <div className="input-tools">
          <Space>
            <Tooltip title="图片">
              <Button type="text" icon={<PictureOutlined />} onClick={handleImageClick} />
            </Tooltip>
            <Tooltip title="表情">
              <Button type="text" icon={<SmileOutlined />} onClick={handleEmojiClick} />
            </Tooltip>
          </Space>
        </div>

        <div className="input-wrapper">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyPress}
            placeholder="输入消息..."
            suffix={
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                size="small"
              />
            }
            size="large"
            className="chat-input"
          />
        </div>
      </div>
    </div>
  )
}

export default ChatRoom
