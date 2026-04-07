/**
 * AI Native Chat 布局
 * 简化的布局，专注于对话式交互
 */
import React from 'react'
import { Layout, Avatar, Dropdown, Button, Typography, Badge, theme } from 'antd'
import {
  UserOutlined,
  BellOutlined,
  MoonOutlined,
  SunOutlined,
  GlobalOutlined,
  LogoutOutlined,
  ShoppingOutlined,
} from '@ant-design/icons'
import { useAuthStore, useNotificationStore, useSettingsStore } from '@/stores'
import { useNotifications } from '@/hooks/useApi'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const { Header, Content, Footer } = Layout
const { Text } = Typography

interface ChatLayoutProps {
  children: React.ReactNode
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({ children }) => {
  const { user, logout } = useAuthStore()
  const { unreadCount, markAllAsRead } = useNotificationStore()
  const { theme: appTheme, setTheme, language, setLanguage } = useSettingsStore()
  const { token } = theme.useToken()

  const { data: notifications = [] } = useNotifications(user?.id || '', true)

  const userMenuItems = [
    {
      key: 'theme',
      icon: appTheme === 'dark' ? <SunOutlined /> : <MoonOutlined />,
      label: appTheme === 'dark' ? '明亮模式' : '黑暗模式',
      onClick: () => setTheme(appTheme === 'dark' ? 'light' : 'dark'),
    },
    {
      key: 'language',
      icon: <GlobalOutlined />,
      label: language === 'zh' ? 'English' : '中文',
      onClick: () => setLanguage(language === 'zh' ? 'en' : 'zh'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: logout,
    },
  ]

  const notificationMenu = (
    <div style={{ width: 300, maxHeight: 400, overflow: 'auto' }}>
      {notifications.length > 0 ? (
        <>
          <div
            style={{
              padding: '8px 16px',
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <Text strong>通知</Text>
            <Button type="link" size="small" onClick={markAllAsRead}>
              全部已读
            </Button>
          </div>
          {notifications.map((n) => (
            <div
              key={n.id}
              style={{
                padding: '12px 16px',
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                background: !n.isRead ? token.colorPrimaryBg : undefined,
              }}
            >
              <div style={{ fontWeight: 500 }}>{n.title}</div>
              <div style={{ fontSize: 12, color: token.colorTextSecondary }}>{n.content}</div>
              <div style={{ fontSize: 11, color: token.colorTextTertiary, marginTop: 4 }}>
                {dayjs(n.createdAt).fromNow()}
              </div>
            </div>
          ))}
        </>
      ) : (
        <div style={{ padding: '20px', textAlign: 'center', color: token.colorTextTertiary }}>
          暂无通知
        </div>
      )}
    </div>
  )

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <div
        style={{
          width: 80,
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <ShoppingOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
        </div>

        {/* 侧边功能按钮 */}
        <div style={{ flex: 1, padding: '16px 8px' }}>
          {/* 可以添加侧边功能 */}
        </div>

        {/* 底部用户信息 */}
        <div
          style={{
            padding: '16px',
            borderTop: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Dropdown menu={{ items: userMenuItems }} trigger={['click']}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <Avatar src={user?.avatar} icon={<UserOutlined />} />
            </div>
          </Dropdown>
        </div>
      </div>

      <Layout>
        <Header
          style={{
            padding: '0 16px',
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 64,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Text strong style={{ fontSize: 18 }}>AI 社区团购</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Dropdown dropdownRender={() => notificationMenu} trigger={['click']}>
              <Badge count={unreadCount} size="small">
                <Button type="text" icon={<BellOutlined />} style={{ fontSize: 18 }} />
              </Badge>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: 0,
            overflow: 'hidden',
            background: token.colorBgContainer,
          }}
        >
          {children}
        </Content>
        <Footer style={{ textAlign: 'center', color: token.colorTextTertiary, padding: '12px' }}>
          AI 社区团购平台 - AI Native 版 ©{new Date().getFullYear()}
        </Footer>
      </Layout>
    </Layout>
  )
}
