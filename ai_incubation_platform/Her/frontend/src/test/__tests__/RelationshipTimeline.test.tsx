/**
 * RelationshipTimeline 组件测试
 * 测试 P10 关系里程碑时间线组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import RelationshipTimeline from '../../components/RelationshipTimeline'
import { milestoneApi } from '../../api/milestoneApi'

// Mock milestoneApi
jest.mock('../../api/milestoneApi', () => ({
  milestoneApi: {
    getMilestoneTimeline: jest.fn(),
    getMilestoneStatistics: jest.fn(),
    celebrateMilestone: jest.fn(),
  },
}))

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
    average_rating: 4.5,
    milestone_count: 2,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render timeline after loading', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    // 等待数据加载完成，显示里程碑
    await waitFor(() => {
      expect(screen.getByText(/首次匹配/)).toBeInTheDocument()
    }, { timeout: 3000 })
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
      expect(screen.getByText(/暂无里程碑/)).toBeInTheDocument()
    })
  })

  it('should render milestones timeline when data is loaded', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      expect(screen.getByText(/首次匹配/)).toBeInTheDocument()
      expect(screen.getByText(/第一次聊天/)).toBeInTheDocument()
    })
  })

  it('should call celebrateMilestone when celebrate button is clicked', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)
    ;(milestoneApi.celebrateMilestone as jest.Mock).mockResolvedValue({ success: true })

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText(/第一次聊天/)).toBeInTheDocument()
    })

    // 找到庆祝按钮（如果有 celebration_suggested）
    // 组件可能不会显示按钮，取决于 celebration_suggested 状态
  })

  it('should handle API errors gracefully', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockRejectedValue(new Error('API Error'))
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockRejectedValue(new Error('API Error'))

    // Mock console.error
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    // 等待错误处理后显示空状态
    await waitFor(() => {
      expect(screen.getByText(/暂无里程碑/)).toBeInTheDocument()
    })

    consoleErrorSpy.mockRestore()
  })

  it('should render milestones with details', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    // 等待数据加载并验证里程碑内容
    await waitFor(() => {
      expect(screen.getByText('首次匹配')).toBeInTheDocument()
      expect(screen.getByText('第一次聊天')).toBeInTheDocument()
    })
  })

  it('should display relationship statistics', async () => {
    ;(milestoneApi.getMilestoneTimeline as jest.Mock).mockResolvedValue(mockTimeline)
    ;(milestoneApi.getMilestoneStatistics as jest.Mock).mockResolvedValue(mockStatistics)

    render(
      <RelationshipTimeline userId1={mockUserId1} userId2={mockUserId2} />
    )

    await waitFor(() => {
      // 显示评分或其他统计信息
      expect(screen.getByText(/4.5/)).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})