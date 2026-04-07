/**
 * AI Native App - 主布局组件
 * Bento Grid & Monochromatic 设计风格
 */

import React, { useState } from 'react';
import { Layout, Menu, Drawer, Badge, Avatar, Dropdown } from 'antd';
import {
  RobotOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  BellOutlined,
  MenuOutlined,
  CloseOutlined,
  BugOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useNotificationStore } from '@/store';
import { colors, shadows, radii, spacing, typography } from '@/styles/design-tokens';

const { Header, Content, Sider } = Layout;

interface MainLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: string) => void;
}

/**
 * 主布局组件 - Bento Grid 风格
 */
const MainLayout: React.FC<MainLayoutProps> = ({ children, currentPage, onNavigate }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const { notifications, unreadCount } = useNotificationStore();

  const menuItems: MenuProps['items'] = [
    {
      key: 'chat',
      icon: <MessageOutlined />,
      label: 'AI 对话',
      title: 'AI 对话',
    },
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '动态仪表板',
      title: '动态仪表板',
    },
    {
      key: 'agents',
      icon: <ThunderboltOutlined />,
      label: 'Agent 可视化',
      title: 'Agent 可视化',
    },
    {
      key: 'diagnosis',
      icon: <BugOutlined />,
      label: 'AI 诊断',
      title: 'AI 诊断',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
      title: '设置',
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    onNavigate(e.key);
    setMobileDrawerOpen(false);
  };

  // 通知下拉菜单 - Bento 风格
  const notificationMenu = (
    <div style={{
      padding: parseInt(spacing[4]),
      maxWidth: 400,
      background: colors.dark.bgCard,
      borderRadius: radii.lg,
      border: `1px solid ${colors.dark.border}`,
      boxShadow: shadows.elevated,
    }}>
      <div style={{
        fontWeight: 600,
        marginBottom: parseInt(spacing[3]),
        color: colors.neutral[100],
        fontSize: typography.fontSize.sm,
      }}>通知</div>
      {notifications.length === 0 ? (
        <div style={{
          color: colors.neutral[500],
          textAlign: 'center',
          padding: parseInt(spacing[5]),
          fontSize: typography.fontSize.sm,
        }}>
          暂无通知
        </div>
      ) : (
        notifications.slice(0, 5).map((n) => (
          <div
            key={n.id}
            style={{
              padding: `${spacing[2]} ${spacing[3]}`,
              background: colors.dark.bgCardHover,
              borderRadius: radii.md,
              marginBottom: spacing[2],
              transition: `all ${transitions.durations.normal} ${transitions.timing.ease}`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.primary[900];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = colors.dark.bgCardHover;
            }}
          >
            <div style={{ color: colors.neutral[100], fontWeight: 500, fontSize: typography.fontSize.base }}>{n.title}</div>
            <div style={{ color: colors.neutral[400], fontSize: typography.fontSize.xs, marginTop: spacing[1] }}>{n.message}</div>
          </div>
        ))
      )}
    </div>
  );

  return (
    <Layout style={{
      minHeight: '100vh',
      background: colors.dark.bg,
    }}>
      {/* 桌面端侧边栏 - Bento 风格 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        collapsedWidth={80}
        style={{
          background: `linear-gradient(180deg, ${colors.dark.bgElevated} 0%, ${colors.dark.bg} 100%)`,
          borderRight: `1px solid ${colors.dark.border}`,
          overflow: 'auto',
        }}
      >
        {/* Logo - Bento 卡片风格 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0.05) 100%)`,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: radii.lg,
              background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: shadows.glow,
            }}
          >
            <RobotOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          {!collapsed && (
            <span
              style={{
                color: colors.neutral[100],
                fontWeight: 600,
                marginLeft: parseInt(spacing[3]),
                fontSize: typography.fontSize.lg,
                letterSpacing: '0.5px',
              }}
            >
              AI Optimizer
            </span>
          )}
        </div>

        {/* 导航菜单 - Bento 风格 */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            borderRight: 'none',
            padding: parseInt(spacing[2]),
          }}
          itemRender={(node, { isSelected }) => (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: `${spacing[3]} ${spacing[3]}`,
                marginBottom: spacing[1],
                borderRadius: radii.lg,
                background: isSelected
                  ? `linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%)`
                  : 'transparent',
                border: isSelected ? `1px solid ${colors.primary[700]}` : '1px solid transparent',
                transition: `all ${transitions.durations.normal} ${transitions.timing.ease}`,
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.background = colors.dark.bgCardHover;
                  e.currentTarget.style.borderColor = colors.dark.borderHover;
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.borderColor = 'transparent';
                }
              }}
            >
              {node}
            </div>
          )}
        />
      </Sider>

      {/* 主内容区 */}
      <Layout>
        {/* 顶部栏 - Bento 风格 */}
        <Header
          style={{
            background: `rgba(${parseInt(colors.dark.bgElevated.slice(1, 3), 16)}, ${parseInt(colors.dark.bgElevated.slice(3, 5), 16)}, ${parseInt(colors.dark.bgElevated.slice(5, 7), 16)}, 0.8)`,
            backdropFilter: 'blur(12px)',
            borderBottom: `1px solid ${colors.dark.border}`,
            padding: `0 ${spacing[6]}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 64,
          }}
        >
          {/* 左侧：移动端菜单按钮 */}
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <MenuOutlined
              onClick={() => setMobileDrawerOpen(true)}
              style={{
                fontSize: 20,
                color: colors.neutral[300],
                cursor: 'pointer',
                display: 'none',
                marginRight: parseInt(spacing[4]),
              }}
            />
            <span style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.base,
              fontWeight: 500,
            }}>
              AI 运行态优化平台
            </span>
          </div>

          {/* 右侧：操作区 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: parseInt(spacing[4]) }}>
            {/* 通知 */}
            <Dropdown
              overlay={notificationMenu}
              trigger={['click']}
              placement="bottomRight"
              overlayStyle={{ background: 'transparent' }}
            >
              <Badge
                count={unreadCount}
                size="small"
                styles={{
                  indicator: {
                    background: colors.semantic.error,
                    boxShadow: `0 0 12px ${colors.semantic.error}`,
                  }
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: radii.lg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: colors.dark.bgCard,
                    border: `1px solid ${colors.dark.border}`,
                    cursor: 'pointer',
                    transition: `all ${transitions.durations.normal} ${transitions.timing.ease}`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = colors.dark.bgCardHover;
                    e.currentTarget.style.borderColor = colors.primary[700];
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = colors.dark.bgCard;
                    e.currentTarget.style.borderColor = colors.dark.border;
                  }}
                >
                  <BellOutlined
                    style={{
                      fontSize: 18,
                      color: colors.neutral[300],
                    }}
                  />
                </div>
              </Badge>
            </Dropdown>

            {/* 用户头像 - Bento 风格 */}
            <Avatar
              style={{
                backgroundColor: colors.primary[700],
                cursor: 'pointer',
                width: 40,
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: shadows.card,
                border: `1px solid ${colors.primary[600]}`,
              }}
              icon={<RobotOutlined style={{ fontSize: 18 }} />}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = colors.primary[600];
                e.currentTarget.style.boxShadow = shadows.glow;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = colors.primary[700];
                e.currentTarget.style.boxShadow = shadows.card;
              }}
            />
          </div>
        </Header>

        {/* 内容区 - Bento 风格背景 */}
        <Content
          style={{
            padding: spacing[6],
            overflow: 'auto',
            background: colors.dark.bg,
          }}
        >
          <div
            style={{
              maxWidth: 1400,
              margin: '0 auto',
              minHeight: 'calc(100vh - 188px)',
            }}
          >
            {children}
          </div>
        </Content>
      </Layout>

      {/* 移动端抽屉 */}
      <Drawer
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        width={280}
        styles={{
          body: {
            padding: 0,
            background: colors.dark.bgElevated,
          },
          header: { display: 'none' },
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `0 ${spacing[6]}`,
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0.05) 100%)`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: radii.lg,
                background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
            </div>
            <span style={{
              color: colors.neutral[100],
              fontWeight: 600,
              marginLeft: parseInt(spacing[3]),
              fontSize: typography.fontSize.lg,
            }}>
              AI Optimizer
            </span>
          </div>
          <CloseOutlined
            onClick={() => setMobileDrawerOpen(false)}
            style={{
              color: colors.neutral[400],
              cursor: 'pointer',
              fontSize: 18,
              transition: `color ${transitions.durations.fast}`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = colors.neutral[200];
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = colors.neutral[400];
            }}
          />
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            borderRight: 'none',
            padding: spacing[2],
          }}
        />
      </Drawer>
    </Layout>
  );
};

export default MainLayout;
