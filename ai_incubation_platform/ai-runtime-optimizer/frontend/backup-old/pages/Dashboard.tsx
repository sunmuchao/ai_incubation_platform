import React from 'react';
import { Card, Row, Col, Statistic, Progress, Table, Space, Badge } from 'antd';
import {
  ArrowUpOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  BellOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

// 模拟数据 - 实际应从 API 获取
const mockDashboardData = {
  total_services: 12,
  healthy_services: 8,
  warning_services: 3,
  critical_services: 1,
  total_alerts: 24,
  active_alerts: 5,
  avg_health_score: 82.5,
  total_bottlenecks: 7,
  total_recommendations: 15,
};

const mockServices = [
  { key: '1', name: 'api-gateway', type: 'Gateway', status: 'healthy', healthScore: 95, latency: 45, errorRate: 0.1 },
  { key: '2', name: 'user-service', type: 'Service', status: 'healthy', healthScore: 88, latency: 120, errorRate: 0.3 },
  { key: '3', name: 'payment-service', type: 'Service', status: 'warning', healthScore: 65, latency: 350, errorRate: 1.2 },
  { key: '4', name: 'order-service', type: 'Service', status: 'healthy', healthScore: 92, latency: 89, errorRate: 0.2 },
  { key: '5', name: 'inventory-db', type: 'Database', status: 'critical', healthScore: 35, latency: 890, errorRate: 5.8 },
  { key: '6', name: 'cache-redis', type: 'Cache', status: 'healthy', healthScore: 98, latency: 12, errorRate: 0.01 },
];

const mockAlerts = [
  { key: '1', service: 'inventory-db', type: '高延迟', severity: 'critical', time: '2 分钟前' },
  { key: '2', service: 'payment-service', type: '错误率上升', severity: 'high', time: '5 分钟前' },
  { key: '3', service: 'api-gateway', type: 'CPU 使用率高', severity: 'medium', time: '15 分钟前' },
];

const Dashboard: React.FC = () => {
  // 健康趋势图表配置
  const healthTrendOption = {
    title: { text: '健康评分趋势', left: 'center', textStyle: { color: '#fff' } },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      {
        name: '平均健康分',
        type: 'line',
        smooth: true,
        data: [78, 82, 85, 83, 80, 82.5],
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
            { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
          ]),
        },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  // 服务状态分布图表
  const statusDistOption = {
    title: { text: '服务状态分布', left: 'center', textStyle: { color: '#fff' } },
    tooltip: { trigger: 'item' },
    series: [
      {
        name: '服务状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '55%'],
        itemStyle: {
          borderRadius: 8,
          borderColor: '#141414',
          borderWidth: 2,
        },
        label: { color: '#fff' },
        data: [
          { value: 8, name: '健康', itemStyle: { color: '#52c41a' } },
          { value: 3, name: '警告', itemStyle: { color: '#faad14' } },
          { value: 1, name: '严重', itemStyle: { color: '#ff4d4f' } },
        ],
      },
    ],
  };

  // 告警趋势图表
  const alertTrendOption = {
    title: { text: '告警趋势', left: 'center', textStyle: { color: '#fff' } },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      {
        name: '告警数',
        type: 'bar',
        data: [12, 8, 15, 6, 10, 18, 5],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#722ed1' },
            { offset: 1, color: '#1890ff' },
          ]),
        },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  const statusColumns = [
    { title: '服务名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'type', key: 'type' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = {
          healthy: { color: '#52c41a', icon: <CheckCircleOutlined /> },
          warning: { color: '#faad14', icon: <WarningOutlined /> },
          critical: { color: '#ff4d4f', icon: <CloseCircleOutlined /> },
        }[status];
        return (
          <Space>
            <span style={{ color: config?.color }}>{config?.icon}</span>
            <span style={{ color: config?.color, textTransform: 'capitalize' }}>{status}</span>
          </Space>
        );
      },
    },
    {
      title: '健康分',
      dataIndex: 'healthScore',
      key: 'healthScore',
      render: (score: number) => (
        <Progress
          percent={score}
          strokeColor={score > 80 ? '#52c41a' : score > 50 ? '#faad14' : '#ff4d4f'}
          trailColor="transparent"
          size="small"
          format={() => score}
        />
      ),
    },
    { title: '延迟 (ms)', dataIndex: 'latency', key: 'latency' },
    {
      title: '错误率 (%)',
      dataIndex: 'errorRate',
      key: 'errorRate',
      render: (rate: number) => (
        <span style={{ color: rate > 1 ? '#ff4d4f' : '#52c41a' }}>{rate}%</span>
      ),
    },
  ];

  const alertColumns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const color = { critical: 'red', high: 'orange', medium: 'gold', low: 'blue' }[severity];
        return <Badge color={color} />;
      },
    },
    { title: '服务', dataIndex: 'service', key: 'service' },
    { title: '类型', dataIndex: 'type', key: 'type' },
    { title: '时间', dataIndex: 'time', key: 'time' },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>
          Dashboard - 运行概览
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          实时监控 AI 运行态，智能诊断与优化建议
        </p>
      </div>

      {/* 核心指标卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="服务总数"
              value={mockDashboardData.total_services}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#fff' }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
              <span style={{ color: '#52c41a' }}>
                <ArrowUpOutlined /> 健康 {mockDashboardData.healthy_services}
              </span>
              <span style={{ marginLeft: 12, color: '#faad14' }}>
                <WarningOutlined /> 警告 {mockDashboardData.warning_services}
              </span>
              <span style={{ marginLeft: 12, color: '#ff4d4f' }}>
                <CloseCircleOutlined /> 严重 {mockDashboardData.critical_services}
              </span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均健康分"
              value={mockDashboardData.avg_health_score}
              suffix="/ 100"
              valueStyle={{ color: '#1890ff' }}
            />
            <Progress
              percent={mockDashboardData.avg_health_score}
              strokeColor="#1890ff"
              trailColor="#303030"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃告警"
              value={mockDashboardData.active_alerts}
              prefix={<BellOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
              总计 {mockDashboardData.total_alerts} 条告警
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="优化建议"
              value={mockDashboardData.total_recommendations}
              prefix={<RocketOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1' }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
              检测 {mockDashboardData.total_bottlenecks} 个瓶颈
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图表行 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card>
            <div style={{ height: 300 }}>
              <ReactECharts option={healthTrendOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card>
            <div style={{ height: 300 }}>
              <ReactECharts option={statusDistOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card>
            <div style={{ height: 300 }}>
              <ReactECharts option={alertTrendOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 服务状态和告警 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="服务状态">
            <Table
              columns={statusColumns}
              dataSource={mockServices}
              pagination={false}
              size="small"
              scroll={{ x: 600 }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="最近告警">
            <Table
              columns={alertColumns}
              dataSource={mockAlerts}
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
