/**
 * AI Native 应用状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  ChatMessage,
  ConversationState,
  AIAgent,
  GenerativeUIResponse,
  FeedItem,
  Notification,
  Reputation,
  AuthorType,
  FeedSort,
} from '@/types/ai-native';
import { aiApi } from '@/lib/api-ai-native';

interface AIState {
  // 对话状态
  conversations: Map<string, ConversationState>;
  activeConversationId: string | null;
  currentUserId: string;

  // AI Agent 状态
  agents: AIAgent[];
  agentsLoading: boolean;

  // Generative UI 状态
  uiComponents: GenerativeUIResponse | null;
  uiLoading: boolean;

  // Feed 状态
  feedItems: FeedItem[];
  feedLoading: boolean;
  feedSort: FeedSort;

  // 通知状态
  notifications: Notification[];
  unreadCount: number;

  // 声誉状态
  reputation: Reputation | null;

  // 用户偏好
  preferredAuthorType: AuthorType | 'all';

  // Actions - 对话
  setActiveConversation: (id: string | null) => void;
  sendMessage: (message: string, context?: Record<string, any>) => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
  clearConversation: (conversationId: string) => void;

  // Actions - Agent
  loadAgents: () => Promise<void>;

  // Actions - UI
  loadGenerativeUI: (limit?: number, authorType?: AuthorType) => Promise<void>;

  // Actions - Feed
  loadFeed: (sort?: FeedSort) => Promise<void>;
  setFeedSort: (sort: FeedSort) => void;

  // Actions - Notifications
  loadNotifications: () => Promise<void>;
  markNotificationAsRead: (notificationId: string) => Promise<void>;
  markAllNotificationsAsRead: () => Promise<void>;

  // Actions - Reputation
  loadReputation: () => Promise<void>;

  // Actions - 用户
  setCurrentUserId: (id: string) => void;
  setPreferredAuthorType: (type: AuthorType | 'all') => void;
}

// 演示用户 ID
const DEMO_USER_ID = 'user_001';

export const useAINativeStore = create<AIState>()(
  persist(
    (set, get) => ({
      // 初始状态
      conversations: new Map(),
      activeConversationId: null,
      currentUserId: DEMO_USER_ID,

      agents: [],
      agentsLoading: false,

      uiComponents: null,
      uiLoading: false,

      feedItems: [],
      feedLoading: false,
      feedSort: 'hot',

      notifications: [],
      unreadCount: 0,

      reputation: null,

      preferredAuthorType: 'all',

      // 设置当前用户 ID
      setCurrentUserId: (id: string) => {
        set({ currentUserId: id });
      },

      // 设置偏好的作者类型
      setPreferredAuthorType: (type: AuthorType | 'all') => {
        set({ preferredAuthorType: type });
      },

      // 设置活跃对话
      setActiveConversation: (id: string | null) => {
        set({ activeConversationId: id });
      },

      // 发送消息
      sendMessage: async (message: string, context?: Record<string, any>) => {
        const { currentUserId, activeConversationId, conversations } = get();

        try {
          const response = await aiApi.chat.chat(
            currentUserId,
            message,
            activeConversationId || undefined,
            context
          );

          set((state) => {
            const newConversationId = response.conversation_id;
            const newMessage: ChatMessage = {
              ...response.message,
              suggestedActions: response.suggested_actions,
              metadata: response.metadata,
            };

            const existingConversation = conversations.get(newConversationId);
            const updatedConversation: ConversationState = existingConversation
              ? {
                  ...existingConversation,
                  messages: [...existingConversation.messages, newMessage],
                  updatedAt: new Date().toISOString(),
                }
              : {
                  conversationId: newConversationId,
                  userId: currentUserId,
                  messages: [newMessage],
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  context: context || {},
                };

            const newConversations = new Map(conversations);
            newConversations.set(newConversationId, updatedConversation);

            return {
              conversations: newConversations,
              activeConversationId: newConversationId,
            };
          });
        } catch (error) {
          console.error('Failed to send message:', error);
          throw error;
        }
      },

      // 加载对话
      loadConversation: async (conversationId: string) => {
        try {
          const conversation = await aiApi.chat.getConversation(conversationId);
          set((state) => {
            const newConversations = new Map(state.conversations);
            newConversations.set(conversationId, conversation);
            return {
              conversations: newConversations,
              activeConversationId: conversationId,
            };
          });
        } catch (error) {
          console.error('Failed to load conversation:', error);
          throw error;
        }
      },

      // 清除对话
      clearConversation: async (conversationId: string) => {
        try {
          await aiApi.chat.deleteConversation(conversationId);
          set((state) => {
            const newConversations = new Map(state.conversations);
            newConversations.delete(conversationId);
            return {
              conversations: newConversations,
              activeConversationId:
                state.activeConversationId === conversationId
                  ? null
                  : state.activeConversationId,
            };
          });
        } catch (error) {
          console.error('Failed to delete conversation:', error);
        }
      },

      // 加载 AI Agent 状态
      loadAgents: async () => {
        set({ agentsLoading: true });
        try {
          const response = await aiApi.ui.getAgentStatus();
          set({ agents: response.agents, agentsLoading: false });
        } catch (error) {
          console.error('Failed to load agents:', error);
          set({ agentsLoading: false });
        }
      },

      // 加载 Generative UI
      loadGenerativeUI: async (limit: number = 20, authorType?: AuthorType) => {
        set({ uiLoading: true });
        try {
          const response = await aiApi.ui.getContentFeed(limit, authorType);
          set({ uiComponents: response, uiLoading: false });
        } catch (error) {
          console.error('Failed to load generative UI:', error);
          set({ uiLoading: false });
        }
      },

      // 加载 Feed
      loadFeed: async (sort: FeedSort = 'hot') => {
        set({ feedLoading: true, feedSort: sort });
        try {
          const { currentUserId, preferredAuthorType } = get();

          // 根据排序类型获取不同的 feed
          let response;
          if (sort === 'hot' || sort === 'new' || sort === 'top' || sort === 'rising') {
            response = await aiApi.ui.getContentFeed(20, preferredAuthorType === 'all' ? undefined : preferredAuthorType);
          } else if (sort === 'ai') {
            response = await aiApi.ui.getContentFeed(20, 'ai');
          } else if (sort === 'human') {
            response = await aiApi.ui.getContentFeed(20, 'human');
          } else {
            response = await aiApi.ui.getContentFeed(20);
          }

          // 转换为 FeedItem 格式
          const feedItems: FeedItem[] = response.components
            .filter((c) => c.type === 'content_card')
            .map((c) => ({
              id: c.data.id,
              type: c.data.type,
              title: c.data.title,
              content: c.data.content,
              authorBadge: c.data.author_badge,
              createdAt: c.data.created_at,
              tags: c.data.tags || [],
              aiContributionRatio: c.data.ai_contribution_ratio,
              moderationStatus: c.data.moderation_status,
              decisionTraceId: c.data.decision_trace_id,
              upvotes: Math.floor(Math.random() * 100),
              downvotes: Math.floor(Math.random() * 10),
              commentCount: Math.floor(Math.random() * 50),
            }));

          set({ feedItems, feedLoading: false });
        } catch (error) {
          console.error('Failed to load feed:', error);
          set({ feedLoading: false });
        }
      },

      // 设置 Feed 排序
      setFeedSort: (sort: FeedSort) => {
        set({ feedSort: sort });
        get().loadFeed(sort);
      },

      // 加载通知
      loadNotifications: async () => {
        try {
          const { currentUserId } = get();
          const [notificationsResp, unreadResp] = await Promise.all([
            aiApi.notifications.getUserNotifications(currentUserId, 50),
            aiApi.notifications.getUnreadCount(currentUserId),
          ]);

          set({
            notifications: notificationsResp.notifications,
            unreadCount: unreadResp.unread_count,
          });
        } catch (error) {
          console.error('Failed to load notifications:', error);
        }
      },

      // 标记通知为已读
      markNotificationAsRead: async (notificationId: string) => {
        try {
          const { currentUserId } = get();
          await aiApi.notifications.markAsRead(currentUserId, notificationId);
          set((state) => ({
            notifications: state.notifications.map((n) =>
              n.id === notificationId ? { ...n, isRead: true } : n
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          }));
        } catch (error) {
          console.error('Failed to mark notification as read:', error);
        }
      },

      // 标记所有通知为已读
      markAllNotificationsAsRead: async () => {
        try {
          const { currentUserId } = get();
          await aiApi.notifications.markAllAsRead(currentUserId);
          set((state) => ({
            notifications: state.notifications.map((n) => ({ ...n, isRead: true })),
            unreadCount: 0,
          }));
        } catch (error) {
          console.error('Failed to mark all as read:', error);
        }
      },

      // 加载声誉
      loadReputation: async () => {
        try {
          const reputation = await aiApi.reputation.getMyReputation();
          set({ reputation });
        } catch (error) {
          console.error('Failed to load reputation:', error);
        }
      },
    }),
    {
      name: 'ai-native-storage',
      partialize: (state) => ({
        currentUserId: state.currentUserId,
        preferredAuthorType: state.preferredAuthorType,
        activeConversationId: state.activeConversationId,
      }),
    }
  )
);
