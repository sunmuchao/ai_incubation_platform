/**
 * AI Native API 服务层
 * 对接后端 AI Native API
 */

import axios from 'axios';
import type {
  Alert,
  ServiceHealth,
  AgentTool,
  WorkflowExecution,
  AIDashboardResponse,
  AIDiagnoseResponse,
  AIAskResponse,
  AutonomousLoopResult,
  RecommendedAction,
} from '@/types';

const API_BASE = '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // AI operations may take longer
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// AI Native API - 核心对话和诊断
// ============================================================================

export const aiNativeApi = {
  /**
   * 自然语言问答
   */
  ask: async (question: string, context?: Record<string, unknown>): Promise<AIAskResponse> => {
    const response = await apiClient.post<AIAskResponse>('/ai/ask', { question, context });
    return {
      ...response.data,
      confidence: response.data.confidence || 0.8,
    };
  },

  /**
   * AI 深度诊断
   */
  diagnose: async (
    service?: string,
    symptoms?: string[],
    timeWindow = 300
  ): Promise<AIDiagnoseResponse> => {
    const response = await apiClient.post<AIDiagnoseResponse>('/ai/diagnose', {
      service,
      symptoms,
      time_window: timeWindow,
    });
    return response.data;
  },

  /**
   * 自主修复
   */
  remediate: async (
    diagnosisId?: string,
    action?: Record<string, unknown>,
    autoApprove = false
  ): Promise<{
    success: boolean;
    action_name: string;
    details: Record<string, unknown>;
    validation_result?: Record<string, unknown>;
    rollback_performed: boolean;
  }> => {
    const response = await apiClient.post('/ai/remediate', {
      diagnosis_id: diagnosisId,
      action,
      auto_approve: autoApprove,
    });
    return response.data;
  },

  /**
   * 优化建议
   */
  optimize: async (
    service?: string,
    goals?: string[],
    autoExecute = false
  ): Promise<{
    success: boolean;
    optimization_name: string;
    recommendations: RecommendedAction[];
    pr_url?: string;
  }> => {
    const response = await apiClient.post('/ai/optimize', {
      service,
      goals,
      auto_execute: autoExecute,
    });
    return response.data;
  },

  /**
   * 动态仪表板
   */
  getDashboard: async (
    service?: string,
    focus?: string
  ): Promise<AIDashboardResponse> => {
    const response = await apiClient.get<AIDashboardResponse>('/ai/dashboard', {
      params: { service, focus },
    });
    return response.data;
  },

  /**
   * 自主运维循环
   */
  autonomousLoop: async (
    service?: string,
    autoExecute = true
  ): Promise<AutonomousLoopResult> => {
    const response = await apiClient.post<AutonomousLoopResult>('/ai/autonomous-loop', {
      service,
      auto_execute: autoExecute,
    });
    return response.data;
  },

  /**
   * 获取可用工具列表
   */
  getTools: async (): Promise<AgentTool[]> => {
    const response = await apiClient.get<{ tools: AgentTool[] }>('/ai/tools');
    return response.data.tools;
  },

  /**
   * 调用工具
   */
  invokeTool: async (
    toolName: string,
    parameters: Record<string, unknown>
  ): Promise<{ success: boolean; result: unknown }> => {
    const response = await apiClient.post(`/ai/tools/${toolName}/invoke`, parameters);
    return response.data;
  },
};

// ============================================================================
// 可观测性 API v2.4
// ============================================================================

