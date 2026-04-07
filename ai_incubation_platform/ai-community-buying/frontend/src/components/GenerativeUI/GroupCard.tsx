/**
 * Generative UI - 团购卡片组件
 * 显示团购进度、成团概率、倒计时等
 */
import React from 'react'
import { Card, Progress, Tag, Button, Space, Statistic, Typography } from 'antd'
import {
  TeamOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FireOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import type { GroupData, PredictionData } from '@/types/chat'

const { Text } = Typography

interface GenerativeGroupCardProps {
  group: GroupData
  prediction?: PredictionData
  onJoin?: (group: GroupData) => void
  onShare?: (group: GroupData) => void
  onViewDetail?: (group: GroupData) => void
  compact?: boolean
}

export const GenerativeGroupCard: React.FC<GenerativeGroupCardProps> = ({
  group,
  prediction,
  onJoin,
  onShare,
  onViewDetail,
  compact = false,
}) => {
  const progress = group.current_participants && group.min_participants
    ? Math.round((group.current_participants / group.min_participants) * 100)
    : 0

  const isCompleted = group.status === 'completed' || progress >= 100
  const isUrgent = !isCompleted && group.deadline &&
    new Date(group.deadline).getTime() - Date.now() < 3600000 // 1 小时内

  const successProbability = prediction?.success_probability ||
    group.min_participants ? progress : 0

  const getStatusColor = () => {
    if (isCompleted) return 'success' as const
    if (isUrgent) return 'exception' as const
    if (successProbability > 80) return 'success' as const
    if (successProbability > 50) return 'normal' as const
    return 'active' as const
  }

  const getStatusText = () => {
    if (isCompleted) return '已成团'
    if (isUrgent) return '即将截止'
    if (successProbability > 80) return '很可能成团'
    if (successProbability > 50) return '可能成团'
    return '需要更多人参团'
  }

  return (
    <Card
      size={compact ? 'small' : 'default'}
      style={{
        width: compact ? 300 : 380,
        borderLeft: `4px solid ${
          isCompleted ? '#52c41a' : isUrgent ? '#ff4d4f' : '#1890ff'
        }`,
      }}
      title={
        <Space>
          <span>{group.product_name}</span>
          <Tag color="blue">
            {group.current_participants || 0}/{group.min_participants}
          </Tag>
        </Space>
      }
      extra={
        prediction?.confidence && (
          <Tag color={
            prediction.confidence === 'high' ? 'green' :
            prediction.confidence === 'medium' ? 'orange' : 'red'
          }>
            {prediction.confidence === 'high' ? '高置信' :
             prediction.confidence === 'medium' ? '中置信' : '低置信'}
          </Tag>
        )
      }
    >
      {compact ? (
        <div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ff4d4f' }}>
              ¥{group.group_price.toFixed(2)}
              <span style={{ fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                {' '}成团价
              </span>
            </div>
          </div>

          <Progress
            percent={progress}
            strokeColor={{
              '0%': '#1890ff',
              '100%': '#52c41a',
            }}
            status={getStatusColor()}
            format={() => getStatusText()}
          />

          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between' }}>
            <Statistic
              title="目标人数"
              value={group.min_participants}
              suffix="人"
              valueStyle={{ fontSize: 14 }}
            />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: '#666' }}>截止时间</div>
              <Text style={{ fontSize: 12, color: isUrgent ? '#ff4d4f' : '#1890ff' }}>
                {new Date(group.deadline).toLocaleString('zh-CN', {
                  month: 'numeric',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Text>
            </div>
          </div>

          {prediction?.factors && prediction.factors.length > 0 && (
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              <ExclamationCircleOutlined />{' '}
              {prediction.factors.slice(0, 2).join('，')}
            </div>
          )}

          {!isCompleted && (
            <Space wrap style={{ marginTop: 12 }}>
              <Button
                type="primary"
                size="small"
                icon={<TeamOutlined />}
                onClick={() => onJoin?.(group)}
              >
                立即参团
              </Button>
              <Button
                size="small"
                icon={<FireOutlined />}
                onClick={() => onShare?.(group)}
              >
                邀请好友
              </Button>
              <Button
                size="small"
                onClick={() => onViewDetail?.(group)}
              >
                详情
              </Button>
            </Space>
          )}
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Space size="large">
              <Statistic
                title="成团价"
                value={group.group_price}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#ff4d4f', fontWeight: 'bold' }}
              />
              <Statistic
                title="进度"
                value={group.current_participants || 0}
                suffix={`/ ${group.min_participants}人`}
                valueStyle={{ color: '#1890ff' }}
              />
              {group.status === 'completed' && (
                <Statistic
                  title="状态"
                  value="已成团"
                  valueStyle={{ color: '#52c41a' }}
                />
              )}
            </Space>
          </div>

          <Progress
            percent={progress}
            strokeColor={{
              '0%': '#1890ff',
              '100%': '#52c41a',
            }}
            status={getStatusColor()}
            format={(percent) => (
              <span style={{ fontWeight: 500 }}>
                {percent}% - {getStatusText()}
              </span>
            )}
          />

          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                <ClockCircleOutlined /> 剩余时间
              </div>
              <Text style={{ fontSize: 18, color: isUrgent ? '#ff4d4f' : '#1890ff' }}>
                {new Date(group.deadline).toLocaleString('zh-CN', {
                  month: 'numeric',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Text>
            </div>

            {successProbability > 0 && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                  <TrophyOutlined /> 成团概率
                </div>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#52c41a' }}>
                  {successProbability}%
                </div>
              </div>
            )}
          </div>

          {prediction?.factors && prediction.factors.length > 0 && (
            <div style={{ marginTop: 12, padding: '8px 12px', background: '#f5f5f5', borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                <ExclamationCircleOutlined /> 影响因素
              </div>
              <div style={{ fontSize: 12, color: '#333' }}>
                {prediction.factors.join(',')}
              </div>
            </div>
          )}

          {!compact && (
            <Space wrap style={{ marginTop: 16 }}>
              {!isCompleted && (
                <>
                  <Button
                    type="primary"
                    icon={<TeamOutlined />}
                    onClick={() => onJoin?.(group)}
                  >
                    立即参团
                  </Button>
                  <Button
                    icon={<FireOutlined />}
                    onClick={() => onShare?.(group)}
                  >
                    邀请好友
                  </Button>
                </>
              )}
              <Button
                onClick={() => onViewDetail?.(group)}
              >
                查看详情
              </Button>
            </Space>
          )}
        </div>
      )}
    </Card>
  )
}

/**
 * 团购列表组件
 */
interface GroupListProps {
  groups: GroupData[]
  predictions?: Record<string, PredictionData>
  onJoin?: (group: GroupData) => void
  onShare?: (group: GroupData) => void
  onViewDetail?: (group: GroupData) => void
}

export const GroupList: React.FC<GroupListProps> = ({
  groups,
  predictions,
  onJoin,
  onShare,
  onViewDetail,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {groups.map((group, index) => (
        <GenerativeGroupCard
          key={group.id || index}
          group={group}
          prediction={predictions?.[String(group.id)]}
          onJoin={onJoin}
          onShare={onShare}
          onViewDetail={onViewDetail}
          compact={false}
        />
      ))}
    </div>
  )
}
