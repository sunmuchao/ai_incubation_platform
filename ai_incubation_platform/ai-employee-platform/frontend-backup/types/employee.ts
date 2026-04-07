/**
 * AI 员工相关类型
 */
import type { ID } from './index';

// 员工状态
export type EmployeeStatus = 'available' | 'unavailable' | 'offline' | 'busy';

// 技能等级
export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert' | 'master';

// 技能定义
export interface Skill {
  id: ID;
  name: string;
  level: SkillLevel;
  years_of_experience?: number;
  verified?: boolean;
}

// AI 员工
export interface AIEmployee {
  id: ID;
  name: string;
  description: string;
  avatar_url?: string;
  owner_id: ID;
  tenant_id: ID;
  status: EmployeeStatus;
  category: string;
  skills: Record<string, SkillLevel>;
  hourly_rate: number;
  rating: number;
  review_count: number;
  total_hours_worked: number;
  completion_rate: number;
  response_time_hours: number;
  available_from?: string;
  available_to?: string;
  timezone?: string;
  languages?: string[];
  tags?: string[];
  created_at: string;
  updated_at: string;
}

// 创建员工请求
export interface AIEmployeeCreate {
  name: string;
  description: string;
  category: string;
  skills?: Record<string, SkillLevel>;
  hourly_rate: number;
  avatar_url?: string;
  timezone?: string;
  languages?: string[];
  tags?: string[];
}

// 员工搜索参数
export interface EmployeeSearchParams {
  query?: string;
  skills?: string[];
  category?: string;
  min_rating?: number;
  max_hourly_rate?: number;
  available_only?: boolean;
  timezone?: string;
  languages?: string[];
  sort_by?: 'rating' | 'hourly_rate' | 'completion_rate' | 'total_hours';
  sort_order?: 'asc' | 'desc';
}

// 员工统计数据
export interface EmployeeStats {
  total_employees: number;
  available_employees: number;
  busy_employees: number;
  offline_employees: number;
  avg_rating: number;
  avg_hourly_rate: number;
  total_hours_this_month: number;
  total_revenue_this_month: number;
}
