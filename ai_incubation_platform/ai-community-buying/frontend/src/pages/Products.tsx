import React, { useState } from 'react'
import { Spin, Empty, Pagination, Input, Select, Slider, message } from 'antd'
import { SearchOutlined, FilterOutlined } from '@ant-design/icons'
import { ProductCard } from '@/components'
import { useProducts } from '@/hooks/useApi'
import { useCartStore } from '@/stores'
import type { Product, ProductFilter } from '@/types'

const { Option } = Select

type SortByType = 'created_at' | 'price' | 'sales' | 'stock'
type SortOrderType = 'asc' | 'desc'

const ProductsPage: React.FC = () => {
  const [filter, setFilter] = useState<ProductFilter & { sortBy?: SortByType; sortOrder?: SortOrderType }>({
    page: 1,
    pageSize: 12,
  })
  const { data, isLoading } = useProducts(filter)
  const addItem = useCartStore((state) => state.addItem)

  const handleAddToCart = (product: any) => {
    addItem({
      id: `product-${product.id}`,
      productId: product.id,
      product: product as any,
      quantity: 1,
      selected: true,
    })
    message.success('已加入购物车')
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: 'var(--color-text-primary)',
            margin: 0,
          }}
        >
          商品列表
        </h1>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginTop: 4 }}>
          发现精选好物，享受团购优惠
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '280px 1fr',
          gap: 'var(--gap-bento-lg)',
        }}
      >
        {/* 筛选侧边栏 - Bento 卡片 */}
        <div style={{ position: 'sticky', top: 24, height: 'fit-content' }}>
          <div className="bento-card">
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-bento-sm)',
                  background: 'var(--color-primary-light)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: 12,
                }}
              >
                <FilterOutlined style={{ color: 'var(--color-primary)', fontSize: 16 }} />
              </div>
              <h2
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                筛选条件
              </h2>
            </div>

            {/* 搜索 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                搜索商品
              </div>
              <Input
                placeholder="输入商品名称"
                prefix={<SearchOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
                onChange={(e) => setFilter({ ...filter, keyword: e.target.value, page: 1 })}
                style={{
                  borderRadius: 'var(--radius-bento-sm)',
                  borderColor: 'var(--color-border)',
                }}
              />
            </div>

            {/* 价格范围 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                价格范围
              </div>
              <Slider
                range
                min={0}
                max={1000}
                defaultValue={[0, 500]}
                onChange={(value) => setFilter({ ...filter, priceRange: value as [number, number], page: 1 })}
              />
            </div>

            {/* 商品状态 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                商品状态
              </div>
              <Select
                style={{ width: '100%', borderRadius: 'var(--radius-bento-sm)' }}
                onChange={(value) => setFilter({ ...filter, status: value, page: 1 })}
                allowClear
              >
                <Option value="active">在售</Option>
                <Option value="sold_out">售罄</Option>
                <Option value="inactive">下架</Option>
              </Select>
            </div>

            {/* 排序方式 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                排序方式
              </div>
              <Select
                style={{ width: '100%', borderRadius: 'var(--radius-bento-sm)' }}
                defaultValue="created_at"
                onChange={(value: SortByType) => setFilter({ ...filter, sortBy: value, page: 1 })}
              >
                <Option value="created_at">最新上架</Option>
                <Option value="price">价格</Option>
                <Option value="sales">销量</Option>
                <Option value="stock">库存</Option>
              </Select>
            </div>

            {/* 排序方向 */}
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)', marginBottom: 8 }}>
                排序方向
              </div>
              <Select
                style={{ width: '100%', borderRadius: 'var(--radius-bento-sm)' }}
                defaultValue="desc"
                onChange={(value: SortOrderType) => setFilter({ ...filter, sortOrder: value, page: 1 })}
              >
                <Option value="desc">降序</Option>
                <Option value="asc">升序</Option>
              </Select>
            </div>
          </div>
        </div>

        {/* 商品列表 - Bento Grid */}
        <div>
          {isLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', minHeight: 400 }}>
              <Spin size="large" tip="加载中..." />
            </div>
          ) : data?.items?.length ? (
            <>
              <div
                className="bento-grid"
                style={{
                  gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                  gap: 'var(--gap-bento)',
                }}
              >
                {data.items.map((product: Product) => (
                  <ProductCard
                    key={product.id}
                    product={product as any}
                    onAddToCart={handleAddToCart}
                  />
                ))}
              </div>

              {/* 分页 */}
              <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center' }}>
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
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 400,
                padding: 40,
                background: 'var(--color-bg-card)',
                borderRadius: 'var(--radius-bento-lg)',
                boxShadow: 'var(--shadow-bento)',
              }}
            >
              <Empty description="暂无商品" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProductsPage
