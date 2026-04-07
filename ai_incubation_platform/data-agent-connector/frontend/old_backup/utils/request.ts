import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'antd'
import { API_CONFIG } from '../config/api'

// 响应数据接口
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// API 客户端类
class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.baseURL,
      timeout: API_CONFIG.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        // 从本地存储获取 API Key
        const apiKey = localStorage.getItem('dac_api_key')
        if (apiKey) {
          config.headers['X-API-Key'] = apiKey
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        return response
      },
      (error) => {
        let errorMessage = '请求失败，请稍后重试'

        if (error.response) {
          const { status, data } = error.response
          switch (status) {
            case 400:
              errorMessage = data?.detail || '请求参数错误'
              break
            case 401:
              errorMessage = '未授权，请检查 API Key'
              break
            case 403:
              errorMessage = '权限不足'
              break
            case 404:
              errorMessage = '资源不存在'
              break
            case 429:
              errorMessage = '请求频率超限'
              break
            case 500:
              errorMessage = '服务器内部错误'
              break
            case 502:
              errorMessage = '网关错误'
              break
            case 503:
              errorMessage = '服务不可用'
              break
            default:
              errorMessage = data?.detail || errorMessage
          }
        } else if (error.request) {
          errorMessage = '网络错误，请检查网络连接'
        }

        message.error(errorMessage)
        return Promise.reject(error)
      }
    )
  }

  // GET 请求
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return this.client.get<ApiResponse<T>>(url, config)
  }

  // POST 请求
  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return this.client.post<ApiResponse<T>>(url, data, config)
  }

  // PUT 请求
  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return this.client.put<ApiResponse<T>>(url, data, config)
  }

  // DELETE 请求
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return this.client.delete<ApiResponse<T>>(url, config)
  }
}

// 导出单例
export const apiClient = new ApiClient()
