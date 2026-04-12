/**
 * 仪表板组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  List,
  Space,
  Divider,
  Row,
  Col,
  Statistic,
  Progress,
  Avatar
} from 'antd'
import {
  LineChartOutlined,
  WarningOutlined,
  SyncOutlined,
  CalendarOutlined,
  HeartFilled
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 风控仪表板
 */
export const RiskControlDashboard: React.FC<{
  metrics?: any
  risks?: any[]
}> = ({ metrics, risks }) => {
  return (
    <Card
      className="risk-control-dashboard"
      title={
        <Space>
          <LineChartOutlined />
          风控仪表板
        </Space>
      }
    >
      {metrics && (
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic
              title="活跃用户"
              value={metrics.active_users}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="互动率"
              value={Math.round(metrics.engagement_rate * 100)}
              suffix="%"
              valueStyle={{ color: metrics.engagement_trend === 'up' ? '#52c41a' : '#faad14' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="风险事件"
              value={metrics.risk_events}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
        </Row>
      )}

      <Divider />

      {risks && risks.length > 0 && (
        <div className="risks-section">
          <Title level={5}>风险事件</Title>
          <List
            size="small"
            dataSource={risks.slice(0, 5)}
            renderItem={(risk: any) => (
              <List.Item>
                <Tag color="red">{risk.type}</Tag>
                <Text>{risk.description}</Text>
              </List.Item>
            )}
          />
        </div>
      )}
    </Card>
  )
}

/**
 * 风险评估仪表板
 */
export const RiskAssessmentDashboard: React.FC<{ assessment?: any }> = ({ assessment }) => {
  if (!assessment) {
    return <Card className="risk-assessment-dashboard"><Text type="secondary">暂无风险评估数据</Text></Card>
  }

  return (
    <Card
      className="risk-assessment-dashboard"
      title={
        <Space>
          <WarningOutlined />
          风险评估
        </Space>
      }
    >
      <div className="risk-score">
        <Progress
          type="dashboard"
          percent={Math.round(assessment.risk_score * 100)}
          status={assessment.risk_level === 'high' ? 'exception' : 'normal'}
        />
        <Text>风险得分</Text>
      </div>

      <Divider />

      <div className="risk-factors">
        <Title level={6}>风险因素</Title>
        <List
          size="small"
          dataSource={assessment.risk_factors || []}
          renderItem={(factor: string) => (
            <List.Item>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              {factor}
            </List.Item>
          )}
        />
      </div>
    </Card>
  )
}

/**
 * 分享增长仪表板
 */
export const ShareGrowthDashboard: React.FC<{
  metrics?: any
  invites?: any[]
}> = ({ metrics, invites }) => {
  return (
    <Card
      className="share-growth-dashboard"
      title={
        <Space>
          <SyncOutlined spin />
          分享增长
        </Space>
      }
    >
      {metrics && (
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="分享次数"
              value={metrics.share_count}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="转化率"
              value={Math.round(metrics.conversion_rate * 100)}
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="病毒系数"
              value={metrics.k_factor}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="新增用户"
              value={metrics.new_users}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
        </Row>
      )}

      {invites && invites.length > 0 && (
        <>
          <Divider />
          <div className="invites-section">
            <Title level={5}>邀请记录</Title>
            <List
              size="small"
              dataSource={invites.slice(0, 5)}
              renderItem={(invite: any) => (
                <List.Item>
                  <Text>{invite.target}</Text>
                  <Tag color={invite.status === 'accepted' ? 'green' : 'gray'}>
                    {invite.status}
                  </Tag>
                </List.Item>
              )}
            />
          </div>
        </>
      )}
    </Card>
  )
}

/**
 * 活动导演仪表板
 */
export const ActivityDirectorDashboard: React.FC<{
  activities?: any[]
  recommendations?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ activities, recommendations, onAction }) => {
  return (
    <Card
      className="activity-director-dashboard"
      title={
        <Space>
          <CalendarOutlined />
          活动导演
        </Space>
      }
    >
      {recommendations && recommendations.length > 0 && (
        <div className="recommendations-section">
          <Title level={5}>推荐活动</Title>
          <List
            dataSource={recommendations}
            renderItem={(item: any) => (
              <List.Item
                actions={[
                  <Button
                    key="select"
                    type="link"
                    onClick={() => onAction?.({ type: 'select_activity', item })}
                  >
                    选择
                  </Button>
                ]}
              >
                <List.Item.Meta
                  title={item.name}
                  description={`${item.duration} · ¥${item.budget}`}
                />
              </List.Item>
            )}
          />
        </div>
      )}

      {activities && activities.length > 0 && (
        <>
          <Divider />
          <div className="activities-section">
            <Title level={5}>历史活动</Title>
            <List
              size="small"
              dataSource={activities}
              renderItem={(activity: any) => (
                <List.Item>
                  <Text>{activity.name}</Text>
                  <Text type="secondary">{activity.date}</Text>
                </List.Item>
              )}
            />
          </div>
        </>
      )}
    </Card>
  )
}

/**
 * 对话匹配仪表板
 */
export const ConversationMatchmakerDashboard: React.FC<{
  matches?: any[]
  intents?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ matches, intents, onAction }) => {
  return (
    <Card
      className="conversation-matchmaker-dashboard"
      title={
        <Space>
          <HeartFilled style={{ color: '#FF8FAB' }} />
          对话匹配
        </Space>
      }
    >
      {intents && intents.length > 0 && (
        <div className="intents-section">
          <Title level={5}>用户意图</Title>
          <List
            size="small"
            dataSource={intents}
            renderItem={(intent: any) => (
              <List.Item>
                <Tag color="blue">{intent.type}</Tag>
                <Text>{intent.description}</Text>
              </List.Item>
            )}
          />
        </div>
      )}

      {matches && matches.length > 0 && (
        <>
          <Divider />
          <div className="matches-section">
            <Title level={5}>匹配推荐</Title>
            <List
              dataSource={matches}
              renderItem={(match: any) => (
                <List.Item
                  actions={[
                    <Button
                      key="view"
                      type="link"
                      onClick={() => onAction?.({ type: 'view_match', match })}
                    >
                      查看
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    avatar={<Avatar src={match.avatar} />}
                    title={match.name}
                    description={`${Math.round(match.score * 100)}% 匹配`}
                  />
                </List.Item>
              )}
            />
          </div>
        </>
      )}
    </Card>
  )
}