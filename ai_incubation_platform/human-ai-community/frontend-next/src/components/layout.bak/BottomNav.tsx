/**
 * 移动端底部导航
 */
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/useAppStore';
import { Home, Folder, Search, Bell, User } from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

export function BottomNav() {
  const currentTab = useAppStore((state) => state.currentTab);
  const setCurrentTab = useAppStore((state) => state.setCurrentTab);
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
    { id: 'profile', label: '我的', icon: <User className="h-5 w-5" /> },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-card border-t border-border lg:hidden safe-bottom z-50">
      <ul className="flex justify-around items-center">
        {navItems.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => setCurrentTab(item.id)}
              className={cn(
                'flex flex-col items-center justify-center w-full py-3 px-2 touch-feedback',
                currentTab === item.id
                  ? 'text-primary'
                  : 'text-muted-foreground'
              )}
            >
              <div className="relative">
                {item.icon}
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-destructive text-destructive-foreground text-xs rounded-full flex items-center justify-center">
                    {item.badge > 9 ? '9+' : item.badge}
                  </span>
                )}
              </div>
              <span className="text-xs mt-0.5">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
