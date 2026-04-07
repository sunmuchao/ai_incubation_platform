/**
 * 主应用布局组件
 */
'use client';

import React, { useState, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { BottomNav } from '@/components/layout/BottomNav';
import { Header } from '@/components/layout/Header';
import { HomePage } from '@/components/pages/HomePage';
import { ChannelsPage } from '@/components/pages/ChannelsPage';
import { SearchPage } from '@/components/pages/SearchPage';
import { NotificationsPage } from '@/components/pages/NotificationsPage';
import { ProfilePage } from '@/components/pages/ProfilePage';
import { AdminPage } from '@/components/pages/AdminPage';
import { useAppStore } from '@/stores/useAppStore';
import { MobileDrawer } from '@/components/layout/MobileDrawer';

export function AppLayout() {
  const currentTab = useAppStore((state) => state.currentTab);
  const theme = useAppStore((state) => state.theme);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // 初始化主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('human-ai-community-storage');
    if (savedTheme) {
      const parsed = JSON.parse(savedTheme);
      if (parsed.state?.theme) {
        document.documentElement.classList.toggle('light', parsed.state.theme === 'light');
      }
    }
  }, []);

  // 同步主题到 store
  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light');
  }, [theme]);

  const renderPage = () => {
    switch (currentTab) {
      case 'home':
        return <HomePage />;
      case 'channels':
        return <ChannelsPage />;
      case 'search':
        return <SearchPage />;
      case 'notifications':
        return <NotificationsPage />;
      case 'profile':
        return <ProfilePage />;
      case 'admin':
        return <AdminPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* 桌面端侧边栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col lg:ml-64">
        {/* 头部 */}
        <Header onMenuClick={() => setMobileDrawerOpen(true)} />

        {/* 页面内容 */}
        <main className="flex-1 overflow-hidden">
          {renderPage()}
        </main>

        {/* 移动端底部导航 */}
        <BottomNav />

        {/* 移动端导航抽屉 */}
        <MobileDrawer
          open={mobileDrawerOpen}
          onOpenChange={setMobileDrawerOpen}
        />
      </div>
    </div>
  );
}
