import React from 'react';
import { Card, Row, Col, Table, Button, Space, Switch, Timeline } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';

// 模拟自动化任务数据
const mockAutomationTasks = [
  {
    key: '1',
    name: '自动扩缩容',
    description: '根据 CPU/内存使用率自动调整实例数',
    enabled: true,
    lastRun: '2024-01-15 10:00:00',
    status: 'success',
    nextRun: '2024-01-15 11:00:00',
  },
  {
    key: '2',
    name: '故障自动恢复',
    description: '检测到服务故障时自动重启',
    enabled: true,
    lastRun: '2024-01-15 08:30:00',
    status: 'success',
    nextRun: '-',
  },
  {
    key: '3',
    name: '日志归档',
    description: '每日凌晨归档历史日志',
    enabled: false,
    lastRun: '2024-01-15 02:00:00',
    status: 'success',
    nextRun: '2024-01-16 02:00:00',
  },
  {
    key: '4',
    name: '数据库备份',
    description: '每小时增量备份',
    enabled: true,
    lastRun: '2024-01-15 10:00:00',
    status: 'success',
    nextRun: '2024-01-15 11:00:00',
  },
];

// 模拟变更记录
const mockChangeHistory = [
  { time: '2024-01-15 10:00:00', type: '自动扩容', service: 'payment-service', status: 'success', details: '2 -> 4 实例' },
  { time: '2024-01-15 08:30:00', type: '故障恢复', service: 'order-service', status: 'success', details: '服务重启' },
  { time: '2024-01-15 02:00:00', type: '日志归档', service: 'all', status: 'success', details: '归档 1.2GB 日志' },
];

const Automation: React.FC = () => {
  const columns = [
    { title: '任务名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => <Switch checked={enabled} />,
    },
    {
      title: '最近执行',
      dataIndex: 'lastRun',
      key: 'lastRun',
      render: (time: string, record: typeof mockAutomationTasks[0]) => (
        <Space>
          <span>{time}</span>
          {record.status === 'success' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        </Space>
      ),
    },
    { title: '下次执行', dataIndex: 'nextRun', key: 'nextRun' },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">配置</Button>
          <Button type="link" size="small">执行记录</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>自动化中心</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          配置和管理自动化运维任务
        </p>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="自动化任务">
            <Table columns={columns} dataSource={mockAutomationTasks} pagination={false} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="变更历史">
            <Timeline>
              {mockChangeHistory.map((item, i) => (
                <Timeline.Item key={i} color="green">
                  <div style={{ fontSize: 14, color: '#fff' }}>{item.type}</div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
                    {item.service} - {item.details}
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>{item.time}</div>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Automation;
