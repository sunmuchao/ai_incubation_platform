/**
 * 机会匹配页面
 * 展示 AI 智能匹配的工作机会
 */
import React, { useState, useEffect } from 'react';
import { Layout, Typography, Card, Row, Col, Input, Select, Slider, Space, Tag, Button, Empty } from 'antd';
import { SearchOutlined, FilterOutlined, ThunderboltOutlined } from '@ant-design/icons';
import OpportunityCards from '@/components/OpportunityCards';
import './OpportunityMatch.less';

const { Header, Content } = Layout;
const { Title, Text } = Typography;
const { Search } = Input;

const OpportunityMatch: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [filters, setFilters] = useState({
    type: 'all',
    minMatchScore: 0.6,
    keyword: '',
  });

  // 模拟数据
  useEffect(() => {
    // 实际应该调用 API
    setOpportunities([
      {
        id: '1',
        type: 'promotion',
        title: '高级算法工程师',
        department: 'AI 研究院',
        match_score: 0.87,
        requirements: ['Python', '机器学习', '深度学习'],
        description: '负责 NLP 方向的算法研究和落地，参与大模型研发',
      },
      {
        id: '2',
        type: 'transfer',
        title: '技术专家 - 数据分析',
        department: '数据智能部',
        match_score: 0.75,
        requirements: ['SQL', 'Python', '数据可视化'],
        description: '构建企业级数据分析平台，支持业务决策',
      },
      {
        id: '3',
        type: 'project',
        title: '智能客服系统项目',
        department: '产品研发中心',
        match_score: 0.82,
        requirements: ['NLP', '对话系统', '工程化'],
        description: '从 0 到 1 搭建智能客服系统，提升客户满意度',
      },
      {
        id: '4',
        type: 'promotion',
        title: '技术团队负责人',
        department: '创新业务部',
        match_score: 0.68,
        requirements: ['团队管理', '技术规划', '沟通能力'],
        description: '带领 10 人技术团队，负责新产品线技术规划',
      },
    ]);
  }, []);

  const handleSearch = (value: string) => {
    setFilters({ ...filters, keyword: value });
  };

  const filteredOpportunities = opportunities.filter((opp) => {
    if (filters.type !== 'all' && opp.type !== filters.type) return false;
    if (opp.match_score < filters.minMatchScore) return false;
    if (filters.keyword && !opp.title.toLowerCase().includes(filters.keyword.toLowerCase())) return false;
    return true;
  });

  return (
    <Layout className="opportunity-match-page">
      <Header className="page-header">
        <div className="header-content">
          <ThunderboltOutlined className="header-icon" />
          <div>
            <Title level={4} style={{ margin: 0 }}>机会匹配</Title>
            <Text type="secondary">AI 智能匹配适合您的发展机会</Text>
          </div>
        </div>
      </Header>
      <Content className="page-content">
        {/* 筛选区域 */}
        <Card className="filter-card" size="small">
          <Row gutter={[16, 16]} align="middle">
            <Col xs={24} sm={8}>
              <Search
                placeholder="搜索职位、部门"
                allowClear
                enterButton={<SearchOutlined />}
                onSearch={handleSearch}
                style={{ width: '100%' }}
              />
            </Col>
            <Col xs={24} sm={4}>
              <Select
                value={filters.type}
                onChange={(value) => setFilters({ ...filters, type: value })}
                options={[
                  { value: 'all', label: '全部类型' },
                  { value: 'promotion', label: '晋升机会' },
                  { value: 'transfer', label: '转岗机会' },
                  { value: 'project', label: '项目机会' },
                ]}
                style={{ width: '100%' }}
              />
            </Col>
            <Col xs={24} sm={8}>
              <div className="slider-container">
                <Text type="secondary" style={{ marginRight: 8 }}>最低匹配度:</Text>
                <Slider
                  value={filters.minMatchScore}
                  onChange={(value) => setFilters({ ...filters, minMatchScore: value })}
                  min={0}
                  max={1}
                  step={0.05}
                  marks={{ 0: '0%', 0.5: '50%', 0.8: '80%', 1: '100%' }}
                />
              </div>
            </Col>
            <Col xs={24} sm={4}>
              <div className="result-count">
                <Text type="secondary">找到 </Text>
                <Text strong>{filteredOpportunities.length}</Text>
                <Text type="secondary"> 个机会</Text>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 机会列表 */}
        <Card className="opportunities-card" size="small">
          {filteredOpportunities.length > 0 ? (
            <OpportunityCards data={{ opportunities: filteredOpportunities }} />
          ) : (
            <Empty description="没有找到匹配的机会，尝试调整筛选条件" />
          )}
        </Card>

        {/* AI 提示 */}
        <Card className="ai-tip-card" size="small">
          <div className="tip-content">
            <ThunderboltOutlined className="tip-icon" />
            <div>
              <Text strong>AI 匹配提示</Text>
              <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
                匹配度基于您的技能、经验、绩效和文化适配度综合计算。
                匹配度越高表示您与该机会的适配程度越高。
                建议您优先关注匹配度 80% 以上的机会。
              </Text>
            </div>
          </div>
        </Card>
      </Content>
    </Layout>
  );
};

export default OpportunityMatch;
