/**
 * 统一的 Axios API 客户端配置
 *
 * 所有 API 模块应导入此实例，避免重复配置
 *
 * 统一认证入口：
 * - getAuthHeaders() - 获取认证头
 * - getCurrentUserId() - 获取当前用户 ID（从 useCurrentUserId.ts 统一导出）
 */

import axios from 'axios'
import { authStorage, devStorage } from '@/utils/storage'
import { getCurrentUserId as _getCurrentUserId } from '@/hooks/useCurrentUserId'

const API_BASE_URL = ''

// ==================== 统一认证入口 ====================

/**
 * 获取认证请求头
 *
 * 所有 API 模块应使用此函数，避免重复实现
 */
export function getAuthHeaders(): Record<string, string> {
  const token = authStorage.getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

/**
 * 获取当前用户 ID
 *
 * 统一从 useCurrentUserId.ts 导出，确保单一真相来源
 */
export const getCurrentUserId = _getCurrentUserId

// ==================== Axios 客户端 ====================

// 创建统一的 axios 实例
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 JWT token
apiClient.interceptors.request.use((config) => {
  const token = authStorage.getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else if (process.env.NODE_ENV === 'development') {
    // 开发环境：使用默认测试用户
    const testUserId = devStorage.getTestUserId() || 'user-test-001'
    devStorage.setTestUserId(testUserId)
    config.headers['X-Dev-User-Id'] = testUserId
  }
  return config
})

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isDev = process.env.NODE_ENV === 'development'
    if (isDev) {
      console.error('API Error:', error.response?.data || error.message)
    }
    // 包装错误信息
    const wrappedError = new Error(
      error.response?.data?.detail || error.message || '请求失败'
    ) as any
    wrappedError.detail = error.response?.data?.detail
    wrappedError.status = error.response?.status
    wrappedError.data = error.response?.data
    throw wrappedError
  }
)

export default apiClient