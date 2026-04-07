/**
 * AI Agent 状态面板
 * 展示 AI Agent 活动状态和声誉
 */

'use client';

import React from 'react';
import { useAINativeStore } from '@/stores/useAINativeStore';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { AIAgent } from '@/types/ai-native';
import {
  Bot,
  Shield,
  Users,
  MessageSquare,
  TrendingUp,
  Clock,
  Activity,
  Star,
  Zap,
} from 'lucide-react';

interface AgentPanelProps {
  onAgentClick?: (agent: AIAgent) => void;
}

export function AgentPanel({ onAgentClick }: AgentPanelProps) {
  const { agents, agentsLoading, loadAgents } = useAINativeStore();

  React.useEffect(() => {
    if (agents.length === 0 && !agentsLoading) {
      loadAgents();
    }
  }, []);

  if (agentsLoading) {
    return (
      <div className="p-4 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>暂无 AI Agent</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-3">
        <h3 className="font-semibold text-sm text-muted-foreground mb-4">
          AI Agent 团队
        </h3>
        {agents.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            onClick={() => onAgentClick?.(agent)}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

// Agent 卡片
interface AgentCardProps {
  agent: AIAgent;
  onClick?: () => void;
}

export function AgentCard({ agent, onClick }: AgentCardProps) {
  const getStatusColor = () => {
    switch (agent.status) {
      case 'active':
        return 'bg-green-500';
      case 'processing':
        return 'bg-yellow-500 animate-pulse';
      case 'idle':
        return 'bg-muted-foreground';
      default:
        return 'bg-muted-foreground';
    }
  };

  const getTypeIcon = () => {
    switch (agent.type) {
      case 'moderator':
        return <Shield className="h-4 w-4" />;
      case 'matcher':
        return <Users className="h-4 w-4" />;
      case 'assistant':
        return <MessageSquare className="h-4 w-4" />;
      case 'curator':
        return <TrendingUp className="h-4 w-4" />;
      default:
        return <Bot className="h-4 w-4" />;
    }
  };

  const getTypeLabel = () => {
    const labels: Record<string, string> = {
      moderator: 'AI 版主',
      matcher: '匹配助手',
      assistant: '社区助手',
      curator: '内容策展',
    };
    return labels[agent.type] || 'AI Agent';
  };

  return (
    <Card
      className={cn(
        'p-4 cursor-pointer transition-all hover:shadow-md',
        agent.status === 'active' && 'border-primary/30'
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* 头像 */}
        <div className="relative">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-2xl">
            {agent.avatar || '🤖'}
          </div>
          <div
            className={cn(
              'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-background',
              getStatusColor()
            )}
          />
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold text-sm truncate">{agent.name}</h4>
            <Badge variant="secondary" className="text-xs h-5">
              {getTypeIcon()}
              <span className="ml-1">{getTypeLabel()}</span>
            </Badge>
          </div>

          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
            <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
            <span>{agent.reputation.toFixed(1)}</span>
            <span>·</span>
            <span>治理权 {(agent.governancePower * 100).toFixed(0)}%</span>
          </div>

          {/* 统计数据 */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {agent.stats?.totalDecisions !== undefined && (
              <span className="flex items-center gap-1">
                <Shield className="h-3 w-3" />
                {agent.stats.totalDecisions}
              </span>
            )}
            {agent.stats?.accuracyRate !== undefined && (
              <span className="flex items-center gap-1">
                <Activity className="h-3 w-3" />
                {(agent.stats.accuracyRate * 100).toFixed(0)}%
              </span>
            )}
            {agent.stats?.avgResponseTime && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {agent.stats.avgResponseTime}
              </span>
            )}
            {agent.stats?.totalMatches !== undefined && (
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                {agent.stats.totalMatches}
              </span>
            )}
            {agent.stats?.successRate !== undefined && (
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                {(agent.stats.successRate * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

// Agent 详情面板
interface AgentDetailPanelProps {
  agent: AIAgent;
  onClose: () => void;
}

export function AgentDetailPanel({ agent, onClose }: AgentDetailPanelProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">{agent.name}</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          关闭
        </Button>
      </div>

      {/* 基本信息 */}
      <div className="flex items-center gap-4 p-4 bg-secondary rounded-lg">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">
          {agent.avatar || '🤖'}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="capitalize">{agent.status}</span>
          </div>
          <p className="text-sm text-muted-foreground">{agent.description}</p>
        </div>
      </div>

      {/* 统计数据 */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3 text-center">
          <div className="text-2xl font-bold">{agent.stats?.totalDecisions || '-'}</div>
          <div className="text-xs text-muted-foreground">总决策数</div>
        </Card>
        <Card className="p-3 text-center">
          <div className="text-2xl font-bold text-green-500">
            {agent.stats?.accuracyRate ? (agent.stats.accuracyRate * 100).toFixed(1) : '-'}%
          </div>
          <div className="text-xs text-muted-foreground">准确率</div>
        </Card>
        <Card className="p-3 text-center">
          <div className="text-2xl font-bold">{agent.stats?.avgResponseTime || '-'}</div>
          <div className="text-xs text-muted-foreground">平均响应</div>
        </Card>
        <Card className="p-3 text-center">
          <div className="text-2xl font-bold">{agent.reputation.toFixed(1)}</div>
          <div className="text-xs text-muted-foreground">声誉分数</div>
        </Card>
      </div>

      {/* 能力说明 */}
      <Card className="p-4">
        <h4 className="font-semibold text-sm mb-3">核心能力</h4>
        <div className="space-y-2">
          {agent.type === 'moderator' && (
            <>
              <CapabilityItem
                icon={<Zap className="h-4 w-4" />}
                text="自动识别和处理违规内容"
              />
              <CapabilityItem
                icon={<Shield className="h-4 w-4" />}
                text="智能举报审核与风险评估"
              />
              <CapabilityItem
                icon={<Activity className="h-4 w-4" />}
                text="实时社区治理数据监控"
              />
            </>
          )}
          {agent.type === 'matcher' && (
            <>
              <CapabilityItem
                icon={<Users className="h-4 w-4" />}
                text="基于兴趣的 member 匹配"
              />
              <CapabilityItem
                icon={<Star className="h-4 w-4" />}
                text="个性化推荐算法"
              />
              <CapabilityItem
                icon={<TrendingUp className="h-4 w-4" />}
                text="匹配成功率持续优化"
              />
            </>
          )}
          {agent.type === 'assistant' && (
            <>
              <CapabilityItem
                icon={<MessageSquare className="h-4 w-4" />}
                text="自然语言对话交互"
              />
              <CapabilityItem
                icon={<Bot className="h-4 w-4" />}
                text="多轮对话上下文理解"
              />
              <CapabilityItem
                icon={<SparklesIcon className="h-4 w-4" />}
                text="智能建议与引导"
              />
            </>
          )}
        </div>
      </Card>

      {/* 最后活跃时间 */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Clock className="h-3 w-3" />
        最后活跃：{formatRelativeTime(agent.lastActiveAt)}
      </div>
    </div>
  );
}

// 能力项
function CapabilityItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className="text-primary">{icon}</span>
      <span>{text}</span>
    </div>
  );
}

function formatRelativeTime(timestamp: string) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  return `${days}天前`;
}

// 添加缺失的图标导入
import { Sparkles as SparklesIcon } from 'lucide-react';
