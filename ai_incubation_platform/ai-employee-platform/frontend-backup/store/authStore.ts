/**
 * 认证 Store
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Tenant, LoginResponse } from '@/types';
import { authApi } from '@/services/http';

interface AuthState {
  // 状态
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (username: string, password: string) => Promise<LoginResponse>;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tenant: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(username, password);
          // 保存 token
          localStorage.setItem('ai_employee_token', response.access_token);
          localStorage.setItem('ai_employee_refresh_token', response.refresh_token);
          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
          });
          return response;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : '登录失败';
          set({ error: errorMessage, isLoading: false });
          throw error;
        }
      },

      logout: () => {
        authApi.logout();
        set({
          user: null,
          tenant: null,
          isAuthenticated: false,
        });
      },

      updateUser: (userData) => {
        const currentUser = get().user;
        if (currentUser) {
          set({ user: { ...currentUser, ...userData } });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        tenant: state.tenant,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
