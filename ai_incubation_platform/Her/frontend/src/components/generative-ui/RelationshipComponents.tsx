/**
 * 关系进展相关组件
 */
import React from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Timeline,
  Progress,
  Row,
  Col,
  Descriptions,
  Divider,
  Space,
  List,
  Statistic
} from 'antd'
import {
  TrophyOutlined,
  ClockCircleOutlined,
  HeartOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  LineChartOutlined,
  CalendarOutlined
} from '@ant-design/icons'
import type { GenerativeAction } from './types'

const { Title, Text, Paragraph } = Typography

/**
 * 里程碑时间轴
 */
export const MilestoneTimeline: React.FC<{ milestones: any[] }> = ({ milestones }) => {
  return (
    <Card className="milestone-timeline-card" title={<><TrophyOutlined /> 关系里程碑</>}>
      <Timeline
        items={
          milestones?.map((milestone, i) => ({
            children: (
              <div className="milestone-item">
                <Title level={5}>{milestone.name}</Title>
                <Text type="secondary">{milestone.date}</Text>
                <Paragraph type="secondary">{milestone.description}</Paragraph>
                {milestone.achieved && (
                  <Tag color="green">
                    <CheckCircleOutlined /> 已完成
                  </Tag>
                )}
              </div>
            ),
            color: milestone.achieved ? 'green' : 'gray'
          })) || []
        }
      />
    </Card>
  )
}

/**
 * 关系时间线
 */
export const RelationshipTimeline: React.FC<{
  current_stage?: string
  milestones?: any[]
  show_progress_indicator?: boolean
  onAction?: (action: GenerativeAction) => void
}> = ({ current_stage, milestones, show_progress_indicator, onAction }) => {
  return (
    <Card className="relationship-timeline-card" title={<><ClockCircleOutlined /> 关系时间线</>}>
      {show_progress_indicator && current_stage && (
        <div className="current-stage-display">
          <Tag color="red" style={{ fontSize: 14 }}>当前阶段：{current_stage}</Tag>
        </div>
      )}

      <Timeline
        items={
          milestones?.map((milestone, i) => ({
            children: (
              <div className="timeline-item">
                <Title level={5}>{milestone.progress_type_label || milestone.name}</Title>
                <Text type="secondary">{milestone.date || milestone.created_at}</Text>
                <Paragraph type="secondary">{milestone.description}</Paragraph>
                {milestone.progress_score && (
                  <Progress
                    percent={milestone.progress_score * 10}
                    size="small"
                    format={(percent: number) => `${percent}分`}
                  />
                )}
              </div>
            ),
            color: milestone.achieved ? 'green' : 'blue'
          })) || []
        }
      />

      <Divider />

      <Space>
        <Button type="primary" onClick={() => onAction?.({ type: 'record_progress' })}>
          记录新进展
        </Button>
        <Button onClick={() => onAction?.({ type: 'view_health' })}>查看健康度</Button>
      </Space>
    </Card>
  )
}

/**
 * 关系健康度评分卡
 */
