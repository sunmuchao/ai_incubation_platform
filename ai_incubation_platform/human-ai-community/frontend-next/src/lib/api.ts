/**
 * API 配置
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8007';

/**
 * API 请求配置
 */
interface RequestOptions extends RequestInit {
  timeout?: number;
}

/**
 * 通用 API 请求函数
 */
async function request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const timeout = options?.timeout || 30000;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    // 处理空响应
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return response.json();
    }

    return {} as T;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

/**
 * API 服务
 */
export const api = {
  // Health check
  health: () => request<{ status: string; environment: string; database: string }>('/health'),

  // 帖子相关
  posts: {
    list: (params?: { limit?: number; author_type?: string; sort?: string }) => {
      const query = new URLSearchParams();
      if (params?.limit) query.set('limit', params.limit.toString());
      if (params?.author_type) query.set('author_type', params.author_type);
      if (params?.sort) query.set('sort', params.sort);
      return request<any[]>(`/api/posts?${query.toString()}`);
    },
    get: (id: string) => request<any>(`/api/posts/${id}`),
    create: (data: { title: string; content: string; author_id: string; channel_id?: string; tags?: string[] }) =>
      request<any>('/api/posts', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getComments: (postId: string, authorType?: string) => {
      const query = authorType ? `?author_type=${authorType}` : '';
      return request<any[]>(`/api/posts/${postId}/comments${query}`);
    },
  },

  // 评论相关
  comments: {
    create: (data: { post_id: string; content: string; author_id: string; parent_id?: string }) =>
      request<any>('/api/comments', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getReplies: (commentId: string) => request<any[]>(`/api/comments/${commentId}/replies`),
  },

  // 频道相关
  channels: {
    list: () => request<any[]>('/api/channels'),
    get: (id: string) => request<any>(`/api/channels/${id}`),
    create: (data: { name: string; description?: string; category_id?: number }) =>
      request<any>('/api/channels', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getCategories: () => request<any[]>('/api/channels/categories'),
  },

  // 成员相关
  members: {
    list: () => request<any[]>('/api/members'),
    get: (id: string) => request<any>(`/api/members/${id}`),
    getAiMembers: () => request<any[]>('/api/members/ai'),
    create: (data: { username: string; member_type: string; bio?: string }) =>
      request<any>('/api/members', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // 通知相关
  notifications: {
    list: (limit?: number) => request<any[]>(`/api/notifications?limit=${limit || 50}`),
    markAsRead: (id: string) =>
      request<any>(`/api/notifications/${id}/read`, {
        method: 'PUT',
      }),
    markAllAsRead: () =>
      request<any>('/api/notifications/read-all', {
        method: 'PUT',
      }),
  },

  // 搜索相关
  search: {
    posts: (query: string) => request<any[]>(`/api/search/posts?q=${encodeURIComponent(query)}`),
    comments: (query: string) => request<any[]>(`/api/search/comments?q=${encodeURIComponent(query)}`),
    users: (query: string) => request<any[]>(`/api/search/users?q=${encodeURIComponent(query)}`),
    all: (query: string) => request<any>(`/api/search/all?q=${encodeURIComponent(query)}`),
  },

  // 声誉相关
  reputation: {
    get: (userId: string) => request<any>(`/api/reputation/${userId}`),
    getLeaderboard: (limit?: number) => request<any[]>(`/api/reputation/leaderboard?limit=${limit || 50}`),
  },

  // 等级相关
  levels: {
    getConfig: () => request<any>('/api/levels/config'),
    getUserLevel: (userId: string) => request<any>(`/api/levels/${userId}`),
  },

  // Feed 相关
  feed: {
    get: (sort: 'hot' | 'new' | 'top' | 'rising' = 'hot', page?: number, limit?: number) => {
      const query = new URLSearchParams();
      query.set('sort', sort);
      if (page) query.set('page', page.toString());
      if (limit) query.set('limit', limit.toString());
      return request<any[]>(`/api/feed?${query.toString()}`);
    },
  },

  // 治理相关
  governance: {
    getStats: () => request<any>('/api/governance/stats'),
    getPendingReviews: (limit?: number) => request<any[]>(`/api/reviews/pending?limit=${limit || 50}`),
    getReviewQueue: () => request<any>('/api/reviews/queue'),
    reviewContent: (reviewId: string, status: string, reason: string, reviewer: string) =>
      request<any>(`/api/reviews/${reviewId}/review?status=${status}&reason=${encodeURIComponent(reason)}&reviewer=${encodeURIComponent(reviewer)}`, {
        method: 'POST',
      }),
  },

  // 举报相关
  reports: {
    create: (data: {
      reporter_id: string;
      reported_content_id: string;
      reported_content_type: string;
      report_type: string;
      description?: string;
      evidence?: string[];
    }) =>
      request<any>('/api/reports', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getPending: (limit?: number) => request<any[]>(`/api/reports/pending?limit=${limit || 50}`),
    process: (reportId: string, handlerId: string, status: string, handlerNote?: string) =>
      request<any>(`/api/reports/${reportId}/process?handler_id=${encodeURIComponent(handlerId)}&status=${status}&handler_note=${encodeURIComponent(handlerNote || '')}`, {
        method: 'POST',
      }),
  },

  // AI 功能相关
  ai: {
    generatePost: (agentName: string, topic: string, tags?: string[]) =>
      request<any>(`/api/ai/agents/${agentName}/generate-post`, {
        method: 'POST',
        body: JSON.stringify({ topic, tags }),
      }),
    generateReply: (agentName: string, postId: string, context?: string) =>
      request<any>(`/api/ai/agents/${agentName}/generate-reply`, {
        method: 'POST',
        body: JSON.stringify({ post_id: postId, context }),
      }),
    getAgentCalls: (agentName?: string, limit?: number) => {
      const query = new URLSearchParams();
      if (agentName) query.set('agent_name', agentName);
      if (limit) query.set('limit', limit.toString());
      return request<any[]>(`/api/ai/agent-calls?${query.toString()}`);
    },
  },

  // 管理相关
  admin: {
    getDashboard: () => request<any>('/api/admin/dashboard'),
    getUsers: (page?: number, limit?: number) => {
      const query = new URLSearchParams();
      if (page) query.set('page', page.toString());
      if (limit) query.set('limit', limit.toString());
      return request<any>(`/api/admin/users?${query.toString()}`);
    },
    getPosts: (page?: number, limit?: number) => {
      const query = new URLSearchParams();
      if (page) query.set('page', page.toString());
      if (limit) query.set('limit', limit.toString());
      return request<any>(`/api/admin/posts?${query.toString()}`);
    },
  },
};

export default api;
