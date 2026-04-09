/**
 * GenerativeUI 组件测试
 * 测试 AI Native Generative UI 动态容器组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import GenerativeUI from '../../components/GenerativeUI'

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
    Typography: {
      Text: ({ children, strong, className }: any) => (
        <span data-testid="text" data-strong={strong} className={className}>
          {children}
        </span>
      ),
    },
  }
})

describe('GenerativeUI Component', () => {
  const mockOnAction = jest.fn()

  const matchData = {
    type: 'match' as const,
    priority: 'high' as const,
    ai_message: '为你找到一位非常匹配的对象',
    data: { name: '测试用户', age: 28 },
    actions: [
      { label: '查看详情', action: 'view' },
      { label: '跳过', action: 'skip' },
    ],
  }

  const analysisData = {
    type: 'analysis' as const,
    priority: 'medium' as const,
    ai_message: '根据你的行为模式分析，你偏好深度交流',
    data: { score: 85, category: 'communication' },
    actions: [
      { label: '了解详情', action: 'details' },
    ],
  }

  const suggestionData = {
    type: 'suggestion' as const,
    priority: 'low' as const,
    ai_message: '建议尝试新的约会地点',
    data: { venue: '咖啡厅', location: '朝阳区' },
    actions: [
      { label: '采纳建议', action: 'accept' },
      { label: '稍后考虑', action: 'later' },
    ],
  }

  const notificationData = {
    type: 'notification' as const,
    priority: 'high' as const,
    ai_message: '你有新的消息提醒',
    data: { count: 3 },
    actions: [
      { label: '查看', action: 'view' },
    ],
  }

  const defaultData = {
    type: 'default' as const,
    priority: 'medium' as const,
    ai_message: '这是一条默认消息',
    data: { info: 'test' },
    actions: [
      { label: '确定', action: 'ok' },
    ],
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render match card correctly', () => {
    render(<GenerativeUI data={matchData} onAction={mockOnAction} />)

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('为你找到一位非常匹配的对象')).toBeInTheDocument()
    expect(screen.getByText('查看详情')).toBeInTheDocument()
    expect(screen.getByText('跳过')).toBeInTheDocument()
  })

  it('should render analysis card correctly', () => {
    render(<GenerativeUI data={analysisData} onAction={mockOnAction} />)

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('AI 分析报告')).toBeInTheDocument()
    expect(screen.getByText('根据你的行为模式分析，你偏好深度交流')).toBeInTheDocument()
  })

  it('should render suggestion card correctly', () => {
    render(<GenerativeUI data={suggestionData} onAction={mockOnAction} />)

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('💡')).toBeInTheDocument()
    expect(screen.getByText('建议尝试新的约会地点')).toBeInTheDocument()
  })

  it('should render notification card correctly', () => {
    render(<GenerativeUI data={notificationData} onAction={mockOnAction} />)

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('🔔')).toBeInTheDocument()
    expect(screen.getByText('你有新的消息提醒')).toBeInTheDocument()
  })

  it('should render default card for unknown type', () => {
    render(<GenerativeUI data={defaultData} onAction={mockOnAction} />)

    expect(screen.getByTestId('card')).toBeInTheDocument()
    expect(screen.getByText('这是一条默认消息')).toBeInTheDocument()
  })

  it('should call onAction when action button is clicked', () => {
    render(<GenerativeUI data={matchData} onAction={mockOnAction} />)

    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[0])

    expect(mockOnAction).toHaveBeenCalledWith('view')
  })

  it('should apply correct border color based on priority', () => {
    const { rerender } = render(
      <GenerativeUI data={matchData} onAction={mockOnAction} />
    )

    const card = screen.getByTestId('card')
    // High priority should have red border
    expect(card).toHaveStyle({ borderColor: '#ff4d4f' })

    rerender(<GenerativeUI data={analysisData} onAction={mockOnAction} />)
    // Medium priority should have orange border
    expect(card).toHaveStyle({ borderColor: '#faad14' })

    rerender(<GenerativeUI data={suggestionData} onAction={mockOnAction} />)
    // Low priority should have green border
    expect(card).toHaveStyle({ borderColor: '#52c41a' })
  })

  it('should handle animation state correctly', async () => {
    jest.useFakeTimers()

    render(<GenerativeUI data={matchData} onAction={mockOnAction} />)

    // Initially should have animating class
    const card = screen.getByTestId('card')
    expect(card).toHaveClass('animating')

    // Fast-forward timers
    jest.advanceTimersByTime(300)

    await waitFor(() => {
      expect(card).not.toHaveClass('animating')
    })

    jest.useRealTimers()
  })

  it('should reset animation when data changes', async () => {
    jest.useFakeTimers()

    const { rerender } = render(
      <GenerativeUI data={matchData} onAction={mockOnAction} />
    )

    jest.advanceTimersByTime(300)

    await waitFor(() => {
      expect(screen.getByTestId('card')).not.toHaveClass('animating')
    })

    // Change data
    rerender(<GenerativeUI data={analysisData} onAction={mockOnAction} />)

    // Should have animating class again
    expect(screen.getByTestId('card')).toHaveClass('animating')

    jest.useRealTimers()
  })

  it('should render all action buttons', () => {
    render(<GenerativeUI data={matchData} onAction={mockOnAction} />)

    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBe(2)
    expect(buttons[0]).toHaveTextContent('查看详情')
    expect(buttons[1]).toHaveTextContent('跳过')
  })

  it('should handle undefined onAction gracefully', () => {
    // Should not throw error when onAction is undefined
    expect(() => {
      render(<GenerativeUI data={matchData} />)
    }).not.toThrow()
  })
})
