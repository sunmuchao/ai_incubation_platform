/**
 * API 服务层
 */
import { http } from '@/utils/http'
import type {
  ApiResponse,
  TrafficData,
  TrafficTrendPoint,
  AIInsight,
  CompetitorData,
  QueryHistory,
  AlertData,
  DataSource,
} from '@/types/api'

// ==================== 仪表板 API ====================

export const dashboardApi = {
  /** 获取仪表板概览 */
  getOverview: () => http.get<ApiResponse>('/dashboard/overview'),

  /** 获取 AI 洞察 */
  getInsights: (startDate: string, endDate: string, domain?: string) =>
    http.get<ApiResponse>('/dashboard/insights', { start_date: startDate, end_date: endDate, domain }),

  /** 获取流量趋势（含异常标注） */
  getTrafficTrend: (startDate: string, endDate: string) =>
    http.get<ApiResponse<{ trend: TrafficTrendPoint[] }>>('/dashboard/traffic/trend/enhanced', {
      start_date: startDate,
      end_date: endDate,
    }),

  /** 获取关键词热力图 */
  getKeywordHeatmap: (startDate: string, endDate: string, limit = 50) =>
    http.get<ApiResponse>('/dashboard/heatmap/keywords', {
      start_date: startDate,
      end_date: endDate,
      limit,
    }),

  /** 获取竞品雷达图数据 */
  getCompetitorRadar: (domains: string[]) =>
    http.get<ApiResponse<{ competitors: CompetitorData[]; dimensions: string[] }>>(
      '/dashboard/competitors/radar',
      { domains: domains.join(',') }
    ),

  /** 导出数据 */
  exportData: (data: {
    export_type: string
    format: string
    start_date: string
    end_date: string
    include_charts: boolean
    include_insights: boolean
  }) => http.post<ApiResponse>('/dashboard/export/enhanced', data),
}

// ==================== AI 查询助手 API ====================

export const queryAssistantApi = {
  /** 自然语言查询 */
  ask: (queryText: string, userId?: string, sessionId?: string) =>
    http.post<ApiResponse>('/ai/query/ask', { query_text: queryText, user_id: userId, session_id: sessionId }),

  /** 获取查询历史 */
  getHistory: (sessionId: string, limit = 50) =>
    http.get<ApiResponse<{ queries: QueryHistory[] }>>(`/ai/query/history/session/${sessionId}`, { limit }),

  /** 获取用户查询历史 */
  getUserHistory: (userId: string, limit = 100) =>
    http.get<ApiResponse>(`/ai/query/history/user/${userId}`, { limit }),

  /** 获取收藏列表 */
  getFavorites: (userId: string) =>
    http.get<ApiResponse>(`/ai/query/favorites/${userId}`),

  /** 添加收藏 */
  addFavorite: (queryId: string, queryText: string, userId: string, customName?: string) =>
    http.post<ApiResponse>('/ai/query/favorites', {
      query_id: queryId,
      query_text: queryText,
      user_id: userId,
      custom_name: customName,
    }),

  /** 获取查询模板 */
  getTemplates: (category?: string) =>
    http.get<ApiResponse>('/ai/query/templates', { category }),

  /** 获取推荐查询 */
  getSuggestions: (context?: string) =>
    http.get<ApiResponse>('/ai/query/suggestions', { context }),

  /** 生成报告 */
  generateReport: (reportTitle: string, reportType: string, queryIds: string[], userId: string) =>
    http.post<ApiResponse>('/ai/query/report/generate', {
      report_title: reportTitle,
      report_type: reportType,
      query_ids: queryIds,
      user_id: userId,
    }),

  /** 获取用户报告列表 */
  getUserReports: (userId: string) =>
    http.get<ApiResponse>(`/ai/query/reports/${userId}`),
}

// ==================== 告警 API ====================

export const alertsApi = {
  /** 获取告警列表 */
  getAlerts: (status?: string, limit = 50) =>
    http.get<ApiResponse>('/alerts', { status, limit }),

  /** 确认告警 */
  acknowledgeAlert: (alertId: string, userId: string) =>
    http.post<ApiResponse>(`/alerts/${alertId}/acknowledge`, { user_id: userId }),

  /** 创建告警规则 */
  createAlert: (data: {
    name: string
    metric: string
    condition: string
    threshold: number
    notification_channels: string[]
  }) => http.post<ApiResponse>('/alerts', data),
}

