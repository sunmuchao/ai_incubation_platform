import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Progress, Tooltip, Badge, Avatar } from 'antd';
import { LoadingOutlined, RocketOutlined, ThunderboltOutlined, } from '@ant-design/icons';
import designTokens from '../styles/designTokens';
/**
 * Agent 状态可视化组件 - Bento Grid 风格
 *
 * 显示 AI Agent 的思考和执行过程
 */
export const AgentStatus = ({ agentState, visible = true }) => {
    if (!visible || !agentState) {
        return null;
    }
    const { thinking, executing, workflow, step, totalSteps, confidence, autoExecute } = agentState;
    // 渲染置信度指示器
    const renderConfidence = () => {
        if (confidence === undefined)
            return null;
        const confidencePercent = Math.round(confidence * 100);
        let color = 'default';
        let status = 'normal';
        if (confidence >= 0.8) {
            color = 'success';
            status = 'high';
        }
        else if (confidence >= 0.6) {
            color = 'blue';
            status = 'medium';
        }
        else if (confidence >= 0.4) {
            color = 'warning';
            status = 'low';
        }
        else {
            color = 'error';
            status = 'very-low';
        }
        return (_jsxs("div", { style: styles.confidenceContainer, children: [_jsx(Tooltip, { title: `置信度：${confidencePercent}% - ${getConfidenceLabel(status)}`, children: _jsx(Badge, { count: `${confidencePercent}%`, style: {
                            backgroundColor: getStatusColor(color),
                            fontSize: '11px',
                            fontWeight: 600,
                        } }) }), autoExecute && confidence >= 0.8 && (_jsx(Tooltip, { title: "\u9AD8\u7F6E\u4FE1\u5EA6\uFF0C\u81EA\u52A8\u6267\u884C", children: _jsx(ThunderboltOutlined, { style: {
                            color: designTokens.colors.amber[600],
                            marginLeft: 8,
                            fontSize: 14,
                        } }) }))] }));
    };
    // 渲染执行进度
    const renderProgress = () => {
        if (!executing || !totalSteps)
            return null;
        const progressPercent = step && totalSteps ? Math.round((step / totalSteps) * 100) : 0;
        return (_jsxs("div", { style: styles.progressContainer, children: [_jsxs("div", { style: styles.progressLabel, children: [_jsx(RocketOutlined, { spin: true, style: { marginRight: 8, color: designTokens.colors.blue[600] } }), _jsx("span", { style: { fontWeight: 500 }, children: workflow || '正在执行' })] }), _jsx(Progress, { percent: progressPercent, size: "small", strokeColor: {
                        '0%': designTokens.colors.blue[400],
                        '100%': designTokens.colors.green[500],
                    }, showInfo: false, style: { margin: 0 } }), _jsxs("div", { style: styles.stepLabel, children: ["\u6B65\u9AA4 ", step, " / ", totalSteps] })] }));
    };
    // 渲染思考状态
    const renderThinking = () => {
        if (!thinking)
            return null;
        return (_jsxs("div", { style: styles.thinkingContainer, children: [_jsx(Avatar, { style: {
                        backgroundColor: designTokens.colors.blue[50],
                        width: 24,
                        height: 24,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }, children: _jsx(LoadingOutlined, { spin: true, style: { color: designTokens.colors.blue[600] } }) }), _jsx("span", { style: {
                        color: designTokens.colors.blue[600],
                        fontWeight: 500,
                        marginLeft: 8,
                    }, children: "AI \u6B63\u5728\u601D\u8003..." })] }));
    };
    return (_jsxs("div", { style: styles.container, children: [_jsxs("div", { style: styles.header, children: [_jsx("span", { style: styles.title, children: "Agent \u72B6\u6001" }), renderConfidence()] }), _jsxs("div", { style: styles.content, children: [renderThinking(), renderProgress(), executing && !thinking && (_jsxs("div", { style: styles.executingContainer, children: [_jsx(Avatar, { style: {
                                    backgroundColor: designTokens.colors.green[50],
                                    width: 24,
                                    height: 24,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }, children: _jsx(RocketOutlined, { spin: true, style: { color: designTokens.colors.green[600] } }) }), _jsx("span", { style: {
                                    marginLeft: 8,
                                    color: designTokens.colors.green[600],
                                    fontWeight: 500,
                                }, children: "\u6267\u884C\u4E2D..." })] }))] })] }));
};
function getConfidenceLabel(status) {
    const labels = {
        high: '高置信度',
        medium: '中等置信度',
        low: '低置信度',
        'very-low': '极低置信度',
        normal: '正常',
    };
    return labels[status] || status;
}
function getStatusColor(color) {
    const colors = {
        success: designTokens.colors.green[600],
        blue: designTokens.colors.blue[600],
        warning: designTokens.colors.amber[600],
        error: designTokens.colors.red[600],
        default: designTokens.colors.slate[400],
    };
    return colors[color] || colors.default;
}
const styles = {
    container: {
        padding: `${designTokens.spacing.md} ${designTokens.spacing.lg}`,
        backgroundColor: '#ffffff',
        borderRadius: designTokens.radii.lg,
        border: `1px solid ${designTokens.semanticColors.border.subtle}`,
        boxShadow: designTokens.shadows.card,
        transition: designTokens.transitions.all,
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: designTokens.spacing.md,
        paddingBottom: designTokens.spacing.md,
        borderBottom: `1px solid ${designTokens.semanticColors.border.subtle}`,
    },
    title: {
        fontWeight: 600,
        fontSize: 13,
        color: designTokens.semanticColors.text.primary,
    },
    content: {
        minHeight: 32,
        display: 'flex',
        flexDirection: 'column',
        gap: designTokens.spacing.sm,
    },
    thinkingContainer: {
        display: 'flex',
        alignItems: 'center',
        padding: `${designTokens.spacing.xs} 0`,
    },
    executingContainer: {
        display: 'flex',
        alignItems: 'center',
        padding: `${designTokens.spacing.xs} 0`,
    },
    progressContainer: {
        padding: `${designTokens.spacing.xs} 0`,
    },
    progressLabel: {
        marginBottom: 6,
        fontSize: 13,
        display: 'flex',
        alignItems: 'center',
    },
    stepLabel: {
        marginTop: 6,
        fontSize: 11,
        color: designTokens.semanticColors.text.tertiary,
        textAlign: 'right',
    },
    confidenceContainer: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
    },
};
export default AgentStatus;
