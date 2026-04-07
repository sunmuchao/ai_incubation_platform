import React from 'react'
import { Typography, Row, Col, Card, Statistic, Progress, Table, Tag, Space, Button, theme } from 'antd'
import {
  TeamOutlined,
  DollarOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores'
import { useOrganizerProfile, useCommissionRecords, useGroupBuys } from '@/hooks/useApi'

const { Title, Text } = Typography

const OrganizerDashboardPage: React.FC = () => {
  const { token } = theme.useToken()
  const { user } = useAuthStore()
  const { data: profile } = useOrganizerProfile(user?.id || '')
  const { data: commissionRecords } = useCommissionRecords(user?.id || '')
  const { data: groups } = useGroupBuys()

  const statCards = [
    {
      title: '团购总数',
      value: profile?.totalGroups || 0,
      icon: <TeamOutlined />,
      color: token.colorWarning,
    },
    {
      title: '成功成团',
      value: profile?.successGroups || 0,
      icon: <CheckCircleOutlined />,
      color: token.colorSuccess,
    },
    {
      title: '订单总数',
      value: profile?.totalOrders || 0,
      icon: <FileTextOutlined />,
      color: token.colorInfo,
    },
    {
      title: '佣金总额',
      value: `¥${(profile?.totalCommission || 0).toFixed(2)}`,
      icon: <DollarOutlined />,
      color: token.colorSuccess,
    },
  ]

  const commissionColumns = [
    {
      title: '记录 ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '团购 ID',
      dataIndex: 'groupBuyId',
      key: 'groupBuyId',
      width: 80,
    },
    {
      title: '佣金金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `¥${amount.toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'warning',
          paid: 'success',
          withdrawn: 'default',
        }
        const textMap: Record<string, string> = {
          pending: '待结算',
          paid: '已结算',
          withdrawn: '已提现',
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

  const groupColumns = [
    {
      title: '团购 ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '商品',
      dataIndex: ['product', 'name'],
      key: 'product',
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: any, record: any) => (
        <Progress
          percent={Math.round((record.joinedCount / record.targetQuantity) * 100)}
          size="small"
          status={record.status === 'success' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          open: 'processing',
          success: 'success',
          failed: 'error',
          expired: 'default',
        }
        const textMap: Record<string, string> = {
          open: '进行中',
          success: '已成团',
          failed: '已失败',
          expired: '已过期',
        }
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>
      },
    },
  ]

  const successRate = profile?.totalGroups
    ? Math.round((profile.successGroups / profile.totalGroups) * 100)
    : 0

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>团长看板</Title>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} md={6} key={index}>
            <Card>
              <Statistic
                title={stat.title}
                value={stat.value}
                prefix={
                  <span style={{ color: stat.color, fontSize: 24 }}>{stat.icon}</span>
                }
                valueStyle={{ color: stat.color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="成团率">
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Progress
                type="dashboard"
                percent={successRate}
                strokeColor={{
                  '0%': token.colorPrimary,
                  '100%': token.colorSuccess,
                }}
                format={(percent) => `${percent}%`}
              />
              <div style={{ marginTop: 16 }}>
                <Space size="large">
                  <div>
                    <Text type="secondary">成功</Text>
                    <div style={{ fontSize: 20, fontWeight: 600 }}>{profile?.successGroups || 0}</div>
                  </div>
                  <div>
                    <Text type="secondary">失败/过期</Text>
                    <div style={{ fontSize: 20, fontWeight: 600 }}>
                      {((profile?.totalGroups || 0) - (profile?.successGroups || 0))}
                    </div>
                  </div>
                </Space>
              </div>
            </div>
          </Card>

          <Card title="我的团购" style={{ marginTop: 16 }}>
            <Table
              columns={groupColumns}
              dataSource={groups?.slice(0, 5)}
              rowKey="id"
              pagination={false}
              size="small"
            />
            <Button type="link" block style={{ textAlign: 'center' }}>
              查看全部
            </Button>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="佣金记录">
            <Table
              columns={commissionColumns}
              dataSource={commissionRecords?.slice(0, 10)}
              rowKey="id"
              pagination={false}
              size="small"
              scroll={{ x: 400 }}
            />
            <Space style={{ marginTop: 16 }}>
              <Button type="primary">申请提现</Button>
              <Button>查看全部</Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default OrganizerDashboardPage
