import React, { useState } from 'react'
import { Typography, Row, Col, Tabs, Button, Spin, Empty, Modal, Form, Input, InputNumber, Select, message, Space } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { GroupBuyCard } from '@/components/ProductCard'
import { useGroupBuys, useCreateGroupBuy, useProducts } from '@/hooks/useApi'
import type { GroupBuy, Product } from '@/types'

const { Title } = Typography
const { Option } = Select

const GroupsPage: React.FC = () => {
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [form] = Form.useForm()
  const { data: openGroups, isLoading: openLoading } = useGroupBuys('open')
  const { data: successGroups } = useGroupBuys('success')
  const { data: products } = useProducts()
  const createGroupBuy = useCreateGroupBuy()

  const handleCreate = async (values: any) => {
    try {
      await createGroupBuy.mutateAsync({
        productId: values.productId,
        targetQuantity: values.targetQuantity,
        deadlineHours: values.deadlineHours,
        leaderId: values.leaderId || 'current_user',
      })
      message.success('团购创建成功')
      setCreateModalOpen(false)
      form.resetFields()
    } catch (e: any) {
      message.error(e.message || '创建失败')
    }
  }

  const renderGroupList = (groups: GroupBuy[] = []) => {
    if (groups.length === 0) {
      return <Empty description="暂无团购" style={{ width: '100%' }} />
    }
    return (
      <Row gutter={[16, 16]}>
        {groups.map((group: GroupBuy) => (
          <Col xs={24} sm={12} md={8} lg={6} key={group.id}>
            <GroupBuyCard groupBuy={group} />
          </Col>
        ))}
      </Row>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>团购列表</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          发起团购
        </Button>
      </div>

      {openLoading ? (
        <Spin size="large" />
      ) : (
        <Tabs
          items={[
            {
              key: 'open',
              label: `进行中 (${openGroups?.length || 0})`,
              children: renderGroupList(openGroups),
            },
            {
              key: 'success',
              label: `已成团 (${successGroups?.length || 0})`,
              children: renderGroupList(successGroups),
            },
          ]}
        />
      )}

      {/* 创建团购弹窗 */}
      <Modal
        title="发起团购"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="productId"
            label="选择商品"
            rules={[{ required: true, message: '请选择商品' }]}
          >
            <Select placeholder="请选择商品">
              {products?.items?.map((p: Product) => (
                <Option key={p.id} value={p.id}>
                  {p.name} - ¥{p.price} (库存：{p.stock})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="targetQuantity"
            label="目标数量"
            rules={[{ required: true, message: '请输入目标数量' }]}
          >
            <InputNumber min={1} style={{ width: '100%' }} placeholder="例如：50" />
          </Form.Item>

          <Form.Item
            name="deadlineHours"
            label="成团时限 (小时)"
            initialValue={24}
            rules={[{ required: true, message: '请输入成团时限' }]}
          >
            <InputNumber min={1} max={720} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="leaderId"
            label="团长 ID"
            rules={[{ required: true, message: '请输入团长 ID' }]}
          >
            <Input placeholder="例如：user_001" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreateModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">发起团购</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default GroupsPage
