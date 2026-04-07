/**
 * 认证服务
 */
import { api } from './api';

const AUTH_BASE_URL = '/api/auth';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  role: 'worker' | 'employer';
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    username: string;
    email: string;
    role: string;
  };
}

export const authService = {
  /**
   * 用户登录
   */
  login: async (credentials: LoginRequest) => {
    const response = await api.post<AuthResponse>(`${AUTH_BASE_URL}/login`, credentials);
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
      localStorage.setItem('user_info', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  /**
   * 用户注册
   */
  register: async (data: RegisterRequest) => {
    const response = await api.post(`${AUTH_BASE_URL}/register`, data);
    return response.data;
  },

  /**
   * 退出登录
   */
  logout: async () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
  },

  /**
   * 刷新 Token
   */
  refreshToken: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    const response = await api.post<AuthResponse>(`${AUTH_BASE_URL}/refresh`, {
      refresh_token: refreshToken,
    });
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
    }
    return response.data;
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser: () => {
    const userInfo = localStorage.getItem('user_info');
    if (userInfo) {
      return JSON.parse(userInfo);
    }
    return null;
  },

  /**
   * 修改密码
   */
  changePassword: async (oldPassword: string, newPassword: string) => {
    const response = await api.post(`${AUTH_BASE_URL}/change-password`, {
      old_password: oldPassword,
      new_password: newPassword,
    });
    return response.data;
  },

  /**
   * 重置密码
   */
  resetPassword: async (email: string) => {
    const response = await api.post(`${AUTH_BASE_URL}/reset-password`, { email });
    return response.data;
  },
};

export default authService;
