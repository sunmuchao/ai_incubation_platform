/**
 * Bento Grid 风格数据概览组件
 * 使用模块化网格布局，每个统计指标呈矩形卡片
 */
import React from 'react'
import {
  ShoppingOutlined,
  TeamOutlined,
  FileTextOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  FireOutlined,
  TrophyOutlined,
} from '@ant-design/icons'

interface GroupBuy {
  id: string
  product?: { name: string }
  joinedCount: number
  targetQuantity: number
  status: string
  deadline: string
}

interface Order {
  id: string
  orderNo: string
  product?: { name: string }
  totalAmount: number
  status: string
  createdAt: string
}

interface DashboardStats {
  totalUsers?: number
  totalProducts?: number
  totalGroups?: number
  totalOrders?: number
  totalSales?: number
  growthRate?: number
  successRate?: number
}

interface DashboardProps {
  stats?: DashboardStats
  recentGroups?: GroupBuy[]
  recentOrders?: Order[]
}

// 统计卡片组件
const StatCard: React.FC<{
  title: string
  value: string | number
  icon?: React.ReactNode
  trend?: number
  color?: string
  delay?: number
}> = ({ title, value, icon, trend, color, delay = 0 }) => {
  return (
    <div
      className="bento-card"
      style={{
        animation: `fadeIn 0.3s ease-out ${delay * 0.1}s both`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            {title}
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: color || 'var(--color-text-primary)',
              lineHeight: 1.2,
            }}
          >
            {value}
          </div>
          {trend !== undefined && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                marginTop: 8,
                fontSize: 12,
              }}
            >
              {trend >= 0 ? (
                <RiseOutlined style={{ color: 'var(--color-success)' }} />
              ) : (
                <FallOutlined style={{ color: 'var(--color-error)' }} />
              )}
              <span style={{ color: trend >= 0 ? 'var(--color-success)' : 'var(--color-error)', fontWeight: 500 }}>
                {trend >= 0 ? '+' : ''}{trend}%
              </span>
              <span style={{ color: 'var(--color-text-tertiary)' }}>较上周</span>
            </div>
          )}
        </div>
        {icon && (
          <div
            style={{
              fontSize: 28,
              color: color || 'var(--color-primary)',
              opacity: 0.15,
            }}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}

// 小型团购卡片
const MiniGroupCard: React.FC<{ group: GroupBuy }> = ({ group }) => {
  const progress = Math.round((group.joinedCount / group.targetQuantity) * 100)

  const statusConfig: Record<string, { color: string; text: string }> = {
    open: { color: 'var(--color-primary)', text: '进行中' },
    success: { color: 'var(--color-success)', text: '已成团' },
    failed: { color: 'var(--color-error)', text: '已失败' },
    expired: { color: 'var(--color-text-tertiary)', text: '已过期' },
  }

  const status = statusConfig[group.status] || statusConfig.open

  return (
    <div
      style={{
        padding: '12px',
        borderRadius: 'var(--radius-bento-sm)',
        background: 'var(--color-bg-tertiary)',
        transition: 'background 0.2s ease',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--color-bg-card-hover)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'var(--color-bg-tertiary)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span
          className="tag"
          style={{
            background: status.color === 'var(--color-success)'
              ? 'var(--color-success-light)'
              : status.color === 'var(--color-error)'
              ? 'var(--color-error-light)'
              : 'var(--color-info-light)',
            color: status.color,
            fontSize: 11,
            padding: '2px 8px',
          }}
        >
          {status.text}
        </span>
        <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
          {new Date(group.deadline).toLocaleString('zh-CN', {
            month: 'numeric',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--color-text-primary)',
          marginBottom: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {group.product?.name || `团购 #${group.id}`}
      </div>
      <div style={{ height: 4, background: 'var(--color-bg-secondary)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${progress}%`,
            background: `linear-gradient(90deg,
              ${progress > 80 ? 'var(--color-success)' :
               progress > 50 ? 'var(--color-primary)' : 'var(--color-warning)'} 0%,
              ${progress > 80 ? 'var(--color-success-light)' :
               progress > 50 ? 'var(--color-info-light)' : 'var(--color-warning-light)'} 100%
            )`,
            borderRadius: 2,
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 4 }}>
        {group.joinedCount} / {group.targetQuantity} 人
      </div>
    </div>
  )
}

// 小型订单卡片
const MiniOrderCard: React.FC<{ order: Order }> = ({ order }) => {
  const statusConfig: Record<string, { color: string; text: string }> = {
    pending: { color: 'var(--color-warning)', text: '待支付' },
    paid: { color: 'var(--color-primary)', text: '已支付' },
    shipped: { color: 'var(--color-info)', text: '已发货' },
    completed: { color: 'var(--color-success)', text: '已完成' },
    cancelled: { color: 'var(--color-error)', text: '已取消' },
    refunded: { color: 'var(--color-text-tertiary)', text: '已退款' },
  }

  const status = statusConfig[order.status] || statusConfig.pending

  return (
    <div
      style={{
        padding: '12px',
        borderRadius: 'var(--radius-bento-sm)',
        background: 'var(--color-bg-tertiary)',
        transition: 'background 0.2s ease',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--color-bg-card-hover)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'var(--color-bg-tertiary)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
          {order.orderNo}
        </span>
        <span
          className="tag"
          style={{
            background: status.color === 'var(--color-success)'
              ? 'var(--color-success-light)'
              : status.color === 'var(--color-error)'
              ? 'var(--color-error-light)'
              : status.color === 'var(--color-warning)'
              ? 'var(--color-warning-light)'
              : 'var(--color-info-light)',
            color: status.color,
            fontSize: 11,
            padding: '2px 8px',
          }}
        >
          {status.text}
        </span>
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--color-text-primary)',
          marginBottom: 4,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {order.product?.name || '商品'}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-primary)' }}>
        ¥{order.totalAmount.toFixed(2)}
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-text-tertiary)', marginTop: 4 }}>
        {new Date(order.createdAt).toLocaleString('zh-CN', {
          month: 'numeric',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })}
      </div>
    </div>
  )
}

const Dashboard: React.FC<DashboardProps> = ({
  stats,
  recentGroups = [],
  recentOrders = [],
}) => {
  const statCards = [
    {
      title: '用户总数',
      value: stats?.totalUsers || 0,
      icon: <ShoppingOutlined />,
      color: 'var(--color-primary)',
      trend: stats?.growthRate || 0,
    },
    {
      title: '商品总数',
      value: stats?.totalProducts || 0,
      icon: <ShoppingOutlined />,
      color: 'var(--color-success)',
      trend: 5.2,
    },
    {
      title: '团购总数',
      value: stats?.totalGroups || 0,
      icon: <TeamOutlined />,
      color: 'var(--color-warning)',
      trend: stats?.successRate || 0,
    },
    {
      title: '订单总数',
      value: stats?.totalOrders || 0,
      icon: <FileTextOutlined />,
      color: 'var(--color-info)',
      trend: 12.5,
    },
    {
      title: '销售总额',
      value: `¥${(stats?.totalSales || 0).toLocaleString()}`,
      icon: <DollarOutlined />,
      color: 'var(--color-success)',
      trend: 8.3,
    },
    {
      title: '成团率',
      value: `${stats?.successRate || 0}%`,
      icon: <TrophyOutlined />,
      color: 'var(--color-accent)',
      trend: 3.2,
    },
  ]

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
          数据概览
        </h1>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginTop: 4 }}>
          实时监控业务数据，掌握运营动态
        </p>
      </div>

      {/* 统计卡片网格 - Bento Grid 布局 */}
      <div
        className="bento-grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          marginBottom: 24,
        }}
      >
        {statCards.map((stat, index) => (
          <StatCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            trend={stat.trend}
            color={stat.color}
            delay={index}
          />
        ))}
      </div>

      {/* 最近团购和订单 - 双列布局 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: 'var(--gap-bento)',
        }}
      >
        {/* 最近团购 */}
        <div className="bento-card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FireOutlined style={{ color: 'var(--color-accent)', fontSize: 18 }} />
              <h2
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                最近团购
              </h2>
            </div>
          </div>

          {recentGroups.length > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 12,
              }}
            >
              {recentGroups.slice(0, 4).map((group) => (
                <MiniGroupCard key={group.id} group={group} />
              ))}
            </div>
          ) : (
            <div
              style={{
                padding: 40,
                textAlign: 'center',
                color: 'var(--color-text-tertiary)',
              }}
            >
              暂无团购数据
            </div>
          )}
        </div>

        {/* 最近订单 */}
        <div className="bento-card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileTextOutlined style={{ color: 'var(--color-primary)', fontSize: 18 }} />
              <h2
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                最近订单
              </h2>
            </div>
          </div>

          {recentOrders.length > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 12,
              }}
            >
              {recentOrders.slice(0, 4).map((order) => (
                <MiniOrderCard key={order.id} order={order} />
              ))}
            </div>
          ) : (
            <div
              style={{
                padding: 40,
                textAlign: 'center',
                color: 'var(--color-text-tertiary)',
              }}
            >
              暂无订单数据
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
