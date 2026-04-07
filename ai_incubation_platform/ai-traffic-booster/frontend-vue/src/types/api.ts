/**
 * API 类型定义
 */

// 通用响应类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页响应
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// 流量数据
export interface TrafficData {
  date: string
  visitors: number
  page_views: number
  sessions: number
  bounce_rate: number
  avg_session_duration: number
}

// 流量趋势数据（含异常标注）
export interface TrafficTrendPoint extends TrafficData {
  is_anomaly?: boolean
  anomaly_type?: 'spike' | 'drop'
  anomaly_score?: number
  root_cause?: string
}

// SEO 数据
export interface SEOMetrics {
  keyword: string
  position: number
  previous_position: number
  change: number
  search_volume: number
  difficulty: number
  url: string
}

// 竞品数据
export interface CompetitorData {
  domain: string
  metrics: {
    traffic_volume: number
    domain_authority: number
    content_quality: number
    backlinks: number
    keyword_coverage: number
    social_presence: number
  }
}

// AI 洞察
export interface AIInsight {
  type: 'opportunity' | 'risk' | 'alert'
  title: string
  description: string
  suggestion: string
  impact: '高' | '中' | '低'
  confidence: number
}

// 查询历史
export interface QueryHistory {
  query_id: string
  session_id: string
  query_text: string
  intent: string
  data: any
  interpretation: string
  suggestions: string[]
  created_at: string
}

// 告警数据
export interface AlertData {
  alert_id: string
  type: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  created_at: string
  acknowledged: boolean
}

// 数据源状态
export interface DataSource {
  source_id: string
  name: string
  type: string
  status: 'healthy' | 'warning' | 'error'
  last_sync: string
  quota_used: number
  quota_limit: number
}

// 自动化任务
export interface AutomationTask {
  task_id: string
  name: string
  type: string
  status: 'active' | 'paused' | 'completed'
  schedule: string
  last_run: string
  next_run: string
}
