/**
 * 应用路由配置
 */
export const ROUTES = {
  // 首页
  DASHBOARD: '/',

  // 连接器管理
  CONNECTORS: '/connectors',
  CONNECTOR_DETAIL: '/connectors/:id',

  // 数据查询
  DATA_QUERY: '/query',
  SQL_EDITOR: '/query/sql',
  QUERY_HISTORY: '/query/history',

  // 血缘图谱
  LINEAGE: '/lineage',
  LINEAGE_GRAPH: '/lineage/graph',

  // 数据治理
  GOVERNANCE: '/governance',
  GOVERNANCE_CLASSIFICATION: '/governance/classification',
  GOVERNANCE_SENSITIVE: '/governance/sensitive',
  GOVERNANCE_MASKING: '/governance/masking',

  // 权限管理
  PERMISSIONS: '/permissions',
  PERMISSIONS_ROLES: '/permissions/roles',
  PERMISSIONS_USERS: '/permissions/users',
  PERMISSIONS_AUDIT: '/permissions/audit',

  // API 管理
  API_MANAGEMENT: '/api',
  API_DOCS: '/api/docs',
  API_KEYS: '/api/keys',
  API_USAGE: '/api/usage',

  // 监控中心
  MONITORING: '/monitoring',
  MONITORING_METRICS: '/monitoring/metrics',
  MONITORING_ALERTS: '/monitoring/alerts',

  // 日志审计
  LOGS: '/logs',
  LOGS_AUDIT: '/logs/audit',
  LOGS_QUERY: '/logs/query',

  // 连接器市场
  MARKETPLACE: '/marketplace',

  // 管理后台
  ADMIN: '/admin',
}
