/**
 * 数据源/连接器类型定义
 */
export interface DataSource {
  name: string
  connector_type: string
  datasource_name: string
  status: 'connected' | 'disconnected' | 'error'
  created_at?: string
  updated_at?: string
}

export interface ConnectorType {
  name: string
  display_name: string
  description: string
  icon: string
  category: 'database' | 'warehouse' | 'nosql' | 'api' | 'file' | 'message'
}

export interface ConnectorSchema {
  tables: SchemaTable[]
}

export interface SchemaTable {
  name: string
  columns: SchemaColumn[]
  primary_key?: string[]
  indexes?: SchemaIndex[]
}

export interface SchemaColumn {
  name: string
  type: string
  nullable: boolean
  default?: any
  comment?: string
  is_primary?: boolean
  is_foreign?: boolean
  references?: {
    table: string
    column: string
  }
}

export interface SchemaIndex {
  name: string
  columns: string[]
  unique: boolean
}

/**
 * 查询相关类型
 */
export interface QueryRequest {
  connector_name: string
  query: string
  params?: Record<string, any>
}

export interface QueryResponse {
  success: boolean
  data: any[]
  execution_time_ms: number
  operation_type: string
  rows_returned: number
  error?: string
}

export interface NLQueryRequest {
  connector_name: string
  natural_language: string
}

export interface AIQueryRequest {
  connector_name: string
  natural_language: string
  use_llm?: boolean
  use_enhanced?: boolean
  enable_self_correction?: boolean
}

export interface AIQueryResponse {
  success: boolean
  sql: string
  intent: Record<string, any>
  confidence: number
  validation: Record<string, any>
  suggestions: string[]
  data?: any[]
  explanation?: string
  execution_time_ms?: number
  clarification?: {
    is_ambiguous: boolean
    options: string[]
    question: string
  }
}

/**
 * 血缘相关类型
 */
export interface LineageNode {
  id: string
  name: string
  type: 'table' | 'column' | 'view' | 'query'
  datasource: string
  schema_name?: string
  table_name?: string
  column_name?: string
  created_at?: string
  updated_at?: string
  metadata?: Record<string, any>
}

export interface LineageEdge {
  id: string
  source_id: string
  target_id: string
  operation: string
  created_at?: string
  metadata?: Record<string, any>
}

export interface LineageGraph {
  nodes: LineageNode[]
  edges: LineageEdge[]
  center_node?: string
  direction?: 'upstream' | 'downstream' | 'both'
}

export interface LineageStatistics {
  total_nodes: number
  total_edges: number
  nodes_by_type: Record<string, number>
  nodes_by_datasource: Record<string, number>
}

/**
 * 数据治理相关类型
 */
export interface Classification {
  id: string
  name: string
  description?: string
  parent_id?: string
  level: number
  tags?: string[]
  children?: Classification[]
  created_at?: string
}

export interface DataLabel {
  id: string
  datasource: string
  table_name: string
  column_name?: string
  label_type: 'classification' | 'sensitivity' | 'business' | 'custom'
  label_key: string
  label_value?: string
  created_at?: string
}

export interface SensitiveRecord {
  id: string
  datasource: string
  table_name: string
  column_name: string
  sensitivity_level: 'high' | 'medium' | 'low'
  pattern_type: string
  sample_value?: string
  is_masked: boolean
  is_reviewed: boolean
  reviewed_by?: string
  reviewed_at?: string
}

export interface MaskingPolicy {
  id: string
  name: string
  description?: string
  masking_type: 'full' | 'partial' | 'hash' | 'encrypt' | 'redact'
  sensitivity_level?: string
  data_type?: string
  column_pattern?: string
  priority: number
  masking_params?: Record<string, any>
  created_at?: string
}

export interface GovernanceScore {
  overall_score: number
  classification_coverage: number
  sensitivity_coverage: number
  masking_coverage: number
  lineage_coverage: number
  quality_score: number
}

/**
 * 监控告警类型
 */
export interface MetricData {
  name: string
  value: number
  timestamp: string
  tags?: Record<string, string>
  unit?: string
}

export interface AlertRule {
  id: string
  name: string
  description?: string
  metric_name: string
  operator: '>' | '<' | '>=' | '<=' | '==' | '!='
  threshold: number
  duration_seconds: number
  severity: 'critical' | 'warning' | 'info'
  notify_channels: string[]
  notify_receivers: string[]
  enabled: boolean
  silenced: boolean
  silenced_until?: string
  created_at?: string
}

export interface Alert {
  id: string
  rule_id: string
  rule_name: string
  status: 'firing' | 'resolved' | 'acknowledged'
  severity: 'critical' | 'warning' | 'info'
  triggered_at: string
  resolved_at?: string
  acknowledged_at?: string
  acknowledged_by?: string
  metric_value: number
  threshold: number
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  active_connections: number
  max_connections: number
  current_qps: number
  current_concurrent: number
  total_lineage_nodes: number
  total_lineage_edges: number
}

/**
 * RBAC 权限类型
 */
export interface Role {
  name: string
  description?: string
  permissions: string[]
  created_at?: string
}

export interface User {
  id: string
  name: string
  email?: string
  roles: string[]
  permissions: string[]
  created_at?: string
}

export interface PermissionCheck {
  user_id: string
  resource: string
  operation: string
  has_permission: boolean
  reason?: string
}

/**
 * 日志类型
 */
export interface AuditLog {
  id: string
  tenant_id?: string
  user_id: string
  action_type: string
  resource_type: string
  resource_id?: string
  action: string
  details?: Record<string, any>
  ip_address?: string
  user_agent?: string
  created_at: string
}

export interface QueryLog {
  id: string
  user_id: string
  connector_name: string
  query: string
  status: 'success' | 'error' | 'timeout'
  execution_time_ms: number
  rows_returned: number
  error_message?: string
  created_at: string
}

export interface AccessLog {
  id: string
  user_id: string
  resource: string
  action: string
  granted: boolean
  reason?: string
  created_at: string
}

/**
 * 仪表盘数据类型
 */
export interface DashboardSummary {
  total_datasources: number
  active_connectors: number
  total_queries_24h: number
  avg_query_latency_ms: number
  total_lineage_nodes: number
  governance_score: number
  active_alerts: number
  error_rate_24h: number
}

export interface ChartData {
  name: string
  value: number
  timestamp?: string
}
