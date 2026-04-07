/**
 * 职业时间线组件
 * 展示 AI 生成的职业发展路径
 */
import React from 'react';
import { Timeline, Card, Tag, Progress, Typography, Space, Row, Col } from 'antd';
import {
  FlagOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
  BookOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import './CareerTimeline.less';

const { Title, Text, Paragraph } = Typography;

interface Milestone {
  name: string;
  description?: string;
  completed?: boolean;
  target_date?: string;
}

interface Phase {
  name: string;
  duration_months: number;
  milestones: Milestone[];
  focus_areas?: string[];
}

interface CareerTimelineProps {
  data?: {
    target_state?: {
      role_name: string;
      match_score: number;
    };
    development_phases?: Phase[];
    recommended_actions?: Array<{ action: string; priority: string }>;
    timeline?: {
      duration_months: number;
      start_date?: string;
    };
    [key: string]: any;
  };
}

const CareerTimeline: React.FC<CareerTimelineProps> = ({ data }) => {
  const phases = data?.development_phases || [];
  const targetState = data?.target_state;
  const timeline = data?.timeline;

  const getPhaseIcon = (index: number, total: number) => {
    if (index === 0) return <FlagOutlined />;
    if (index === total - 1) return <TrophyOutlined />;
    return <RocketOutlined />;
  };

  const getPhaseColor = (index: number) => {
    const colors = ['#722ed1', '#1890ff', '#52c41a', '#faad14'];
    return colors[index % colors.length];
  };

  return (
    <Card className="career-timeline-card" size="small">
      {targetState && (
        <div className="target-role">
          <div className="target-header">
            <TrophyOutlined className="target-icon" />
            <div className="target-info">
              <Text strong className="target-role-name">目标职位：{targetState.role_name}</Text>
              {targetState.match_score && (
                <Progress
                  type="line"
                  percent={targetState.match_score * 100}
                  size="small"
                  strokeColor={
                    targetState.match_score >= 0.8
                      ? '#52c41a'
                      : targetState.match_score >= 0.6
                      ? '#faad14'
                      : '#ff4d4f'
                  }
                  format={(percent) => `匹配度 ${percent}%`}
                />
              )}
            </div>
          </div>
          {timeline && (
            <Text type="secondary" className="target-timeline">
              预计耗时：{timeline.duration_months} 个月
            </Text>
          )}
        </div>
      )}

      <div className="phases-container">
        <Timeline
          mode="left"
          items={phases.map((phase, index) => ({
            color: getPhaseColor(index),
            children: (
              <div className="phase-item">
                <div className="phase-header">
                  <Space>
                    {getPhaseIcon(index, phases.length)}
                    <Text strong style={{ color: getPhaseColor(index) }}>
                      {phase.name}
                    </Text>
                  </Space>
                  <Tag color={getPhaseColor(index)}>{phase.duration_months}个月</Tag>
                </div>

                {phase.focus_areas && phase.focus_areas.length > 0 && (
                  <div className="phase-focus">
                    <Text type="secondary" className="focus-label">重点领域：</Text>
                    <Space wrap>
                      {phase.focus_areas.map((area, idx) => (
                        <Tag key={idx} color="default">
                          <BookOutlined /> {area}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}

                {phase.milestones && phase.milestones.length > 0 && (
                  <div className="phase-milestones">
                    <Text type="secondary" className="milestones-label">里程碑：</Text>
                    <Timeline
                      items={phase.milestones.map((milestone, mIndex) => ({
                        color: milestone.completed ? '#52c41a' : '#d9d9d9',
                        children: (
                          <div className="milestone-item">
                            <Text>{milestone.name}</Text>
                            {milestone.target_date && (
                              <div className="milestone-date">
                                <ClockCircleOutlined />
                                <Text type="secondary">{milestone.target_date}</Text>
                              </div>
                            )}
                          </div>
                        ),
                      }))}
                    />
                  </div>
                )}
              </div>
            ),
          }))}
        />
      </div>

      {data?.recommended_actions && data.recommended_actions.length > 0 && (
        <div className="recommended-actions">
          <Title level={5}>推荐行动</Title>
          <Row gutter={[8, 8]}>
            {data.recommended_actions.slice(0, 4).map((action, index) => (
              <Col xs={24} sm={12} key={index}>
                <Card size="small" className="action-card">
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    <Text>{action.action}</Text>
                    {action.priority === 'high' && (
                      <Tag color="red">优先</Tag>
                    )}
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      )}
    </Card>
  );
};

export default CareerTimeline;
