import React from 'react'
import { Typography, Row, Col, Card, Table, Tag, Button, theme } from 'antd'
import {
  ShoppingOutlined,
  TeamOutlined,
  FileTextOutlined,
  BarChartOutlined,
  DashboardOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useDashboardStats, useProducts, useOrders } from '@/hooks/useApi'

const { Title, Text } = Typography

const AdminDashboardPage: React.FC = () => {
  const { token } = theme.useToken()
  const { data: stats } = useDashboardStats()
  const { data: products } = useProducts({ pageSize: 5 })
  const { data: orders } = useOrders({ pageSize: 5 })

  const statCards = [
    {
      title: '用户总数',
      value: stats?.totalUsers || 0,
      icon: <ShoppingOutlined />,
      color: token.colorPrimary,
    },
    {
      title: '商品总数',
      value: stats?.totalProducts || 0,
      icon: <ShoppingOutlined />,
      color: token.colorSuccess,
    },
    {
      title: '团购总数',
      value: stats?.totalGroups || 0,
      icon: <TeamOutlined />,
      color: token.colorWarning,
    },
    {
      title: '订单总数',
      value: stats?.totalOrders || 0,
      icon: <FileTextOutlined />,
      color: token.colorInfo,
    },
    {
      title: '销售总额',
      value: `¥${(stats?.totalSales || 0).toLocaleString()}`,
      icon: <BarChartOutlined />,
      color: token.colorSuccess,
    },
    {
      title: '成团率',
      value: `${stats?.successRate || 0}%`,
      icon: <DashboardOutlined />,
      color: token.colorWarning,
    },
  ]

  const productColumns = [
    {
      title: '商品名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '库存',
      dataIndex: 'stock',
      key: 'stock',
    },
    {
      title: '销量',
      dataIndex: 'soldStock',
      key: 'soldStock',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          active: 'success',
          inactive: 'default',
          sold_out: 'error',
        }
        const textMap: Record<string, string> = {
          active: '在售',
          inactive: '下架',
          sold_out: '售罄',
        }
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>
      },
    },
  ]

  const orderColumns = [
    {
      title: '订单号',
      dataIndex: 'orderNo',
      key: 'orderNo',
    },
    {
      title: '金额',
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
        }
        const textMap: Record<string, string> = {
          pending: '待支付',
          paid: '已支付',
          shipped: '已发货',
          completed: '已完成',
          cancelled: '已取消',
        }
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (createdAt: string) => new Date(createdAt).toLocaleString(),
    },
  ]

  const menuItems = [
    {
      key: 'products',
      label: '商品管理',
      icon: <ShoppingOutlined />,
    },
    {
      key: 'users',
      label: '用户管理',
      icon: <TeamOutlined />,
    },
    {
      key: 'orders',
      label: '订单管理',
      icon: <FileTextOutlined />,
    },
    {
      key: 'activities',
      label: '活动管理',
      icon: <SettingOutlined />,
    },
    {
      key: 'analytics',
      label: '数据分析',
      icon: <BarChartOutlined />,
    },
  ]

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>运营后台</Title>

      {/* 功能菜单 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {menuItems.map((item) => (
          <Col xs={24} sm={12} md={8} lg={4} key={item.key}>
            <Card hoverable style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 32, color: token.colorPrimary, marginBottom: 12 }}>
                {item.icon}
              </div>
              <Text strong style={{ fontSize: 16 }}>{item.label}</Text>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 数据统计 */}
      <Title level={4} style={{ marginBottom: 16 }}>数据概览</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} md={8} lg={4} key={index}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 14 }}>{stat.title}</Text>
                  <div style={{ fontSize: 24, fontWeight: 600, marginTop: 8, color: stat.color }}>
                    {stat.value}
                  </div>
                </div>
                <div style={{ fontSize: 32, color: stat.color, opacity: 0.3 }}>
                  {stat.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Title level={4} style={{ marginBottom: 16 }}>商品管理</Title>
          <Card>
            <Table
              columns={productColumns}
              dataSource={products?.items}
              rowKey="id"
              pagination={false}
              size="small"
            />
            <Button type="link" block style={{ textAlign: 'center', marginTop: 8 }}>
              查看全部商品
            </Button>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Title level={4} style={{ marginBottom: 16 }}>订单管理</Title>
          <Card>
            <Table
              columns={orderColumns}
              dataSource={orders?.items}
              rowKey="id"
              pagination={false}
              size="small"
            />
            <Button type="link" block style={{ textAlign: 'center', marginTop: 8 }}>
              查看全部订单
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AdminDashboardPage
