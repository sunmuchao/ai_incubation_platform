import React from 'react';
import { Card, Row, Col, Progress, Table, Tag, Button, Alert, Badge } from 'antd';
import ReactECharts from 'echarts-for-react';

// 模拟预测性维护数据
const mockHealthScores = [
  { key: '1', service: 'api-gateway', score: 95, trend: 'stable', risk: '低' },
  { key: '2', service: 'user-service', score: 88, trend: 'improving', risk: '低' },
  { key: '3', service: 'payment-service', score: 65, trend: 'degrading', risk: '中' },
  { key: '4', service: 'order-service', score: 92, trend: 'stable', risk: '低' },
  { key: '5', service: 'inventory-db', score: 35, trend: 'degrading', risk: '高' },
];

const mockPredictiveAlerts = [
  {
    key: '1',
    service: 'inventory-db',
    event: '连接池耗尽',
    predictedTime: '6 小时后',
    probability: 0.87,
    severity: 'high',
  },
  {
    key: '2',
    service: 'payment-service',
    event: '内存溢出',
    predictedTime: '12 小时后',
    probability: 0.72,
    severity: 'medium',
  },
  {
    key: '3',
    service: 'cache-redis',
    event: '命中率下降',
    predictedTime: '24 小时后',
    probability: 0.65,
    severity: 'low',
  },
];

const Predictive: React.FC = () => {
  // 健康趋势图
  const healthTrendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['api-gateway', 'payment-service', 'inventory-db'], textStyle: { color: '#fff' } },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
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
      { name: 'api-gateway', type: 'line', smooth: true, data: [92, 94, 93, 95, 94, 96, 95], itemStyle: { color: '#52c41a' } },
      { name: 'payment-service', type: 'line', smooth: true, data: [78, 75, 72, 68, 65, 62, 60], itemStyle: { color: '#faad14' } },
      { name: 'inventory-db', type: 'line', smooth: true, data: [55, 50, 45, 40, 38, 35, 32], itemStyle: { color: '#ff4d4f' } },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  // RUL 预测图
  const rulOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['DB 连接池', '支付内存', '订单线程池'],
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)', rotate: 15 },
    },
    yAxis: {
      type: 'value',
      name: '剩余寿命 (小时)',
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      {
        type: 'bar',
        data: [48, 120, 200],
        itemStyle: {
          color: new (window as any).echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#1890ff' },
            { offset: 1, color: '#722ed1' },
          ]),
        },
        label: { show: true, position: 'top', color: '#fff' },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  const healthColumns = [
    { title: '服务名称', dataIndex: 'service', key: 'service' },
    {
      title: '健康分',
      dataIndex: 'score',
      key: 'score',
      render: (score: number) => (
        <Progress
          percent={score}
          strokeColor={score > 80 ? '#52c41a' : score > 50 ? '#faad14' : '#ff4d4f'}
          trailColor="#303030"
          size="small"
          format={() => score}
        />
      ),
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      render: (trend: string) => {
        const config = {
          improving: { color: '#52c41a', text: '改善' },
          stable: { color: '#1890ff', text: '稳定' },
          degrading: { color: '#ff4d4f', text: '恶化' },
        }[trend];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      },
    },
    {
      title: '风险等级',
      dataIndex: 'risk',
      key: 'risk',
      render: (risk: string) => {
        const color = { 高: 'red', 中: 'orange', 低: 'green' }[risk];
        return <Tag color={color}>{risk}</Tag>;
      },
    },
  ];

  const alertColumns = [
    { title: '服务', dataIndex: 'service', key: 'service' },
    { title: '预测事件', dataIndex: 'event', key: 'event' },
    { title: '预计时间', dataIndex: 'predictedTime', key: 'predictedTime' },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'probability',
      render: (val: number) => (
        <span style={{ color: val > 0.8 ? '#ff4d4f' : val > 0.6 ? '#faad14' : '#1890ff' }}>
          {(val * 100).toFixed(0)}%
        </span>
      ),
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (sev: string) => {
        const color = { high: 'red', medium: 'orange', low: 'blue' }[sev];
        return <Badge color={color} />;
      },
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>预测性维护</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          基于 LSTM 时序预测的故障预警和剩余寿命预测
        </p>
      </div>

      <Alert
        message="预测性告警"
        description="检测到 inventory-db 连接池可能在 6 小时后耗尽，建议提前进行维护"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        action={
          <Button size="small" type="primary">
            创建维护计划
          </Button>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="健康评分趋势">
            <div style={{ height: 300 }}>
              <ReactECharts option={healthTrendOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="剩余寿命预测 (RUL)">
            <div style={{ height: 300 }}>
              <ReactECharts option={rulOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="服务健康度">
            <Table columns={healthColumns} dataSource={mockHealthScores} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="预测性告警">
            <Table columns={alertColumns} dataSource={mockPredictiveAlerts} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Predictive;
