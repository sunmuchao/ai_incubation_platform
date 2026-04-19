/**
 * 统一的 Axios API 客户端配置
 *
 * 所有 API 模块应导入此实例，避免重复配置
 *
 * 统一认证入口：
 * - getAuthHeaders() - 获取认证头
 * - getCurrentUserId() - 获取当前用户 ID（从 useCurrentUserId.ts 统一导出）
 * - refreshToken() - 自动刷新令牌（401 时触发）
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
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

// ==================== Token 刷新机制 ====================

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

/**
 * 刷新访问令牌
 *
 * 当 access_token 过期时，使用 refresh_token 获取新的令牌对
 * 返回 true 表示刷新成功，false 表示刷新失败需要重新登录
 */
async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = authStorage.getRefreshToken()

  if (!refreshToken) {
    console.warn('[TokenRefresh] No refresh_token available, user needs to re-login')
    return false
  }

  try {
    const response = await axios.post('/api/users/refresh', {
      refresh_token: refreshToken
    })

    const { access_token, refresh_token: new_refresh_token } = response.data

    // 存储新的令牌对
    authStorage.setToken(access_token)
    if (new_refresh_token) {
      authStorage.setRefreshToken(new_refresh_token)
    }

    console.info('[TokenRefresh] Token refreshed successfully')
    return true
  } catch (error) {
    console.warn('[TokenRefresh] Refresh failed:', error)
    // 刷新失败，清除认证信息
    authStorage.clear()
    return false
  }
}

/**
 * 处理 401 错误并尝试刷新令牌
 *
 * 返回 true 表示已成功刷新，可以重试请求
 * 返回 false 表示需要重新登录
 */
async function handle401AndRefresh(originalRequest: InternalAxiosRequestConfig): Promise<boolean> {
  // 防止并发刷新：多个请求同时 401 时，只刷新一次
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  refreshPromise = refreshAccessToken()

  try {
    const success = await refreshPromise
    if (success) {
      // 更新原请求的 Authorization header
      const newToken = authStorage.getToken()
      if (newToken && originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
      }
    }
    return success
  } finally {
    isRefreshing = false
    refreshPromise = null
  }
}

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

// 响应拦截器 - 统一错误处理 + 401 自动刷新
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig
    const isDev = process.env.NODE_ENV === 'development'

    // 401 错误：尝试刷新令牌后重试
    if (error.response?.status === 401 && originalRequest) {
      // 防止无限循环：如果刷新请求本身也 401，不再重试
      const isRefreshRequest = originalRequest.url?.includes('/users/refresh')

      if (!isRefreshRequest) {
        console.warn('[API] 401 Unauthorized, attempting token refresh...')

        const refreshed = await handle401AndRefresh(originalRequest)

        if (refreshed) {
          // 刷新成功，重试原请求
          console.info('[API] Token refreshed, retrying original request')
          return apiClient(originalRequest)
        } else {
          // 刷新失败，跳转到登录页
          console.warn('[API] Token refresh failed, redirecting to login')
          // 触发全局登录事件（App 组件监听并跳转）
          window.dispatchEvent(new CustomEvent('auth:expired', { detail: { reason: 'token_refresh_failed' } }))
        }
      }
    }

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