export const observabilityApi = {
  getOverview: async () => {
    const response = await apiClient.get('/observability/v2.4/overview');
    return response.data;
  },

  getDashboard: async () => {
    const response = await apiClient.get('/observability/v2.4/dashboard/main');
    return response.data;
  },

  getServices: async (): Promise<{ services: Record<string, ServiceHealth> }> => {
    const response = await apiClient.get('/observability/v2.4/services');
    return response.data;
  },

  getServiceHealth: async (serviceName: string): Promise<ServiceHealth> => {
    const response = await apiClient.get(`/observability/v2.4/services/${serviceName}`);
    return response.data;
  },

  searchLogs: async (params: {
    service_name?: string;
    level?: string;
    trace_id?: string;
    query?: string;
    limit?: number;
  }) => {
    const response = await apiClient.post('/observability/v2.4/logs/search', params);
    return response.data;
  },

  getErrorPatterns: async (limit = 20) => {
    const response = await apiClient.get('/observability/v2.4/logs/error-patterns', {
      params: { limit },
    });
    return response.data;
  },

  correlateTrace: async (traceId: string) => {
    const response = await apiClient.post('/observability/v2.4/correlate', {
      trace_id: traceId,
      include_logs: true,
      include_metrics: true,
    });
    return response.data;
  },
};

// ============================================================================
// AI 优化建议 API v2.5
// ============================================================================

export const optimizationApi = {
  getOverview: async () => {
    const response = await apiClient.get('/optimization/v2.5/dashboard/overview');
    return response.data;
  },

  getBottlenecks: async (params?: { service_name?: string; severity?: string }) => {
    const response = await apiClient.get('/optimization/v2.5/bottlenecks', { params });
    return response.data;
  },

  getRecommendations: async (params?: {
    service_name?: string;
    category?: string;
    priority?: string;
    limit?: number;
  }) => {
    const response = await apiClient.get('/optimization/v2.5/recommendations', { params });
    return response.data;
  },

  quickDiagnosis: async (serviceName: string) => {
    const response = await apiClient.get(
      `/optimization/v2.5/quick-diagnosis/${serviceName}`
    );
    return response.data;
  },

  getCostAnalysis: async (serviceName: string) => {
    const response = await apiClient.get(`/optimization/v2.5/cost-analysis/${serviceName}`);
    return response.data;
  },
};

// ============================================================================
// 告警 API
// ============================================================================

export const alertApi = {
  getAlerts: async (): Promise<{ alerts: Alert[] }> => {
    const response = await apiClient.get('/runtime/alerts');
    return response.data;
  },

  acknowledgeAlert: async (alertId: string) => {
    const response = await apiClient.post(`/runtime/alerts/${alertId}/acknowledge`);
    return response.data;
  },
};

// ============================================================================
// Agent 状态 API
// ============================================================================

export const agentApi = {
  /**
   * 获取 Agent 状态
   */
  getState: async (): Promise<{ state: unknown[] }> => {
    // 临时实现 - 后端需要提供此 API
    return {
      state: [
        {
          name: 'Perception Agent',
          status: 'idle',
          last_activity: new Date(),
        },
        {
          name: 'Diagnosis Agent',
          status: 'idle',
          last_activity: new Date(),
        },
        {
          name: 'Remediation Agent',
          status: 'idle',
          last_activity: new Date(),
        },
        {
          name: 'Optimization Agent',
          status: 'idle',
          last_activity: new Date(),
        },
      ],
    };
  },

  /**
   * 获取工作流执行状态
   */
  getWorkflowStatus: async (): Promise<{ workflows: WorkflowExecution[] }> => {
    // 临时实现
    return { workflows: [] };
  },
};

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 将后端时间字符串转换为 Date 对象
 */
export const parseDate = (dateString: string): Date => {
  return new Date(dateString);
};

/**
 * 格式化置信度分数
 */
export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(0)}%`;
};

/**
 * 获取严重性颜色
 */
export const getSeverityColor = (severity: string): string => {
  const colors: Record<string, string> = {
    low: '#52c41a',
    medium: '#faad14',
    high: '#ff7a45',
    critical: '#ff4d4f',
  };
  return colors[severity.toLowerCase()] || '#d9d9d9';
};

/**
 * 获取健康状态颜色
 */
export const getHealthColor = (status: string): string => {
  const colors: Record<string, string> = {
    healthy: '#52c41a',
    warning: '#faad14',
    critical: '#ff4d4f',
    unknown: '#d9d9d9',
  };
  return colors[status.toLowerCase()] || '#d9d9d9';
};

export default apiClient;
