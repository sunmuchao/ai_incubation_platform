/**
 * AI Native Generative UI 组件库

AI Native 设计原则:
1. 界面由 AI 动态生成，而非固定布局
2. 根据任务类型/用户意图动态重组
3. 可视化组件由 AI 选择并生成
4. 支持所有 Agent Skills 的 UI 渲染
 */

import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Button,
  Rate,
  Avatar,
  List,
  Space,
  Statistic,
  Row,
  Col,
  Empty,
  Timeline,
  Progress,
  Alert,
  Divider,
  Descriptions,
  Collapse,
  Checkbox,
  Input,
  Result
} from 'antd'
import {
  HeartOutlined,
  HeartFilled,
  GiftOutlined,
  EnvironmentOutlined,
  ShopOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  FireOutlined,
  ThunderboltOutlined,
  MessageOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  SafetyOutlined,
  TrophyOutlined,
  LineChartOutlined,
  CloudOutlined,
  SyncOutlined,
  ExperimentOutlined,
  BookOutlined,
  CheckSquareOutlined,
  CameraOutlined,
  ShoppingOutlined,
  DashboardOutlined
} from '@ant-design/icons'
import './GenerativeUI.less'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse

// ========== 类型定义 ==========

export interface GenerativeUIConfig {
  component_type: string
  props: Record<string, any>
}

export interface GenerativeUIProps {
  uiConfig: GenerativeUIConfig
  onAction?: (action: { type: string; payload?: any }) => void
}

// ========== 匹配相关组件 ==========

/**
 * 匹配聚焦卡片 - 展示单个高匹配对象
 */
export const MatchSpotlight: React.FC<{ match: any; onAction?: (action: any) => void }> = ({
  match,
  onAction
}) => {
  return (
    <div className="match-spotlight-card">
      <div className="match-avatar-section">
        <Avatar size={120} src={match.avatar_url || '/default-avatar.png'} />
        <div className="match-score-badge">{Math.round(match.score * 100)}%</div>
      </div>
      <div className="match-info-section">
        <Title level={3}>{match.name}</Title>
        <Text type="secondary">{match.age}岁 · {match.location}</Text>
        <Paragraph className="match-reasoning">
          <HeartOutlined /> {match.reasoning}
        </Paragraph>
        <div className="common-interests">
          <Text strong>共同兴趣：</Text>
          <Space wrap>
            {match.common_interests?.map((interest: string, i: number) => (
              <Tag key={i} color="blue">{interest}</Tag>
            ))}
          </Space>
        </div>
      </div>
      <div className="match-actions">
        <Space>
          <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match })}>
            查看详细资料
          </Button>
          <Button onClick={() => onAction?.({ type: 'start_chat', match })}>
            开始聊天
          </Button>
        </Space>
      </div>
    </div>
  )
}

/**
 * 匹配卡片列表
 */
export const MatchCardList: React.FC<{ matches: any[]; onAction?: (action: any) => void }> = ({
  matches,
  onAction
}) => {
  return (
    <List
      grid={{ gutter: 16, column: 1 }}
      dataSource={matches}
      renderItem={(match) => (
        <List.Item>
          <Card className="match-list-item" hoverable>
            <Space>
              <Avatar src={match.avatar_url || '/default-avatar.png'} />
              <div className="match-list-info">
                <Text strong>{match.name}</Text>
                <br />
                <Text type="secondary">{match.age}岁 · {match.location}</Text>
              </div>
              <div className="match-list-score">
                <Tag color="red">{Math.round(match.score * 100)}%</Tag>
              </div>
              <Button type="link" onClick={() => onAction?.({ type: 'view_profile', match })}>
                查看
              </Button>
            </Space>
          </Card>
        </List.Item>
      )}
    />
  )
}

/**
 * 匹配轮播卡片
 */
