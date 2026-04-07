/**
 * 绩效评估页面
 * 展示 AI 生成的绩效评估和改进建议
 */
import React, { useState } from 'react';
import { Layout, Typography, Card, Row, Col, Progress, Table, Tag, Space, Timeline, Rate, Button } from 'antd';
import {
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import './PerformanceReview.less';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

const PerformanceReview: React.FC = () => {
  // 模拟绩效数据
  const performanceData = {
    overall: {
      rating: 4.5,
      score: 88,
      trend: 'up',
      percentile: 85,
    },
    dimensions: [
      { name: '工作质量', score: 92, trend: 'up', weight: 0.3 },
      { name: '工作效率', score: 85, trend: 'stable', weight: 0.25 },
      { name: '团队协作', score: 90, trend: 'up', weight: 0.2 },
      { name: '创新能力', score: 82, trend: 'up', weight: 0.15 },
      { name: '学习能力', score: 88, trend: 'stable', weight: 0.1 },
    ],
    history: [
      { quarter: 'Q1 2025', rating: 4.2, score: 82 },
      { quarter: 'Q2 2025', rating: 4.3, score: 84 },
      { quarter: 'Q3 2025', rating: 4.4, score: 86 },
      { quarter: 'Q4 2025', rating: 4.5, score: 88 },
    ],
    achievements: [
      { title: '完成 AI 助手核心模块开发', impact: 'high', date: '2025-12' },
      { title: '优化系统性能提升 40%', impact: 'high', date: '2025-11' },
      { title: '获得客户表扬信 3 封', impact: 'medium', date: '2025-10' },
    ],
    improvements: [
      { area: '时间管理', suggestion: '使用番茄工作法提高专注度', priority: 'high' },
      { area: '文档写作', suggestion: '参加技术写作培训课程', priority: 'medium' },
      { area: '公开演讲', suggestion: '参与内部分享锻炼表达能力', priority: 'low' },
    ],
  };

  const dimensionColumns = [
    {
      title: '维度',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '得分',
      dataIndex: 'score',
      key: 'score',
      render: (score: number) => (
        <Progress
          type="line"
          percent={score}
          size="small"
          strokeColor={score >= 90 ? '#52c41a' : score >= 80 ? '#1890ff' : '#faad14'}
          format={() => `${score}分`}
        />
      ),
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      render: (trend: string) => (
        <Tag color={trend === 'up' ? 'green' : trend === 'down' ? 'red' : 'blue'}>
          {trend === 'up' && <RiseOutlined />}
          {trend === 'down' && <FallOutlined />}
          {trend === 'stable' && '➡️'}
          {trend === 'up' ? '上升' : trend === 'down' ? '下降' : '稳定'}
        </Tag>
      ),
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      render: (weight: number) => `${(weight * 100).toFixed(0)}%`,
    },
  ];

  const trendChartOption = {
    xAxis: {
      type: 'category',
      data: performanceData.history.map((h) => h.quarter),
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
    },
    series: [
      {
        name: '绩效得分',
        data: performanceData.history.map((h) => h.score),
        type: 'line',
        smooth: true,
        areaStyle: {
          color: 'rgba(114, 46, 209, 0.3)',
        },
        lineStyle: {
          color: '#722ed1',
          width: 3,
        },
        itemStyle: {
          color: '#722ed1',
        },
      },
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    tooltip: {
      formatter: '{b}: {c}分',
    },
  };

  const radarChartOption = {
    radar: {
      indicator: performanceData.dimensions.map((d) => ({ name: d.name, max: 100 })),
      shape: 'circle',
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: performanceData.dimensions.map((d) => d.score),
            name: '当前表现',
            areaStyle: {
              color: 'rgba(114, 46, 209, 0.5)',
            },
            lineStyle: {
              color: '#722ed1',
            },
          },
        ],
      },
    ],
  };

  return (
    <Layout className="performance-review-page">
      <Header className="page-header">
        <div className="header-content">
          <TrophyOutlined className="header-icon" />
          <div>
            <Title level={4} style={{ margin: 0 }}>绩效评估</Title>
            <Text type="secondary">AI 生成的绩效分析和改进建议</Text>
          </div>
        </div>
        <Button type="primary" icon={<ThunderboltOutlined />}>
          生成 AI 评估报告
        </Button>
      </Header>
      <Content className="page-content">
        {/* 总体评分 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <Card className="overall-card" size="small">
              <div className="overall-content">
                <Text type="secondary">综合评级</Text>
                <div className="rating-display">
                  <Rate disabled defaultValue={4.5} allowHalf character={<TrophyOutlined />} />
                </div>
                <Text strong style={{ fontSize: 24 }}>{performanceData.overall.rating} / 5.0</Text>
                <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                  超过 {performanceData.overall.percentile}% 的员工
                </Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card className="overall-card" size="small">
              <div className="overall-content">
                <Text type="secondary">综合得分</Text>
                <div className="score-display">
                  <Progress
                    type="dashboard"
                    percent={performanceData.overall.score}
                    strokeColor={{
                      '0%': '#722ed1',
                      '100%': '#1890ff',
                    }}
                  />
                </div>
                <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                  较上季度 +2 分
                </Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card className="overall-card" size="small">
              <div className="overall-content">
                <Text type="secondary">绩效趋势</Text>
                <div className="trend-display">
                  {performanceData.overall.trend === 'up' ? (
                    <RiseOutlined className="trend-icon-up" />
                  ) : (
                    <FallOutlined className="trend-icon-down" />
                  )}
                  <Text strong className="trend-text">
                    {performanceData.overall.trend === 'up' ? '持续上升' : '需要关注'}
                  </Text>
                </div>
                <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                  连续 4 个季度增长
                </Text>
              </div>
            </Card>
          </Col>
        </Row>

        {/* 图表区域 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}>
            <Card title="绩效趋势" size="small">
              <ReactECharts option={trendChartOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="能力雷达图" size="small">
              <ReactECharts option={radarChartOption} style={{ height: 300 }} />
            </Card>
          </Col>
        </Row>

        {/* 详细分析 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="各维度表现" size="small">
              <Table
                columns={dimensionColumns}
                dataSource={performanceData.dimensions}
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="主要成就" size="small">
              <Timeline
                items={performanceData.achievements.map((achievement, index) => ({
                  color: achievement.impact === 'high' ? '#52c41a' : '#1890ff',
                  children: (
                    <div className="achievement-item">
                      <Text strong>{achievement.title}</Text>
                      <div className="achievement-meta">
                        <Tag color={achievement.impact === 'high' ? 'green' : 'blue'}>
                          {achievement.impact === 'high' ? '高影响' : '中等影响'}
                        </Tag>
                        <Text type="secondary">{achievement.date}</Text>
                      </div>
                    </div>
                  ),
                }))}
              />
            </Card>
          </Col>
        </Row>

        {/* 改进建议 */}
        <Card title="AI 改进建议" size="small" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            {performanceData.improvements.map((item, index) => (
              <Col xs={24} sm={8} key={index}>
                <Card className="improvement-card" size="small">
                  <div className="improvement-header">
                    <ExclamationCircleOutlined className="improvement-icon" />
                    <Text strong>{item.area}</Text>
                    <Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'blue'}>
                      {item.priority === 'high' ? '优先' : item.priority === 'medium' ? '中等' : '建议'}
                    </Tag>
                  </div>
                  <Text type="secondary">{item.suggestion}</Text>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      </Content>
    </Layout>
  );
};

export default PerformanceReview;
