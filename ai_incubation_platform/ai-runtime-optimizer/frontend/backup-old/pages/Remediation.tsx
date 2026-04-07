import React, { useState } from 'react';
import { Card, Row, Col, Table, Button, Modal, Steps, Tag, Alert } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';

// 模拟修复脚本数据
const mockScripts = [
  {
    key: '1',
    id: 'restart-service',
    name: '重启服务',
    category: '服务恢复',
    riskLevel: 'low',
    description: '安全重启目标服务实例',
    autoApproved: true,
  },
  {
    key: '2',
    id: 'scale-up',
    name: '扩容实例',
    category: '容量调整',
    riskLevel: 'medium',
    description: '增加服务实例数量',
    autoApproved: false,
  },
  {
    key: '3',
    id: 'clear-cache',
    name: '清理缓存',
    category: '性能优化',
    riskLevel: 'low',
    description: '清理 Redis 缓存数据',
    autoApproved: true,
  },
  {
    key: '4',
    id: 'db-connection-reset',
    name: '重置数据库连接',
    category: '数据库',
    riskLevel: 'high',
    description: '重置数据库连接池',
    autoApproved: false,
  },
];

const mockExecutions = [
  {
    key: '1',
    script: 'restart-service',
    service: 'payment-service',
    status: 'completed',
    result: '成功',
    time: '2024-01-15 10:30:00',
  },
  {
    key: '2',
    script: 'scale-up',
    service: 'order-service',
    status: 'running',
    result: '-',
    time: '2024-01-15 11:00:00',
  },
  {
    key: '3',
    script: 'clear-cache',
    service: 'user-service',
    status: 'failed',
    result: '超时',
    time: '2024-01-15 09:15:00',
  },
];

const Remediation: React.FC = () => {
  const [executionModal, setExecutionModal] = useState(false);

  const handleExecute = (_scriptId: string) => {
    setExecutionModal(true);
  };

  const columns = [
    { title: '脚本名称', dataIndex: 'name', key: 'name' },
    { title: '类别', dataIndex: 'category', key: 'category' },
    {
      title: '风险等级',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      render: (level: string) => {
        const color = { low: 'green', medium: 'orange', high: 'red' }[level];
        return <Tag color={color}>{level}</Tag>;
      },
    },
    {
      title: '自动审批',
      dataIndex: 'autoApproved',
      key: 'autoApproved',
      render: (approved: boolean) =>
        approved ? (
          <Tag icon={<CheckCircleOutlined />} color="success">是</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="warning">否</Tag>
        ),
    },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: typeof mockScripts[0]) => (
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => handleExecute(record.id)}
        >
          执行
        </Button>
      ),
    },
  ];

  const executionColumns = [
    { title: '脚本', dataIndex: 'script', key: 'script' },
    { title: '服务', dataIndex: 'service', key: 'service' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = {
          completed: { color: '#52c41a', text: '完成' },
          running: { color: '#1890ff', text: '执行中' },
          failed: { color: '#ff4d4f', text: '失败' },
        }[status];
        return <Tag color={config?.color}>{config?.text}</Tag>;
      },
    },
    { title: '结果', dataIndex: 'result', key: 'result' },
    { title: '时间', dataIndex: 'time', key: 'time' },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>自主修复</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          安全可控的自动化修复执行引擎
        </p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="修复脚本库">
            <Table columns={columns} dataSource={mockScripts} pagination={false} size="small" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="执行历史">
            <Table columns={executionColumns} dataSource={mockExecutions} pagination={false} size="small" />
          </Card>
        </Col>
      </Row>

      <Modal
        title="执行修复脚本"
        open={executionModal}
        onCancel={() => setExecutionModal(false)}
        footer={[
          <Button key="cancel" onClick={() => setExecutionModal(false)}>取消</Button>,
          <Button key="execute" type="primary" onClick={() => setExecutionModal(false)}>确认执行</Button>,
        ]}
      >
        <Steps
          current={1}
          items={[
            { title: '审批', status: 'finish' },
            { title: '创建快照', status: 'process' },
            { title: '执行', status: 'wait' },
            { title: '验证', status: 'wait' },
          ]}
          style={{ marginBottom: 24 }}
        />
        <Alert
          message="安全提示"
          description="执行前将自动创建服务快照，支持一键回滚"
          type="info"
          showIcon
        />
      </Modal>
    </div>
  );
};

export default Remediation;
