/**
 * API 客户端配置
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// API 基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8004';

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // 添加请求 ID 用于追踪
    config.headers['X-Request-ID'] = generateRequestId();
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      // 服务器返回错误响应
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // 未授权，清除 token 并跳转登录
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
          break;
        case 403:
          // 禁止访问
          console.error('禁止访问:', data);
          break;
        case 404:
          // 资源不存在
          console.error('资源不存在:', data);
          break;
        case 500:
          // 服务器错误
          console.error('服务器错误:', data);
          break;
        default:
          console.error('API 错误:', data);
      }
    } else if (error.request) {
      // 请求已发送但未收到响应
      console.error('网络错误：无法连接到服务器');
    } else {
      // 请求配置错误
      console.error('请求配置错误:', error.message);
    }

    return Promise.reject(error);
  }
);

// 生成请求 ID
function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// 通用请求方法
export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return apiClient.get<T>(url, config);
  },

  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return apiClient.post<T>(url, data, config);
  },

  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return apiClient.put<T>(url, data, config);
  },

  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return apiClient.patch<T>(url, data, config);
  },

  delete: <T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return apiClient.delete<T>(url, config);
  },
};

export default apiClient;
