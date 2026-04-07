import { Table, Tag, Card, Input, Button, Space, Select } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { useState } from 'react'

function PatentStream() {
  const [searchText, setSearchText] = useState('')
  const [patentType, setPatentType] = useState('all')

  const patentData = [
    { key: '1', patentNo: 'CN202410001234', title: '一种人工智能数据处理方法', type: '发明专利', status: '公开', company: '某科技有限公司', date: '2024-01-15' },
    { key: '2', patentNo: 'CN202420002345', title: '一种智能穿戴设备', type: '实用新型', status: '授权', company: '某电子公司', date: '2024-01-14' },
    { key: '3', patentNo: 'CN202430003456', title: '图形用户界面设计', type: '外观设计', status: '公开', company: '某设计公司', date: '2024-01-13' },
    { key: '4', patentNo: 'CN202410004567', title: '基于区块链的数据存储系统', type: '发明专利', status: '实审', company: '某区块链公司', date: '2024-01-12' },
    { key: '5', patentNo: 'CN202410005678', title: '一种新能源汽车电池管理系统', type: '发明专利', status: '授权', company: '某汽车公司', date: '2024-01-11' },
  ]

  const columns = [
    { title: '专利号', dataIndex: 'patentNo', key: 'patentNo' },
    { title: '专利名称', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', key: 'type' },
    { title: '申请人', dataIndex: 'company', key: 'company' },
    { title: '日期', dataIndex: 'date', key: 'date' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          '公开': 'blue',
          '授权': 'green',
          '实审': 'orange',
        }
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
      }
    },
  ]

  return (
    <div>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="搜索专利名称或专利号"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            value={patentType}
            onChange={setPatentType}
            style={{ width: 150 }}
            options={[
              { value: 'all', label: '全部类型' },
              { value: '发明专利', label: '发明专利' },
              { value: '实用新型', label: '实用新型' },
              { value: '外观设计', label: '外观设计' },
            ]}
          />
          <Button icon={<ReloadOutlined />}>刷新</Button>
        </Space>
        <Table 
          columns={columns} 
          dataSource={patentData} 
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}

export default PatentStream
