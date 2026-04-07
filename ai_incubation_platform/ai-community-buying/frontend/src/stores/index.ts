import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, CartItem, Notification } from '@/types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
  updateUser: (user: Partial<User>) => void
}

interface SettingsState {
  theme: 'light' | 'dark'
  language: 'zh' | 'en'
  notifications: boolean
  soundEnabled: boolean
  setTheme: (theme: 'light' | 'dark') => void
  setLanguage: (language: 'zh' | 'en') => void
  toggleNotifications: () => void
  toggleSound: () => void
}

interface CartState {
  items: CartItem[]
  addItem: (item: CartItem) => void
  removeItem: (id: string) => void
  updateQuantity: (id: string, quantity: number) => void
  toggleSelected: (id: string) => void
  clearCart: () => void
  selectedItems: CartItem[]
  totalAmount: number
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  setNotifications: (notifications: Notification[]) => void
  addNotification: (notification: Notification) => void
  markAsRead: (ids: number[]) => void
  markAllAsRead: () => void
  clearNotifications: () => void
}

// Auth Store
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) => {
        localStorage.setItem('auth_token', token)
        set({ token, user, isAuthenticated: true })
      },
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ user: null, token: null, isAuthenticated: false })
      },
      updateUser: (userData) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        })),
    }),
    {
      name: 'auth-storage',
    }
  )
)

// Settings Store
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'light',
      language: 'zh',
      notifications: true,
      soundEnabled: true,
      setTheme: (theme) => {
        set({ theme })
        if (theme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },
      setLanguage: (language) => {
        set({ language })
        localStorage.setItem('i18n-lang', language)
      },
      toggleNotifications: () =>
        set((state) => ({ notifications: !state.notifications })),
      toggleSound: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
    }),
    {
      name: 'settings-storage',
    }
  )
)

// Cart Store
export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (item) =>
        set((state) => {
          const existingItem = state.items.find((i) => i.id === item.id)
          if (existingItem) {
            return {
              items: state.items.map((i) =>
                i.id === item.id ? { ...i, quantity: i.quantity + item.quantity } : i
              ),
            }
          }
          return { items: [...state.items, item] }
        }),
      removeItem: (id) =>
        set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
      updateQuantity: (id, quantity) =>
        set((state) => ({
          items: state.items.map((i) => (i.id === id ? { ...i, quantity: Math.max(0, quantity) } : i)),
        })),
      toggleSelected: (id) =>
        set((state) => ({
          items: state.items.map((i) =>
            i.id === id ? { ...i, selected: !i.selected } : i
          ),
        })),
      clearCart: () => set({ items: [] }),
      get selectedItems() {
        return get().items.filter((i) => i.selected)
      },
      get totalAmount() {
        return get().items
          .filter((i) => i.selected && i.product)
          .reduce((sum, i) => sum + (i.product?.price || 0) * i.quantity, 0)
      },
    }),
    {
      name: 'cart-storage',
    }
  )
)

// Notification Store
export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  unreadCount: 0,
  setNotifications: (notifications) =>
    set({
      notifications,
      unreadCount: notifications.filter((n) => !n.isRead).length,
    }),
  addNotification: (notification) =>
    set((state) => ({
      notifications: [notification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    })),
  markAsRead: (ids) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        ids.includes(n.id) ? { ...n, isRead: true } : n
      ),
      unreadCount: state.unreadCount - ids.length,
    })),
  markAllAsRead: () =>
    set({
      notifications: [],
      unreadCount: 0,
    }),
  clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
}))
