import React from 'react';
import { Progress, Tag, Tooltip, Badge, Avatar } from 'antd';
import {
  LoadingOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { AgentState } from '../services/chatService';
import designTokens from '../styles/designTokens';

interface AgentStatusProps {
  agentState?: AgentState;
  visible?: boolean;
}

/**
 * Agent 状态可视化组件 - Bento Grid 风格
 *
 * 显示 AI Agent 的思考和执行过程
 */
export const AgentStatus: React.FC<AgentStatusProps> = ({ agentState, visible = true }) => {
  if (!visible || !agentState) {
    return null;
  }

  const { thinking, executing, workflow, step, totalSteps, confidence, autoExecute } = agentState;

  // 渲染置信度指示器
  const renderConfidence = () => {
    if (confidence === undefined) return null;

    const confidencePercent = Math.round(confidence * 100);
    let color = 'default';
    let status = 'normal';

    if (confidence >= 0.8) {
      color = 'success';
      status = 'high';
    } else if (confidence >= 0.6) {
      color = 'blue';
      status = 'medium';
    } else if (confidence >= 0.4) {
      color = 'warning';
      status = 'low';
    } else {
      color = 'error';
      status = 'very-low';
    }

    return (
      <div style={styles.confidenceContainer}>
        <Tooltip title={`置信度：${confidencePercent}% - ${getConfidenceLabel(status)}`}>
          <Badge
            count={`${confidencePercent}%`}
            style={{
              backgroundColor: getStatusColor(color),
              fontSize: '11px',
              fontWeight: 600,
            }}
          />
        </Tooltip>
        {autoExecute && confidence >= 0.8 && (
          <Tooltip title="高置信度，自动执行">
            <ThunderboltOutlined
              style={{
                color: designTokens.colors.amber[600],
                marginLeft: 8,
                fontSize: 14,
              }}
            />
          </Tooltip>
        )}
      </div>
    );
  };

  // 渲染执行进度
  const renderProgress = () => {
    if (!executing || !totalSteps) return null;

    const progressPercent = step && totalSteps ? Math.round((step / totalSteps) * 100) : 0;

    return (
      <div style={styles.progressContainer}>
        <div style={styles.progressLabel}>
          <RocketOutlined spin style={{ marginRight: 8, color: designTokens.colors.blue[600] }} />
          <span style={{ fontWeight: 500 }}>{workflow || '正在执行'}</span>
        </div>
        <Progress
          percent={progressPercent}
          size="small"
          strokeColor={{
            '0%': designTokens.colors.blue[400],
            '100%': designTokens.colors.green[500],
          }}
          showInfo={false}
          style={{ margin: 0 }}
        />
        <div style={styles.stepLabel}>
          步骤 {step} / {totalSteps}
        </div>
      </div>
    );
  };

  // 渲染思考状态
  const renderThinking = () => {
    if (!thinking) return null;

    return (
      <div style={styles.thinkingContainer}>
        <Avatar
          style={{
            backgroundColor: designTokens.colors.blue[50],
            width: 24,
            height: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <LoadingOutlined spin style={{ color: designTokens.colors.blue[600] }} />
        </Avatar>
        <span style={{
          color: designTokens.colors.blue[600],
          fontWeight: 500,
          marginLeft: 8,
        }}>
          AI 正在思考...
        </span>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Agent 状态</span>
        {renderConfidence()}
      </div>
      <div style={styles.content}>
        {renderThinking()}
        {renderProgress()}
        {executing && !thinking && (
          <div style={styles.executingContainer}>
            <Avatar
              style={{
                backgroundColor: designTokens.colors.green[50],
                width: 24,
                height: 24,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <RocketOutlined spin style={{ color: designTokens.colors.green[600] }} />
            </Avatar>
            <span style={{
              marginLeft: 8,
              color: designTokens.colors.green[600],
              fontWeight: 500,
            }}>
              执行中...
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

function getConfidenceLabel(status: string): string {
  const labels: Record<string, string> = {
    high: '高置信度',
    medium: '中等置信度',
    low: '低置信度',
    'very-low': '极低置信度',
    normal: '正常',
  };
  return labels[status] || status;
}

function getStatusColor(color: string): string {
  const colors: Record<string, string> = {
    success: designTokens.colors.green[600],
    blue: designTokens.colors.blue[600],
    warning: designTokens.colors.amber[600],
    error: designTokens.colors.red[600],
    default: designTokens.colors.slate[400],
  };
  return colors[color] || colors.default;
}

const styles: Record<string, React.CSSProperties> = {
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
