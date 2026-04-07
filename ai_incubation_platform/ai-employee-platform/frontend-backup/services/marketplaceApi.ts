/**
 * 市场 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { AIEmployee, EmployeeStatus, SkillLevel } from '@/types/employee';
import type { ApiResponse } from '@/types';

export interface MarketplaceFilters {
  status?: EmployeeStatus;
  min_rating?: number;
  max_hourly_rate?: number;
  skill?: string;
  skill_level?: SkillLevel;
  category?: string;
  available_only?: boolean;
  sort_by?: 'rating' | 'hourly_rate' | 'completion_rate';
}

export interface MarketplaceStats {
  total_employees: number;
  avg_rating: number;
  avg_hourly_rate: number;
  categories: Record<string, number>;
  trending_skills: string[];
}

export const marketplaceApi = {
  // 获取市场员工列表
  list: async (filters: MarketplaceFilters = {}): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(API_ENDPOINTS.MARKETPLACE, {
      params: filters,
    });
    return response.data;
  },

  // 搜索市场员工
  search: async (filters: MarketplaceFilters = {}): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(`${API_ENDPOINTS.MARKETPLACE}/search`, {
      params: filters,
    });
    return response.data;
  },

  // 获取筛选条件
  getFilters: async (): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.MARKETPLACE}/filters`);
    return response.data;
  },

  // 保存搜索条件
  saveSearch: async (name: string, filters: MarketplaceFilters): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.MARKETPLACE}/save-search`, {
      name,
      filters,
    });
    return response.data;
  },

  // 获取市场统计
  getStats: async (): Promise<MarketplaceStats> => {
    const response = await httpClient.get<MarketplaceStats>(`${API_ENDPOINTS.MARKETPLACE}/stats`);
    return response.data;
  },

  // 获取排行榜
  getRankings: async (
    type: 'top_rated' | 'most_hired' | 'newest' | 'trending',
    limit: number = 10
  ): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(`${API_ENDPOINTS.MARKETPLACE}/rankings`, {
      params: { type, limit },
    });
    return response.data;
  },

  // 获取精选推荐
  getFeatured: async (limit: number = 10): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(`${API_ENDPOINTS.MARKETPLACE}/featured`, {
      params: { limit },
    });
    return response.data;
  },

  // 获取技能趋势
  getTrendingSkills: async (): Promise<string[]> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.MARKETPLACE}/trending-skills`);
    return (response.data.data as string[]) || [];
  },

  // 获取个性化推荐
  getRecommendations: async (userId: string, limit: number = 10): Promise<AIEmployee[]> => {
    const response = await httpClient.get<AIEmployee[]>(`${API_ENDPOINTS.MARKETPLACE}/recommendations`, {
      params: { user_id: userId, limit },
    });
    return response.data;
  },
};
