/**
 * 认证服务
 */
import { api } from './api';
const AUTH_BASE_URL = '/api/auth';
export const authService = {
    /**
     * 用户登录
     */
    login: async (credentials) => {
        const response = await api.post(`${AUTH_BASE_URL}/login`, credentials);
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
    register: async (data) => {
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
        const response = await api.post(`${AUTH_BASE_URL}/refresh`, {
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
    changePassword: async (oldPassword, newPassword) => {
        const response = await api.post(`${AUTH_BASE_URL}/change-password`, {
            old_password: oldPassword,
            new_password: newPassword,
        });
        return response.data;
    },
    /**
     * 重置密码
     */
    resetPassword: async (email) => {
        const response = await api.post(`${AUTH_BASE_URL}/reset-password`, { email });
        return response.data;
    },
};
export default authService;
