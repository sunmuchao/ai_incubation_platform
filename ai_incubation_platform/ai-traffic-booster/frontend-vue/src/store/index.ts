/**
 * Pinia Store 配置
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dashboardApi, alertsApi, dataSourcesApi, queryAssistantApi } from '@/api'

// ==================== 应用状态 ====================

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentTheme = ref('light')
  const loading = ref(false)

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const setTheme = (theme: string) => {
    currentTheme.value = theme
    localStorage.setItem('theme', theme)
  }

  const setLoading = (value: boolean) => {
    loading.value = value
  }

  return {
    sidebarCollapsed,
    currentTheme,
    loading,
    toggleSidebar,
    setTheme,
    setLoading,
  }
})

// ==================== 仪表板状态 ====================

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref<any>(null)
  const insights = ref<any[]>([])
  const trafficTrend = ref<any[]>([])
  const keywordHeatmap = ref<any[]>([])
  const competitorRadar = ref<any[]>([])

  const fetchOverview = async () => {
    try {
      const res = await dashboardApi.getOverview()
      overview.value = res.data
    } catch (error) {
      console.error('Failed to fetch overview:', error)
    }
  }

  const fetchInsights = async (startDate: string, endDate: string) => {
    try {
      const res = await dashboardApi.getInsights(startDate, endDate)
      insights.value = res.data.insights || []
    } catch (error) {
      console.error('Failed to fetch insights:', error)
    }
  }

  const fetchTrafficTrend = async (startDate: string, endDate: string) => {
    try {
      const res = await dashboardApi.getTrafficTrend(startDate, endDate)
      trafficTrend.value = res.data.trend || []
    } catch (error) {
      console.error('Failed to fetch traffic trend:', error)
    }
  }

  const fetchKeywordHeatmap = async (startDate: string, endDate: string, limit = 50) => {
    try {
      const res = await dashboardApi.getKeywordHeatmap(startDate, endDate, limit)
      keywordHeatmap.value = res.data.keywords || []
    } catch (error) {
      console.error('Failed to fetch keyword heatmap:', error)
    }
  }

  const fetchCompetitorRadar = async (domains: string[]) => {
    try {
      const res = await dashboardApi.getCompetitorRadar(domains)
      competitorRadar.value = res.data.competitors || []
    } catch (error) {
      console.error('Failed to fetch competitor radar:', error)
    }
  }

  const anomalyCount = computed(() => {
    return trafficTrend.value.filter((item) => item.is_anomaly).length
  })

  return {
    overview,
    insights,
    trafficTrend,
    keywordHeatmap,
    competitorRadar,
    fetchOverview,
    fetchInsights,
    fetchTrafficTrend,
    fetchKeywordHeatmap,
    fetchCompetitorRadar,
    anomalyCount,
  }
})

// ==================== AI 助手状态 ====================

export const useAIAssistantStore = defineStore('aiAssistant', () => {
  const queries = ref<any[]>([])
  const favorites = ref<any[]>([])
  const templates = ref<any[]>([])
  const suggestions = ref<any[]>([])
  const currentSession = ref<string>('')
  const isChatLoading = ref(false)

  const userId = computed(() => localStorage.getItem('user_id') || 'guest')

  const initSession = () => {
    currentSession.value = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const sendMessage = async (queryText: string) => {
    if (!currentSession.value) {
      initSession()
    }

    isChatLoading.value = true
    try {
      const res = await queryAssistantApi.ask(queryText, userId.value, currentSession.value)
      const query = {
        query_id: res.data.query_id,
        query_text: queryText,
        response: res.data,
        created_at: new Date().toISOString(),
      }
      queries.value.unshift(query)
      return res.data
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    } finally {
      isChatLoading.value = false
    }
  }

  const fetchTemplates = async (category?: string) => {
    try {
      const res = await queryAssistantApi.getTemplates(category)
      templates.value = res.data.templates || []
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    }
  }

  const fetchSuggestions = async (context?: string) => {
    try {
      const res = await queryAssistantApi.getSuggestions(context)
      suggestions.value = res.data.suggestions || []
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
    }
  }

  const addToFavorites = async (queryId: string, queryText: string, customName?: string) => {
    try {
      await queryAssistantApi.addFavorite(queryId, queryText, userId.value, customName)
      await fetchFavorites()
    } catch (error) {
      console.error('Failed to add to favorites:', error)
    }
  }

  const fetchFavorites = async () => {
    try {
      const res = await queryAssistantApi.getFavorites(userId.value)
      favorites.value = res.data.favorites || []
    } catch (error) {
      console.error('Failed to fetch favorites:', error)
    }
  }

  return {
    queries,
    favorites,
    templates,
    suggestions,
    currentSession,
    isChatLoading,
    userId,
    initSession,
    sendMessage,
    fetchTemplates,
    fetchSuggestions,
    addToFavorites,
    fetchFavorites,
  }
})

// ==================== 告警状态 ====================

export const useAlertStore = defineStore('alert', () => {
  const alerts = ref<any[]>([])
  const unreadCount = ref(0)

  const fetchAlerts = async (status?: string) => {
    try {
      const res = await alertsApi.getAlerts(status)
      alerts.value = res.data.alerts || []
      unreadCount.value = alerts.value.filter((a) => !a.acknowledged).length
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    }
  }

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await alertsApi.acknowledgeAlert(alertId, localStorage.getItem('user_id') || 'guest')
      await fetchAlerts()
    } catch (error) {
      console.error('Failed to acknowledge alert:', error)
    }
  }

  return {
    alerts,
    unreadCount,
    fetchAlerts,
    acknowledgeAlert,
  }
})

// ==================== 数据源状态 ====================

export const useDataSourceStore = defineStore('dataSource', () => {
  const sources = ref<any[]>([])
  const healthStatus = ref<any>(null)

  const fetchSources = async () => {
    try {
      const res = await dataSourcesApi.getDataSources()
      sources.value = res.data.sources || []
    } catch (error) {
      console.error('Failed to fetch data sources:', error)
    }
  }

  const fetchHealth = async () => {
    try {
      const res = await dataSourcesApi.getHealth()
      healthStatus.value = res.data
    } catch (error) {
      console.error('Failed to fetch health status:', error)
    }
  }

  return {
    sources,
    healthStatus,
    fetchSources,
    fetchHealth,
  }
})
