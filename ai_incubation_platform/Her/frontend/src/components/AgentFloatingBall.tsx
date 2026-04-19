/**
 * Her 悬浮球组件
 *
 * 功能：
 * - 可拖拽的悬浮球
 * - 点击展开快速对话面板
 * - 最小化 AI 助手存在
 * - 自动贴边吸附
 *
 * 🚀 [改进点3] 悬浮球面板支持直接向 Her 提问，不跳转页面
 * 🚀 [改进点5] Her 使用临时上下文（用户信息 + 匹配对象信息 + 最近聊天），不依赖主页 Her 对话历史
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Avatar, Button, Typography, Input, Space, Tag, message, Spin, Divider } from 'antd'
import { CloseOutlined, SendOutlined, ThunderboltOutlined, HeartOutlined, UserOutlined, BulbOutlined, LoadingOutlined } from '@ant-design/icons'
import HerAvatar from '../assets/her-avatar.svg'
import { authStorage } from '../utils/storage'
import { deerflowClient } from '../api/deerflowClient'
import './AgentFloatingBall.less'

const { Text } = Typography

interface ChatContext {
  partnerId: string
  partnerName: string
  partnerAvatar?: string
  recentMessages?: Array<{
    content: string
    sender: 'user' | 'partner'
    timestamp: Date
  }>
}

interface QuickChatOption {
  label: string
  trigger: string
  icon?: React.ReactNode  // 🚀 [新增] 支持自定义图标
}

interface AgentFloatingBallProps {
  visible?: boolean
  hasNewMessage?: boolean
  chatContext?: ChatContext | null
  quickOptions?: QuickChatOption[] // 外部传入，不传则根据场景自动生成
  onQuickChat?: (message: string) => void
  /** 🚀 [新增] 当前场景类型 */
  scene?: 'home' | 'chat' | 'swipe' | 'profile' | 'general'
}

// 🚀 [改进] 根据场景定义不同的快速入口选项
const SCENE_QUICK_OPTIONS: Record<string, QuickChatOption[]> = {
  // 聊天室场景：分析对象、破冰建议、约会建议
  chat: [
    { label: '分析这位对象', trigger: '帮我分析一下这位匹配对象，我们合适吗？', icon: <UserOutlined /> },
    { label: '破冰建议', trigger: '给我一些和TA聊天的破冰话题建议', icon: <BulbOutlined /> },
    { label: '约会建议', trigger: '如果我们要约会，有什么好的建议？', icon: <HeartOutlined /> },
  ],
  // 滑动匹配场景：看更多、更新偏好、匹配建议
  swipe: [
    { label: '看更多推荐', trigger: '给我看更多匹配对象', icon: <HeartOutlined /> },
    { label: '更新偏好', trigger: '我想更新我的匹配偏好', icon: <UserOutlined /> },
    { label: '匹配建议', trigger: '有什么建议可以提高我的匹配率？', icon: <BulbOutlined /> },
  ],
  // 个人资料场景：完善资料、置信度、隐私设置
  profile: [
    { label: '完善资料', trigger: '帮我看看我的资料还有什么需要完善的', icon: <UserOutlined /> },
    { label: '提高置信度', trigger: '如何提高我的置信度？', icon: <ThunderboltOutlined /> },
    { label: '隐私设置', trigger: '我想调整我的隐私设置', icon: <BulbOutlined /> },
  ],
  // 首页/通用场景：找对象、看资料、建议
  home: [
    { label: '帮我找对象', trigger: '帮我找对象', icon: <HeartOutlined /> },
    { label: '查看我的资料', trigger: '查看我的资料完善情况', icon: <UserOutlined /> },
    { label: '有什么建议', trigger: '有什么建议可以提高匹配度', icon: <BulbOutlined /> },
  ],
  // 默认/通用场景
  general: [
    { label: '帮我找对象', trigger: '帮我找对象', icon: <HeartOutlined /> },
    { label: '查看我的资料', trigger: '查看我的资料完善情况', icon: <UserOutlined /> },
    { label: '有什么建议', trigger: '有什么建议可以提高匹配度', icon: <BulbOutlined /> },
  ],
}

