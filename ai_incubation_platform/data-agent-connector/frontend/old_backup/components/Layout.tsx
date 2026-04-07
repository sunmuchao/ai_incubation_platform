/**
 * 主布局组件
 */
import React, { useState } from 'react'
import { Layout, Menu, theme, Avatar, Dropdown, Badge } from 'antd'
import {
  DashboardOutlined,
  DatabaseOutlined,
  SearchOutlined,
  DeploymentUnitOutlined,
  TeamOutlined,
  SafetyCertificateOutlined,
  AlertOutlined,
  FileTextOutlined,
  ShopOutlined,
  SettingOutlined,
  BellOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { ROUTES } from '../config/routes'

import type { MenuProps } from 'antd'
type MenuItem = Required<MenuProps>['items'][number]

const { Header, Sider, Content } = Layout

// 导航菜单配置
const navigationItems: MenuItem[] = [
  {
    key: ROUTES.DASHBOARD,
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    type: 'divider' as const,
  },
  {
    key: ROUTES.CONNECTORS,
    icon: <DatabaseOutlined />,
    label: '连接器管理',
  },
  {
    key: ROUTES.DATA_QUERY,
    icon: <SearchOutlined />,
    label: '数据查询',
    children: [
      { key: ROUTES.SQL_EDITOR, label: 'SQL 编辑器' },
      { key: ROUTES.QUERY_HISTORY, label: '查询历史' },
    ],
  },
  {
    key: ROUTES.LINEAGE,
    icon: <DeploymentUnitOutlined />,
    label: '血缘图谱',
  },
  {
    type: 'divider' as const,
  },
  {
    key: ROUTES.GOVERNANCE,
    icon: <SafetyCertificateOutlined />,
    label: '数据治理',
  },
  {
    key: ROUTES.PERMISSIONS,
    icon: <TeamOutlined />,
    label: '权限管理',
  },
  {
    type: 'divider' as const,
  },
  {
    key: ROUTES.API_MANAGEMENT,
    icon: <ShopOutlined />,
    label: 'API 管理',
    children: [
      { key: ROUTES.API_DOCS, label: 'API 文档' },
      { key: ROUTES.API_KEYS, label: '密钥管理' },
      { key: ROUTES.API_USAGE, label: '用量统计' },
    ],
  },
  {
    key: ROUTES.MONITORING,
    icon: <AlertOutlined />,
    label: '监控中心',
  },
  {
    key: ROUTES.LOGS,
    icon: <FileTextOutlined />,
    label: '日志审计',
  },
  {
    key: ROUTES.MARKETPLACE,
    icon: <ShopOutlined />,
    label: '连接器市场',
  },
  {
    type: 'divider' as const,
  },
  {
    key: ROUTES.ADMIN,
    icon: <SettingOutlined />,
    label: '管理后台',
  },
]

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  // 用户菜单下拉
  const userMenuItems: MenuItem[] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        localStorage.removeItem('dac_api_key')
        navigate('/login')
      },
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        collapsedWidth={80}
        onBreakpoint={(broken) => {
          setCollapsed(broken)
        }}
        theme="dark"
      >
        <div className="flex items-center justify-center h-16 bg-[#002140]">
          {!collapsed ? (
            <h1 className="text-white text-lg font-bold">DAC 数据网关</h1>
          ) : (
            <DatabaseOutlined className="text-white text-xl" />
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={navigationItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div className="flex items-center">
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger text-lg cursor-pointer mr-4',
              onClick: () => setCollapsed(!collapsed),
            })}
          </div>
          <div className="flex items-center gap-4">
            <Badge count={3} size="small">
              <BellOutlined className="text-lg cursor-pointer" />
            </Badge>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div className="flex items-center gap-2 cursor-pointer">
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <span className="hidden md:inline">管理员</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            minHeight: 280,
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