export const HealthScoreCard: React.FC<{
  score: number
  max_score?: number
  level?: string
  color?: string
  dimensions?: Record<string, number>
  suggestions?: string[]
  onAction?: (action: GenerativeAction) => void
}> = ({ score, max_score = 10, level, color = 'blue', dimensions, suggestions, onAction }) => {
  const percentage = Math.round((score / max_score) * 100)

  const getLevelColor = (lvl?: string) => {
    const colorMap: Record<string, string> = {
      excellent: '#52c41a',
      good: '#1890ff',
      fair: '#faad14',
      needs_attention: '#ff4d4f',
      no_data: '#d9d9d9'
    }
    return colorMap[lvl || 'no_data'] || color
  }

  const getLevelLabel = (lvl?: string) => {
    const labelMap: Record<string, string> = {
      excellent: '优秀',
      good: '良好',
      fair: '一般',
      needs_attention: '需要关注',
      no_data: '暂无数据'
    }
    return labelMap[lvl || 'no_data'] || level
  }

  return (
    <Card className="health-score-card" title={<><HeartOutlined /> 关系健康度</>}>
      <div className="health-score-display">
        <div className="score-circle">
          <Progress
            type="circle"
            percent={percentage}
            strokeColor={getLevelColor(level)}
            size={120}
            format={(percent: number) => `${score}/${max_score}`}
          />
          <div className="score-label" style={{ color: getLevelColor(level) }}>
            {getLevelLabel(level)}
          </div>
        </div>
      </div>

      {dimensions && Object.keys(dimensions).length > 0 && (
        <>
          <Divider />
          <div className="health-dimensions">
            <Title level={6}>维度分析</Title>
            <Row gutter={[16, 16]}>
              {Object.entries(dimensions).map(([key, value]) => (
                <Col span={12} key={key}>
                  <div className="dimension-item">
                    <Text>{key}</Text>
                    <Progress
                      percent={Math.round(value * 100)}
                      strokeColor={getLevelColor(level)}
                      format={null}
                      size="small"
                    />
                  </div>
                </Col>
              ))}
            </Row>
          </div>
        </>
      )}

      {suggestions && suggestions.length > 0 && (
        <>
          <Divider />
          <div className="health-suggestions">
            <Title level={6}>改进建议</Title>
            <List
              size="small"
              dataSource={suggestions}
              renderItem={(suggestion: string, index: number) => (
                <List.Item>
                  <Text type="secondary">{index + 1}. {suggestion}</Text>
                </List.Item>
              )}
            />
          </div>
        </>
      )}

      <Divider />

      <Space>
        <Button onClick={() => onAction?.({ type: 'record_progress' })}>记录新进展</Button>
        <Button type="primary" onClick={() => onAction?.({ type: 'view_timeline' })}>
          查看时间线
        </Button>
      </Space>
    </Card>
  )
}

/**
 * 关系趋势图
 */
export const RelationshipChart: React.FC<{
  chart_type?: string
  labels?: string[]
  activity_data?: number[]
  stage_changes?: any[]
  onAction?: (action: GenerativeAction) => void
}> = ({ chart_type = 'line', labels, activity_data, stage_changes, onAction }) => {
  return (
    <Card className="relationship-chart-card" title={<><LineChartOutlined /> 关系趋势</>}>
      <div className="chart-placeholder">
        <LineChartOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        <Paragraph type="secondary">
          互动频率趋势图（需集成图表库）
        </Paragraph>
        {labels && labels.length > 0 && (
          <div className="chart-data-preview">
            <Text type="secondary">数据点：{labels.length} 个</Text>
          </div>
        )}
      </div>

      <Divider />

      <Space>
        <Button onClick={() => onAction?.({ type: 'export_report' })}>导出报告</Button>
        <Button onClick={() => onAction?.({ type: 'share_timeline' })}>分享时间线</Button>
      </Space>
    </Card>
  )
}

/**
 * 关系综合仪表板
 */
export const RelationshipDashboard: React.FC<{
  summary?: string
  timeline?: any
  health_score?: any
  onAction?: (action: GenerativeAction) => void
}> = ({ summary, timeline, health_score, onAction }) => {
  return (
    <Card className="relationship-dashboard-card" title={<><DashboardOutlined /> 关系全景</>}>
      {summary && (
        <Paragraph className="dashboard-summary">{summary}</Paragraph>
      )}

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card size="small" title="关系阶段">
            <Title level={3}>{timeline?.current_stage_label || '未知'}</Title>
            <Text type="secondary">
              共同走过 {timeline?.total_milestones || 0} 个里程碑
            </Text>
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="健康度">
            <Title level={3} style={{ color: '#52c41a' }}>
              {health_score?.overall_score?.toFixed(1) || '-'}分
            </Title>
            <Text type="secondary">
              {health_score?.health_level === 'excellent' ? '关系非常健康' : '需要关注'}
            </Text>
          </Card>
        </Col>
      </Row>

      <Divider />

      <Space>
        <Button type="primary" onClick={() => onAction?.({ type: 'view_full_analysis' })}>
          查看详细分析
        </Button>
        <Button onClick={() => onAction?.({ type: 'create_plan' })}>制定关系计划</Button>
      </Space>
    </Card>
  )
}