interface DragState {
  isDragging: boolean
  startX: number
  startY: number
  currentX: number
  currentY: number
}

const BALL_SIZE = 56
const PANEL_WIDTH = 280
const PADDING = 16

// 🚀 [改进点5] 构建临时上下文，传递给 Her
// Her 不依赖主页对话历史，只使用当前场景的临时信息
interface HerContext {
  user_info: {
    id: string
    name: string
    age?: number
    gender?: string
    location?: string
  }
  partner_info: {
    id: string
    name: string
    avatar?: string
  }
  recent_chat: Array<{
    content: string
    sender: 'user' | 'partner'
    timestamp: string
  }>
}

/**
 * 构建发送给 Her 的临时上下文
 * 🚀 [改进点5] 不依赖主页 Her 的对话历史
 */
function buildHerContext(chatContext: ChatContext | null | undefined): HerContext | null {
  const user = authStorage.getUser()
  if (!user || !chatContext) return null

  return {
    user_info: {
      id: user.id || user.username,
      name: user.name || user.username,
      age: user.age,
      gender: user.gender,
      location: user.location,
    },
    partner_info: {
      id: chatContext.partnerId,
      name: chatContext.partnerName,
      avatar: chatContext.partnerAvatar,
    },
    recent_chat: (chatContext.recentMessages || []).slice(-5).map(msg => ({
      content: msg.content,
      sender: msg.sender,
      timestamp: msg.timestamp.toISOString(),
    })),
  }
}

