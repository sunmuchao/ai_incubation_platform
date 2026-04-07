import React, { useState } from 'react';
import { Card, Row, Col, Button, Table, Tag, Space, Timeline, Badge } from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

// 模拟根因分析数据
const mockRootCauses = [
  {
    key: '1',
    service: 'inventory-db',
    type: '数据库连接池耗尽',
    probability: 0.85,
    confidence: 0.92,
    evidence: ['连接数达到上限', '等待队列增长', '查询超时增加'],
  },
  {
    key: '2',
    service: 'payment-service',
    type: '下游依赖延迟',
    probability: 0.72,
    confidence: 0.78,
    evidence: ['外部 API 响应慢', '重试次数增加'],
  },
  {
    key: '3',
    service: 'api-gateway',
    type: '资源竞争',
    probability: 0.45,
    confidence: 0.61,
    evidence: ['CPU 使用率波动', '线程阻塞'],
  },
];

const mockAnalysisHistory = [
  { time: '2024-01-15 10:30:00', service: 'inventory-db', issue: '连接池耗尽', status: 'resolved' },
  { time: '2024-01-15 09:15:00', service: 'payment-service', issue: '超时增加', status: 'resolved' },
  { time: '2024-01-14 23:45:00', service: 'user-service', issue: '内存泄漏', status: 'resolved' },
];

const RootCause: React.FC = () => {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const handleAnalyze = () => {
    setAnalyzing(true);
    setTimeout(() => {
      setAnalyzing(false);
      setAnalysisComplete(true);
    }, 2000);
  };

  // 因果图配置
  const causalGraphOption = {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: { repulsion: 400, edgeLength: [150, 250], gravity: 0.1 },
        data: [
          { id: '0', name: 'api-gateway', symbolSize: 70, value: 'degraded', itemStyle: { color: '#faad14' } },
          { id: '1', name: 'user-service', symbolSize: 50, value: 'normal', itemStyle: { color: '#52c41a' } },
          { id: '2', name: 'payment-service', symbolSize: 60, value: 'degraded', itemStyle: { color: '#faad14' } },
          { id: '3', name: 'order-service', symbolSize: 50, value: 'normal', itemStyle: { color: '#52c41a' } },
          { id: '4', name: 'inventory-db', symbolSize: 80, value: 'failed', itemStyle: { color: '#ff4d4f' } },
          { id: '5', name: 'cache-redis', symbolSize: 40, value: 'normal', itemStyle: { color: '#52c41a' } },
        ],
        links: [
          { source: '0', target: '1', lineStyle: { width: 2 } },
          { source: '0', target: '2', lineStyle: { width: 3 } },
          { source: '0', target: '3', lineStyle: { width: 2 } },
          { source: '1', target: '4', lineStyle: { width: 4, type: 'dashed' } },
          { source: '2', target: '4', lineStyle: { width: 4, type: 'dashed' } },
          { source: '3', target: '4', lineStyle: { width: 3 } },
          { source: '0', target: '5', lineStyle: { width: 1 } },
        ],
        label: { show: true, position: 'bottom', color: '#fff' },
        lineStyle: { color: '#303030', curveness: 0.1 },
        emphasis: { focus: 'adjacency', lineStyle: { color: '#1890ff' } },
      },
    ],
  };

  // 置信度雷达图
  const confidenceRadarOption = {
    radar: {
      indicator: [
        { name: '统计置信', max: 1 },
        { name: '因果置信', max: 1 },
        { name: '时间置信', max: 1 },
        { name: '结构置信', max: 1 },
        { name: '一致性置信', max: 1 },
      ],
      axisName: { color: '#fff' },
      splitArea: { areaStyle: { color: ['#1a1a1a', '#141414', '#1a1a1a', '#141414'] } },
      splitLine: { lineStyle: { color: '#303030' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [0.92, 0.88, 0.95, 0.85, 0.9],
            name: 'inventory-db',
            itemStyle: { color: '#ff4d4f' },
            areaStyle: { color: 'rgba(255, 77, 79, 0.3)' },
          },
        ],
      },
    ],
  };

  const columns = [
    { title: '候选服务', dataIndex: 'service', key: 'service' },
    { title: '根因类型', dataIndex: 'type', key: 'type' },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'probability',
      render: (val: number) => (
        <Badge
          count={`${(val * 100).toFixed(0)}%`}
          style={{
            backgroundColor: val > 0.7 ? '#ff4d4f' : val > 0.5 ? '#faad14' : '#1890ff',
          }}
        />
      ),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (val: number) => <span style={{ color: '#1890ff' }}>{(val * 100).toFixed(0)}%</span>,
    },
    {
      title: '证据',
      dataIndex: 'evidence',
      key: 'evidence',
      render: (evidence: string[]) => (
        <Space direction="vertical" size={4}>
          {evidence.map((e, i) => (
            <Tag key={i} color="blue">{e}</Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, color: '#fff', margin: 0 }}>根因分析</h1>
        <p style={{ color: 'rgba(255,255,255,0.45)', marginTop: 8 }}>
          基于因果推断和贝叶斯网络的智能根因定位
        </p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<SearchOutlined />}
          size="large"
          onClick={handleAnalyze}
          loading={analyzing}
        >
          {analyzing ? '分析中...' : '开始根因分析'}
        </Button>
      </div>

      {analysisComplete && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} lg={16}>
              <Card title="因果图谱 - 红线路径为最可能根因链">
                <div style={{ height: 400 }}>
                  <ReactECharts option={causalGraphOption} style={{ height: '100%' }} />
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card title="根因置信度分析">
                <div style={{ height: 400 }}>
                  <ReactECharts option={confidenceRadarOption} style={{ height: '100%' }} />
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <Card title="根因假设列表">
                <Table columns={columns} dataSource={mockRootCauses} pagination={false} />
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card title="分析历史">
                <Timeline>
                  {mockAnalysisHistory.map((item, i) => (
                    <Timeline.Item key={i} color="green">
                      <div style={{ fontSize: 14, color: '#fff' }}>{item.service}</div>
                      <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
                        {item.issue}
                      </div>
                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>{item.time}</div>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </Card>
            </Col>
          </Row>
        </>
      )}

      {!analysisComplete && !analyzing && (
        <Card>
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <ThunderboltOutlined style={{ fontSize: 64, color: '#1890ff' }} />
            <p style={{ marginTop: 16, color: 'rgba(255,255,255,0.65)' }}>
              点击"开始根因分析"按钮进行智能诊断
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};

export default RootCause;
