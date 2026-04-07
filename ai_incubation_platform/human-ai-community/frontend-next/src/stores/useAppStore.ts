/**
 * 应用状态管理 (Zustand)
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Post, Comment, Channel, Notification, User, FeedSort, AuthorType } from '@/types';
import { api } from '@/lib/api';

interface AppState {
  // 当前用户
  currentUser: User | null;
  setCurrentUser: (user: User | null) => void;

  // 帖子列表
  posts: Post[];
  setPosts: (posts: Post[]) => void;
  addPost: (post: Post) => void;
  updatePost: (id: string, updates: Partial<Post>) => void;

  // 频道列表
  channels: Channel[];
  setChannels: (channels: Channel[]) => void;

  // 通知列表
  notifications: Notification[];
  setNotifications: (notifications: Notification[]) => void;
  addNotification: (notification: Notification) => void;
  markNotificationAsRead: (id: string) => void;
  markAllNotificationsAsRead: () => void;
  getUnreadCount: () => number;

  // 当前标签页
  currentTab: string;
  setCurrentTab: (tab: string) => void;

  //  Feed 排序
  feedSort: FeedSort;
  setFeedSort: (sort: FeedSort) => void;

  // 加载状态
  loading: boolean;
  setLoading: (loading: boolean) => void;

  // 错误状态
  error: string | null;
  setError: (error: string | null) => void;

  // 主题
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;

  // 语言
  language: string;
  setLanguage: (language: string) => void;

  // WebSocket 连接状态
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // 当前用户
      currentUser: null,
      setCurrentUser: (user) => set({ currentUser: user }),

      // 帖子列表
      posts: [],
      setPosts: (posts) => set({ posts }),
      addPost: (post) => set((state) => ({ posts: [post, ...state.posts] })),
      updatePost: (id, updates) =>
        set((state) => ({
          posts: state.posts.map((p) => (p.id === id ? { ...p, ...updates } : p)),
        })),

      // 频道列表
      channels: [],
      setChannels: (channels) => set({ channels }),

      // 通知列表
      notifications: [],
      setNotifications: (notifications) => set({ notifications }),
      addNotification: (notification) =>
        set((state) => ({ notifications: [notification, ...state.notifications] })),
      markNotificationAsRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, isRead: true } : n
          ),
        })),
      markAllNotificationsAsRead: () =>
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, isRead: true })),
        })),
      getUnreadCount: () => {
        const state = get();
        return state.notifications.filter((n) => !n.isRead).length;
      },

      // 当前标签页
      currentTab: 'home',
      setCurrentTab: (tab) => set({ currentTab: tab }),

      // Feed 排序
      feedSort: 'hot',
      setFeedSort: (sort) => set({ feedSort: sort }),

      // 加载状态
      loading: false,
      setLoading: (loading) => set({ loading }),

      // 错误状态
      error: null,
      setError: (error) => set({ error }),

      // 主题
      theme: 'dark',
      setTheme: (theme) => {
        set({ theme });
        if (typeof document !== 'undefined') {
          document.documentElement.classList.toggle('light', theme === 'light');
        }
      },

      // 语言
      language: 'zh',
      setLanguage: (language) => set({ language }),

      // WebSocket 连接状态
      wsConnected: false,
      setWsConnected: (connected) => set({ wsConnected: connected }),
    }),
    {
      name: 'human-ai-community-storage',
      partialize: (state) => ({
        theme: state.theme,
        language: state.language,
        currentTab: state.currentTab,
      }),
    }
  )
);

// 数据加载 Actions
export const appActions = {
  // 加载 Feed
  loadFeed: async (sort: FeedSort = 'hot') => {
    try {
      const posts = await api.feed.get(sort);
      useAppStore.getState().setPosts(posts);
    } catch (error) {
      console.error('加载 Feed 失败:', error);
      useAppStore.getState().setError('加载失败，请稍后重试');
    }
  },

  // 加载频道
  loadChannels: async () => {
    try {
      const channels = await api.channels.list();
      useAppStore.getState().setChannels(channels);
    } catch (error) {
      console.error('加载频道失败:', error);
    }
  },

  // 加载通知
  loadNotifications: async () => {
    try {
      const notifications = await api.notifications.list(50);
      useAppStore.getState().setNotifications(notifications);
    } catch (error) {
      console.error('加载通知失败:', error);
    }
  },

  // 标记通知已读
  markAsRead: async (id: string) => {
    try {
      await api.notifications.markAsRead(id);
      useAppStore.getState().markNotificationAsRead(id);
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  },

  // 全部标记已读
  markAllAsRead: async () => {
    try {
      await api.notifications.markAllAsRead();
      useAppStore.getState().markAllNotificationsAsRead();
    } catch (error) {
      console.error('全部标记已读失败:', error);
    }
  },

  // 发布帖子
  createPost: async (data: {
    title: string;
    content: string;
    authorId: string;
    authorType: AuthorType;
    channelId?: string;
    tags?: string[];
  }) => {
    try {
      const post = await api.posts.create({
        title: data.title,
        content: data.content,
        author_id: data.authorId,
        channel_id: data.channelId,
        tags: data.tags,
      });
      useAppStore.getState().addPost(post);
      return post;
    } catch (error) {
      console.error('发布帖子失败:', error);
      throw error;
    }
  },
};
