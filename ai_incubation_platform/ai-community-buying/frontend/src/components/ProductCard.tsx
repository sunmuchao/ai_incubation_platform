/**
 * Bento Grid 风格商品卡片 - Linear 风格设计
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ShoppingCartOutlined,
  FireOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  StarOutlined,
} from '@ant-design/icons'

interface Product {
  id: string
  name: string
  price: number
  originalPrice?: number
  imageUrl?: string
  category?: string
  stock: number
  soldStock?: number
  status: 'active' | 'inactive' | 'sold_out'
  rating?: number
  sales?: number
  groupPrice?: number
  successProbability?: number
  reason?: string
  description?: string
}

interface ProductCardProps {
  product: Product
  onAddToCart?: (product: Product) => void
  onBuyNow?: (product: Product) => void
  compact?: boolean
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onAddToCart,
  onBuyNow,
  compact = false,
}) => {
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(false)

  const discount = product.originalPrice && product.price
    ? Math.round((1 - product.price / product.originalPrice) * 100)
    : 0

  const groupDiscount = product.price && product.groupPrice
    ? Math.round((1 - product.groupPrice / product.price) * 100)
    : 0

  const statusMap: Record<string, { color: string; text: string }> = {
    active: { color: 'var(--color-success)', text: '在售' },
    inactive: { color: 'var(--color-text-tertiary)', text: '下架' },
    sold_out: { color: 'var(--color-error)', text: '售罄' },
  }

  const status = statusMap[product.status] || statusMap.active

  return (
    <div
      className={`bento-card bento-card-clickable ${compact ? '' : 'bento-card-interactive'}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => navigate(`/products/${product.id}`)}
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: hovered ? 'translateY(-4px)' : 'none',
        boxShadow: hovered
          ? 'var(--shadow-bento-hover)'
          : 'var(--shadow-bento)',
      }}
    >
      {/* 图片区域 */}
      <div
        style={{
          position: 'relative',
          height: compact ? 140 : 180,
          overflow: 'hidden',
          borderRadius: 'var(--radius-bento)',
          marginBottom: 12,
        }}
      >
        <img
          src={product.imageUrl || 'https://via.placeholder.com/300x200?text=No+Image'}
          alt={product.name}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transition: 'transform 0.3s ease',
            transform: hovered ? 'scale(1.05)' : 'none',
          }}
          loading="lazy"
        />

        {/* 状态标签 */}
        <span
          className="tag"
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
            background: status.color === 'var(--color-success)'
              ? 'var(--color-success-light)'
              : status.color === 'var(--color-error)'
              ? 'var(--color-error-light)'
              : 'var(--color-bg-tertiary)',
            color: status.color,
            backdropFilter: 'blur(8px)',
          }}
        >
          {status.text}
        </span>

        {/* 折扣标签 */}
        {discount > 0 && (
          <span
            className="tag"
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              background: 'var(--color-accent)',
              color: 'white',
            }}
          >
            -{discount}%
          </span>
        )}

        {/* 热销标签 */}
        {product.sales && product.sales > 100 && (
          <span
            className="tag"
            style={{
              position: 'absolute',
              bottom: 8,
              left: 8,
              background: 'rgba(255, 255, 255, 0.9)',
              color: 'var(--color-accent)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <FireOutlined style={{ marginRight: 4 }} />
            热销
          </span>
        )}
      </div>

      {/* 内容区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 分类 */}
        <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 6 }}>
          {product.category || '未分类'}
        </div>

        {/* 商品名称 */}
        <h3
          style={{
            fontSize: compact ? 14 : 15,
            fontWeight: 600,
            color: 'var(--color-text-primary)',
            margin: '0 0 8px 0',
            lineHeight: 1.4,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {product.name}
        </h3>

        {/* 评分 */}
        {product.rating && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
            <StarOutlined style={{ color: 'var(--color-warning)', fontSize: 12 }} />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
              {product.rating.toFixed(1)}
            </span>
            {product.soldStock && (
              <>
                <span style={{ color: 'var(--color-border-dark)', fontSize: 12 }}>|</span>
                <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
                  已售 {product.soldStock}
                </span>
              </>
            )}
          </div>
        )}

        {/* 推荐理由 */}
        {product.reason && (
          <div
            style={{
              fontSize: 12,
              color: 'var(--color-primary)',
              marginBottom: 8,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 4,
            }}
          >
            <CheckCircleOutlined style={{ marginTop: 2 }} />
            <span>{product.reason}</span>
          </div>
        )}

        {/* 成团概率 */}
        {product.successProbability && !compact && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginBottom: 4 }}>
              成团概率
            </div>
            <div style={{ height: 4, background: 'var(--color-bg-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${product.successProbability}%`,
                  background: `linear-gradient(90deg,
                    ${product.successProbability > 80 ? 'var(--color-success)' :
                      product.successProbability > 50 ? 'var(--color-warning)' : 'var(--color-error)'} 0%,
                    ${product.successProbability > 80 ? 'var(--color-success-light)' :
                      product.successProbability > 50 ? 'var(--color-warning-light)' : 'var(--color-error-light)'} 100%
                  )`,
                  borderRadius: 2,
                  transition: 'width 0.5s ease',
                }}
              />
            </div>
            <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
              {product.successProbability > 80 ? '很高' :
               product.successProbability > 50 ? '中等' : '较低'}
            </span>
          </div>
        )}

        {/* 价格区域 - 推到最底部 */}
        <div style={{ marginTop: 'auto', paddingTop: 12 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
            <span
              style={{
                fontSize: compact ? 18 : 22,
                fontWeight: 700,
                color: 'var(--color-primary)',
              }}
            >
              ¥{product.price?.toFixed(2)}
            </span>
            {product.originalPrice && (
              <span
                style={{
                  fontSize: 12,
                  color: 'var(--color-text-tertiary)',
                  textDecoration: 'line-through',
                }}
              >
                ¥{product.originalPrice.toFixed(2)}
              </span>
            )}
          </div>

          {/* 团购价格 */}
          {product.groupPrice && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--color-accent)',
                marginBottom: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ThunderboltOutlined style={{ fontSize: 12 }} />
              团购价 ¥{product.groupPrice.toFixed(2)} (省 {groupDiscount}%)
            </div>
          )}

          {/* 操作按钮 */}
          <div
            style={{
              display: 'flex',
              gap: 8,
              opacity: hovered || compact ? 1 : 0,
              transform: hovered || compact ? 'translateY(0)' : 'translateY(8px)',
              transition: 'all 0.2s ease',
            }}
          >
            <button
              className="btn-primary"
              style={{ flex: 1 }}
              onClick={(e) => {
                e.stopPropagation()
                onAddToCart?.(product)
              }}
              disabled={product.status !== 'active'}
            >
              <ShoppingCartOutlined /> 加入购物车
            </button>
            {!compact && (
              <button
                className="btn-secondary"
                style={{ flex: 1 }}
                onClick={(e) => {
                  e.stopPropagation()
                  onBuyNow?.(product)
                }}
                disabled={product.status !== 'active'}
              >
                立即购买
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
