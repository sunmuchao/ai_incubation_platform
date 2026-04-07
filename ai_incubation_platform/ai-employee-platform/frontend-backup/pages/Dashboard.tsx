/**
 * 工作台页面
 */
import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Tag, Progress, Space, Typography } from 'antd';
import {
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { StatCard, ChartCard } from '@/components';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const [_loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalEmployees: 0,
    availableEmployees: 0,
    totalHours: 0,
    totalRevenue: 0,
    avgRating: 0,
  });

  // 获取统计数据
  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      try {
        // 这里可以调用实际的 API
        setStats({
          totalEmployees: 24,
          availableEmployees: 18,
          totalHours: 1280,
          totalRevenue: 45600,
          avgRating: 4.6,
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // 员工状态数据
  const employeeStatusData = {
    legend: { data: ['可雇佣', '工作中', '不可用'] },
    series: [{
      type: 'pie',
      radius: ['50%', '60%'],
      data: [
        { name: '可雇佣', value: stats.availableEmployees },
        { name: '工作中', value: 4 },
        { name: '不可用', value: 2 },
      ],
    }],
  };

  // 收入趋势数据
  const revenueTrendData = {
    xAxis: { data: ['1 月', '2 月', '3 月', '4 月', '5 月', '6 月'] },
    series: [{
      type: 'line',
      data: [12000, 15000, 18000, 22000, 28000, stats.totalRevenue],
      smooth: true,
    }],
  };

  // 热门员工表格
  const topEmployeesColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank: number) => {
        const colors = ['#ff4d4f', '#faad14', '#52c41a'];
        return (
          <span
            style={{
              display: 'inline-block',
              width: 24,
              height: 24,
              lineHeight: '24px',
              textAlign: 'center',
              borderRadius: '50%',
              backgroundColor: colors[rank - 1] || '#d9d9d9',
              color: rank <= 3 ? '#fff' : '#666',
              fontWeight: rank <= 3 ? 'bold' : 'normal',
            }}
          >
            {rank}
          </span>
        );
      },
    },
    {
      title: '员工名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '技能',
      dataIndex: 'skills',
      key: 'skills',
      render: (skills: Record<string, string>) => (
        <Space wrap>
          {Object.keys(skills).slice(0, 3).map((skill) => (
            <Tag key={skill} color="blue">
              {skill}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      render: (rating: number) => `${rating.toFixed(1)} ⭐`,
    },
    {
      title: '收入',
      dataIndex: 'revenue',
      key: 'revenue',
      render: (revenue: number) => `¥${revenue.toLocaleString()}`,
    },
  ];

  const topEmployeesData = [
    { key: '1', rank: 1, name: '数据分析助手', skills: { Python: 'expert', SQL: 'advanced' }, rating: 4.9, revenue: 15600 },
    { key: '2', rank: 2, name: '客服机器人', skills: { '沟通': 'expert', '多语言': 'advanced' }, rating: 4.8, revenue: 12800 },
    { key: '3', rank: 3, name: '代码审查助手', skills: { CodeReview: 'expert', Security: 'advanced' }, rating: 4.8, revenue: 11200 },
    { key: '4', rank: 4, name: '文档生成器', skills: { Writing: 'advanced', TechDoc: 'intermediate' }, rating: 4.7, revenue: 9600 },
    { key: '5', rank: 5, name: '图像识别专家', skills: { CV: 'expert', PyTorch: 'advanced' }, rating: 4.6, revenue: 8400 },
  ];

  // 任务完成情况
  const taskColumns = [
    {
      title: '任务类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '完成数',
      dataIndex: 'completed',
      key: 'completed',
    },
    {
      title: '进行中',
      dataIndex: 'inProgress',
      key: 'inProgress',
    },
    {
      title: '完成率',
      dataIndex: 'rate',
      key: 'rate',
      render: (rate: number) => <Progress percent={rate} size="small" strokeColor={rate >= 90 ? '#52c41a' : rate >= 70 ? '#faad14' : '#ff4d4f'} />,
    },
  ];

  const taskData = [
    { key: '1', type: '数据分析', completed: 156, inProgress: 8, rate: 95 },
    { key: '2', type: '内容创作', completed: 89, inProgress: 12, rate: 88 },
    { key: '3', type: '代码开发', completed: 67, inProgress: 15, rate: 82 },
    { key: '4', type: '客户服务', completed: 234, inProgress: 6, rate: 97 },
  ];

  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>工作台</Title>
        <p style={{ color: '#666', margin: 0 }}>
          欢迎回来，这里是您的 AI 员工管理平台
        </p>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="AI 员工总数"
            value={stats.totalEmployees}
            suffix="人"
            prefix={<TeamOutlined style={{ color: '#1890ff' }} />}
            trend={12}
            trendType="up"
            progress={(stats.availableEmployees / stats.totalEmployees) * 100}
            progressColor="#1890ff"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="可雇佣员工"
            value={stats.availableEmployees}
            suffix="人"
            prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            trend={8}
            trendType="up"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="总工作时长"
            value={stats.totalHours}
            suffix="小时"
            prefix={<ClockCircleOutlined style={{ color: '#faad14' }} />}
            trend={25}
            trendType="up"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="总收入"
            value={stats.totalRevenue.toLocaleString()}
            prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
            trend={18}
            trendType="up"
          />
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <ChartCard
            title="员工状态分布"
            option={employeeStatusData}
            height={280}
          />
        </Col>
        <Col xs={24} lg={12}>
          <ChartCard
            title="月收入趋势"
            option={revenueTrendData}
            height={280}
          />
        </Col>
      </Row>

      {/* 表格区域 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="热门员工 Top 5" bordered={false}>
            <Table
              columns={topEmployeesColumns}
              dataSource={topEmployeesData}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="任务完成情况" bordered={false}>
            <Table
              columns={taskColumns}
              dataSource={taskData}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
