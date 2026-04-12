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
  // 优先使用真实用户 ID
  const userId = authStorage.getUserId()
  if (userId) {
    return userId
  }

  // 开发环境使用测试用户 ID
  const testUserId = devStorage.getTestUserId()
  if (testUserId) {
    return testUserId
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
  return authStorage.getUserId() || devStorage.getTestUserId() || 'user-test-001'
}

export default useCurrentUserId