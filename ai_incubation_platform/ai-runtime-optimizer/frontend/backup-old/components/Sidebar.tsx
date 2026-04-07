import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  MonitorOutlined,
  SearchOutlined,
  LineChartOutlined,
  ToolOutlined,
  RocketOutlined,
  EyeOutlined,
  RobotOutlined,
  BellOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: 'Dashboard',
  },
  {
    key: '/monitoring',
    icon: <MonitorOutlined />,
    label: '运行态监控',
  },
  {
    key: '/root-cause',
    icon: <SearchOutlined />,
    label: '根因分析',
  },
  {
    key: '/predictive',
    icon: <LineChartOutlined />,
    label: '预测维护',
  },
  {
    key: '/remediation',
    icon: <ToolOutlined />,
    label: '自主修复',
  },
  {
    key: '/optimization',
    icon: <RocketOutlined />,
    label: 'AI 优化建议',
  },
  {
    key: '/observability',
    icon: <EyeOutlined />,
    label: '可观测性',
  },
  {
    key: '/automation',
    icon: <RobotOutlined />,
    label: '自动化中心',
  },
  {
    key: '/alerts',
    icon: <BellOutlined />,
    label: '告警管理',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '设置',
  },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Sider
      width={220}
      theme="dark"
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
          borderBottom: '1px solid #303030',
        }}
      >
        <RocketOutlined style={{ fontSize: 24, color: '#1890ff', marginRight: 12 }} />
        <span style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>
          AI Runtime Optimizer
        </span>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{
          borderRight: 0,
          marginTop: 8,
        }}
      />
    </Sider>
  );
};

export default Sidebar;
