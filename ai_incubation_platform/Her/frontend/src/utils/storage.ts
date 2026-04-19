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
  id?: string  // 🎯 [修复] 添加数据库 UUID
  username: string
  name: string
  email?: string
  age?: number
  gender?: string
  location?: string
  relationship_goal?: string
  avatar?: string
  // ===== QuickStart 收集的重要匹配字段 =====
  education?: string  // 学历
  occupation?: string // 职业
  income?: number     // 收入（万元）
  housing?: string    // 房产情况
  // ===== 核心维度（无法行为推断，必须问卷）=====
  height?: number     // 身高 (v11)
  has_car?: boolean   // 是否有车 (v15)
  want_children?: string  // 是否想要孩子 (v17) 🔴 一票否决
  spending_style?: string // 消费观念 (v27) 🔴 一票否决
  family_importance?: number  // 家庭重要程度 (v16)
  work_life_balance?: string  // 工作生活平衡 (v23)
  migration_willingness?: number  // 迁移意愿 (v160)
  accept_remote?: boolean   // 异地接受度 (v163)
  sleep_type?: string  // 作息类型 (v88)
  [key: string]: any
}

export interface AuthData {
  access_token: string
  refresh_token: string
  user: UserInfo
}

// ==================== 存储键常量 ====================

const STORAGE_KEYS = {
  JWT_TOKEN: 'jwt_token',
  TOKEN: 'token', // 兼容旧版本
  REFRESH_TOKEN: 'refresh_token', // 🔧 [新增] 刷新令牌
  USER_INFO: 'user_info',
  REGISTRATION_COMPLETED: 'has_completed_registration_conversation',
  TEST_USER_ID: 'test_user_id',
  PWA_INSTALL_DISMISSED: 'pwa-install-dismissed',
  HER_SLEEPING_IN_CHAT: 'her_sleeping_in_chat', // 聊天室中 Her 休眠偏好
  CHAT_MESSAGES: 'chat_messages', // ChatInterface 消息持久化
  FEATURE_GUIDE_SHOWN: 'feature_guide_shown', // 🔧 [问题17方案B] 首次功能引导已显示
} as const

// ==================== 认证存储 ====================

export const authStorage = {
  /**
   * 获取 JWT Token (access_token)
   */
  getToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.JWT_TOKEN) || localStorage.getItem(STORAGE_KEYS.TOKEN)
  },

  /**
   * 设置 JWT Token (access_token)
   */
  setToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.JWT_TOKEN, token)
  },

  /**
   * 获取 Refresh Token
   * 🔧 [新增] 用于刷新 access_token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
  },

  /**
   * 设置 Refresh Token
   */
  setRefreshToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, token)
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
   * 获取用户 ID
   *
   * 🎯 [修复] 优先返回数据库 UUID (user.id)，用于后端查询
   * 如果没有 id，则返回 username（兼容旧数据）
   */
  getUserId(): string {
    const user = this.getUser()
    // 优先返回数据库 UUID
    if (user?.id) {
      return user.id
    }
    // 兼容旧数据：返回 username
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
   * 🔧 [修复] 存储 access_token + refresh_token
   */
  saveAuth(data: AuthData): void {
    // 兼容旧格式：如果传入的是 { token, user }，则只存储 token
    if ('token' in data && !('access_token' in data)) {
      this.setToken((data as any).token)
    } else {
      this.setToken(data.access_token)
      if (data.refresh_token) {
        this.setRefreshToken(data.refresh_token)
      }
    }
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
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
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
   * 🔧 [问题16方案A] 默认返回 false（唤醒），让用户能立刻看到悬浮球
   */
  isSleepingInChat(): boolean {
    const value = localStorage.getItem(STORAGE_KEYS.HER_SLEEPING_IN_CHAT)
    // 🔧 [修复] 新用户默认唤醒（休眠需要用户主动设置）
    // 只有明确设置为 'true' 才返回 true
    return value === 'true'
  },

  /**
   * 设置 Her 在聊天室中的休眠状态
   */
  setSleepingInChat(sleeping: boolean): void {
    localStorage.setItem(STORAGE_KEYS.HER_SLEEPING_IN_CHAT, sleeping ? 'true' : 'false')
  },
}

// ==================== 首次引导弹窗存储 ====================

/**
 * 🔧 [问题17方案B] 首次功能引导弹窗存储
 * 新用户首次进入时显示功能引导，告知用户如何使用 Her
 */
export const guideStorage = {
  /**
   * 检查是否已显示过功能引导弹窗
   */
  isFeatureGuideShown(): boolean {
    return localStorage.getItem(STORAGE_KEYS.FEATURE_GUIDE_SHOWN) === 'true'
  },

  /**
   * 标记功能引导弹窗已显示
   */
  markFeatureGuideShown(): void {
    localStorage.setItem(STORAGE_KEYS.FEATURE_GUIDE_SHOWN, 'true')
  },

  /**
   * 重置功能引导弹窗状态（用于测试）
   */
  resetFeatureGuide(): void {
    localStorage.removeItem(STORAGE_KEYS.FEATURE_GUIDE_SHOWN)
  },
}

// ==================== ChatInterface 消息存储 ====================

// 消息存储上限（防止 localStorage 超限）
const MAX_STORED_MESSAGES = 30

export interface StoredMessage {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  timestamp: string
  generativeCard?: string
  generativeData?: unknown
  featureAction?: string
  suggestions?: string[]
  next_actions?: string[]
  matches?: unknown[]
}

export const chatStorage = {
  /**
   * 获取用户的聊天消息
   * @param userId 用户 ID，用于区分不同用户的消息
   */
  getMessages(userId: string): StoredMessage[] {
    const key = `${STORAGE_KEYS.CHAT_MESSAGES}_${userId}`
    const data = localStorage.getItem(key)
    if (!data) return []

    try {
      const messages = JSON.parse(data) as StoredMessage[]
      // 过滤掉过期消息（超过 7 天）
      const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
      return messages.filter(msg => {
        const msgTime = new Date(msg.timestamp).getTime()
        return msgTime > sevenDaysAgo
      })
    } catch {
      return []
    }
  },

  /**
   * 保存用户的聊天消息
   * @param userId 用户 ID
   * @param messages 消息列表
   */
  setMessages(userId: string, messages: StoredMessage[]): void {
    const key = `${STORAGE_KEYS.CHAT_MESSAGES}_${userId}`
    // 只保留最近的消息（防止 localStorage 超限）
    const toStore = messages.slice(-MAX_STORED_MESSAGES)
    try {
      localStorage.setItem(key, JSON.stringify(toStore))
    } catch (e) {
      // localStorage 超限，清理旧数据后重试
      console.warn('[chatStorage] localStorage 超限，清理旧数据')
      localStorage.removeItem(key)
      try {
        localStorage.setItem(key, JSON.stringify(toStore.slice(-15)))
      } catch {
        // 仍然失败，放弃存储
        console.error('[chatStorage] 无法存储消息')
      }
    }
  },

  /**
   * 清除用户的聊天消息
   * @param userId 用户 ID
   */
  clearMessages(userId: string): void {
    const key = `${STORAGE_KEYS.CHAT_MESSAGES}_${userId}`
    localStorage.removeItem(key)
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
  guide: guideStorage, // 🔧 [问题17方案B] 首次引导弹窗存储
  chat: chatStorage,
  ...storage,
}