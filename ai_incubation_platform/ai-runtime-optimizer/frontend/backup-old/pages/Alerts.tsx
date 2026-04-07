import React, { useState } from 'react';
import { Card, Row, Col, Table, Tag, Button, Space, Input, Badge, Modal } from 'antd';
import { CheckOutlined } from '@ant-design/icons';

// 模拟告警数据
const mockAlerts = [
  {
    key: '1',
    service: 'inventory-db',
    type: '高延迟告警',
    severity: 'critical',
    message: '平均延迟超过阈值 (890ms > 200ms)',
    time: '2 分钟前',
    acknowledged: false,
  },
  {
    key: '2',
    service: 'payment-service',
    type: '错误率告警',
    severity: 'high',
    message: '错误率超过阈值 (1.2% > 0.5%)',
    time: '5 分钟前',
    acknowledged: false,
  },
  {
    key: '3',
    service: 'api-gateway',
    type: 'CPU 使用率告警',
    severity: 'medium',
    message: 'CPU 使用率超过 80%',
    time: '15 分钟前',
    acknowledged: true,
  },
  {
    key: '4',
    service: 'user-service',
    type: '内存告警',
    severity: 'low',
    message: '内存使用率达到 75%',
    time: '30 分钟前',
    acknowledged: true,
  },
];

// 模拟告警规则
const mockRules = [
  { key: '1', name: '高延迟检测', metric: 'latency_p99', threshold: 200, severity: 'critical' },
  { key: '2', name: '错误率检测', metric: 'error_rate', threshold: 0.5, severity: 'high' },
  { key: '3', name: 'CPU 告警', metric: 'cpu_percent', threshold: 80, severity: 'medium' },
  { key: '4', name: '内存告警', metric: 'memory_percent', threshold: 85, severity: 'medium' },
];

const Alerts: React.FC = () => {
  const [acknowledgeModal, setAcknowledgeModal] = useState(false);

  const handleAcknowledge = (_alertId: string) => {
    setAcknowledgeModal(true);
  };

  const columns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (sev: string) => {
        const config = {
          critical: { color: 'red', text: '严重' },
          high: { color: 'orange', text: '高' },
          medium: { color: 'yellow', text: '中' },
          low: { color: 'blue', text: '低' },
        }[sev];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      },
    },
    { title: '服务', dataIndex: 'service', key: 'service' },
    { title: '类型', dataIndex: 'type', key: 'type' },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
    { title: '时间', dataIndex: 'time', key: 'time' },
    {
      title: '状态',
      dataIndex: 'acknowledged',
      key: 'acknowledged',
      width: 80,
      render: (ack: boolean) => (ack ? <Tag color="green">已确认</Tag> : <Badge count />),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: typeof mockAlerts[0]) => (
        <Space>
          {!record.acknowledged && (
            <Button
              type="link"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleAcknowledge(record.key)}
            >
              确认
            </Button>
          )}
          <Button type="link" size="small">详情</Button>
        </Space>
      ),
    },
  ];

  const ruleColumns = [
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '指标', dataIndex: 'metric', key: 'metric' },
    { title: '阈值', dataIndex: 'threshold', key: 'threshold' },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (sev: string) => {
        const color = { critical: 'red', high: 'orange', medium: 'yellow', low: 'blue' }[sev];
        return <Tag color={color}>{sev}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: () => <Button type="link" size="small">编辑</Button>,
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>告警管理</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          告警规则配置、通知管理和告警历史
        </p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title={`活跃告警 (${mockAlerts.filter(a => !a.acknowledged).length})`}>
            <Table columns={columns} dataSource={mockAlerts} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="告警规则">
            <Table columns={ruleColumns} dataSource={mockRules} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>

      <Modal
        title="确认告警"
        open={acknowledgeModal}
        onCancel={() => setAcknowledgeModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setAcknowledgeModal(false)}>取消</Button>,
          <Button key="confirm" type="primary" icon={<CheckOutlined />} onClick={() => setAcknowledgeModal(false)}>
            确认
          </Button>,
        ]}
      >
        <Input.TextArea placeholder="请输入确认备注（可选）" rows={4} />
      </Modal>
    </div>
  );
};

export default Alerts;
