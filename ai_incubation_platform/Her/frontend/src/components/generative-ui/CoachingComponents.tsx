/**
 * 教练与模拟组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Button,
  List,
  Space,
  Divider,
  Row,
  Col,
  Statistic,
  Timeline,
  Progress,
  Alert,
  Empty
} from 'antd'
import {
  CameraOutlined,
  ShoppingOutlined,
  ExperimentOutlined,
  DashboardOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  HeartFilled
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 视频约会教练仪表板
 */
export const VideoDateCoachDashboard: React.FC<{
  coaching?: any
  outfit?: any
  icebreakers?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ coaching, outfit, icebreakers, onAction }) => {
  return (
    <Card
      className="video-date-coach-dashboard"
      title={
        <Space>
          <CameraOutlined />
          视频约会教练
        </Space>
      }
    >
      {outfit && (
        <div className="outfit-section">
          <Title level={5}>
            <ShoppingOutlined /> 着装建议
          </Title>
          <Alert message={outfit.suggestion} type="info" showIcon />
        </div>
      )}

      <Divider />

      {icebreakers && icebreakers.length > 0 && (
        <div className="icebreaker-section">
          <Title level={5}>破冰话题</Title>
          <List
            size="small"
            dataSource={icebreakers}
            renderItem={(item: any) => (
              <List.Item
                actions={[
                  <Button
                    key="use"
                    type="link"
                    size="small"
                    onClick={() => onAction?.({ type: 'use_icebreaker', item })}
                  >
                    使用
                  </Button>
                ]}
              >
                <List.Item.Meta description={item} />
              </List.Item>
            )}
          />
        </div>
      )}

      {coaching && (
        <div className="coaching-section">
          <Title level={5}>实时指导</Title>
          <Paragraph type="secondary">{coaching.tip}</Paragraph>
        </div>
      )}
    </Card>
  )
}

/**
 * 约会模拟反馈
 */
export const DateSimulationFeedback: React.FC<{ feedback?: any }> = ({ feedback }) => {
  if (!feedback) {
    return <Card className="date-simulation-feedback"><Empty description="暂无模拟反馈" /></Card>
  }

  return (
    <Card className="date-simulation-feedback" title={<><ExperimentOutlined /> 模拟反馈</>}>
      <div className="simulation-score">
        <Statistic title="综合得分" value={feedback.score} suffix="/100" />
      </div>

      <Divider />

      <div className="simulation-details">
        <Title level={6}>优势</Title>
        <List
          size="small"
          dataSource={feedback.strengths || []}
          renderItem={(s: string) => (
            <List.Item>
              <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
              {s}
            </List.Item>
          )}
        />

        <Title level={6}>改进建议</Title>
        <List
          size="small"
          dataSource={feedback.improvements || []}
          renderItem={(s: string) => (
            <List.Item>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              {s}
            </List.Item>
          )}
        />
      </div>
    </Card>
  )
}

/**
 * 绩效教练仪表板
 */
export const PerformanceCoachDashboard: React.FC<{
  metrics?: any
  milestones?: any[]
  suggestions?: any[]
}> = ({ metrics, milestones, suggestions }) => {
  return (
    <Card
      className="performance-coach-dashboard"
      title={
        <Space>
          <DashboardOutlined />
          绩效教练
        </Space>
      }
    >
      {metrics && (
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="互动频率"
              value={metrics.interaction_frequency}
              suffix={metrics.interaction_trend === 'up' ? '↑' : '↓'}
            />
          </Col>
          <Col span={12}>
            <Statistic title="关系得分" value={metrics.relationship_score} suffix="/100" />
          </Col>
          <Col span={12}>
            <Statistic title="连续天数" value={metrics.streak_days} suffix="天" />
          </Col>
          <Col span={12}>
            <Statistic title="约会次数" value={metrics.date_count} suffix="次" />
          </Col>
        </Row>
      )}

      <Divider />

      {milestones && milestones.length > 0 && (
        <div className="milestones-section">
          <Title level={5}>里程碑进度</Title>
          <Timeline
            items={
              milestones.map((m, i) => ({
                children: (
                  <div>
                    <Text>{m.name}</Text>
                    <Progress
                      percent={Math.round(m.progress * 100)}
                      size="small"
                      format={null}
                    />
                  </div>
                ),
                color: m.completed ? 'green' : 'blue'
              })) || []
            }
          />
        </div>
      )}

      {suggestions && suggestions.length > 0 && (
        <div className="suggestions-section">
          <Title level={5}>改进建议</Title>
          <List
            size="small"
            dataSource={suggestions}
            renderItem={(s: any) => (
              <List.Item>
                <HeartFilled style={{ marginRight: 8, color: '#FF8FAB' }} />
                {s.text}
              </List.Item>
            )}
          />
        </div>
      )}
    </Card>
  )
}

/**
 * 教练空状态
 */
export const CoachEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="coach-empty-card">
      <Empty
        image={<HeartFilled style={{ fontSize: 48, color: '#FF8FAB' }} />}
        description={message || '暂无教练建议'}
      />
    </Card>
  )
}