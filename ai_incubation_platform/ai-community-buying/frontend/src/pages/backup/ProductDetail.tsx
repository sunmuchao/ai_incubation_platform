import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Row, Col, Image, Typography, Space, Tag, InputNumber, Divider, Spin, message, theme } from 'antd'
import { ShoppingCartOutlined, ShareAltOutlined } from '@ant-design/icons'
import { useProduct, useCreateOrder } from '@/hooks/useApi'
import { useCartStore } from '@/stores'

const { Title, Text, Paragraph } = Typography

const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { token } = theme.useToken()
  const [quantity, setQuantity] = useState(1)
  const { data: product, isLoading } = useProduct(Number(id))
  const createOrder = useCreateOrder()
  const addItem = useCartStore((state) => state.addItem)

  const handleAddToCart = () => {
    if (!product) return
    addItem({
      id: `product-${product.id}`,
      productId: product.id,
      product,
      quantity,
      selected: true,
    })
    message.success('已加入购物车')
  }

  const handleBuyNow = async () => {
    if (!product) return
    try {
      const order = await createOrder.mutateAsync({
        productId: product.id,
        quantity,
      })
      message.success('订单创建成功')
      navigate(`/orders/${order.id}`)
    } catch (e: any) {
      message.error(e.message || '下单失败')
    }
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', minHeight: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!product) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Text type="secondary">商品不存在</Text>
      </div>
    )
  }

  return (
    <div>
      <Row gutter={[32, 32]}>
        {/* 商品图片 */}
        <Col xs={24} md={12}>
          <div className="card">
            <Image
              src={product.imageUrl || 'https://via.placeholder.com/600x400'}
              alt={product.name}
              style={{ width: '100%', borderRadius: 8 }}
              preview={false}
            />
          </div>
        </Col>

        {/* 商品信息 */}
        <Col xs={24} md={12}>
          <Title level={2}>{product.name}</Title>

          <div style={{ marginBottom: 16 }}>
            <Tag color={product.status === 'active' ? 'green' : product.status === 'sold_out' ? 'red' : 'gray'}>
              {product.status === 'active' ? '在售' : product.status === 'sold_out' ? '售罄' : '下架'}
            </Tag>
            {product.category && (
              <Tag color="blue">{product.category}</Tag>
            )}
          </div>

          <div style={{ marginBottom: 24 }}>
            <Text type="secondary" style={{ fontSize: 14 }}>价格</Text>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <Text style={{ fontSize: 32, fontWeight: 600, color: token.colorPrimary }}>
                ¥{product.price.toFixed(2)}
              </Text>
              {product.originalPrice && (
                <Text delete style={{ fontSize: 18 }}>
                  ¥{product.originalPrice.toFixed(2)}
                </Text>
              )}
            </div>
          </div>

          <Divider />

          <div style={{ marginBottom: 24 }}>
            <Space size="large">
              <div>
                <Text type="secondary">库存</Text>
                <div style={{ fontSize: 18, fontWeight: 500 }}>{product.stock}</div>
              </div>
              <div>
                <Text type="secondary">已售</Text>
                <div style={{ fontSize: 18, fontWeight: 500 }}>{product.soldStock || 0}</div>
              </div>
            </Space>
          </div>

          <div style={{ marginBottom: 24 }}>
            <Text type="secondary">购买数量</Text>
            <div style={{ marginTop: 8 }}>
              <InputNumber
                min={1}
                max={product.stock}
                value={quantity}
                onChange={(v) => setQuantity(v || 1)}
                size="large"
              />
            </div>
          </div>

          <Space size="large" style={{ marginBottom: 24 }}>
            <Button
              type="primary"
              size="large"
              icon={<ShoppingCartOutlined />}
              onClick={handleAddToCart}
              disabled={product.status !== 'active'}
            >
              加入购物车
            </Button>
            <Button
              type="primary"
              danger
              size="large"
              onClick={handleBuyNow}
              disabled={product.status !== 'active'}
            >
              立即购买
            </Button>
            <Button size="large" icon={<ShareAltOutlined />}>
              分享
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 商品详情 */}
      <div className="card" style={{ marginTop: 24 }}>
        <Title level={4}>商品详情</Title>
        <Paragraph>{product.description || '暂无商品描述'}</Paragraph>
      </div>
    </div>
  )
}

export default ProductDetailPage