const AgentFloatingBall: React.FC<AgentFloatingBallProps> = ({
  visible = true,
  hasNewMessage = false,
  chatContext,
  quickOptions,  // 外部传入的选项（优先）
  onQuickChat,
  scene = 'general',  // 🚀 [新增] 默认场景
}) => {
  // 🚀 [改进] 根据场景动态生成快速入口选项
  const effectiveQuickOptions = useMemo(() => {
    // 外部传入优先
    if (quickOptions) return quickOptions
    // 如果有聊天上下文，使用聊天场景选项
    if (chatContext) return SCENE_QUICK_OPTIONS['chat']
    // 否则根据 scene 参数选择
    return SCENE_QUICK_OPTIONS[scene] || SCENE_QUICK_OPTIONS['general']
  }, [quickOptions, chatContext, scene])
  const [isExpanded, setIsExpanded] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [position, setPosition] = useState({ x: window.innerWidth - BALL_SIZE - PADDING, y: 200 })
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
  })
  const [panelSide, setPanelSide] = useState<'left' | 'right'>('left')
  const [quickInput, setQuickInput] = useState('')

  // 🚀 [改进点3] Her 响应状态 - 单次问答，不保留对话历史
  const [herResponse, setHerResponse] = useState<string | null>(null)
  const [isLoadingHer, setIsLoadingHer] = useState(false)

  // 🚀 [新增] 长按检测相关状态
  const longPressTimerRef = useRef<number | null>(null)
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null)
  const isLongPressRef = useRef(false)
  const LONG_PRESS_THRESHOLD = 300  // 长按阈值（毫秒）
  const MOVE_THRESHOLD = 10  // 移动阈值（像素），超过则取消长按

  const ballRef = useRef<HTMLDivElement>(null)

  // 根据位置自动决定面板展开方向，确保面板不超出屏幕
  useEffect(() => {
    const screenWidth = window.innerWidth
    const halfWidth = screenWidth / 2

    // 计算面板在左侧和右侧时的边界
    const panelFitsOnLeft = position.x >= PANEL_WIDTH + 12
    const panelFitsOnRight = position.x + BALL_SIZE + PANEL_WIDTH + 12 <= screenWidth

    // 优先选择不超出屏幕的方向，如果都不超出则根据左右半屏决定
    if (panelFitsOnLeft && !panelFitsOnRight) {
      setPanelSide('left')
    } else if (panelFitsOnRight && !panelFitsOnLeft) {
      setPanelSide('right')
    } else {
      // 两边都能放下或都放不下，根据中点决定
      setPanelSide(position.x < halfWidth ? 'right' : 'left')
    }
  }, [position.x])

  // 贴边吸附（只在收起状态执行）
  const snapToEdge = useCallback(() => {
    if (isExpanded) return

    const screenWidth = window.innerWidth
    const halfWidth = screenWidth / 2

    if (position.x < halfWidth) {
      setPosition(prev => ({ ...prev, x: PADDING }))
    } else {
      setPosition(prev => ({ ...prev, x: screenWidth - BALL_SIZE - PADDING }))
    }
  }, [position.x, isExpanded])

  // 点击展开/收起（提前定义，供 handleTouchEndCheck 使用）
  const handleToggleExpand = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 🚀 [改进] 长按开始拖拽
  const handleLongPressStart = useCallback((clientX: number, clientY: number) => {
    touchStartRef.current = { x: clientX, y: clientY, time: Date.now() }
    isLongPressRef.current = false

    // 设置长按计时器
    longPressTimerRef.current = window.setTimeout(() => {
      isLongPressRef.current = true
      setIsDragging(true)
      setDragState({
        isDragging: true,
        startX: clientX - position.x,
        startY: clientY - position.y,
        currentX: position.x,
        currentY: position.y,
      })
    }, LONG_PRESS_THRESHOLD)
  }, [position.x, position.y])

  // 🚀 [改进] 触摸移动检测
  const handleTouchMoveCheck = useCallback((clientX: number, clientY: number) => {
    if (!touchStartRef.current || isLongPressRef.current) return

    const deltaX = Math.abs(clientX - touchStartRef.current.x)
    const deltaY = Math.abs(clientY - touchStartRef.current.y)

    // 如果移动超过阈值，取消长按计时器（改为点击）
    if (deltaX > MOVE_THRESHOLD || deltaY > MOVE_THRESHOLD) {
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current)
        longPressTimerRef.current = null
      }
      touchStartRef.current = null
    }
  }, [])

  // 🚀 [改进] 触摸结束处理
  const handleTouchEndCheck = useCallback(() => {
    // 清除长按计时器
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current)
      longPressTimerRef.current = null
    }

    // 如果是长按拖拽结束
    if (isLongPressRef.current && dragState.isDragging) {
      setDragState(prev => ({ ...prev, isDragging: false }))
      setIsDragging(false)
      setTimeout(() => snapToEdge(), 150)
      isLongPressRef.current = false
    } else if (touchStartRef.current && !isLongPressRef.current) {
      // 如果是短按（点击），展开面板
      const elapsed = Date.now() - touchStartRef.current.time
      if (elapsed < LONG_PRESS_THRESHOLD) {
        handleToggleExpand()
      }
    }

    touchStartRef.current = null
  }, [dragState.isDragging, snapToEdge, handleToggleExpand])

  // 🚀 [改进] 处理拖拽移动 - 使用 useCallback 稳定引用
  const handleDragMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!dragState.isDragging) return

    const clientX = 'clientX' in e ? e.clientX : e.touches[0].clientX
    const clientY = 'clientY' in e ? e.clientY : e.touches[0].clientY

    const newX = clientX - dragState.startX
    const newY = clientY - dragState.startY

    const screenBounds = {
      minX: PADDING,
      maxX: window.innerWidth - BALL_SIZE - PADDING,
      minY: PADDING,
      maxY: window.innerHeight - BALL_SIZE - PADDING,
    }

    setPosition({
      x: Math.max(screenBounds.minX, Math.min(screenBounds.maxX, newX)),
      y: Math.max(screenBounds.minY, Math.min(screenBounds.maxY, newY)),
    })
  }, [dragState.isDragging, dragState.startX, dragState.startY])

  // 绑定全局拖拽事件
  useEffect(() => {
    if (dragState.isDragging) {
      window.addEventListener('mousemove', handleDragMove)
      window.addEventListener('mouseup', handleTouchEndCheck)
      window.addEventListener('touchmove', handleDragMove as any, { passive: false })
      window.addEventListener('touchend', handleTouchEndCheck)
    }

    return () => {
      window.removeEventListener('mousemove', handleDragMove)
      window.removeEventListener('mouseup', handleTouchEndCheck)
      window.removeEventListener('touchmove', handleDragMove as any)
      window.removeEventListener('touchend', handleTouchEndCheck)
    }
  }, [dragState.isDragging, handleDragMove, handleTouchEndCheck])

  // 关闭悬浮球
  const handleClose = useCallback(() => {
    setIsExpanded(false)
    // 🚀 [改进点3] 关闭时清空响应，下次打开是新的问答
    setHerResponse(null)
    setQuickInput('')
  }, [])

  // 🚀 [改进点3 + 改进点5] 直接调用 Her API，不跳转页面
  // 使用临时上下文，不依赖主页 Her 的对话历史
  const callHerAPI = useCallback(async (question: string) => {
    if (!question.trim()) {
      message.warning('请输入内容')
      return
    }

    setIsLoadingHer(true)
    setHerResponse(null)

    try {
      // 构建临时上下文
      const herContext = buildHerContext(chatContext)

      // 构建带上下文的消息
      let contextMessage = question
      if (herContext) {
        // 🚀 [改进点5] 将临时上下文注入消息，让 Her 了解当前场景
        contextMessage = `[上下文]
用户：${herContext.user_info.name}（${herContext.user_info.age || '未知'}岁，${herContext.user_info.location || '未知'}）
聊天对象：${herContext.partner_info.name}
最近聊天：${herContext.recent_chat.length > 0 ? herContext.recent_chat.map(m => `${m.sender === 'user' ? '我' : 'TA'}: ${m.content}`).join('\n') : '暂无聊天记录'}

[用户问题]
${question}`
      }

      // 使用临时 thread ID，不保留对话历史
      const tempThreadId = `her-floating-${Date.now()}`
      const response = await deerflowClient.chat(contextMessage, tempThreadId)

      if (response.success && response.ai_message) {
        setHerResponse(response.ai_message)
      } else {
        setHerResponse('抱歉，我暂时无法回答这个问题，请稍后再试~')
      }
    } catch (error) {
      console.error('[AgentFloatingBall] Her API error:', error)
      setHerResponse('网络出现问题，请稍后再试~')
    } finally {
      setIsLoadingHer(false)
    }
  }, [chatContext])

  // 发送快速对话 - 🚀 [改进点3] 直接调用 Her，不跳转
  const handleQuickSend = useCallback(() => {
    callHerAPI(quickInput)
  }, [quickInput, callHerAPI])

  // 点击预设选项 - 🚀 [改进点3] 直接调用 Her，不跳转
  const handleQuickOption = useCallback((trigger: string) => {
    callHerAPI(trigger)
  }, [callHerAPI])

  if (!visible) {
    return null
  }

  // 计算面板位置
  const panelStyle: React.CSSProperties = isExpanded ? {
    position: 'fixed',
    top: position.y,
    left: panelSide === 'left'
      ? position.x - PANEL_WIDTH - 12 // 面板在左侧，距离悬浮球 12px
      : position.x + BALL_SIZE + 12, // 面板在右侧，距离悬浮球 12px
    zIndex: 10000,
  } : undefined

  return (
    <>
      {/* 悬浮球容器 */}
      <div
        ref={ballRef}
        className={`agent-floating-ball ${isExpanded ? 'expanded' : ''} ${hasNewMessage ? 'has-message' : ''} ${isDragging ? 'dragging' : ''}`}
        style={{
          left: position.x,
          top: position.y,
        }}
        onMouseDown={(e) => {
          e.preventDefault()
          handleLongPressStart(e.clientX, e.clientY)
        }}
        onMouseMove={(e) => {
          handleTouchMoveCheck(e.clientX, e.clientY)
        }}
        onMouseUp={handleTouchEndCheck}
        onTouchStart={(e) => {
          const touch = e.touches[0]
          handleLongPressStart(touch.clientX, touch.clientY)
        }}
        onTouchMove={(e) => {
          const touch = e.touches[0]
          handleTouchMoveCheck(touch.clientX, touch.clientY)
          // 如果正在拖拽，也处理拖拽移动
          if (dragState.isDragging) {
            handleDragMove(e as any)
          }
        }}
        onTouchEnd={handleTouchEndCheck}
      >
        {/* 悬浮球本体 - 🚀 [改进] 整个球都是拖拽区域 */}
          <Avatar
            size={BALL_SIZE}
            className="agent-ball"
            src={HerAvatar}
            style={{ backgroundColor: '#fff', padding: 4 }}
          />
      </div>

      {/* 展开的快速对话面板 */}
      {isExpanded && (
        <div
          className={`agent-ball-panel panel-${panelSide}`}
          style={panelStyle}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="panel-header">
            <Avatar
              size={40}
              className="agent-avatar"
              src={HerAvatar}
              style={{ backgroundColor: '#fff', padding: 4 }}
            />
            <div className="agent-info">
              <Text strong className="agent-name">Her</Text>
              <Text type="secondary" className="agent-status">
                {hasNewMessage ? '有新消息' : '在线'}
              </Text>
            </div>
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              className="close-btn"
              onClick={handleClose}
              onMouseDown={(e) => e.stopPropagation()}
            />
          </div>

          {/* 快速对话面板 */}
          <div className="quick-chat-panel">
            {/* 预设选项 */}
            <div className="quick-options" style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
                快速入口
              </Text>
              <Space wrap size={4}>
                {effectiveQuickOptions.map((opt) => (
                  <Tag
                    key={opt.trigger}
                    className="quick-option-tag"
                    icon={opt.icon || <ThunderboltOutlined />}
                    onClick={() => handleQuickOption(opt.trigger)}
                    style={{ cursor: isLoadingHer ? 'not-allowed' : 'pointer', opacity: isLoadingHer ? 0.5 : 1 }}
                  >
                    {opt.label}
                  </Tag>
                ))}
              </Space>
            </div>

            {/* 🚀 [改进点3] Her 响应显示区域 - 单次问答，不显示历史对话 */}
            {(isLoadingHer || herResponse) && (
              <div className="her-response-area">
                {isLoadingHer ? (
                  <div className="her-loading">
                    <Spin indicator={<LoadingOutlined style={{ fontSize: 16, color: '#C88B8B' }} spin />} />
                    <Text type="secondary" style={{ marginLeft: 8 }}>正在思考...</Text>
                  </div>
                ) : (
                  <div className="her-response-bubble">
                    <Avatar size={24} src={HerAvatar} style={{ backgroundColor: '#fff', padding: 2 }} />
                    <div className="her-response-content">
                      <Text style={{ fontSize: 13, lineHeight: 1.6, color: '#333' }}>{herResponse}</Text>
                    </div>
                    <Button
                      type="text"
                      size="small"
                      icon={<CloseOutlined />}
                      className="clear-response-btn"
                      onClick={() => setHerResponse(null)}
                    />
                  </div>
                )}
                <Divider style={{ margin: '12px 0' }} />
              </div>
            )}

            {/* 自定义输入 */}
            <div className="quick-input-area">
              <Input
                value={quickInput}
                onChange={(e) => setQuickInput(e.target.value)}
                placeholder={herResponse ? "继续提问..." : "输入问题..."}
                size="small"
                disabled={isLoadingHer}
                onPressEnter={handleQuickSend}
                suffix={
                  <Button
                    type="primary"
                    size="small"
                    icon={<SendOutlined />}
                    onClick={handleQuickSend}
                    disabled={isLoadingHer || !quickInput.trim()}
                    style={{ borderRadius: 4 }}
                  />
                }
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default AgentFloatingBall
