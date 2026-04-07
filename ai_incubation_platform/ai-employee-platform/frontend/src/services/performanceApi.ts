/**
 * 绩效管理 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface ReviewCycle {
  id: string;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  review_type: '360' | 'manager' | 'peer' | 'self';
  status: 'draft' | 'active' | 'completed';
  progress: Record<string, unknown>;
}

export interface PerformanceReview {
  id: string;
  employee_id: string;
  reviewer_id: string;
  review_type: string;
  status: 'draft' | 'in_progress' | 'submitted' | 'completed';
  scores: Record<string, number>;
  overall_score?: number;
  comments?: string;
  strengths: string[];
  areas_for_improvement: string[];
  goals: string[];
}

export interface Objective {
  id: string;
  title: string;
  description?: string;
  progress: number;
  status: 'on_track' | 'at_risk' | 'off_track' | 'completed';
  key_results_count: number;
  due_date: string;
}

export const performanceApi = {
  // === 评估周期 ===
  createReviewCycle: async (data: {
    name: string;
    start_date: string;
    end_date: string;
    review_type: string;
    target_employee_ids?: string[];
  }): Promise<ReviewCycle> => {
    const response = await httpClient.post<ReviewCycle>(`${API_ENDPOINTS.PERFORMANCE}/cycles`, data);
    return response.data;
  },

  getReviewCycles: async (status?: string, limit: number = 20): Promise<ReviewCycle[]> => {
    const params: Record<string, unknown> = { limit };
    if (status) params.status = status;
    const response = await httpClient.get<ReviewCycle[]>(`${API_ENDPOINTS.PERFORMANCE}/cycles`, { params });
    return response.data;
  },

  getReviewCycle: async (cycleId: string): Promise<ReviewCycle> => {
    const response = await httpClient.get<ReviewCycle>(`${API_ENDPOINTS.PERFORMANCE}/cycles/${cycleId}`);
    return response.data;
  },

  launchReviewCycle: async (cycleId: string): Promise<ReviewCycle> => {
    const response = await httpClient.post<ReviewCycle>(`${API_ENDPOINTS.PERFORMANCE}/cycles/${cycleId}/launch`);
    return response.data;
  },

  completeReviewCycle: async (cycleId: string): Promise<ReviewCycle> => {
    const response = await httpClient.post<ReviewCycle>(`${API_ENDPOINTS.PERFORMANCE}/cycles/${cycleId}/complete`);
    return response.data;
  },

  // === 绩效评估 ===
  createReview: async (data: {
    employee_id: string;
    reviewer_id: string;
    review_type: string;
    cycle_id?: string;
    due_date?: string;
  }): Promise<PerformanceReview> => {
    const response = await httpClient.post<PerformanceReview>(`${API_ENDPOINTS.PERFORMANCE}/reviews`, data);
    return response.data;
  },

  getReview: async (reviewId: string): Promise<PerformanceReview> => {
    const response = await httpClient.get<PerformanceReview>(`${API_ENDPOINTS.PERFORMANCE}/reviews/${reviewId}`);
    return response.data;
  },

  updateReview: async (reviewId: string, data: {
    scores?: Record<string, number>;
    comments?: string;
    strengths?: string[];
    areas_for_improvement?: string[];
    goals?: string[];
  }): Promise<PerformanceReview> => {
    const response = await httpClient.put<PerformanceReview>(`${API_ENDPOINTS.PERFORMANCE}/reviews/${reviewId}`, data);
    return response.data;
  },

  submitReview: async (reviewId: string): Promise<PerformanceReview> => {
    const response = await httpClient.post<PerformanceReview>(`${API_ENDPOINTS.PERFORMANCE}/reviews/${reviewId}/submit`);
    return response.data;
  },

  getEmployeeReviews: async (employeeId: string, status?: string, limit: number = 20): Promise<PerformanceReview[]> => {
    const params: Record<string, unknown> = { limit };
    if (status) params.status = status;
    const response = await httpClient.get<PerformanceReview[]>(
      `${API_ENDPOINTS.PERFORMANCE}/employees/${employeeId}/reviews`,
      { params }
    );
    return response.data;
  },

  // === OKR 目标 ===
  createObjective: async (data: {
    title: string;
    description?: string;
    start_date: string;
    due_date: string;
    employee_id?: string;
    parent_objective_id?: string;
  }): Promise<Objective> => {
    const response = await httpClient.post<Objective>(`${API_ENDPOINTS.PERFORMANCE}/objectives`, data);
    return response.data;
  },

  getObjective: async (objectiveId: string): Promise<Objective> => {
    const response = await httpClient.get<Objective>(`${API_ENDPOINTS.PERFORMANCE}/objectives/${objectiveId}`);
    return response.data;
  },

  updateObjective: async (objectiveId: string, data: {
    title?: string;
    progress?: number;
    status?: string;
    confidence_level?: number;
  }): Promise<Objective> => {
    const response = await httpClient.put<Objective>(`${API_ENDPOINTS.PERFORMANCE}/objectives/${objectiveId}`, data);
    return response.data;
  },

  getEmployeeObjectives: async (employeeId: string, status?: string): Promise<Objective[]> => {
    const params: Record<string, unknown> = {};
    if (status) params.status = status;
    const response = await httpClient.get<Objective[]>(
      `${API_ENDPOINTS.PERFORMANCE}/employees/${employeeId}/objectives`,
      { params }
    );
    return response.data;
  },

  createKeyResult: async (objectiveId: string, data: {
    title: string;
    target_value: number;
    start_value?: number;
    unit?: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(
      `${API_ENDPOINTS.PERFORMANCE}/objectives/${objectiveId}/key-results`,
      data
    );
    return response.data;
  },

  updateKeyResultProgress: async (krId: string, currentValue: number): Promise<ApiResponse> => {
    const response = await httpClient.put<ApiResponse>(
      `${API_ENDPOINTS.PERFORMANCE}/key-results/${krId}/progress`,
      { current_value: currentValue }
    );
    return response.data;
  },

  // === 仪表盘 ===
  getDashboard: async (employeeIds?: string[]): Promise<ApiResponse> => {
    const params = employeeIds ? { employee_ids: employeeIds.join(',') } : {};
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.PERFORMANCE}/dashboard`, { params });
    return response.data;
  },

  getBenchmarks: async (): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.PERFORMANCE}/benchmarks`);
    return response.data;
  },

  // === 1 对 1 会议 ===
  createMeeting: async (data: {
    employee_id: string;
    manager_id: string;
    meeting_date: string;
    agenda?: string;
    meeting_type?: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.PERFORMANCE}/one-on-ones`, data);
    return response.data;
  },

  getEmployeeMeetings: async (employeeId: string, limit: number = 20): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(
      `${API_ENDPOINTS.PERFORMANCE}/employees/${employeeId}/one-on-ones`,
      { params: { limit } }
    );
    return response.data;
  },
};
