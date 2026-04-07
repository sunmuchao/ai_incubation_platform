import React, { useState } from 'react'
import { Row, Col, Input, Select, Slider, Pagination, Spin, Empty, Typography, theme } from 'antd'
import { SearchOutlined, FilterOutlined } from '@ant-design/icons'
import { ProductCard } from '@/components'
import { useProducts } from '@/hooks/useApi'
import { useCartStore } from '@/stores'
import type { Product, ProductFilter } from '@/types'
import { message } from 'antd'

const { Title } = Typography
const { Option } = Select

type SortByType = 'created_at' | 'price' | 'sales' | 'stock'
type SortOrderType = 'asc' | 'desc'

const ProductsPage: React.FC = () => {
  const { token } = theme.useToken()
  const [filter, setFilter] = useState<ProductFilter & { sortBy?: SortByType; sortOrder?: SortOrderType }>({
    page: 1,
    pageSize: 12,
  })
  const { data, isLoading } = useProducts(filter)
  const addItem = useCartStore((state) => state.addItem)

  const handleAddToCart = (product: Product) => {
    addItem({
      id: `product-${product.id}`,
      productId: product.id,
      product,
      quantity: 1,
      selected: true,
    })
    message.success('已加入购物车')
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>商品列表</Title>
      </div>

      <Row gutter={[24, 24]}>
        {/* 筛选侧边栏 */}
        <Col xs={24} lg={6}>
          <div className="card" style={{ position: 'sticky', top: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
              <FilterOutlined style={{ marginRight: 8, color: token.colorPrimary }} />
              <Title level={5} style={{ margin: 0 }}>筛选</Title>
            </div>

            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>搜索商品</div>
              <Input
                placeholder="输入商品名称"
                prefix={<SearchOutlined />}
                onChange={(e) => setFilter({ ...filter, keyword: e.target.value, page: 1 })}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>价格范围</div>
              <Slider
                range
                min={0}
                max={1000}
                defaultValue={[0, 500]}
                onChange={(value) => setFilter({ ...filter, priceRange: value as [number, number], page: 1 })}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>商品状态</div>
              <Select
                style={{ width: '100%' }}
                onChange={(value) => setFilter({ ...filter, status: value, page: 1 })}
                allowClear
              >
                <Option value="active">在售</Option>
                <Option value="sold_out">售罄</Option>
                <Option value="inactive">下架</Option>
              </Select>
            </div>

            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>排序方式</div>
              <Select
                style={{ width: '100%' }}
                defaultValue="created_at"
                onChange={(value: SortByType) => setFilter({ ...filter, sortBy: value, page: 1 })}
              >
                <Option value="created_at">最新上架</Option>
                <Option value="price">价格</Option>
                <Option value="sales">销量</Option>
                <Option value="stock">库存</Option>
              </Select>
            </div>

            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>排序方向</div>
              <Select
                style={{ width: '100%' }}
                defaultValue="desc"
                onChange={(value: SortOrderType) => setFilter({ ...filter, sortOrder: value, page: 1 })}
              >
                <Option value="desc">降序</Option>
                <Option value="asc">升序</Option>
              </Select>
            </div>
          </div>
        </Col>

        {/* 商品列表 */}
        <Col xs={24} lg={18}>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', minHeight: 400 }}>
              <Spin size="large" />
            </div>
          ) : data?.items?.length ? (
            <>
              <Row gutter={[16, 16]}>
                {data.items.map((product: Product) => (
                  <Col xs={24} sm={12} md={8} key={product.id}>
                    <ProductCard product={product} onAddToCart={handleAddToCart} />
                  </Col>
                ))}
              </Row>

              <div style={{ marginTop: 24, textAlign: 'center' }}>
                <Pagination
                  current={data.page}
                  pageSize={data.pageSize}
                  total={data.total}
                  onChange={(page, pageSize) => setFilter({ ...filter, page, pageSize })}
                  showSizeChanger
                  showTotal={(total) => `共 ${total} 个商品`}
                />
              </div>
            </>
          ) : (
            <Empty description="暂无商品" style={{ marginTop: 48 }} />
          )}
        </Col>
      </Row>
    </div>
  )
}

export default ProductsPage
