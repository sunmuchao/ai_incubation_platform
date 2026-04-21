/**
 * 获取当前用户 ID 的通用 Hook
 *
 * 统一封装用户 ID 获取逻辑，替代多处重复的 authStorage.getUserId() || devStorage.getTestUserId() || 'user-test-001'
 *
 * 使用示例:
 *   import { useCurrentUserId } from '@/hooks/useCurrentUserId'
 *
 *   const userId = useCurrentUserId()
 *   // 返回当前用户 ID，或测试用户 ID，或默认值 'user-test-001'
 */

import { authStorage, devStorage } from '../utils/storage'

/**
 * 获取当前用户 ID（Hook 版本）
 *
 * @returns 当前用户 ID 字符串
 */
export function useCurrentUserId(): string {
  const token = authStorage.getToken()

  // 有 token 时优先使用真实登录用户
  if (token) {
    const userId = authStorage.getUserId()
    if (userId) {
      return userId
    }
  }

  // 无 token 时优先使用开发态测试用户（与 API 请求头一致）
  const testUserId = devStorage.getTestUserId()
  if (testUserId) {
    return testUserId
  }

  // 次选本地用户 ID（兼容历史数据）
  const userId = authStorage.getUserId()
  if (userId) {
    return userId
  }

  // 默认 fallback
  return 'user-test-001'
}

/**
 * 获取当前用户 ID（非 Hook 版本，用于 API 文件）
 *
 * @returns 当前用户 ID 字符串
 */
export function getCurrentUserId(): string {
  const token = authStorage.getToken()

  if (token) {
    return authStorage.getUserId() || devStorage.getTestUserId() || 'user-test-001'
  }

  return devStorage.getTestUserId() || authStorage.getUserId() || 'user-test-001'
}

export default useCurrentUserId