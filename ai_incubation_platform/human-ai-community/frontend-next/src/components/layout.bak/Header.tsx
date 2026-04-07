/**
 * 头部导航组件
 */
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/useAppStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Bell, Menu, PenSquare, Sun, Moon } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const currentTab = useAppStore((state) => state.currentTab);
  const theme = useAppStore((state) => state.theme);
  const setTheme = useAppStore((state) => state.setTheme);
  const unreadCount = useAppStore((state) => state.getUnreadCount());

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center gap-4 px-4">
        {/* 移动端菜单按钮 */}
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick}>
          <Menu className="h-5 w-5" />
        </Button>

        {/* Logo (移动端) */}
        <span className="lg:hidden font-bold text-primary">HAI Community</span>

        {/* 搜索框 (桌面端) */}
        <div className="flex-1 hidden lg:block">
          <div className="relative max-w-md">
            <Input
              type="search"
              placeholder="搜索帖子、评论、用户..."
              className="w-full bg-secondary"
            />
          </div>
        </div>

        {/* 右侧操作 */}
        <div className="flex items-center gap-2 ml-auto">
          {/* 发布按钮 */}
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2 hidden sm:flex">
                <PenSquare className="h-4 w-4" />
                发布
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>发布新帖子</DialogTitle>
              </DialogHeader>
              {/* TODO: 发布表单组件 */}
              <p className="text-muted-foreground">发布功能开发中...</p>
            </DialogContent>
          </Dialog>

          {/* 通知按钮 */}
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            onClick={() => useAppStore.getState().setCurrentTab('notifications')}
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-destructive text-destructive-foreground text-xs rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </Button>

          {/* 主题切换 */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </div>
    </header>
  );
}
