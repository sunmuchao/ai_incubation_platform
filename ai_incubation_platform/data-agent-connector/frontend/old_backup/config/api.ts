/**
 * API 配置
 */
export const API_CONFIG = {
  baseURL: '/api',
  timeout: 30000,
}

/**
 * API 端点定义
 */
export const API_ENDPOINTS = {
  // 查询相关
  QUERY_EXECUTE: '/query/execute',
  QUERY_NL: '/query/nl-query',
  QUERY_SOURCES: '/query/sources',
  QUERY_REFRESH_SCHEMA: '/query/refresh-schema',
  QUERY_LINEAGE: '/lineage',

  // 连接器相关
  CONNECTORS_TYPES: '/connectors/types',
  CONNECTORS_ACTIVE: '/connectors/active',
  CONNECTORS_CONNECT: '/connectors/{connector_id}/connect',
  CONNECTORS_DISCONNECT: '/connectors/{connector_id}/disconnect',
  CONNECTORS_SCHEMA: '/connectors/{name}/schema',

  // AI 查询相关
  AI_QUERY: '/ai/query',
  AI_QUERY_V2: '/ai/query/v2',
  AI_INTENT: '/ai/intent',
  AI_EXPLAIN: '/ai/explain',
  AI_OPTIMIZE: '/ai/optimize',
  AI_HISTORY: '/ai/history',
  AI_EXAMPLES: '/ai/examples',
  AI_EVALUATE: '/ai/evaluate',

  // 血缘相关
  LINEAGE_NODES: '/lineage/nodes',
  LINEAGE_GRAPH: '/lineage/graph',
  LINEAGE_IMPACT: '/lineage/impact',
  LINEAGE_LINEAGE: '/lineage/lineage',
  LINEAGE_HISTORY: '/lineage/history',
  LINEAGE_STATISTICS: '/lineage/statistics',

  // 数据治理相关
  GOVERNANCE_CLASSIFICATIONS: '/governance/classifications',
  GOVERNANCE_LABELS: '/governance/labels',
  GOVERNANCE_SENSITIVE: '/governance/scan-sensitive',
  GOVERNANCE_MASKING: '/governance/masking-policies',
  GOVERNANCE_SCORE: '/governance/score',
  GOVERNANCE_DASHBOARD: '/governance/dashboard',

  // 监控相关
  MONITORING_METRICS: '/monitoring/metrics',
  MONITORING_ALERTS: '/monitoring/alerts',
  MONITORING_DASHBOARD: '/monitoring/dashboard',

  // 日志相关
  LOGS_AUDIT: '/logs/audit',
  LOGS_QUERY: '/logs/query',
  LOGS_ACCESS: '/logs/access',
  LOGS_STATISTICS: '/logs/statistics',

  // RBAC 权限相关
  RBAC_ROLES: '/rbac/roles',
  RBAC_USERS: '/rbac/users',
  RBAC_AUDIT: '/rbac/audit',
  RBAC_CHECK: '/rbac/check',
}
