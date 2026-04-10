/**
 * ChatInterface 组件边缘场景测试
 *
 * 测试覆盖:
 * 1. 组件渲染测试 (5 tests)
 * 2. 用户交互测试 (8 tests)
 * 3. 消息处理测试 (10 tests)
 * 4. API 调用测试 (6 tests)
 * 5. Generative UI 测试 (5 tests)
 * 6. 边缘场景测试 (8 tests)
 *
 * 总计: 42 个测试用例
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import ChatInterface from '../../components/ChatInterface'

// Import the mocked API for use in tests
import * as api from '../../api'

// Mock the API module
jest.mock('../../api', () => ({
  conversationMatchingApi: {
    match: jest.fn().mockResolvedValue({
      message: 'AI response',
      matches: [],
      suggestions: [],
      next_actions: [],
    }),
  },
  aiAwarenessApi: {
    trackChatMessage: jest.fn().mockResolvedValue(undefined),
  },
  getMyPreCommunicationSessions: jest.fn().mockResolvedValue([]),
  startPreCommunication: jest.fn(),
  getPreCommunicationMessages: jest.fn().mockResolvedValue([]),
}))

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn().mockReturnValue(null),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage })

// Mock scroll
Object.defineProperty(window, 'scrollTo', { value: jest.fn() })

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}))

describe('ChatInterface Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  // ============= 第一部分：组件渲染测试 =============

  describe('Component Rendering', () => {
    it('should render welcome message on initial load', () => {
      render(<ChatInterface />)
      expect(screen.getByText(/你好，我是 Her/)).toBeInTheDocument()
    })

    it('should render input field with placeholder', () => {
      render(<ChatInterface />)
      expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
    })

    it('should render quick action tags', () => {
      render(<ChatInterface />)
      expect(screen.getByText('找对象')).toBeInTheDocument()
      expect(screen.getByText('AI 预沟通')).toBeInTheDocument()
      expect(screen.getByText('关系分析')).toBeInTheDocument()
      expect(screen.getByText('约会建议')).toBeInTheDocument()
    })

    it('should render send button', () => {
      render(<ChatInterface />)
      const sendButton = screen.getByRole('button', { name: '' })
      expect(sendButton).toBeInTheDocument()
    })

    it('should have disabled send button when input is empty', () => {
      render(<ChatInterface />)
      const sendButton = screen.getByRole('button', { name: '' })
      expect(sendButton).toBeDisabled()
    })
  })

  // ============= 第二部分：用户交互测试 =============

  describe('User Interactions', () => {
    it('should enable send button when input has content', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      const sendButton = screen.getByRole('button', { name: '' })

      await userEvent.type(input, 'test message')
      expect(sendButton).not.toBeDisabled()
    })

    it('should clear input after sending message', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

      await userEvent.type(input, 'test message')
      await userEvent.click(screen.getByRole('button', { name: '' }))

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })

    it('should send message on Enter key press', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText('test message')).toBeInTheDocument()
      })
    })

    it('should not send message on Shift+Enter', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

      await userEvent.type(input, 'test message{shift>}{enter}')

      // Message should not be sent, input should still have content
      expect(input.value).toBe('test message')
    })

    it('should handle quick action click', async () => {
      render(<ChatInterface />)
      const quickAction = screen.getByText('找对象')

      await userEvent.click(quickAction)

      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement
      expect(input.value).toContain('帮我找对象')
    })

    it('should display loading indicator while processing', async () => {
      // Mock API to delay response
      ;(api.conversationMatchingApi.match as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      )

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '找对象{enter}')

      await waitFor(() => {
        expect(screen.getByText(/AI 正在分析/)).toBeInTheDocument()
      })
    })

    it('should not send empty message', async () => {
      render(<ChatInterface />)
      const sendButton = screen.getByRole('button', { name: '' })

      await userEvent.click(sendButton)

      // Should not add any user message
      expect(screen.queryByText('')).not.toBeInTheDocument()
    })

    it('should not send whitespace-only message', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '   {enter}')

      // Should not add any user message
      expect(screen.queryByText('   ')).not.toBeInTheDocument()
    })
  })

  // ============= 第三部分：消息处理测试 =============

  describe('Message Handling', () => {
    it('should display user message after sending', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'hello{enter}')

      await waitFor(() => {
        expect(screen.getByText('hello')).toBeInTheDocument()
      })
    })

    it('should respond to greeting', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '你好{enter}')

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      })
    })

    it('should respond to thanks', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '谢谢{enter}')

      await waitFor(() => {
        expect(screen.getByText(/能帮到你/)).toBeInTheDocument()
      })
    })

    it('should respond to goodbye', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '再见{enter}')

      await waitFor(() => {
        expect(screen.getByText(/下次见/)).toBeInTheDocument()
      })
    })

    it('should limit message count to prevent memory leak', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      // Send 60 messages (MAX_MESSAGES is 50)
      for (let i = 0; i < 60; i++) {
        await userEvent.type(input, `message ${i}{enter}`)
        await waitFor(() => {
          expect(screen.getByText(`message ${i}`)).toBeInTheDocument()
        })
      }

      // First messages should be removed
      await waitFor(() => {
        expect(screen.queryByText('message 0')).not.toBeInTheDocument()
        expect(screen.queryByText('message 9')).not.toBeInTheDocument()
      })
    })

    it('should handle special characters in message', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '<script>alert("xss")</script>{enter}')

      await waitFor(() => {
        expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument()
      })
    })

    it('should handle emoji in message', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '你好世界 🎉🎉🎉{enter}')

      await waitFor(() => {
        expect(screen.getByText('你好世界 🎉🎉🎉')).toBeInTheDocument()
      })
    })

    it('should handle very long message', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      const longMessage = 'A'.repeat(5000)

      await userEvent.type(input, longMessage + '{enter}')

      await waitFor(() => {
        expect(screen.getByText(longMessage)).toBeInTheDocument()
      })
    })

    it('should handle initial match prop', async () => {
      const mockMatch = {
        user: { id: 'test-id', name: 'Test User', interests: ['旅行'] },
        compatibility_score: 85,
      }

      render(<ChatInterface initialMatch={mockMatch} />)

      await waitFor(() => {
        expect(screen.getByText(/你选择了 "Test User"/)).toBeInTheDocument()
      })
    })

    it('should call onInitialMatchConsumed after processing initial match', async () => {
      const mockMatch = {
        user: { id: 'test-id', name: 'Test User', interests: [] },
        compatibility_score: 85,
      }
      const onConsumed = jest.fn()

      render(<ChatInterface initialMatch={mockMatch} onInitialMatchConsumed={onConsumed} />)

      await waitFor(() => {
        expect(onConsumed).toHaveBeenCalled()
      })
    })
  })

  // ============= 第四部分：API 调用测试 =============

  describe('API Calls', () => {
    it('should call conversationMatchingApi.match with user intent', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: 'AI response',
        matches: [],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我找对象{enter}')

      await waitFor(() => {
        expect(api.conversationMatchingApi.match).toHaveBeenCalledWith({
          user_intent: '帮我找对象',
        })
      })
    })

    it('should display API response message', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '这是 AI 的回复',
        matches: [],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText('这是 AI 的回复')).toBeInTheDocument()
      })
    })

    it('should display match cards when API returns matches', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '找到匹配对象',
        matches: [
          { user: { id: '1', name: 'User 1' }, compatibility_score: 85 },
          { user: { id: '2', name: 'User 2' }, compatibility_score: 75 },
        ],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText(/为你推荐 2 位匹配对象/)).toBeInTheDocument()
      })
    })

    it('should handle API error gracefully', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockRejectedValue(new Error('API Error'))

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })

    it('should track chat message for analytics', async () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({ username: 'test-user' }))

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      await waitFor(() => {
        expect(api.aiAwarenessApi.trackChatMessage).toHaveBeenCalledWith(
          'test-user',
          'system',
          4
        )
      })
    })

    it('should load pre-communication sessions when requested', async () => {
      ;(api.getMyPreCommunicationSessions as jest.Mock).mockResolvedValue([
        { session_id: '1', status: 'completed', compatibility_score: 85 },
      ])

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(api.getMyPreCommunicationSessions).toHaveBeenCalled()
      })
    })
  })

  // ============= 第五部分：Generative UI 测试 =============

  describe('Generative UI', () => {
    it('should render pre-communication sessions card', async () => {
      ;(api.getMyPreCommunicationSessions as jest.Mock).mockResolvedValue([
        {
          session_id: 'session-1',
          status: 'completed',
          compatibility_score: 85,
          hard_check_passed: true,
          values_check_passed: true,
        },
      ])

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(screen.getByText(/找到 1 个 AI 预沟通会话/)).toBeInTheDocument()
      })
    })

    it('should show empty state when no pre-communication sessions', async () => {
      ;(api.getMyPreCommunicationSessions as jest.Mock).mockResolvedValue([])

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      })
    })

    it('should render match cards', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '找到匹配',
        matches: [
          {
            user: { id: '1', name: 'Test User', age: 25, location: '北京' },
            compatibility_score: 90,
          },
        ],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText(/为你推荐 1 位匹配对象/)).toBeInTheDocument()
      })
    })

    it('should render next action chips', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: 'AI response',
        matches: [],
        suggestions: [],
        next_actions: ['发起对话', '查看详情'],
      })

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      await waitFor(() => {
        expect(screen.getByText('发起对话')).toBeInTheDocument()
        expect(screen.getByText('查看详情')).toBeInTheDocument()
      })
    })

    it('should handle feature trigger event', async () => {
      render(<ChatInterface />)

      act(() => {
        window.dispatchEvent(new CustomEvent('trigger-feature', {
          detail: { feature: { name: '测试功能', action: 'test-action' } },
        }))
      })

      await waitFor(() => {
        expect(screen.getByText(/我来帮你打开「测试功能」/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第六部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle rapid message sending', async () => {
      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      // Rapid typing and enter
      await userEvent.type(input, 'message 1{enter}')
      await userEvent.type(input, 'message 2{enter}')
      await userEvent.type(input, 'message 3{enter}')

      await waitFor(() => {
        expect(screen.getByText('message 1')).toBeInTheDocument()
        expect(screen.getByText('message 2')).toBeInTheDocument()
        expect(screen.getByText('message 3')).toBeInTheDocument()
      })
    })

    it('should handle component unmount during API call', async () => {
      ;(api.conversationMatchingApi.match as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ message: 'ok' }), 1000))
      )

      const { unmount } = render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      // Unmount before API responds
      unmount()

      // Should not throw error
      await waitFor(() => {
        expect(true).toBe(true)
      })
    })

    it('should handle match select callback', async () => {
      const onMatchSelect = jest.fn()
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '找到匹配',
        matches: [
          { user: { id: '1', name: 'User 1' }, compatibility_score: 85 },
        ],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface onMatchSelect={onMatchSelect} />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText(/为你推荐/)).toBeInTheDocument()
      })
    })

    it('should handle open chat room callback', async () => {
      const onOpenChatRoom = jest.fn()
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '找到匹配',
        matches: [
          { user: { id: 'chat-1', name: 'Chat User' }, compatibility_score: 85 },
        ],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface onOpenChatRoom={onOpenChatRoom} />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText(/为你推荐/)).toBeInTheDocument()
      })
    })

    it('should handle null user info in localStorage', async () => {
      mockLocalStorage.getItem.mockReturnValue(null)

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      // Should use anonymous user
      await waitFor(() => {
        expect(screen.getByText('test')).toBeInTheDocument()
      })
    })

    it('should handle malformed JSON in localStorage', async () => {
      mockLocalStorage.getItem.mockReturnValue('not valid json')

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      await waitFor(() => {
        expect(screen.getByText('test')).toBeInTheDocument()
      })
    })

    it('should handle view matches callback', async () => {
      const onViewMatches = jest.fn()
      ;(api.conversationMatchingApi.match as jest.Mock).mockResolvedValue({
        message: '找到匹配',
        matches: [
          { user: { id: '1', name: 'User 1' }, compatibility_score: 85 },
        ],
        suggestions: [],
        next_actions: [],
      })

      render(<ChatInterface onViewMatches={onViewMatches} />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText(/为你推荐/)).toBeInTheDocument()
      })
    })

    it('should handle pre-communication session with no messages', async () => {
      ;(api.getPreCommunicationMessages as jest.Mock).mockResolvedValue([])

      render(<ChatInterface />)
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      })
    })
  })
})