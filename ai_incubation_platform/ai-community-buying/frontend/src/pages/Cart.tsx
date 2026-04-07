import React from 'react'
import { Typography, Table, Button, Space, Checkbox, Card, theme } from 'antd'
import { ShoppingCartOutlined, DeleteOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useCartStore } from '@/stores'
import { message } from 'antd'

const { Title, Text } = Typography

const CartPage: React.FC = () => {
  const navigate = useNavigate()
  const { token } = theme.useToken()
  const { items, updateQuantity, removeItem, toggleSelected, selectedItems, totalAmount, clearCart } = useCartStore()

  const columns = [
    {
      title: '选择',
      key: 'selected',
      render: (_: any, record: any) => (
        <Checkbox
          checked={record.selected}
          onChange={() => toggleSelected(record.id)}
        />
      ),
    },
    {
      title: '商品',
      dataIndex: ['product', 'name'],
      key: 'product',
      render: (text: string, record: any) => (
        <Space>
          <img
            src={record.product?.imageUrl || 'https://via.placeholder.com/60x60'}
            alt={text}
            style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 8 }}
          />
          <Text strong>{text || '未知商品'}</Text>
        </Space>
      ),
    },
    {
      title: '单价',
      dataIndex: ['product', 'price'],
      key: 'price',
      render: (price: number) => `¥${price?.toFixed(2) || '0.00'}`,
    },
    {
      title: '数量',
      key: 'quantity',
      render: (_: any, record: any) => (
        <input
          type="number"
          min={1}
          max={record.product?.stock || 99}
          value={record.quantity}
          onChange={(e) => updateQuantity(record.id, parseInt(e.target.value) || 1)}
          style={{ width: 60, padding: '4px 8px', borderRadius: 4, border: `1px solid ${token.colorBorder}` }}
        />
      ),
    },
    {
      title: '小计',
      key: 'subtotal',
      render: (_: any, record: any) => (
        <Text strong>
          ¥{((record.product?.price || 0) * record.quantity).toFixed(2)}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeItem(record.id)}
        >
          删除
        </Button>
      ),
    },
  ]

  const handleCheckout = () => {
    if (selectedItems.length === 0) {
      message.warning('请选择商品')
      return
    }
    message.info('跳转至结算页')
  }

  if (items.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <ShoppingCartOutlined style={{ fontSize: 64, color: token.colorTextTertiary, marginBottom: 16 }} />
        <Title level={4}>购物车空空如也</Title>
        <Button type="primary" icon={<PlusCircleOutlined />} onClick={() => navigate('/products')}>
          去逛逛
        </Button>
      </div>
    )
  }

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>购物车 ({items.length} 件商品)</Title>

      <Table
        columns={columns}
        dataSource={items}
        rowKey="id"
        pagination={false}
        scroll={{ x: 800 }}
      />

      <Card style={{ marginTop: 24, textAlign: 'right' }}>
        <Space size="large" style={{ marginRight: 24 }}>
          <Button onClick={clearCart}>清空购物车</Button>
          <div>
            <Text type="secondary">已选 {selectedItems.length} 件商品，</Text>
            <Text strong style={{ fontSize: 20, color: token.colorPrimary }}>
              合计：¥{totalAmount.toFixed(2)}
            </Text>
          </div>
          <Button type="primary" size="large" onClick={handleCheckout}>
            去结算
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default CartPage
