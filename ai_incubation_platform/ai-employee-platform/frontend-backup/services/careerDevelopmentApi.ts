/**
 * 职业发展 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  parent_skill_id?: string;
  tags?: string[];
}

export interface EmployeeSkill {
  skill: Skill;
  level: 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'master';
  years_of_experience: number;
  verified: boolean;
}

export interface CareerRole {
  id: string;
  name: string;
  description: string;
  level: number;
  path_type: string;
  required_skills: Record<string, number>;
  salary_range_min?: number;
  salary_range_max?: number;
}

export interface DevelopmentPlan {
  id: string;
  employee_id: string;
  plan_name: string;
  status: 'draft' | 'active' | 'completed' | 'archived';
  target_role_id?: string;
  start_date?: string;
  target_completion_date?: string;
  progress: number;
}

export const careerDevelopmentApi = {
  // === 技能图谱 ===
  getSkills: async (
    category?: string,
    parent_skill_id?: string,
    search?: string,
    limit: number = 100
  ): Promise<Skill[]> => {
    const params: Record<string, unknown> = { limit };
    if (category) params.category = category;
    if (parent_skill_id !== undefined) params.parent_skill_id = parent_skill_id;
    if (search) params.search = search;
    const response = await httpClient.get<Skill[]>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/skills`, { params });
    return response.data;
  },

  getSkillTree: async (root_skill_id?: string): Promise<ApiResponse> => {
    const params = root_skill_id ? { root_skill_id } : {};
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/skills/tree`, { params });
    return response.data;
  },

  getLearningPath: async (from_skill_id: string, to_skill_id: string): Promise<Skill[]> => {
    const response = await httpClient.get<Skill[]>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/skills/path`, {
      params: { from_skill_id, to_skill_id },
    });
    return response.data;
  },

  // === 员工技能 ===
  getEmployeeSkills: async (employeeId: string, level?: string, category?: string): Promise<EmployeeSkill[]> => {
    const params: Record<string, unknown> = {};
    if (level) params.level = level;
    if (category) params.category = category;
    const response = await httpClient.get<EmployeeSkill[]>(
      `${API_ENDPOINTS.CAREER_DEVELOPMENT}/employees/${employeeId}/skills`,
      { params }
    );
    return response.data;
  },

  addEmployeeSkill: async (data: {
    employee_id: string;
    skill_id: string;
    level: string;
    years_of_experience?: number;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/employees/skills`, data);
    return response.data;
  },

  // === 职业角色 ===
  getCareerRoles: async (
    path_type?: string,
    level?: number,
    search?: string,
    limit: number = 100
  ): Promise<CareerRole[]> => {
    const params: Record<string, unknown> = { limit };
    if (path_type) params.path_type = path_type;
    if (level) params.level = level;
    if (search) params.search = search;
    const response = await httpClient.get<CareerRole[]>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/career-roles`, { params });
    return response.data;
  },

  recommendCareerPaths: async (employeeId: string, limit: number = 5): Promise<ApiResponse[]> => {
    const response = await httpClient.post<ApiResponse[]>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/career-paths/recommend`, null, {
      params: { employee_id: employeeId, limit },
    });
    return response.data;
  },

  // === 发展计划 ===
  getDevelopmentPlans: async (employeeId: string, status?: string, limit: number = 100): Promise<DevelopmentPlan[]> => {
    const params: Record<string, unknown> = { limit };
    if (status) params.status = status;
    const response = await httpClient.get<DevelopmentPlan[]>(
      `${API_ENDPOINTS.CAREER_DEVELOPMENT}/employees/${employeeId}/development-plans`,
      { params }
    );
    return response.data;
  },

  createDevelopmentPlan: async (data: {
    employee_id: string;
    plan_name: string;
    target_role_id?: string;
    start_date?: string;
    target_completion_date?: string;
  }): Promise<DevelopmentPlan> => {
    const response = await httpClient.post<DevelopmentPlan>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/development-plans`, data);
    return response.data;
  },

  getPlanProgress: async (planId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/development-plans/${planId}/progress`);
    return response.data;
  },

  // === 导师匹配 ===
  getMentorMatches: async (menteeId: string, limit: number = 3): Promise<ApiResponse[]> => {
    const response = await httpClient.post<ApiResponse[]>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/mentorship/auto-match`, null, {
      params: { mentee_id: menteeId, limit },
    });
    return response.data;
  },

  // === 仪表盘 ===
  getDashboard: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.CAREER_DEVELOPMENT}/employees/${employeeId}/dashboard`);
    return response.data;
  },
};
