import React from 'react';
import { Card, Row, Col, Table, Tag, Progress, Button, Statistic, Alert } from 'antd';
import { RocketOutlined, ArrowUpOutlined, DollarOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

// 模拟优化建议数据
const mockRecommendations = [
  {
    key: '1',
    service: 'payment-service',
    category: 'performance',
    priority: 'critical',
    title: '优化数据库查询',
    description: '检测到慢查询，建议添加索引',
    confidence: 0.92,
    estimatedImprovement: '40% 延迟降低',
  },
  {
    key: '2',
    service: 'user-service',
    category: 'resource',
    priority: 'high',
    title: '调整 JVM 堆内存',
    description: '当前配置不足以支撑峰值流量',
    confidence: 0.85,
    estimatedImprovement: '25% GC 减少',
  },
  {
    key: '3',
    service: 'order-service',
    category: 'cost',
    priority: 'medium',
    title: '降低冗余实例',
    description: '夜间流量低谷时可缩减实例',
    confidence: 0.78,
    estimatedImprovement: '￥2000/月节省',
  },
  {
    key: '4',
    service: 'api-gateway',
    category: 'reliability',
    priority: 'high',
    title: '增加熔断配置',
    description: '下游依赖故障时保护服务',
    confidence: 0.88,
    estimatedImprovement: '99.9% 可用性',
  },
];

const mockBottlenecks = [
  { key: '1', service: 'inventory-db', type: 'CPU 瓶颈', severity: 'critical', impact: '查询延迟增加 300%' },
  { key: '2', service: 'payment-service', type: '内存瓶颈', severity: 'high', impact: 'GC 频繁' },
  { key: '3', service: 'cache-redis', type: '网络延迟', severity: 'medium', impact: '缓存命中延迟增加' },
];

const Optimization: React.FC = () => {
  // 优化类别分布
  const categoryPieOption = {
    title: { text: '优化建议分布', left: 'center', textStyle: { color: '#fff' } },
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 8, borderColor: '#141414', borderWidth: 2 },
        label: { color: '#fff' },
        data: [
          { value: 12, name: '性能优化', itemStyle: { color: '#ff4d4f' } },
          { value: 8, name: '资源优化', itemStyle: { color: '#1890ff' } },
          { value: 5, name: '成本优化', itemStyle: { color: '#52c41a' } },
          { value: 3, name: '可靠性', itemStyle: { color: '#faad14' } },
        ],
      },
    ],
  };

  // 成本分析图
  const costOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['当前成本', '优化后', '节省'], textStyle: { color: '#fff' } },
    xAxis: {
      type: 'category',
      data: ['计算资源', '存储', '网络', '数据库'],
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
    },
    yAxis: {
      type: 'value',
      name: '元/月',
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      { name: '当前成本', type: 'bar', data: [5000, 3000, 2000, 4000], itemStyle: { color: '#69c0ff' } },
      { name: '优化后', type: 'bar', data: [3500, 2500, 1500, 3200], itemStyle: { color: '#1890ff' } },
      { name: '节省', type: 'bar', data: [1500, 500, 500, 800], itemStyle: { color: '#52c41a' } },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  const recommendationColumns = [
    { title: '服务', dataIndex: 'service', key: 'service' },
    { title: '标题', dataIndex: 'title', key: 'title' },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      render: (cat: string) => {
        const config = {
          performance: { color: 'red', text: '性能' },
          resource: { color: 'blue', text: '资源' },
          cost: { color: 'green', text: '成本' },
          reliability: { color: 'orange', text: '可靠性' },
        }[cat];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (pri: string) => {
        const color = { critical: 'red', high: 'orange', medium: 'blue', low: 'gray' }[pri];
        return <Tag color={color}>{pri}</Tag>;
      },
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (val: number) => <Progress percent={val * 100} size="small" strokeColor="#1890ff" trailColor="#303030" format={() => `${(val * 100).toFixed(0)}%`} />,
    },
    { title: '预估改进', dataIndex: 'estimatedImprovement', key: 'estimatedImprovement' },
    {
      title: '操作',
      key: 'action',
      render: () => <Button type="link" size="small">详情</Button>,
    },
  ];

  const bottleneckColumns = [
    { title: '服务', dataIndex: 'service', key: 'service' },
    { title: '瓶颈类型', dataIndex: 'type', key: 'type' },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (sev: string) => {
        const color = { critical: 'red', high: 'orange', medium: 'yellow', low: 'blue' }[sev];
        return <Tag color={color}>{sev}</Tag>;
      },
    },
    { title: '影响', dataIndex: 'impact', key: 'impact' },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>AI 优化建议</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          基于 AI 分析的智能优化建议和成本优化方案
        </p>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="优化建议总数"
              value={28}
              prefix={<RocketOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#fff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="关键问题"
              value={5}
              prefix={<ArrowUpOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="预估月节省"
              value={3300}
              prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均置信度"
              value={86}
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="优化建议列表">
            <Alert
              message="AI 已识别 5 个关键性能问题，建议优先处理"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table columns={recommendationColumns} dataSource={mockRecommendations} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="建议分布">
            <div style={{ height: 250 }}>
              <ReactECharts option={categoryPieOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="性能瓶颈检测">
            <Table columns={bottleneckColumns} dataSource={mockBottlenecks} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="成本分析">
            <div style={{ height: 250 }}>
              <ReactECharts option={costOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Optimization;
