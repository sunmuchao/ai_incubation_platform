import React from 'react'
import { Row, Col, Typography, Tabs, Space, Spin, Empty, theme } from 'antd'
import { FireOutlined, StarOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { ProductCard, Dashboard } from '@/components'
import { useHotProducts, useProducts, useGroupBuys, useDashboardStats } from '@/hooks/useApi'
import { useAuthStore } from '@/stores'
import type { Product, GroupBuy } from '@/types'

const { Title } = Typography

const HomePage: React.FC = () => {
  const { token } = theme.useToken()
  const { isAuthenticated } = useAuthStore()
  const { data: hotProducts, isLoading: hotLoading } = useHotProducts(8)
  const { data: allProducts, isLoading: productsLoading } = useProducts({ pageSize: 8 })
  const { data: groupBuys, isLoading: groupsLoading } = useGroupBuys('open')
  const { data: stats, isLoading: statsLoading } = useDashboardStats()

  const isLoading = hotLoading || productsLoading || groupsLoading

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  return (
    <div>
      {isAuthenticated && !statsLoading && stats && (
        <Dashboard stats={stats} />
      )}

      {!isAuthenticated && (
        <div
          style={{
            background: `linear-gradient(135deg, ${token.colorPrimaryBg} 0%, ${token.colorBgContainer} 100%)`,
            padding: 48,
            borderRadius: token.borderRadiusLG,
            marginBottom: 24,
            textAlign: 'center',
          }}
        >
          <Title level={1} style={{ marginBottom: 16 }}>
            欢迎使用 AI 社区团购
          </Title>
          <Title level={4} type="secondary" style={{ fontWeight: 400 }}>
            基于 AI 智能选品和动态定价的社区团购系统
            <br />
            让每个社区都有自己的 AI 团购管家
          </Title>
        </div>
      )}

      <Tabs
        items={[
          {
            key: 'hot',
            label: (
              <Space>
                <FireOutlined />
                <span>热销商品</span>
              </Space>
            ),
            children: (
              <Row gutter={[16, 16]}>
                {hotProducts?.length ? (
                  hotProducts.map((product: Product) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={product.id}>
                      <ProductCard product={product} />
                    </Col>
                  ))
                ) : (
                  <Empty description="暂无热销商品" style={{ width: '100%' }} />
                )}
              </Row>
            ),
          },
          {
            key: 'products',
            label: (
              <Space>
                <StarOutlined />
                <span>推荐商品</span>
              </Space>
            ),
            children: (
              <Row gutter={[16, 16]}>
                {allProducts?.items?.length ? (
                  allProducts.items.map((product: Product) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={product.id}>
                      <ProductCard product={product} />
                    </Col>
                  ))
                ) : (
                  <Empty description="暂无商品" style={{ width: '100%' }} />
                )}
              </Row>
            ),
          },
          {
            key: 'groups',
            label: (
              <Space>
                <ClockCircleOutlined />
                <span>热门团购</span>
              </Space>
            ),
            children: (
              <Row gutter={[16, 16]}>
                {groupBuys?.length ? (
                  groupBuys.map((group: GroupBuy) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={group.id}>
                      <div className="card" style={{ height: '100%' }}>
                        <div style={{ marginBottom: 12 }}>
                          <Title level={5} ellipsis={{ rows: 1 }}>
                            {group.product?.name || `团购 #${group.id}`}
                          </Title>
                        </div>
                        {group.product?.imageUrl && (
                          <img
                            src={group.product.imageUrl}
                            alt={group.product.name}
                            style={{ width: '100%', height: 150, objectFit: 'cover', borderRadius: 8, marginBottom: 12 }}
                          />
                        )}
                        <div style={{ marginBottom: 12 }}>
                          <div style={{ fontSize: 14, color: token.colorPrimary, fontWeight: 600 }}>
                            ¥{group.product?.price?.toFixed(2) || '0.00'}
                          </div>
                          <div style={{ fontSize: 12, color: token.colorTextTertiary }}>
                            已参团：{group.joinedCount}/{group.targetQuantity}
                          </div>
                        </div>
                        <div style={{ fontSize: 12, color: token.colorTextSecondary }}>
                          截止：{new Date(group.deadline).toLocaleString()}
                        </div>
                      </div>
                    </Col>
                  ))
                ) : (
                  <Empty description="暂无进行中团购" style={{ width: '100%' }} />
                )}
              </Row>
            ),
          },
        ]}
      />
    </div>
  )
}

export default HomePage
