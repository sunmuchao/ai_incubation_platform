/**
 * AI Native 类型定义
 */

// 作者类型（人机身份标识）
export type AuthorType = 'human' | 'ai' | 'hybrid';

// AI Agent 类型
export interface AIAgent {
  id: string;
  name: string;
  type: 'moderator' | 'matcher' | 'assistant' | 'curator';
  status: 'active' | 'idle' | 'processing';
  reputation: number;
  governancePower: number;
  stats: {
    totalDecisions?: number;
    accuracyRate?: number;
    avgResponseTime?: string;
    totalMatches?: number;
    successRate?: number;
  };
  lastActiveAt: string;
  avatar?: string;
  description?: string;
}

// 人机身份徽章
export interface AuthorBadge {
  type: AuthorType;
  icon: string;
  label: string;
  color: string;
  tooltip: string;
  aiModelInfo?: string;
  aiContributionRatio?: number;
}

// 决策过程可视化
export interface DecisionStep {
  stepName: string;
  result: string;
  confidence: number;
  reasoning: string;
  timestamp: string;
}

export interface DecisionVisualization {
  traceId: string;
  agentId: string;
  agentName: string;
  actionType: string;
  decisionSteps: DecisionStep[];
  finalDecision: string;
  confidenceScore: number;
  reasoning: string;
  appealUrl: string;
}

// Generative UI 组件类型
export interface UIComponent {
  type: 'content_card' | 'widget' | 'chart' | 'timeline' | 'agent_status';
  data: Record<string, any>;
  layout?: Record<string, any>;
}

export interface GenerativeUIResponse {
  components: UIComponent[];
  layout: {
    type: 'grid' | 'dashboard' | 'sidebar' | 'flow';
    columns?: number;
    rows?: string[][];
    gap?: string;
    position?: 'left' | 'right' | 'center';
  };
  metadata: Record<string, any>;
}

// 聊天消息
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  suggestedActions?: SuggestedAction[];
  uiComponents?: UIComponent[];
  metadata?: Record<string, any>;
}

// 建议操作
export interface SuggestedAction {
  action: string;
  label: string;
  placeholder?: string;
  topics?: string[];
  params?: Record<string, any>;
}

// 对话状态
export interface ConversationState {
  conversationId: string;
  userId: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  context: Record<string, any>;
}

// 声誉维度
export interface ReputationDimensions {
  contentQuality: number;
  communityContribution: number;
  collaboration: number;
  trustworthiness: number;
}

// 声誉信息
export interface Reputation {
  memberId: string;
  memberName: string;
  memberType: AuthorType;
  totalScore: number;
  level: string;
  dimensionScores: ReputationDimensions;
  statistics: {
    totalPosts: number;
    totalComments: number;
    totalUpvotesReceived: number;
    totalDownvotesReceived: number;
    helpfulActions: number;
    violationActions: number;
  };
  probationMode?: boolean;
  probationEndDate?: string;
}

// 透明度统计
export interface TransparencyStats {
  aiContentRatio: number;
  totalAiDecisions: number;
  decisionDistribution: Record<string, number>;
  averageConfidence: number;
  appealCount: number;
  appealSuccessRate: number;
}

// 仪表盘组件
export interface DashboardWidget {
  widgetId: string;
  widgetType: 'stat_card' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'agent_card';
  title: string;
  data: Record<string, any>;
  config: Record<string, any>;
}

// 通知类型
export interface Notification {
  id: string;
  userId: string;
  type: string;
  title: string;
  content: string;
  isRead: boolean;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  createdAt: string;
  relatedPostId?: string;
  relatedCommentId?: string;
  metadata?: Record<string, any>;
}

// Feed 项目
export interface FeedItem {
  id: string;
  type: 'post' | 'comment' | 'discussion';
  title: string;
  content: string;
  authorBadge: AuthorBadge;
  createdAt: string;
  tags: string[];
  aiContributionRatio?: number;
  moderationStatus?: string;
  decisionTraceId?: string;
  upvotes: number;
  downvotes: number;
  commentCount: number;
  heatScore?: number;
}

// 排序类型
export type FeedSort = 'hot' | 'new' | 'top' | 'rising' | 'ai' | 'human';
