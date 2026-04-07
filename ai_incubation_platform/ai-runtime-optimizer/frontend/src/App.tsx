/**
 * AI Native App - 主应用入口
 * Bento Grid & Monochromatic 主题
 */

import React, { useState } from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from '@/components/MainLayout';
import ChatPage from '@/pages/ChatPage';
import DashboardPage from '@/pages/DashboardPage';
import AgentsPage from '@/pages/AgentsPage';
import DiagnosisPage from '@/pages/DiagnosisPage';
import SettingsPage from '@/pages/SettingsPage';
import { colors, shadows, radii } from '@/styles/design-tokens';

// 初始化 Agent 状态
import { useAgentStore } from '@/store';

// 初始化默认 Agent 状态
const initializeAgents = () => {
  const { setAgents } = useAgentStore.getState();
  setAgents([
    {
      name: 'Perception Agent',
      status: 'idle',
      last_activity: new Date(),
    },
    {
      name: 'Diagnosis Agent',
      status: 'idle',
      last_activity: new Date(),
    },
    {
      name: 'Remediation Agent',
      status: 'idle',
      last_activity: new Date(),
    },
    {
      name: 'Optimization Agent',
      status: 'idle',
      last_activity: new Date(),
    },
  ]);
};

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState('chat');

  // 初始化 Agent 状态
  React.useEffect(() => {
    initializeAgents();
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'chat':
        return <ChatPage />;
      case 'dashboard':
        return <DashboardPage />;
      case 'agents':
        return <AgentsPage />;
      case 'diagnosis':
        return <DiagnosisPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <ChatPage />;
    }
  };

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: colors.primary[500],
          colorBgBase: colors.dark.bg,
          colorTextBase: colors.neutral[100],
          colorBorder: colors.dark.border,
          borderRadius: parseFloat(radii.md),
          boxShadow: shadows.card,
        },
        components: {
          Layout: {
            bodyBg: colors.dark.bg,
            headerBg: colors.dark.bgElevated,
            siderBg: colors.dark.bgElevated,
          },
          Card: {
            colorBgContainer: colors.dark.bgCard,
            borderRadius: parseFloat(radii.lg),
          },
          Menu: {
            darkItemSelectedBg: 'rgba(99, 102, 241, 0.15)',
            darkItemBg: 'transparent',
            colorText: colors.neutral[300],
            colorTextSelected: colors.neutral[0],
          },
          Button: {
            colorPrimary: colors.primary[500],
          },
        },
      }}
    >
      <MainLayout currentPage={currentPage} onNavigate={setCurrentPage}>
        {renderPage()}
      </MainLayout>
    </ConfigProvider>
  );
};

export default App;
