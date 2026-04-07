/**
 * AI Native 综合演示页面
 *
 * 展示所有 AI Native 特性:
 * - 对话式交互
 * - Generative UI 动态生成
 * - Agent 可视化
 * - 主动推送通知
 * - 置信度显示
 * - 工作流编排可视化
 */
import React, { useState, useEffect } from 'react';
import {
  Layout,
  Typography,
  Card,
  Row,
  Col,
  Space,
  Tag,
  Button,
  Progress,
  Statistic,
  Divider,
  Switch,
  Collapse,
  Badge,
  Timeline,
  Alert,
} from 'antd';
import {
  RobotOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  BellOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  BranchesOutlined,
  ToolOutlined,
  MessageOutlined,
  StarOutlined,
} from '@ant-design/icons';
import AINotification from '@/components/AINotification';
import GenerativeUIRenderer from '@/components/GenerativeUIRenderer';
import AgentStatusPanel from '@/components/AgentStatusPanel';
import aiNativeService, { AISuggestion, PushNotification } from '@/services/aiNativeService';
import './AINativeDemo.less';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

const AINativeDemo: React.FC = () => {
  const [agentStatus, setAgentStatus] = useState<'idle' | 'thinking' | 'executing' | 'completed'>('idle');
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [notifications, setNotifications] = useState<PushNotification[]>([]);
  const [autoPushEnabled, setAutoPushEnabled] = useState(true);
  const [confidence, setConfidence] = useState(0.85);

  useEffect(() => {
    // 初始化 AI Native 服务
    aiNativeService.initialize();

    // 订阅 AI 建议
    const unsubscribe = aiNativeService.onSuggestion((suggestion) => {
      setSuggestions((prev) => [suggestion, ...prev]);
    });

    // 订阅通知
    const unsubscribeNotification = aiNativeService.onNotification((notification) => {
      setNotifications((prev) => [notification, ...prev]);
    });

    // 模拟 AI 主动推送演示
    const demoInterval = setInterval(() => {
      if (autoPushEnabled) {
        simulateProactivePush();
      }
    }, 15000); // 每 15 秒模拟一次主动推送

    return () => {
      unsubscribe();
      unsubscribeNotification();
      clearInterval(demoInterval);
    };
  }, [autoPushEnabled]);

  // 模拟 AI 主动推送
  const simulateProactivePush = () => {
    const demoSuggestions: AISuggestion[] = [
      {
        id: `sug-${Date.now()}`,
        category: 'opportunity',
        title: '新的晋升机会',
        description: 'AI 检测到您已完成所有前置条件，建议申请高级工程师职位',
        confidence: 0.89,
        data: { opportunity_id: 'promo-001', match_score: 0.89 },
        actions: [
          { action: 'apply', label: '立即申请' },
          { action: 'learn_more', label: '了解更多' },
        ],
      },
      {
        id: `sug-${Date.now() + 1}`,
        category: 'skill',
        title: '技能提升建议',
        description: '您的 Python 技能已达到高级水平，建议学习系统设计知识',
        confidence: 0.76,
        data: { skill_area: 'system_design' },
        actions: [
          { action: 'find_courses', label: '查找课程' },
          { action: 'dismiss', label: '暂不需要' },
        ],
      },
      {
        id: `sug-${Date.now() + 2}`,
        category: 'performance',
        title: '绩效改进提醒',
        description: 'AI 注意到您最近的项目交付时间有所延迟，需要帮助吗？',
        confidence: 0.72,
        data: { area: 'time_management' },
        actions: [
          { action: 'get_help', label: '获取帮助' },
          { action: 'dismiss', label: '不需要' },
        ],
      },
    ];

    const randomSuggestion = demoSuggestions[Math.floor(Math.random() * demoSuggestions.length)];
    setSuggestions((prev) => [randomSuggestion, ...prev]);
  };

  // 模拟 Agent 执行工作流
  const simulateAgentWorkflow = async () => {
    setAgentStatus('thinking');
    setConfidence(0.6);

    // 模拟思考阶段
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setAgentStatus('executing');
    setConfidence(0.75);

    // 模拟执行阶段
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setAgentStatus('completed');
    setConfidence(0.92);

    // 完成后重置
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setAgentStatus('idle');
    setConfidence(0.85);
  };

  // 置信度颜色
  const getConfidenceColor = (value: number) => {
    if (value >= 0.8) return '#52c41a';
    if (value >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const getConfidenceLabel = (value: number) => {
    if (value >= 0.8) return '高';
    if (value >= 0.6) return '中';
    return '低';
  };

  return (
    <Layout className="ai-native-demo-page">
      <Header className="demo-header">
        <div className="header-content">
          <RobotOutlined className="header-icon" style={{ color: '#722ed1' }} />
          <div>
            <Title level={4} style={{ margin: 0 }}>
              AI Native 功能演示
            </Title>
            <Text type="secondary">对话式交互 · Generative UI · Agent 可视化 · 主动推送</Text>
          </div>
        </div>
        <Space>
          <AINotification />
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={simulateAgentWorkflow}>
            模拟 AI 工作流
          </Button>
        </Space>
      </Header>

      <Content className="demo-content">
        <Row gutter={[16, 16]}>
          {/* 左侧：Agent 状态和置信度 */}
          <Col xs={24} lg={6}>
            <Card
              className="agent-card"
              size="small"
              title={
                <Space>
                  <RobotOutlined />
                  AI Agent 状态
                </Space>
              }
            >
              <AgentStatusPanel status={agentStatus} confidence={confidence} />
            </Card>

            <Card className="confidence-card" size="small" style={{ marginTop: 16 }}>
              <div className="confidence-display">
                <div className="confidence-header">
                  <EyeOutlined />
                  <Text strong>当前置信度</Text>
                </div>
                <div className="confidence-value" style={{ color: getConfidenceColor(confidence) }}>
                  {(confidence * 100).toFixed(0)}%
                  <Tag color={confidence >= 0.8 ? 'green' : confidence >= 0.6 ? 'orange' : 'red'}>
                    {getConfidenceLabel(confidence)} 置信度
                  </Tag>
                </div>
                <Progress
                  percent={confidence * 100}
                  strokeColor={getConfidenceColor(confidence)}
                  showInfo={false}
                />
                <Paragraph type="secondary" className="confidence-description">
                  {confidence >= 0.8
                    ? 'AI 高度确信，可自主执行'
                    : confidence >= 0.6
                    ? 'AI 较为确信，建议人类确认'
                    : 'AI 不确定，需要人类决策'}
                </Paragraph>
              </div>
            </Card>

            <Card className="workflow-card" size="small" style={{ marginTop: 16 }}>
              <div className="workflow-display">
                <div className="workflow-header">
                  <BranchesOutlined />
                  <Text strong>工作流编排</Text>
                </div>
                <Timeline
                  items={[
                    {
                      color: agentStatus !== 'idle' ? '#52c41a' : '#d9d9d9',
                      children: (
                        <div className="workflow-step">
                          <Text>感知环境</Text>
                          {agentStatus !== 'idle' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                        </div>
                      ),
                    },
                    {
                      color: agentStatus === 'thinking' || agentStatus === 'executing' || agentStatus === 'completed' ? '#1890ff' : '#d9d9d9',
                      children: (
                        <div className="workflow-step">
                          <Text>理解意图</Text>
                          {(agentStatus === 'thinking' || agentStatus === 'executing' || agentStatus === 'completed') && (
                            <LoadingOutlined spin={agentStatus === 'thinking'} style={{ color: '#1890ff' }} />
                          )}
                        </div>
                      ),
                    },
                    {
                      color: agentStatus === 'executing' || agentStatus === 'completed' ? '#722ed1' : '#d9d9d9',
                      children: (
                        <div className="workflow-step">
                          <Text>工具调用</Text>
                          {(agentStatus === 'executing' || agentStatus === 'completed') && (
                            <CheckCircleOutlined style={{ color: '#722ed1' }} />
                          )}
                        </div>
                      ),
                    },
                    {
                      color: agentStatus === 'completed' ? '#52c41a' : '#d9d9d9',
                      children: (
                        <div className="workflow-step">
                          <Text>生成响应</Text>
                          {agentStatus === 'completed' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                        </div>
                      ),
                    },
                  ]}
                />
              </div>
            </Card>
          </Col>

          {/* 中间：Generative UI 展示 */}
          <Col xs={24} lg={12}>
            <Card
              className="generative-ui-card"
              size="small"
              title={
                <Space>
                  <ThunderboltOutlined />
                  Generative UI 展示
                </Space>
              }
              extra={
                <Space>
                  <Tag color="purple">动态生成</Tag>
                  <Tag color="blue">情境感知</Tag>
                </Space>
              }
            >
              <GenerativeUIRenderer
                componentType="opportunity_cards"
                data={{
                  opportunities: [
                    {
                      id: '1',
                      type: 'promotion',
                      title: '高级算法工程师',
                      department: 'AI 研究院',
                      match_score: 0.87,
                      requirements: ['Python', '机器学习', '深度学习'],
                    },
                    {
                      id: '2',
                      type: 'transfer',
                      title: '技术专家 - 数据分析',
                      department: '数据智能部',
                      match_score: 0.75,
                      requirements: ['SQL', 'Python', '数据可视化'],
                    },
                  ],
                }}
              />
            </Card>

            <Card className="skills-card" size="small" style={{ marginTop: 16 }}>
              <GenerativeUIRenderer
                componentType="skill_radar"
                data={{
                  skills: [
                    { name: 'Python', level: 'expert', category: '编程语言' },
                    { name: '机器学习', level: 'advanced', category: 'AI 技术' },
                    { name: '深度学习', level: 'intermediate', category: 'AI 技术' },
                    { name: '数据分析', level: 'advanced', category: '数据科学' },
                    { name: 'SQL', level: 'advanced', category: '数据库' },
                  ],
                  strengths: ['Python 编程', '机器学习算法'],
                  areas_for_improvement: ['深度学习', '大模型应用'],
                }}
              />
            </Card>
          </Col>

          {/* 右侧：主动推送和设置 */}
          <Col xs={24} lg={6}>
            <Card
              className="push-settings-card"
              size="small"
              title={
                <Space>
                  <BellOutlined />
                  主动推送设置
                </Space>
              }
            >
              <div className="push-settings">
                <div className="setting-item">
                  <Text>启用主动推送</Text>
                  <Switch
                    checked={autoPushEnabled}
                    onChange={setAutoPushEnabled}
                    checkedChildren="开"
                    unCheckedChildren="关"
                  />
                </div>
                <Divider style={{ margin: '12px 0' }} />
                <div className="setting-item">
                  <Text>推送类型</Text>
                  <Space wrap>
                    <Tag color="purple">机会匹配</Tag>
                    <Tag color="blue">技能提升</Tag>
                    <Tag color="green">绩效提醒</Tag>
                  </Space>
                </div>
                <div className="setting-item">
                  <Text>置信度阈值</Text>
                  <Tag color="orange">≥70% 推送</Tag>
                </div>
              </div>
            </Card>

            <Card
              className="ai-suggestions-card"
              size="small"
              style={{ marginTop: 16 }}
              title={
                <Space>
                  <BulbOutlined style={{ color: '#faad14' }} />
                  AI 智能建议
                  <Badge count={suggestions.length} offset={[-5, 0]} />
                </Space>
              }
            >
              <div className="suggestions-list">
                {suggestions.length === 0 ? (
                  <Text type="secondary">暂无 AI 建议</Text>
                ) : (
                  suggestions.slice(0, 5).map((suggestion) => (
                    <Card
                      key={suggestion.id}
                      size="small"
                      className="suggestion-item"
                      type="inner"
                    >
                      <div className="suggestion-header">
                        <Text strong>{suggestion.title}</Text>
                        <Tag
                          color={suggestion.confidence >= 0.8 ? 'green' : suggestion.confidence >= 0.6 ? 'orange' : 'red'}
                        >
                          {(suggestion.confidence * 100).toFixed(0)}%
                        </Tag>
                      </div>
                      <Paragraph type="secondary" className="suggestion-description" ellipsis={{ rows: 2 }}>
                        {suggestion.description}
                      </Paragraph>
                      {suggestion.actions && (
                        <Space wrap size={[0, 4]}>
                          {suggestion.actions.map((action, idx) => (
                            <Button key={idx} type="link" size="small">
                              {action.label}
                            </Button>
                          ))}
                        </Space>
                      )}
                    </Card>
                  ))
                )}
              </div>
            </Card>

            <Alert
              className="demo-tip"
              type="info"
              message="AI Native 特性"
              description="AI 不仅是工具，更是自主代理。系统会主动感知环境变化，推送高置信度建议，并在人类确认下自主执行。"
              showIcon
              icon={<MessageOutlined />}
            />
          </Col>
        </Row>

        {/* 底部：特性说明 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <Collapse ghost>
              <Panel header={<Space><StarOutlined />AI Native 核心特性说明</Space>} key="1">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={6}>
                    <Card size="small" className="feature-card">
                      <div className="feature-icon" style={{ backgroundColor: '#722ed1' }}>
                        <MessageOutlined />
                      </div>
                      <Title level={5}>对话式交互</Title>
                      <Text type="secondary">
                        通过自然语言表达意图，而非表单 + 按钮。AI 理解上下文并执行操作。
                      </Text>
                    </Card>
                  </Col>
                  <Col xs={24} sm={6}>
                    <Card size="small" className="feature-card">
                      <div className="feature-icon" style={{ backgroundColor: '#1890ff' }}>
                        <ThunderboltOutlined />
                      </div>
                      <Title level={5}>Generative UI</Title>
                      <Text type="secondary">
                        界面由 AI 动态生成，根据任务类型、用户偏好和数据特征实时构建最适合的展示形态。
                      </Text>
                    </Card>
                  </Col>
                  <Col xs={24} sm={6}>
                    <Card size="small" className="feature-card">
                      <div className="feature-icon" style={{ backgroundColor: '#52c41a' }}>
                        <EyeOutlined />
                      </div>
                      <Title level={5}>Agent 可视化</Title>
                      <Text type="secondary">
                        实时显示 AI 工作状态、置信度和执行进度，让人类了解 AI 的决策过程。
                      </Text>
                    </Card>
                  </Col>
                  <Col xs={24} sm={6}>
                    <Card size="small" className="feature-card">
                      <div className="feature-icon" style={{ backgroundColor: '#faad14' }}>
                        <BellOutlined />
                      </div>
                      <Title level={5}>主动推送</Title>
                      <Text type="secondary">
                        AI 主动感知环境变化，推送高置信度建议，形成"感知→行动→确认"的闭环。
                      </Text>
                    </Card>
                  </Col>
                </Row>
              </Panel>
            </Collapse>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default AINativeDemo;
