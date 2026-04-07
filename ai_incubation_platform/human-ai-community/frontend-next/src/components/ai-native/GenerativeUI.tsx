/**
 * Generative UI 组件
 * 动态生成界面组件
 */

'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type {
  UIComponent,
  GenerativeUIResponse,
  FeedItem,
  AuthorBadge,
  DecisionVisualization,
} from '@/types/ai-native';
import {
  Bot,
  User,
  Sparkles,
  TrendingUp,
  MessageSquare,
  Heart,
  Share2,
  MoreHorizontal,
  Shield,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

interface GenerativeUIProps {
  uiResponse?: GenerativeUIResponse;
  feedItems?: FeedItem[];
  loading?: boolean;
  onPostClick?: (post: FeedItem) => void;
  onDecisionView?: (traceId: string) => void;
}

export function GenerativeUI({
  uiResponse,
  feedItems,
  loading = false,
  onPostClick,
  onDecisionView,
}: GenerativeUIProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-muted-foreground">AI 正在生成界面...</p>
        </div>
      </div>
    );
  }

  // 如果有 UI 响应，使用动态布局
  if (uiResponse) {
    return (
      <div className="p-4 space-y-4">
        {uiResponse.components.map((component, index) => (
          <UIComponentRenderer
            key={index}
            component={component}
            onDecisionView={onDecisionView}
          />
        ))}
      </div>
    );
  }

  // 默认使用 Feed Items
  if (feedItems && feedItems.length > 0) {
    return (
      <div className="space-y-4">
        {feedItems.map((item) => (
          <ContentCard
            key={item.id}
            item={item}
            onClick={() => onPostClick?.(item)}
            onViewDecision={() => item.decisionTraceId && onDecisionView?.(item.decisionTraceId)}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      <p className="text-muted-foreground">暂无内容</p>
    </div>
  );
}

// UI 组件渲染器
function UIComponentRenderer({
  component,
  onDecisionView,
}: {
  component: UIComponent;
  onDecisionView?: (traceId: string) => void;
}) {
  switch (component.type) {
    case 'content_card':
      return (
        <ContentCard
          item={{
            id: component.data.id,
            type: component.data.type,
            title: component.data.title,
            content: component.data.content,
            authorBadge: component.data.author_badge,
            createdAt: component.data.created_at,
            tags: component.data.tags || [],
            aiContributionRatio: component.data.ai_contribution_ratio,
            moderationStatus: component.data.moderation_status,
            decisionTraceId: component.data.decision_trace_id,
            upvotes: component.data.upvotes || 0,
            downvotes: component.data.downvotes || 0,
            commentCount: component.data.commentCount || 0,
          }}
          onViewDecision={() =>
            component.data.decision_trace_id && onDecisionView?.(component.data.decision_trace_id)
          }
        />
      );

    case 'widget':
      return <DashboardWidget data={component.data} />;

    case 'agent_status':
      return <AgentStatusCard data={component.data} />;

    default:
      return null;
  }
}

// 内容卡片组件
interface ContentCardProps {
  item: FeedItem;
  onClick?: () => void;
  onViewDecision?: () => void;
}

export function ContentCard({ item, onClick, onViewDecision }: ContentCardProps) {
  const authorBadge = item.authorBadge;

  return (
    <Card
      className="p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* 作者信息栏 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AuthorBadgeDisplay badge={authorBadge} />
          <span className="text-xs text-muted-foreground">
            {formatTime(item.createdAt)}
          </span>
        </div>
        {item.moderationStatus && (
          <ModerationBadge status={item.moderationStatus} />
        )}
      </div>

      {/* 内容 */}
      <h3 className="font-semibold text-lg mb-2 line-clamp-2">{item.title}</h3>
      <p className="text-muted-foreground text-sm mb-3 line-clamp-3">
        {item.content}
      </p>

      {/* 标签 */}
      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {item.tags.map((tag, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              #{tag}
            </Badge>
          ))}
        </div>
      )}

      {/* AI 贡献度指示器 */}
      {item.aiContributionRatio !== undefined && authorBadge.type === 'hybrid' && (
        <div className="mb-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="h-3 w-3" />
            <span>AI 贡献度 {(item.aiContributionRatio * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full h-1 bg-secondary rounded-full mt-1">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${item.aiContributionRatio * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 决策追溯 */}
      {item.decisionTraceId && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onViewDecision?.();
          }}
          className="flex items-center gap-1 text-xs text-primary hover:underline mb-3"
        >
          <Shield className="h-3 w-3" />
          查看 AI 决策过程
        </button>
      )}

      {/* 互动数据 */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <button className="flex items-center gap-1 hover:text-primary transition-colors">
            <Heart className="h-4 w-4" />
            {item.upvotes}
          </button>
          <button className="flex items-center gap-1 hover:text-primary transition-colors">
            <MessageSquare className="h-4 w-4" />
            {item.commentCount}
          </button>
          <button className="flex items-center gap-1 hover:text-primary transition-colors">
            <Share2 className="h-4 w-4" />
            分享
          </button>
        </div>
        <button className="text-muted-foreground hover:text-foreground">
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>
    </Card>
  );
}

// 作者徽章显示
function AuthorBadgeDisplay({ badge }: { badge: AuthorBadge }) {
  const getIcon = () => {
    switch (badge.type) {
      case 'human':
        return <User className="h-3 w-3" />;
      case 'ai':
        return <Bot className="h-3 w-3" />;
      case 'hybrid':
        return (
          <>
            <User className="h-3 w-3" />
            <Bot className="h-3 w-3" />
          </>
        );
    }
  };

  const getColorClass = () => {
    switch (badge.type) {
      case 'human':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/30';
      case 'ai':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/30';
      case 'hybrid':
        return 'bg-gradient-to-r from-blue-500/10 to-purple-500/10 text-primary border-primary/30';
    }
  };

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border',
        getColorClass()
      )}
      title={badge.tooltip}
    >
      {getIcon()}
      <span className="font-medium">{badge.label}</span>
      {badge.type === 'ai' && badge.aiModelInfo && (
        <span className="text-muted-foreground ml-1">· {badge.aiModelInfo}</span>
      )}
    </div>
  );
}

