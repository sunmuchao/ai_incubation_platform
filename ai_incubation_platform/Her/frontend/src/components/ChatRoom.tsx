/**
 * 聊天室组件 - 真实的两人聊天界面
 *
 * 功能:
 * - 发送/接收消息
 * - 消息历史记录
 * - 已读/未读状态
 * - Her 助手提示（问题 9 修复）
 * - 发送动画反馈（问题 10 修复）
 * - 表情入口优化（问题 11 修复）
 */

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Input, Button, Avatar, Typography, Space, Empty, Tooltip, message, Tag, Modal, Dropdown, Badge, Spin } from 'antd'
import { SendOutlined, LeftOutlined, PictureOutlined, SmileOutlined, MoreOutlined, EyeInvisibleOutlined, EyeOutlined, ClockCircleOutlined, RocketOutlined, CloseOutlined, BulbOutlined } from '@ant-design/icons'
import type { MatchCandidate } from '../types'
import { chatApi, yourTurnApi } from '../api'
import { websocketService } from '../services/websocket'
import { authStorage, herStorage } from '../utils/storage'
import { isIOS, optimizeIOSScroll, optimizeIOSInput } from '../utils/iosUtils'
import HerAvatar from '../assets/her-avatar.svg'
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
  // 🔧 [问题16方案A] 默认唤醒 Her，让用户能立刻看到悬浮球
  const [herSleepingLocal, setHerSleepingLocal] = useState(() => {
    // 🔧 [修复] 首次进入聊天室时，默认唤醒（不休眠）
    // 只有用户主动休眠后才隐藏悬浮球
    return herStorage.isSleepingInChat()
  })

  // 🔧 [问题16方案A] Her 提示条状态 - 首次进入时显示，告知用户 Her 正在旁观
  const [showHerTip, setShowHerTip] = useState(() => {
    // 如果用户已经主动休眠了，不显示提示
    // 否则默认显示提示，3秒后自动隐藏
    return !herStorage.isSleepingInChat()
  })

  // 🔧 [问题9修复] 首次进入时，3 秒后自动隐藏 Her 提示条
  useEffect(() => {
    if (showHerTip) {
      const timer = setTimeout(() => {
        setShowHerTip(false)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [showHerTip])

  // ==================== 🔧 [改进点4] 犹豫检测 + Her 智能建议 ====================

  // Her 建议状态
  interface HerAdvice {
    message: string       // 建议内容
    triggerType: string   // 触发类型：'no_reply' | 'input_hesitate' | 'emoji_hesitate'
    timestamp: Date       // 显示时间
  }
  const [herAdvice, setHerAdvice] = useState<HerAdvice | null>(null)
  const [herAdviceLoading, setHerAdviceLoading] = useState(false)

  // 犹豫检测状态
  const [lastPartnerMessageTime, setLastPartnerMessageTime] = useState<Date | null>(null)  // 对方最后发消息时间
  const [userLastSendTime, setUserLastSendTime] = useState<Date | null>(null)  // 用户最后发送时间
  const [inputStartTime, setInputStartTime] = useState<Date | null>(null)  // 输入开始时间
  const [emojiOpenCount, setEmojiOpenCount] = useState(0)  // 表情面板打开次数
  const hesitationDetectedRef = useRef(false)  // 是否已触发犹豫检测（避免重复触发）

  // 犹豫检测配置
  const HESITATION_CONFIG = {
    NO_REPLY_THRESHOLD: 30000,      // 对方发消息后，用户多久没回复触发（30秒）
    INPUT_HESITATE_THRESHOLD: 20000, // 输入框有内容但没发送触发（20秒）
    EMOJI_OPEN_THRESHOLD: 3,        // 表情面板打开次数触发（3次）
    ADVICE_DISPLAY_DURATION: 8000,  // 建议显示时长（8秒）
  }

  // 🔧 [改进点4] 检测 1：对方发消息后，用户多久没回复
  useEffect(() => {
    if (!lastPartnerMessageTime || herSleepingLocal || hesitationDetectedRef.current) return

    const checkInterval = setInterval(() => {
      const now = new Date()
      const elapsed = now.getTime() - lastPartnerMessageTime.getTime()

      // 超过阈值没回复 → 触发犹豫检测
      if (elapsed > HESITATION_CONFIG.NO_REPLY_THRESHOLD && !hesitationDetectedRef.current) {
        hesitationDetectedRef.current = true
        triggerHerAdvice('no_reply', '对方发消息了，用户犹豫怎么回复')
      }
    }, 5000)  // 每 5 秒检查一次

    return () => clearInterval(checkInterval)
  }, [lastPartnerMessageTime, herSleepingLocal])

  // 🔧 [改进点4] 检测 2：输入框有内容但没发送
  useEffect(() => {
    // 用户刚发送消息，重置犹豫检测
    if (userLastSendTime) {
      const elapsed = new Date().getTime() - userLastSendTime.getTime()
      if (elapsed < 5000) {  // 发送后 5 秒内不触发犹豫检测
        return
      }
    }

    if (!inputValue.trim()) {
      // 输入框清空，重置输入开始时间
      setInputStartTime(null)
      return
    }

    // 输入框有内容，记录开始时间
    if (!inputStartTime) {
      setInputStartTime(new Date())
    }

    // 检测犹豫：输入框有内容超过阈值时间
    const inputHesitateTimer = setTimeout(() => {
      if (inputValue.trim() && !hesitationDetectedRef.current && !herSleepingLocal) {
        hesitationDetectedRef.current = true
        triggerHerAdvice('input_hesitate', '用户在输入但犹豫发送')
      }
    }, HESITATION_CONFIG.INPUT_HESITATE_THRESHOLD)

    return () => clearTimeout(inputHesitateTimer)
  }, [inputValue, inputStartTime, userLastSendTime, herSleepingLocal])

  // 🔧 [改进点4] 触发 Her 建议（直接显示建议气泡）
  const triggerHerAdvice = useCallback((triggerType: string, context: string) => {
    if (herSleepingLocal) return

    console.log(`[犹豫检测] 触发类型: ${triggerType}, 上下文: ${context}`)

    // 🔧 [临时方案] 根据触发类型生成预设建议
    // 后续改进点5实施后，改为调用 Her API 获取建议
    let adviceMessage = ''

    // 获取当前用户 ID（直接从 storage 获取，避免依赖顺序）
    const userId = authStorage.getUser()?.id || authStorage.getUser()?.username || 'anonymous'

    // 获取最近一条对方消息的内容（用于生成针对性建议）
    const lastPartnerMessage = messages.filter(m => m.sender_id !== userId).pop()
    const lastPartnerContent = lastPartnerMessage?.content || ''

    switch (triggerType) {
      case 'no_reply':
        // 对方发消息后用户没回复
        if (lastPartnerContent.includes('旅行') || lastPartnerContent.includes('旅游')) {
          adviceMessage = '可以分享你的旅行经历，或者问她去过最难忘的地方'
        } else if (lastPartnerContent.includes('电影') || lastPartnerContent.includes('看书')) {
          adviceMessage = '可以聊聊最近看的电影或书籍，问问她的推荐'
        } else if (lastPartnerContent.includes('吃') || lastPartnerContent.includes('美食')) {
          adviceMessage = '可以聊聊你喜欢的美食，或者问她有什么餐厅推荐'
        } else {
          adviceMessage = '可以先回应她的话题，再延伸到你的经历'
        }
        break

      case 'input_hesitate':
        // 用户在输入但犹豫发送
        adviceMessage = '不确定怎么表达？可以试着发送，对方会理解的'
        break

      case 'emoji_hesitate':
        // 用户犹豫发表情
        adviceMessage = '发个 😊 笑脸或 ❤️ 爱心，简单又温暖'
        break

      default:
        adviceMessage = '点击详细对话，让 Her 帮你想想'
    }

    // 设置建议状态
    setHerAdvice({
      message: adviceMessage,
      triggerType,
      timestamp: new Date(),
    })
    setHerAdviceLoading(false)

    // 8 秒后自动消失
    setTimeout(() => {
      setHerAdvice(null)
      hesitationDetectedRef.current = false
    }, HESITATION_CONFIG.ADVICE_DISPLAY_DURATION)
  }, [herSleepingLocal, messages])

  // 🔧 [改进点4] 重置犹豫检测状态（用户发送消息后）
  const resetHesitationDetection = useCallback(() => {
    hesitationDetectedRef.current = false
    setLastPartnerMessageTime(null)
    setInputStartTime(null)
    setEmojiOpenCount(0)
    setHerAdvice(null)
  }, [])

  // 🔧 [改进点4] 关闭建议气泡
  const handleCloseAdvice = useCallback(() => {
    setHerAdvice(null)
    // 重置犹豫检测，允许下次触发
    hesitationDetectedRef.current = false
  }, [])

  // ==================== 图片和表情功能状态 ====================
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
  // 🔧 [改进点4] 表情点击计数，用于犹豫检测
  const handleEmojiClick = useCallback(() => {
    setShowEmojiPicker(prev => !prev)

    // 如果是打开表情面板（之前是关闭状态）
    if (!showEmojiPicker) {
      setEmojiOpenCount(prev => prev + 1)

      // 超过阈值 → 触发犹豫检测
      if (emojiOpenCount + 1 >= HESITATION_CONFIG.EMOJI_OPEN_THRESHOLD && !hesitationDetectedRef.current && !herSleepingLocal) {
        hesitationDetectedRef.current = true
        triggerHerAdvice('emoji_hesitate', '用户犹豫发表情')
      }
    }
  }, [showEmojiPicker, emojiOpenCount, herSleepingLocal, triggerHerAdvice])

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

          // 🔧 [改进点4] 收到对方消息，记录时间用于犹豫检测
          setLastPartnerMessageTime(new Date())
          // 重置犹豫检测状态，允许新的犹豫检测
          hesitationDetectedRef.current = false
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

  // 🚀 [改进点5] 向悬浮球发送上下文更新事件
  // 让悬浮球 Her 了解当前用户、聊天对象和最近消息
  useEffect(() => {
    if (!actualPartnerId) return

    // 构建最近消息（最多 5 条）
    const recentMessages = messages.slice(-5).map(msg => ({
      content: msg.content,
      sender: msg.sender_id === currentUserId ? 'user' : 'partner',
      timestamp: new Date(msg.created_at),
    }))

    // 派发上下文更新事件
    window.dispatchEvent(new CustomEvent('her-context-update', {
      detail: {
        partnerId: actualPartnerId,
        partnerName: actualPartnerName,
        partnerAvatar: actualPartnerAvatar,
        recentMessages,
      }
    }))
  }, [messages, actualPartnerId, actualPartnerName, actualPartnerAvatar, currentUserId])

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

    // 🔧 [改进点4] 用户发送消息，重置犹豫检测状态
    setUserLastSendTime(new Date())
    resetHesitationDetection()

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
  }, [inputValue, isLoading, actualPartnerId, currentUserId, resetHesitationDetection])

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

      {/* 🔧 [问题9修复] Her 活跃提示条 - 首次进入时显示，告诉用户 Her 正在旁观 */}
      {!herSleepingLocal && showHerTip && (
        <div className="her-active-tip-bar">
          <Avatar size={20} src={HerAvatar} style={{ backgroundColor: '#fff', padding: 2 }} />
          <Text style={{ fontSize: 12, color: '#C88B8B' }}>
            Her 正在旁观，点击右下角悬浮球可请求建议
          </Text>
          <Button
            type="link"
            size="small"
            onClick={() => setShowHerTip(false)}
            style={{ fontSize: 12, padding: '0 4px', marginLeft: 8 }}
          >
            知道了
          </Button>
        </div>
      )}

      {/* 🔧 [改进点4] Her 智能建议气泡 - 只在用户犹豫时显示 */}
      {!herSleepingLocal && herAdvice && (
        <div className="her-advice-bubble">
          <div className="advice-header">
            <Avatar size={20} src={HerAvatar} style={{ backgroundColor: '#fff', padding: 2 }} />
            <Text style={{ fontSize: 12, color: '#C88B8B', fontWeight: 500 }}>Her 建议</Text>
          </div>
          <div className="advice-content">
            <Text style={{ fontSize: 13, color: '#666' }}>{herAdvice.message}</Text>
          </div>
          <div className="advice-actions">
            <Button
              type="link"
              size="small"
              icon={<BulbOutlined />}
              onClick={() => {
                // 触发悬浮球面板打开，让用户跟 Her 详细对话
                window.dispatchEvent(new CustomEvent('open-her-panel'))
                handleCloseAdvice()
              }}
              style={{ fontSize: 12, color: '#C88B8B' }}
            >
              详细对话
            </Button>
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={handleCloseAdvice}
              style={{ fontSize: 12, color: '#999' }}
            />
          </div>
        </div>
      )}

      {/* 🔧 [改进点4] Her 建议加载状态 */}
      {herAdviceLoading && (
        <div className="her-advice-loading">
          <Spin size="small" />
          <Text type="secondary" style={{ fontSize: 12 }}>Her 正在思考...</Text>
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

        {/* 🔧 [问题11修复] 表情按钮移到更显眼位置 - 输入框左侧 */}
        <div className="input-tools-left">
          <Tooltip title="表情">
            <Button
              type="text"
              icon={<SmileOutlined style={{ fontSize: 20 }} />}
              onClick={handleEmojiClick}
              className={showEmojiPicker ? 'emoji-btn-active' : ''}
            />
          </Tooltip>
          <Tooltip title="图片">
            <Button type="text" icon={<PictureOutlined style={{ fontSize: 20 }} />} onClick={handleImageClick} />
          </Tooltip>
        </div>

        <div className="input-wrapper">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyPress}
            placeholder="输入消息..."
            suffix={
              <Space size={4}>
                {/* 🔧 [问题10修复] 发送按钮动画效果 */}
                <Button
                  type="primary"
                  icon={isLoading ? <RocketOutlined className="send-animation" /> : <SendOutlined />}
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isLoading}
                  size="small"
                  className={`send-btn ${isLoading ? 'sending' : ''}`}
                />
              </Space>
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
