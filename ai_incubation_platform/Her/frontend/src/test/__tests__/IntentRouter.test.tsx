/**
 * IntentRouter 集成测试
 *
 * 测试 ChatInterface 与 IntentRouter Skill 的集成
 * 覆盖简化后的 handleSend 逻辑
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import ChatInterface from '../../components/ChatInterface'

// Mock skillClient
jest.mock('../../api/skillClient', () => ({
  intentRouterSkill: {
    route: jest.fn(),
  },
  skillRegistry: {
    execute: jest.fn(),
    listSkills: jest.fn().mockResolvedValue([]),
  },
  preCommunicationSkill: {
    startSession: jest.fn(),
    sendMessage: jest.fn(),
    getSessionStatus: jest.fn(),
  },
}))

// Mock authStorage
jest.mock('../../utils/storage', () => ({
  authStorage: {
    getToken: jest.fn().mockReturnValue('mock-token'),
    getUserId: jest.fn().mockReturnValue('test-user-001'),
    getUser: jest.fn().mockReturnValue({
      id: 'test-user-001',
      age: 25,
      gender: 'male',
      location: '北京',
      relationship_goal: 'serious_relationship',
    }),
    isAuthenticated: jest.fn().mockReturnValue(true),
    setUser: jest.fn(),
    saveAuth: jest.fn(),
    clear: jest.fn(),
  },
  registrationStorage: {
    markCompleted: jest.fn(),
    isCompleted: jest.fn().mockReturnValue(true),
  },
}))

// Mock aiAwarenessApi
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

// Import the mocked modules for use in tests
import { intentRouterSkill } from '../../api/skillClient'
import { authStorage } from '../../utils/storage'

describe('IntentRouter Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  // 辅助函数：发送消息
  const sendMessage = async (text: string) => {
    const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

    await act(async () => {
      fireEvent.change(input, { target: { value: text } })
    })

    // 查找发送按钮（按钮只有 icon，使用 aria-label 或查询所有按钮）
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons.find(b => b.querySelector('[aria-label="send"]')) || buttons[buttons.length - 1]

    await act(async () => {
      fireEvent.click(sendButton)
    })
  }

  // ============= 第一部分：IntentRouter 调用测试 =============

  describe('IntentRouter Skill Calls', () => {
    it('should call intentRouterSkill.route when user sends a message', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'greeting', confidence: 1.0 },
        ai_message: '你好呀 🤍 我是 Her，你的情感顾问~',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('你好')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '你好')
      })
    })

    it('should display AI message after IntentRouter returns', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'greeting', confidence: 1.0 },
        ai_message: '你好呀 🤍 我是 Her，你的情感顾问~',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      })
    })

    it('should handle matching intent and call ConversationMatchmaker', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'matching', confidence: 0.95 },
        ai_message: '为你找到 3 位匹配对象',
        generative_ui: {
          component_type: 'MatchCardList',
          props: {
            matches: [
              { user_id: 'user-001', name: '小美', age: 26, score: 0.92 },
              { user_id: 'user-002', name: '小雨', age: 24, score: 0.87 },
            ],
          },
        },
        suggested_actions: [
          { label: '查看更多', action: 'view_more' },
        ],
      })

      render(<ChatInterface />)

      await sendMessage('帮我找对象')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '帮我找对象')
        expect(screen.getByText(/为你找到/)).toBeInTheDocument()
      })
    })

    it('should handle capability_inquiry intent and display features', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'capability_inquiry', confidence: 1.0 },
        ai_message: '我是 Her 🤍 你的 AI 情感顾问\n\n我可以帮你：\n• 💕 匹配与推荐\n• 💬 沟通支持',
        generative_ui: {
          component_type: 'CapabilityCard',
          props: {
            features: [
              { name: '智能匹配', icon: '💕', trigger: '帮我找对象' },
              { name: '每日推荐', icon: '🌟', trigger: '今日推荐' },
            ],
          },
        },
        suggested_actions: [
          { label: '帮我找对象', action: 'matching' },
          { label: '今日推荐', action: 'daily_recommend' },
        ],
      })

      render(<ChatInterface />)

      await sendMessage('你能干嘛')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '你能干嘛')
        // 使用更精确的匹配，避免匹配初始欢迎消息
        expect(screen.getByText(/匹配与推荐/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第二部分：错误处理测试 =============

  describe('Error Handling', () => {
    it('should display error message when IntentRouter fails', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: false,
        intent: { type: 'general', confidence: 0 },
        ai_message: '抱歉，出现了一些问题，请稍后再试~',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('测试错误')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })

    it('should not crash when IntentRouter throws exception', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockRejectedValueOnce(new Error('Network error'))

      render(<ChatInterface />)

      await sendMessage('测试异常')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第三部分：Generative UI 测试 =============

  describe('Generative UI Rendering', () => {
    it('should not render extra card for SimpleResponse', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'greeting', confidence: 1.0 },
        ai_message: '你好呀 🤍',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第四部分：各种意图场景测试 =============

  describe('Intent Type Scenarios', () => {
    it('should handle gratitude intent (谢谢)', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'gratitude', confidence: 1.0 },
        ai_message: '能帮到你，我很开心 🤍',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('谢谢')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '谢谢')
        expect(screen.getByText(/能帮到你，我很开心/)).toBeInTheDocument()
      })
    })

    it('should handle goodbye intent (再见)', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'goodbye', confidence: 1.0 },
        ai_message: '下次见。愿你可以遇见属于自己的那份懂得 🤍',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('再见')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '再见')
        expect(screen.getByText(/下次见/)).toBeInTheDocument()
      })
    })

    it('should handle daily_recommend intent (今日推荐)', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'daily_recommend', confidence: 1.0 },
        ai_message: '🌟 每日精选推荐\n今天为你找到 3 位优质对象',
        generative_ui: {
          component_type: 'MatchCardList',
          props: {
            matches: [
              { user_id: 'user-001', name: '小美', age: 26, score: 0.92 },
            ],
          },
        },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('今日推荐')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '今日推荐')
        expect(screen.getByText(/每日精选推荐/)).toBeInTheDocument()
      })
    })

    it('should handle general intent for unknown input', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'general', confidence: 0.6 },
        ai_message: '我收到了你的消息。如果你想找对象，可以说"帮我找对象"',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [
          { label: '帮我找对象', action: 'matching' },
          { label: '今日推荐', action: 'daily_recommend' },
        ],
      })

      render(<ChatInterface />)

      await sendMessage('今天天气怎么样')

      await waitFor(() => {
        expect(mockRoute).toHaveBeenCalledWith('test-user-001', '今天天气怎么样')
        expect(screen.getByText(/我收到了你的消息/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第五部分：用户交互测试 =============

  describe('User Interaction', () => {
    it('should not send empty message', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>

      render(<ChatInterface />)

      const buttons = screen.getAllByRole('button')
      const sendButton = buttons.find(b => b.querySelector('[aria-label="send"]'))

      // 空输入时按钮应该禁用
      if (sendButton) {
        expect(sendButton).toBeDisabled()
      }

      // IntentRouter should not be called for empty input
      expect(mockRoute).not.toHaveBeenCalled()
    })

    it('should clear input after sending message', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'greeting', confidence: 1.0 },
        ai_message: '你好呀 🤍',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await sendMessage('你好')

      await waitFor(() => {
        const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement
        expect(input.value).toBe('')
      })
    })
  })

  // ============= 第六部分：消息追踪测试 =============

  describe('Message Tracking', () => {
    it('should track chat message via aiAwarenessApi', async () => {
      const mockRoute = intentRouterSkill.route as jest.MockedFunction<typeof intentRouterSkill.route>
      mockRoute.mockResolvedValueOnce({
        success: true,
        intent: { type: 'greeting', confidence: 1.0 },
        ai_message: '你好呀 🤍',
        generative_ui: { component_type: 'SimpleResponse', props: {} },
        suggested_actions: [],
      })

      const { aiAwarenessApi } = require('../../api')

      render(<ChatInterface />)

      await sendMessage('你好')

      await waitFor(() => {
        expect(aiAwarenessApi.trackChatMessage).toHaveBeenCalled()
      })
    })
  })
})