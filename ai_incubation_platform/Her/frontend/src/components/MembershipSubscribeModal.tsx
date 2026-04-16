/**
 * 会员订阅 Modal
 *
 * 实现会员订阅流程：
 * 1. 显示会员计划选择
 * 2. 选择支付方式
 * 3. 创建订单并跳转支付
 */

import React, { useState, useEffect } from 'react'
import { Modal, Card, Radio, Button, Space, Typography, Tag, List, Divider, Spin, message, Alert } from 'antd'
import { CrownOutlined, CheckCircleOutlined, WechatOutlined, AlipayCircleOutlined } from '@ant-design/icons'
import membershipApi, { MembershipPlan, MembershipStatus } from '../api/membershipApi'

const { Text, Title, Paragraph } = Typography

// 主题色
const GOLD_COLOR = '#FFD700'
const PRIMARY_COLOR = '#C88B8B'

interface MembershipSubscribeModalProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

/**
 * 会员订阅 Modal 组件
 */
const MembershipSubscribeModal: React.FC<MembershipSubscribeModalProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const [loading, setLoading] = useState(true)
  const [plans, setPlans] = useState<MembershipPlan[]>([])
  const [currentStatus, setCurrentStatus] = useState<MembershipStatus | null>(null)
  const [selectedTier, setSelectedTier] = useState<string>('premium')
  const [selectedDuration, setSelectedDuration] = useState<number>(1)
  const [paymentMethod, setPaymentMethod] = useState<'wechat' | 'alipay'>('wechat')
  const [submitting, setSubmitting] = useState(false)
  const [orderResult, setOrderResult] = useState<{ payment_url?: string; amount: number } | null>(null)

  // 加载会员计划和当前状态
  useEffect(() => {
    if (open) {
      loadData()
    }
  }, [open])

  const loadData = async () => {
    setLoading(true)
    try {
      // 获取会员计划（公开 API，不需要认证）
      const plansData = await membershipApi.getPlans()
      setPlans(plansData)

      // 默认选择热门计划
      const popularPlan = plansData.find(p => p.popular)
      if (popularPlan) {
        setSelectedTier(popularPlan.tier)
        setSelectedDuration(popularPlan.duration_months)
      }

      // 尝试获取会员状态（需要认证，失败时显示默认免费状态）
      try {
        const statusData = await membershipApi.getStatus()
        setCurrentStatus(statusData)
      } catch (statusError: any) {
        // 认证失败时，显示默认免费会员状态
        if (statusError.status === 401) {
          setCurrentStatus({
            tier: 'free',
            status: 'inactive',
            is_active: false,
            auto_renew: false,
            features: [],
            limits: {},
          })
        } else {
          console.warn('获取会员状态失败:', statusError.message)
        }
      }
    } catch (error: any) {
      message.error(error.message || '加载会员信息失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取当前选中的计划
  const getSelectedPlan = (): MembershipPlan | undefined => {
    return plans.find(p => p.tier === selectedTier && p.duration_months === selectedDuration)
  }

  // 创建订单并支付
  const handleSubscribe = async () => {
    const plan = getSelectedPlan()
    if (!plan) {
      message.error('请选择会员计划')
      return
    }

    setSubmitting(true)
    try {
      const order = await membershipApi.createOrder({
        tier: selectedTier,
        duration_months: selectedDuration,
        payment_method: paymentMethod,
        auto_renew: false,
      })

      message.success('订单创建成功')

      // 显示支付结果
      setOrderResult({
        payment_url: order.payment_url,
        amount: order.amount,
      })

      // 如果有支付链接，提示用户跳转
      if (order.payment_url) {
        Modal.confirm({
          title: '支付提示',
          content: (
            <Space direction="vertical">
              <Text>订单金额：¥{order.amount}</Text>
              <Text>请在新窗口完成支付后返回</Text>
            </Space>
          ),
          okText: '前往支付',
          cancelText: '稍后支付',
          onOk: () => {
            window.open(order.payment_url, '_blank')
            // 刷新会员状态
            loadData()
            onSuccess?.()
          },
          onCancel: () => {
            loadData()
          },
        })
      } else {
        // 模拟支付成功（开发环境）
        message.info('开发环境：模拟支付成功')
        loadData()
        onSuccess?.()
      }
    } catch (error: any) {
      // 认证失败时，提示用户重新登录
      if (error.status === 401) {
        Modal.confirm({
          title: '登录已过期',
          content: '您的登录状态已过期，请重新登录后再订阅会员',
          okText: '重新登录',
          cancelText: '取消',
          onOk: () => {
            // 清除本地存储的过期 token
            localStorage.removeItem('auth_token')
            localStorage.removeItem('auth_user')
            // 跳转到登录页面（刷新页面会触发 App.tsx 的登录检查）
            window.location.reload()
          },
        })
      } else {
        message.error(error.message || '创建订单失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  // 渲染计划选择
  const renderPlanSelection = () => {
    // 按等级分组
    const tierGroups = {
      standard: plans.filter(p => p.tier === 'standard'),
      premium: plans.filter(p => p.tier === 'premium'),
    }

    return (
      <div className="plan-selection">
        {/* 等级选择 */}
        <div style={{ marginBottom: 16 }}>
          <Text strong>选择会员等级：</Text>
          <Radio.Group
            value={selectedTier}
            onChange={(e) => setSelectedTier(e.target.value)}
            style={{ marginTop: 8 }}
          >
            <Radio.Button value="standard">标准会员</Radio.Button>
            <Radio.Button value="premium">
              <CrownOutlined style={{ color: GOLD_COLOR }} />
              高级会员
            </Radio.Button>
          </Radio.Group>
        </div>

        {/* 时长选择 */}
        <div style={{ marginBottom: 16 }}>
          <Text strong>订阅时长：</Text>
          <Radio.Group
            value={selectedDuration}
            onChange={(e) => setSelectedDuration(e.target.value)}
            style={{ marginTop: 8 }}
          >
            {tierGroups[selectedTier]?.map((plan) => (
              <Radio.Button key={plan.duration_months} value={plan.duration_months}>
                {plan.duration_months === 1 ? '月度' :
                 plan.duration_months === 3 ? '季度' : '年度'}
                {plan.discount_rate > 0 && (
                  <Tag color="red" style={{ marginLeft: 4 }}>
                    省{Math.round(plan.discount_rate * 100)}%
                  </Tag>
                )}
              </Radio.Button>
            ))}
          </Radio.Group>
        </div>

        {/* 价格显示 */}
        {getSelectedPlan() && (
          <Card size="small" style={{ background: '#f6ffed', marginBottom: 16 }}>
            <Space>
              <Text>应付金额：</Text>
              <Text strong style={{ fontSize: 24, color: PRIMARY_COLOR }}>
                ¥{getSelectedPlan()!.price}
              </Text>
              {getSelectedPlan()!.discount_rate > 0 && (
                <Text type="secondary">
                  原价 ¥{getSelectedPlan()!.original_price}
                </Text>
              )}
            </Space>
          </Card>
        )}

        {/* 权益列表 */}
        {getSelectedPlan() && (
          <div style={{ marginBottom: 16 }}>
            <Text strong>会员权益：</Text>
            <List
              size="small"
              dataSource={getSelectedPlan()!.features}
              renderItem={(feature) => (
                <List.Item style={{ border: 'none', padding: '4px 0' }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <Text>{feature}</Text>
                </List.Item>
              )}
            />
          </div>
        )}
      </div>
    )
  }

  // 渲染支付方式选择
  const renderPaymentSelection = () => {
    return (
      <div style={{ marginBottom: 16 }}>
        <Text strong>支付方式：</Text>
        <Radio.Group
          value={paymentMethod}
          onChange={(e) => setPaymentMethod(e.target.value)}
          style={{ marginTop: 8 }}
        >
          <Radio value="wechat">
            <WechatOutlined style={{ color: '#07C160', fontSize: 20 }} />
            微信支付
          </Radio>
          <Radio value="alipay">
            <AlipayCircleOutlined style={{ color: '#1677FF', fontSize: 20 }} />
            支付宝
          </Radio>
        </Radio.Group>
      </div>
    )
  }

  // 当前会员状态提示
  const renderCurrentStatus = () => {
    if (!currentStatus) return null

    if (currentStatus.is_active && currentStatus.tier !== 'free') {
      return (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={`您当前是 ${currentStatus.tier === 'premium' ? '高级' : '标准'}会员`}
          description={
            currentStatus.end_date
              ? `有效期至：${new Date(currentStatus.end_date).toLocaleDateString()}`
              : '永久有效'
          }
        />
      )
    }

    return null
  }

  return (
    <Modal
      title={
        <Space>
          <CrownOutlined style={{ color: GOLD_COLOR }} />
          <span>会员订阅</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={500}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="subscribe"
          type="primary"
          loading={submitting}
          onClick={handleSubscribe}
          style={{
            background: GOLD_COLOR,
            borderColor: GOLD_COLOR,
          }}
        >
          立即订阅
        </Button>,
      ]}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载会员信息...">
            <div style={{ padding: 50 }} />
          </Spin>
        </div>
      ) : (
        <div className="membership-subscribe-content">
          {renderCurrentStatus()}
          {renderPlanSelection()}
          <Divider />
          {renderPaymentSelection()}
        </div>
      )}

      <style>{`
        .membership-subscribe-content .ant-radio-button-wrapper {
          border-radius: 8px;
          margin-right: 8px;
        }
        .membership-subscribe-content .ant-radio-button-wrapper-checked {
          border-color: ${PRIMARY_COLOR};
        }
      `}</style>
    </Modal>
  )
}

export default MembershipSubscribeModal