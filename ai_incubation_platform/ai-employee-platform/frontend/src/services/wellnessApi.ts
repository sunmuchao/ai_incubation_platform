/**
 * 员工福祉 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface WellnessAssessment {
  id: string;
  employee_id: string;
  assessment_type: 'mental_health' | 'stress' | 'satisfaction' | 'work_life_balance';
  score: number;
  responses: Record<string, unknown>;
  recommendations: string[];
  created_at: string;
}

export interface CounselingSession {
  id: string;
  employee_id: string;
  counselor_id: string;
  session_date: string;
  duration_minutes: number;
  notes?: string;
  status: 'scheduled' | 'completed' | 'cancelled';
}

export interface LeaveRequest {
  id: string;
  employee_id: string;
  leave_type: 'annual' | 'sick' | 'personal' | 'maternity' | 'paternity';
  start_date: string;
  end_date: string;
  reason?: string;
  status: 'pending' | 'approved' | 'rejected';
}

export const wellnessApi = {
  // === 心理健康评估 ===
  createAssessment: async (data: {
    employee_id: string;
    assessment_type: string;
    responses: Record<string, unknown>;
  }): Promise<WellnessAssessment> => {
    const response = await httpClient.post<WellnessAssessment>(`${API_ENDPOINTS.WELLNESS}/assessments`, data);
    return response.data;
  },

  getEmployeeAssessments: async (employeeId: string, assessmentType?: string, limit: number = 10): Promise<WellnessAssessment[]> => {
    const params: Record<string, unknown> = { limit };
    if (assessmentType) params.assessment_type = assessmentType;
    const response = await httpClient.get<WellnessAssessment[]>(
      `${API_ENDPOINTS.WELLNESS}/employees/${employeeId}/assessments`,
      { params }
    );
    return response.data;
  },

  // === 压力水平追踪 ===
  logStressLevel: async (employeeId: string, level: number, notes?: string): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/stress/log`, {
      employee_id: employeeId,
      level,
      notes,
    });
    return response.data;
  },

  getStressTrend: async (employeeId: string, days: number = 30): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/stress/trend`, {
      params: { employee_id: employeeId, days },
    });
    return response.data;
  },

  // === 心理咨询 ===
  bookCounselingSession: async (data: {
    employee_id: string;
    counselor_id: string;
    session_date: string;
    duration_minutes?: number;
  }): Promise<CounselingSession> => {
    const response = await httpClient.post<CounselingSession>(`${API_ENDPOINTS.WELLNESS}/counseling/book`, data);
    return response.data;
  },

  getEmployeeSessions: async (employeeId: string, status?: string): Promise<CounselingSession[]> => {
    const params: Record<string, unknown> = {};
    if (status) params.status = status;
    const response = await httpClient.get<CounselingSession[]>(
      `${API_ENDPOINTS.WELLNESS}/employees/${employeeId}/counseling`,
      { params }
    );
    return response.data;
  },

  // === 请假管理 ===
  requestLeave: async (data: {
    employee_id: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    reason?: string;
  }): Promise<LeaveRequest> => {
    const response = await httpClient.post<LeaveRequest>(`${API_ENDPOINTS.WELLNESS}/leave/request`, data);
    return response.data;
  },

  getEmployeeLeaves: async (employeeId: string, status?: string): Promise<LeaveRequest[]> => {
    const params: Record<string, unknown> = {};
    if (status) params.status = status;
    const response = await httpClient.get<LeaveRequest[]>(
      `${API_ENDPOINTS.WELLNESS}/employees/${employeeId}/leave`,
      { params }
    );
    return response.data;
  },

  approveLeave: async (leaveId: string, approverId: string): Promise<LeaveRequest> => {
    const response = await httpClient.post<LeaveRequest>(`${API_ENDPOINTS.WELLNESS}/leave/${leaveId}/approve`, null, {
      params: { approver_id: approverId },
    });
    return response.data;
  },

  // === 满意度调查 ===
  createSatisfactionSurvey: async (data: {
    tenant_id: string;
    title: string;
    questions: unknown[];
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/surveys`, data);
    return response.data;
  },

  submitSurveyResponse: async (surveyId: string, employeeId: string, responses: Record<string, unknown>): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/surveys/${surveyId}/responses`, {
      employee_id: employeeId,
      responses,
    });
    return response.data;
  },

  // === 离职风险预测 ===
  getTurnoverRisk: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/turnover-risk/${employeeId}`);
    return response.data;
  },

  // === 仪表盘 ===
  getWellnessDashboard: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/dashboard/${employeeId}`);
    return response.data;
  },

  getOrganizationWellness: async (tenantId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.WELLNESS}/organization`, {
      params: { tenant_id: tenantId },
    });
    return response.data;
  },
};
