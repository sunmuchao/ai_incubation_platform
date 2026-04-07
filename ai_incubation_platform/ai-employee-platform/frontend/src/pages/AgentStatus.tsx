/**
 * Agent 状态页面
 * 显示 AI 智能体的详细工作状态
 */
import React, { useState, useEffect } from 'react';
import { Layout, Typography, Card, Row, Col, Progress, Timeline, Tag, Space, Statistic, Badge } from 'antd';
import {
  RobotOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BranchesOutlined,
  ToolOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import './AgentStatus.less';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const AgentStatus: React.FC = () => {
  // 模拟 Agent 状态数据
  const [agentData] = useState({
    status: 'active',
    uptime: '99.8%',
    totalRequests: 1247,
    avgResponseTime: '1.2s',
    activeWorkflows: 3,
    completedTasks: 856,
    toolsAvailable: 12,
    recentActivities: [
      { time: '10:32', action: '执行机会匹配', status: 'completed' },
      { time: '10:28', action: '生成职业规划', status: 'completed' },
      { time: '10:15', action: '技能差距分析', status: 'completed' },
      { time: '09:45', action: '绩效评估报告', status: 'completed' },
    ],
    activeWorkflowsList: [
      { name: 'auto_talent_match', progress: 75, step: '匹配度计算' },
      { name: 'auto_career_planning', progress: 40, step: '分析员工画像' },
      { name: 'auto_performance_review', progress: 90, step: '生成改进建议' },
    ],
    toolsUsage: [
      { name: 'analyze_profile', calls: 156, success: 98 },
      { name: 'match_opportunities', calls: 89, success: 95 },
      { name: 'plan_career', calls: 67, success: 97 },
      { name: 'track_performance', calls: 45, success: 99 },
    ],
  });

  return (
    <Layout className="agent-status-page">
      <Header className="page-header">
        <div className="header-content">
          <RobotOutlined className="header-icon" />
          <div>
            <Title level={4} style={{ margin: 0 }}>Agent 状态监控</Title>
            <Text type="secondary">AI 智能体实时工作状态</Text>
          </div>
        </div>
        <Badge status="success" text="运行正常" />
      </Header>
      <Content className="page-content">
        {/* 统计卡片 */}
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card size="small" className="stat-card">
              <Statistic
                title="总请求数"
                value={agentData.totalRequests}
                prefix={<FileTextOutlined />}
                suffix="次"
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" className="stat-card">
              <Statistic
                title="平均响应时间"
                value={agentData.avgResponseTime}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" className="stat-card">
              <Statistic
                title="活跃工作流"
                value={agentData.activeWorkflows}
                prefix={<BranchesOutlined />}
                suffix="个"
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" className="stat-card">
              <Statistic
                title="任务完成率"
                value={98}
                suffix="%"
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 工作流进度 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="活跃工作流" size="small">
              <div className="workflow-list">
                {agentData.activeWorkflowsList.map((workflow, index) => (
                  <div key={index} className="workflow-item">
                    <div className="workflow-header">
                      <Space>
                        <BranchesOutlined className="workflow-icon" />
                        <Text strong>{workflow.name}</Text>
                      </Space>
                      <Tag color="blue">{workflow.step}</Tag>
                    </div>
                    <Progress percent={workflow.progress} strokeColor="#722ed1" />
                  </div>
                ))}
              </div>
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="最近活动" size="small">
              <Timeline
                items={agentData.recentActivities.map((activity, index) => ({
                  color: activity.status === 'completed' ? '#52c41a' : '#1890ff',
                  children: (
                    <div className="activity-item">
                      <Text strong>{activity.action}</Text>
                      <div className="activity-meta">
                        <ClockCircleOutlined />
                        <Text type="secondary">{activity.time}</Text>
                        {activity.status === 'completed' && (
                          <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 8 }} />
                        )}
                      </div>
                    </div>
                  ),
                }))}
              />
            </Card>
          </Col>
        </Row>

        {/* 工具使用统计 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <Card title="工具使用统计" size="small">
              <div className="tools-grid">
                {agentData.toolsUsage.map((tool, index) => (
                  <div key={index} className="tool-stat">
                    <div className="tool-header">
                      <ToolOutlined className="tool-icon" />
                      <Text strong className="tool-name">{tool.name}</Text>
                    </div>
                    <div className="tool-stats">
                      <div className="stat-item">
                        <Text type="secondary">调用</Text>
                        <Text strong>{tool.calls}</Text>
                      </div>
                      <div className="stat-item">
                        <Text type="secondary">成功率</Text>
                        <Text strong style={{ color: '#52c41a' }}>{tool.success}%</Text>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </Col>
        </Row>

        {/* Agent 信息 */}
        <Card title="Agent 信息" size="small" style={{ marginTop: 16 }}>
          <div className="agent-info-grid">
            <div className="info-item">
              <Text type="secondary">Agent 名称</Text>
              <Text strong>TalentAgent v2.0</Text>
            </div>
            <div className="info-item">
              <Text type="secondary">运行时间</Text>
              <Text strong>{agentData.uptime}</Text>
            </div>
            <div className="info-item">
              <Text type="secondary">可用工具</Text>
              <Text strong>{agentData.toolsAvailable} 个</Text>
            </div>
            <div className="info-item">
              <Text type="secondary">工作流</Text>
              <Text strong>4 个核心工作流</Text>
            </div>
          </div>
        </Card>
      </Content>
    </Layout>
  );
};

export default AgentStatus;
