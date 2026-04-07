import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { ConfigProvider, Layout, Menu } from 'antd';
import { HomeOutlined, TeamOutlined, FileTextOutlined, BarChartOutlined, SettingOutlined, MenuFoldOutlined, MenuUnfoldOutlined, } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
// Bento Grid 组件和样式
import { Card } from './components/BentoGrid';
import designTokens from './styles/designTokens';
import { cssVariables } from './styles/globalStyles';
// AI Native 组件
import ChatInterface from './components/ChatInterface';
import NotificationPanel from './components/NotificationPanel';
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
const App = () => {
    const [collapsed, setCollapsed] = useState(false);
    const [currentView, setCurrentView] = useState('chat');
    // 处理 AI 生成的 UI 中的操作选择
    const handleActionSelect = (action, data) => {
        console.log('Action selected:', action, data);
    };
    // 处理通知点击
    const handleNotificationClick = (notification) => {
        console.log('Notification clicked:', notification);
    };
    // 菜单项配置 - Monochromatic 配色
    const menuItems = [
        {
            key: 'chat',
            icon: _jsx(HomeOutlined, { style: { color: designTokens.colors.blue[500] } }),
            label: 'AI 助手',
        },
        {
            key: 'tasks',
            icon: _jsx(FileTextOutlined, { style: { color: designTokens.colors.blue[500] } }),
            label: '任务管理',
        },
        {
            key: 'workers',
            icon: _jsx(TeamOutlined, { style: { color: designTokens.colors.blue[500] } }),
            label: '工人管理',
        },
        {
            key: 'analytics',
            icon: _jsx(BarChartOutlined, { style: { color: designTokens.colors.blue[500] } }),
            label: '数据分析',
        },
        {
            key: 'settings',
            icon: _jsx(SettingOutlined, { style: { color: designTokens.colors.blue[500] } }),
            label: '设置',
        },
    ];
    return (_jsxs(ConfigProvider, { locale: zhCN, theme: {
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
        }, children: [_jsx("style", { children: cssVariables }), _jsxs(Layout, { style: { minHeight: '100vh', background: designTokens.semanticColors.background.primary }, children: [_jsxs(Sider, { trigger: null, collapsible: true, collapsed: collapsed, theme: "light", style: {
                            background: '#ffffff',
                            boxShadow: designTokens.shadows.card,
                            borderRight: `1px solid ${designTokens.semanticColors.border.subtle}`,
                            zIndex: 100,
                        }, children: [_jsx("div", { style: styles.logo, children: collapsed ? '🤖' : (_jsxs(_Fragment, { children: [_jsx("span", { style: { marginRight: 8 }, children: "\uD83E\uDD16" }), _jsx("span", { style: {
                                                fontSize: 14,
                                                fontWeight: 600,
                                                background: `linear-gradient(135deg, ${designTokens.colors.blue[600]}, ${designTokens.colors.blue[400]})`,
                                                WebkitBackgroundClip: 'text',
                                                WebkitTextFillColor: 'transparent',
                                            }, children: "AI \u62DB\u8058\u5E73\u53F0" })] })) }), _jsx(Menu, { mode: "inline", selectedKeys: [currentView], items: menuItems, onClick: ({ key }) => setCurrentView(key), style: {
                                    borderRight: 'none',
                                    background: 'transparent',
                                } })] }), _jsxs(Layout, { children: [_jsxs(Header, { style: {
                                    ...styles.header,
                                    paddingLeft: collapsed ? 80 : 200,
                                    background: '#ffffff',
                                    borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
                                    boxShadow: designTokens.shadows.card,
                                }, children: [_jsxs("div", { style: styles.headerLeft, children: [_jsx("button", { onClick: () => setCollapsed(!collapsed), style: styles.trigger, children: collapsed ? _jsx(MenuUnfoldOutlined, {}) : _jsx(MenuFoldOutlined, {}) }), _jsx("span", { style: styles.headerTitle, children: "AI Native \u62DB\u8058\u5E73\u53F0" }), _jsx("span", { style: styles.headerBadge, children: "DeerFlow 2.0 \u9A71\u52A8" })] }), _jsx("div", { style: styles.headerRight, children: _jsx(NotificationPanel, { userId: "current_user", onNotificationClick: handleNotificationClick }) })] }), _jsx(Content, { style: styles.content, children: _jsxs("div", { style: styles.contentInner, children: [currentView === 'chat' && (_jsx(Card, { variant: "default", padding: "none", style: {
                                                height: 'calc(100vh - 140px)',
                                                overflow: 'hidden',
                                            }, children: _jsx(ChatInterface, { userId: "current_user", onActionSelect: handleActionSelect }) })), currentView === 'tasks' && (_jsxs("div", { style: styles.placeholder, children: [_jsx("div", { style: styles.placeholderIcon, children: _jsx(FileTextOutlined, {}) }), _jsx("h3", { style: { color: designTokens.semanticColors.text.primary }, children: "\u4EFB\u52A1\u7BA1\u7406" }), _jsx("p", { style: { color: designTokens.semanticColors.text.tertiary }, children: "\u8BF7\u901A\u8FC7 AI \u52A9\u624B\u7BA1\u7406\u4EFB\u52A1\uFF0C\u4F8B\u5982\uFF1A\"\u67E5\u770B\u6211\u7684\u4EFB\u52A1\u5217\u8868\"" })] })), currentView === 'workers' && (_jsxs("div", { style: styles.placeholder, children: [_jsx("div", { style: { ...styles.placeholderIcon, color: designTokens.colors.green[600] }, children: _jsx(TeamOutlined, {}) }), _jsx("h3", { style: { color: designTokens.semanticColors.text.primary }, children: "\u5DE5\u4EBA\u7BA1\u7406" }), _jsx("p", { style: { color: designTokens.semanticColors.text.tertiary }, children: "\u8BF7\u901A\u8FC7 AI \u52A9\u624B\u7BA1\u7406\u5DE5\u4EBA\uFF0C\u4F8B\u5982\uFF1A\"\u641C\u7D22\u6570\u636E\u6807\u6CE8\u5DE5\u4EBA\"" })] })), currentView === 'analytics' && (_jsxs("div", { style: styles.placeholder, children: [_jsx("div", { style: { ...styles.placeholderIcon, color: designTokens.colors.amber[600] }, children: _jsx(BarChartOutlined, {}) }), _jsx("h3", { style: { color: designTokens.semanticColors.text.primary }, children: "\u6570\u636E\u5206\u6790" }), _jsx("p", { style: { color: designTokens.semanticColors.text.tertiary }, children: "\u8BF7\u901A\u8FC7 AI \u52A9\u624B\u67E5\u770B\u6570\u636E\uFF0C\u4F8B\u5982\uFF1A\"\u67E5\u770B\u5E73\u53F0\u7EDF\u8BA1\u6570\u636E\"" })] })), currentView === 'settings' && (_jsxs("div", { style: styles.placeholder, children: [_jsx("div", { style: { ...styles.placeholderIcon, color: designTokens.colors.purple[600] }, children: _jsx(SettingOutlined, {}) }), _jsx("h3", { style: { color: designTokens.semanticColors.text.primary }, children: "\u8BBE\u7F6E" }), _jsx("p", { style: { color: designTokens.semanticColors.text.tertiary }, children: "\u8BBE\u7F6E\u9875\u9762\u5F00\u53D1\u4E2D..." })] }))] }) })] })] })] }));
};
const styles = {
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
