/**
 * 统一的 Axios API 客户端配置
 *
 * 所有 API 模块应导入此实例，避免重复配置
 */

import axios from 'axios'

const API_BASE_URL = ''

// 创建统一的 axios 实例
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else if (process.env.NODE_ENV === 'development') {
    // 开发环境：使用默认测试用户
    const testUserId = localStorage.getItem('test_user_id') || 'user-test-001'
    localStorage.setItem('test_user_id', testUserId)
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