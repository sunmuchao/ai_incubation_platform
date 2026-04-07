/**
 * 用户布局组件 - 用于登录/注册页面
 */
import React from 'react';
import { Layout } from 'antd';
import type { ReactNode } from 'react';

const { Content } = Layout;

interface UserLayoutProps {
  children: ReactNode;
}

const UserLayout: React.FC<UserLayoutProps> = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 480,
            padding: 40,
            background: '#fff',
            borderRadius: 16,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          }}
        >
          {children}
        </div>
      </Content>
    </Layout>
  );
};

export default UserLayout;
