/**
 * 场景监听服务
 *
 * AI Native 核心能力：
 * 监听用户行为，触发场景检测，适时推送功能入口
 *
 * 设计原则：
 * 1. 被动监听，不打扰用户
 * 2. 适时推送，自然融入对话流
 * 3. 与 ChatInterface 集成，生成功能卡片
 */

import { apiClient } from '../api/apiClient'

// ========== 类型定义 ==========

export interface SceneContext {
  [key: string]: any
}

export interface PushAction {
  scene: string
  feature: string
  priority: 'high' | 'medium' | 'low'
  message: string
  delay_seconds: number
}

export interface SceneDetectResult {
  success: boolean
  user_id: string
  trigger: string
  push_actions: PushAction[] | null
}

// ========== 场景监听器类 ==========

class SceneListener {
  private userId: string | null = null
  private isInitialized: boolean = false

  /**
   * 初始化场景监听器
   */
  init(userId: string) {
    this.userId = userId
    this.isInitialized = true
  }

  /**
   * 设置用户 ID
   */
  setUserId(userId: string) {
    this.userId = userId
  }

  /**
   * 用户注册完成
   */
  async onUserRegistered() {
    return this.detectScene('user_registered', {})
  }

  /**
   * 资料完整性检查
   */
  async onProfileCheck(profileCompletion: number) {
    return this.detectScene('profile_check', {
      profile_completion: profileCompletion
    })
  }

  /**
   * 匹配创建
   */
  async onMatchCreated(matchCount: number, compatibilityScore?: number) {
    return this.detectScene('match_created', {
      match_count: matchCount,
      compatibility_score: compatibilityScore
    })
  }

  /**
   * 聊天时长变化
   */
  async onChatDuration(partnerId: string, days: number) {
    // 只在特定天数触发
    if (![1, 3, 7, 14, 30].includes(days)) {
      return null
    }

    return this.detectScene('chat_duration', {
      partner_id: partnerId,
      days
    })
  }

  /**
   * 沉默检测
   */
  async onSilenceDetected(conversationId: string, seconds: number) {
    // 只在超过阈值时触发
    if (seconds < 300) { // 5 分钟
      return null
    }

    return this.detectScene('silence_duration', {
      conversation_id: conversationId,
      seconds
    })
  }

  /**
   * 用户意图检测
   */
  async onIntentDetected(intent: string, context: SceneContext = {}) {
    return this.detectScene('intent_detected', {
      intent,
      ...context
    })
  }

  /**
   * 特殊场合检测
   */
  async onOccasionDetected(occasion: string, context: SceneContext = {}) {
    return this.detectScene('occasion_detected', {
      occasion,
      ...context
    })
  }

  /**
   * 关系健康度检查
   */
  async onHealthCheck(healthScore: number, partnerId: string) {
    return this.detectScene('health_check', {
      health_score: healthScore,
      partner_id: partnerId
    })
  }

  /**
   * 情感分析结果
   */
  async onEmotionAnalysis(conflictLevel: number, conversationId: string) {
    return this.detectScene('emotion_analysis', {
      conflict_level: conflictLevel,
      conversation_id: conversationId
    })
  }

  /**
   * 安全检查
   */
  async onSafetyCheck(riskLevel: string) {
    return this.detectScene('safety_check', {
      risk_level: riskLevel
    })
  }

  /**
   * 核心方法：检测场景
   */
  private async detectScene(
    trigger: string,
    context: SceneContext
  ): Promise<PushAction[] | null> {
    if (!this.userId || !this.isInitialized) {
      console.warn('[SceneListener] Not initialized or no user ID')
      return null
    }

    try {
      const response = await apiClient.post('/apiClient/scene/detect', {
        trigger,
        context
      })

      const result: SceneDetectResult = response.data

      if (result.push_actions && result.push_actions.length > 0) {
        return result.push_actions
      }

      return null
    } catch (error) {
      console.error('[SceneListener] Scene detection failed:', error)
      return null
    }
  }

  /**
   * 推送功能卡片到对话区
   */
  pushFeatureCards(actions: PushAction[]) {
    actions.forEach((action, index) => {
      setTimeout(() => {
        // 触发事件，ChatInterface 会监听并生成卡片
        window.dispatchEvent(new CustomEvent('push-feature-card', {
          detail: {
            feature: action.feature,
            message: action.message,
            priority: action.priority
          }
        }))
      }, (action.delay_seconds || 0) * 1000 + index * 500) // 间隔 500ms 避免同时推送
    })
  }

  /**
   * 自动处理场景检测结果
   * 检测场景并自动推送卡片
   */
  async detectAndPush(trigger: string, context: SceneContext): Promise<boolean> {
    const actions = await this.detectScene(trigger, context)

    if (actions && actions.length > 0) {
      this.pushFeatureCards(actions)
      return true
    }

    return false
  }
}

// 单例实例
export const sceneListener = new SceneListener()

// ========== React Hook ==========

import { useEffect, useRef } from 'react'

/**
 * 使用场景监听的 React Hook
 */
export function useSceneListener(userId: string | null) {
  const initializedRef = useRef(false)

  useEffect(() => {
    if (userId && !initializedRef.current) {
      sceneListener.init(userId)
      initializedRef.current = true
    } else if (userId) {
      sceneListener.setUserId(userId)
    }
  }, [userId])

  return sceneListener
}

/**
 * 监听推送功能卡片事件的 Hook
 */
export function useFeatureCardPush(
  onPush: (data: { feature: string; message: string; priority: string }) => void
) {
  useEffect(() => {
    const handler = (event: CustomEvent) => {
      onPush(event.detail)
    }

    window.addEventListener('push-feature-card', handler as EventListener)

    return () => {
      window.removeEventListener('push-feature-card', handler as EventListener)
    }
  }, [onPush])
}

export default sceneListener