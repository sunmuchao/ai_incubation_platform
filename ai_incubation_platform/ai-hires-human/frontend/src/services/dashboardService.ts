/**
 * 仪表板 API 服务
 */
import { api } from './api';
import type { DashboardOverview, TrendDataPoint } from '@/types';

const DASHBOARD_BASE_URL = '/api/dashboard';

export const dashboardService = {
  /**
   * 获取仪表板总览数据
   */
  getOverview: async (timeRange: string = 'realtime', organizationId?: string) => {
    const response = await api.get<DashboardOverview>(`${DASHBOARD_BASE_URL}/overview`, {
      params: { time_range: timeRange, organization_id: organizationId },
    });
    return response.data;
  },

  /**
   * 获取任务分析数据
   */
  getTaskAnalysis: async (timeRange: string = 'daily', organizationId?: string) => {
    const response = await api.get(`${DASHBOARD_BASE_URL}/tasks`, {
      params: { time_range: timeRange, organization_id: organizationId },
    });
    return response.data;
  },

  /**
   * 获取工人分析数据
   */
  getWorkerAnalysis: async (timeRange: string = 'daily', organizationId?: string) => {
    const response = await api.get(`${DASHBOARD_BASE_URL}/workers`, {
      params: { time_range: timeRange, organization_id: organizationId },
    });
    return response.data;
  },

  /**
   * 获取质量分析数据
   */
  getQualityAnalysis: async (timeRange: string = 'daily', organizationId?: string) => {
    const response = await api.get(`${DASHBOARD_BASE_URL}/quality`, {
      params: { time_range: timeRange, organization_id: organizationId },
    });
    return response.data;
  },

  /**
   * 获取财务分析数据
   */
  getFinancialAnalysis: async (timeRange: string = 'daily', organizationId?: string) => {
    const response = await api.get(`${DASHBOARD_BASE_URL}/financial`, {
      params: { time_range: timeRange, organization_id: organizationId },
    });
    return response.data;
  },

  /**
   * 获取任务趋势
   */
  getTaskTrend: async (days: number = 7, organizationId?: string) => {
    const response = await api.get<{ trend_type: string; days: number; data: Array<{ date: string; created: number; completed: number }> }>(
      `${DASHBOARD_BASE_URL}/trend/tasks`,
      { params: { days, organization_id: organizationId }}
    );
    return response.data;
  },

  /**
   * 获取工人活跃趋势
   */
  getWorkerTrend: async (days: number = 7, organizationId?: string) => {
    const response = await api.get<{ trend_type: string; days: number; data: Array<{ date: string; active_workers: number }> }>(
      `${DASHBOARD_BASE_URL}/trend/workers`,
      { params: { days, organization_id: organizationId }}
    );
    return response.data;
  },

  /**
   * 获取财务趋势
   */
  getFinancialTrend: async (days: number = 7, organizationId?: string) => {
    const response = await api.get<{ trend_type: string; days: number; data: Array<{ date: string; gmv: number }> }>(
      `${DASHBOARD_BASE_URL}/trend/financial`,
      { params: { days, organization_id: organizationId }}
    );
    return response.data;
  },

  /**
   * 获取可用指标列表
   */
  getAvailableMetrics: async () => {
    const response = await api.get(`${DASHBOARD_BASE_URL}/metrics`);
    return response.data;
  },
};

export default dashboardService;
