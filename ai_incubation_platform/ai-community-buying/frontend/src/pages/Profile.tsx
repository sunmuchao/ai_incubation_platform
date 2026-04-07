import React from 'react'
import { Typography, Avatar, Card, Row, Col, Descriptions, Tabs, List, Tag, Space, Button, theme } from 'antd'
import { UserOutlined, PhoneOutlined, MailOutlined, EnvironmentOutlined, StarOutlined, TrophyOutlined, GiftOutlined } from '@ant-design/icons'
import { useOrganizerProfile, useUserCoupons } from '@/hooks/useApi'
import { useAuthStore } from '@/stores'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography

const ProfilePage: React.FC = () => {
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { data: organizerProfile } = useOrganizerProfile(user?.id || '')
  const { data: coupons } = useUserCoupons(user?.id || '')

  const userMenuItems = [
    {
      title: '我的订单',
      icon: <StarOutlined />,
      onClick: () => navigate('/orders'),
    },
    {
      title: '我的收藏',
      icon: <TrophyOutlined />,
      onClick: () => navigate('/favorites'),
    },
    {
      title: '优惠券',
      icon: <GiftOutlined />,
      onClick: () => navigate('/coupons'),
      badge: coupons?.length || 0,
    },
  ]

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>个人中心</Title>

      <Row gutter={[24, 24]}>
        {/* 用户信息卡片 */}
        <Col xs={24} md={8}>
          <Card>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Avatar
                size={100}
                src={user?.avatar}
                icon={<UserOutlined />}
                style={{ marginBottom: 16, background: token.colorPrimary }}
              />
              <Title level={4} style={{ margin: '0 0 8px' }}>{user?.nickname || '用户'}</Title>
              <Tag color="blue">{user?.memberLevel?.name || '普通会员'}</Tag>
            </div>

            <Descriptions column={1} size="small">
              <Descriptions.Item label="会员等级">
                {user?.memberLevel?.name || '普通会员'}
              </Descriptions.Item>
              <Descriptions.Item label="积分">
                {user?.points || 0}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="快捷入口" style={{ marginTop: 16 }}>
            <List
              dataSource={userMenuItems}
              renderItem={(item: any) => (
                <List.Item
                  onClick={item.onClick}
                  style={{ cursor: 'pointer', padding: '12px 0' }}
                >
                  <List.Item.Meta
                    avatar={
                      <div style={{ fontSize: 20, color: token.colorPrimary }}>
                        {item.icon}
                      </div>
                    }
                    title={
                      <Space>
                        <span>{item.title}</span>
                        {item.badge > 0 && (
                          <Tag color="red">{item.badge}</Tag>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 主要内容区域 */}
        <Col xs={24} md={16}>
          <Tabs
            items={[
              {
                key: 'info',
                label: '个人信息',
                children: (
                  <Card>
                    <Descriptions column={1} bordered>
                      <Descriptions.Item label="昵称">{user?.nickname || '未设置'}</Descriptions.Item>
                      <Descriptions.Item label="手机号">
                        <Space>
                          <PhoneOutlined />
                          {user?.phone || '未绑定'}
                        </Space>
                      </Descriptions.Item>
                      <Descriptions.Item label="邮箱">
                        <Space>
                          <MailOutlined />
                          {user?.email || '未绑定'}
                        </Space>
                      </Descriptions.Item>
                      <Descriptions.Item label="收货地址">
                        <Space>
                          <EnvironmentOutlined />
                          暂无收货地址
                        </Space>
                      </Descriptions.Item>
                    </Descriptions>
                    <Button type="primary" style={{ marginTop: 16 }}>
                      编辑资料
                    </Button>
                  </Card>
                ),
              },
              {
                key: 'organizer',
                label: '团长信息',
                children: organizerProfile ? (
                  <Card>
                    <Descriptions column={1} bordered>
                      <Descriptions.Item label="团长等级">{organizerProfile.level}</Descriptions.Item>
                      <Descriptions.Item label="团长评分">{organizerProfile.rating} 分</Descriptions.Item>
                      <Descriptions.Item label="团购总数">{organizerProfile.totalGroups}</Descriptions.Item>
                      <Descriptions.Item label="成功成团">{organizerProfile.successGroups}</Descriptions.Item>
                      <Descriptions.Item label="订单总数">{organizerProfile.totalOrders}</Descriptions.Item>
                      <Descriptions.Item label="佣金总额">¥{organizerProfile.totalCommission}</Descriptions.Item>
                      <Descriptions.Item label="可提现佣金">
                        <Text type="success" strong>¥{organizerProfile.availableCommission}</Text>
                      </Descriptions.Item>
                    </Descriptions>
                    <Space style={{ marginTop: 16 }}>
                      <Button type="primary">申请提现</Button>
                      <Button>查看明细</Button>
                    </Space>
                  </Card>
                ) : (
                  <Card>
                    <div style={{ textAlign: 'center', padding: 48 }}>
                      <Text type="secondary">暂无团长信息</Text>
                      <div style={{ marginTop: 16 }}>
                        <Button type="primary" onClick={() => navigate('/organizer/apply')}>
                          申请成为团长
                        </Button>
                      </div>
                    </div>
                  </Card>
                ),
              },
              {
                key: 'coupons',
                label: '优惠券',
                children: (
                  <Card>
                    {coupons && coupons.length > 0 ? (
                      <List
                        dataSource={coupons}
                        renderItem={(coupon) => (
                          <List.Item>
                            <Card
                              hoverable
                              style={{ width: '100%', marginBottom: 12 }}
                            >
                              <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                                <div>
                                  <Title level={5} style={{ margin: '0 0 8px' }}>{coupon.templateName}</Title>
                                  <Text type="secondary">
                                    {coupon.type === 'fixed' ? '¥' : ''}{coupon.value}{coupon.type === 'percentage' ? '%' : ''}
                                    {coupon.minPurchase > 0 && ` (满¥${coupon.minPurchase}可用)`}
                                  </Text>
                                </div>
                                <Tag color={coupon.status === 'unused' ? 'green' : coupon.status === 'used' ? 'gray' : 'red'}>
                                  {coupon.status === 'unused' ? '未使用' : coupon.status === 'used' ? '已使用' : '已过期'}
                                </Tag>
                              </Space>
                            </Card>
                          </List.Item>
                        )}
                      />
                    ) : (
                      <div style={{ textAlign: 'center', padding: 48 }}>
                        <Text type="secondary">暂无优惠券</Text>
                        <div style={{ marginTop: 16 }}>
                          <Button type="primary" onClick={() => navigate('/coupons')}>
                            领取优惠券
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card>
                ),
              },
            ]}
          />
        </Col>
      </Row>
    </div>
  )
}

export default ProfilePage