// 审核状态徽章
function ModerationBadge({ status }: { status: string }) {
  const getStatusConfig = () => {
    switch (status.toLowerCase()) {
      case 'approved':
        return {
          icon: <CheckCircle className="h-3 w-3" />,
          className: 'bg-green-500/10 text-green-500',
          label: '已审核',
        };
      case 'pending':
        return {
          icon: <AlertCircle className="h-3 w-3" />,
          className: 'bg-yellow-500/10 text-yellow-500',
          label: '审核中',
        };
      case 'flagged':
        return {
          icon: <Shield className="h-3 w-3" />,
          className: 'bg-red-500/10 text-red-500',
          label: '已标记',
        };
      default:
        return {
          icon: null,
          className: 'bg-secondary text-muted-foreground',
          label: status,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <Badge variant="secondary" className={cn('text-xs gap-1', config.className)}>
      {config.icon}
      {config.label}
    </Badge>
  );
}

// 仪表盘组件
function DashboardWidget({ data }: { data: any }) {
  switch (data.widget_type) {
    case 'stat_card':
      return (
        <Card className="p-4">
          <h4 className="text-sm text-muted-foreground mb-2">{data.title}</h4>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">{data.data.value}</span>
            <span className="text-xs text-muted-foreground">{data.data.unit}</span>
            {data.data.trend && (
              <span
                className={cn(
                  'text-xs',
                  data.data.trend.startsWith('+') ? 'text-green-500' : 'text-red-500'
                )}
              >
                {data.data.trend}
              </span>
            )}
          </div>
        </Card>
      );

    case 'bar_chart':
      return (
        <Card className="p-4">
          <h4 className="text-sm text-muted-foreground mb-4">{data.title}</h4>
          <div className="space-y-2">
            {Object.entries(data.data).map(([key, value]: [string, any]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground w-16">{key}</span>
                <div className="flex-1 h-4 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${(value / 100) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground w-8">{value}</span>
              </div>
            ))}
          </div>
        </Card>
      );

    default:
      return null;
  }
}

// Agent 状态卡片
function AgentStatusCard({ data }: { data: any }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-xl">
          {data.icon || '🤖'}
        </div>
        <div className="flex-1">
          <h4 className="font-semibold">{data.agent_name}</h4>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="capitalize">{data.agent_type}</span>
            <span>·</span>
            <span
              className={cn(
                'flex items-center gap-1',
                data.status === 'active' ? 'text-green-500' : 'text-muted-foreground'
              )}
            >
              <span
                className={cn(
                  'w-1.5 h-1.5 rounded-full',
                  data.status === 'active' ? 'bg-green-500' : 'bg-muted-foreground'
                )}
              />
              {data.status}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="text-center p-2 bg-secondary rounded-lg">
          <div className="text-lg font-bold">{data.stats?.accuracy_rate || 'N/A'}</div>
          <div className="text-xs text-muted-foreground">准确率</div>
        </div>
        <div className="text-center p-2 bg-secondary rounded-lg">
          <div className="text-lg font-bold">{data.stats?.total_decisions || 'N/A'}</div>
          <div className="text-xs text-muted-foreground">决策数</div>
        </div>
      </div>
    </Card>
  );
}

// 决策过程可视化组件
export function DecisionTraceViewer({
  traceId,
  onClose,
}: {
  traceId: string;
  onClose: () => void;
}) {
  const [visualization, setVisualization] = React.useState<DecisionVisualization | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // 实际应调用 API 获取
    // 这里使用占位数据
    setTimeout(() => {
      setVisualization({
        traceId,
        agentId: 'agent_001',
        agentName: 'AI 版主小安',
        actionType: 'content_removal',
        decisionSteps: [
          {
            stepName: '关键词检测',
            result: '匹配 3 个垃圾广告关键词',
            confidence: 0.85,
            reasoning: '检测到"加微信"、"转账"等关键词',
            timestamp: new Date().toISOString(),
          },
          {
            stepName: '内容特征分析',
            result: '包含 5 个外部链接',
            confidence: 0.6,
            reasoning: '内容长度异常短且包含过多链接',
            timestamp: new Date().toISOString(),
          },
          {
            stepName: '用户历史考量',
            result: '过去 24 小时发布 15 条内容',
            confidence: 0.7,
            reasoning: '用户发布频率异常',
            timestamp: new Date().toISOString(),
          },
        ],
        finalDecision: 'removed',
        confidenceScore: 0.78,
        reasoning: '综合风险分数 0.78，超过阈值 0.7',
        appealUrl: `/appeal/${traceId}`,
      });
      setLoading(false);
    }, 500);
  }, [traceId]);

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (!visualization) return null;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">AI 决策追溯</h3>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X />
        </button>
      </div>

      <div className="space-y-3">
        {visualization.decisionSteps.map((step, index) => (
          <div key={index} className="p-3 bg-secondary rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{step.stepName}</span>
              <Badge
                variant={step.confidence > 0.7 ? 'default' : 'secondary'}
                className="text-xs"
              >
                置信度 {(step.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{step.reasoning}</p>
          </div>
        ))}
      </div>

      <Card className="p-4 bg-primary/5">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="h-4 w-4 text-primary" />
          <span className="font-medium">最终决策</span>
        </div>
        <p className="text-sm text-muted-foreground">{visualization.reasoning}</p>
        <div className="mt-2 flex items-center gap-2">
          <Badge className="text-xs">
            置信度 {(visualization.confidenceScore * 100).toFixed(0)}%
          </Badge>
          <a
            href={visualization.appealUrl}
            className="text-xs text-primary hover:underline"
          >
            对此决策有疑问？点击申诉
          </a>
        </div>
      </Card>
    </div>
  );
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// 添加缺失的 X 图标导入
import { X } from 'lucide-react';
