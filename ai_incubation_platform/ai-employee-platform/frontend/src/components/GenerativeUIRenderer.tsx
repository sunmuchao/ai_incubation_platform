/**
 * Generative UI 渲染器
 *
 * 根据 AI 响应动态生成不同的 UI 组件
 * 实现"动态生成界面"的 AI Native 交互范式
 */
import React from 'react';
import { Card, Row, Col, Progress, Tag, Space, Typography, Rate, Statistic } from 'antd';
import {
  ThunderboltOutlined,
  RiseOutlined,
  FallOutlined,
  TrophyOutlined,
  BookOutlined,
  UsergroupAddOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import OpportunityCards from './OpportunityCards';
import CareerTimeline from './CareerTimeline';
import SkillRadar from './SkillRadar';
import DashboardStats from './DashboardStats';
import './GenerativeUIRenderer.less';

const { Title, Text, Paragraph } = Typography;

interface GenerativeUIRendererProps {
  componentType: string;
  data?: Record<string, any>;
}

/**
 * 置信度指示器组件
 * 显示 AI 决策的可信度
 */
const ConfidenceIndicator: React.FC<{ confidence: number }> = ({ confidence }) => {
  const getColor = (value: number) => {
    if (value >= 0.8) return '#52c41a';
    if (value >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const getLabel = (value: number) => {
    if (value >= 0.8) return '高置信度';
    if (value >= 0.6) return '中等置信度';
    return '低置信度';
  };

  return (
    <div className="confidence-indicator">
      <div className="confidence-bar">
        <div
          className="confidence-fill"
          style={{ width: `${confidence * 100}%`, backgroundColor: getColor(confidence) }}
        />
      </div>
      <Text className="confidence-label" style={{ color: getColor(confidence) }}>
        {getLabel(confidence)} ({(confidence * 100).toFixed(0)}%)
      </Text>
    </div>
  );
};

/**
 * AI 执行状态组件
 * 显示 AI 正在执行的操作
 */
const AIExecutionStatus: React.FC<{ steps: Array<{ name: string; status: 'pending' | 'running' | 'completed' }> }> = ({
  steps,
}) => {
  return (
    <Card className="ai-execution-status" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <Text strong>AI 执行步骤</Text>
        {steps.map((step, index) => (
          <div key={index} className="execution-step">
            {step.status === 'completed' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
            {step.status === 'running' && <ClockCircleOutlined spin style={{ color: '#1890ff' }} />}
            {step.status === 'pending' && <div className="step-pending-dot" />}
            <Text className={step.status === 'completed' ? 'step-completed' : ''}>{step.name}</Text>
          </div>
        ))}
      </Space>
    </Card>
  );
};

const GenerativeUIRenderer: React.FC<GenerativeUIRendererProps> = ({ componentType, data }) => {
  // 渲染不同的组件类型
  const renderComponent = () => {
    switch (componentType) {
      case 'opportunity_cards':
        return <OpportunityCards data={data} />;

      case 'career_timeline':
        return <CareerTimeline data={data} />;

      case 'skill_radar':
        return <SkillRadar data={data} />;

      case 'dashboard_stats':
        return <DashboardStats data={data} />;

      case 'confidence_indicator':
        return data?.confidence ? <ConfidenceIndicator confidence={data.confidence} /> : null;

      case 'execution_status':
        return data?.steps ? <AIExecutionStatus steps={data.steps} /> : null;

      default:
        // 默认卡片渲染
        return (
          <Card className="default-data-card" size="small">
            <Title level={5}>数据分析</Title>
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </Card>
        );
    }
  };

  return <div className="generative-ui-renderer">{renderComponent()}</div>;
};

export default GenerativeUIRenderer;
