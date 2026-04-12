/**
 * 行为追踪 Hook - 隐性偏好推断
 *
 * 用于收集用户行为数据并推断隐性偏好
 *
 * 使用示例：
 * ```tsx
 * const { trackProfileView, trackSwipe, trackChatMessage, flushEvents } = useBehaviorTracking(userId)
 *
 * // 查看资料时
 * trackProfileView(targetUserId, { duration_seconds: 12, photo_view_count: 3 })
 *
 * // 滑动操作时
 * trackSwipe(targetUserId, 'like', { decision_time_seconds: 2.5 })
 *
 * // 定期上报
 * flushEvents()
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { quickStartApi, BehaviorEvent, BehaviorSignals } from '../api/quickStartApi'

interface ProfileViewOptions {
  duration_seconds?: number
  photo_view_count?: number
  bio_read_duration?: number
}

interface SwipeOptions {
  decision_time_seconds?: number
}

interface ChatOptions {
  emojis_used?: string[]
}

interface BehaviorTrackingState {
  events: BehaviorEvent[]
  signals: BehaviorSignals | null
  isTracking: boolean
  lastFlushTime: Date | null
}

const FLUSH_INTERVAL = 30000 // 30秒定期上报
const MAX_BUFFER_SIZE = 50 // 最大缓存事件数

export function useBehaviorTracking(userId: string | null) {
  const [state, setState] = useState<BehaviorTrackingState>({
    events: [],
    signals: null,
    isTracking: false,
    lastFlushTime: null,
  })

  const eventBufferRef = useRef<BehaviorEvent[]>([])
  const flushTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 定期上报
  const flushEvents = useCallback(async () => {
    if (!userId || eventBufferRef.current.length === 0) return

    setState(prev => ({ ...prev, isTracking: true }))

    try {
      const result = await quickStartApi.trackBatchBehaviorEvents(
        userId,
        eventBufferRef.current
      )

      // 清空缓存
      eventBufferRef.current = []

      setState(prev => ({
        ...prev,
        events: [],
        signals: result.data.signals_calculated,
        isTracking: false,
        lastFlushTime: new Date(),
      }))
    } catch (error) {
      console.error('[BehaviorTracking] Flush failed:', error)
      setState(prev => ({ ...prev, isTracking: false }))
    }
  }, [userId])

  // 追踪资料查看
  const trackProfileView = useCallback(
    (targetId: string, options: ProfileViewOptions = {}) => {
      if (!userId) return

      const event: BehaviorEvent = {
        user_id: userId,
        event_type: 'profile_view',
        target_id: targetId,
        duration_seconds: options.duration_seconds,
        photo_view_count: options.photo_view_count,
        bio_read_duration: options.bio_read_duration,
      }

      addEvent(event)
    },
    [userId]
  )

  // 追踪滑动操作
  const trackSwipe = useCallback(
    (targetId: string, action: 'like' | 'dislike' | 'skip', options: SwipeOptions = {}) => {
      if (!userId) return

      const event: BehaviorEvent = {
        user_id: userId,
        event_type: 'swipe_action',
        target_id: targetId,
        decision_time_seconds: options.decision_time_seconds,
        metadata: { action },
      }

      addEvent(event)
    },
    [userId]
  )

  // 追踪聊天消息
  const trackChatMessage = useCallback(
    (receiverId: string, options: ChatOptions = {}) => {
      if (!userId) return

      const event: BehaviorEvent = {
        user_id: userId,
        event_type: 'chat_message',
        target_id: receiverId,
        emojis_used: options.emojis_used,
      }

      addEvent(event)
    },
    [userId]
  )

  // 内部方法：添加事件到缓存
  const addEvent = (event: BehaviorEvent) => {
    eventBufferRef.current.push(event)

    // 缓存满时自动上报
    if (eventBufferRef.current.length >= MAX_BUFFER_SIZE) {
      flushEvents()
    }
  }

  // 设置定期上报
  useEffect(() => {
    if (!userId) return

    flushTimerRef.current = setInterval(flushEvents, FLUSH_INTERVAL)

    return () => {
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current)
      }
      // 组件卸载时上报剩余事件
      if (eventBufferRef.current.length > 0) {
        flushEvents()
      }
    }
  }, [userId, flushEvents])

  // 获取信号统计
  const fetchSignals = useCallback(async (days: number = 7) => {
    if (!userId) return null

    try {
      const result = await quickStartApi.getBehaviorSignals(userId, days)
      setState(prev => ({ ...prev, signals: result.signals }))
      return result
    } catch (error) {
      console.error('[BehaviorTracking] Fetch signals failed:', error)
      return null
    }
  }, [userId])

  return {
    // 状态
    events: state.events,
    signals: state.signals,
    isTracking: state.isTracking,
    lastFlushTime: state.lastFlushTime,

    // 追踪方法
    trackProfileView,
    trackSwipe,
    trackChatMessage,

    // 上报方法
    flushEvents,
    fetchSignals,
  }
}

/**
 * 浏览时长追踪 Hook
 *
 * 自动追踪用户在某个资料上停留的时间
 */
export function useBrowseDurationTracker(
  userId: string | null,
  targetId: string | null,
  onTrack?: (duration: number) => void
) {
  const startTimeRef = useRef<number | null>(null)
  const photoViewCountRef = useRef<number>(0)
  const bioReadStartRef = useRef<number | null>(null)

  // 开始追踪
  const startTracking = useCallback(() => {
    startTimeRef.current = Date.now()
    photoViewCountRef.current = 0
    bioReadStartRef.current = null
  }, [])

  // 记录照片查看
  const recordPhotoView = useCallback(() => {
    photoViewCountRef.current += 1
  }, [])

  // 开始记录简介阅读
  const startBioRead = useCallback(() => {
    bioReadStartRef.current = Date.now()
  }, [])

  // 结束追踪并上报
  const endTracking = useCallback(() => {
    if (!userId || !targetId || startTimeRef.current === null) return

    const duration_seconds = (Date.now() - startTimeRef.current) / 1000
    const photo_view_count = photoViewCountRef.current

    let bio_read_duration = 0
    if (bioReadStartRef.current !== null) {
      bio_read_duration = (Date.now() - bioReadStartRef.current) / 1000
    }

    // 上报事件
    quickStartApi.trackBehaviorEvent({
      user_id: userId,
      event_type: 'profile_view',
      target_id: targetId,
      duration_seconds,
      photo_view_count,
      bio_read_duration,
    })

    if (onTrack) {
      onTrack(duration_seconds)
    }

    // 重置
    startTimeRef.current = null
    photoViewCountRef.current = 0
    bioReadStartRef.current = null
  }, [userId, targetId, onTrack])

  return {
    startTracking,
    endTracking,
    recordPhotoView,
    startBioRead,
  }
}