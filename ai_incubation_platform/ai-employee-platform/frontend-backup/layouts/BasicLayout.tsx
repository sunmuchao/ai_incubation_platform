/**
 * 基础布局组件 - 带侧边栏导航
 */
import React, { useState, useMemo } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, theme } from 'antd';
import {
  DashboardOutlined,
  ShopOutlined,
  TrophyOutlined,
  RocketOutlined,
  TeamOutlined,
  HeartOutlined,
  RobotOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks';
import type { ReactNode } from 'react';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;

interface BasicLayoutProps {
  children: ReactNode;
}

const BasicLayout: React.FC<BasicLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { token } = theme.useToken();

  // 菜单配置
  const menuItems: MenuProps['items'] = useMemo(
    () => [
      {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: '工作台',
      },
      {
        key: '/marketplace',
        icon: <ShopOutlined />,
        label: '人才市场',
      },
      {
        key: '/performance',
        icon: <TrophyOutlined />,
        label: '绩效管理',
      },
      {
        key: '/career',
        icon: <RocketOutlined />,
        label: '职业发展',
      },
      {
        key: '/remote-work',
        icon: <TeamOutlined />,
        label: '远程工作',
      },
      {
        key: '/culture',
        icon: <HeartOutlined />,
        label: '组织文化',
      },
      {
        key: '/wellness',
        icon: <HeartOutlined />,
        label: '员工福祉',
      },
      {
        key: '/assistant',
        icon: <RobotOutlined />,
        label: '智能助手',
      },
      {
        type: 'divider',
      },
      {
        key: '/settings',
        icon: <SettingOutlined />,
        label: '系统设置',
      },
    ],
    []
  );

  // 用户菜单
  const userMenuItems: MenuProps['items'] = useMemo(
    () => [
      {
        key: 'profile',
        icon: <UserOutlined />,
        label: '个人中心',
        onClick: () => navigate('/settings'),
      },
      {
        type: 'divider',
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: () => {
          logout();
          navigate('/login');
        },
      },
    ],
    [navigate, logout]
  );

  // 通知菜单
  const notificationMenuItems: MenuProps['items'] = useMemo(
    () => [
      {
        key: '1',
        label: '您有新的绩效评估任务',
        onClick: () => navigate('/performance'),
      },
      {
        key: '2',
        label: '团队活动即将开始',
        onClick: () => navigate('/remote-work'),
      },
      {
        key: '3',
        label: '职业发展建议已生成',
        onClick: () => navigate('/career'),
      },
    ],
    [navigate]
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        breakpoint="lg"
        collapsedWidth={80}
        width={256}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#002140',
            color: '#fff',
            fontSize: collapsed ? 20 : 18,
            fontWeight: 600,
            overflow: 'hidden',
          }}
        >
          {collapsed ? 'AI' : 'AI Employee'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout
        style={{
          marginLeft: collapsed ? 80 : 256,
          transition: 'margin-left 0.2s',
        }}
      >
        <Header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 99,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: token.colorBgContainer,
            boxShadow: '0 1px 4px rgba(0,21,41,0.08)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <span
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 20,
                cursor: 'pointer',
              }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
            }}
          >
            {/* 通知 */}
            <Dropdown menu={{ items: notificationMenuItems }} placement="bottomRight" arrow>
              <Badge count={3} size="small">
                <BellOutlined
                  style={{
                    fontSize: 18,
                    cursor: 'pointer',
                    color: token.colorTextSecondary,
                  }}
                />
              </Badge>
            </Dropdown>

            {/* 用户信息 */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  cursor: 'pointer',
                }}
              >
                <Avatar
                  size={32}
                  style={{ backgroundColor: token.colorPrimary }}
                  icon={<UserOutlined />}
                />
                <span style={{ color: token.colorTextHeading }}>
                  {user?.username || '用户'}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
            minHeight: 'calc(100vh - 128px)',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default BasicLayout;
