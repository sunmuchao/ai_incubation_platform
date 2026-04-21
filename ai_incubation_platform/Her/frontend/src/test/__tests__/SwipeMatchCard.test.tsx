import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import SwipeMatchCard from '../../components/SwipeMatchCard'

jest.mock('../../components/RoseButton', () => ({
  __esModule: true,
  default: () => <button data-testid="rose-button">Rose</button>,
}))

jest.mock('../../components/VerificationBadge', () => ({
  __esModule: true,
  default: () => <span data-testid="verification-badge">Verified</span>,
}))

jest.mock('../../utils/storage', () => ({
  authStorage: {
    getUserId: jest.fn().mockReturnValue('test-user-id'),
    getToken: jest.fn().mockReturnValue(null),
  },
  devStorage: {
    getTestUserId: jest.fn().mockReturnValue(null),
  },
}))

const baseMatch = {
  user: {
    id: 'user-1',
    name: '候选人A',
    age: 27,
    gender: 'female',
    location: '上海',
    bio: '测试资料',
    interests: [],
    verified: false,
  },
  compatibility_score: 50,
  score: 0.5,
  common_interests: [],
  reasoning: '',
}

describe('SwipeMatchCard vector highlights', () => {
  const renderSwipeCard = (overrides: Record<string, unknown> = {}) => {
    const match = {
      ...baseMatch,
      ...overrides,
    }
    return render(<SwipeMatchCard match={match as any} index={0} isActive />)
  }

  it('renders vector_match_highlights when reasoning is empty', () => {
    renderSwipeCard({
      vector_match_highlights: {
        relationship_goal: 'serious',
        want_children: 'yes',
        spending_style: 'balanced',
      },
    })

    expect(screen.getByText((text) => text.includes('关系目标：') && text.includes('serious'))).toBeInTheDocument()
    expect(screen.getByText((text) => text.includes('生育观：') && text.includes('yes'))).toBeInTheDocument()
    expect(screen.getByText((text) => text.includes('消费观：') && text.includes('balanced'))).toBeInTheDocument()
  })

  it('does not render vector fallback reasons without vector_match_highlights', () => {
    renderSwipeCard({
      vector_match_highlights: undefined,
    })

    expect(screen.queryByText((text) => text.includes('关系目标：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('生育观：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('消费观：'))).not.toBeInTheDocument()
  })

  it('prefers reasoning text over vector fallback reasons', () => {
    renderSwipeCard({
      reasoning: '你们沟通风格非常契合',
      vector_match_highlights: {
        relationship_goal: 'serious',
        want_children: 'yes',
        spending_style: 'balanced',
      },
    })

    expect(screen.getByText('你们沟通风格非常契合')).toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('关系目标：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('生育观：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('消费观：'))).not.toBeInTheDocument()
  })

  it('renders only available vector fields when highlights are partial', () => {
    renderSwipeCard({
      vector_match_highlights: {
        relationship_goal: 'serious',
      },
    })

    expect(screen.getByText((text) => text.includes('关系目标：') && text.includes('serious'))).toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('生育观：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('消费观：'))).not.toBeInTheDocument()
  })

  it('does not render vector fields for null values', () => {
    renderSwipeCard({
      vector_match_highlights: {
        relationship_goal: null,
        want_children: null,
        spending_style: null,
      },
    })

    expect(screen.queryByText((text) => text.includes('关系目标：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('生育观：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('消费观：'))).not.toBeInTheDocument()
  })

  it('does not render vector fields for empty string values', () => {
    renderSwipeCard({
      vector_match_highlights: {
        relationship_goal: '',
        want_children: '',
        spending_style: '',
      },
    })

    expect(screen.queryByText((text) => text.includes('关系目标：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('生育观：'))).not.toBeInTheDocument()
    expect(screen.queryByText((text) => text.includes('消费观：'))).not.toBeInTheDocument()
  })
})

