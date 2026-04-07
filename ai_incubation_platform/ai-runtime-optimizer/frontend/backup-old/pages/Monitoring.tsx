import React, { useState } from 'react';
import { Card, Row, Col, Table, Space, Badge, Button, Select } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

// 模拟监控数据
const mockMetrics = [
  { time: '10:00', cpu: 45, memory: 62, latency: 120, errorRate: 0.2 },
  { time: '10:05', cpu: 52, memory: 65, latency: 135, errorRate: 0.3 },
  { time: '10:10', cpu: 68, memory: 70, latency: 180, errorRate: 0.5 },
  { time: '10:15', cpu: 75, memory: 72, latency: 220, errorRate: 0.8 },
  { time: '10:20', cpu: 82, memory: 75, latency: 280, errorRate: 1.2 },
  { time: '10:25', cpu: 78, memory: 73, latency: 250, errorRate: 0.9 },
  { time: '10:30', cpu: 65, memory: 68, latency: 160, errorRate: 0.4 },
];

const mockServices = [
  { key: '1', name: 'api-gateway', status: 'healthy', qps: 1250, latency: 45, errorRate: 0.1 },
  { key: '2', name: 'user-service', status: 'healthy', qps: 850, latency: 89, errorRate: 0.3 },
  { key: '3', name: 'payment-service', status: 'warning', qps: 320, latency: 350, errorRate: 1.2 },
  { key: '4', name: 'order-service', status: 'healthy', qps: 560, latency: 120, errorRate: 0.2 },
  { key: '5', name: 'inventory-db', status: 'critical', qps: 180, latency: 890, errorRate: 5.8 },
];

const Monitoring: React.FC = () => {
  const [selectedService, setSelectedService] = useState('all');

  // 指标趋势图
  const metricTrendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU %', 'Memory %', 'Latency ms'], textStyle: { color: '#fff' } },
    xAxis: {
      type: 'category',
      data: mockMetrics.map(m => m.time),
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
    },
    yAxis: [
      {
        type: 'value',
        name: '使用率 %',
        min: 0,
        max: 100,
        axisLine: { lineStyle: { color: '#303030' } },
        axisLabel: { color: 'rgba(255,255,255,0.65)' },
        splitLine: { lineStyle: { color: '#303030' } },
      },
      {
        type: 'value',
        name: '延迟 ms',
        axisLine: { lineStyle: { color: '#303030' } },
        axisLabel: { color: 'rgba(255,255,255,0.65)' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'CPU %',
        type: 'line',
        data: mockMetrics.map(m => m.cpu),
        itemStyle: { color: '#ff4d4f' },
      },
      {
        name: 'Memory %',
        type: 'line',
        data: mockMetrics.map(m => m.memory),
        itemStyle: { color: '#1890ff' },
      },
      {
        name: 'Latency ms',
        type: 'line',
        yAxisIndex: 1,
        data: mockMetrics.map(m => m.latency),
        itemStyle: { color: '#52c41a' },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  };

  // 错误率趋势
  const errorRateOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: mockMetrics.map(m => m.time),
      axisLine: { lineStyle: { color: '#303030' } },
      axisLabel: { color: 'rgba(255,255,255,0.65)' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '{value}%', color: 'rgba(255,255,255,0.65)' },
      axisLine: { lineStyle: { color: '#303030' } },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      {
        name: '错误率 %',
        type: 'line',
        smooth: true,
        data: mockMetrics.map(m => m.errorRate),
        itemStyle: { color: '#faad14' },
        areaStyle: {
          color: new (window as any).echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(250, 173, 20, 0.3)' },
            { offset: 1, color: 'rgba(250, 173, 20, 0.05)' },
          ]),
        },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
  };

  // 服务拓扑图
  const topologyOption = {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: { repulsion: 300, edgeLength: [100, 200] },
        data: [
          { id: '0', name: 'api-gateway', symbolSize: 80, value: 95, itemStyle: { color: '#52c41a' } },
          { id: '1', name: 'user-service', symbolSize: 60, value: 88, itemStyle: { color: '#52c41a' } },
          { id: '2', name: 'payment-service', symbolSize: 60, value: 65, itemStyle: { color: '#faad14' } },
          { id: '3', name: 'order-service', symbolSize: 60, value: 92, itemStyle: { color: '#52c41a' } },
          { id: '4', name: 'inventory-db', symbolSize: 70, value: 35, itemStyle: { color: '#ff4d4f' } },
          { id: '5', name: 'cache-redis', symbolSize: 50, value: 98, itemStyle: { color: '#52c41a' } },
        ],
        links: [
          { source: '0', target: '1' },
          { source: '0', target: '2' },
          { source: '0', target: '3' },
          { source: '1', target: '4' },
          { source: '2', target: '4' },
          { source: '3', target: '4' },
          { source: '0', target: '5' },
        ],
        label: { show: true, position: 'bottom', color: '#fff' },
        lineStyle: { color: '#303030', width: 2, curveness: 0.1 },
      },
    ],
  };

  const columns = [
    { title: '服务名称', dataIndex: 'name', key: 'name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          healthy: '#52c41a',
          warning: '#faad14',
          critical: '#ff4d4f',
        };
        return <Badge color={colorMap[status]} text={status} />;
      },
    },
    { title: 'QPS', dataIndex: 'qps', key: 'qps' },
    {
      title: '延迟 (ms)',
      dataIndex: 'latency',
      key: 'latency',
      render: (val: number) => (
        <span style={{ color: val > 200 ? '#ff4d4f' : val > 100 ? '#faad14' : '#52c41a' }}>
          {val}
        </span>
      ),
    },
    {
      title: '错误率 (%)',
      dataIndex: 'errorRate',
      key: 'errorRate',
      render: (val: number) => (
        <span style={{ color: val > 1 ? '#ff4d4f' : val > 0.5 ? '#faad14' : '#52c41a' }}>
          {val}%
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">详情</Button>
          <Button type="link" size="small">日志</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>运行态监控</h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>实时监控服务性能指标与健康状态</p>
        </div>
        <Space>
          <Select
            value={selectedService}
            onChange={setSelectedService}
            options={[
              { value: 'all', label: '全部服务' },
              { value: 'api-gateway', label: 'api-gateway' },
              { value: 'user-service', label: 'user-service' },
            ]}
            style={{ width: 150 }}
          />
          <Button icon={<ReloadOutlined />}>刷新</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="核心指标趋势">
            <div style={{ height: 350 }}>
              <ReactECharts option={metricTrendOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="错误率趋势">
            <div style={{ height: 350 }}>
              <ReactECharts option={errorRateOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="服务拓扑">
            <div style={{ height: 350 }}>
              <ReactECharts option={topologyOption} style={{ height: '100%' }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="服务列表">
            <Table columns={columns} dataSource={mockServices} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Monitoring;
