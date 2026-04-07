import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Table, Tag, Button, Space, Descriptions, Collapse, Statistic, Row, Col, Alert, Avatar, List, Rate, Card as AntCard } from 'antd';
import { UserOutlined, CheckCircleOutlined, TeamOutlined, RocketOutlined, WarningOutlined, NotificationOutlined, } from '@ant-design/icons';
import designTokens from '../styles/designTokens';
const { Panel } = Collapse;
/**
 * Generative UI 动态渲染引擎 - Bento Grid 风格
 *
 * 根据 AI 响应的 action 类型动态生成最适合的 UI 组件
 */
export const GenerativeUI = ({ message, onActionSelect }) => {
    const { action, data } = message;
    if (!action || !data) {
        return null;
    }
    switch (action) {
        case 'search_tasks':
            return _jsx(TaskList, { data: data, onActionSelect: onActionSelect });
        case 'search_workers':
            return _jsx(WorkerList, { data: data, onActionSelect: onActionSelect });
        case 'post_task':
            return _jsx(TaskCreated, { data: data, onActionSelect: onActionSelect });
        case 'match_workers':
            return _jsx(MatchResults, { data: data, onActionSelect: onActionSelect });
        case 'get_task_status':
            return _jsx(TaskStatus, { data: data, onActionSelect: onActionSelect });
        case 'get_stats':
            return _jsx(DashboardStats, { data: data, onActionSelect: onActionSelect });
        case 'verify_delivery':
            return _jsx(VerificationResult, { data: data, onActionSelect: onActionSelect });
        case 'notification':
            return _jsx(NotificationPanel, { data: data, onActionSelect: onActionSelect });
        case 'team_match':
            return _jsx(TeamComposition, { data: data, onActionSelect: onActionSelect });
        default:
            return _jsx(GenericData, { data: data });
    }
};
const TaskList = ({ data, onActionSelect }) => {
    const tasks = data.tasks || [];
    const columns = [
        {
            title: '任务名称',
            dataIndex: 'title',
            key: 'title',
            render: (text, record) => (_jsxs(Space, { children: [_jsx("span", { style: { fontWeight: 500 }, children: text }), record.priority === 'urgent' && _jsx(Tag, { color: "red", style: { borderRadius: designTokens.radii.sm }, children: "\u7D27\u6025" }), record.priority === 'high' && _jsx(Tag, { color: "orange", style: { borderRadius: designTokens.radii.sm }, children: "\u9AD8\u4F18\u5148\u7EA7" })] })),
        },
        {
            title: '报酬',
            dataIndex: 'reward_amount',
            key: 'reward_amount',
            render: (amount) => (_jsxs("span", { style: { color: designTokens.colors.green[600], fontWeight: 600 }, children: ["\u00A5", amount] })),
        },
        {
            title: '交互类型',
            dataIndex: 'interaction_type',
            key: 'interaction_type',
            render: (type) => {
                const typeMap = {
                    physical: { text: '线下', color: 'blue' },
                    digital: { text: '线上', color: 'green' },
                    hybrid: { text: '混合', color: 'purple' },
                };
                const config = typeMap[type] || { text: type, color: 'default' };
                return _jsx(Tag, { color: config.color, style: { borderRadius: designTokens.radii.sm }, children: config.text });
            },
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                const statusMap = {
                    published: { text: '已发布', color: 'blue' },
                    in_progress: { text: '进行中', color: 'processing' },
                    completed: { text: '已完成', color: 'success' },
                    cancelled: { text: '已取消', color: 'default' },
                };
                const config = statusMap[status] || { text: status, color: 'default' };
                return _jsx(Tag, { color: config.color, style: { borderRadius: designTokens.radii.sm }, children: config.text });
            },
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (_jsxs(Space, { size: "small", children: [_jsx(Button, { type: "link", size: "small", onClick: () => onActionSelect?.('view_task', record), style: { color: designTokens.colors.blue[600] }, children: "\u67E5\u770B" }), _jsx(Button, { type: "link", size: "small", onClick: () => onActionSelect?.('match_worker', record), style: { color: designTokens.colors.blue[600] }, children: "\u5339\u914D" })] })),
        },
    ];
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsx(AntCard, { size: "small", title: _jsxs("span", { style: { fontWeight: 600 }, children: ["\u627E\u5230 ", data.total || tasks.length, " \u4E2A\u4EFB\u52A1"] }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: _jsx(Table, { dataSource: tasks, columns: columns, rowKey: "id", pagination: { pageSize: 5, size: 'small' }, size: "small", scroll: { x: 800 }, showHeader: true }) }) }));
};
const WorkerList = ({ data, onActionSelect }) => {
    const workers = data.workers || [];
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsx(AntCard, { size: "small", title: _jsxs("span", { style: { fontWeight: 600 }, children: ["\u627E\u5230 ", data.total || workers.length, " \u4E2A\u5DE5\u4EBA"] }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: _jsx(List, { dataSource: workers, renderItem: (worker) => (_jsx(List.Item, { actions: [
                        _jsx(Button, { type: "link", size: "small", onClick: () => onActionSelect?.('view_worker', worker), style: { color: designTokens.colors.blue[600] }, children: "\u67E5\u770B" }, "view"),
                        _jsx(Button, { type: "primary", size: "small", onClick: () => onActionSelect?.('hire_worker', worker), style: {
                                borderRadius: designTokens.radii.md,
                                background: designTokens.colors.blue[600],
                            }, children: "\u96C7\u4F63" }, "hire"),
                    ], style: {
                        padding: `${designTokens.spacing.md} 0`,
                        borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
                    }, children: _jsx(List.Item.Meta, { avatar: _jsx(Avatar, { style: {
                                backgroundColor: designTokens.colors.blue[500],
                                boxShadow: designTokens.shadows.card,
                            }, icon: _jsx(UserOutlined, {}) }), title: _jsxs(Space, { children: [_jsx("span", { style: { fontWeight: 600 }, children: worker.name }), _jsxs(Tag, { color: "gold", style: { borderRadius: designTokens.radii.sm }, children: ["Lv.", worker.level] })] }), description: _jsxs(Space, { direction: "vertical", size: 0, children: [_jsxs(Space, { children: [_jsx(Rate, { disabled: true, defaultValue: worker.rating, allowHalf: true }), _jsxs("span", { style: { color: designTokens.semanticColors.text.secondary }, children: [worker.rating, "\u5206"] })] }), _jsxs(Space, { size: "small", children: [_jsxs(Tag, { style: { borderRadius: designTokens.radii.sm }, children: [worker.completed_tasks, "\u5355\u5B8C\u6210"] }), _jsxs(Tag, { style: { borderRadius: designTokens.radii.sm }, children: [(worker.success_rate * 100).toFixed(0), "%\u6210\u529F\u7387"] })] }), worker.skills && (_jsx(Space, { size: "small", wrap: true, children: Object.keys(worker.skills).slice(0, 5).map((skill) => (_jsx(Tag, { color: "blue", style: { borderRadius: designTokens.radii.sm }, children: skill }, skill))) }))] }) }) })) }) }) }));
};
const TaskCreated = ({ data, onActionSelect }) => {
    const task = data.task || data;
    return (_jsxs("div", { style: { marginTop: 12 }, children: [_jsx(Alert, { message: "\u4EFB\u52A1\u53D1\u5E03\u6210\u529F\uFF01", description: _jsxs(Descriptions, { column: 1, size: "small", children: [_jsx(Descriptions.Item, { label: "\u4EFB\u52A1 ID", children: task.id }), _jsx(Descriptions.Item, { label: "\u4EFB\u52A1\u540D\u79F0", children: task.title }), _jsx(Descriptions.Item, { label: "\u62A5\u916C", children: _jsxs("span", { style: { color: designTokens.colors.green[600], fontWeight: 600 }, children: ["\u00A5", task.reward_amount] }) }), _jsx(Descriptions.Item, { label: "\u72B6\u6001", children: _jsx(Tag, { color: "blue", style: { borderRadius: designTokens.radii.sm }, children: "\u5DF2\u53D1\u5E03" }) })] }), type: "success", showIcon: true, icon: _jsx(CheckCircleOutlined, {}), style: {
                    borderRadius: designTokens.radii.lg,
                    border: `1px solid ${designTokens.colors.green[200]}`,
                } }), _jsxs(Space, { style: { marginTop: 12 }, children: [_jsx(Button, { type: "primary", onClick: () => onActionSelect?.('match_workers', { task_id: task.id }), style: {
                            borderRadius: designTokens.radii.md,
                            background: designTokens.colors.blue[600],
                        }, children: "\u5339\u914D\u5DE5\u4EBA" }), _jsx(Button, { onClick: () => onActionSelect?.('view_task', { id: task.id }), style: {
                            borderRadius: designTokens.radii.md,
                            border: `1px solid ${designTokens.semanticColors.border.default}`,
                        }, children: "\u67E5\u770B\u4EFB\u52A1" })] })] }));
};
const MatchResults = ({ data, onActionSelect }) => {
    const matches = data.matches || [];
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsxs(AntCard, { size: "small", title: _jsxs(Space, { children: [_jsx("span", { style: { fontWeight: 600 }, children: "\u5339\u914D\u7ED3\u679C" }), _jsxs(Tag, { color: "blue", style: { borderRadius: designTokens.radii.sm }, children: ["\u5171", matches.length, "\u4E2A\u5339\u914D"] })] }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: [_jsx(Space, { direction: "vertical", style: { width: '100%' }, size: "small", children: matches.map((match, index) => (_jsx("div", { style: {
                            padding: designTokens.spacing.md,
                            borderRadius: designTokens.radii.lg,
                            border: `1px solid ${designTokens.semanticColors.border.subtle}`,
                            backgroundColor: match.confidence >= 0.8 ? designTokens.colors.green[50] : '#ffffff',
                            transition: designTokens.transitions.all,
                        }, onMouseEnter: (e) => {
                            e.currentTarget.style.boxShadow = designTokens.shadows.cardHover;
                        }, onMouseLeave: (e) => {
                            e.currentTarget.style.boxShadow = 'none';
                        }, children: _jsxs(Space, { style: { width: '100%', justifyContent: 'space-between' }, children: [_jsxs(Space, { children: [_jsx(Avatar, { style: {
                                                backgroundColor: getConfidenceColor(match.confidence),
                                                boxShadow: designTokens.shadows.card,
                                            }, children: index + 1 }), _jsxs("div", { children: [_jsx("div", { style: { fontWeight: 600 }, children: match.worker_name }), _jsxs(Space, { size: "small", children: [_jsxs(Tag, { color: getConfidenceColor(match.confidence), style: { borderRadius: designTokens.radii.sm }, children: ["\u5339\u914D\u5EA6 ", Math.round(match.confidence * 100), "%"] }), _jsxs(Tag, { style: { borderRadius: designTokens.radii.sm }, children: [match.rating, "\u5206"] })] })] })] }), _jsx(Button, { type: match.confidence >= 0.8 ? 'primary' : 'default', size: "small", onClick: () => onActionSelect?.('assign_worker', {
                                        task_id: data.task_id,
                                        worker_id: match.worker_id,
                                    }), style: {
                                        borderRadius: designTokens.radii.md,
                                    }, children: match.confidence >= 0.8 ? '自动分配' : '分配' })] }) }, match.worker_id || index))) }), data.auto_assigned && (_jsx(Alert, { message: "\u5DF2\u81EA\u52A8\u5206\u914D\u7ED9\u6700\u4F73\u5339\u914D\u5DE5\u4EBA", type: "success", showIcon: true, icon: _jsx(CheckCircleOutlined, {}), style: {
                        marginTop: 8,
                        borderRadius: designTokens.radii.lg,
                    } }))] }) }));
};
const TaskStatus = ({ data, onActionSelect }) => {
    const task = data.task || {};
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsxs(AntCard, { size: "small", title: _jsx("span", { style: { fontWeight: 600 }, children: "\u4EFB\u52A1\u72B6\u6001" }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: [_jsxs(Descriptions, { column: 1, size: "small", children: [_jsx(Descriptions.Item, { label: "\u4EFB\u52A1 ID", children: task.id }), _jsx(Descriptions.Item, { label: "\u4EFB\u52A1\u540D\u79F0", children: task.title }), _jsx(Descriptions.Item, { label: "\u72B6\u6001", children: _jsx(StatusTag, { status: task.status }) }), _jsx(Descriptions.Item, { label: "\u5F53\u524D\u5DE5\u4EBA", children: task.worker_id || '暂无' }), _jsxs(Descriptions.Item, { label: "\u62A5\u916C", children: ["\u00A5", task.reward_amount] }), _jsx(Descriptions.Item, { label: "\u521B\u5EFA\u65F6\u95F4", children: formatDate(task.created_at) })] }), _jsxs(Space, { style: { marginTop: 12 }, children: [_jsx(Button, { onClick: () => onActionSelect?.('view_task', { id: task.id }), style: {
                                borderRadius: designTokens.radii.md,
                                border: `1px solid ${designTokens.semanticColors.border.default}`,
                            }, children: "\u67E5\u770B\u8BE6\u60C5" }), task.status === 'published' && (_jsx(Button, { danger: true, onClick: () => onActionSelect?.('cancel_task', { id: task.id }), style: { borderRadius: designTokens.radii.md }, children: "\u53D6\u6D88\u4EFB\u52A1" }))] })] }) }));
};
const DashboardStats = ({ data }) => {
    const taskStats = data.task_stats || {};
    const workerStats = data.worker_stats || {};
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsx(AntCard, { size: "small", title: _jsx("span", { style: { fontWeight: 600 }, children: "\u5E73\u53F0\u7EDF\u8BA1" }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: _jsxs(Row, { gutter: [16, 16], children: [_jsx(Col, { span: 6, children: _jsx("div", { style: {
                                padding: designTokens.spacing.lg,
                                borderRadius: designTokens.radii.lg,
                                backgroundColor: designTokens.colors.blue[50],
                                border: `1px solid ${designTokens.colors.blue[100]}`,
                            }, children: _jsx(Statistic, { title: "\u603B\u4EFB\u52A1\u6570", value: taskStats.total || 0, prefix: _jsx(RocketOutlined, { style: { color: designTokens.colors.blue[600] } }), valueStyle: { fontSize: 24, fontWeight: 700 } }) }) }), _jsx(Col, { span: 6, children: _jsx("div", { style: {
                                padding: designTokens.spacing.lg,
                                borderRadius: designTokens.radii.lg,
                                backgroundColor: designTokens.colors.green[50],
                                border: `1px solid ${designTokens.colors.green[100]}`,
                            }, children: _jsx(Statistic, { title: "\u603B\u5DE5\u4EBA\u6570", value: workerStats.total_workers || 0, prefix: _jsx(TeamOutlined, { style: { color: designTokens.colors.green[600] } }), valueStyle: { fontSize: 24, fontWeight: 700 } }) }) }), _jsx(Col, { span: 6, children: _jsx("div", { style: {
                                padding: designTokens.spacing.lg,
                                borderRadius: designTokens.radii.lg,
                                backgroundColor: designTokens.colors.amber[50],
                                border: `1px solid ${designTokens.colors.amber[100]}`,
                            }, children: _jsx(Statistic, { title: "\u5E73\u5747\u8BC4\u5206", value: workerStats.avg_rating || 0, precision: 1, prefix: _jsx(UserOutlined, { style: { color: designTokens.colors.amber[600] } }), valueStyle: { fontSize: 24, fontWeight: 700 } }) }) }), _jsx(Col, { span: 6, children: _jsx("div", { style: {
                                padding: designTokens.spacing.lg,
                                borderRadius: designTokens.radii.lg,
                                backgroundColor: designTokens.colors.purple[50],
                                border: `1px solid ${designTokens.colors.purple[100]}`,
                            }, children: _jsx(Statistic, { title: "\u5B8C\u6210\u7387", value: taskStats.completion_rate || 0, precision: 1, suffix: "%", prefix: _jsx(CheckCircleOutlined, { style: { color: designTokens.colors.purple[600] } }), valueStyle: { fontSize: 24, fontWeight: 700 } }) }) })] }) }) }));
};
const VerificationResult = ({ data, onActionSelect }) => {
    const passed = data.passed || data.confidence >= 0.9;
    const confidence = data.confidence || 0;
    return (_jsxs("div", { style: { marginTop: 12 }, children: [_jsx(Alert, { message: passed ? '验证通过' : '验证未通过', description: _jsxs(Space, { direction: "vertical", size: 8, style: { width: '100%' }, children: [_jsxs("div", { children: ["\u7F6E\u4FE1\u5EA6\uFF1A", _jsxs("span", { style: { fontWeight: 600 }, children: [Math.round(confidence * 100), "%"] })] }), data.details && (_jsx(Collapse, { size: "small", ghost: true, children: _jsx(Panel, { header: "\u67E5\u770B\u8BE6\u60C5", children: _jsx("pre", { style: {
                                        fontSize: 12,
                                        margin: 0,
                                        padding: designTokens.spacing.md,
                                        backgroundColor: designTokens.semanticColors.background.secondary,
                                        borderRadius: designTokens.radii.md,
                                        overflow: 'auto',
                                    }, children: JSON.stringify(data.details, null, 2) }) }, "details") }))] }), type: passed ? 'success' : 'warning', showIcon: true, icon: passed ? _jsx(CheckCircleOutlined, {}) : _jsx(WarningOutlined, {}), style: {
                    borderRadius: designTokens.radii.lg,
                } }), passed && (_jsx(Space, { style: { marginTop: 12 }, children: _jsx(Button, { type: "primary", onClick: () => onActionSelect?.('approve_task', data), style: {
                        borderRadius: designTokens.radii.md,
                        background: designTokens.colors.green[600],
                    }, children: "\u6279\u51C6\u5B8C\u6210" }) }))] }));
};
const NotificationPanel = ({ data, onActionSelect }) => {
    const notifications = data.notifications || [data];
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsx(AntCard, { size: "small", title: _jsxs(Space, { children: [_jsx(NotificationOutlined, { style: { color: designTokens.colors.blue[600] } }), _jsx("span", { style: { fontWeight: 600 }, children: "\u901A\u77E5" })] }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: _jsx(List, { dataSource: notifications, renderItem: (notification) => (_jsx(List.Item, { style: { padding: `${designTokens.spacing.md} 0` }, children: _jsx(Alert, { message: notification.title || '新通知', description: notification.content || notification.message, type: notification.type || 'info', showIcon: true, style: {
                            width: '100%',
                            borderRadius: designTokens.radii.lg,
                        } }) })) }) }) }));
};
const TeamComposition = ({ data }) => {
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsxs(AntCard, { size: "small", title: _jsxs(Space, { children: [_jsx(TeamOutlined, { style: { color: designTokens.colors.blue[600] } }), _jsx("span", { style: { fontWeight: 600 }, children: "\u56E2\u961F\u7EC4\u6210" })] }), style: {
                borderRadius: designTokens.radii.lg,
                boxShadow: designTokens.shadows.card,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: [_jsxs(Descriptions, { column: 1, size: "small", children: [_jsx(Descriptions.Item, { label: "\u56E2\u961F ID", children: data.team_id }), _jsx(Descriptions.Item, { label: "\u9879\u76EE ID", children: data.project_id }), _jsx(Descriptions.Item, { label: "\u72B6\u6001", children: _jsx(StatusTag, { status: data.status }) }), _jsx(Descriptions.Item, { label: "\u603B\u4FE1\u8A89\u5206", children: data.total_reputation })] }), data.members && (_jsx(AntCard, { size: "small", title: "\u6210\u5458", style: {
                        marginTop: 8,
                        backgroundColor: designTokens.semanticColors.background.secondary,
                        borderRadius: designTokens.radii.md,
                    }, children: _jsx(List, { dataSource: Object.entries(data.members), renderItem: ([workerId, role]) => (_jsx(List.Item, { style: { padding: `${designTokens.spacing.sm} 0` }, children: _jsxs(Space, { children: [_jsx(Avatar, { icon: _jsx(UserOutlined, {}), style: { backgroundColor: designTokens.colors.blue[500] } }), _jsx("span", { children: workerId }), _jsx(Tag, { style: { borderRadius: designTokens.radii.sm }, children: role })] }) })) }) }))] }) }));
};
const GenericData = ({ data }) => {
    return (_jsx("div", { style: { marginTop: 12 }, children: _jsx("div", { style: {
                padding: designTokens.spacing.lg,
                borderRadius: designTokens.radii.lg,
                backgroundColor: designTokens.semanticColors.background.secondary,
                border: `1px solid ${designTokens.semanticColors.border.subtle}`,
            }, children: _jsx("pre", { style: {
                    fontSize: 12,
                    overflow: 'auto',
                    margin: 0,
                    fontFamily: designTokens.typography.fontFamily.mono,
                    color: designTokens.semanticColors.text.secondary,
                }, children: JSON.stringify(data, null, 2) }) }) }));
};
// ==================== 工具函数和组件 ====================
const StatusTag = ({ status }) => {
    const statusMap = {
        published: { text: '已发布', color: 'blue' },
        in_progress: { text: '进行中', color: 'processing' },
        completed: { text: '已完成', color: 'success' },
        cancelled: { text: '已取消', color: 'default' },
        pending: { text: '待处理', color: 'warning' },
        active: { text: '活跃', color: 'green' },
        inactive: { text: '未激活', color: 'default' },
    };
    const config = statusMap[status] || { text: status, color: 'default' };
    return (_jsx(Tag, { color: config.color, style: {
            borderRadius: designTokens.radii.sm,
            fontWeight: 500,
        }, children: config.text }));
};
function getConfidenceColor(confidence) {
    if (confidence >= 0.8)
        return designTokens.colors.green[600];
    if (confidence >= 0.6)
        return designTokens.colors.blue[600];
    if (confidence >= 0.4)
        return designTokens.colors.amber[600];
    return designTokens.colors.red[600];
}
function formatDate(dateString) {
    if (!dateString)
        return '-';
    try {
        return new Date(dateString).toLocaleString('zh-CN');
    }
    catch {
        return dateString;
    }
}
export default GenerativeUI;
