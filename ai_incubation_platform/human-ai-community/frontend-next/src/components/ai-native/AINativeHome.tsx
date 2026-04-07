/**
 * AI Native 首页
 * Chat-first 交互范式
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useAINativeStore } from '@/stores/useAINativeStore';
import { ChatInterface } from '@/components/ai-native/ChatInterface';
import { GenerativeUI, ContentCard, DecisionTraceViewer } from '@/components/ai-native/GenerativeUI';
import { AgentPanel, AgentCard, AgentDetailPanel } from '@/components/ai-native/AgentPanel';
import { ReputationCard, ReputationDetail } from '@/components/ai-native/ReputationDisplay';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import {
  Home,
  Bot,
  User,
  Bell,
  TrendingUp,
  Sparkles,
  Menu,
  X,
  MessageSquare,
  Users,
  Shield,
  Star,
} from 'lucide-react';

type ActiveTab = 'chat' | 'feed' | 'agents' | 'profile' | 'notifications';
type ActivePage = 'home' | 'governance' | 'stats' | 'agent-detail' | 'reputation-detail';

export function AINativeHome() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('chat');
  const [activePage, setActivePage] = useState<ActivePage>('home');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [showDecisionTrace, setShowDecisionTrace] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { loadFeed, loadNotifications, notifications, unreadCount } = useAINativeStore();

  // 初始加载
  useEffect(() => {
    loadFeed('hot');
    loadNotifications();
  }, []);

  // 导航处理
  const handleNavigate = (page: string, params?: Record<string, any>) => {
    if (page === 'governance') {
      setActivePage('governance');
    } else if (page === 'stats') {
      setActivePage('stats');
    } else if (page === 'agent-detail' && params?.agent) {
      setSelectedAgentId(params.agent.id);
      setActivePage('agent-detail');
    }
  };

  // 渲染主内容
  const renderMainContent = () => {
    switch (activePage) {
      case 'agent-detail':
        return (
          <AgentDetailPanel
            agent={useAINativeStore.getState().agents.find((a) => a.id === selectedAgentId)!}
            onClose={() => setActivePage('home')}
          />
        );

      case 'reputation-detail':
        return <ReputationDetail onClose={() => setActivePage('home')} />;

      case 'governance':
        return (
          <div className="p-4">
            <h2 className="text-xl font-bold mb-4">社区治理</h2>
            <p className="text-muted-foreground">治理功能开发中...</p>
          </div>
        );

      case 'stats':
        return (
          <div className="p-4">
            <h2 className="text-xl font-bold mb-4">统计数据</h2>
            <p className="text-muted-foreground">统计功能开发中...</p>
          </div>
        );

      default:
        return (
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ActiveTab)} className="h-full">
            <TabsContent value="chat" className="h-full mt-0">
              <ChatInterface onNavigate={handleNavigate} />
            </TabsContent>

            <TabsContent value="feed" className="h-full mt-0">
              <FeedView />
            </TabsContent>

            <TabsContent value="agents" className="h-full mt-0">
              <AgentPanel onAgentClick={(agent) => handleNavigate('agent-detail', { agent })} />
            </TabsContent>

            <TabsContent value="profile" className="h-full mt-0">
              <ProfileView onReputationClick={() => setActivePage('reputation-detail')} />
            </TabsContent>

            <TabsContent value="notifications" className="h-full mt-0">
              <NotificationsView />
            </TabsContent>
          </Tabs>
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* 顶部导航栏 */}
      <header className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <button
            className="lg:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
              Human-AI Community
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveTab('notifications')}
            className="relative"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-5 min-w-5 px-1 text-xs"
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </Badge>
            )}
          </Button>
        </div>
      </header>

      {/* 主要内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 桌面端侧边栏 */}
        <aside className="hidden lg:block w-64 border-r border-border bg-card">
          <DesktopSidebar activeTab={activeTab} onTabChange={setActiveTab} />
        </aside>

        {/* 主内容 */}
        <main className="flex-1 overflow-hidden">
          {renderMainContent()}
        </main>

        {/* 桌面端右侧面板 - Agent 状态 */}
        <aside className="hidden xl:block w-72 border-l border-border bg-card">
          <RightPanel />
        </aside>
      </div>

      {/* 移动端底部导航 */}
      <nav className="lg:hidden border-t border-border bg-card safe-area-pb">
        <div className="flex items-center justify-around py-2">
          <MobileNavButton
            icon={<Home className="h-5 w-5" />}
            label="首页"
            active={activeTab === 'chat' || activeTab === 'feed'}
            onClick={() => setActiveTab('chat')}
          />
          <MobileNavButton
            icon={<Bot className="h-5 w-5" />}
            label="Agent"
            active={activeTab === 'agents'}
            onClick={() => setActiveTab('agents')}
          />
          <MobileNavButton
            icon={<MessageSquare className="h-5 w-5" />}
            label="动态"
            active={activeTab === 'feed'}
            onClick={() => setActiveTab('feed')}
          />
          <MobileNavButton
            icon={<User className="h-5 w-5" />}
            label="我的"
            active={activeTab === 'profile'}
            onClick={() => setActiveTab('profile')}
          />
        </div>
      </nav>
    </div>
  );
}

