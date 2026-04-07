/**
 * Agent Visualization - Agent 工作流可视化组件
 * Bento Grid & Monochromatic 设计风格
 */

import React, { useEffect, useState } from 'react';
import { Card, Timeline, Tag, Progress, Collapse, Descriptions, Spin, Alert } from 'antd';
import {
  CheckCircleOutlined,
  LoadingOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  EyeOutlined,
  SolutionOutlined,
  ToolOutlined,
  LightningOutlined,
} from '@ant-design/icons';
import type { WorkflowStep } from '@/types';
import type { AgentStateItem } from '@/store';
import { useAgentStore } from '@/store';
import { agentApi } from '@/services/api';
import { colors, shadows, radii, spacing, typography, transitions, bentoGrid } from '@/styles/design-tokens';

const { Panel } = Collapse;

/**
 * Bento Grid 卡片容器
 */
interface BentoCardProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}

const BentoCard: React.FC<BentoCardProps> = ({ title, children, noPadding = false }) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="bento-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: colors.dark.bgCard,
        borderRadius: radii.lg,
        border: `1px solid ${colors.dark.border}`,
        boxShadow: isHovered ? shadows.cardHover : shadows.card,
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {title && (
        <div
          style={{
            padding: spacing[4],
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 100%)`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: parseInt(spacing[2]) }}>
            {title}
          </div>
        </div>
      )}
      <div style={{ padding: noPadding ? 0 : spacing[4], flex: 1 }}>
        {children}
      </div>
    </div>
  );
};

/**
 * Agent 状态图标
 */
const getAgentIcon = (status: string) => {
  const icons: Record<string, React.ReactNode> = {
    idle: <RobotOutlined />,
    perceiving: <EyeOutlined />,
    diagnosing: <SolutionOutlined />,
    remediating: <ToolOutlined />,
    optimizing: <LightningOutlined />,
    error: <CloseCircleOutlined />,
  };
  return icons[status] || <RobotOutlined />;
};

/**
 * Agent 状态配置
 */
const getAgentStatusConfig = (status: string) => {
  const configs: Record<string, { icon: string; color: string; text: string; gradient: string }> = {
    idle: {
      icon: '🟢',
      color: colors.semantic.success,
      text: '空闲',
      gradient: `linear-gradient(135deg, ${colors.semantic.success}20 0%, ${colors.semantic.success}10 100%)`,
    },
    perceiving: {
      icon: '👁️',
      color: colors.semantic.info,
      text: '感知中',
      gradient: `linear-gradient(135deg, ${colors.semantic.info}20 0%, ${colors.semantic.info}10 100%)`,
    },
    diagnosing: {
      icon: '🔬',
      color: colors.semantic.accent,
      text: '诊断中',
      gradient: `linear-gradient(135deg, ${colors.semantic.accent}20 0%, ${colors.semantic.accent}10 100%)`,
    },
    remediating: {
      icon: '🔧',
      color: colors.semantic.warning,
      text: '修复中',
      gradient: `linear-gradient(135deg, ${colors.semantic.warning}20 0%, ${colors.semantic.warning}10 100%)`,
    },
    optimizing: {
      icon: '⚡',
      color: colors.semantic.success,
      text: '优化中',
      gradient: `linear-gradient(135deg, ${colors.semantic.success}20 0%, ${colors.semantic.success}10 100%)`,
    },
    error: {
      icon: '❌',
      color: colors.semantic.error,
      text: '错误',
      gradient: `linear-gradient(135deg, ${colors.semantic.error}20 0%, ${colors.semantic.error}10 100%)`,
    },
  };
  return configs[status] || configs.idle;
};

/**
 * Agent 状态卡片 - Bento Grid 风格
 */
const AgentCard: React.FC<{ agent: AgentStateItem }> = ({ agent }) => {
  const config = getAgentStatusConfig(agent.status);

  return (
    <div
      style={{
        background: colors.dark.bgCard,
        borderRadius: radii.lg,
        border: `1px solid ${colors.dark.border}`,
        boxShadow: shadows.card,
        padding: spacing[5],
        minWidth: 220,
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        cursor: 'default',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = shadows.cardHover;
        e.currentTarget.style.borderColor = config.color;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = shadows.card;
        e.currentTarget.style.borderColor = colors.dark.border;
      }}
    >
      {/* 背景渐变效果 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: config.gradient,
        }}
      />

      {/* Agent 图标 */}
      <div
        style={{
          width: 64,
          height: 64,
          margin: '0 auto',
          borderRadius: radii.xl,
          background: config.gradient,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
          marginBottom: spacing[3],
          position: 'relative',
        }}
      >
        {config.icon}
        {/* 状态光晕 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            boxShadow: `0 0 20px ${config.color}40`,
            animation: 'pulse 2s ease-in-out infinite',
          }}
        />
      </div>

      {/* Agent 名称 */}
      <div style={{
        textAlign: 'center',
        fontWeight: 600,
        color: colors.neutral[100],
        fontSize: typography.fontSize.base,
        marginBottom: spacing[2],
      }}>
        {agent.name}
      </div>

      {/* 状态标签 */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: spacing[3],
      }}>
        <Tag
          color={config.color}
          style={{
            borderRadius: radii.full,
            padding: `${spacing[1]} ${spacing[3]}`,
            fontSize: typography.fontSize.xs,
            fontWeight: 500,
            border: `1px solid ${config.color}`,
            background: `${config.color}15`,
          }}
        >
          {config.text}
        </Tag>
      </div>

      {/* 当前任务 */}
      {agent.current_task && (
        <div style={{
          background: colors.dark.bgCardHover,
          borderRadius: radii.md,
          padding: spacing[2],
          marginBottom: spacing[3],
        }}>
          <div style={{
            fontSize: typography.fontSize.xs,
            color: colors.neutral[500],
            marginBottom: spacing[1],
          }}>
            当前任务
          </div>
          <div style={{
            fontSize: typography.fontSize.sm,
            color: colors.neutral[200],
            fontWeight: 500,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {agent.current_task}
          </div>
        </div>
      )}

      {/* 进度条 */}
      {agent.progress !== undefined && (
        <div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: spacing[1],
          }}>
            <span style={{ fontSize: typography.fontSize.xs, color: colors.neutral[400] }}>进度</span>
            <span style={{ fontSize: typography.fontSize.xs, color: colors.neutral[200], fontWeight: 600 }}>
              {agent.progress}%
            </span>
          </div>
          <Progress
            percent={agent.progress}
            strokeColor={config.color}
            trailColor={colors.dark.border}
            strokeWidth={6}
            showInfo={false}
            style={{ borderRadius: radii.full }}
          />
        </div>
      )}
    </div>
  );
};

/**
 * Agent 列表 - Bento Grid 布局
 */
const AgentList: React.FC = () => {
  const { agents } = useAgentStore();

  if (agents.length === 0) {
    return (
      <BentoCard>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: spacing[12],
        }}>
          <div style={{
            width: 80,
            height: 80,
            borderRadius: radii.xl,
            background: `linear-gradient(135deg, ${colors.primary[800]} 0%, ${colors.primary[900]} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: spacing[4],
          }}>
            <RobotOutlined style={{ color: colors.neutral[400], fontSize: 36 }} />
          </div>
          <div style={{
            color: colors.neutral[300],
            fontSize: typography.fontSize.lg,
            fontWeight: 500,
            marginBottom: spacing[2],
          }}>
            暂无 Agent 数据
          </div>
          <div style={{
            color: colors.neutral[500],
            fontSize: typography.fontSize.sm,
          }}>
            Agent 状态将在执行任务时自动更新
          </div>
        </div>
      </BentoCard>
    );
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: bentoGrid.gap.lg,
    }}>
      {agents.map((agent, index) => (
        <AgentCard key={index} agent={agent} />
      ))}
    </div>
  );
};

