/**
 * 员工管理 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { AIEmployee, AIEmployeeCreate, EmployeeStatus, EmployeeSearchParams, EmployeeStats } from '@/types/employee';
import type { ApiResponse } from '@/types';

export const employeeApi = {
  // 获取员工列表
  list: async (status?: EmployeeStatus): Promise<AIEmployee[]> => {
    const params = status ? { status } : {};
    const response = await httpClient.get<AIEmployee[]>(API_ENDPOINTS.EMPLOYEES, { params });
    return response.data;
  },

  // 获取员工详情
  get: async (employeeId: string): Promise<AIEmployee> => {
    const response = await httpClient.get<AIEmployee>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}`);
    return response.data;
  },

  // 创建员工
  create: async (data: AIEmployeeCreate, ownerId: string): Promise<AIEmployee> => {
    const response = await httpClient.post<AIEmployee>(API_ENDPOINTS.EMPLOYEES, data, {
      params: { owner_id: ownerId },
    });
    return response.data;
  },

  // 更新员工（上架）
  publish: async (employeeId: string): Promise<AIEmployee> => {
    const response = await httpClient.post<AIEmployee>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/publish`);
    return response.data;
  },

  // 更新员工（下线）
  offline: async (employeeId: string): Promise<AIEmployee> => {
    const response = await httpClient.post<AIEmployee>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/offline`);
    return response.data;
  },

  // 搜索员工
  search: async (params: EmployeeSearchParams): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(`${API_ENDPOINTS.EMPLOYEES}/search/${params.skills?.[0] || ''}`, {
      params: {
        min_rating: params.min_rating,
      },
    });
    return response.data;
  },

  // 获取员工统计数据
  getStats: async (): Promise<EmployeeStats> => {
    const response = await httpClient.get<EmployeeStats>(`${API_ENDPOINTS.EMPLOYEES}/stats`);
    return response.data;
  },

  // 获取员工订单
  getOrders: async (employeeId: string): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/orders`);
    return response.data;
  },

  // 获取员工评价
  getReviews: async (employeeId: string, minRating?: number): Promise<ApiResponse[]> => {
    const params = minRating ? { min_rating: minRating } : {};
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/reviews`, { params });
    return response.data;
  },

  // 获取员工风险报告
  getRiskReport: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/risk-report`);
    return response.data;
  },

  // 创建训练数据版本
  uploadTrainingData: async (employeeId: string, data: {
    version_name: string;
    description: string;
    training_config: Record<string, unknown>;
  }, createdBy: string): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(
      `${API_ENDPOINTS.EMPLOYEES}/${employeeId}/training-data`,
      data,
      { params: { created_by: createdBy } }
    );
    return response.data;
  },

  // 获取训练数据版本列表
  getTrainingVersions: async (employeeId: string): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.EMPLOYEES}/${employeeId}/training-data`);
    return response.data;
  },

  // 开始训练
  startTraining: async (employeeId: string, versionId: string, config?: Record<string, unknown>): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(
      `${API_ENDPOINTS.EMPLOYEES}/${employeeId}/training/start`,
      { version_id: versionId, training_config: config }
    );
    return response.data;
  },

  // 创建 DeerFlow Agent
  createAgent: async (employeeId: string): Promise<{ agent_id: string }> => {
    const response = await httpClient.post<{ agent_id: string }>(
      `${API_ENDPOINTS.EMPLOYEES}/${employeeId}/agent/create`
    );
    return response.data;
  },
};
