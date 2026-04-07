/**
 * 通用类型定义
 */

// API 响应基础类型
export interface ApiResponse<T = unknown> {
  success?: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 分页参数
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

// 分页响应
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  limit: number;
}

// 用户角色
export type UserRole = 'admin' | 'enterprise' | 'employee' | 'visitor';

// 用户信息
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

// 租户信息
export interface Tenant {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'inactive' | 'suspended';
  quota: {
    max_employees: number;
    max_storage_mb: number;
    max_api_calls: number;
  };
  created_at: string;
}

// JWT Token
export interface TokenPayload {
  user_id: string;
  username: string;
  role: UserRole;
  tenant_id: string;
  exp: number;
}

// 认证响应
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

// 错误响应
export interface ErrorResponse {
  detail: string;
  status_code?: number;
}

// 排序方向
export type SortOrder = 'asc' | 'desc';

// 通用 ID 类型
export type ID = string;
