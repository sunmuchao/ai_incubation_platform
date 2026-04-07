/**
 * 基础布局组件 - Bento Grid 风格
 * 精致的侧边栏导航和顶部栏
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
  MoonOutlined,
  SunOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks';
import type { ReactNode } from 'react';
import type { MenuProps } from 'antd';
import './BasicLayout.less';

const { Header, Sider, Content } = Layout;

interface BasicLayoutProps {
  children: ReactNode;
}

const BasicLayout: React.FC<BasicLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { token } = theme.useToken();

  // 切换暗色模式
  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    document.documentElement.setAttribute('data-theme', newMode ? 'dark' : 'light');
  };

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
    <Layout className="basic-layout">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        breakpoint="lg"
        collapsedWidth={80}
        width={256}
        className="layout-sider"
      >
        <div className="sider-logo">
          {collapsed ? 'AI' : 'AI Employee'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="sider-menu"
        />
      </Sider>
      <Layout className="layout-main">
        <Header className="layout-header">
          <div className="header-start">
            <span
              className="header-collapse-btn"
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </span>
          </div>

          <div className="header-end">
            {/* 暗色模式切换 */}
            <span
              className="header-icon-btn"
              onClick={toggleDarkMode}
              title={darkMode ? '切换亮色模式' : '切换暗色模式'}
            >
              {darkMode ? <SunOutlined /> : <MoonOutlined />}
            </span>

            {/* 通知 */}
            <Dropdown menu={{ items: notificationMenuItems }} placement="bottomRight" arrow>
              <Badge count={3} size="small" className="header-notification">
                <BellOutlined className="header-icon-btn" />
              </Badge>
            </Dropdown>

            {/* 用户信息 */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div className="header-user">
                <Avatar
                  size={32}
                  style={{ backgroundColor: token.colorPrimary }}
                  icon={<UserOutlined />}
                />
                <span className="header-user-name">
                  {user?.username || '用户'}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="layout-content">
          <div className="content-inner">
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default BasicLayout;