export const MatchCarousel: React.FC<{ matches: any[]; onAction?: (action: any) => void }> = ({
  matches,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = matches[currentIndex]
  if (!current) return <Empty description="暂无匹配" />

  return (
    <div className="match-carousel">
      <Card className="match-carousel-card">
        <div className="match-carousel-content">
          <Avatar size={100} src={current.avatar_url || '/default-avatar.png'} />
          <div className="match-carousel-info">
            <Title level={4}>{current.name}</Title>
            <Text>{current.reasoning}</Text>
            <div className="match-interests">
              <Space wrap>
                {current.common_interests?.map((interest: string, i: number) => (
                  <Tag key={i} color="blue">{interest}</Tag>
                ))}
              </Space>
            </div>
          </div>
        </div>
        <div className="match-carousel-nav">
          <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
            上一个
          </Button>
          <Text>
            {currentIndex + 1} / {matches.length}
          </Text>
          <Button
            disabled={currentIndex === matches.length - 1}
            onClick={() => setCurrentIndex(i => i + 1)}
          >
            下一个
          </Button>
        </div>
        <div className="match-carousel-actions">
          <Space>
            <Button type="primary" onClick={() => onAction?.({ type: 'view_profile', match: current })}>
              查看详细资料
            </Button>
            <Button onClick={() => onAction?.({ type: 'start_chat', match: current })}>
              开始聊天
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}

// ========== 礼物相关组件 ==========

/**
 * 礼物网格
 */
export const GiftGrid: React.FC<{ gifts: any[]; columns?: number; onAction?: (action: any) => void }> = ({
  gifts,
  columns = 3,
  onAction
}) => {
  return (
    <Row gutter={[16, 16]}>
      {gifts.map((gift, index) => (
        <Col key={index} xs={24} sm={columns === 3 ? 8 : 12}>
          <Card className="gift-card" hoverable>
            <div className="gift-image">
              <GiftOutlined style={{ fontSize: 48, color: '#ff69b4' }} />
            </div>
            <div className="gift-info">
              <Title level={5}>{gift.name}</Title>
              <Text type="secondary" className="gift-price">
                ¥{gift.price}
              </Text>
              <Paragraph className="gift-reason" ellipsis={{ rows: 2 }}>
                {gift.match_reason}
              </Paragraph>
            </div>
            <div className="gift-actions">
              <Space>
                <Button size="small" onClick={() => onAction?.({ type: 'compare_gift', gift })}>
                  比价
                </Button>
                <Button type="primary" size="small" onClick={() => onAction?.({ type: 'buy_gift', gift })}>
                  购买
                </Button>
              </Space>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  )
}

/**
 * 礼物轮播
 */
export const GiftCarousel: React.FC<{ gifts: any[]; onAction?: (action: any) => void }> = ({
  gifts,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = gifts[currentIndex]
  if (!current) return <Empty description="暂无礼物" />

  return (
    <Card className="gift-carousel-card">
      <div className="gift-carousel-content">
        <div className="gift-carousel-image">
          <GiftOutlined style={{ fontSize: 80, color: '#ff69b4' }} />
        </div>
        <div className="gift-carousel-info">
          <Title level={4}>{current.name}</Title>
          <Text type="secondary" className="gift-carousel-price">
            ¥{current.price}
          </Text>
          <Paragraph>{current.match_reason}</Paragraph>
        </div>
      </div>
      <div className="gift-carousel-nav">
        <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
          上一个
        </Button>
        <Text>
          {currentIndex + 1} / {gifts.length}
        </Text>
        <Button
          disabled={currentIndex === gifts.length - 1}
          onClick={() => setCurrentIndex(i => i + 1)}
        >
          下一个
        </Button>
      </div>
      <div className="gift-carousel-actions">
        <Button type="primary" block onClick={() => onAction?.({ type: 'buy_gift', gift: current })}>
          立即购买
        </Button>
      </div>
    </Card>
  )
}

// ========== 消费画像组件 ==========

/**
 * 消费画像展示
 */
export const ConsumptionProfile: React.FC<{ profile: any }> = ({ profile }) => {
  return (
    <Card className="consumption-profile-card" title={<><LineChartOutlined /> 消费画像</>}>
      <div className="profile-header">
        <Tag color="gold" className="profile-level-tag">
          {profile.level}
        </Tag>
      </div>
      <Row gutter={[16, 16]} className="profile-stats">
        <Col span={12}>
          <Statistic
            label="消费频率"
            value={profile.frequency}
            suffix={profile.frequency === '高频' ? '🔥' : ''}
          />
        </Col>
        <Col span={12}>
          <Statistic label="平均客单" value={profile.average_transaction} />
        </Col>
        <Col span={12}>
          <Statistic label="消费模式" value={profile.spending_pattern} />
        </Col>
        <Col span={12}>
          <Statistic label="价格敏感度" value={profile.price_sensitivity} />
        </Col>
      </Row>
      <div className="profile-categories">
        <Text strong>偏好类别：</Text>
        <Space wrap className="category-tags">
          {profile.preferred_categories?.map((cat: string, i: number) => (
            <Tag key={i} color="blue">
              {cat}
            </Tag>
          ))}
        </Space>
      </div>
    </Card>
  )
}

// ========== 约会地点组件 ==========

/**
 * 约会地点列表
 */
export const DateSpotList: React.FC<{ spots: any[] }> = ({ spots }) => {
  return (
    <List
      dataSource={spots}
      renderItem={(spot) => (
        <List.Item>
          <Card className="date-spot-card" size="small">
            <div className="date-spot-header">
              <Space>
                <EnvironmentOutlined style={{ color: '#1890ff' }} />
                <Title level={5}>{spot.name}</Title>
              </Space>
              <Rate disabled defaultValue={spot.rating} allowHalf />
            </div>
            <div className="date-spot-content">
              <Text type="secondary">{spot.type}</Text>
              <br />
              <Text>{spot.address}</Text>
              <br />
              <Space split={<span>|</span>}>
                <Tag color="green">{spot.price_range}</Tag>
                <Text>距中点{spot.distance_from_midpoint}m</Text>
              </Space>
            </div>
            <Paragraph className="date-spot-reason" type="secondary">
              推荐理由：{spot.reason}
            </Paragraph>
          </Card>
        </List.Item>
      )}
    />
  )
}

/**
 * 约会计划轮播
 */
export const DatePlanCarousel: React.FC<{ plans: any[]; onAction?: (action: any) => void }> = ({
  plans,
  onAction
}) => {
  const [currentIndex, setCurrentIndex] = useState(0)

  const current = plans[currentIndex]
  if (!current) return <Empty description="暂无约会计划" />

  return (
    <Card className="date-plan-carousel">
      <div className="date-plan-content">
        <Title level={4}>{current.title}</Title>
        <Paragraph>{current.description}</Paragraph>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="时间">{current.duration}</Descriptions.Item>
          <Descriptions.Item label="预算">¥{current.budget}</Descriptions.Item>
          <Descriptions.Item label="适合">{current.suitable_for}</Descriptions.Item>
          <Descriptions.Item label="评分">
            <Rate disabled defaultValue={current.rating} />
          </Descriptions.Item>
        </Descriptions>
      </div>
      <div className="date-plan-nav">
        <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex(i => i - 1)}>
          上一个
        </Button>
        <Text>
          {currentIndex + 1} / {plans.length}
        </Text>
        <Button disabled={currentIndex === plans.length - 1} onClick={() => setCurrentIndex(i => i + 1)}>
          下一个
        </Button>
      </div>
      <div className="date-plan-actions">
        <Space>
          <Button type="primary" onClick={() => onAction?.({ type: 'book_date', plan: current })}>
            预订此约会
          </Button>
          <Button onClick={() => onAction?.({ type: 'save_plan', plan: current })}>收藏</Button>
        </Space>
      </div>
    </Card>
  )
}

// ========== 健康报告组件 ==========

export const HealthReport: React.FC<{ report: any }> = ({ report }) => {
  const healthScore = report.health_score || 0
  const isGood = healthScore >= 0.8

  return (
    <Card
      className="health-report-card"
      title={
        <Space>
          {isGood ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : (
            <WarningOutlined style={{ color: '#faad14' }} />
          )}
          关系健康报告
        </Space>
      }
    >
      <div className="health-score-display">
        <Statistic
          value={Math.round(healthScore * 100)}
          suffix="分"
          valueStyle={{ color: isGood ? '#52c41a' : '#faad14' }}
        />
        <Text type={isGood ? 'success' : 'warning'}>
          {isGood ? '关系非常健康！' : '需要关注'}
        </Text>
      </div>

      {report.issues?.length > 0 && (
        <div className="report-issues">
          <Text strong>需要注意的问题：</Text>
          <List
            size="small"
            dataSource={report.issues}
            renderItem={(issue: any) => (
              <List.Item>
                <Tag color="orange">{issue.type}</Tag>
                <Text type="secondary">{issue.description}</Text>
              </List.Item>
            )}
          />
        </div>
      )}

      {report.recommendations?.length > 0 && (
        <div className="report-recommendations">
          <Text strong>建议：</Text>
          <List
            size="small"
            dataSource={report.recommendations}
            renderItem={(rec: string) => <List.Item>• {rec}</List.Item>}
          />
        </div>
      )}
    </Card>
  )
}

// ========== 情感分析组件 ==========

/**
 * 情感雷达图
 */
export const EmotionRadar: React.FC<{ emotions: any[]; dominant_emotion?: string; intensity?: number }> = ({
  emotions,
  dominant_emotion,
  intensity
}) => {
  return (
    <Card className="emotion-radar-card" title={<><FireOutlined /> 情感分析</>}>
      <div className="emotion-summary">
        <div className="emotion-dominant">
          <Text strong>主导情绪：</Text>
          <Tag color="red">{dominant_emotion || '未知'}</Tag>
        </div>
        <div className="emotion-intensity">
          <Text strong>强度：</Text>
          <Progress
            percent={Math.round((intensity || 0) * 100)}
            strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
            format={(percent: number) => `${percent}%`}
          />
        </div>
      </div>
      <div className="emotion-chart">
        <Row gutter={[8, 8]}>
          {emotions.map((emotion, i) => (
            <Col span={12} key={i}>
              <div className="emotion-bar">
                <Text>{emotion.name}</Text>
                <Progress
                  percent={Math.round(emotion.value * 100)}
                  strokeColor="#ff6b6b"
                  format={null}
                  size="small"
                />
              </div>
            </Col>
          ))}
        </Row>
      </div>
    </Card>
  )
}

/**
 * 情感空状态
 */
export const EmotionEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="emotion-empty-card">
      <Empty
        image={<FireOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '暂无情感数据'}
      />
    </Card>
  )
}

// ========== 爱之语组件 ==========

/**
 * 爱之语卡片
 */
export const LoveLanguageCard: React.FC<{ profile: any }> = ({ profile }) => {
  return (
    <Card className="love-language-card" title={<><HeartOutlined /> 爱之语画像</>}>
      <div className="love-language-profile">
        <Title level={5}>主要爱之语</Title>
        <Tag color="pink" className="primary-love-language">
          {profile.primary_love_language}
        </Tag>
        <Paragraph type="secondary">{profile.description}</Paragraph>

        <Divider />

        <Title level={5}>五种爱之语得分</Title>
        <Timeline
          items={
            profile.scores?.map((score: any, i: number) => ({
              children: (
                <div className="love-language-score">
                  <Text>{score.name}</Text>
                  <Progress
                    percent={Math.round(score.score * 100)}
                    strokeColor="#ff69b4"
                    format={null}
                    size="small"
                  />
                </div>
              ),
              color: i === 0 ? 'pink' : 'gray'
            })) || []
          }
        />
      </div>
    </Card>
  )
}

/**
 * 爱之语翻译卡片
 */
export const LoveLanguageTranslationCard: React.FC<{
  original_expression?: string
  translated_expression?: string
  love_language_type?: string
  explanation?: string
}> = ({ original_expression, translated_expression, love_language_type, explanation }) => {
  return (
    <Card className="love-language-translation-card">
      <div className="translation-content">
        <div className="translation-original">
          <Text type="secondary">原始表达：</Text>
          <Paragraph>{original_expression}</Paragraph>
        </div>
        <div className="translation-arrow">
          <ThunderboltOutlined style={{ color: '#C88B8B', fontSize: 24 }} />
        </div>
        <div className="translation-translated">
          <Text strong>爱之语表达：</Text>
          <Paragraph className="translated-text">{translated_expression}</Paragraph>
          <Tag color="pink">{love_language_type}</Tag>
        </div>
        {explanation && (
          <div className="translation-explanation">
            <Text type="secondary">解读：</Text>
            <Paragraph type="secondary">{explanation}</Paragraph>
          </div>
        )}
      </div>
    </Card>
  )
}

// ========== 关系预测组件 ==========

/**
 * 关系预测空状态
 */
export const PredictionEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="prediction-empty-card">
      <Empty
        image={<CloudOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '暂无预测数据'}
      />
    </Card>
  )
}

/**
 * 关系天气报告
 */
export const RelationshipWeatherReport: React.FC<{ weather: string; forecast: any }> = ({
  weather,
  forecast
}) => {
  const weatherIcon = {
    sunny: <FireOutlined style={{ fontSize: 48, color: '#faad14' }} />,
    cloudy: <CloudOutlined style={{ fontSize: 48, color: '#8c8c8c' }} />,
    rainy: <ThunderboltOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    stormy: <WarningOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />
  }

  return (
    <Card className="relationship-weather-card">
      <div className="weather-display">
        <div className="weather-icon">{weatherIcon[weather as keyof typeof weatherIcon]}</div>
        <Title level={3}>关系天气：{weather}</Title>
        <Paragraph type="secondary">{forecast?.description}</Paragraph>
      </div>
      <div className="weather-forecast">
        <Title level={5}>未来趋势</Title>
        <List
          size="small"
          dataSource={forecast?.trend?.slice(0, 3)}
          renderItem={(item: any) => (
            <List.Item>
              <Text>{item.day}</Text>
              <Tag color={item.condition === 'good' ? 'green' : 'orange'}>{item.condition}</Tag>
            </List.Item>
          )}
        />
      </div>
    </Card>
  )
}

// ========== 沉默检测组件 ==========

/**
 * 沉默状态
 */
export const SilenceStatus: React.FC<{ duration?: number; level?: string }> = ({ duration, level }) => {
  const getColor = (lvl: string) => {
    switch (lvl) {
      case 'minor':
        return 'green'
      case 'moderate':
        return 'orange'
      case 'severe':
      case 'critical':
        return 'red'
      default:
        return 'gray'
    }
  }

  return (
    <Card className="silence-status-card">
      <div className="silence-indicator">
        <MessageOutlined
          style={{ fontSize: 32, color: getColor(level || 'minor') }}
          className="silence-icon"
        />
        <div className="silence-info">
          <Title level={4}>沉默检测</Title>
          <Text>已持续 {duration || 0} 秒</Text>
          <Tag color={getColor(level || 'minor')} className="silence-level">
            {level || 'normal'}
          </Tag>
        </div>
      </div>
      {level === 'critical' && (
        <Alert
          message="需要立即破冰！"
          description="沉默时间过长，建议立即发起新话题或互动"
          type="warning"
          showIcon
        />
      )}
    </Card>
  )
}

// ========== 话题建议组件 ==========

/**
 * 话题工具包
 */
export const TopicKit: React.FC<{ topics: any[]; onAction?: (action: any) => void }> = ({
  topics,
  onAction
}) => {
  return (
    <Card className="topic-kit-card" title={<><BookOutlined /> 话题工具包</>}>
      <Collapse
        items={(topics || []).map((topic, i) => ({
          key: i,
          label: (
            <Space>
              <Tag color="blue">{topic.category}</Tag>
              <Text>{topic.title}</Text>
            </Space>
          ),
          children: (
            <div className="topic-detail">
              <Paragraph>{topic.description}</Paragraph>
              <Space>
                <Button
                  size="small"
                  onClick={() => onAction?.({ type: 'use_topic', topic })}
                >
                  使用此话题
                </Button>
                <Button
                  size="small"
                  onClick={() => onAction?.({ type: 'save_topic', topic })}
                >
                  收藏
                </Button>
              </Space>
            </div>
          )
        }))}
      />
    </Card>
  )
}

/**
 * 话题建议
 */
export const TopicSuggestions: React.FC<{ suggestions: any[]; onAction?: (action: any) => void }> = ({
  suggestions,
  onAction
}) => {
  return (
    <Card className="topic-suggestions-card" title={<><MessageOutlined /> 话题建议</>}>
      <List
        dataSource={suggestions}
        renderItem={(suggestion) => (
          <List.Item
            actions={[
              <Button
                key="use"
                type="link"
                size="small"
                onClick={() => onAction?.({ type: 'use_topic', suggestion })}
              >
                使用
              </Button>
            ]}
          >
            <List.Item.Meta
              title={suggestion.title}
              description={suggestion.description}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

// ========== 关系策展组件 ==========

/**
 * 关系策展人
 */
export const RelationshipCurator: React.FC<{ relationship: any }> = ({ relationship }) => {
  return (
    <Card className="relationship-curator-card" title={<><HeartOutlined /> 关系策展</>}>
      <Descriptions column={1} bordered>
        <Descriptions.Item label="关系阶段">{relationship.stage}</Descriptions.Item>
        <Descriptions.Item label="在一起天数">{relationship.days_together}</Descriptions.Item>
        <Descriptions.Item label="互动频率">{relationship.interaction_frequency}</Descriptions.Item>
        <Descriptions.Item label="匹配度">
          <Progress
            percent={Math.round((relationship.compatibility_score || 0) * 100)}
            strokeColor="#ff6b6b"
            format={null}
          />
        </Descriptions.Item>
      </Descriptions>

      <Divider />

      <Title level={5}>关系亮点</Title>
      <List
        size="small"
        dataSource={relationship.highlights}
        renderItem={(highlight: string) => (
          <List.Item>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            {highlight}
          </List.Item>
        )}
      />
    </Card>
  )
}

// ========== 里程碑时间轴组件 ==========

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

// ========== 约会助手组件 ==========

/**
 * 约会助手卡片
 */
export const DateAssistantCard: React.FC<{ suggestion: any; onAction?: (action: any) => void }> = ({
  suggestion,
  onAction
}) => {
  return (
    <Card className="date-assistant-card">
      <div className="date-suggestion">
        <Title level={5}>{suggestion.title}</Title>
        <Paragraph>{suggestion.description}</Paragraph>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="最佳时间">{suggestion.best_time}</Descriptions.Item>
          <Descriptions.Item label="预计时长">{suggestion.duration}</Descriptions.Item>
        </Descriptions>
        <Space className="date-actions">
          <Button type="primary" onClick={() => onAction?.({ type: 'accept_suggestion', suggestion })}>
            接受建议
          </Button>
          <Button onClick={() => onAction?.({ type: 'dismiss_suggestion', suggestion })}>跳过</Button>
        </Space>
      </div>
    </Card>
  )
}

/**
 * 约会回顾
 */
export const DateReview: React.FC<{ review: any }> = ({ review }) => {
  return (
    <Card className="date-review-card" title={<><CalendarOutlined /> 约会回顾</>}>
      <div className="date-review-summary">
        <Title level={5}>{review.date_title}</Title>
        <Text type="secondary">{review.date}</Text>
        <Rate disabled defaultValue={review.rating} allowHalf className="date-review-rating" />
      </div>

      <Divider />

      <div className="date-review-details">
        <Title level={6}>亮点时刻</Title>
        <Paragraph>{review.highlight}</Paragraph>

        <Title level={6}>改进建议</Title>
        <Paragraph type="secondary">{review.suggestion}</Paragraph>
      </div>
    </Card>
  )
}

// ========== 视频约会教练组件 ==========

/**
 * 视频约会教练仪表板
 */
export const VideoDateCoachDashboard: React.FC<{
  coaching?: any
  outfit?: any
  icebreakers?: any[]
  onAction?: (action: any) => void
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
export const DateSimulationFeedback: React.FC<{ feedback: any }> = ({ feedback }) => {
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
          dataSource={feedback.strengths}
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
          dataSource={feedback.improvements}
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

// ========== 绩效教练组件 ==========

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

// ========== 活动准备组件 ==========

/**
 * 准备清单
 */
export const PrepChecklist: React.FC<{
  items: any[]
  onAction?: (action: any) => void
}> = ({ items, onAction }) => {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({})

  return (
    <Card className="prep-checklist-card" title={<><CheckSquareOutlined /> 准备清单</>}>
      <List
        dataSource={items}
        renderItem={(item, index) => (
          <List.Item>
            <Checkbox
              checked={checkedItems[index]}
              onChange={(e) =>
                setCheckedItems({ ...checkedItems, [index]: e.target.checked })
              }
            >
              <div className="checklist-item">
                <Text>{item.task}</Text>
                {item.priority === 'high' && <Tag color="red">重要</Tag>}
              </div>
            </Checkbox>
          </List.Item>
        )}
      />
      <Button
        type="primary"
        block
        onClick={() => onAction?.({ type: 'complete_prep', items: checkedItems })}
      >
        准备完成
      </Button>
    </Card>
  )
}

/**
 * 着装建议
 */
export const OutfitRecommendations: React.FC<{ outfits: any[] }> = ({ outfits }) => {
  return (
    <Card className="outfit-recommendations" title={<><ShoppingOutlined /> 着装建议</>}>
      <Row gutter={[16, 16]}>
        {outfits.map((outfit, i) => (
          <Col span={24} key={i}>
            <Card size="small">
              <div className="outfit-item">
                <Title level={5}>{outfit.name}</Title>
                <Paragraph type="secondary">{outfit.description}</Paragraph>
                <Tag color={outfit.occasion === 'formal' ? 'purple' : 'blue'}>
                  {outfit.occasion}
                </Tag>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  )
}

// ========== 安全组件 ==========

/**
 * 安全警报
 */
export const SafetyAlert: React.FC<{ level: string; message: string }> = ({
  level,
  message
}) => {
  const alertType = level === 'high' ? 'error' : level === 'medium' ? 'warning' : 'info'

  return (
    <Alert
      className="safety-alert"
      message={
        <Space>
          <SafetyOutlined />
          安全提醒
        </Space>
      }
      description={message}
      type={alertType}
      showIcon
    />
  )
}

/**
 * 安全状态
 */
export const SafetyStatus: React.FC<{ status: string; details?: any }> = ({ status, details }) => {
  return (
    <Card className="safety-status-card" title={<><SafetyOutlined /> 安全状态</>}>
      <div className="safety-indicator">
        <div className={`status-dot ${status}`}></div>
        <Text strong>当前状态：{status}</Text>
      </div>

      {details && (
        <Descriptions column={1} size="small">
          {Object.entries(details).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {value}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </Card>
  )
}

/**
 * 安全紧急情况
 */
export const SafetyEmergency: React.FC<{ message: string; onAction?: (action: any) => void }> = ({
  message,
  onAction
}) => {
  return (
    <Alert
      className="safety-emergency"
      message={
        <Space>
          <WarningOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
          <Title level={4} style={{ margin: 0 }}>紧急安全提醒</Title>
        </Space>
      }
      description={message}
      type="error"
      showIcon
      action={
        <Space>
          <Button danger onClick={() => onAction?.({ type: 'get_help' })}>
            获取帮助
          </Button>
          <Button onClick={() => onAction?.({ type: 'dismiss' })}>我知道了</Button>
        </Space>
      }
    />
  )
}

// ========== 风控组件 ==========

/**
 * 风控仪表板
 */
export const RiskControlDashboard: React.FC<{ metrics: any; risks: any[] }> = ({
  metrics,
  risks
}) => {
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
export const RiskAssessmentDashboard: React.FC<{ assessment: any }> = ({ assessment }) => {
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
          dataSource={assessment.risk_factors}
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

// ========== 分享增长组件 ==========

/**
 * 分享增长仪表板
 */
export const ShareGrowthDashboard: React.FC<{ metrics: any; invites?: any[] }> = ({
  metrics,
  invites
}) => {
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

// ========== 活动导演组件 ==========

/**
 * 活动导演仪表板
 */
export const ActivityDirectorDashboard: React.FC<{
  activities?: any[]
  recommendations?: any[]
  onAction?: (action: any) => void
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

// ========== 约会模拟组件 ==========

/**
 * 场地推荐
 */
export const VenueRecommendations: React.FC<{ venues: any[] }> = ({ venues }) => {
  return (
    <Card className="venue-recommendations" title={<><EnvironmentOutlined /> 场地推荐</>}>
      <List
        dataSource={venues}
        renderItem={(venue) => (
          <List.Item>
            <List.Item.Meta
              title={venue.name}
              description={`${venue.type} · ${venue.price_range} · ${venue.distance}`}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

// ========== 关系趋势组件 ==========

/**
 * 关系趋势图表
 */
export const RelationshipTrendChart: React.FC<{ data: any[] }> = ({ data }) => {
  return (
    <Card className="relationship-trend-chart" title={<><LineChartOutlined /> 关系趋势</>}>
      <div className="trend-placeholder">
        <LineChartOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        <Text>关系趋势图表区域</Text>
        <Paragraph type="secondary">需集成图表库 (如 Recharts/AntV)</Paragraph>
      </div>
    </Card>
  )
}

/**
 * 关系天气
 */
export const RelationshipWeather: React.FC<{ weather: string; score: number }> = ({
  weather,
  score
}) => {
  const weatherIcon = {
    sunny: <FireOutlined style={{ fontSize: 32, color: '#faad14' }} />,
    cloudy: <CloudOutlined style={{ fontSize: 32, color: '#8c8c8c' }} />,
    rainy: <ThunderboltOutlined style={{ fontSize: 32, color: '#1890ff' }} />,
    stormy: <WarningOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />
  }

  return (
    <Card className="relationship-weather-card">
      <div className="weather-display">
        <div className="weather-icon">
          {weatherIcon[weather as keyof typeof weatherIcon]}
        </div>
        <Title level={4}>{weather}</Title>
        <Progress
          type="circle"
          percent={Math.round(score * 100)}
          size={80}
          format={(percent: number) => `${percent}分`}
        />
      </div>
    </Card>
  )
}

// ========== 冲突计量器组件 ==========

/**
 * 冲突计量器
 */
export const ConflictMeter: React.FC<{ level: number }> = ({ level }) => {
  const getColor = (lvl: number) => {
    if (lvl < 0.3) return '#52c41a'
    if (lvl < 0.6) return '#faad14'
    return '#ff4d4f'
  }

  return (
    <Card className="conflict-meter-card">
      <div className="meter-display">
        <Title level={5}>冲突程度</Title>
        <Progress
          type="dashboard"
          percent={Math.round(level * 100)}
          strokeColor={getColor(level)}
        />
        <Text type={level < 0.3 ? 'success' : level < 0.6 ? 'warning' : 'danger'}>
          {level < 0.3 ? '和谐' : level < 0.6 ? '中等' : '紧张'}
        </Text>
      </div>
    </Card>
  )
}

// ========== 调解组件 ==========

/**
 * 调解空状态
 */
export const MediationEmpty: React.FC<{ message?: string }> = ({ message }) => {
  return (
    <Card className="mediation-empty-card">
      <Empty
        image={<MessageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        description={message || '无需调解'}
      />
    </Card>
  )
}

// ========== 对话匹配组件 ==========

/**
 * 对话匹配仪表板
 */
export const ConversationMatchmakerDashboard: React.FC<{
  matches?: any[]
  intents?: any[]
  onAction?: (action: any) => void
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

// ========== 关系进展追踪组件 (新增 Skill) ==========

/**
 * 关系进展里程碑卡片
 * AI Native: 自动识别并庆祝重要时刻
 */
export const MilestoneCard: React.FC<{
  type: string
  status?: string
  icon?: string
  onAction?: (action: any) => void
}> = ({ type, status, icon = 'celebration', onAction }) => {
  return (
    <Card className="milestone-card" title={<><TrophyOutlined /> 关系里程碑</>}>
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a', fontSize: 48 }} />}
        title={`已记录：${type}`}
        subTitle={status === 'recorded' ? '继续用心经营你们的关系吧~' : ''}
        extra={
          <Space>
            <Button onClick={() => onAction?.({ type: 'view_timeline' })}>查看时间线</Button>
            <Button type="primary" onClick={() => onAction?.({ type: 'view_health' })}>
              查看健康度
            </Button>
          </Space>
        }
      />
    </Card>
  )
}

/**
 * 关系时间线
 * AI Native: 动态生成关系发展历程
 */
export const RelationshipTimeline: React.FC<{
  current_stage?: string
  milestones?: any[]
  show_progress_indicator?: boolean
  onAction?: (action: any) => void
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
 * AI Native: 多维度分析 + 智能建议生成
 */
export const HealthScoreCard: React.FC<{
  score: number
  max_score?: number
  level?: string
  color?: string
  dimensions?: Record<string, number>
  suggestions?: string[]
  onAction?: (action: any) => void
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
 * AI Native: 动态选择最适合的图表类型
 */
export const RelationshipChart: React.FC<{
  chart_type?: string
  labels?: string[]
  activity_data?: number[]
  stage_changes?: any[]
  onAction?: (action: any) => void
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

      {stage_changes && stage_changes.length > 0 && (
        <>
          <Divider />
          <div className="stage-changes">
            <Title level={6}>阶段变化</Title>
            <Timeline
              items={stage_changes.map((change, i) => ({
                children: (
                  <div>
                    <Text strong>{change.stage}</Text>
                    <Text type="secondary"> - {change.date}</Text>
                  </div>
                ),
                color: 'blue'
              }))}
            />
          </div>
        </>
      )}

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
 * AI Native: 整合多维度数据的全局视图
 */
export const RelationshipDashboard: React.FC<{
  summary?: string
  timeline?: any
  health_score?: any
  onAction?: (action: any) => void
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

// ========== 聊天助手组件 (新增 Skill) ==========

/**
 * 消息发送状态
 * AI Native: 自动优化消息内容
 */
export const MessageSent: React.FC<{
  message_id?: string
  status?: string
  onAction?: (action: any) => void
}> = ({ message_id, status = 'sent', onAction }) => {
  return (
    <Card className="message-sent-card">
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title="消息已发送"
        subTitle={status === 'sent' ? '对方将尽快收到您的消息' : status}
        extra={
          <Button type="primary" onClick={() => onAction?.({ type: 'view_conversation' })}>
            查看会话
          </Button>
        }
      />
    </Card>
  )
}

/**
 * 会话列表
 * AI Native: 智能排序，重要对话置顶
 */
export const ConversationList: React.FC<{
  conversations?: any[]
  show_unread?: boolean
  onAction?: (action: any) => void
}> = ({ conversations, show_unread, onAction }) => {
  if (!conversations || conversations.length === 0) {
    return <Empty description="暂无会话" />
  }

  return (
    <Card className="conversation-list-card" title={<><MessageOutlined /> 会话列表</>}>
      <List
        dataSource={conversations}
        renderItem={(conversation) => (
          <List.Item
            className="conversation-item"
            actions={[
              <Button
                key="chat"
                type="link"
                onClick={() => onAction?.({ type: 'open_chat', conversation })}
              >
                进入聊天
              </Button>
            ]}
          >
            <List.Item.Meta
              avatar={
                <Avatar
                  src={conversation.avatar}
                  style={{
                    backgroundColor: conversation.unread_count > 0 ? '#1890ff' : '#d9d9d9'
                  }}
                />
              }
              title={
                <Space>
                  <Text strong>{conversation.partner_name || '未知用户'}</Text>
                  {show_unread && conversation.unread_count > 0 && (
                    <Tag color="red">{conversation.unread_count} 条未读</Tag>
                  )}
                </Space>
              }
              description={
                <div className="conversation-preview">
                  <Text type="secondary" ellipsis>{conversation.last_message_preview}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {conversation.last_message_at}
                  </Text>
                </div>
              }
            />
          </List.Item>
        )}
      />

      <Divider />

      <Button type="primary" block onClick={() => onAction?.({ type: 'start_new_chat' })}>
        开始新对话
      </Button>
    </Card>
  )
}

/**
 * 聊天历史
 * AI Native: 智能摘要长对话
 */
export const ChatHistory: React.FC<{
  messages?: any[]
  show_sender?: boolean
  onAction?: (action: any) => void
}> = ({ messages, show_sender, onAction }) => {
  if (!messages || messages.length === 0) {
    return <Empty description="暂无聊天历史" />
  }

  return (
    <Card className="chat-history-card" title={<><ClockCircleOutlined /> 聊天历史</>}>
      <div className="messages-container">
        {messages.map((message: any, index: number) => (
          <div
            key={message.id || index}
            className={`message-item ${message.sender_id === 'me' ? 'message-me' : 'message-other'}`}
          >
            {show_sender && (
              <Avatar
                size="small"
                src={message.avatar}
                className="message-avatar"
              />
            )}
            <div className="message-content">
              <div className="message-bubble">{message.content}</div>
              <div className="message-meta">
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {message.created_at}
                </Text>
                {message.is_read && (
                  <CheckCircleOutlined style={{ fontSize: 12, color: '#1890ff' }} />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <Divider />

      <Button type="primary" block onClick={() => onAction?.({ type: 'send_message' })}>
        发送消息
      </Button>
    </Card>
  )
}

/**
 * 聊天建议卡片
 * AI Native: 基于兴趣和地理位置生成个性化建议
 */
export const SuggestionCards: React.FC<{
  suggestions?: any[]
  show_reason?: boolean
  onAction?: (action: any) => void
}> = ({ suggestions, show_reason, onAction }) => {
  if (!suggestions || suggestions.length === 0) {
    return <Empty description="暂无聊天建议" />
  }

  return (
    <Card className="suggestion-cards-card" title={<><HeartFilled style={{ color: '#FF8FAB' }} /> 聊天建议</>}>
      <List
        dataSource={suggestions}
        renderItem={(suggestion: any, index: number) => (
          <List.Item>
            <Card
              size="small"
              className="suggestion-card"
              hoverable
              onClick={() => onAction?.({ type: 'use_suggestion', suggestion })}
            >
              <div className="suggestion-content">
                <Tag color={suggestion.type === 'icebreaker' ? 'blue' : 'green'}>
                  {suggestion.type === 'icebreaker' ? '破冰' : '话题'}
                </Tag>
                <Paragraph style={{ margin: '8px 0' }}>{suggestion.content}</Paragraph>
                {show_reason && suggestion.reason && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    💡 {suggestion.reason}
                  </Text>
                )}
              </div>
            </Card>
          </List.Item>
        )}
      />

      <Divider />

      <Space>
        <Button onClick={() => onAction?.({ type: 'refresh_suggestions' })}>刷新建议</Button>
        <Button type="primary" onClick={() => onAction?.({ type: 'use_suggestion' })}>
          使用建议
        </Button>
      </Space>
    </Card>
  )
}

/**
 * 未读消息徽章
 * AI Native: 智能分级，重要消息优先提醒
 */
export const UnreadBadge: React.FC<{
  count?: number
  onAction?: (action: any) => void
}> = ({ count = 0, onAction }) => {
  if (count === 0) {
    return (
      <Card className="unread-badge-card">
        <Result
          icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
          title="没有未读消息"
          subTitle="所有消息都已处理"
        />
      </Card>
    )
  }

  return (
    <Card className="unread-badge-card">
      <div className="unread-display">
        <Badge count={count} offset={[-10, -10]} style={{ backgroundColor: '#ff4d4f' }}>
          <MessageOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        </Badge>
      </div>
      <Title level={4} style={{ textAlign: 'center', marginTop: 16 }}>
        你有 {count} 条未读消息
      </Title>
      <Paragraph type="secondary" style={{ textAlign: 'center' }}>
        及时回复可以增进关系哦~
      </Paragraph>
      <Button type="primary" block onClick={() => onAction?.({ type: 'view_messages' })}>
        查看消息
      </Button>
    </Card>
  )
}

// ========== 安全守护 - 紧急求助组件 (新增 Skill) ==========

/**
 * 紧急求助面板
 * AI Native: 自主触发、分级响应、自动通知联系人
 */
export const EmergencyPanel: React.FC<{
  emergency_type?: string
  status?: string
  contacts_notified?: any[]
  location_shared?: boolean
  onAction?: (action: any) => void
}> = ({ emergency_type, status, contacts_notified, location_shared, onAction }) => {
  const getTypeColor = (type?: string) => {
    const colorMap: Record<string, string> = {
      general: 'blue',
      medical: 'red',
      danger: 'red',
      harassment: 'orange'
    }
    return colorMap[type || 'general'] || 'blue'
  }

  const getTypeLabel = (type?: string) => {
    const labelMap: Record<string, string> = {
      general: '一般求助',
      medical: '医疗急救',
      danger: '人身危险',
      harassment: '骚扰威胁'
    }
    return labelMap[type || 'general'] || '一般求助'
  }

  return (
    <Card className="emergency-panel-card">
      <Alert
        message={
          <Space>
            <WarningOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
            <Title level={4} style={{ margin: 0 }}>紧急求助</Title>
          </Space>
        }
        description={
          <div className="emergency-details">
            <div className="emergency-type">
              <Tag color={getTypeColor(emergency_type)}>{getTypeLabel(emergency_type)}</Tag>
            </div>
            <div className="emergency-status">
              <Text strong>状态：</Text>
              <Text type={status === 'active' ? 'danger' : 'success'}>
                {status === 'active' ? '处理中' : '已处理'}
              </Text>
            </div>
            {contacts_notified && contacts_notified.length > 0 && (
              <div className="contacts-notified">
                <Text strong>已通知联系人：</Text>
                <List
                  size="small"
                  dataSource={contacts_notified}
                  renderItem={(contact: any) => (
                    <List.Item>
                      <Text>{contact.name}</Text>
                      <Tag color={contact.notified ? 'green' : 'gray'}>
                        {contact.notified ? '已通知' : '未通知'}
                      </Tag>
                    </List.Item>
                  )}
                />
              </div>
            )}
            {location_shared && (
              <div className="location-shared">
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text>位置已共享</Text>
              </div>
            )}
          </div>
        }
        type="error"
        showIcon
      />

      <Divider />

      <Space style={{ width: '100%', justifyContent: 'center' }}>
        <Button danger onClick={() => onAction?.({ type: 'cancel_emergency' })}>
          取消求助
        </Button>
        <Button onClick={() => onAction?.({ type: 'update_status' })}>更新状态</Button>
        <Button type="primary" onClick={() => onAction?.({ type: 'contact_help' })}>
          联系帮助
        </Button>
      </Space>
    </Card>
  )
}

// ========== 空状态 ==========

export const EmptyState: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div className="empty-state">
      <Empty description={message} />
    </div>
  )
}

// ========== 主渲染器 ==========

/**
 * Generative UI 渲染器

根据 AI 生成的 UI 配置动态渲染组件
 */
export const GenerativeUIRenderer: React.FC<GenerativeUIProps> = ({ uiConfig, onAction }) => {
  const { component_type, props } = uiConfig

  const renderComponent = () => {
    // 匹配相关
    switch (component_type) {
      case 'match_spotlight':
        return <MatchSpotlight match={props?.match} onAction={onAction} />

      case 'match_card_list':
        return <MatchCardList matches={props?.matches || []} onAction={onAction} />

      case 'match_carousel':
        return <MatchCarousel matches={props?.matches || []} onAction={onAction} />

      // 礼物相关
      case 'gift_grid':
        return <GiftGrid gifts={props?.gifts || []} columns={props?.columns} onAction={onAction} />

      case 'gift_carousel':
        return <GiftCarousel gifts={props?.gifts || []} onAction={onAction} />

      // 消费画像
      case 'consumption_profile':
        return <ConsumptionProfile profile={props?.profile || {}} />

      // 约会相关
      case 'date_spot_map':
      case 'date_plan_carousel':
        return <DatePlanCarousel plans={props?.plans || props?.spots || []} onAction={onAction} />

      // 健康报告
      case 'health_report':
        return <HealthReport report={props?.report || {}} />

      // 情感分析
      case 'emotion_radar':
        return (
          <EmotionRadar
            emotions={props?.emotions || []}
            dominant_emotion={props?.dominant_emotion}
            intensity={props?.intensity}
          />
        )

      case 'emotion_empty':
        return <EmotionEmpty message={props?.message} />

      // 爱之语
      case 'love_language_card':
        return <LoveLanguageCard profile={props?.profile || {}} />

      case 'love_language_translation_card':
        return (
          <LoveLanguageTranslationCard
            original_expression={props?.original_expression}
            translated_expression={props?.translated_expression}
            love_language_type={props?.love_language_type}
            explanation={props?.explanation}
          />
        )

      // 关系预测
      case 'prediction_empty':
        return <PredictionEmpty message={props?.message} />

      case 'relationship_weather_report':
      case 'relationship_weather':
        return (
          <RelationshipWeatherReport
            weather={props?.weather}
            forecast={props?.forecast || {}}
          />
        )

      // 沉默检测
      case 'silence_status':
        return (
          <SilenceStatus duration={props?.duration} level={props?.level} />
        )

      // 话题建议
      case 'topic_kit':
        return <TopicKit topics={props?.topics || []} onAction={onAction} />

      case 'topic_suggestions':
        return <TopicSuggestions suggestions={props?.suggestions || []} onAction={onAction} />

      // 关系策展
      case 'relationship_curator':
        return <RelationshipCurator relationship={props?.relationship || {}} />

      case 'milestone_timeline':
        return <MilestoneTimeline milestones={props?.milestones || []} />

      // 约会助手
      case 'date_assistant_card':
        return <DateAssistantCard suggestion={props?.suggestion || {}} onAction={onAction} />

      case 'date_review':
        return <DateReview review={props?.review || {}} />

      // 视频约会教练
      case 'video_date_coach_dashboard':
        return (
          <VideoDateCoachDashboard
            coaching={props?.coaching}
            outfit={props?.outfit}
            icebreakers={props?.icebreakers}
            onAction={onAction}
          />
        )

      case 'date_simulation_feedback':
        return <DateSimulationFeedback feedback={props?.feedback || {}} />

      // 绩效教练
      case 'performance_coach_dashboard':
        return (
          <PerformanceCoachDashboard
            metrics={props?.metrics}
            milestones={props?.milestones}
            suggestions={props?.suggestions}
          />
        )

      case 'coach_empty':
        return <CoachEmpty message={props?.message} />

      // 活动准备
      case 'prep_checklist':
        return <PrepChecklist items={props?.items || []} onAction={onAction} />

      case 'outfit_recommendations':
        return <OutfitRecommendations outfits={props?.outfits || []} />

      // 安全组件
      case 'safety_alert':
        return <SafetyAlert level={props?.level} message={props?.message} />

      case 'safety_status':
        return <SafetyStatus status={props?.status} details={props?.details} />

      case 'safety_emergency':
        return <SafetyEmergency message={props?.message} onAction={onAction} />

      // 风控组件
      case 'risk_control_dashboard':
        return <RiskControlDashboard metrics={props?.metrics || {}} risks={props?.risks || []} />

      case 'risk_assessment_dashboard':
        return <RiskAssessmentDashboard assessment={props?.assessment || {}} />

      // 分享增长
      case 'share_growth_dashboard':
        return (
          <ShareGrowthDashboard
            metrics={props?.metrics || {}}
            invites={props?.invites}
          />
        )

      // 活动导演
      case 'activity_director_dashboard':
        return (
          <ActivityDirectorDashboard
            activities={props?.activities}
            recommendations={props?.recommendations}
            onAction={onAction}
          />
        )

      // 场地推荐
      case 'venue_recommendations':
        return <VenueRecommendations venues={props?.venues || []} />

      // 关系趋势
      case 'relationship_trend_chart':
        return <RelationshipTrendChart data={props?.data || []} />

      // 冲突计量器
      case 'conflict_meter':
        return <ConflictMeter level={props?.level || 0} />

      // 调解
      case 'mediation_empty':
        return <MediationEmpty message={props?.message} />

      // 对话匹配
      case 'conversation_matchmaker_dashboard':
        return (
          <ConversationMatchmakerDashboard
            matches={props?.matches}
            intents={props?.intents}
            onAction={onAction}
          />
        )

      // 新增 Skill - 关系进展追踪
      case 'milestone_card':
        return <MilestoneCard type={props?.type} status={props?.status} onAction={onAction} />

      case 'relationship_timeline':
        return (
          <RelationshipTimeline
            current_stage={props?.current_stage}
            milestones={props?.milestones}
            show_progress_indicator={props?.show_progress_indicator}
            onAction={onAction}
          />
        )

      case 'health_score_card':
        return (
          <HealthScoreCard
            score={props?.score}
            max_score={props?.max_score}
            level={props?.level}
            color={props?.color}
            dimensions={props?.dimensions}
            suggestions={props?.suggestions}
            onAction={onAction}
          />
        )

      case 'relationship_chart':
        return (
          <RelationshipChart
            chart_type={props?.chart_type}
            labels={props?.labels}
            activity_data={props?.activity_data}
            stage_changes={props?.stage_changes}
            onAction={onAction}
          />
        )

      case 'relationship_dashboard':
        return (
          <RelationshipDashboard
            summary={props?.summary}
            timeline={props?.timeline}
            health_score={props?.health_score}
            onAction={onAction}
          />
        )

      // 新增 Skill - 聊天助手
      case 'message_sent':
        return <MessageSent message_id={props?.message_id} status={props?.status} onAction={onAction} />

      case 'conversation_list':
        return (
          <ConversationList
            conversations={props?.conversations}
            show_unread={props?.show_unread}
            onAction={onAction}
          />
        )

      case 'chat_history':
        return (
          <ChatHistory
            messages={props?.messages}
            show_sender={props?.show_sender}
            onAction={onAction}
          />
        )

      case 'suggestion_cards':
        return (
          <SuggestionCards
            suggestions={props?.suggestions}
            show_reason={props?.show_reason}
            onAction={onAction}
          />
        )

      case 'unread_badge':
        return <UnreadBadge count={props?.count} onAction={onAction} />

      // 新增 Skill - 安全守护
      case 'emergency_panel':
        return (
          <EmergencyPanel
            emergency_type={props?.emergency_type}
            status={props?.status}
            contacts_notified={props?.contacts_notified}
            location_shared={props?.location_shared}
            onAction={onAction}
          />
        )

      // 空状态
      case 'empty_state':
        return <EmptyState message={props?.message || '暂无内容'} />

      default:
        return <EmptyState message={`未知组件类型：${component_type}`} />
    }
  }

  return <div className="generative-ui-container">{renderComponent()}</div>
}

export default GenerativeUIRenderer