/**
 * HTTP 客户端封装
 */
import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { env, API_ENDPOINTS } from '@/config';
import type { ErrorResponse, LoginResponse } from '@/types';

// 请求拦截器配置
const setupRequestInterceptors = (axiosInstance: ReturnType<typeof axios.create>) => {
  axiosInstance.interceptors.request.use(
    (config) => {
      // 添加认证头
      const token = localStorage.getItem(env.TOKEN_KEY);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // 添加请求时间戳（防止缓存）
      if (config.method === 'get') {
        config.params = {
          ...config.params,
          _t: Date.now(),
        };
      }

      return config;
    },
    (error) => Promise.reject(error)
  );
};

// 响应拦截器配置
const setupResponseInterceptors = (axiosInstance: ReturnType<typeof axios.create>) => {
  axiosInstance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ErrorResponse>) => {
      // 处理 401 错误
      if (error.response?.status === 401) {
        // 清除本地 token
        localStorage.removeItem(env.TOKEN_KEY);
        localStorage.removeItem(env.REFRESH_TOKEN_KEY);
        // 重定向到登录页
        window.location.href = '/login';
      }

      // 处理 500 错误
      if (error.response?.status === 500) {
        console.error('Server error:', error.response.data);
      }

      return Promise.reject(error);
    }
  );
};

// 创建 axios 实例
const axiosInstance = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 设置拦截器
setupRequestInterceptors(axiosInstance);
setupResponseInterceptors(axiosInstance);

// 封装请求方法
export const httpClient = {
  // GET 请求
  get<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.get<T>(url, config);
  },

  // POST 请求
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.post<T>(url, data, config);
  },

  // PUT 请求
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.put<T>(url, data, config);
  },

  // PATCH 请求
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.patch<T>(url, data, config);
  },

  // DELETE 请求
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.delete<T>(url, config);
  },

  // 上传文件
  upload<T>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return axiosInstance.post<T>(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // 下载文件
  download(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<Blob>> {
    return axiosInstance.get<Blob>(url, {
      ...config,
      responseType: 'blob',
    });
  },
};

// 认证相关 API
export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await httpClient.post<LoginResponse>(API_ENDPOINTS.LOGIN, {
      username,
      password,
    });
    return response.data;
  },

  logout: async (): Promise<void> => {
    localStorage.removeItem(env.TOKEN_KEY);
    localStorage.removeItem(env.REFRESH_TOKEN_KEY);
  },

  refreshToken: async (): Promise<string> => {
    const refreshToken = localStorage.getItem(env.REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      throw new Error('No refresh token');
    }
    // TODO: 实现刷新 token 的 API
    return refreshToken;
  },
};

export default httpClient;
