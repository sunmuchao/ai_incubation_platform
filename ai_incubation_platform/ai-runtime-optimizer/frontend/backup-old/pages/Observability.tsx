import React, { useState } from 'react';
import { Card, Row, Col, Input, Button, Table, Tag, Tabs, Typography, Select } from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';

const { Text } = Typography;

// 模拟日志数据
const mockLogs = [
  { key: '1', time: '2024-01-15 10:30:15.123', level: 'ERROR', service: 'inventory-db', message: 'Connection timeout after 30000ms', traceId: 'abc123' },
  { key: '2', time: '2024-01-15 10:30:14.456', level: 'WARN', service: 'payment-service', message: 'Slow query detected: 2500ms', traceId: 'abc123' },
  { key: '3', time: '2024-01-15 10:30:13.789', level: 'INFO', service: 'api-gateway', message: 'Request processed successfully', traceId: 'abc123' },
  { key: '4', time: '2024-01-15 10:30:12.012', level: 'DEBUG', service: 'user-service', message: 'Cache hit for user_123', traceId: 'def456' },
  { key: '5', time: '2024-01-15 10:30:11.345', level: 'ERROR', service: 'order-service', message: 'Failed to process order: validation error', traceId: 'ghi789' },
];

// 模拟日志模式
const mockPatterns = [
  { key: '1', pattern: 'Connection timeout after *ms', count: 156, severity: 'high' },
  { key: '2', pattern: 'Slow query detected: *ms', count: 89, severity: 'medium' },
  { key: '3', pattern: 'Failed to process order: *', count: 45, severity: 'high' },
  { key: '4', pattern: 'Cache * for *', count: 1250, severity: 'low' },
];

// 模拟追踪数据
const mockTraces = [
  { key: '1', traceId: 'abc123', service: 'api-gateway', operation: 'POST /api/payment', duration: 450, status: 'error' },
  { key: '2', traceId: 'def456', service: 'user-service', operation: 'GET /api/users/:id', duration: 85, status: 'ok' },
  { key: '3', traceId: 'ghi789', service: 'order-service', operation: 'POST /api/orders', duration: 320, status: 'error' },
];

const Observability: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');

  const logColumns = [
    { title: '时间', dataIndex: 'time', key: 'time', width: 200 },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: string) => {
        const color = { ERROR: 'red', WARN: 'orange', INFO: 'blue', DEBUG: 'gray' }[level];
        return <Tag color={color}>{level}</Tag>;
      },
    },
    { title: '服务', dataIndex: 'service', key: 'service', width: 150 },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
    { title: 'Trace ID', dataIndex: 'traceId', key: 'traceId', width: 100, render: (val: string) => <Text code>{val}</Text> },
  ];

  const patternColumns = [
    { title: '模式', dataIndex: 'pattern', key: 'pattern' },
    { title: '出现次数', dataIndex: 'count', key: 'count' },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (sev: string) => {
        const color = { high: 'red', medium: 'orange', low: 'green' }[sev];
        return <Tag color={color}>{sev}</Tag>;
      },
    },
  ];

  const traceColumns = [
    { title: 'Trace ID', dataIndex: 'traceId', key: 'traceId', width: 100, render: (val: string) => <Text code>{val}</Text> },
    { title: '服务', dataIndex: 'service', key: 'service', width: 150 },
    { title: '操作', dataIndex: 'operation', key: 'operation' },
    {
      title: '耗时 (ms)',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (val: number) => <span style={{ color: val > 200 ? '#ff4d4f' : '#52c41a' }}>{val}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={status === 'ok' ? 'green' : 'red'}>{status}</Tag>
      ),
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>可观测性</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          统一的日志、追踪、指标可观测性平台
        </p>
      </div>

      <Tabs
        defaultActiveKey="logs"
        items={[
          { key: 'logs', label: '日志查询' },
          { key: 'patterns', label: '日志模式' },
          { key: 'traces', label: '链路追踪' },
        ]}
      />

      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Input
          placeholder="搜索日志..."
          prefix={<SearchOutlined />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ width: 300 }}
        />
        <Select
          placeholder="日志级别"
          value={selectedLevel}
          onChange={setSelectedLevel}
          options={[
            { value: 'all', label: '全部' },
            { value: 'ERROR', label: 'ERROR' },
            { value: 'WARN', label: 'WARN' },
            { value: 'INFO', label: 'INFO' },
            { value: 'DEBUG', label: 'DEBUG' },
          ]}
          style={{ width: 120 }}
        />
        <Button icon={<FilterOutlined />}>过滤</Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="日志列表">
            <Table
              columns={logColumns}
              dataSource={mockLogs}
              pagination={{ pageSize: 5 }}
              size="small"
              scroll={{ x: 800 }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="错误模式 TOP5">
            <Table
              columns={patternColumns}
              dataSource={mockPatterns}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <div style={{ marginTop: 16 }}>
        <Card title="最近追踪">
          <Table columns={traceColumns} dataSource={mockTraces} pagination={false} size="small" />
        </Card>
      </div>
    </div>
  );
};

export default Observability;
