import { Table, Tag, DatePicker, Space, Button } from 'antd'
import { SearchOutlined } from '@ant-design/icons'

function MatchHistory() {
  const historyData = [
    { key: '1', candidate: '张三', position: '高级前端工程师', company: '某某科技', matchDate: '2024-01-15', status: '成功', score: 95 },
    { key: '2', candidate: '李四', position: 'Java 开发工程师', company: '某某网络', matchDate: '2024-01-14', status: '成功', score: 92 },
    { key: '3', candidate: '王五', position: '产品经理', company: '某某创新', matchDate: '2024-01-13', status: '失败', score: 65 },
    { key: '4', candidate: '赵六', position: 'UI 设计师', company: '某某设计', matchDate: '2024-01-12', status: '成功', score: 88 },
    { key: '5', candidate: '孙七', position: '数据分析师', company: '某某数据', matchDate: '2024-01-11', status: '成功', score: 91 },
  ]

  const columns = [
    { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
    { title: '职位', dataIndex: 'position', key: 'position' },
    { title: '公司', dataIndex: 'company', key: 'company' },
    { title: '匹配日期', dataIndex: 'matchDate', key: 'matchDate' },
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
          '失败': 'red',
          '进行中': 'blue',
        }
        return <Tag color={colorMap[status]}>{status}</Tag>
      }
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <DatePicker.RangePicker />
        <Button type="primary" icon={<SearchOutlined />}>
          搜索
        </Button>
      </Space>
      <Table columns={columns} dataSource={historyData} pagination={{ pageSize: 10 }} />
    </div>
  )
}

export default MatchHistory
