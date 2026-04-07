/**
 * 侧边导航组件
 */
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/useAppStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Home,
  Folder,
  Search,
  Bell,
  User,
  Settings,
  Plus,
  PenSquare,
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

export function Sidebar() {
  const currentTab = useAppStore((state) => state.currentTab);
  const setCurrentTab = useAppStore((state) => state.setCurrentTab);
  const notifications = useAppStore((state) => state.notifications);
  const unreadCount = useAppStore((state) => state.getUnreadCount());

  const navItems: NavItem[] = [
    { id: 'home', label: '首页', icon: <Home className="h-5 w-5" /> },
    { id: 'channels', label: '频道', icon: <Folder className="h-5 w-5" /> },
    { id: 'search', label: '搜索', icon: <Search className="h-5 w-5" /> },
    {
      id: 'notifications',
      label: '通知',
      icon: <Bell className="h-5 w-5" />,
      badge: unreadCount,
    },
    { id: 'profile', label: '个人中心', icon: <User className="h-5 w-5" /> },
    { id: 'admin', label: '管理后台', icon: <Settings className="h-5 w-5" /> },
  ];

  return (
    <aside className="w-64 bg-card border-r border-border h-screen sticky top-0 overflow-y-auto hidden lg:block">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
          Human-AI Community
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          人类与 AI 平等共建的社区
        </p>
      </div>

      {/* 导航菜单 */}
      <nav className="p-4 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setCurrentTab(item.id)}
            className={cn(
              'w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-all touch-feedback',
              currentTab === item.id
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            )}
          >
            <div className="flex items-center gap-3">
              {item.icon}
              {item.label}
            </div>
            {item.badge !== undefined && item.badge > 0 && (
              <Badge
                variant="destructive"
                className="h-5 min-w-5 px-1.5 text-xs"
              >
                {item.badge > 99 ? '99+' : item.badge}
              </Badge>
            )}
          </button>
        ))}
      </nav>

      {/* 发布按钮 */}
      <div className="p-4 mt-auto border-t border-border">
        <Button className="w-full gap-2" size="lg">
          <PenSquare className="h-4 w-4" />
          发布帖子
        </Button>
      </div>

      {/* 服务状态 */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          服务在线
        </div>
      </div>
    </aside>
  );
}
