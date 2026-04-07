import React, { useState } from 'react'
import { Typography, Table, Tag, Space, Button, Input, Select, Pagination, Spin, Empty } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useOrders } from '@/hooks/useApi'
import { useNavigate } from 'react-router-dom'
import type { Order } from '@/types'

const { Title } = Typography
const { Option } = Select

const OrdersPage: React.FC = () => {
  const navigate = useNavigate()
  const [filter, setFilter] = useState({
    status: '',
    keyword: '',
    page: 1,
    pageSize: 10,
  })
  const { data, isLoading } = useOrders(filter as any)

  const columns = [
    {
      title: '订单号',
      dataIndex: 'orderNo',
      key: 'orderNo',
      render: (text: string, record: Order) => (
        <Button type="link" onClick={() => navigate(`/orders/${record.id}`)}>
          {text || `#${record.id}`}
        </Button>
      ),
    },
    {
      title: '商品',
      dataIndex: ['product', 'name'],
      key: 'product',
      render: (text: string) => text || '未知商品',
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: '单价',
      dataIndex: 'unitPrice',
      key: 'unitPrice',
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '总额',
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      render: (amount: number) => `¥${amount.toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'warning',
          paid: 'processing',
          shipped: 'blue',
          completed: 'success',
          cancelled: 'error',
          refunded: 'default',
        }
        const textMap: Record<string, string> = {
          pending: '待支付',
          paid: '已支付',
          shipped: '已发货',
          completed: '已完成',
          cancelled: '已取消',
          refunded: '已退款',
        }
        return <Tag color={colorMap[status] || 'default'}>{textMap[status] || status}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (createdAt: string) => new Date(createdAt).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Order) => (
        <Space>
          <Button
            type="link"
            onClick={() => navigate(`/orders/${record.id}`)}
          >
            详情
          </Button>
          {record.status === 'pending' && (
            <Button type="link" danger>
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>订单管理</Title>

      <div className="card" style={{ marginBottom: 16 }}>
        <Space size="large">
          <div>
            <span style={{ marginRight: 8 }}>订单状态:</span>
            <Select
              style={{ width: 150 }}
              value={filter.status}
              onChange={(value) => setFilter({ ...filter, status: value, page: 1 })}
              allowClear
            >
              <Option value="pending">待支付</Option>
              <Option value="paid">已支付</Option>
              <Option value="shipped">已发货</Option>
              <Option value="completed">已完成</Option>
              <Option value="cancelled">已取消</Option>
              <Option value="refunded">已退款</Option>
            </Select>
          </div>
          <div>
            <Input
              placeholder="搜索订单号"
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              value={filter.keyword}
              onChange={(e) => setFilter({ ...filter, keyword: e.target.value, page: 1 })}
            />
          </div>
        </Space>
      </div>

      {isLoading ? (
        <Spin size="large" />
      ) : data?.items?.length ? (
        <>
          <Table
            columns={columns}
            dataSource={data.items}
            rowKey="id"
            pagination={false}
            scroll={{ x: 1000 }}
          />
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Pagination
              current={data.page}
              pageSize={data.pageSize}
              total={data.total}
              onChange={(page, pageSize) => setFilter({ ...filter, page, pageSize })}
              showSizeChanger
              showTotal={(total) => `共 ${total} 个订单`}
            />
          </div>
        </>
      ) : (
        <Empty description="暂无订单" style={{ marginTop: 48 }} />
      )}
    </div>
  )
}

export default OrdersPage
