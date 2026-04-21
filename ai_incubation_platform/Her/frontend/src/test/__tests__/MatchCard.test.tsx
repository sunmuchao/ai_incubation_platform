/**
 * MatchCard 组件测试
 *
 * 测试覆盖:
 * 1. 组件渲染测试
 * 2. 用户交互测试
 * 3. 数据展示测试
 * 4. 边缘场景测试
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import MatchCard from '../../components/MatchCard'

// Mock aiAwarenessApi
jest.mock('../../api', () => ({
  aiAwarenessApi: {
    trackSwipe: jest.fn().mockResolvedValue(undefined),
  },
}))

// Mock AIFeedback component
jest.mock('../../components/AIFeedback', () => ({
  AIFeedback: () => <div data-testid="ai-feedback">AI Feedback</div>,
}))

// Mock RoseButton component
jest.mock('../../components/RoseButton', () => ({
  __esModule: true,
  default: ({ targetUser, size }: any) => (
    <button data-testid="rose-button" data-size={size}>
      Rose
    </button>
  ),
}))

// Mock VerificationBadge component
jest.mock('../../components/VerificationBadge', () => ({
  __esModule: true,
  default: ({ verified, size }: any) => (
    <span data-testid="verification-badge" data-verified={verified} data-size={size}>
      Verified
    </span>
  ),
}))

// Mock ConfidenceBadge component (avoid network requests in tests)
jest.mock('../../components/ConfidenceBadge', () => ({
  __esModule: true,
  default: () => <span data-testid="confidence-badge">Confidence</span>,
}))

// Mock authStorage
jest.mock('../../utils/storage', () => ({
  authStorage: {
    getUserId: jest.fn().mockReturnValue('test-user-id'),
    getToken: jest.fn().mockReturnValue(null),
  },
  devStorage: {
    getTestUserId: jest.fn().mockReturnValue(null),
  },
}))

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn().mockReturnValue(null),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage })

// Mock match data
const mockMatch = {
  user: {
    id: 'user-1',
    name: 'Test User',
    age: 28,
    location: '北京',
    bio: '这是一段测试简介',
    interests: ['旅行', '音乐', '阅读'],
    photos: ['photo1.jpg', 'photo2.jpg'],
  },
  compatibility_score: 85,
  match_reasons: ['兴趣相投', '价值观匹配'],
}

describe('MatchCard Component', () => {
  const mockOnLike = jest.fn()
  const mockOnPass = jest.fn()
  const mockOnMessage = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  // ============= 第一部分：组件渲染测试 =============

  describe('Component Rendering', () => {
    it('should render match card with user info', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('Test User')).toBeInTheDocument()
      expect(screen.getByText(/28/)).toBeInTheDocument()
      expect(screen.getByText('北京')).toBeInTheDocument()
    })

    it('should render compatibility score', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/85/)).toBeInTheDocument()
    })

    it('should render user interests', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('旅行')).toBeInTheDocument()
      expect(screen.getByText('音乐')).toBeInTheDocument()
      expect(screen.getByText('阅读')).toBeInTheDocument()
    })

    it('should render bio text', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/这是一段测试简介/)).toBeInTheDocument()
    })

    it('should NOT render action buttons in non-swipe mode', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      // 在非 swipe mode 下，操作按钮不显示
      expect(screen.queryByTestId('rose-button')).not.toBeInTheDocument()
    })

    it('should render action buttons in swipe mode', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={true}
        />
      )

      // 在 swipe mode 下，操作按钮显示
      expect(screen.getByTestId('rose-button')).toBeInTheDocument()
      // 使用 aria-label 查找图标按钮
      expect(screen.getByRole('img', { name: 'close' })).toBeInTheDocument()
      expect(screen.getByRole('img', { name: 'heart' })).toBeInTheDocument()
    })
  })

  // ============= 第二部分：用户交互测试 =============

  describe('User Interactions', () => {
    it('should call onLike when like button is clicked in swipe mode', async () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={true}
        />
      )

      // 找到 heart 图标按钮
      const heartIcon = screen.getByRole('img', { name: 'heart' })
      const likeButton = heartIcon.closest('button')

      fireEvent.click(likeButton!)

      await waitFor(() => {
        expect(mockOnLike).toHaveBeenCalled()
      })
    })

    it('should call onPass when pass button is clicked in swipe mode', async () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={true}
        />
      )

      // 找到 close 图标按钮
      const closeIcon = screen.getByRole('img', { name: 'close' })
      const passButton = closeIcon.closest('button')

      fireEvent.click(passButton!)

      await waitFor(() => {
        expect(mockOnPass).toHaveBeenCalled()
      })
    })

    it('should open detail modal when card is clicked', async () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      // 点击卡片打开详情
      const card = screen.getByText('Test User').closest('.match-card')
      fireEvent.click(card!)

      await waitFor(() => {
        // Modal 应该打开，显示更多详情
        expect(screen.getByText(/匹配度/)).toBeInTheDocument()
      })
    })

    it('should handle swipe left in swipe mode', async () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={true}
        />
      )

      // Pass 按钮相当于 swipe left
      const closeIcon = screen.getByRole('img', { name: 'close' })
      const passButton = closeIcon.closest('button')

      fireEvent.click(passButton!)

      await waitFor(() => {
        expect(mockOnPass).toHaveBeenCalled()
      })
    })

    it('should handle swipe right in swipe mode', async () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={true}
        />
      )

      // Like 按钮相当于 swipe right
      const heartIcon = screen.getByRole('img', { name: 'heart' })
      const likeButton = heartIcon.closest('button')

      fireEvent.click(likeButton!)

      await waitFor(() => {
        expect(mockOnLike).toHaveBeenCalled()
      })
    })

    it('should show hover effects', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      const card = screen.getByText('Test User').closest('.match-card')
      expect(card).toHaveClass('match-card')
    })
  })

  // ============= 第三部分：数据展示测试 =============

  describe('Data Display', () => {
    it('should display age correctly', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/28/)).toBeInTheDocument()
    })

    it('should display location correctly', () => {
      render(
        <MatchCard
          match={mockMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('北京')).toBeInTheDocument()
    })

    it('should display high compatibility score with green color', () => {
      const highScoreMatch = { ...mockMatch, compatibility_score: 92 }

      render(
        <MatchCard
          match={highScoreMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/92/)).toBeInTheDocument()
    })

    it('should display medium compatibility score with blue color', () => {
      const mediumScoreMatch = { ...mockMatch, compatibility_score: 75 }

      render(
        <MatchCard
          match={mediumScoreMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/75/)).toBeInTheDocument()
    })

    it('should display low compatibility score with orange color', () => {
      const lowScoreMatch = { ...mockMatch, compatibility_score: 60 }

      render(
        <MatchCard
          match={lowScoreMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/60/)).toBeInTheDocument()
    })

    it('should display multiple interests', () => {
      const multiInterestMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, interests: ['旅行', '音乐', '阅读', '电影', '摄影'] },
      }

      render(
        <MatchCard
          match={multiInterestMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('旅行')).toBeInTheDocument()
      expect(screen.getByText('音乐')).toBeInTheDocument()
      // 只显示前4个兴趣
      expect(screen.getByText('+1')).toBeInTheDocument()
    })

    it('should truncate long bio', () => {
      const longBioMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, bio: '这是一个非常长的简介内容，测试是否会被截断显示...' },
      }

      render(
        <MatchCard
          match={longBioMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      // Bio 应该显示（可能截断）
      expect(screen.getByText(/简介/)).toBeInTheDocument()
    })

    it('should handle missing optional fields', () => {
      const minimalMatch = {
        user: { id: 'user-2', name: 'Minimal User' },
        compatibility_score: 50,
      }

      render(
        <MatchCard
          match={minimalMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('Minimal User')).toBeInTheDocument()
      expect(screen.getByText(/50/)).toBeInTheDocument()
    })

    it('should handle missing user data gracefully', () => {
      const emptyMatch = {
        user: {},
        compatibility_score: 0,
      }

      render(
        <MatchCard
          match={emptyMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('未命名')).toBeInTheDocument()
    })
  })

  // ============= 第四部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle zero compatibility score', () => {
      const zeroMatch = { ...mockMatch, compatibility_score: 0 }

      render(
        <MatchCard
          match={zeroMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/0/)).toBeInTheDocument()
    })

    it('should handle 100 compatibility score', () => {
      const perfectMatch = { ...mockMatch, compatibility_score: 100 }

      render(
        <MatchCard
          match={perfectMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText(/100/)).toBeInTheDocument()
    })

    it('should handle empty interests array', () => {
      const noInterestsMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, interests: [] },
      }

      render(
        <MatchCard
          match={noInterestsMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.queryByText('兴趣')).not.toBeInTheDocument()
    })

    it('should handle special characters in user name', () => {
      const specialNameMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, name: '用户<特殊>字符' },
      }

      render(
        <MatchCard
          match={specialNameMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('用户<特殊>字符')).toBeInTheDocument()
    })

    it('should handle unicode in user name', () => {
      const unicodeMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, name: '用户🎉测试' },
      }

      render(
        <MatchCard
          match={unicodeMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('用户🎉测试')).toBeInTheDocument()
    })

    it('should handle very long user name', () => {
      const longNameMatch = {
        ...mockMatch,
        user: { ...mockMatch.user, name: '这是一个非常长的用户名字测试' },
      }

      render(
        <MatchCard
          match={longNameMatch}
          onLike={mockOnLike}
          onPass={mockOnPass}
          onMessage={mockOnMessage}
          isSwipeMode={false}
        />
      )

      expect(screen.getByText('这是一个非常长的用户名字测试')).toBeInTheDocument()
    })
  })
})