// 桌面端侧边栏
function DesktopSidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
}) {
  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'chat', label: 'AI 对话', icon: <MessageSquare className="h-5 w-5" /> },
    { id: 'feed', label: '内容流', icon: <TrendingUp className="h-5 w-5" /> },
    { id: 'agents', label: 'AI Agent', icon: <Bot className="h-5 w-5" /> },
    { id: 'profile', label: '个人中心', icon: <User className="h-5 w-5" /> },
    { id: 'notifications', label: '通知', icon: <Bell className="h-5 w-5" /> },
  ];

  return (
    <div className="p-4 space-y-2">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onTabChange(item.id)}
          className={cn(
            'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
            activeTab === item.id
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
          )}
        >
          {item.icon}
          {item.label}
        </button>
      ))}
    </div>
  );
}

// 右侧面板
function RightPanel() {
  return (
    <div className="p-4 space-y-4">
      <h3 className="font-semibold text-sm text-muted-foreground">AI Agent 状态</h3>
      <AgentPanel />
      <div className="pt-4 border-t border-border">
        <ReputationCard />
      </div>
    </div>
  );
}

// Feed 视图
function FeedView() {
  const { feedItems, feedLoading, feedSort, setFeedSort } = useAINativeStore();

  const sortOptions: { value: string; label: string }[] = [
    { value: 'hot', label: '热门' },
    { value: 'new', label: '最新' },
    { value: 'top', label: ' Top' },
    { value: 'rising', label: '上升' },
    { value: 'ai', label: 'AI 创作' },
    { value: 'human', label: '人类创作' },
  ];

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* 排序标签 */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {sortOptions.map((opt) => (
            <Badge
              key={opt.value}
              variant={feedSort === opt.value ? 'default' : 'secondary'}
              className="cursor-pointer whitespace-nowrap"
              onClick={() => setFeedSort(opt.value as any)}
            >
              {opt.label}
            </Badge>
          ))}
        </div>

        {/* 内容列表 */}
        {feedLoading ? (
          <div className="text-center py-8 text-muted-foreground">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            加载中...
          </div>
        ) : feedItems.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
            暂无内容
          </div>
        ) : (
          feedItems.map((item) => (
            <ContentCard key={item.id} item={item} />
          ))
        )}
      </div>
    </ScrollArea>
  );
}

// 个人中心工作区
function ProfileView({ onReputationClick }: { onReputationClick: () => void }) {
  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        <h2 className="text-xl font-bold">个人中心</h2>

        {/* 声誉卡片 */}
        <ReputationCard onExpand={onReputationClick} />

        {/* 我的统计 */}
        <Card className="p-4">
          <h3 className="font-semibold mb-4">我的统计</h3>
          <div className="grid grid-cols-2 gap-3">
            <StatItem label="帖子数" value="12" />
            <StatItem label="评论数" value="45" />
            <StatItem label="获赞数" value="128" />
            <StatItem label="关注数" value="23" />
          </div>
        </Card>

        {/* 设置选项 */}
        <Card className="p-4">
          <h3 className="font-semibold mb-4">设置</h3>
          <div className="space-y-2">
            <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-secondary transition-colors">
              <span className="text-sm">通知偏好</span>
              <span className="text-muted-foreground">›</span>
            </button>
            <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-secondary transition-colors">
              <span className="text-sm">隐私设置</span>
              <span className="text-muted-foreground">›</span>
            </button>
            <button className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-secondary transition-colors">
              <span className="text-sm">AI 助手设置</span>
              <span className="text-muted-foreground">›</span>
            </button>
          </div>
        </Card>
      </div>
    </ScrollArea>
  );
}

// 通知视图
function NotificationsView() {
  const { notifications, markNotificationAsRead, markAllNotificationsAsRead } =
    useAINativeStore();

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">通知</h2>
          {notifications.some((n) => !n.isRead) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={markAllNotificationsAsRead}
            >
              全部已读
            </Button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
            暂无通知
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={cn(
                  'p-4 rounded-lg border transition-colors cursor-pointer',
                  notification.isRead
                    ? 'bg-card border-border'
                    : 'bg-primary/5 border-primary/30'
                )}
                onClick={() => markNotificationAsRead(notification.id)}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full mt-2',
                      notification.isRead ? 'bg-muted-foreground' : 'bg-primary'
                    )}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{notification.title}</span>
                      <Badge
                        variant={
                          notification.priority === 'high' ||
                          notification.priority === 'urgent'
                            ? 'destructive'
                            : 'secondary'
                        }
                        className="text-xs"
                      >
                        {notification.priority}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {notification.content}
                    </p>
                    <span className="text-xs text-muted-foreground mt-2 block">
                      {formatRelativeTime(notification.createdAt)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}

// 移动端导航按钮
function MobileNavButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-colors',
        active ? 'text-primary' : 'text-muted-foreground'
      )}
    >
      {icon}
      <span className="text-xs">{label}</span>
    </button>
  );
}

// 统计项
function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 bg-secondary rounded-lg text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

// 辅助组件 Card
function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('bg-card rounded-lg border border-border', className)}>{children}</div>;
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
  return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' });
}
