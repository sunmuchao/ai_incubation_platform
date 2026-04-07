/**
 * Agent 工作流可视化组件 - Bento Grid 风格重构
 * 显示 AI Agent 执行工作流的进度和状态
 */
import React from 'react';
import { Steps, Progress, Space, Typography, Tag, Timeline, Spin } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  SearchOutlined,
  LineChartOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { WorkflowStep } from '../types';

const { Title, Text } = Typography;
const { Step } = Steps;

interface AgentWorkflowProps {
  steps: WorkflowStep[];
  title?: string;
  showTimeline?: boolean;
}

/**
 * 步骤图标映射
 */
const getStepIcon = (stepName: string, status: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    '理解意图': <SearchOutlined />,
    '数据收集': <FileTextOutlined />,
    '智能分析': <LineChartOutlined />,
    '生成报告': <FileTextOutlined />,
    '评估机会': <ThunderboltOutlined />,
  };

  const icon = iconMap[stepName] || <RobotOutlined />;

  if (status === 'completed') {
    return <CheckCircleOutlined style={{ color: 'var(--color-success)' }} />;
  }
  if (status === 'failed') {
    return <CloseCircleOutlined style={{ color: 'var(--color-error)' }} />;
  }
  if (status === 'running') {
    return <SyncOutlined spin style={{ color: 'var(--color-primary-500)' }} />;
  }
  return icon;
};

/**
 * 步骤状态描述
 */
const getStatusDescription = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
  };
  return statusMap[status] || status;
};

/**
 * Agent 工作流组件 - Bento Grid 风格
 */
