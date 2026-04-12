/**
 * 统一的本地存储工具
 *
 * 封装 localStorage 操作，提供类型安全的存取方法
 *
 * 使用示例:
 *   import { authStorage } from '@/utils/storage'
 *
 *   // 获取 token
 *   const token = authStorage.getToken()
 *
 *   // 设置用户信息
 *   authStorage.setUser({ username: 'test', name: 'Test User' })
 *
 *   // 清除所有认证信息
 *   authStorage.clear()
 */

// ==================== 类型定义 ====================

export interface UserInfo {
  username: string
  name: string
  email?: string
  age?: number
  gender?: string
  avatar?: string
  [key: string]: any
}

export interface AuthData {
  token: string
  user: UserInfo
}

// ==================== 存储键常量 ====================

const STORAGE_KEYS = {
  JWT_TOKEN: 'jwt_token',
  TOKEN: 'token', // 兼容旧版本
  USER_INFO: 'user_info',
  REGISTRATION_COMPLETED: 'has_completed_registration_conversation',
  TEST_USER_ID: 'test_user_id',
  PWA_INSTALL_DISMISSED: 'pwa-install-dismissed',
  HER_SLEEPING_IN_CHAT: 'her_sleeping_in_chat', // 聊天室中 Her 休眠偏好
} as const

// ==================== 认证存储 ====================

export const authStorage = {
  /**
   * 获取 JWT Token
   */
  getToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.JWT_TOKEN) || localStorage.getItem(STORAGE_KEYS.TOKEN)
  },

  /**
   * 设置 JWT Token
   */
  setToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.JWT_TOKEN, token)
  },

  /**
   * 获取用户信息
   */
  getUser(): UserInfo | null {
    const userStr = localStorage.getItem(STORAGE_KEYS.USER_INFO)
    if (!userStr) return null

    try {
      return JSON.parse(userStr) as UserInfo
    } catch {
      // JSON 解析失败，返回 null
      return null
    }
  },

  /**
   * 获取用户 ID (username)
   */
  getUserId(): string {
    const user = this.getUser()
    return user?.username || 'anonymous'
  },

  /**
   * 设置用户信息
   */
  setUser(user: UserInfo): void {
    localStorage.setItem(STORAGE_KEYS.USER_INFO, JSON.stringify(user))
  },

  /**
   * 保存认证数据 (登录成功后调用)
   */
  saveAuth(data: AuthData): void {
    this.setToken(data.token)
    this.setUser(data.user)
  },

  /**
   * 检查是否已登录
   */
  isAuthenticated(): boolean {
    return !!this.getToken()
  },

  /**
   * 清除所有认证信息
   */
  clear(): void {
    localStorage.removeItem(STORAGE_KEYS.JWT_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER_INFO)
    localStorage.removeItem(STORAGE_KEYS.REGISTRATION_COMPLETED)
  },
}

// ==================== 注册流程存储 ====================

export const registrationStorage = {
  /**
   * 检查是否已完成注册对话
   */
  isCompleted(): boolean {
    return localStorage.getItem(STORAGE_KEYS.REGISTRATION_COMPLETED) === 'true'
  },

  /**
   * 标记注册对话已完成
   */
  markCompleted(): void {
    localStorage.setItem(STORAGE_KEYS.REGISTRATION_COMPLETED, 'true')
  },

  /**
   * 重置注册对话状态
   */
  reset(): void {
    localStorage.removeItem(STORAGE_KEYS.REGISTRATION_COMPLETED)
  },
}

// ==================== 开发环境存储 ====================

export const devStorage = {
  /**
   * 获取测试用户 ID
   */
  getTestUserId(): string | null {
    return localStorage.getItem(STORAGE_KEYS.TEST_USER_ID)
  },

  /**
   * 设置测试用户 ID
   */
  setTestUserId(userId: string): void {
    localStorage.setItem(STORAGE_KEYS.TEST_USER_ID, userId)
  },
}

// ==================== PWA 存储 ====================

export const pwaStorage = {
  /**
   * 检查是否关闭了安装提示
   */
  isInstallDismissed(): boolean {
    return !!localStorage.getItem(STORAGE_KEYS.PWA_INSTALL_DISMISSED)
  },

  /**
   * 记录关闭安装提示
   */
  dismissInstall(): void {
    localStorage.setItem(STORAGE_KEYS.PWA_INSTALL_DISMISSED, Date.now().toString())
  },
}

// ==================== Her 悬浮球存储 ====================

export const herStorage = {
  /**
   * 检查在聊天室中 Her 是否处于休眠状态
   */
  isSleepingInChat(): boolean {
    return localStorage.getItem(STORAGE_KEYS.HER_SLEEPING_IN_CHAT) === 'true'
  },

  /**
   * 设置 Her 在聊天室中的休眠状态
   */
  setSleepingInChat(sleeping: boolean): void {
    localStorage.setItem(STORAGE_KEYS.HER_SLEEPING_IN_CHAT, sleeping ? 'true' : 'false')
  },
}

// ==================== 通用存储工具 ====================

export const storage = {
  /**
   * 获取存储项
   */
  get<T = string>(key: string): T | null {
    const value = localStorage.getItem(key)
    if (value === null) return null

    try {
      return JSON.parse(value) as T
    } catch {
      return value as unknown as T
    }
  },

  /**
   * 设置存储项
   */
  set<T>(key: string, value: T): void {
    if (typeof value === 'string') {
      localStorage.setItem(key, value)
    } else {
      localStorage.setItem(key, JSON.stringify(value))
    }
  },

  /**
   * 移除存储项
   */
  remove(key: string): void {
    localStorage.removeItem(key)
  },

  /**
   * 清空所有存储
   */
  clearAll(): void {
    localStorage.clear()
  },
}

// 默认导出
export default {
  auth: authStorage,
  registration: registrationStorage,
  dev: devStorage,
  pwa: pwaStorage,
  her: herStorage,
  ...storage,
}