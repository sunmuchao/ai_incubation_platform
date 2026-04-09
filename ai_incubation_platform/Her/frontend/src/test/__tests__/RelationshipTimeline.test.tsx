/**
 * RelationshipTimeline 组件测试
 * 测试 P10 关系里程碑时间线组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import RelationshipTimeline from '../../components/RelationshipTimeline'
import { milestoneApi } from '../../api/p10_api'

// Mock p10_api
jest.mock('../../api/p10_api', () => ({
  milestoneApi: {
    getMilestoneTimeline: jest.fn(),
    getMilestoneStatistics: jest.fn(),
    celebrateMilestone: jest.fn(),
  },
}))

// Mock Ant Design 组件
jest.mock('antd', () => {
  const actualAntd = jest.requireActual('antd')
  return {
    ...actualAntd,
    Spin: ({ children, tip }: any) => (
      <div data-testid="spin" data-tip={tip}>
        {children || 'loading'}
      </div>
    ),
    Empty: ({ description }: any) => (
      <div data-testid="empty">{description}</div>
    ),
    Card: ({ children, className, hoverable, onClick }: any) => (
      <div
        className={className}
        data-testid="card"
        onClick={onClick}
      >
        {children}
      </div>
    ),
    Timeline: ({ children }: any) => (
      <div data-testid="timeline">{children}</div>
    ),
    'Timeline.Item': ({ children, color }: any) => (
      <div data-testid="timeline-item" data-color={color}>
        {children}
      </div>
    ),
    Tag: ({ children, color }: any) => (
      <span data-testid="tag" data-color={color}>{children}</span>
    ),
    Button: ({ children, onClick, icon, type, size }: any) => (
      <button
        data-testid="button"
        data-type={type}
        data-size={size}
        onClick={onClick}
      >
        {children}
      </button>
    ),
    Modal: ({ children, open, title, onCancel }: any) =>
      open ? (
        <div data-testid="modal" onClick={onCancel}>
          {title}
          {children}
        </div>
      ) : null,
    Progress: ({ percent, strokeColor }: any) => (
      <div data-testid="progress" data-percent={percent} data-color={strokeColor} />
    ),
    Rate: ({ value, disabled }: any) => (
      <div data-testid="rate" data-value={value} data-disabled={disabled} />
    ),
    Space: ({ children }: any) => <div data-testid="space">{children}</div>,
    Typography: {
      Title: ({ level, children }: any) => (
        <h{level} data-testid="title">{children}</h{level}>
      ),
      Text: ({ children, strong, type }: any) => (
        <span data-testid="text" data-strong={strong} data-type={type}>
          {children}
        </span>
      ),
      Paragraph: ({ children, ellipsis }: any) => (
        <p data-testid="paragraph">{children}</p>
      ),
    },
  }
})

describe('RelationshipTimeline Component', () => {
  const mockUserId1 = 'user-1'
  const mockUserId2 = 'user-2'

  const mockMilestones = [
    {
      id: 'milestone-1',
      milestone_type: 'first_match',
      title: '首次匹配',
      description: '你们成功匹配了',
      milestone_date: '2024-01-01T00:00:00Z',
      celebration_suggested: false,
      is_private: false,
    },
    {
      id: 'milestone-2',
      milestone_type: 'first_chat',
      title: '第一次聊天',
      description: '开始了第一次交流',
      milestone_date: '2024-01-02T00:00:00Z',
      celebration_suggested: true,
      is_private: false,
    },
  ]

  const mockTimeline = {
    milestones: mockMilestones,
    relationship_duration_days: 30,
    milestone_count: 2,
    average_rating: 4.5,
  }

  const mockStatistics = {
    total_milestones: 2,
    by_type: { first_match: 1, first_chat: 1 },
    by_month: { '2024-01': 2 },
    relationship_score: 75,
    growth_trend: 'improving' as const,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render loading state initially', async () => {
    (milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    (milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    expect(screen.getByTestId('spin')).toBeInTheDocument()
  })

  it('should render empty state when no milestones', async () => {
    const emptyTimeline = {
      milestones: [],
      relationship_duration_days: 0,
      milestone_count: 0,
      average_rating: 0,
    }

    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(emptyTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByTestId('empty')).toBeInTheDocument()
    })

    expect(screen.getByText('暂无里程碑记录')).toBeInTheDocument()
  })

  it('should render milestones timeline when data is loaded', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByTestId('timeline')).toBeInTheDocument()
    })

    expect(screen.getByTestId('timeline-item')).toBeInTheDocument()
  })

  it('should call celebrateMilestone when celebrate button is clicked', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)
    ;(milestoneApi.celebrateMilestone as jest.Mock).mockResolvedValue({ status: 'success' })

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByTestId('timeline')).toBeInTheDocument()
    })

    // Find and click celebrate button
    const celebrateButtons = screen.getAllByTestId('button')
    const celebrateButton = celebrateButtons.find(
      btn => btn.getAttribute('data-type') === 'primary'
    )

    if (celebrateButton) {
      fireEvent.click(celebrateButton)
    }

    expect(milestoneApi.celebrateMilestone).toHaveBeenCalled()
  })

  it('should handle API errors gracefully', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockRejectedValue(new Error('API Error'))

    // Mock console.error to avoid polluting test output
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByTestId('empty')).toBeInTheDocument()
    })

    consoleErrorSpy.mockRestore()
  })

  it('should display milestone details in modal when clicked', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByTestId('timeline')).toBeInTheDocument()
    })

    // Click on milestone card
    const cards = screen.getAllByTestId('card')
    fireEvent.click(cards[0])

    // Modal should open
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
  })
})
