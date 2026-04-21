import React from 'react'
import { render, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'
import HomePage from '../../pages/HomePage'
import * as storageModule from '../../utils/storage'
import { chatApi } from '../../api'

jest.mock('../../api', () => ({
  chatApi: {
    getConversations: jest.fn(),
  },
  conversationMatchingApi: {
    getAiPushRecommendations: jest.fn().mockResolvedValue({ matches: [] }),
  },
}))

// 将复杂子组件替换为轻量 mock，聚焦 HomePage 数据流
jest.mock('../../components/ChatInterface', () => () => <div data-testid="chat-interface">Chat Interface</div>)
jest.mock('../../components/ChatRoom', () => () => <div data-testid="chat-room">Chat Room</div>)
jest.mock('../../components/MatchCard', () => () => <div data-testid="match-card">Match Card</div>)
jest.mock('../../components/FeaturesDrawer', () => ({
  __esModule: true,
  default: () => <div data-testid="features-drawer">Features Drawer</div>,
  FeaturesButton: () => <button>features</button>,
}))
jest.mock('../../components/PushNotifications', () => () => <div data-testid="push">Push</div>)
jest.mock('../../components/AgentFloatingBall', () => () => <div data-testid="ball">Ball</div>)
jest.mock('../../pages/SwipeMatchPage', () => () => <div data-testid="swipe">Swipe</div>)
jest.mock('../../pages/WhoLikesMePage', () => () => <div data-testid="likes">Likes</div>)
jest.mock('../../pages/ConfidenceManagementPage', () => () => <div data-testid="confidence">Confidence</div>)
jest.mock('../../pages/FaceVerificationPage', () => () => <div data-testid="face">Face</div>)
jest.mock('../../components/YourTurnReminder', () => () => <div data-testid="turn">Turn</div>)
jest.mock('../../components/FeatureGuideModal', () => () => <div data-testid="guide">Guide</div>)

const renderWithRouter = (component: React.ReactElement) =>
  render(<MemoryRouter>{component}</MemoryRouter>)

describe('HomePage conversation summary cache', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorage.clear()
  })

  it('loads cached conversation summaries before polling', async () => {
    const cached = [
      {
        id: 'conv-1',
        user_id_1: 'user-anonymous-dev',
        user_id_2: 'u2',
        last_message_preview: 'cached msg',
        last_message_at: new Date().toISOString(),
        unread_count: 2,
        last_sync_at: new Date().toISOString(),
      },
    ]
    const getCacheSpy = jest
      .spyOn(storageModule.conversationSummaryStorage, 'getConversations')
      .mockReturnValue(cached as any)
    ;(chatApi.getConversations as jest.Mock).mockResolvedValue([])

    renderWithRouter(<HomePage />)

    await waitFor(() => {
      expect(getCacheSpy).toHaveBeenCalledWith('anonymous')
    })
  })

  it('writes server conversations back into cache after poll', async () => {
    jest
      .spyOn(storageModule.conversationSummaryStorage, 'getConversations')
      .mockReturnValue([])
    const setCacheSpy = jest.spyOn(storageModule.conversationSummaryStorage, 'setConversations')
    const serverRows = [
      {
        id: 'conv-2',
        user_id_1: 'user-anonymous-dev',
        user_id_2: 'u3',
        last_message_preview: 'server msg',
        last_message_at: new Date().toISOString(),
        unread_count: 1,
      },
    ]
    ;(chatApi.getConversations as jest.Mock).mockResolvedValue(serverRows)

    renderWithRouter(<HomePage />)

    await waitFor(() => {
      expect(setCacheSpy).toHaveBeenCalledWith('anonymous', serverRows)
    })
  })
})

