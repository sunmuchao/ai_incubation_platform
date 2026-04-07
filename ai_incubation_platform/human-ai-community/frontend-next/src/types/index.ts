/**
 * 类型定义
 */

// 作者类型
export type AuthorType = 'human' | 'ai' | 'hybrid';

// 内容类型
export type ContentType = 'post' | 'comment';

// 用户类型
export interface User {
  id: string;
  username: string;
  email?: string;
  avatar?: string;
  memberType: AuthorType;
  reputation?: number;
  level?: number;
  createdAt?: string;
}

// 帖子类型
export interface Post {
  id: string;
  title: string;
  content: string;
  authorId: string;
  authorName?: string;
  authorType: AuthorType;
  channelId?: string;
  channelName?: string;
  tags?: string[];
  upvotes: number;
  downvotes: number;
  commentCount: number;
  views: number;
  heatScore?: number;
  createdAt: string;
  updatedAt?: string;
  isEdited?: boolean;
  aiConfidence?: number;
}

// 评论类型
export interface Comment {
  id: string;
  postId: string;
  content: string;
  authorId: string;
  authorName?: string;
  authorType: AuthorType;
  parentId?: string;
  upvotes: number;
  downvotes: number;
  replyCount: number;
  createdAt: string;
  updatedAt?: string;
  isEdited?: boolean;
}

// 频道类型
export interface Channel {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  categoryId?: string;
  categoryName?: string;
  memberCount: number;
  postCount: number;
  createdAt: string;
}

// 通知类型
export interface Notification {
  id: string;
  userId: string;
  type: string;
  content: string;
  isRead: boolean;
  createdAt: string;
  relatedPostId?: string;
  relatedCommentId?: string;
  relatedUserId?: string;
}

// 声誉类型
export interface Reputation {
  userId: string;
  score: number;
  level: number;
  badges?: string[];
  history?: ReputationHistory[];
}

export interface ReputationHistory {
  id: string;
  userId: string;
  change: number;
  reason: string;
  createdAt: string;
}

// API 响应类型
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// 分页类型
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// 搜索类型
export interface SearchParams {
  query: string;
  type?: 'posts' | 'comments' | 'users' | 'all';
  channelId?: string;
  authorType?: AuthorType;
  sortBy?: 'relevance' | 'latest' | 'popular';
  page?: number;
  pageSize?: number;
}

export interface SearchResult {
  posts?: Post[];
  comments?: Comment[];
  users?: User[];
  all?: (Post | Comment | User)[];
}

// Feed 排序类型
export type FeedSort = 'hot' | 'new' | 'top' | 'rising';

// 创建帖子类型
export interface CreatePostInput {
  title: string;
  content: string;
  authorId: string;
  authorType: AuthorType;
  channelId?: string;
  tags?: string[];
}

// 创建评论类型
export interface CreateCommentInput {
  postId: string;
  content: string;
  authorId: string;
  authorType: AuthorType;
  parentId?: string;
}

// WebSocket 消息类型
export interface WebSocketMessage {
  type: 'notification' | 'update' | 'error';
  payload: unknown;
  timestamp: string;
}
