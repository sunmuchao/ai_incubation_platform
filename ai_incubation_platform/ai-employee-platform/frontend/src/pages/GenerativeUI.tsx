/**
 * Generative UI 展示页面
 * 演示 AI 动态生成的界面
 */
import React, { useState } from 'react';
import { Layout, Typography, Card, Space, Button, Select } from 'antd';
import { AppstoreOutlined } from '@ant-design/icons';
import GenerativeUIRenderer from '@/components/GenerativeUIRenderer';
import './GenerativeUI.less';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const GenerativeUI: React.FC = () => {
  const [selectedDemo, setSelectedDemo] = useState('opportunity');

  // 演示数据
  const demoData: Record<string, any> = {
    opportunity: {
      opportunities: [
        {
          id: '1',
          type: 'promotion',
          title: '高级算法工程师',
          department: 'AI 研究院',
          match_score: 0.87,
          requirements: ['Python', '机器学习', '深度学习'],
          description: '负责 NLP 方向的算法研究和落地',
        },
        {
          id: '2',
          type: 'transfer',
          title: '技术专家 - 数据分析',
          department: '数据智能部',
          match_score: 0.75,
          requirements: ['SQL', 'Python', '数据可视化'],
          description: '构建企业级数据分析平台',
        },
        {
          id: '3',
          type: 'project',
          title: '智能客服系统项目',
          department: '产品研发中心',
          match_score: 0.82,
          requirements: ['NLP', '对话系统', '工程化'],
          description: '从 0 到 1 搭建智能客服系统',
        },
      ],
    },
    career: {
      target_state: {
        role_name: 'AI 技术专家',
        match_score: 0.65,
      },
      timeline: {
        duration_months: 18,
      },
      development_phases: [
        {
          name: '基础夯实阶段',
          duration_months: 6,
          focus_areas: ['深度学习', '大模型原理'],
          milestones: [
            { name: '完成深度学习专项课程', completed: true },
            { name: '阅读 10 篇顶会论文', completed: false },
          ],
        },
        {
          name: '实践提升阶段',
          duration_months: 6,
          focus_areas: ['项目实战', '技术影响力'],
          milestones: [
            { name: '主导一个 AI 项目', completed: false },
            { name: '发表技术博客 5 篇', completed: false },
          ],
        },
        {
          name: '专家突破阶段',
          duration_months: 6,
          focus_areas: ['技术创新', '团队建设'],
          milestones: [
            { name: '申请技术专利', completed: false },
            { name: '培养 2 名初级工程师', completed: false },
          ],
        },
      ],
      recommended_actions: [
        { action: '报名参加 AI 训练营', priority: 'high' },
        { action: '参与开源项目', priority: 'medium' },
      ],
    },
    skill: {
      skills: [
        { name: 'Python', level: 'expert', category: '编程语言' },
        { name: '机器学习', level: 'advanced', category: 'AI 技术' },
        { name: '深度学习', level: 'intermediate', category: 'AI 技术' },
        { name: '数据分析', level: 'advanced', category: '数据科学' },
        { name: 'SQL', level: 'advanced', category: '数据库' },
        { name: '云计算', level: 'intermediate', category: '基础设施' },
      ],
      strengths: ['Python 编程', '机器学习算法', '数据敏感度'],
      areas_for_improvement: ['深度学习', '大模型应用', '系统设计'],
    },
    dashboard: {
      skills: Array(15).fill({}),
      performance_history: [
        { rating: 4.2, trend: 'up' },
        { rating: 4.3, trend: 'up' },
        { rating: 4.1, trend: 'down' },
        { rating: 4.5, trend: 'up' },
      ],
      development_plans: Array(3).fill({}),
      total_earnings: 128000,
      total_hours: 856,
      completed_projects: 24,
    },
  };

  const componentMap: Record<string, string> = {
    opportunity: 'opportunity_cards',
    career: 'career_timeline',
    skill: 'skill_radar',
    dashboard: 'dashboard_stats',
  };

  return (
    <Layout className="generative-ui-page">
      <Header className="page-header">
        <div className="header-content">
          <AppstoreOutlined className="header-icon" />
          <div>
            <Title level={4} style={{ margin: 0 }}>Generative UI 演示</Title>
            <Text type="secondary">AI 动态生成的界面组件</Text>
          </div>
        </div>
        <Select
          value={selectedDemo}
          onChange={setSelectedDemo}
          options={[
            { value: 'opportunity', label: '机会匹配卡片' },
            { value: 'career', label: '职业发展时间线' },
            { value: 'skill', label: '技能雷达图' },
            { value: 'dashboard', label: '仪表盘统计' },
          ]}
          style={{ width: 200 }}
        />
      </Header>
      <Content className="page-content">
        <Card className="demo-card">
          <GenerativeUIRenderer componentType={componentMap[selectedDemo]} data={demoData[selectedDemo]} />
        </Card>

        <div className="demo-info">
          <Title level={5}>关于 Generative UI</Title>
          <Text type="secondary">
            Generative UI 是 AI Native 应用的核心特性之一。界面不再由开发者预先定义，
            而是由 AI 根据用户意图、上下文和数据特征动态生成最适合的展示形态。
            这实现了真正的"千人千面"甚至"一时一面"的个性化体验。
          </Text>
        </div>
      </Content>
    </Layout>
  );
};

export default GenerativeUI;
