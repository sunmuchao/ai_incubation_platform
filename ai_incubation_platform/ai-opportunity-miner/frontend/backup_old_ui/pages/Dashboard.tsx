import { Card, Col, Row, Statistic, Table, Tag, Progress } from 'antd'
import {
  ArrowUpOutlined,
  FileTextOutlined,
  BellOutlined,
  UserOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'

function Dashboard() {
  const statsData = [
    { title: '今日事件总数', value: 2847, icon: <ArrowUpOutlined />, color: '#722ed1' },
    { title: '企业事件', value: 1205, icon: <UserOutlined />, color: '#1890ff' },
    { title: '专利事件', value: 856, icon: <FileTextOutlined />, color: '#52c41a' },
    { title: '新闻事件', value: 786, icon: <BellOutlined />, color: '#faad14' },
  ]

  const eventData = [
    { key: '1', type: '企业融资', company: '某科技公司', amount: 'B 轮 5000 万', time: '10 分钟前', priority: 'high' },
    { key: '2', type: '专利公开', company: '某制药公司', patent: 'CN202410001', time: '15 分钟前', priority: 'normal' },
    { key: '3', type: '新闻发布', company: '某汽车公司', title: '新品发布会', time: '20 分钟前', priority: 'normal' },
    { key: '4', type: '企业融资', company: '某生物公司', amount: 'A 轮 2000 万', time: '30 分钟前', priority: 'high' },
    { key: '5', type: '专利授权', company: '某电子公司', patent: 'CN202410002', time: '1 小时前', priority: 'low' },
  ]

  const eventColumns = [
    { title: '事件类型', dataIndex: 'type', key: 'type' },
    { title: '主体', dataIndex: 'company', key: 'company' },
    { 
      title: '详情', 
      dataIndex: 'amount', 
      key: 'amount',
      render: (text: string, record: any) => text || record.patent || record.title
    },
    { title: '时间', dataIndex: 'time', key: 'time' },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => {
        const colorMap: Record<string, string> = { high: 'red', normal: 'blue', low: 'gray' }
        const textMap: Record<string, string> = { high: '高', normal: '中', low: '低' }
        return <Tag color={colorMap[priority]}>{textMap[priority]}</Tag>
      }
    },
  ]

  const streamStats = [
    { name: '企业数据流', count: 1205, health: 98 },
    { name: '专利数据流', count: 856, health: 95 },
    { name: '新闻数据流', count: 786, health: 92 },
    { name: '社交媒体流', count: 342, health: 88 },
  ]

  return (
    <div>
      <Row gutter={16}>
        {statsData.map((stat, index) => (
          <Col span={6} key={index}>
            <Card>
              <Statistic
                title={stat.title}
                value={stat.value}
                valueStyle={{ color: stat.color }}
                prefix={stat.icon}
              />
            </Card>
          </Col>
        ))}
      </Row>
      
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={16}>
          <Card title="实时事件流" style={{ height: '100%' }}>
            <Table columns={eventColumns} dataSource={eventData} pagination={false} size="small" />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="数据流健康度" style={{ height: '100%' }}>
            {streamStats.map((stream, index) => (
              <div key={index} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>{stream.name}</span>
                  <span style={{ color: stream.health >= 95 ? '#52c41a' : stream.health >= 90 ? '#faad14' : '#ff4d4f' }}>
                    {stream.health}%
                  </span>
                </div>
                <Progress percent={stream.health} showInfo={false} strokeColor={stream.health >= 95 ? '#52c41a' : stream.health >= 90 ? '#faad14' : '#ff4d4f'} />
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4 }}>
                  今日处理：{stream.count} 条
                </div>
              </div>
            ))}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
