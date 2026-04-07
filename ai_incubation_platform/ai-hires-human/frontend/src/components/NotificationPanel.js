import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from 'react';
import { BellOutlined, CheckCircleOutlined, ExclamationCircleOutlined, InfoCircleOutlined, WarningOutlined, ThunderboltOutlined, } from '@ant-design/icons';
import { Badge, Button, Card, List, Space, Tag, Avatar } from 'antd';
import designTokens from '../styles/designTokens';
const { Meta } = Card;
/**
 * AI 主动推送通知面板 - Bento Grid 风格
 *
 * 功能：
 * - 新候选人匹配提醒
 * - 面试机会提醒
 * - 风险预警通知
 * - AI 建议推送
 */
export const NotificationPanel = ({ userId, onNotificationClick, }) => {
    const [notifications, setNotifications] = useState([]);
    const [visible, setVisible] = useState(false);
    // 模拟 AI 主动推送的通知
    useEffect(() => {
        // 实际项目中应该从 WebSocket 或轮询获取
        const mockNotifications = [
            {
                id: 'notif_1',
                type: 'ai_suggestion',
                title: 'AI 发现合适候选人',
                content: '发现一位匹配度 92% 的候选人，擅长数据标注和线下采集，评分 4.8 分',
                timestamp: new Date(),
                data: { worker_id: 'worker_123', confidence: 0.92 },
                action: {
                    label: '查看候选人',
                    handler: () => console.log('查看候选人'),
                },
            },
            {
                id: 'notif_2',
                type: 'info',
                title: '面试提醒',
                content: '您有 1 个面试安排在今天下午 3 点',
                timestamp: new Date(Date.now() - 3600000),
            },
            {
                id: 'notif_3',
                type: 'warning',
                title: '风险预警',
                content: '检测到任务 task-456 的交付物存在异常，建议进行人工复核',
                timestamp: new Date(Date.now() - 7200000),
                data: { task_id: 'task-456', risk_level: 'medium' },
                action: {
                    label: '查看详情',
                    handler: () => console.log('查看风险详情'),
                },
            },
        ];
        setNotifications(mockNotifications);
    }, []);
    const unreadCount = notifications.filter((n) => !n.read).length;
    const getNotificationIcon = (type) => {
        const icons = {
            success: _jsx(CheckCircleOutlined, { style: { color: designTokens.colors.green[600] } }),
            info: _jsx(InfoCircleOutlined, { style: { color: designTokens.colors.blue[600] } }),
            warning: _jsx(WarningOutlined, { style: { color: designTokens.colors.amber[600] } }),
            error: _jsx(ExclamationCircleOutlined, { style: { color: designTokens.colors.red[600] } }),
            ai_suggestion: _jsx(ThunderboltOutlined, { style: { color: designTokens.colors.purple[600] } }),
        };
        return icons[type] || icons.info;
    };
    const getNotificationBg = (type) => {
        const colors = {
            success: designTokens.colors.green[50],
            info: designTokens.colors.blue[50],
            warning: designTokens.colors.amber[50],
            error: designTokens.colors.red[50],
            ai_suggestion: designTokens.colors.purple[50],
        };
        return colors[type] || '#fff';
    };
    const handleNotificationClick = (notification) => {
        // 标记为已读
        setNotifications((prev) => prev.map((n) => (n.id === notification.id ? { ...n, read: true } : n)));
        onNotificationClick?.(notification);
    };
    const handleMarkAllRead = () => {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    };
    const handleClearAll = () => {
        setNotifications([]);
    };
    return (_jsxs("div", { style: styles.container, children: [_jsx(Badge, { count: unreadCount, size: "small", children: _jsx(Button, { type: "text", icon: _jsx(BellOutlined, { style: { fontSize: 18 } }), onClick: () => setVisible(!visible), style: {
                        borderRadius: designTokens.radii.md,
                        transition: designTokens.transitions.all,
                    }, onMouseEnter: (e) => {
                        e.currentTarget.style.backgroundColor = designTokens.semanticColors.background.hover;
                    }, onMouseLeave: (e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                    } }) }), visible && (_jsx(Card, { size: "small", title: _jsxs(Space, { style: { justifyContent: 'space-between', width: '100%' }, children: [_jsx("span", { style: { fontWeight: 600 }, children: "\u901A\u77E5\u4E2D\u5FC3" }), _jsxs(Space, { size: "small", children: [_jsx(Button, { type: "link", size: "small", onClick: handleMarkAllRead, style: { color: designTokens.colors.blue[600] }, children: "\u5168\u90E8\u5DF2\u8BFB" }), _jsx(Button, { type: "link", size: "small", danger: true, onClick: handleClearAll, style: { color: designTokens.colors.red[600] }, children: "\u6E05\u7A7A" })] })] }), style: {
                    ...styles.notificationCard,
                    borderRadius: designTokens.radii.lg,
                    boxShadow: designTokens.shadows.dropdown,
                    border: `1px solid ${designTokens.semanticColors.border.default}`,
                }, children: notifications.length === 0 ? (_jsxs("div", { style: styles.emptyState, children: [_jsx("div", { style: {
                                width: 64,
                                height: 64,
                                borderRadius: designTokens.radii.xxl,
                                backgroundColor: designTokens.semanticColors.background.secondary,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto',
                            }, children: _jsx(BellOutlined, { style: { fontSize: 32, color: designTokens.semanticColors.text.tertiary } }) }), _jsx("div", { style: {
                                marginTop: 16,
                                color: designTokens.semanticColors.text.tertiary,
                                fontSize: 14,
                            }, children: "\u6682\u65E0\u901A\u77E5" })] })) : (_jsx(List, { dataSource: notifications, renderItem: (notification) => (_jsxs(List.Item, { style: {
                            backgroundColor: getNotificationBg(notification.type),
                            borderRadius: designTokens.radii.lg,
                            marginBottom: 8,
                            cursor: 'pointer',
                            opacity: notification.read ? 0.7 : 1,
                            padding: designTokens.spacing.md,
                            border: `1px solid ${designTokens.semanticColors.border.subtle}`,
                            transition: designTokens.transitions.all,
                        }, onClick: () => handleNotificationClick(notification), onMouseEnter: (e) => {
                            e.currentTarget.style.boxShadow = designTokens.shadows.cardHover;
                            e.currentTarget.style.transform = 'translateY(-2px)';
                        }, onMouseLeave: (e) => {
                            e.currentTarget.style.boxShadow = 'none';
                            e.currentTarget.style.transform = 'translateY(0)';
                        }, children: [_jsx(List.Item.Meta, { avatar: _jsx(Avatar, { style: {
                                        backgroundColor: '#ffffff',
                                        boxShadow: designTokens.shadows.card,
                                    }, icon: getNotificationIcon(notification.type) }), title: _jsxs(Space, { children: [_jsx("span", { style: { fontWeight: 600 }, children: notification.title }), !notification.read && (_jsx(Badge, { dot: true, style: { fontSize: 10 } })), notification.type === 'ai_suggestion' && (_jsx(Tag, { color: "purple", style: {
                                                fontSize: 10,
                                                borderRadius: designTokens.radii.sm,
                                                fontWeight: 500,
                                            }, children: "AI \u5EFA\u8BAE" }))] }), description: _jsxs("div", { children: [_jsx("div", { style: { color: designTokens.semanticColors.text.secondary }, children: notification.content }), _jsx("div", { style: {
                                                fontSize: 11,
                                                color: designTokens.semanticColors.text.tertiary,
                                                marginTop: 4,
                                            }, children: formatTimeAgo(notification.timestamp) })] }) }), notification.action && (_jsx(Button, { type: "primary", size: "small", onClick: (e) => {
                                    e.stopPropagation();
                                    notification.action?.handler();
                                }, style: {
                                    borderRadius: designTokens.radii.md,
                                    background: designTokens.colors.blue[600],
                                }, children: notification.action.label }))] })) })) }))] }));
};
function formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1)
        return '刚刚';
    if (diffMins < 60)
        return `${diffMins}分钟前`;
    if (diffHours < 24)
        return `${diffHours}小时前`;
    if (diffDays < 7)
        return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN');
}
const styles = {
    container: {
        position: 'relative',
    },
    notificationCard: {
        position: 'absolute',
        top: 'calc(100% + 8px)',
        right: 0,
        width: 400,
        maxHeight: 500,
        overflowY: 'auto',
        zIndex: 1000,
    },
    emptyState: {
        textAlign: 'center',
        padding: `${designTokens.spacing['3xl']} 0`,
    },
};
export default NotificationPanel;
