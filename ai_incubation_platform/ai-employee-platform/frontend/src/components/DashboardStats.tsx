/**
 * 仪表盘统计组件
 * 展示用户整体情况概览
 */
import React from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Space, Tag } from 'antd';
import {
  TrophyOutlined,
  BookOutlined,
  TeamOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import './DashboardStats.less';

const { Title, Text } = Typography;

interface DashboardStatsProps {
  data?: {
    skills?: any[];
    performance_history?: any[];
    development_plans?: any[];
    total_earnings?: number;
    total_hours?: number;
    completed_projects?: number;
    [key: string]: any;
  };
}

const DashboardStats: React.FC<DashboardStatsProps> = ({ data }) => {
  const skillsCount = data?.skills?.length || 0;
  const performance = data?.performance_history?.[0];
  const plansCount = data?.development_plans?.length || 0;

  // 统计卡片数据
  const stats = [
    {
      title: '技能数量',
      value: skillsCount,
      suffix: '项',
      icon: <BookOutlined />,
      color: '#722ed1',
      trend: skillsCount > 5 ? 'up' : 'stable',
    },
    {
      title: '最新绩效',
      value: performance?.rating || 'N/A',
      suffix: performance ? '/5.0' : '',
      icon: <TrophyOutlined />,
      color: '#faad14',
      trend: performance?.trend === 'up' ? 'up' : 'stable',
    },
    {
      title: '发展计划',
      value: plansCount,
      suffix: '个',
      icon: <RiseOutlined />,
      color: '#1890ff',
    },
    {
      title: '总收入',
      value: data?.total_earnings || 0,
      prefix: '¥',
      icon: <DollarOutlined />,
      color: '#52c41a',
      precision: 0,
    },
  ];

  // 绩效趋势图
  const performanceData = data?.performance_history || [];
  const performanceChartOption = {
    xAxis: {
      type: 'category',
      data: performanceData.slice(0, 6).map((_: any, i: number) => `Q${i + 1}`),
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 5,
    },
    series: [
      {
        data: performanceData.slice(0, 6).map((p: any) => p?.rating || 0),
        type: 'line',
        smooth: true,
        areaStyle: {
          color: 'rgba(250, 173, 20, 0.3)',
        },
        lineStyle: {
          color: '#faad14',
          width: 3,
        },
        itemStyle: {
          color: '#faad14',
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

  // 技能分布饼图
  const skillCategories = data?.skills?.reduce((acc: any, skill: any) => {
    const category = skill.category || '其他';
    acc[category] = (acc[category] || 0) + 1;
    return acc;
  }, {}) || {};

  const pieChartOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        data: Object.entries(skillCategories).map(([name, value]: [string, any]) => ({
          name,
          value,
        })),
        color: ['#722ed1', '#1890ff', '#52c41a', '#faad14', '#ff4d4f'],
      },
    ],
  };

  return (
    <div className="dashboard-stats">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        {stats.map((stat, index) => (
          <Col xs={12} sm={6} key={index}>
            <Card size="small" className="stat-card">
              <div className="stat-icon" style={{ backgroundColor: stat.color }}>
                {stat.icon}
              </div>
              <div className="stat-content">
                <Text type="secondary" className="stat-title">
                  {stat.title}
                </Text>
                <div className="stat-value">
                  {stat.prefix}
                  <span>{stat.value}</span>
                  {stat.suffix && <span className="stat-suffix">{stat.suffix}</span>}
                </div>
                {stat.trend === 'up' && (
                  <Text type="success" className="stat-trend">
                    <RiseOutlined /> 提升
                  </Text>
                )}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card size="small" className="chart-card">
            <Title level={5}>绩效趋势</Title>
            <ReactECharts option={performanceChartOption} style={{ height: 250 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" className="chart-card">
            <Title level={5}>技能分布</Title>
            <ReactECharts option={pieChartOption} style={{ height: 250 }} />
          </Card>
        </Col>
      </Row>

      {/* 快速概览 */}
      <Card size="small" className="overview-card" style={{ marginTop: 16 }}>
        <Title level={5}>快速概览</Title>
        <Space wrap>
          <Tag icon={<CheckCircleOutlined />} color="green">
            活跃状态
          </Tag>
          <Tag icon={<ClockCircleOutlined />} color="blue">
            {data?.total_hours || 0} 工作时长
          </Tag>
          <Tag icon={<TeamOutlined />} color="purple">
            {data?.completed_projects || 0} 完成项目
          </Tag>
        </Space>
      </Card>
    </div>
  );
};

export default DashboardStats;
