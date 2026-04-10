/**
 * Her 悬浮球组件
 *
 * 功能：
 * - 可拖拽的悬浮球
 * - 点击展开快速对话面板
 * - 最小化 AI 助手存在
 * - 自动贴边吸附
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Avatar, Button, Typography } from 'antd'
import { CloseOutlined } from '@ant-design/icons'
import HerAvatar from '../assets/her-avatar.svg'
import QuickChatPanel from './QuickChatPanel'
import './AgentFloatingBall.less'

const { Text } = Typography

interface ChatContext {
  partnerId: string
  partnerName: string
}

interface AgentFloatingBallProps {
  visible?: boolean
  hasNewMessage?: boolean
  chatContext?: ChatContext | null // 当前聊天上下文
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

const AgentFloatingBall: React.FC<AgentFloatingBallProps> = ({
  visible = true,
  hasNewMessage = false,
  chatContext,
}) => {
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

  // 处理拖拽开始
  const handleDragStart = useCallback((e: React.MouseEvent | MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const clientX = 'clientX' in e ? e.clientX : (e as TouchEvent).touches[0].clientX
    const clientY = 'clientY' in e ? e.clientY : (e as TouchEvent).touches[0].clientY

    setIsDragging(true)
    setDragState({
      isDragging: true,
      startX: clientX - position.x,
      startY: clientY - position.y,
      currentX: position.x,
      currentY: position.y,
    })
  }, [position.x, position.y])

  // 处理拖拽移动 - 使用 useCallback 稳定引用
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

  // 处理拖拽结束 - 使用 useCallback 稳定引用
  const handleDragEnd = useCallback(() => {
    if (dragState.isDragging) {
      setDragState(prev => ({ ...prev, isDragging: false }))
      setIsDragging(false)
      setTimeout(() => snapToEdge(), 150)
    }
  }, [dragState.isDragging, snapToEdge])

  // 绑定全局拖拽事件
  useEffect(() => {
    if (dragState.isDragging) {
      window.addEventListener('mousemove', handleDragMove)
      window.addEventListener('mouseup', handleDragEnd)
      window.addEventListener('touchmove', handleDragMove as any, { passive: false })
      window.addEventListener('touchend', handleDragEnd)
    }

    return () => {
      window.removeEventListener('mousemove', handleDragMove)
      window.removeEventListener('mouseup', handleDragEnd)
      window.removeEventListener('touchmove', handleDragMove as any)
      window.removeEventListener('touchend', handleDragEnd)
    }
  }, [dragState.isDragging, handleDragMove, handleDragEnd])

  // 点击展开/收起
  const handleToggleExpand = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 关闭悬浮球
  const handleClose = useCallback(() => {
    setIsExpanded(false)
  }, [])

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
        onMouseDown={handleDragStart}
        onTouchStart={handleDragStart}
      >
        {/* 悬浮球本体 */}
          <Avatar
            size={BALL_SIZE}
            className="agent-ball"
            src={HerAvatar}
            style={{ backgroundColor: '#fff', padding: 4 }}
            onClick={(e) => {
              e.stopPropagation()
              handleToggleExpand()
            }}
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
          <QuickChatPanel chatContext={chatContext} />
        </div>
      )}
    </>
  )
}

export default AgentFloatingBall
