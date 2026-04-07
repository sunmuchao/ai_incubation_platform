import React, { useState } from 'react';
import { Layout, Input, Avatar, Dropdown, Badge, Space } from 'antd';
import {
  SearchOutlined,
  BellOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Header } = Layout;

const HeaderComp: React.FC = () => {
  const [searchValue, setSearchValue] = useState('');

  const menuItems: MenuProps['items'] = [
    {
      key: '1',
      label: '系统设置',
    },
    {
      key: '2',
      label: '个人中心',
    },
    {
      type: 'divider',
    },
    {
      key: '3',
      label: '退出登录',
      danger: true,
    },
  ];

  return (
    <Header
      style={{
        position: 'sticky',
        top: 0,
        left: 220,
        right: 0,
        zIndex: 99,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        background: '#141414',
        borderBottom: '1px solid #303030',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <ThunderboltOutlined style={{ fontSize: 20, color: '#52c41a' }} />
        <span style={{ color: '#52c41a', fontSize: 14 }}>系统运行正常</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <Input
          placeholder="搜索服务、指标、日志..."
          prefix={<SearchOutlined style={{ color: 'rgba(255,255,255,0.45)' }} />}
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          style={{
            width: 300,
            background: '#1f1f1f',
            borderColor: '#303030',
          }}
        />

        <Badge count={5} size="small">
          <BellOutlined style={{ fontSize: 20, cursor: 'pointer', color: 'rgba(255,255,255,0.85)' }} />
        </Badge>

        <Dropdown menu={{ items: menuItems }} placement="bottomRight" arrow>
          <Space style={{ cursor: 'pointer' }}>
            <Avatar icon={<UserOutlined />} style={{ background: '#1890ff' }} />
            <span style={{ color: 'rgba(255,255,255,0.85)' }}>管理员</span>
          </Space>
        </Dropdown>
      </div>
    </Header>
  );
};

export default HeaderComp;
