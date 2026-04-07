import React, { useState } from 'react';
import { ConfigProvider, theme, Layout, Menu, Drawer } from 'antd';
import {
  HomeOutlined,
  TeamOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

// Bento Grid 组件和样式
import { Grid, Card } from './components/BentoGrid';
import designTokens from './styles/designTokens';
import globalStyles, { cssVariables } from './styles/globalStyles';

// AI Native 组件
import ChatInterface from './components/ChatInterface';
import NotificationPanel from './components/NotificationPanel';
import AgentStatus from './components/AgentStatus';

// 设置 dayjs 为中文
dayjs.locale('zh-cn');

const { Header, Sider, Content } = Layout;

/**
 * Bento Grid 风格的 AI Native 应用主界面
 *
 * 设计理念：
 * 1. Bento Grid 布局：模块化卡片，均匀留白
 * 2. Monochromatic 配色：深蓝灰色系，不同明度层次
 * 3. Linear.app 风格：精致阴影，细腻边框，流畅动画
 * 4. Chat-first：对话作为主要交互方式
 */
const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('chat');

  // 处理 AI 生成的 UI 中的操作选择
  const handleActionSelect = (action: string, data?: any) => {
    console.log('Action selected:', action, data);
  };

  // 处理通知点击
  const handleNotificationClick = (notification: any) => {
    console.log('Notification clicked:', notification);
  };

  // 菜单项配置 - Monochromatic 配色
  const menuItems = [
    {
      key: 'chat',
      icon: <HomeOutlined style={{ color: designTokens.colors.blue[500] }} />,
      label: 'AI 助手',
    },
    {
      key: 'tasks',
      icon: <FileTextOutlined style={{ color: designTokens.colors.blue[500] }} />,
      label: '任务管理',
    },
    {
      key: 'workers',
      icon: <TeamOutlined style={{ color: designTokens.colors.blue[500] }} />,
      label: '工人管理',
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined style={{ color: designTokens.colors.blue[500] }} />,
      label: '数据分析',
    },
    {
      key: 'settings',
      icon: <SettingOutlined style={{ color: designTokens.colors.blue[500] }} />,
      label: '设置',
    },
  ];

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: designTokens.colors.blue[600],
          colorSuccess: designTokens.colors.green[600],
          colorWarning: designTokens.colors.amber[600],
          colorError: designTokens.colors.red[600],
          colorInfo: designTokens.colors.blue[600],
          borderRadius: designTokens.radii.md,
          fontFamily: designTokens.typography.fontFamily.sans,
        },
        components: {
          Button: {
            borderRadius: designTokens.radii.md,
          },
          Card: {
            borderRadiusLG: designTokens.radii.lg,
          },
          Menu: {
            borderRadius: designTokens.radii.md,
          },
        },
      }}
    >
      {/* 注入全局 CSS 变量 */}
      <style>{cssVariables}</style>

      <Layout style={{ minHeight: '100vh', background: designTokens.semanticColors.background.primary }}>
        {/* 侧边栏 - Bento 卡片风格 */}
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          theme="light"
          style={{
            background: '#ffffff',
            boxShadow: designTokens.shadows.card,
            borderRight: `1px solid ${designTokens.semanticColors.border.subtle}`,
            zIndex: 100,
          }}
        >
          <div style={styles.logo}>
            {collapsed ? '🤖' : (
              <>
                <span style={{ marginRight: 8 }}>🤖</span>
                <span style={{
                  fontSize: 14,
                  fontWeight: 600,
                  background: `linear-gradient(135deg, ${designTokens.colors.blue[600]}, ${designTokens.colors.blue[400]})`,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}>
                  AI 招聘平台
                </span>
              </>
            )}
          </div>
          <Menu
            mode="inline"
            selectedKeys={[currentView]}
            items={menuItems}
            onClick={({ key }) => setCurrentView(key)}
            style={{
              borderRight: 'none',
              background: 'transparent',
            }}
          />
        </Sider>

        {/* 主内容区 */}
        <Layout>
          {/* 顶栏 - Bento 卡片风格 */}
          <Header style={{
            ...styles.header,
            paddingLeft: collapsed ? 80 : 200,
            background: '#ffffff',
            borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
            boxShadow: designTokens.shadows.card,
          }}>
            <div style={styles.headerLeft}>
              <button
                onClick={() => setCollapsed(!collapsed)}
                style={styles.trigger}
              >
                {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              </button>
              <span style={styles.headerTitle}>AI Native 招聘平台</span>
              <span style={styles.headerBadge}>
                DeerFlow 2.0 驱动
              </span>
            </div>
            <div style={styles.headerRight}>
              <NotificationPanel
                userId="current_user"
                onNotificationClick={handleNotificationClick}
              />
            </div>
          </Header>

          {/* 内容区 - Bento Grid 布局 */}
          <Content style={styles.content}>
            <div style={styles.contentInner}>
              {currentView === 'chat' && (
                <Card
                  variant="default"
                  padding="none"
                  style={{
                    height: 'calc(100vh - 140px)',
                    overflow: 'hidden',
                  }}
                >
                  <ChatInterface
                    userId="current_user"
                    onActionSelect={handleActionSelect}
                  />
                </Card>
              )}
              {currentView === 'tasks' && (
                <div style={styles.placeholder}>
                  <div style={styles.placeholderIcon}>
                    <FileTextOutlined />
                  </div>
                  <h3 style={{ color: designTokens.semanticColors.text.primary }}>任务管理</h3>
                  <p style={{ color: designTokens.semanticColors.text.tertiary }}>
                    请通过 AI 助手管理任务，例如："查看我的任务列表"
                  </p>
                </div>
              )}
              {currentView === 'workers' && (
                <div style={styles.placeholder}>
                  <div style={{ ...styles.placeholderIcon, color: designTokens.colors.green[600] }}>
                    <TeamOutlined />
                  </div>
                  <h3 style={{ color: designTokens.semanticColors.text.primary }}>工人管理</h3>
                  <p style={{ color: designTokens.semanticColors.text.tertiary }}>
                    请通过 AI 助手管理工人，例如："搜索数据标注工人"
                  </p>
                </div>
              )}
              {currentView === 'analytics' && (
                <div style={styles.placeholder}>
                  <div style={{ ...styles.placeholderIcon, color: designTokens.colors.amber[600] }}>
                    <BarChartOutlined />
                  </div>
                  <h3 style={{ color: designTokens.semanticColors.text.primary }}>数据分析</h3>
                  <p style={{ color: designTokens.semanticColors.text.tertiary }}>
                    请通过 AI 助手查看数据，例如："查看平台统计数据"
                  </p>
                </div>
              )}
              {currentView === 'settings' && (
                <div style={styles.placeholder}>
                  <div style={{ ...styles.placeholderIcon, color: designTokens.colors.purple[600] }}>
                    <SettingOutlined />
                  </div>
                  <h3 style={{ color: designTokens.semanticColors.text.primary }}>设置</h3>
                  <p style={{ color: designTokens.semanticColors.text.tertiary }}>
                    设置页面开发中...
                  </p>
                </div>
              )}
            </div>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

const styles: Record<string, React.CSSProperties> = {
  logo: {
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
  },
  header: {
    padding: `0 ${designTokens.spacing['2xl']}px`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    position: 'sticky',
    top: 0,
    zIndex: 99,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: designTokens.spacing.lg,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: designTokens.semanticColors.text.primary,
  },
  headerBadge: {
    fontSize: 11,
    color: designTokens.colors.green[700],
    backgroundColor: designTokens.colors.green[50],
    padding: `2px ${designTokens.spacing.sm}px`,
    borderRadius: designTokens.radii.sm,
    border: `1px solid ${designTokens.colors.green[200]}`,
    fontWeight: 500,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: designTokens.spacing.lg,
  },
  trigger: {
    fontSize: 18,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    color: designTokens.semanticColors.text.secondary,
    transition: designTokens.transitions.all,
    padding: designTokens.spacing.sm,
    borderRadius: designTokens.radii.md,
  },
  content: {
    margin: 0,
    padding: 0,
    background: designTokens.semanticColors.background.primary,
  },
  contentInner: {
    margin: 0,
    padding: designTokens.spacing.lg,
    minHeight: 'calc(100vh - 64px)',
  },
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: 'calc(100vh - 180px)',
    gap: designTokens.spacing.lg,
  },
  placeholderIcon: {
    fontSize: 48,
    color: designTokens.colors.blue[500],
    marginBottom: designTokens.spacing.sm,
  },
};

export default App;
