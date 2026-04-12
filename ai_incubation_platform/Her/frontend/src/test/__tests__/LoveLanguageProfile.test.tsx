/**
 * LoveLanguageProfile 组件测试
 * 测试 P13 爱之语画像组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import LoveLanguageProfile from '../../components/LoveLanguageProfile'
import { relationshipCoachSkill } from '../../api/skillClient'

// Mock relationshipCoachSkill (替代已删除的 loveLanguageProfileApi)
jest.mock('../../api/skillClient', () => ({
  relationshipCoachSkill: {
    analyzeLoveLanguage: jest.fn(),
    getLoveLanguageTranslation: jest.fn(),
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
    Empty: ({ description, image }: any) => (
      <div data-testid="empty">{description}</div>
    ),
    Card: ({ children, className, size }: any) => (
      <div className={className} data-testid="card" data-size={size}>
        {children}
      </div>
    ),
    Button: ({ children, onClick, icon, type, size, loading }: any) => (
      <button
        data-testid="button"
        data-type={type}
        data-size={size}
        data-loading={loading}
        onClick={onClick}
      >
        {children}
      </button>
    ),
    Tag: ({ children, color, size }: any) => (
      <span data-testid="tag" data-color={color} data-size={size}>{children}</span>
    ),
    Progress: ({ percent, strokeColor, size }: any) => (
      <div
        data-testid="progress"
        data-percent={percent}
        data-color={strokeColor}
        data-size={size}
      />
    ),
    Space: ({ children, wrap }: any) => (
      <div data-testid="space" data-wrap={wrap}>{children}</div>
    ),
    Typography: {
      Title: ({ level, children }: any) => {
        const HeadingTag = `h${level || 1}` as keyof JSX.IntrinsicElements
        return <HeadingTag data-testid="title">{children}</HeadingTag>
      },
      Text: ({ children, strong, type }: any) => (
        <span data-testid="text" data-strong={strong} data-type={type}>
          {children}
        </span>
      ),
      Paragraph: ({ children }: any) => (
        <p data-testid="paragraph">{children}</p>
      ),
    },
  }
})

describe('LoveLanguageProfile Component', () => {
  const mockUserId = 'user-123'

  const mockProfile = {
    id: 'profile-1',
    user_id: mockUserId,
    primary_love_language: 'words_of_affirmation' as const,
    secondary_love_language: 'quality_time' as const,
    language_scores: {
      words_of_affirmation: 0.85,
      quality_time: 0.72,
      receiving_gifts: 0.45,
      acts_of_service: 0.58,
      physical_touch: 0.40,
    },
    ai_analysis: '你主要通过肯定的言辞来表达和感受爱。你珍视真诚的赞美和鼓励的话语。',
    relationship_history: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
  }

  const mockDescription = {
    type: 'words_of_affirmation' as const,
    name: '肯定的言辞',
    description: '你通过赞美、感谢和鼓励来表达和感受爱',
    characteristics: ['喜欢听赞美', '重视鼓励', '善于表达感谢'],
    tips: ['多表达你的欣赏', '写感谢信或卡片', '避免批评和指责'],
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render loading state initially', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    expect(screen.getByTestId('spin')).toBeInTheDocument()
  })

  it('should render empty state when no profile exists', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: null,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('empty')).toBeInTheDocument()
    })

    expect(screen.getByText('暂无爱之语画像')).toBeInTheDocument()
  })

  it('should render analyze button when no profile exists', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: null,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('button')).toBeInTheDocument()
    })

    expect(screen.getByText('AI 分析我的爱之语')).toBeInTheDocument()
  })

  it('should call analyzeUserLoveLanguage when analyze button is clicked', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: null,
    })
    ;(loveLanguageProfileApi.analyzeUserLoveLanguage as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('button')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('button'))

    await waitFor(() => {
      expect(loveLanguageProfileApi.analyzeUserLoveLanguage).toHaveBeenCalledWith(mockUserId)
    })
  })

  it('should render profile data when profile is loaded', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })
    ;(loveLanguageProfileApi.getLoveLanguageDescription as jest.Mock).mockResolvedValue({
      success: true,
      love_language: 'words_of_affirmation',
      description: mockDescription,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('card')).toBeInTheDocument()
    })

    // Check if primary love language is displayed
    expect(screen.getByText('爱之语画像')).toBeInTheDocument()
    expect(screen.getByText('主要：肯定的言辞')).toBeInTheDocument()
  })

  it('should display language scores with progress bars', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })
    ;(loveLanguageProfileApi.getLoveLanguageDescription as jest.Mock).mockResolvedValue({
      success: true,
      love_language: 'words_of_affirmation',
      description: mockDescription,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('progress')).toBeInTheDocument()
    })

    // Verify progress bars are rendered for each language
    const progressBars = screen.getAllByTestId('progress')
    expect(progressBars.length).toBeGreaterThan(0)
  })

  it('should display AI analysis section', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })
    ;(loveLanguageProfileApi.getLoveLanguageDescription as jest.Mock).mockResolvedValue({
      success: true,
      love_language: 'words_of_affirmation',
      description: mockDescription,
    })

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('title')).toBeInTheDocument()
    })

    expect(screen.getByText('AI 分析')).toBeInTheDocument()
    expect(screen.getByText(mockProfile.ai_analysis)).toBeInTheDocument()
  })

  it('should call onProfileLoaded callback when profile is loaded', async () => {
    const mockCallback = jest.fn()

    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockResolvedValue({
      success: true,
      profile: mockProfile,
    })

    render(<LoveLanguageProfile userId={mockUserId} onProfileLoaded={mockCallback} />)

    await waitFor(() => {
      expect(mockCallback).toHaveBeenCalledWith(mockProfile)
    })
  })

  it('should handle API errors gracefully', async () => {
    ;(loveLanguageProfileApi.getUserLoveLanguageProfile as jest.Mock).mockRejectedValue(
      new Error('API Error')
    )

    // Mock console.error to avoid polluting test output
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(<LoveLanguageProfile userId={mockUserId} />)

    await waitFor(() => {
      expect(screen.getByTestId('empty')).toBeInTheDocument()
    })

    consoleErrorSpy.mockRestore()
  })
})
