/**
 * 移动端导航抽屉组件
 */
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/useAppStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Home, Folder, Search, Bell, User, Settings, PenSquare } from 'lucide-react';

interface MobileDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MobileDrawer({ open, onOpenChange }: MobileDrawerProps) {
  const currentTab = useAppStore((state) => state.currentTab);
  const setCurrentTab = useAppStore((state) => state.setCurrentTab);
  const unreadCount = useAppStore((state) => state.getUnreadCount());

  const navItems = [
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

  const handleNavClick = (tabId: string) => {
    setCurrentTab(tabId);
    onOpenChange(false);
  };

  return (
    <>
      {/* 遮罩层 */}
      <div
        className={cn(
          'fixed inset-0 bg-black/80 z-50 lg:hidden transition-opacity',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={() => onOpenChange(false)}
      />

      {/* 抽屉 */}
      <div
        className={cn(
          'fixed top-0 left-0 h-full w-72 bg-card border-r border-border z-50 lg:hidden transform transition-transform duration-200',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-bold bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
            Human-AI Community
          </h2>
          <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* 导航菜单 */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={cn(
                'w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-all',
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
                <Badge variant="destructive" className="h-5 min-w-5 px-1.5 text-xs">
                  {item.badge > 99 ? '99+' : item.badge}
                </Badge>
              )}
            </button>
          ))}
        </nav>

        {/* 发布按钮 */}
        <div className="absolute bottom-4 left-4 right-4">
          <Button className="w-full gap-2" size="lg">
            <PenSquare className="h-4 w-4" />
            发布帖子
          </Button>
        </div>
      </div>
    </>
  );
}
