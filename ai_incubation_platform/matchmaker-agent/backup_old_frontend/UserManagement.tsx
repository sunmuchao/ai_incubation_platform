import { Table, Tag, Button, Space } from 'antd'
import { EditOutlined, DeleteOutlined } from '@ant-design/icons'

function UserManagement() {
  const userData = [
    { key: '1', name: '张三', email: 'zhangsan@example.com', role: '求职者', status: 'active', skills: 'React, TypeScript, Node.js' },
    { key: '2', name: '李四', email: 'lisi@example.com', role: '招聘方', status: 'active', skills: 'Java, Spring Boot, MySQL' },
    { key: '3', name: '王五', email: 'wangwu@example.com', role: '求职者', status: 'inactive', skills: 'Python, Django, PostgreSQL' },
    { key: '4', name: '赵六', email: 'zhaoliu@example.com', role: '求职者', status: 'active', skills: 'UI/UX, Figma, Sketch' },
  ]

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '角色', dataIndex: 'role', key: 'role' },
    { title: '技能', dataIndex: 'skills', key: 'skills' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status === 'active' ? '活跃' : '不活跃'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" icon={<EditOutlined />} />
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Space>
      )
    },
  ]

  return (
    <div>
      <Table columns={columns} dataSource={userData} pagination={{ pageSize: 10 }} />
    </div>
  )
}

export default UserManagement
