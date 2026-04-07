/**
 * 智能助手 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface TaskRecommendation {
  id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
  estimated_hours: number;
  related_skills?: string[];
}

export interface MeetingSummary {
  id: string;
  meeting_id: string;
  title: string;
  date: string;
  participants: string[];
  summary: string;
  key_points: string[];
  action_items: { description: string; owner: string; due_date?: string }[];
}

export interface DailyReport {
  id: string;
  employee_id: string;
  date: string;
  completed_tasks: string[];
  hours_worked: number;
  meetings_attended: number;
  highlights: string[];
  blockers: string[];
  tomorrow_plan: string[];
}

export const assistantApi = {
  // === 任务推荐 ===
  getTaskRecommendations: async (employeeId: string, limit: number = 5): Promise<TaskRecommendation[]> => {
    const response = await httpClient.get<TaskRecommendation[]>(`${API_ENDPOINTS.ASSISTANT}/tasks/recommend`, {
      params: { employee_id: employeeId, limit },
    });
    return response.data;
  },

  getScheduledTasks: async (employeeId: string, date?: string): Promise<TaskRecommendation[]> => {
    const params: Record<string, unknown> = {};
    if (date) params.date = date;
    const response = await httpClient.get<TaskRecommendation[]>(`${API_ENDPOINTS.ASSISTANT}/tasks/scheduled`, {
      params: { employee_id: employeeId, ...params },
    });
    return response.data;
  },

  completeTask: async (taskId: string, employeeId: string, notes?: string): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/tasks/${taskId}/complete`, {
      notes,
    }, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  // === 智能日程 ===
  getOptimizedSchedule: async (employeeId: string, date: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/schedule/optimize`, {
      params: { employee_id: employeeId, date },
    });
    return response.data;
  },

  suggestFocusTime: async (employeeId: string, duration: number): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/schedule/focus-time`, {
      employee_id: employeeId,
      duration_minutes: duration,
    });
    return response.data;
  },

  // === 会议管理 ===
  getUpcomingMeetings: async (employeeId: string, hours: number = 24): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.ASSISTANT}/meetings/upcoming`, {
      params: { employee_id: employeeId, hours },
    });
    return response.data;
  },

  prepareMeetingAgenda: async (meetingId: string): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/meetings/${meetingId}/agenda`);
    return response.data;
  },

  // === 会议摘要 ===
  generateMeetingSummary: async (data: {
    meeting_id: string;
    transcript?: string;
    notes?: string;
  }): Promise<MeetingSummary> => {
    const response = await httpClient.post<MeetingSummary>(`${API_ENDPOINTS.ASSISTANT}/meetings/summarize`, data);
    return response.data;
  },

  getMeetingSummaries: async (employeeId: string, limit: number = 10): Promise<MeetingSummary[]> => {
    const response = await httpClient.get<MeetingSummary[]>(`${API_ENDPOINTS.ASSISTANT}/employees/${employeeId}/meeting-summaries`, {
      params: { limit },
    });
    return response.data;
  },

  // === 工作简报 ===
  generateDailyReport: async (employeeId: string, date?: string): Promise<DailyReport> => {
    const params: Record<string, unknown> = {};
    if (date) params.date = date;
    const response = await httpClient.post<DailyReport>(`${API_ENDPOINTS.ASSISTANT}/reports/daily/generate`, null, {
      params: { employee_id: employeeId, ...params },
    });
    return response.data;
  },

  getDailyReports: async (employeeId: string, limit: number = 10): Promise<DailyReport[]> => {
    const response = await httpClient.get<DailyReport[]>(`${API_ENDPOINTS.ASSISTANT}/employees/${employeeId}/reports`, {
      params: { limit },
    });
    return response.data;
  },

  getReportTemplates: async (): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.ASSISTANT}/reports/templates`);
    return response.data;
  },

  // === 智能洞察 ===
  getInsights: async (employeeId: string, category?: string): Promise<ApiResponse[]> => {
    const params: Record<string, unknown> = {};
    if (category) params.category = category;
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.ASSISTANT}/insights`, {
      params: { employee_id: employeeId, ...params },
    });
    return response.data;
  },

  // === 助手设置 ===
  getAssistantSettings: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/settings/${employeeId}`);
    return response.data;
  },

  updateAssistantSettings: async (employeeId: string, settings: Record<string, unknown>): Promise<ApiResponse> => {
    const response = await httpClient.put<ApiResponse>(`${API_ENDPOINTS.ASSISTANT}/settings/${employeeId}`, settings);
    return response.data;
  },
};
