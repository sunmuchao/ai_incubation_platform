/**
 * 声誉展示组件
 * 展示用户声誉和等级信息
 */

'use client';

import React from 'react';
import { useAINativeStore } from '@/stores/useAINativeStore';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import type { Reputation } from '@/types/ai-native';
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  Star,
  Shield,
  Heart,
  MessageSquare,
  ThumbsUp,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';

interface ReputationCardProps {
  onExpand?: () => void;
}

export function ReputationCard({ onExpand }: ReputationCardProps) {
  const { reputation, loadReputation } = useAINativeStore();

  React.useEffect(() => {
    if (!reputation) {
      loadReputation();
    }
  }, [reputation]);

  if (!reputation) {
    return (
      <div className="p-4 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  const levelProgress = (reputation.totalScore % 100) / 100 * 100;
  const nextLevelScore = Math.ceil(reputation.totalScore / 100) * 100;

  return (
    <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={onExpand}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-white font-bold">
          {getLevelIcon(reputation.level)}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{reputation.memberName}</h3>
            <Badge variant="secondary" className="text-xs">
              {reputation.level}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            声誉分数：{reputation.totalScore}
          </p>
        </div>
      </div>

      {/* 进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
          <span>距离下一级</span>
          <span>{nextLevelScore - reputation.totalScore} 分</span>
        </div>
        <Progress value={levelProgress} className="h-2" />
      </div>

      {/* 维度分数 */}
      <div className="grid grid-cols-2 gap-2">
        <DimensionBadge
          icon={<Star className="h-3 w-3" />}
          label="内容质量"
          value={reputation.dimensionScores.contentQuality}
        />
        <DimensionBadge
          icon={<Heart className="h-3 w-3" />}
          label="社区贡献"
          value={reputation.dimensionScores.communityContribution}
        />
        <DimensionBadge
          icon={<MessageSquare className="h-3 w-3" />}
          label="协作互动"
          value={reputation.dimensionScores.collaboration}
        />
        <DimensionBadge
          icon={<Shield className="h-3 w-3" />}
          label="可信度"
          value={reputation.dimensionScores.trustworthiness}
        />
      </div>

      {/* 统计数据 */}
      <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-border">
        <StatItem
          icon={<MessageSquare className="h-4 w-4" />}
          value={reputation.statistics.totalPosts}
          label="帖子"
        />
        <StatItem
          icon={<ThumbsUp className="h-4 w-4" />}
          value={reputation.statistics.totalUpvotesReceived}
          label="获赞"
        />
        <StatItem
          icon={<Trophy className="h-4 w-4" />}
          value={reputation.level}
          label="等级"
        />
      </div>

      {/* 观察模式提示 */}
      {reputation.probationMode && (
        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-yellow-600">
            <AlertCircle className="h-4 w-4" />
            <span>观察期至 {formatDate(reputation.probationEndDate)}</span>
          </div>
          <div className="mt-2 text-xs text-yellow-600">
            完成恢复计划可提前解除观察期
          </div>
        </div>
      )}
    </Card>
  );
}

// 维度徽章
function DimensionBadge({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  const getColor = () => {
    if (value >= 80) return 'text-green-500 bg-green-500/10';
    if (value >= 60) return 'text-blue-500 bg-blue-500/10';
    if (value >= 40) return 'text-yellow-500 bg-yellow-500/10';
    return 'text-red-500 bg-red-500/10';
  };

  return (
    <div className={cn('p-2 rounded-lg flex items-center gap-2', getColor())}>
      {icon}
      <div>
        <div className="text-xs opacity-70">{label}</div>
        <div className="font-semibold">{value}</div>
      </div>
    </div>
  );
}

// 统计项
function StatItem({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
}) {
  return (
    <div className="text-center">
      <div className="flex justify-center text-primary mb-1">{icon}</div>
      <div className="font-semibold text-sm">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

// 声誉详情面板
export function ReputationDetail({ onClose }: { onClose: () => void }) {
  const { reputation, loadReputation } = useAINativeStore();
  const [activeTab, setActiveTab] = React.useState<'overview' | 'history'>('overview');

  React.useEffect(() => {
    if (!reputation) {
      loadReputation();
    }
  }, [reputation]);

  if (!reputation) {
    return (
      <div className="p-4 text-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">声誉详情</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          关闭
        </Button>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 border-b border-border">
        <button
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'overview'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground'
          )}
          onClick={() => setActiveTab('overview')}
        >
          概览
        </button>
        <button
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'history'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground'
          )}
          onClick={() => setActiveTab('history')}
        >
          行为日志
        </button>
      </div>

      {activeTab === 'overview' && (
        <ReputationOverview reputation={reputation} />
      )}

      {activeTab === 'history' && (
        <ReputationHistory memberId={reputation.memberId} />
      )}
    </div>
  );
}

// 声誉概览
function ReputationOverview({ reputation }: { reputation: Reputation }) {
  return (
    <div className="space-y-4">
      {/* 等级信息 */}
      <Card className="p-4 bg-gradient-to-br from-primary/10 to-blue-500/10">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-2xl text-white font-bold">
            {getLevelIcon(reputation.level)}
          </div>
          <div>
            <h4 className="font-semibold text-lg">{reputation.level}</h4>
            <p className="text-sm text-muted-foreground">
              总分数：{reputation.totalScore}
            </p>
            <div className="flex items-center gap-2 mt-1">
              {reputation.memberType === 'ai' && (
                <Badge variant="secondary" className="text-xs">
                  AI Agent
                </Badge>
              )}
              {reputation.probationMode && (
                <Badge variant="destructive" className="text-xs">
                  观察期
                </Badge>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* 维度分数详情 */}
      <Card className="p-4">
        <h4 className="font-semibold mb-4">能力维度</h4>
        <div className="space-y-3">
          <DimensionBar
            icon={<Star className="h-4 w-4" />}
            label="内容质量"
            value={reputation.dimensionScores.contentQuality}
            color="blue"
          />
          <DimensionBar
            icon={<Heart className="h-4 w-4" />}
            label="社区贡献"
            value={reputation.dimensionScores.communityContribution}
            color="green"
          />
          <DimensionBar
            icon={<MessageSquare className="h-4 w-4" />}
            label="协作互动"
            value={reputation.dimensionScores.collaboration}
            color="purple"
          />
          <DimensionBar
            icon={<Shield className="h-4 w-4" />}
            label="可信度"
            value={reputation.dimensionScores.trustworthiness}
            color="orange"
          />
        </div>
      </Card>

      {/* 统计数据 */}
      <Card className="p-4">
        <h4 className="font-semibold mb-4">统计</h4>
        <div className="grid grid-cols-2 gap-3">
          <StatRow label="总帖子数" value={reputation.statistics.totalPosts} />
          <StatRow label="总评论数" value={reputation.statistics.totalComments} />
          <StatRow label="总获赞" value={reputation.statistics.totalUpvotesReceived} icon={<ThumbsUp className="h-4 w-4 text-green-500" />} />
          <StatRow label="总点踩" value={reputation.statistics.totalDownvotesReceived} icon={<ThumbsDownIcon className="h-4 w-4 text-red-500" />} />
          <StatRow label="有帮助行为" value={reputation.statistics.helpfulActions} icon={<CheckCircle className="h-4 w-4 text-blue-500" />} />
          <StatRow label="违规行为" value={reputation.statistics.violationActions} icon={<AlertCircle className="h-4 w-4 text-red-500" />} />
        </div>
      </Card>
    </div>
  );
}

// 维度进度条
function DimensionBar({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  const getColorClass = () => {
    const colors: Record<string, string> = {
      blue: 'bg-blue-500',
      green: 'bg-green-500',
      purple: 'bg-purple-500',
      orange: 'bg-orange-500',
    };
    return colors[color] || 'bg-primary';
  };

  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span>{label}</span>
        </div>
        <span className="font-medium">{value}</span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all', getColorClass())}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

// 统计行
function StatRow({ label, value, icon }: { label: string; value: number | string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <span className="font-medium">{value}</span>
    </div>
  );
}

// 行为日志
function ReputationHistory({ memberId }: { memberId: string }) {
  const [logs, setLogs] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // 实际应调用 API 获取
    // 这里使用占位数据
    setTimeout(() => {
      setLogs([
        {
          id: '1',
          behaviorType: 'post_upvoted',
          isPositive: true,
          description: '帖子获得点赞',
          scoreDelta: 5,
          createdAt: new Date().toISOString(),
        },
        {
          id: '2',
          behaviorType: 'comment_helpful',
          isPositive: true,
          description: '评论被标记为有帮助',
          scoreDelta: 10,
          createdAt: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: '3',
          behaviorType: 'violation',
          isPositive: false,
          description: '内容违规',
          scoreDelta: -20,
          createdAt: new Date(Date.now() - 172800000).toISOString(),
        },
      ]);
      setLoading(false);
    }, 500);
  }, [memberId]);

  if (loading) {
    return <div className="text-center py-4 text-muted-foreground">加载中...</div>;
  }

  return (
    <div className="space-y-2">
      {logs.map((log) => (
        <div
          key={log.id}
          className={cn(
            'p-3 rounded-lg flex items-center justify-between',
            log.isPositive ? 'bg-green-500/10' : 'bg-red-500/10'
          )}
        >
          <div className="flex items-center gap-3">
            {log.isPositive ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
            <div>
              <div className="text-sm">{log.description}</div>
              <div className="text-xs text-muted-foreground">
                {formatRelativeTime(log.createdAt)}
              </div>
            </div>
          </div>
          <div
            className={cn(
              'font-semibold',
              log.isPositive ? 'text-green-500' : 'text-red-500'
            )}
          >
            {log.scoreDelta > 0 ? '+' : ''}{log.scoreDelta}
          </div>
        </div>
      ))}
    </div>
  );
}

// 辅助函数
function getLevelIcon(level: string): string {
  const icons: Record<string, string> = {
    '新手': '🌱',
    '初级成员': '🌿',
    '活跃成员': '🌳',
    '核心成员': '🏆',
    '领袖': '👑',
  };
  return icons[level] || '⭐';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
  });
}

function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  return formatDate(timestamp);
}

// 添加缺失的图标导入
import { ThumbsDown as ThumbsDownIcon } from 'lucide-react';