const AgentWorkflow: React.FC<AgentWorkflowProps> = ({
  steps,
  title,
  showTimeline = true,
}) => {
  // 计算整体进度
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const totalSteps = steps.length;
  const progressPercent = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  // 检查是否正在运行
  const isRunning = steps.some((s) => s.status === 'running');
  const hasFailed = steps.some((s) => s.status === 'failed');
  const isCompleted = !isRunning && !hasFailed && completedSteps === totalSteps;

  // Steps 组件数据转换
  const stepsData = steps.map((step) => ({
    title: step.name,
    description: step.description,
    status: step.status === 'completed' ? 'finish' : step.status === 'failed' ? 'error' : step.status === 'running' ? 'process' : 'wait',
    icon: getStepIcon(step.name, step.status),
  }));

  return (
    <div>
      {/* 标题区域 - Bento 风格 */}
      {title && (
        <div
          style={{
            marginBottom: 16,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space size={8}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 'var(--radius-lg)',
                background: 'var(--gradient-accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-glow-sm)',
              }}
            >
              <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />
            </div>
            <Title
              level={5}
              style={{
                margin: 0,
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: 'var(--font-weight-semibold)',
              }}
            >
              {title}
            </Title>
          </Space>
          <Tag
            color={hasFailed ? 'red' : isRunning ? 'purple' : 'green'}
            style={{
              borderRadius: 'var(--radius-md)',
              padding: '2px 10px',
              fontSize: 'var(--font-size-xs)',
            }}
          >
            {hasFailed ? '执行失败' : isRunning ? '进行中' : '已完成'}
          </Tag>
        </div>
      )}

      {/* 整体进度条 - Bento 风格 */}
      <div
        style={{
          marginBottom: 20,
          padding: 12,
          background: 'var(--color-bg-subtle)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--color-border-secondary)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text
            style={{
              color: 'var(--color-text-tertiary)',
              fontSize: 'var(--font-size-xs)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            工作流进度
          </Text>
          <Text
            style={{
              color: 'var(--color-primary-400)',
              fontWeight: 'var(--font-weight-semibold)',
              fontSize: 'var(--font-size-xs)',
            }}
          >
            {completedSteps}/{totalSteps} 步骤
          </Text>
        </div>
        <Progress
          percent={progressPercent}
          showInfo={false}
          strokeColor={{
            '0%': 'var(--color-primary-600)',
            '100%': 'var(--color-primary-400)',
          }}
          trailColor="var(--color-bg-container)"
          strokeWidth={6}
        />
      </div>

      {/* Steps 步骤条 - Bento 风格 */}
      <div
        style={{
          marginBottom: 20,
          display: 'flex',
          gap: 8,
          overflowX: 'auto',
          paddingBottom: 8,
        }}
      >
        {stepsData.map((step, index) => {
          const isActive = step.status === 'running' || step.status === 'pending';
          const isCompleted = step.status === 'completed';
          const isFailed = step.status === 'failed';

          return (
            <div
              key={step.title}
              className="bento-card bento-card-sm"
              style={{
                minWidth: 120,
                flex: '0 0 auto',
                background: isFailed
                  ? 'var(--color-error)10'
                  : isCompleted
                  ? 'var(--color-success)10'
                  : isActive
                  ? 'var(--color-primary-500)15'
                  : 'var(--color-bg-subtle)',
                border: `1px solid ${
                  isFailed
                    ? 'var(--color-error)30'
                    : isCompleted
                    ? 'var(--color-success)30'
                    : isActive
                    ? 'var(--color-primary-500)30'
                    : 'var(--color-border-secondary)'
                }`,
              }}
            >
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: 'var(--radius-md)',
                    background: isFailed
                      ? 'var(--color-error)20'
                      : isCompleted
                      ? 'var(--color-success)20'
                      : isActive
                      ? 'var(--color-primary-500)20'
                      : 'var(--color-bg-container)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {getStepIcon(step.title, step.status === 'process' ? 'running' : step.status)}
                </div>
                <Text
                  strong
                  style={{
                    color:
                      isCompleted || step.status === 'process'
                        ? 'var(--color-text-primary)'
                        : 'var(--color-text-tertiary)',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  {step.title}
                </Text>
              </Space>
            </div>
          );
        })}
      </div>

      {/* 时间线详情 - Bento 风格 */}
      {showTimeline && (
        <Timeline
          mode="left"
          style={{ marginTop: 16 }}
          items={steps.map((step, index) => {
            const isCurrentStep = step.status === 'running';
            const isCompleted = step.status === 'completed';
            const isFailed = step.status === 'failed';

            return {
              key: step.id,
              color: isFailed
                ? 'var(--color-error)'
                : isCompleted
                ? 'var(--color-success)'
                : isCurrentStep
                ? 'var(--color-primary-500)'
                : 'var(--color-neutral-500)',
              children: (
                <div
                  className="bento-card bento-card-sm"
                  style={{
                    background: isCurrentStep
                      ? 'var(--color-primary-500)10'
                      : isCompleted
                      ? 'var(--color-success)10'
                      : 'var(--color-bg-subtle)',
                    border: `1px solid ${
                      isFailed
                        ? 'var(--color-error)30'
                        : isCompleted
                        ? 'var(--color-success)30'
                        : isCurrentStep
                        ? 'var(--color-primary-500)30'
                        : 'var(--color-border-secondary)'
                    }`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Space size={8}>
                      <Text
                        strong
                        style={{
                          color: isFailed
                            ? 'var(--color-error)'
                            : isCompleted
                            ? 'var(--color-success)'
                            : isCurrentStep
                            ? 'var(--color-primary-400)'
                            : 'var(--color-text-secondary)',
                          fontSize: 'var(--font-size-sm)',
                        }}
                      >
                        {step.name}
                      </Text>
                      {isCurrentStep && (
                        <Spin size="small" style={{ color: 'var(--color-primary-500)' }} />
                      )}
                    </Space>
                    <Tag
                      color={
                        isFailed
                          ? 'red'
                          : isCompleted
                          ? 'green'
                          : isCurrentStep
                          ? 'purple'
                          : 'default'
                      }
                      style={{
                        borderRadius: 'var(--radius-md)',
                        fontSize: 'var(--font-size-xs)',
                        padding: '1px 8px',
                      }}
                    >
                      {getStatusDescription(step.status)}
                    </Tag>
                  </div>
                  {step.result && (
                    <Text
                      style={{
                        color: 'var(--color-text-tertiary)',
                        fontSize: 'var(--font-size-xs)',
                        display: 'block',
                      }}
                    >
                      结果：{JSON.stringify(step.result)}
                    </Text>
                  )}
                  {step.startTime && step.endTime && (
                    <Space size={4}>
                      <ClockCircleOutlined
                        style={{
                          color: 'var(--color-text-tertiary)',
                          fontSize: 10,
                        }}
                      />
                      <Text
                        style={{
                          color: 'var(--color-text-tertiary)',
                          fontSize: 'var(--font-size-xs)',
                        }}
                      >
                        耗时：{new Date(step.endTime).getTime() - new Date(step.startTime).getTime()}ms
                      </Text>
                    </Space>
                  )}
                </div>
              ),
            };
          })}
        />
      )}
    </div>
  );
};

export default AgentWorkflow;
