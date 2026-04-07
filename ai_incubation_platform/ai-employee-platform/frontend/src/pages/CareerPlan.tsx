/**
 * 职业规划页面
 * 展示 AI 生成的职业发展路径
 */
import React, { useState } from 'react';
import { Layout, Typography, Card, Row, Col, Timeline, Tag, Progress, Space, Button, Steps } from 'antd';
import { RocketOutlined, FlagOutlined, TrophyOutlined, BookOutlined, RiseOutlined } from '@ant-design/icons';
import CareerTimeline from '@/components/CareerTimeline';
import './CareerPlan.less';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

const CareerPlan: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  // 模拟职业规划数据
  const careerData = {
    target_state: {
      role_name: 'AI 技术专家 / 架构师',
      match_score: 0.65,
    },
    timeline: {
      duration_months: 18,
      start_date: '2026-04',
      end_date: '2027-10',
    },
    development_phases: [
      {
        name: '第一阶段：基础夯实',
        duration_months: 6,
        focus_areas: ['深度学习进阶', '大模型原理与应用', '系统架构设计'],
        milestones: [
          { name: '完成高级深度学习课程', completed: true, target_date: '2026-06' },
          { name: '阅读并理解 15 篇顶会论文', completed: false, target_date: '2026-08' },
          { name: '掌握至少一个大模型框架', completed: false, target_date: '2026-09' },
        ],
      },
      {
        name: '第二阶段：实践提升',
        duration_months: 6,
        focus_areas: ['项目实战经验', '技术影响力建设', '跨团队协作'],
        milestones: [
          { name: '主导一个 AI 项目从 0 到 1 落地', completed: false, target_date: '2026-12' },
          { name: '发表技术博客/文章 5 篇', completed: false, target_date: '2027-01' },
          { name: '在技术大会/内部分享 2 次', completed: false, target_date: '2027-03' },
        ],
      },
      {
        name: '第三阶段：专家突破',
        duration_months: 6,
        focus_areas: ['技术创新', '团队领导力', '战略规划'],
        milestones: [
          { name: '申请 1-2 项技术专利', completed: false, target_date: '2027-06' },
          { name: '培养 2-3 名初级工程师', completed: false, target_date: '2027-08' },
          { name: '制定团队技术 roadmap', completed: false, target_date: '2027-10' },
        ],
      },
    ],
    recommended_actions: [
      { action: '报名参加公司 AI 训练营', priority: 'high' },
      { action: '参与开源项目贡献', priority: 'high' },
      { action: '寻找技术导师指导', priority: 'medium' },
      { action: '建立个人技术品牌', priority: 'medium' },
    ],
    skills_gap: [
      { skill: '大模型应用', current: 40, target: 80 },
      { skill: '系统架构', current: 50, target: 85 },
      { skill: '团队管理', current: 30, target: 70 },
      { skill: '战略规划', current: 25, target: 65 },
    ],
  };

  return (
    <Layout className="career-plan-page">
      <Header className="page-header">
        <div className="header-content">
          <RocketOutlined className="header-icon" />
          <div>
            <Title level={4} style={{ margin: 0 }}>职业发展规划</Title>
            <Text type="secondary">AI 生成的个性化职业发展路径</Text>
          </div>
        </div>
        <Button type="primary" icon={<RiseOutlined />}>
          更新规划
        </Button>
      </Header>
      <Content className="page-content">
        {/* 目标职位 */}
        <Card className="target-card" size="small">
          <div className="target-header">
            <div className="target-icon-wrapper">
              <TrophyOutlined className="target-icon" />
            </div>
            <div className="target-info">
              <Title level={3} style={{ margin: '0 0 8px 0' }}>
                {careerData.target_state.role_name}
              </Title>
              <div className="target-stats">
                <Space size="large">
                  <div className="stat">
                    <Text type="secondary">当前匹配度</Text>
                    <div>
                      <Progress
                        type="circle"
                        percent={careerData.target_state.match_score * 100}
                        size={50}
                        strokeColor={{
                          '0%': '#722ed1',
                          '100%': '#1890ff',
                        }}
                        format={(percent) => `${percent}%`}
                      />
                    </div>
                  </div>
                  <div className="stat">
                    <Text type="secondary">预计耗时</Text>
                    <div className="stat-value">{careerData.timeline.duration_months} 个月</div>
                  </div>
                  <div className="stat">
                    <Text type="secondary">规划周期</Text>
                    <div className="stat-value">
                      {careerData.timeline.start_date} - {careerData.timeline.end_date}
                    </div>
                  </div>
                </Space>
              </div>
            </div>
          </div>
        </Card>

        {/* 发展阶段 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}>
            <CareerTimeline data={careerData} />
          </Col>

          <Col xs={24} lg={8}>
            {/* 技能差距 */}
            <Card title="技能差距分析" size="small" className="gap-card">
              <div className="skills-gap-list">
                {careerData.skills_gap.map((gap, index) => (
                  <div key={index} className="gap-item">
                    <div className="gap-header">
                      <Text strong>{gap.skill}</Text>
                      <Text type="secondary">
                        {gap.current} → {gap.target}
                      </Text>
                    </div>
                    <div className="gap-progress">
                      <div className="gap-bar">
                        <div
                          className="gap-current"
                          style={{ width: `${gap.current}%` }}
                        />
                        <div
                          className="gap-target"
                          style={{ width: `${gap.target}%`, left: 0 }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* 推荐行动 */}
            <Card title="推荐行动" size="small" className="actions-card" style={{ marginTop: 16 }}>
              <div className="actions-list">
                {careerData.recommended_actions.map((action, index) => (
                  <div key={index} className="action-item">
                    <FlagOutlined className="action-icon" />
                    <Text>{action.action}</Text>
                    {action.priority === 'high' && (
                      <Tag color="red" style={{ marginLeft: 'auto' }}>
                        优先
                      </Tag>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default CareerPlan;
