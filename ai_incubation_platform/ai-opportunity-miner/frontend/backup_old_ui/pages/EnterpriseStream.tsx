import { Table, Tag, Card, Input, Button, Space, Badge } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useState } from 'react'

function EnterpriseStream() {
  const [searchText, setSearchText] = useState('')

  const enterpriseData = [
    { key: '1', event: '企业注册', name: '某科技有限公司', time: '2024-01-15 10:30', status: 'new', funding: '-' },
    { key: '2', event: '企业融资', name: '某生物制药公司', time: '2024-01-15 09:45', status: 'hot', funding: 'B 轮 5000 万' },
    { key: '3', event: '信息变更', name: '某网络科技公司', time: '2024-01-15 09:15', status: 'update', funding: '-' },
    { key: '4', event: '企业融资', name: '某人工智能公司', time: '2024-01-15 08:30', status: 'hot', funding: 'A 轮 3000 万' },
    { key: '5', event: '企业年报', name: '某智能制造公司', time: '2024-01-15 08:00', status: 'normal', funding: '-' },
  ]

  const columns = [
    { title: '事件类型', dataIndex: 'event', key: 'event' },
    { title: '企业名称', dataIndex: 'name', key: 'name' },
    { title: '融资金额', dataIndex: 'funding', key: 'funding' },
    { title: '时间', dataIndex: 'time', key: 'time' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; text: string }> = {
          new: { color: 'green', text: '新增' },
          hot: { color: 'red', text: '热门' },
          update: { color: 'blue', text: '更新' },
          normal: { color: 'gray', text: '正常' },
        }
        const { color, text } = config[status] || { color: 'default', text: status }
        return <Tag color={color}>{text}</Tag>
      }
    },
  ]

  return (
    <div>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索企业名称"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Button icon={<ReloadOutlined />}>刷新</Button>
        </Space>
        <Table 
          columns={columns} 
          dataSource={enterpriseData} 
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
        />
      </Card>
    </div>
  )
}

export default EnterpriseStream