// ==================== 数据源 API ====================

export const dataSourcesApi = {
  /** 获取数据源列表 */
  getDataSources: () => http.get<ApiResponse<{ sources: DataSource[] }>>('/data-sources'),

  /** 获取健康状态 */
  getHealth: () => http.get<ApiResponse>('/data-sources/health'),

  /** 获取配额状态 */
  getQuota: (sourceId: string) =>
    http.get<ApiResponse>(`/data-sources/quota/${sourceId}`),

  /** 导出数据 */
  export: (format: 'csv' | 'excel') =>
    http.get<Blob>('/data-sources/export', { format }),
}

// ==================== SEO 分析 API ====================

export const seoApi = {
  /** 获取关键词排名 */
  getRankings: (domain: string, limit = 100) =>
    http.get<ApiResponse>('/seo/rankings', { domain, limit }),

  /** 获取 SEO 审计结果 */
  getAudit: (url: string) =>
    http.get<ApiResponse>('/seo/audit', { url }),

  /** 获取竞品对比 */
  getComparison: (domains: string[]) =>
    http.get<ApiResponse>('/seo/comparison', { domains: domains.join(',') }),
}

// ==================== 竞品分析 API ====================

export const competitorApi = {
  /** 追踪竞品 */
  track: (domains: string[]) =>
    http.post<ApiResponse>('/competitor/track', { domains }),

  /** 获取竞品对比 */
  comparison: (domains: string[]) =>
    http.get<ApiResponse>('/competitor/comparison', { domains: domains.join(',') }),

  /** 获取市场份额 */
  getMarketShare: (industry?: string) =>
    http.get<ApiResponse>('/competitor/market-share', { industry }),

  /** 获取竞品策略 */
  getStrategy: (domain: string) =>
    http.get<ApiResponse>(`/competitor/strategy/${domain}`),

  /** 获取竞品告警 */
  getAlerts: () => http.get<ApiResponse>('/competitor/alerts'),

  /** 获取竞品洞察 */
  getInsights: () => http.get<ApiResponse>('/competitor/insights'),
}

// ==================== AI 自动化优化 API ====================

export const aiOptimizationApi = {
  /** 生成 A/B 测试设计 */
  generateABTestDesign: (rootCauses: any[], anomaly: any, context?: any) =>
    http.post<ApiResponse>('/ai-optimization/auto-ab-test/design', {
      root_causes: rootCauses,
      anomaly: anomaly,
      context: context,
    }),

  /** 执行 A/B 测试 */
  executeABTest: (testId: string, createdBy: string) =>
    http.post<ApiResponse>('/ai-optimization/auto-ab-test/execute', {
      test_id: testId,
      created_by: createdBy,
    }),

  /** 生成代码优化建议 */
  generateCodeSuggestions: (rootCauses: any[], anomaly: any, pageContent?: string, techStack?: any) =>
    http.post<ApiResponse>('/ai-optimization/code-optimizer/generate', {
      root_causes: rootCauses,
      anomaly: anomaly,
      page_content: pageContent,
      tech_stack: techStack,
    }),

  /** 获取学习洞察 */
  getLearningInsights: (suggestionType?: string, rootCauseCategory?: string, limit = 10) =>
    http.get<ApiResponse>('/ai-optimization/learning/insights', {
      suggestion_type: suggestionType,
      root_cause_category: rootCauseCategory,
      limit,
    }),
}

// ==================== 实时数据 API ====================

export const realtimeApi = {
  /** 获取实时访客 */
  getRealtimeVisitors: (minutes = 30) =>
    http.get<ApiResponse>('/realtime/visitors', { minutes }),

  /** 获取实时页面热度 */
  getHotPages: (limit = 10) =>
    http.get<ApiResponse>('/realtime/hot-pages', { limit }),

  /** 获取地理分布 */
  getGeoDistribution: () => http.get<ApiResponse>('/geo/distribution'),
}
