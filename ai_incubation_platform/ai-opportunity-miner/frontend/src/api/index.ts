/**
 * API 客户端 - 对接后端 AI Native 接口
 */
import axios from 'axios';
import type {
  BusinessOpportunity,
  ChatMessage,
  ChatData,
  AgentStatus,
  ToolSchema,
  Alert,
  DashboardOverview,
  MarketTrend,
} from '../types';

const API_BASE_URL = 'http://localhost:8006';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== Chat API ====================

export interface ChatRequest {
  query: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  query: string;
  intent: string;
  response: string;
  data?: ChatData;
  suggestions: string[];
}

/**
 * 发送对话消息
 */
export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await apiClient.post('/api/chat', request);
  return response.data;
};

/**
 * 获取支持的意图列表
 */
export const listIntents = async (): Promise<any> => {
  const response = await apiClient.get('/api/chat/intents');
  return response.data;
};

/**
 * 启用主动推送模式
 */
export const enableProactiveMode = async (
  keywords?: string[],
  industries?: string[],
  confidenceThreshold?: number
): Promise<any> => {
  const response = await apiClient.post('/api/chat/proactive', null, {
    params: {
      keywords: keywords?.join(','),
      industries: industries?.join(','),
      confidence_threshold: confidenceThreshold,
    },
  });
  return response.data;
};

/**
 * 获取智能建议
 */
export const getSuggestions = async (): Promise<any> => {
  const response = await apiClient.get('/api/chat/suggestions');
  return response.data;
};

// ==================== Opportunity API ====================

/**
 * 获取商机列表
 */
export const listOpportunities = async (status?: string): Promise<BusinessOpportunity[]> => {
  const response = await apiClient.get('/api/opportunities', {
    params: status ? { status } : {},
  });
  return response.data;
};

/**
 * 获取单个商机详情
 */
export const getOpportunity = async (oppId: string): Promise<BusinessOpportunity> => {
  const response = await apiClient.get(`/api/opportunities/${oppId}`);
  return response.data;
};

/**
 * AI 发现新商机
 */
export const discoverOpportunities = async (): Promise<any> => {
  const response = await apiClient.post('/api/opportunities/discover');
  return response.data;
};

/**
 * 根据关键词发现商机
 */
export const discoverByKeywords = async (keywords: string[], days?: number): Promise<any> => {
  const response = await apiClient.post('/api/opportunities/discover/keywords', {
    keywords,
    days,
  });
  return response.data;
};

/**
 * 根据行业发现商机
 */
export const discoverByIndustry = async (industry: string, days?: number): Promise<any> => {
  const response = await apiClient.post('/api/opportunities/discover/industry', {
    industry,
    days,
  });
  return response.data;
};

// ==================== Trend API ====================

/**
 * 获取市场趋势
 */
export const listTrends = async (minScore?: number): Promise<MarketTrend[]> => {
  const response = await apiClient.get('/api/trends', {
    params: minScore ? { min_score: minScore } : {},
  });
  return response.data;
};

/**
 * 分析趋势
 */
export const analyzeTrend = async (keyword: string, days?: number): Promise<any> => {
  const response = await apiClient.post('/api/trends/analyze', {
    keyword,
    days,
  });
  return response.data;
};

/**
 * 按行业获取趋势
 */
export const getTrendsByIndustry = async (
  industry: string,
  period: '7d' | '30d' | '90d' = '30d'
): Promise<any> => {
  const response = await apiClient.get(`/api/trends/industry/${industry}`, {
    params: { period },
  });
  return response.data;
};

// ==================== Agent API ====================

/**
 * 获取 Agent 状态
 */
export const getAgentStatus = async (): Promise<AgentStatus> => {
  const response = await apiClient.get('/agent/status');
  return response.data;
};

/**
 * 获取工具列表
 */
export const listTools = async (): Promise<{ tools: ToolSchema[]; count: number }> => {
  const response = await apiClient.get('/api/agent/tools');
  return response.data;
};

/**
 * 获取单个工具详情
 */
export const getTool = async (toolName: string): Promise<any> => {
  const response = await apiClient.get(`/api/agent/tools/${toolName}`);
  return response.data;
};

/**
 * 调用工具
 */
export const invokeTool = async (toolName: string, parameters?: Record<string, any>): Promise<any> => {
  const response = await apiClient.post('/api/agent/tools/invoke', {
    tool_name: toolName,
    parameters: parameters || {},
  });
  return response.data;
};

/**
 * 运行商机发现工作流
 */
export const runDiscoverWorkflow = async (
  keywords?: string[],
  industry?: string
): Promise<any> => {
  const response = await apiClient.post('/api/agent/workflow/discover', {
    keywords: keywords || [],
    industry,
  });
  return response.data;
};

/**
 * 运行行业分析工作流
 */
export const runAnalyzeWorkflow = async (industry: string): Promise<any> => {
  const response = await apiClient.post('/api/agent/workflow/analyze', {
    industry,
  });
  return response.data;
};

/**
 * 获取审计日志
 */
export const getAuditLogs = async (toolName?: string): Promise<any> => {
  const response = await apiClient.get('/api/agent/audit-logs', {
    params: toolName ? { tool_name: toolName } : {},
  });
  return response.data;
};

// ==================== Dashboard API ====================

/**
 * 获取仪表板概览
 */
export const getDashboardOverview = async (): Promise<{ success: boolean; data: DashboardOverview }> => {
  const response = await apiClient.get('/api/dashboard/overview');
  return response.data;
};

/**
 * 获取市场地图数据
 */
export const getMarketMap = async (industry?: string): Promise<any> => {
  const response = await apiClient.get('/api/dashboard/market-map', {
    params: industry ? { industry } : {},
  });
  return response.data;
};

/**
 * 获取趋势图表数据
 */
export const getTrendChart = async (keyword: string, days?: number): Promise<any> => {
  const response = await apiClient.get('/api/dashboard/trend-chart', {
    params: { keyword, days },
  });
  return response.data;
};

/**
 * 获取事件时间线
 */
export const getEventTimeline = async (days?: number, eventType?: string): Promise<any> => {
  const response = await apiClient.get('/api/dashboard/event-timeline', {
    params: { days, event_type: eventType },
  });
  return response.data;
};

/**
 * 获取知识图谱数据
 */
export const getKnowledgeGraph = async (keyword: string, depth?: number): Promise<any> => {
  const response = await apiClient.get('/api/dashboard/knowledge-graph', {
    params: { keyword, depth },
  });
  return response.data;
};

/**
 * 获取词云数据
 */
export const getWordCloud = async (industry?: string, days?: number): Promise<any> => {
  const response = await apiClient.get('/api/dashboard/word-cloud', {
    params: { industry, days },
  });
  return response.data;
};

// ==================== Stream API (实时推送) ====================

/**
 * WebSocket URL
 */
export const getWebSocketUrl = (): string => {
  return `ws://${API_BASE_URL.replace('http://', '')}/api/stream/ws`;
};

export default apiClient;
