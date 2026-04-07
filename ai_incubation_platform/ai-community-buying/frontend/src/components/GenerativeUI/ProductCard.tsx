/**
 * Generative UI - 商品卡片组件
 * 根据 AI 返回的商品数据动态渲染
 */
import React, { useState } from 'react'
import { Card, Button, Tag, Progress, Space, Image } from 'antd'
import {
  ShoppingCartOutlined,
  FireOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import type { ProductData } from '@/types/chat'

interface GenerativeProductCardProps {
  product: ProductData
  onAddToCart?: (product: ProductData) => void
  onCreateGroup?: (product: ProductData) => void
  onViewDetail?: (product: ProductData) => void
  compact?: boolean
}

export const GenerativeProductCard: React.FC<GenerativeProductCardProps> = ({
  product,
  onAddToCart,
  onCreateGroup,
  onViewDetail,
  compact = false,
}) => {
  const [hovered, setHovered] = useState(false)

  const discount = product.price && product.group_price
    ? Math.round((1 - product.group_price / product.price) * 100)
    : 0

  const probability = product.success_probability || 0

  return (
    <Card
      hoverable
      size={compact ? 'small' : 'default'}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: compact ? 280 : 320,
        transition: 'all 0.3s',
        transform: hovered ? 'translateY(-4px)' : 'none',
        boxShadow: hovered
          ? '0 8px 24px rgba(0,0,0,0.12)'
          : '0 1px 3px rgba(0,0,0,0.1)',
      }}
      cover={
        <div style={{ height: compact ? 140 : 180, overflow: 'hidden' }}>
          <Image
            src={product.image || '/placeholder-product.jpg'}
            alt={product.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            preview={false}
            fallback="/placeholder-product.jpg"
          />
        </div>
      }
      actions={
        compact
          ? undefined
          : [
              <Button
                key="cart"
                type="text"
                icon={<ShoppingCartOutlined />}
                onClick={() => onAddToCart?.(product)}
              >
                加入购物车
              </Button>,
              <Button
                key="group"
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={() => onCreateGroup?.(product)}
              >
                发起团购
              </Button>,
            ]
      }
    >
      <Card.Meta
        title={
          <Space wrap>
            <span>{product.name}</span>
            {product.sales && product.sales > 100 && (
              <Tag color="red" icon={<FireOutlined />}>
                热销
              </Tag>
            )}
            {discount > 0 && (
              <Tag color="orange">-{discount}%</Tag>
            )}
          </Space>
        }
        description={
          <div>
            {compact ? (
              <Space size="small" wrap>
                <span style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f' }}>
                  ¥{product.group_price?.toFixed(2) || product.price?.toFixed(2)}
                </span>
                {product.price && (
                  <span style={{ fontSize: 12, color: '#999', textDecoration: 'line-through' }}>
                    ¥{product.price.toFixed(2)}
                  </span>
                )}
              </Space>
            ) : (
              <>
                <div style={{ marginBottom: 8 }}>
                  <Space size="small" wrap>
                    <span style={{ fontSize: 20, fontWeight: 'bold', color: '#ff4d4f' }}>
                      ¥{product.group_price?.toFixed(2) || product.price?.toFixed(2)}
                    </span>
                    {product.price && (
                      <span style={{ fontSize: 14, color: '#999', textDecoration: 'line-through' }}>
                        原价 ¥{product.price.toFixed(2)}
                      </span>
                    )}
                  </Space>
                </div>
                {product.description && (
                  <p style={{ fontSize: 13, color: '#666', margin: '8px 0' }}>
                    {product.description}
                  </p>
                )}
                {product.reason && (
                  <div style={{ fontSize: 12, color: '#1890ff', marginBottom: 8 }}>
                    <CheckCircleOutlined /> 推荐理由：{product.reason}
                  </div>
                )}
                {probability > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      成团概率
                    </div>
                    <Progress
                      percent={probability}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                      size="small"
                      format={(percent) =>
                        percent! > 80 ? '很高' : percent! > 50 ? '中等' : '较低'
                      }
                    />
                  </div>
                )}
                {compact && (
                  <Space wrap style={{ marginTop: 8 }}>
                    <Button
                      size="small"
                      type="primary"
                      onClick={() => onCreateGroup?.(product)}
                    >
                      发起团购
                    </Button>
                    <Button
                      size="small"
                      onClick={() => onViewDetail?.(product)}
                    >
                      详情
                    </Button>
                  </Space>
                )}
              </>
            )}
          </div>
        }
      />
    </Card>
  )
}

/**
 * 商品列表横向滚动组件
 */
interface ProductCarouselProps {
  products: ProductData[]
  onAddToCart?: (product: ProductData) => void
  onCreateGroup?: (product: ProductData) => void
  onViewDetail?: (product: ProductData) => void
}

export const ProductCarousel: React.FC<ProductCarouselProps> = ({
  products,
  onAddToCart,
  onCreateGroup,
  onViewDetail,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        gap: 16,
        overflowX: 'auto',
        padding: '8px 0',
        scrollBehavior: 'smooth',
      }}
    >
      {products.map((product, index) => (
        <GenerativeProductCard
          key={product.id || index}
          product={product}
          onAddToCart={onAddToCart}
          onCreateGroup={onCreateGroup}
          onViewDetail={onViewDetail}
          compact
        />
      ))}
    </div>
  )
}
