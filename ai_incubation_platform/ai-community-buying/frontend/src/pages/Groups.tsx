import React, { useState } from 'react'
import { Button, Input, InputNumber, Select, Modal, message, Form } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { GroupBuyCard } from '@/components'
import { useGroupBuys, useCreateGroupBuy, useProducts } from '@/hooks/useApi'
import type { GroupBuy, Product } from '@/types'

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
      return (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 200,
            color: 'var(--color-text-tertiary)',
          }}
        >
          暂无团购
        </div>
      )
    }
    return (
      <div
        className="bento-grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 'var(--gap-bento)',
        }}
      >
        {groups.map((group: GroupBuy) => (
          <GroupBuyCard key={group.id} groupBuy={group as any} />
        ))}
      </div>
    )
  }

  const [activeTab, setActiveTab] = useState('open')

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* 页面标题 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 24,
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              margin: 0,
            }}
          >
            团购列表
          </h1>
          <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginTop: 4 }}>
            参与热门团购，享受超值优惠
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => setCreateModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 20px',
          }}
        >
          <PlusOutlined /> 发起团购
        </button>
      </div>

      {/* 团购 Tabs - Bento 风格 */}
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'inline-flex',
            background: 'var(--color-bg-tertiary)',
            borderRadius: 'var(--radius-bento-lg)',
            padding: 4,
            marginBottom: 16,
          }}
        >
          {[
            { key: 'open', label: '进行中', count: openGroups?.length || 0 },
            { key: 'success', label: '已成团', count: successGroups?.length || 0 },
          ].map((tab) => {
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '8px 20px',
                  borderRadius: 'var(--radius-bento-lg)',
                  background: isActive ? 'var(--color-bg-card)' : 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  boxShadow: isActive ? 'var(--shadow-linear-sm)' : 'none',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'var(--color-bg-card-hover)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = isActive ? 'var(--color-bg-card)' : 'transparent'
                  }
                }}
              >
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                  }}
                >
                  {tab.label}
                </span>
                <span
                  style={{
                    fontSize: 12,
                    padding: '2px 8px',
                    borderRadius: 10,
                    background: isActive ? 'var(--color-primary-light)' : 'transparent',
                    color: isActive ? 'var(--color-primary)' : 'var(--color-text-tertiary)',
                    fontWeight: 500,
                  }}
                >
                  {tab.count}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* 团购列表 */}
      {openLoading ? (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: 300,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              border: '3px solid var(--color-bg-tertiary)',
              borderTopColor: 'var(--color-primary)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }}
          />
        </div>
      ) : (
        activeTab === 'open' ? renderGroupList(openGroups) : renderGroupList(successGroups)
      )}

      {/* 创建团购弹窗 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-bento-sm)',
                background: 'var(--color-primary-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <PlusOutlined style={{ color: 'var(--color-primary)' }} />
            </div>
            <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-text-primary)' }}>
              发起团购
            </span>
          </div>
        }
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
            <Select placeholder="请选择商品" style={{ borderRadius: 'var(--radius-bento-sm)' }}>
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
            <InputNumber
              min={1}
              style={{ width: '100%', borderRadius: 'var(--radius-bento-sm)' }}
              placeholder="例如：50"
            />
          </Form.Item>

          <Form.Item
            name="deadlineHours"
            label="成团时限 (小时)"
            initialValue={24}
            rules={[{ required: true, message: '请输入成团时限' }]}
          >
            <InputNumber
              min={1}
              max={720}
              style={{ width: '100%', borderRadius: 'var(--radius-bento-sm)' }}
            />
          </Form.Item>

          <Form.Item
            name="leaderId"
            label="团长 ID"
            rules={[{ required: true, message: '请输入团长 ID' }]}
          >
            <Input
              placeholder="例如：user_001"
              style={{ borderRadius: 'var(--radius-bento-sm)' }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setCreateModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">发起团购</Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default GroupsPage
