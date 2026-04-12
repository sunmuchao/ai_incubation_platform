/**
 * 关系洞察 API 服务
 * 包含：共同经历、沉默检测、破冰话题、情感调解、爱之语翻译、关系气象
 */

import { apiClient } from './apiClient'

// ==================== 共同经历 API ====================

export const sharedExperiencesApi = {
  /**
   * 检测共同经历
   */
  async detectSharedExperiences(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; experiences: any[] }> {
    const response = await apiClient.get(`/api/shared-experiences/detect/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 记录共同经历
   */
  async recordSharedExperience(
    user_a_id: string,
    user_b_id: string,
    experience_data: Record<string, any>
  ): Promise<{ success: boolean; experience_id: string }> {
    const response = await apiClient.post('/api/shared-experiences/record', {
      user_a_id,
      user_b_id,
      experience_data,
    })
    return response.data
  },

  /**
   * 获取共同经历时间线
   */
  async getSharedExperiencesTimeline(
    user_a_id: string,
    user_b_id: string,
    limit = 20
  ): Promise<{ success: boolean; timeline: any[] }> {
    const response = await apiClient.get(`/api/shared-experiences/timeline/${user_a_id}/${user_b_id}`, {
      params: { limit },
    })
    return response.data
  },
}

// ==================== 沉默检测 API ====================

export const silenceDetectionApi = {
  /**
   * 检测沉默状态
   */
  async detectSilence(
    conversation_id: string
  ): Promise<{ success: boolean; silence_detected: boolean; duration?: number }> {
    const response = await apiClient.get(`/api/silence-detection/detect/${conversation_id}`)
    return response.data
  },

  /**
   * 分析沉默原因
   */
  async analyzeSilenceReason(
    conversation_id: string,
    silence_duration: number
  ): Promise<{ success: boolean; reasons: any[] }> {
    const response = await apiClient.post('/api/silence-detection/analyze', {
      conversation_id,
      silence_duration,
    })
    return response.data
  },

  /**
   * 获取沉默历史
   */
  async getSilenceHistory(
    user_id: string,
    limit = 10
  ): Promise<{ success: boolean; history: any[] }> {
    const response = await apiClient.get(`/api/silence-detection/history/${user_id}`, {
      params: { limit },
    })
    return response.data
  },
}

// ==================== 破冰话题 API ====================

export const icebreakerTopicsApi = {
  /**
   * 获取破冰话题
   */
  async getIcebreakerTopics(
    user_a_id: string,
    user_b_id: string,
    context: 'first_chat' | 'stale_conversation' | 'after_date' = 'first_chat'
  ): Promise<{ success: boolean; topics: any[] }> {
    const response = await apiClient.get(`/api/icebreaker-topics/get/${user_a_id}/${user_b_id}`, {
      params: { context },
    })
    return response.data
  },

  /**
   * 生成个性化话题
   */
  async generatePersonalizedTopics(
    user_id: string,
    target_user_id: string,
    interests?: string[]
  ): Promise<{ success: boolean; topics: any[] }> {
    const response = await apiClient.post('/api/icebreaker-topics/generate', {
      user_id,
      target_user_id,
      interests,
    })
    return response.data
  },

  /**
   * 反馈话题效果
   */
  async feedbackTopicEffect(
    topic_id: string,
    effectiveness: 'good' | 'neutral' | 'bad',
    notes?: string
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post(`/api/icebreaker-topics/feedback/${topic_id}`, {
      effectiveness,
      notes,
    })
    return response.data
  },
}

// ==================== 情感调解 API ====================

export const emotionMediationApi = {
  /**
   * 检测情感冲突
   */
  async detectConflict(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; conflict_detected: boolean; severity?: string }> {
    const response = await apiClient.get(`/api/emotion-mediation/detect/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 开始调解
   */
  async startMediation(
    user_a_id: string,
    user_b_id: string,
    conflict_type: string
  ): Promise<{ success: boolean; mediation_id: string }> {
    const response = await apiClient.post('/api/emotion-mediation/start', {
      user_a_id,
      user_b_id,
      conflict_type,
    })
    return response.data
  },

  /**
   * 获取调解建议
   */
  async getMediationSuggestions(
    mediation_id: string
  ): Promise<{ success: boolean; suggestions: any[] }> {
    const response = await apiClient.get(`/api/emotion-mediation/suggestions/${mediation_id}`)
    return response.data
  },

  /**
   * 完成调解
   */
  async completeMediation(
    mediation_id: string,
    outcome: 'resolved' | 'partial' | 'escalated',
    notes?: string
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post(`/api/emotion-mediation/complete/${mediation_id}`, {
      outcome,
      notes,
    })
    return response.data
  },
}

// ==================== 爱之语翻译 API ====================

export const loveLanguageTranslationApi = {
  /**
   * 分析用户爱之语类型
   */
  async analyzeLoveLanguage(
    user_id: string
  ): Promise<{ success: boolean; love_language: string; scores: Record<string, number> }> {
    const response = await apiClient.get(`/api/love-language-translation/analyze/${user_id}`)
    return response.data
  },

  /**
   * 翻译表达方式
   */
  async translateExpression(
    from_user_id: string,
    to_user_id: string,
    original_expression: string
  ): Promise<{ success: boolean; translated_expression: string }> {
    const response = await apiClient.post('/api/love-language-translation/translate', {
      from_user_id,
      to_user_id,
      original_expression,
    })
    return response.data
  },

  /**
   * 获取爱之语建议
   */
  async getLoveLanguageSuggestions(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; suggestions: any[] }> {
    const response = await apiClient.get(`/api/love-language-translation/suggestions/${user_a_id}/${user_b_id}`)
    return response.data
  },
}

// ==================== 关系气象 API ====================

export const relationshipWeatherApi = {
  /**
   * 获取关系气象
   */
  async getWeather(
    user_a_id: string,
    user_b_id: string
  ): Promise<{ success: boolean; weather: { status: string; temperature: number; forecast: any } }> {
    const response = await apiClient.get(`/api/relationship-weather/${user_a_id}/${user_b_id}`)
    return response.data
  },

  /**
   * 更新气象因素
   */
  async updateWeatherFactors(
    user_a_id: string,
    user_b_id: string,
    factors: Record<string, number>
  ): Promise<{ success: boolean }> {
    const response = await apiClient.post('/api/relationship-weather/update', {
      user_a_id,
      user_b_id,
      factors,
    })
    return response.data
  },

  /**
   * 获取气象预报
   */
  async getWeatherForecast(
    user_a_id: string,
    user_b_id: string,
    days: number = 7
  ): Promise<{ success: boolean; forecast: any[] }> {
    const response = await apiClient.get(`/api/relationship-weather/forecast/${user_a_id}/${user_b_id}`, {
      params: { days },
    })
    return response.data
  },
}