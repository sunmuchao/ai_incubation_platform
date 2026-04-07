import axios from 'axios';
import type {
  DashboardOverview,
  Service,
  Alert,
  LogEntry,
  Bottleneck,
  Recommendation,
  HealthScore,
  RootCause,
  PredictiveAlert,
  ExecutionRecord,
} from '@/types';

const API_BASE = '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 可观测性 API v2.4
export const observabilityApi = {
  getOverview: () =>
    apiClient.get<{ overview: DashboardOverview }>('/observability/v2.4/overview'),

  getDashboard: () =>
    apiClient.get<DashboardOverview>('/observability/v2.4/dashboard/main'),

  getServices: () =>
    apiClient.get<{ services: Record<string, Service> }>('/observability/v2.4/services'),

  getServiceHealth: (serviceName: string) =>
    apiClient.get<HealthScore>(`/observability/v2.4/services/${serviceName}`),

  searchLogs: (params: {
    service_name?: string;
    level?: string;
    trace_id?: string;
    query?: string;
    limit?: number;
  }) => apiClient.post<{ logs: LogEntry[] }>('/observability/v2.4/logs/search', params),

  getErrorPatterns: (limit = 20) =>
    apiClient.get<{ patterns: unknown[] }>('/observability/v2.4/logs/error-patterns', {
      params: { limit },
    }),

  correlateTrace: (trace_id: string) =>
    apiClient.post('/observability/v2.4/correlate', { trace_id, include_logs: true, include_metrics: true }),
};

// AI 优化建议 API v2.5
export const optimizationApi = {
  getOverview: () =>
    apiClient.get<{ summary: unknown; category_breakdown: Record<string, number> }>('/optimization/v2.5/dashboard/overview'),

  getBottlenecks: (params?: { service_name?: string; severity?: string }) =>
    apiClient.get<{ bottlenecks: Bottleneck[] }>('/optimization/v2.5/bottlenecks', { params }),

  getRecommendations: (params?: {
    service_name?: string;
    category?: string;
    priority?: string;
    limit?: number;
  }) =>
    apiClient.get<{ recommendations: Recommendation[] }>('/optimization/v2.5/recommendations', { params }),

  quickDiagnosis: (serviceName: string) =>
    apiClient.get<{ health_score: number; health_status: string; critical_issues: number }>(
      `/optimization/v2.5/quick-diagnosis/${serviceName}`
    ),

  getCostAnalysis: (serviceName: string) =>
    apiClient.get(`/optimization/v2.5/cost-analysis/${serviceName}`),
};

// 根因分析 API v2.2
export const rootCauseApi = {
  buildGraph: (serviceMapData?: unknown) =>
    apiClient.post('/root-cause/v2.2/build-graph', { service_map_data: serviceMapData }),

  analyze: (params: {
    evidence?: Record<string, unknown>;
    lookback_minutes?: number;
    include_counterfactual?: boolean;
    include_visualization?: boolean;
  }) =>
    apiClient.post<{
      analysis_id: string;
      summary: string;
      root_causes: RootCause[];
      confidence_level: string;
      recommendations: string[];
      visualization?: Record<string, unknown>;
    }>('/root-cause/v2.2/analyze', params),

  getCausalGraph: () =>
    apiClient.get('/root-cause/v2.2/graph'),

  getHypotheses: (limit = 10) =>
    apiClient.get<{ hypotheses: RootCause[] }>('/root-cause/v2.2/hypotheses', { params: { limit } }),
};

// 预测性维护 API v2.3
export const predictiveMaintenanceApi = {
  getDashboard: () =>
    apiClient.get<{
      summary: Record<string, unknown>;
      health_scores: HealthScore[];
      active_alerts: PredictiveAlert[];
      rul_predictions: unknown[];
    }>('/predictive-maintenance/v2.3/dashboard'),

  getHealthScores: () =>
    apiClient.get<HealthScore[]>('/predictive-maintenance/v2.3/health'),

  getServiceHealth: (serviceName: string) =>
    apiClient.get<HealthScore>(`/predictive-maintenance/v2.3/health/${serviceName}`),

  getActiveAlerts: (params?: { service_name?: string; priority?: string; limit?: number }) =>
    apiClient.get<PredictiveAlert[]>('/predictive-maintenance/v2.3/alerts', { params }),

  getRulPredictions: () =>
    apiClient.get<unknown[]>('/predictive-maintenance/v2.3/rul'),
};

// 自主修复 API v2.1
export const remediationApi = {
  execute: (params: {
    script_id: string;
    service_id: string;
    parameters?: Record<string, unknown>;
    require_approval?: boolean;
  }) =>
    apiClient.post<ExecutionRecord>('/remediation/v2.1/execute', params),

  getExecutions: (service_id?: string) =>
    apiClient.get<{ executions: ExecutionRecord[] }>('/remediation/v2.1/executions', {
      params: { service_id },
    }),

  getExecution: (execution_id: string) =>
    apiClient.get<ExecutionRecord>(`/remediation/v2.1/executions/${execution_id}`),

  getApprovalRequests: (status?: string) =>
    apiClient.get<{ requests: unknown[] }>('/remediation/v2.1/approvals', { params: { status } }),

  approveRequest: (request_id: string, approver: string) =>
    apiClient.post(`/remediation/v2.1/approval/${request_id}/approve`, { request_id, approver, action: 'approve' }),

  rejectRequest: (request_id: string, approver: string, reason: string) =>
    apiClient.post(`/remediation/v2.1/approval/${request_id}/reject`, {
      request_id,
      approver,
      action: 'reject',
      reason,
    }),

  createSnapshot: (params: {
    service_id: string;
    service_type?: string;
    config?: Record<string, unknown>;
  }) => apiClient.post('/remediation/v2.1/snapshots', params),

  rollback: (snapshot_id: string) =>
    apiClient.post('/remediation/v2.1/rollback', { snapshot_id }),
};

// 告警 API
export const alertApi = {
  getAlerts: () =>
    apiClient.get<{ alerts: Alert[] }>('/runtime/alerts'),

  acknowledgeAlert: (alert_id: string) =>
    apiClient.post(`/runtime/alerts/${alert_id}/acknowledge`),
};

export default apiClient;
