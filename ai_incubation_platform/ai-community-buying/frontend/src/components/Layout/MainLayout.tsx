/**
 * Bento Grid 风格主布局
 * Linear 风格导航和侧边栏
 */
import React, { useState } from 'react'
import {
  HomeOutlined,
  ShoppingOutlined,
  TeamOutlined,
  FileTextOutlined,
  ShoppingCartOutlined,
  UserOutlined,
  BellOutlined,
  SettingOutlined,
  DashboardOutlined,
  MoonOutlined,
  SunOutlined,
  GlobalOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useNotificationStore, useSettingsStore } from '@/stores'
import { useNotifications } from '@/hooks/useApi'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { unreadCount, markAllAsRead } = useNotificationStore()
  const { theme: appTheme, setTheme, language, setLanguage } = useSettingsStore()

  const { data: notifications = [] } = useNotifications(user?.id || '', true)

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/products',
      icon: <ShoppingOutlined />,
      label: '商品',
    },
    {
      key: '/groups',
      icon: <TeamOutlined />,
      label: '团购',
    },
    {
      key: '/orders',
      icon: <FileTextOutlined />,
      label: '订单',
    },
    {
      key: '/cart',
      icon: <ShoppingCartOutlined />,
      label: '购物车',
    },
    {
      key: '/organizer',
      icon: <DashboardOutlined />,
      label: '团长中心',
    },
    {
      key: '/admin',
      icon: <SettingOutlined />,
      label: '运营后台',
    },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
      onClick: () => {
        navigate('/profile')
        setShowUserMenu(false)
      },
    },
    {
      key: 'theme',
      icon: appTheme === 'dark' ? <SunOutlined /> : <MoonOutlined />,
      label: appTheme === 'dark' ? '明亮模式' : '黑暗模式',
      onClick: () => {
        setTheme(appTheme === 'dark' ? 'light' : 'dark')
        setShowUserMenu(false)
      },
    },
    {
      key: 'language',
      icon: <GlobalOutlined />,
      label: language === 'zh' ? 'English' : '中文',
      onClick: () => {
        setLanguage(language === 'zh' ? 'en' : 'zh')
        setShowUserMenu(false)
      },
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

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        background: 'var(--color-bg-secondary)',
      }}
    >
      {/* 侧边栏 - Bento 风格 */}
      <aside
        style={{
          width: collapsed ? 72 : 240,
          background: 'var(--color-bg-card)',
          borderRight: `1px solid var(--color-border)`,
          transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          display: 'flex',
          flexDirection: 'column',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: `1px solid var(--color-border)`,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 'var(--radius-bento-sm)',
              background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 18,
              flexShrink: 0,
            }}
          >
            <ShoppingOutlined />
          </div>
          {!collapsed && (
            <span
              style={{
                marginLeft: 12,
                fontSize: 16,
                fontWeight: 600,
                color: 'var(--color-text-primary)',
                whiteSpace: 'nowrap',
              }}
            >
              AI 社区团购
            </span>
          )}
        </div>

        {/* 导航菜单 */}
        <nav style={{ flex: 1, padding: 12, overflow: 'auto' }}>
          {menuItems.map((item) => {
            const isActive = location.pathname === item.key
            return (
              <button
                key={item.key}
                onClick={() => navigate(item.key)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: collapsed ? '12px' : '12px 16px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  background: isActive
                    ? 'var(--color-primary-light)'
                    : 'transparent',
                  border: 'none',
                  borderRadius: 'var(--radius-bento-sm)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  marginBottom: 4,
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'var(--color-bg-tertiary)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = isActive
                      ? 'var(--color-primary-light)'
                      : 'transparent'
                  }
                }}
              >
                <span
                  style={{
                    fontSize: 18,
                    color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                    flexShrink: 0,
                  }}
                >
                  {item.icon}
                </span>
                {!collapsed && (
                  <span
                    style={{
                      fontSize: 14,
                      fontWeight: isActive ? 500 : 400,
                      color: isActive ? 'var(--color-primary)' : 'var(--color-text-primary)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.label}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* 底部帮助 */}
        {!collapsed && (
          <div
            style={{
              padding: 16,
              borderTop: `1px solid var(--color-border)`,
            }}
          >
            <button
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 16px',
                background: 'transparent',
                border: 'none',
                borderRadius: 'var(--radius-bento-sm)',
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-tertiary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              <QuestionCircleOutlined />
              <span style={{ fontSize: 13 }}>帮助与反馈</span>
            </button>
          </div>
        )}
      </aside>

      {/* 主内容区 */}
      <div
        style={{
          flex: 1,
          marginLeft: collapsed ? 72 : 240,
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}
      >
        {/* 顶部导航栏 - Bento 风格 */}
        <header
          style={{
            height: 64,
            background: 'var(--color-bg-card)',
            borderBottom: `1px solid var(--color-border)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            position: 'sticky',
            top: 0,
            zIndex: 99,
            backdropFilter: 'blur(8px)',
          }}
        >
          {/* 左侧 - 折叠按钮 */}
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button
              onClick={() => setCollapsed(!collapsed)}
              style={{
                width: 40,
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'transparent',
                border: 'none',
                borderRadius: 'var(--radius-bento-sm)',
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                fontSize: 16,
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-tertiary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </button>

            {/* 面包屑/页面标题 */}
            <div
              style={{
                marginLeft: 16,
                fontSize: 14,
                color: 'var(--color-text-secondary)',
              }}
            >
              {menuItems.find((item) => item.key === location.pathname)?.label || '首页'}
            </div>
          </div>

          {/* 右侧 - 操作区 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* 通知按钮 */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                style={{
                  width: 40,
                  height: 40,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 'var(--radius-bento-sm)',
                  cursor: 'pointer',
                  color: 'var(--color-text-secondary)',
                  fontSize: 18,
                  position: 'relative',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--color-bg-tertiary)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                <BellOutlined />
                {unreadCount > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: 6,
                      right: 8,
                      minWidth: 18,
                      height: 18,
                      borderRadius: 9,
                      background: 'var(--color-accent)',
                      color: 'white',
                      fontSize: 11,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: `2px solid var(--color-bg-card)`,
                    }}
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* 通知下拉面板 - Bento 风格 */}
              {showNotifications && (
                <>
                  <div
                    style={{
                      position: 'fixed',
                      inset: 0,
                      zIndex: 98,
                    }}
                    onClick={() => setShowNotifications(false)}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 8px)',
                      right: 0,
                      width: 320,
                      maxHeight: 400,
                      background: 'var(--color-bg-card)',
                      borderRadius: 'var(--radius-bento-lg)',
                      boxShadow: 'var(--shadow-bento-hover)',
                      border: `1px solid var(--color-border)`,
                      zIndex: 99,
                      overflow: 'hidden',
                      animation: 'slideUp 0.2s ease-out',
                    }}
                  >
                    <div
                      style={{
                        padding: '12px 16px',
                        borderBottom: `1px solid var(--color-border)`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>
                        通知
                      </span>
                      <button
                        onClick={markAllAsRead}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--color-primary)',
                          fontSize: 12,
                          cursor: 'pointer',
                          padding: '4px 8px',
                          borderRadius: 'var(--radius-bento-sm)',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'var(--color-primary-light)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'transparent'
                        }}
                      >
                        全部已读
                      </button>
                    </div>
                    <div style={{ overflow: 'auto', maxHeight: 320 }}>
                      {notifications.length > 0 ? (
                        notifications.map((n) => (
                          <div
                            key={n.id}
                            style={{
                              padding: '12px 16px',
                              borderBottom: `1px solid var(--color-border)`,
                              background: !n.isRead ? 'var(--color-primary-light)' : undefined,
                              cursor: 'pointer',
                              transition: 'background 0.2s ease',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = !n.isRead
                                ? 'var(--color-primary-light)'
                                : 'var(--color-bg-tertiary)'
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = !n.isRead
                                ? 'var(--color-primary-light)'
                                : 'transparent'
                            }}
                          >
                            <div
                              style={{
                                fontWeight: 500,
                                fontSize: 14,
                                color: 'var(--color-text-primary)',
                                marginBottom: 4,
                              }}
                            >
                              {n.title}
                            </div>
                            <div
                              style={{
                                fontSize: 13,
                                color: 'var(--color-text-secondary)',
                                marginBottom: 6,
                              }}
                            >
                              {n.content}
                            </div>
                            <div
                              style={{
                                fontSize: 11,
                                color: 'var(--color-text-tertiary)',
                              }}
                            >
                              {dayjs(n.createdAt).fromNow()}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div
                          style={{
                            padding: 40,
                            textAlign: 'center',
                            color: 'var(--color-text-tertiary)',
                          }}
                        >
                          暂无通知
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* 用户菜单 */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 12px 6px 6px',
                  background: 'transparent',
                  border: `1px solid var(--color-border)`,
                  borderRadius: 'var(--radius-bento-lg)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--color-bg-tertiary)'
                  e.currentTarget.style.borderColor = 'var(--color-border-dark)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.borderColor = 'var(--color-border)'
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: user?.avatar
                      ? `url(${user.avatar}) center/cover`
                      : 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: user?.avatar ? 'transparent' : 'white',
                    fontSize: 14,
                    fontWeight: 500,
                  }}
                >
                  {!user?.avatar && (user?.nickname?.[0] || 'U')}
                </div>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {user?.nickname || '用户'}
                </span>
              </button>

              {/* 用户下拉菜单 - Bento 风格 */}
              {showUserMenu && (
                <>
                  <div
                    style={{
                      position: 'fixed',
                      inset: 0,
                      zIndex: 98,
                    }}
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 8px)',
                      right: 0,
                      width: 200,
                      background: 'var(--color-bg-card)',
                      borderRadius: 'var(--radius-bento-lg)',
                      boxShadow: 'var(--shadow-bento-hover)',
                      border: `1px solid var(--color-border)`,
                      zIndex: 99,
                      overflow: 'hidden',
                      animation: 'slideUp 0.2s ease-out',
                    }}
                  >
                    {userMenuItems.map((item, index) => {
                      if (item.type === 'divider') {
                        return (
                          <div
                            key={`divider-${index}`}
                            style={{
                              height: 1,
                              background: 'var(--color-border)',
                              margin: '8px 0',
                            }}
                          />
                        )
                      }
                      return (
                        <button
                          key={item.key}
                          onClick={item.onClick}
                          style={{
                            width: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            padding: '10px 16px',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.2s ease',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--color-bg-tertiary)'
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent'
                          }}
                        >
                          <span
                            style={{
                              fontSize: 16,
                              color: 'var(--color-text-secondary)',
                            }}
                          >
                            {item.icon}
                          </span>
                          <span
                            style={{
                              fontSize: 13,
                              color: 'var(--color-text-primary)',
                            }}
                          >
                            {item.label}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* 内容区域 - Bento Grid 容器 */}
        <main
          style={{
            flex: 1,
            padding: 24,
            overflow: 'auto',
          }}
        >
          <div
            style={{
              maxWidth: 1400,
              margin: '0 auto',
            }}
          >
            {children}
          </div>
        </main>

        {/* 页脚 */}
        <footer
          style={{
            padding: '16px 24px',
            background: 'var(--color-bg-card)',
            borderTop: `1px solid var(--color-border)`,
            textAlign: 'center',
            fontSize: 13,
            color: 'var(--color-text-tertiary)',
          }}
        >
          AI 社区团购平台 ©{new Date().getFullYear()} - 基于 AI 智能选品和动态定价的社区团购系统
        </footer>
      </div>
    </div>
  )
}

export default MainLayout
