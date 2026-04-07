/**
 * Agent 状态面板组件
 * 显示 AI 智能体的工作状态
 */
import React from 'react';
import { Card, Typography, Space, Progress, Tag, Divider, Button, Tooltip } from 'antd';
import {
  RobotOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BranchesOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import './AgentStatusPanel.less';

const { Title, Text, Paragraph } = Typography;

interface AgentStatusPanelProps {
  status: 'idle' | 'thinking' | 'executing' | 'completed';
  onToggle?: () => void;
  activeTools?: string[];
  workflowSteps?: Array<{ name: string; status: string }>;
  confidence?: number;
}

const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({
  status,
  onToggle,
  activeTools = [],
  workflowSteps = [],
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'thinking':
        return {
          icon: <LoadingOutlined spin />,
          label: '思考中',
          color: '#1890ff',
          description: 'AI 正在理解您的需求',
        };
      case 'executing':
        return {
          icon: <ThunderboltOutlined spin />,
          label: '执行中',
          color: '#722ed1',
          description: 'AI 正在调用工具执行操作',
        };
      case 'completed':
        return {
          icon: <CheckCircleOutlined />,
          label: '已完成',
          color: '#52c41a',
          description: '操作已成功完成',
        };
      default:
        return {
          icon: <RobotOutlined />,
          label: '就绪',
          color: '#8c8c8c',
          description: 'AI 助手已就绪，等待指令',
        };
    }
  };

  const statusConfig = getStatusConfig();

  // 模拟的工具使用数据
  const toolsUsage = [
    { name: 'analyze_profile', count: 12, icon: <ToolOutlined /> },
    { name: 'match_opportunities', count: 8, icon: <ThunderboltOutlined /> },
    { name: 'plan_career', count: 5, icon: <BranchesOutlined /> },
  ];

  return (
    <div className="agent-status-panel">
      <div className="panel-header">
        <Space>
          <Button type="text" icon={status === 'idle' ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={onToggle} />
          <Title level={5} style={{ margin: 0, color: '#fff' }}>
            AI Agent
          </Title>
        </Space>
      </div>

      <div className="status-section">
        <div className="status-indicator" style={{ borderColor: statusConfig.color }}>
          <div className="status-icon" style={{ color: statusConfig.color }}>
            {statusConfig.icon}
          </div>
        </div>
        <div className="status-info">
          <Text strong className="status-label" style={{ color: statusConfig.color }}>
            {statusConfig.label}
          </Text>
          <Text className="status-description">{statusConfig.description}</Text>
        </div>
      </div>

      <Divider style={{ borderColor: 'rgba(255,255,255,0.2)', margin: '12px 0' }} />

      {/* 工作流进度 */}
      {status !== 'idle' && (
        <div className="workflow-section">
          <Text className="section-title">工作流进度</Text>
          <div className="workflow-steps">
            <div className="workflow-step completed">
              <CheckCircleOutlined />
              <Text>理解意图</Text>
            </div>
            {status === 'thinking' || status === 'executing' || status === 'completed' ? (
              <div className={`workflow-step ${status === 'thinking' ? 'active' : 'completed'}`}>
                {status === 'thinking' ? <LoadingOutlined spin /> : <CheckCircleOutlined />}
                <Text>分析上下文</Text>
              </div>
            ) : null}
            {status === 'executing' || status === 'completed' ? (
              <div className={`workflow-step ${status === 'executing' ? 'active' : 'completed'}`}>
                {status === 'executing' ? <ThunderboltOutlined spin /> : <CheckCircleOutlined />}
                <Text>执行操作</Text>
              </div>
            ) : null}
            {status === 'completed' ? (
              <div className="workflow-step completed">
                <CheckCircleOutlined />
                <Text>生成响应</Text>
              </div>
            ) : null}
          </div>
        </div>
      )}

      <Divider style={{ borderColor: 'rgba(255,255,255,0.2)', margin: '12px 0' }} />

      {/* 工具使用统计 */}
      <div className="tools-section">
        <Text className="section-title">工具使用</Text>
        <div className="tools-list">
          {toolsUsage.map((tool) => (
            <div key={tool.name} className="tool-item">
              <span className="tool-icon">{tool.icon}</span>
              <Text className="tool-name">{tool.name}</Text>
              <Tag color="purple" className="tool-count">
                {tool.count}
              </Tag>
            </div>
          ))}
        </div>
      </div>

      {/* Agent 能力 */}
      <div className="capabilities-section">
        <Text className="section-title">AI 能力</Text>
        <div className="capability-tags">
          <Tag color="blue">意图识别</Tag>
          <Tag color="green">语义匹配</Tag>
          <Tag color="purple">工作流编排</Tag>
          <Tag color="orange">自主决策</Tag>
        </div>
      </div>
    </div>
  );
};

export default AgentStatusPanel;