/**
 * 工作流步骤展示 - Bento 风格
 */
const WorkflowSteps: React.FC<{ steps: WorkflowStep[] }> = ({ steps }) => {
  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: colors.semantic.success }} />;
      case 'running':
        return <LoadingOutlined style={{ color: colors.semantic.info }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: colors.semantic.error }} />;
      default:
        return <div style={{
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: colors.neutral[600],
        }} />;
    }
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed':
        return colors.semantic.success;
      case 'running':
        return colors.semantic.info;
      case 'failed':
        return colors.semantic.error;
      default:
        return colors.neutral[600];
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
      {steps.map((step, index) => (
        <div
          key={index}
          style={{
            display: 'flex',
            gap: spacing[3],
            padding: spacing[3],
            background: colors.dark.bgCardHover,
            borderRadius: radii.md,
            border: `1px solid ${colors.dark.border}`,
            transition: `all ${transitions.durations.fast}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = getStepColor(step.status);
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = colors.dark.border;
          }}
        >
          {/* 状态图标 */}
          <div style={{
            width: 32,
            height: 32,
            borderRadius: radii.md,
            background: `${getStepColor(step.status)}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            {getStepIcon(step.status)}
          </div>

          {/* 内容区 */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: spacing[2],
              marginBottom: spacing[1],
            }}>
              <span style={{
                fontWeight: 500,
                color: colors.neutral[100],
                fontSize: typography.fontSize.sm,
              }}>
                {step.name}
              </span>
              <Tag
                color={getStepColor(step.status)}
                style={{
                  borderRadius: radii.sm,
                  fontSize: typography.fontSize.xs,
                  padding: `0 ${spacing[1]}`,
                  background: `${getStepColor(step.status)}15`,
                  border: `1px solid ${getStepColor(step.status)}`,
                }}
              >
                {step.status}
              </Tag>
            </div>

            {/* 时间信息 */}
            <div style={{
              fontSize: typography.fontSize.xs,
              color: colors.neutral[500],
            }}>
              {step.started_at && (
                <span>开始：{new Date(step.started_at).toLocaleTimeString()}</span>
              )}
              {step.started_at && step.completed_at && ' | '}
              {step.completed_at && (
                <span>完成：{new Date(step.completed_at).toLocaleTimeString()}</span>
              )}
            </div>

            {/* 错误信息 */}
            {step.error && (
              <Alert
                type="error"
                message={step.error}
                style={{
                  marginTop: spacing[2],
                  background: `${colors.semantic.error}10`,
                  border: `1px solid ${colors.semantic.error}30`,
                  color: colors.semantic.error,
                  fontSize: typography.fontSize.xs,
                  padding: `${spacing[2]} ${spacing[3]}`,
                }}
                showIcon={false}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * 工作流执行列表 - Bento 风格折叠面板
 */
const WorkflowList: React.FC = () => {
  const { workflows } = useAgentStore();

  if (workflows.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
      {workflows.map((workflow, index) => {
        const statusColor = workflow.status === 'completed'
          ? colors.semantic.success
          : workflow.status === 'failed'
          ? colors.semantic.error
          : colors.semantic.info;

        return (
          <div
            key={index}
            style={{
              background: colors.dark.bgCard,
              borderRadius: radii.lg,
              border: `1px solid ${colors.dark.border}`,
              boxShadow: shadows.card,
              overflow: 'hidden',
            }}
          >
            {/* 工作流头部 */}
            <div
              style={{
                padding: spacing[4],
                borderBottom: `1px solid ${colors.dark.border}`,
                background: `linear-gradient(135deg, ${statusColor}10 0%, transparent 100%)`,
                display: 'flex',
                alignItems: 'center',
                gap: spacing[3],
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: radii.md,
                  background: `${statusColor}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: statusColor,
                }}
              >
                <ThunderboltOutlined />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{
                  color: colors.neutral[100],
                  fontWeight: 600,
                  fontSize: typography.fontSize.base,
                }}>
                  {workflow.name}
                </div>
                <div style={{
                  color: colors.neutral[500],
                  fontSize: typography.fontSize.xs,
                  marginTop: spacing[1],
                }}>
                  ID: {workflow.id}
                </div>
              </div>
              <Tag
                color={statusColor}
                style={{
                  borderRadius: radii.full,
                  padding: `${spacing[1]} ${spacing[3]}`,
                  fontSize: typography.fontSize.xs,
                  fontWeight: 500,
                  border: `1px solid ${statusColor}`,
                  background: `${statusColor}15`,
                }}
              >
                {workflow.status === 'completed' ? '完成' : workflow.status === 'failed' ? '失败' : '运行中'}
              </Tag>
            </div>

            {/* 工作流详情 */}
            <div style={{ padding: spacing[4] }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label={<span style={{ color: colors.neutral[400 ], fontSize: typography.fontSize.xs }}>状态</span>}>
                  <Tag
                    color={statusColor}
                    style={{
                      borderRadius: radii.sm,
                      fontSize: typography.fontSize.xs,
                      background: `${statusColor}15`,
                      border: `1px solid ${statusColor}`,
                    }}
                  >
                    {workflow.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label={<span style={{ color: colors.neutral[400], fontSize: typography.fontSize.xs }}>开始时间</span>}>
                  <span style={{ color: colors.neutral[300], fontSize: typography.fontSize.sm }}>
                    {new Date(workflow.started_at).toLocaleString()}
                  </span>
                </Descriptions.Item>
              </Descriptions>

              <div style={{ marginTop: spacing[4] }}>
                <div style={{
                  color: colors.neutral[400],
                  fontSize: typography.fontSize.sm,
                  fontWeight: 500,
                  marginBottom: spacing[3],
                }}>
                  执行步骤
                </div>
                <WorkflowSteps steps={workflow.steps} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * 主 Agent 可视化面板
 */
const AgentVisualization: React.FC = () => {
  const { setAgents, workflows, setWorkflows } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(false);

  const loadAgentData = async () => {
    setLocalLoading(true);
    try {
      const agentData = await agentApi.getState();
      setAgents(agentData.state as AgentStateItem[]);

      const workflowData = await agentApi.getWorkflowStatus();
      setWorkflows(workflowData.workflows);
    } catch (error) {
      console.error('Failed to load agent data:', error);
    } finally {
      setLocalLoading(false);
    }
  };

  useEffect(() => {
    loadAgentData();
    const interval = setInterval(loadAgentData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: spacing[6] }}>
        <h1 style={{
          fontSize: typography.fontSize['4xl'],
          fontWeight: 700,
          color: colors.neutral[100],
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          gap: spacing[3],
        }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: radii.lg,
              background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: shadows.glow,
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          Agent 可视化
        </h1>
        <p style={{
          color: colors.neutral[500],
          marginTop: spacing[2],
          fontSize: typography.fontSize.base,
        }}>
          实时监控 AI Agent 工作状态和执行流程
        </p>
      </div>

      {/* Agent 状态卡片 */}
      <BentoCard
        title={
          <>
            <RobotOutlined style={{ color: colors.semantic.info }} />
            <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>Agent 状态</span>
          </>
        }
      >
        {localLoading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: spacing[12],
          }}>
            <Spin
              indicator={
                <div
                  style={{
                    width: 32,
                    height: 32,
                    border: `3px solid ${colors.primary[800]}`,
                    borderTop: `3px solid ${colors.primary[500]}`,
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                  }}
                />
              }
            />
          </div>
        ) : (
          <AgentList />
        )}
      </BentoCard>

      {/* 工作流执行 */}
      {workflows.length > 0 && (
        <div style={{ marginTop: spacing[6] }}>
          <BentoCard
            title={
              <>
                <LightningOutlined style={{ color: colors.semantic.accent }} />
                <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>工作流执行</span>
              </>
            }
          >
            <WorkflowList />
          </BentoCard>
        </div>
      )}
    </div>
  );
};

export default AgentVisualization;
