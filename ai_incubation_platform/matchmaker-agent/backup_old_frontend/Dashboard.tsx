import { Card, Col, Row, Statistic, Table, Tag } from 'antd'
import { UserOutlined, CheckCircleOutlined, SyncOutlined, ClockCircleOutlined } from '@ant-design/icons'

function Dashboard() {
  const statsData = [
    { title: '总用户数', value: 1280, icon: <UserOutlined />, color: '#1890ff' },
    { title: '成功匹配', value: 856, icon: <CheckCircleOutlined />, color: '#52c41a' },
    { title: '匹配中', value: 124, icon: <SyncOutlined spin />, color: '#faad14' },
    { title: '待处理', value: 36, icon: <ClockCircleOutlined />, color: '#722ed1' },
  ]

  const matchHistoryData = [
    { key: '1', candidate: '张三', position: '高级前端工程师', company: '某某科技', status: '成功', score: 95 },
    { key: '2', candidate: '李四', position: 'Java 开发工程师', company: '某某网络', status: '成功', score: 92 },
    { key: '3', candidate: '王五', position: '产品经理', company: '某某创新', status: '进行中', score: 88 },
    { key: '4', candidate: '赵六', position: 'UI 设计师', company: '某某设计', status: '待处理', score: 85 },
  ]

  const columns = [
    { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
    { title: '职位', dataIndex: 'position', key: 'position' },
    { title: '公司', dataIndex: 'company', key: 'company' },
    { 
      title: '匹配度', 
      dataIndex: 'score', 
      key: 'score',
      render: (score: number) => (
        <span style={{ color: score >= 90 ? '#52c41a' : score >= 80 ? '#faad14' : '#ff4d4f' }}>
          {score}%
        </span>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '成功': 'green',
          '进行中': 'blue',
          '待处理': 'orange',
        }
        return <Tag color={colorMap[status]}>{status}</Tag>
      }
    },
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
      <Card title="最近匹配记录" style={{ marginTop: 24 }}>
        <Table columns={columns} dataSource={matchHistoryData} pagination={false} />
      </Card>
    </div>
  )
}

export default Dashboard
