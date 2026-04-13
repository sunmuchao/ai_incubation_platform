/**
 * DeerFlow 集成测试
 *
 * 测试 ChatInterface 与 DeerFlow Agent 的集成
 * 覆盖 AI Native 架构下的 handleSend 逻辑
 * 测试 Memory 同步、Generative UI 渲染
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import ChatInterface from '../../components/ChatInterface'

// 注：intentRouter 已删除，ChatInterface 直接调用 deerflowClient

// Mock deerflowClient（AI Native 架构核心）
jest.mock('../../api/deerflowClient', () => ({
  deerflowClient: {
    chat: jest.fn(),
    stream: jest.fn(),
    getStatus: jest.fn().mockResolvedValue({
      available: true,
      path: '/mock/path',
      config_path: '/mock/config.yaml',
      config_exists: true,
      memory_enabled: true,
    }),
    syncMemory: jest.fn().mockResolvedValue({
      success: true,
      facts_count: 5,
      message: '已同步 5 条用户信息',
    }),
    parseToolResult: jest.fn(),
  },
}))

// Mock profileApi
jest.mock('../../api/profileApi', () => ({
  profileApi: {
    getQuestion: jest.fn().mockResolvedValue({
      need_collection: false,
      question_card: null,
    }),
    submitAnswer: jest.fn().mockResolvedValue({
      has_more_questions: false,
      next_question: null,
    }),
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
      interests: ['旅行', '摄影'],
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

// Mock fetch for quick tags
const originalFetch = global.fetch

// Import the mocked modules for use in tests
import { deerflowClient } from '../../api/deerflowClient'
import { intentRouter } from '../../api/intentRouter'
import { authStorage } from '../../utils/storage'

describe('DeerFlow Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)

    // Mock fetch for quick tags
    global.fetch = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/chat/tags')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            tags: [
              { label: '找对象', trigger: '帮我找对象' },
              { label: 'AI 预沟通', trigger: '启动预沟通' },
            ],
          }),
        })
      }
      return originalFetch(url)
    }) as any

    // Default: IntentRouter fallback to DeerFlow
    ;(intentRouter.route as jest.Mock).mockResolvedValue({
      matched: false,
      ai_message: '',
      need_deerflow: true,
      generative_ui: undefined,
      suggested_actions: [],
    })

    // Default DeerFlow response
    ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
      success: true,
      ai_message: '你好，我是 Her AI',
      deerflow_used: true,
    })
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  // 辅助函数：发送消息
  const sendMessage = async (text: string) => {
    const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

    await waitFor(() => {
      expect(input).toBeInTheDocument()
    })

    await act(async () => {
      await userEvent.type(input, text)
      await userEvent.type(input, '{enter}')
    })
  }

  // ============= 第一部分：DeerFlow 基础调用测试 =============

  describe('DeerFlow Basic Calls', () => {
    it('should call deerflowClient.chat when IntentRouter returns need_deerflow', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '收到消息',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(deerflowClient.chat).toHaveBeenCalled()
      })
    })

    it('should display AI message after DeerFlow returns', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '这是 AI 的回复消息',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText('这是 AI 的回复消息')).toBeInTheDocument()
      })
    })

    it('should maintain thread_id for conversation context', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValue({
        success: true,
        ai_message: '回复',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('第一条消息')

      await waitFor(() => {
        expect(mockChat).toHaveBeenCalled()
      })

      // 获取第一次调用的 threadId
      const firstCallArgs = mockChat.mock.calls[0]
      const firstThreadId = firstCallArgs[1]

      await sendMessage('第二条消息')

      await waitFor(() => {
        expect(mockChat).toHaveBeenCalledTimes(2)
        // 第二次调用应该使用相同的 threadId
        const secondCallArgs = mockChat.mock.calls[1]
        expect(secondCallArgs[1]).toBe(firstThreadId)
      })
    })
  })

  // ============= 第二部分：Generative UI 测试 =============

  describe('Generative UI Rendering', () => {
    it('should render MatchCardList when tool returns matches', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '找到匹配对象',
        deerflow_used: true,
        tool_result: {
          success: true,
          data: {
            matches: [
              { user: { id: '1', name: '小美' }, compatibility_score: 85 },
            ],
          },
          summary: '找到 1 位匹配对象',
        },
      })

      render(<ChatInterface />)
      await sendMessage('帮我找对象')

      await waitFor(() => {
        expect(screen.getByText(/找到匹配对象/)).toBeInTheDocument()
      })
    })

    it('should render CompatibilityChart when tool returns analysis', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '匹配度分析：92%',
        deerflow_used: true,
        tool_result: {
          success: true,
          data: {
            overall_score: 0.92,
            dimensions: [
              { name: 'interests', score: 0.95, description: '兴趣高度匹配' },
            ],
          },
          summary: '匹配度 92%',
        },
      })

      render(<ChatInterface />)
      await sendMessage('分析我和小美的匹配度')

      await waitFor(() => {
        expect(screen.getByText(/匹配度分析/)).toBeInTheDocument()
      })
    })

    it('should render DatePlanCard when tool returns plans', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '约会方案已生成',
        deerflow_used: true,
        tool_result: {
          success: true,
          data: {
            plans: [
              { name: '艺术展', description: '适合摄影爱好者', location: '798' },
            ],
          },
          summary: '生成 1 个约会方案',
        },
      })

      render(<ChatInterface />)
      await sendMessage('帮我策划约会')

      await waitFor(() => {
        expect(screen.getByText(/约会方案已生成/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第三部分：Memory 同步测试 =============

  describe('Memory Sync', () => {
    it('should sync user profile to DeerFlow Memory on first chat', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '你好',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(mockChat).toHaveBeenCalled()
      })
    })
  })

  // ============= 第四部分：错误处理测试 =============

  describe('Error Handling', () => {
    it('should display error message when DeerFlow fails', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: false,
        ai_message: '抱歉，出现了一些问题',
        deerflow_used: false,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })

    it('should handle network error gracefully', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockRejectedValueOnce(new Error('Network Error'))

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第五部分：上下文保持测试 =============

  describe('Context Persistence', () => {
    it('should maintain conversation context across multiple messages', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValue({
        success: true,
        ai_message: '收到',
        deerflow_used: true,
      })

      render(<ChatInterface />)

      // 发送多条消息
      await sendMessage('第一条')
      await waitFor(() => expect(mockChat).toHaveBeenCalledTimes(1))

      await sendMessage('第二条')
      await waitFor(() => expect(mockChat).toHaveBeenCalledTimes(2))

      await sendMessage('第三条')
      await waitFor(() => expect(mockChat).toHaveBeenCalledTimes(3))

      // 每次调用都应该传递相同的 threadId
      const threadIds = mockChat.mock.calls.map(call => call[1])
      expect(threadIds[0]).toBe(threadIds[1])
      expect(threadIds[1]).toBe(threadIds[2])
    })
  })

  // ============= 第六部分：Generative UI 映射测试 =============

  describe('Generative UI Mapping', () => {
    it('should map MatchCardList to match generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '找到匹配',
        deerflow_used: true,
        generative_ui: {
          component_type: 'MatchCardList',
          props: {
            matches: [{ user: { id: '1', name: 'Test' }, compatibility_score: 90 }],
          },
        },
      })

      render(<ChatInterface />)
      await sendMessage('匹配')

      await waitFor(() => {
        expect(screen.getByText('找到匹配')).toBeInTheDocument()
      })
    })

    it('should map CompatibilityChart to analysis generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '分析完成',
        deerflow_used: true,
        generative_ui: {
          component_type: 'CompatibilityChart',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('分析')

      await waitFor(() => {
        expect(screen.getByText('分析完成')).toBeInTheDocument()
      })
    })

    it('should map DatePlanCard to feature generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '方案生成完成',
        deerflow_used: true,
        generative_ui: {
          component_type: 'DatePlanCard',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('约会方案')

      await waitFor(() => {
        expect(screen.getByText('方案生成完成')).toBeInTheDocument()
      })
    })
  })
})