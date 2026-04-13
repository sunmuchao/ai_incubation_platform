/**
 * GenerativeUI 组件测试
 * 测试 AI Native Generative UI 动态容器组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { GenerativeUIRenderer } from '../../components/GenerativeUI'

// Mock Ant Design 组件
jest.mock('antd', () => {
  const actualAntd = jest.requireActual('antd')
  return {
    ...actualAntd,
    Card: ({ children, className, style }: any) => (
      <div
        className={className}
        data-testid="card"
        style={style}
      >
        {children}
      </div>
    ),
    Spin: ({ children, tip }: any) => (
      <div data-testid="spin" data-tip={tip}>
        {children || 'loading'}
      </div>
    ),
    Empty: ({ description }: any) => (
      <div data-testid="empty">{description || '暂无内容'}</div>
    ),
    Typography: {
      Text: ({ children, strong, className }: any) => (
        <span data-testid="text" data-strong={strong} className={className}>
          {children}
        </span>
      ),
    },
  }
})

// Mock generative-ui 子组件
jest.mock('../../components/generative-ui', () => ({
  // 类型
  GenerativeUIConfig: {},
  GenerativeUIProps: {},
  GenerativeAction: {},

  // 匹配组件
  MatchSpotlight: ({ match, onAction }: any) => (
    <div data-testid="match-spotlight">
      <span>{match?.name || '匹配对象'}</span>
      <button onClick={() => onAction?.('view')}>查看详情</button>
      <button onClick={() => onAction?.('skip')}>跳过</button>
    </div>
  ),
  MatchCardList: ({ matches, onAction }: any) => (
    <div data-testid="match-card-list">
      {matches?.map((m: any, i: number) => <span key={i}>{m.name}</span>)}
    </div>
  ),
  MatchCarousel: ({ matches, onAction }: any) => (
    <div data-testid="match-carousel">
      {matches?.map((m: any, i: number) => <span key={i}>{m.name}</span>)}
    </div>
  ),

  // 礼物组件
  GiftGrid: ({ gifts, onAction }: any) => (
    <div data-testid="gift-grid">
      {gifts?.map((g: any, i: number) => <span key={i}>{g.name}</span>)}
    </div>
  ),
  GiftCarousel: ({ gifts, onAction }: any) => (
    <div data-testid="gift-carousel">
      {gifts?.map((g: any, i: number) => <span key={i}>{g.name}</span>)}
    </div>
  ),

  // 约会组件
  DateSpotList: ({ spots }: any) => (
    <div data-testid="date-spot-list">
      {spots?.map((s: any, i: number) => <span key={i}>{s.name}</span>)}
    </div>
  ),
  DatePlanCarousel: ({ plans, onAction }: any) => (
    <div data-testid="date-plan-carousel">
      {plans?.map((p: any, i: number) => <span key={i}>{p.title}</span>)}
    </div>
  ),

  // 安全组件
  SafetyAlert: ({ level, message }: any) => (
    <div data-testid="safety-alert" data-level={level}>{message}</div>
  ),
  SafetyStatus: ({ status, details }: any) => (
    <div data-testid="safety-status" data-status={status}>{details}</div>
  ),
  SafetyEmergency: ({ message, onAction }: any) => (
    <div data-testid="safety-emergency">{message}</div>
  ),
  EmergencyPanel: ({ emergency_type, status }: any) => (
    <div data-testid="emergency-panel" data-type={emergency_type}>{status}</div>
  ),

  // 共享组件
  EmptyState: ({ message }: any) => (
    <div data-testid="empty-state">{message}</div>
  ),
  ConsumptionProfile: ({ profile }: any) => (
    <div data-testid="consumption-profile">{profile?.category || '消费画像'}</div>
  ),
  HealthReport: ({ report }: any) => (
    <div data-testid="health-report">{report?.summary || '健康报告'}</div>
  ),

  // 情感分析组件
  EmotionRadar: ({ emotions, dominant_emotion }: any) => (
    <div data-testid="emotion-radar">{dominant_emotion || '情感分析'}</div>
  ),
  EmotionEmpty: ({ message }: any) => (
    <div data-testid="emotion-empty">{message}</div>
  ),
  LoveLanguageCard: ({ profile }: any) => (
    <div data-testid="love-language-card">{profile?.type || '爱之语'}</div>
  ),
  LoveLanguageTranslationCard: ({ original_expression }: any) => (
    <div data-testid="love-language-translation">{original_expression}</div>
  ),
  PredictionEmpty: ({ message }: any) => (
    <div data-testid="prediction-empty">{message}</div>
  ),
  RelationshipWeatherReport: ({ weather }: any) => (
    <div data-testid="relationship-weather">{weather?.status || '关系天气'}</div>
  ),
  SilenceStatus: ({ duration, level }: any) => (
    <div data-testid="silence-status" data-level={level}>{duration}</div>
  ),

  // 关系进展组件
  MilestoneTimeline: ({ milestones }: any) => (
    <div data-testid="milestone-timeline">
      {milestones?.map((m: any, i: number) => <span key={i}>{m.title}</span>)}
    </div>
  ),
  RelationshipTimeline: ({ current_stage }: any) => (
    <div data-testid="relationship-timeline">{current_stage}</div>
  ),
  HealthScoreCard: ({ score }: any) => (
    <div data-testid="health-score-card">{score}</div>
  ),
  RelationshipChart: ({ chart_type }: any) => (
    <div data-testid="relationship-chart">{chart_type}</div>
  ),
  RelationshipDashboard: ({ summary }: any) => (
    <div data-testid="relationship-dashboard">{summary}</div>
  ),

  // 聊天助手组件
  MessageSent: ({ message_id, status }: any) => (
    <div data-testid="message-sent" data-status={status}>{message_id}</div>
  ),
  ConversationList: ({ conversations }: any) => (
    <div data-testid="conversation-list">
      {conversations?.map((c: any, i: number) => <span key={i}>{c.id}</span>)}
    </div>
  ),
  ChatHistory: ({ messages }: any) => (
    <div data-testid="chat-history">
      {messages?.map((m: any, i: number) => <span key={i}>{m.content}</span>)}
    </div>
  ),
  SuggestionCards: ({ suggestions }: any) => (
    <div data-testid="suggestion-cards">
      {suggestions?.map((s: any, i: number) => <span key={i}>{s.text}</span>)}
    </div>
  ),
  UnreadBadge: ({ count }: any) => (
    <div data-testid="unread-badge">{count}</div>
  ),

  // 话题建议组件
  TopicKit: ({ topics }: any) => (
    <div data-testid="topic-kit">
      {topics?.map((t: any, i: number) => <span key={i}>{t.title}</span>)}
    </div>
  ),
  TopicSuggestions: ({ suggestions }: any) => (
    <div data-testid="topic-suggestions">
      {suggestions?.map((s: any, i: number) => <span key={i}>{s.title}</span>)}
    </div>
  ),
  RelationshipCurator: ({ relationship }: any) => (
    <div data-testid="relationship-curator">{relationship?.status}</div>
  ),

  // 教练组件
  VideoDateCoachDashboard: ({ coaching }: any) => (
    <div data-testid="video-date-coach">{coaching?.tips || '约会教练'}</div>
  ),
  DateSimulationFeedback: ({ feedback }: any) => (
    <div data-testid="date-simulation-feedback">{feedback?.rating}</div>
  ),
  PerformanceCoachDashboard: ({ metrics }: any) => (
    <div data-testid="performance-coach">{metrics?.score || '绩效教练'}</div>
  ),
  CoachEmpty: ({ message }: any) => (
    <div data-testid="coach-empty">{message}</div>
  ),

  // 活动准备组件
  PrepChecklist: ({ items }: any) => (
    <div data-testid="prep-checklist">
      {items?.map((i: any, idx: number) => <span key={idx}>{i.text}</span>)}
    </div>
  ),
  OutfitRecommendations: ({ outfits }: any) => (
    <div data-testid="outfit-recommendations">
      {outfits?.map((o: any, i: number) => <span key={i}>{o.style}</span>)}
    </div>
  ),
  DateAssistantCard: ({ suggestion }: any) => (
    <div data-testid="date-assistant-card">{suggestion?.title}</div>
  ),
  DateReview: ({ review }: any) => (
    <div data-testid="date-review">{review?.rating}</div>
  ),
  VenueRecommendations: ({ venues }: any) => (
    <div data-testid="venue-recommendations">
      {venues?.map((v: any, i: number) => <span key={i}>{v.name}</span>)}
    </div>
  ),
  MilestoneCard: ({ type }: any) => (
    <div data-testid="milestone-card">{type}</div>
  ),

  // 仪表板组件
  RiskControlDashboard: ({ metrics }: any) => (
    <div data-testid="risk-control-dashboard">{metrics?.level}</div>
  ),
  RiskAssessmentDashboard: ({ assessment }: any) => (
    <div data-testid="risk-assessment-dashboard">{assessment?.score}</div>
  ),
  ShareGrowthDashboard: ({ metrics }: any) => (
    <div data-testid="share-growth-dashboard">{metrics?.invites}</div>
  ),
  ActivityDirectorDashboard: ({ activities }: any) => (
    <div data-testid="activity-director-dashboard">
      {activities?.map((a: any, i: number) => <span key={i}>{a.name}</span>)}
    </div>
  ),
  ConversationMatchmakerDashboard: ({ matches }: any) => (
    <div data-testid="conversation-matchmaker-dashboard">
      {matches?.map((m: any, i: number) => <span key={i}>{m.id}</span>)}
    </div>
  ),

  // 趋势组件
  RelationshipTrendChart: ({ data }: any) => (
    <div data-testid="relationship-trend-chart">{data?.length || 0} points</div>
  ),
  RelationshipWeather: ({ weather }: any) => (
    <div data-testid="relationship-weather-simple">{weather}</div>
  ),
  ConflictMeter: ({ level }: any) => (
    <div data-testid="conflict-meter">{level}</div>
  ),
  MediationEmpty: ({ message }: any) => (
    <div data-testid="mediation-empty">{message}</div>
  ),
}))

describe('GenerativeUIRenderer Component', () => {
  const mockOnAction = jest.fn()

  const matchSpotlightConfig = {
    component_type: 'match_spotlight',
    props: {
      match: { name: '测试用户', age: 28 }
    }
  }

  const giftGridConfig = {
    component_type: 'gift_grid',
    props: {
      gifts: [{ name: '巧克力' }, { name: '鲜花' }]
    }
  }

  const dateSpotListConfig = {
    component_type: 'date_spot_list',
    props: {
      spots: [{ name: '咖啡厅' }, { name: '公园' }]
    }
  }

  const safetyAlertConfig = {
    component_type: 'safety_alert',
    props: {
      level: 'high',
      message: '安全警告'
    }
  }

  const emptyStateConfig = {
    component_type: 'empty_state',
    props: {
      message: '暂无内容'
    }
  }

  const unknownConfig = {
    component_type: 'unknown_type',
    props: {}
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render match spotlight correctly', () => {
    render(<GenerativeUIRenderer uiConfig={matchSpotlightConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('match-spotlight')).toBeInTheDocument()
    expect(screen.getByText('测试用户')).toBeInTheDocument()
  })

  it('should render gift grid correctly', () => {
    render(<GenerativeUIRenderer uiConfig={giftGridConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('gift-grid')).toBeInTheDocument()
    expect(screen.getByText('巧克力')).toBeInTheDocument()
    expect(screen.getByText('鲜花')).toBeInTheDocument()
  })

  it('should render date spot list correctly', () => {
    render(<GenerativeUIRenderer uiConfig={dateSpotListConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('date-spot-list')).toBeInTheDocument()
    expect(screen.getByText('咖啡厅')).toBeInTheDocument()
  })

  it('should render safety alert correctly', () => {
    render(<GenerativeUIRenderer uiConfig={safetyAlertConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('safety-alert')).toBeInTheDocument()
    expect(screen.getByText('安全警告')).toBeInTheDocument()
  })

  it('should render empty state correctly', () => {
    render(<GenerativeUIRenderer uiConfig={emptyStateConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.getByText('暂无内容')).toBeInTheDocument()
  })

  it('should render empty state for unknown component type', () => {
    render(<GenerativeUIRenderer uiConfig={unknownConfig} onAction={mockOnAction} />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.getByText('未知组件类型：unknown_type')).toBeInTheDocument()
  })

  it('should call onAction when action button is clicked', () => {
    render(<GenerativeUIRenderer uiConfig={matchSpotlightConfig} onAction={mockOnAction} />)

    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[0])

    expect(mockOnAction).toHaveBeenCalledWith('view')
  })

  it('should handle undefined onAction gracefully', () => {
    // Should not throw error when onAction is undefined
    expect(() => {
      render(<GenerativeUIRenderer uiConfig={matchSpotlightConfig} />)
    }).not.toThrow()
  })

  it('should render component container', () => {
    const { container } = render(<GenerativeUIRenderer uiConfig={matchSpotlightConfig} onAction={mockOnAction} />)

    expect(container.querySelector('.generative-ui-container')).toBeInTheDocument()
  })
})
