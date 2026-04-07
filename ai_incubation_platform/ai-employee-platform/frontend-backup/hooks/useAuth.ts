/**
 * 认证 Hook
 */
import { useCallback } from 'react';
import { useAuthStore } from '@/store/authStore';

export const useAuth = () => {
  const { user, isAuthenticated, isLoading, error, login, logout, updateUser, clearError } = useAuthStore();

  // 检查权限
  const hasPermission = useCallback((requiredRole?: string) => {
    if (!user) return false;
    if (!requiredRole) return true;

    const roleHierarchy: Record<string, number> = {
      visitor: 0,
      employee: 1,
      enterprise: 2,
      admin: 3,
    };

    return roleHierarchy[user.role] >= roleHierarchy[requiredRole];
  }, [user]);

  // 检查是否是企业管理员
  const isEnterpriseAdmin = useCallback(() => {
    return user?.role === 'enterprise' || user?.role === 'admin';
  }, [user]);

  // 检查是否是普通员工
  const isEmployee = useCallback(() => {
    return user?.role === 'employee';
  }, [user]);

  return {
    // 状态
    user,
    isAuthenticated,
    isLoading,
    error,

    // 方法
    login,
    logout,
    updateUser,
    clearError,

    // 权限检查
    hasPermission,
    isEnterpriseAdmin,
    isEmployee,
  };
};
