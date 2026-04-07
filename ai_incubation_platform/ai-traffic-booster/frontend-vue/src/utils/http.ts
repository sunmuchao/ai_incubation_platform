/**
 * HTTP 客户端配置
 */
import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const config: AxiosRequestConfig = {
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
}

class HttpClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create(config)
    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 可以在这里添加 token 等认证信息
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        const res = response.data
        // 如果响应码不为 0，则视为错误
        if (res.code !== 0 && res.code !== 200) {
          ElMessage.error(res.message || '请求失败')
          return Promise.reject(new Error(res.message || '请求失败'))
        }
        return res
      },
      (error) => {
        console.error('HTTP Error:', error)
        ElMessage.error(error.message || '网络错误')
        return Promise.reject(error)
      }
    )
  }

  public get<T = any>(url: string, params?: any): Promise<T> {
    return this.instance.get(url, { params }).then((res) => res.data)
  }

  public post<T = any>(url: string, data?: any): Promise<T> {
    return this.instance.post(url, data).then((res) => res.data)
  }

  public put<T = any>(url: string, data?: any): Promise<T> {
    return this.instance.put(url, data).then((res) => res.data)
  }

  public delete<T = any>(url: string, params?: any): Promise<T> {
    return this.instance.delete(url, { params }).then((res) => res.data)
  }
}

export const http = new HttpClient()
