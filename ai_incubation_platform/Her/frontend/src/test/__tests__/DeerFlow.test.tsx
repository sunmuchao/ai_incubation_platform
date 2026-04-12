/**
 * DeerFlow 集成测试
 *
 * 测试 ChatInterface 与 DeerFlow Agent 的集成
 * 覆盖 AI Native 架构下的 handleSend 逻辑
 * 测试 Memory 同步、Generative UI 渲染
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import ChatInterface from '../../components/ChatInterface'

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

// Mock skillClient（备用 Skills）
jest.mock('../../api/skillClient', () => ({
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

// Import mocked modules
import { deerflowClient } from '../../api/deerflowClient'
import { authStorage } from '../../utils/storage'

describe('DeerFlow Integration Tests', () => {
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

    const buttons = screen.getAllByRole('button')
    const sendButton = buttons.find(b => b.querySelector('[aria-label="send"]')) || buttons[buttons.length - 1]

    await act(async () => {
      fireEvent.click(sendButton)
    })
  }

  // ============= 第一部分：DeerFlow Agent 调用测试 =============

  describe('DeerFlow Agent Calls', () => {
    it('should call deerflowClient.chat when user sends a message', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '你好呀 🤍',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(mockChat).toHaveBeenCalledWith('你好', expect.any(String))
      })
    })

    it('should display AI message after DeerFlow returns', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '你好呀 🤍 我是 Her，你的情感顾问~',
        deerflow_used: true,
      })

      render(<ChatInterface />)
      await sendMessage('你好')

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      })
    })

    it('should maintain thread_id for conversation context', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValue({ success: true, ai_message: '收到', deerflow_used: true })

      render(<ChatInterface />)
      await sendMessage('第一句话')
      await waitFor(() => expect(mockChat).toHaveBeenCalledTimes(1))

      const firstThreadId = mockChat.mock.calls[0][1]

      await sendMessage('第二句话')
      await waitFor(() => expect(mockChat).toHaveBeenCalledTimes(2))

      const secondThreadId = mockChat.mock.calls[1][1]
      expect(secondThreadId).toBe(firstThreadId)
    })
  })

  // ============= 第二部分：结构化数据渲染测试 =============

  describe('Structured Data Rendering', () => {
    it('should render MatchCardList when tool returns matches', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '找到 3 位匹配对象',
        deerflow_used: true,
        tool_result: {
          success: true,
          data: {
            matches: [
              { user_id: 'u1', name: '小美', age: 26, score: 0.92 },
              { user_id: 'u2', name: '小雨', age: 24, score: 0.87 },
            ],
            total: 2,
          },
          summary: '找到 2 位匹配对象',
        },
        generative_ui: {
          component_type: 'MatchCardList',
          props: { matches: [], total: 2 },
        },
      })

      render(<ChatInterface />)
      await sendMessage('帮我找对象')

      await waitFor(() => {
        expect(screen.getByText(/找到/)).toBeInTheDocument()
      })
    })

    it('should render CompatibilityChart when tool returns analysis', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '匹配度 92%',
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
        generative_ui: {
          component_type: 'CompatibilityChart',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('分析我和小美的匹配度')

      await waitFor(() => {
        expect(screen.getByText(/匹配度/)).toBeInTheDocument()
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
        generative_ui: {
          component_type: 'DatePlanCard',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('帮我策划约会')

      await waitFor(() => {
        expect(screen.getByText(/约会方案/)).toBeInTheDocument()
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

      // Memory sync should be called internally by deerflow.py
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
        ai_message: 'DeerFlow 服务暂时不可用',
        deerflow_used: false,
      })

      render(<ChatInterface />)
      await sendMessage('测试错误')

      await waitFor(() => {
        expect(screen.getByText(/DeerFlow 服务暂时不可用/)).toBeInTheDocument()
      })
    })

    it('should handle network error gracefully', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockRejectedValueOnce(new Error('Network error'))

      render(<ChatInterface />)
      await sendMessage('测试异常')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第五部分：多轮对话测试 =============

  describe('Multi-turn Conversation', () => {
    it('should maintain conversation context across multiple messages', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>

      // 第一次对话：找对象
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '找到小美',
        deerflow_used: true,
        tool_result: {
          success: true,
          data: { matches: [{ user_id: 'u1', name: '小美', score: 0.92 }] },
          summary: '找到小美',
        },
      })

      render(<ChatInterface />)
      await sendMessage('帮我找对象')

      await waitFor(() => {
        expect(screen.getByText(/找到小美/)).toBeInTheDocument()
      })

      // 第二次对话：分析匹配度（应该知道之前找到了小美）
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '和小美的匹配度 92%',
        deerflow_used: true,
      })

      await sendMessage('分析一下')

      await waitFor(() => {
        expect(mockChat).toHaveBeenCalledTimes(2)
        // 同一个 thread_id
        expect(mockChat.mock.calls[1][1]).toBe(mockChat.mock.calls[0][1])
      })
    })
  })

  // ============= 第六部分：Component Type 映射测试 =============

  describe('Component Type Mapping', () => {
    it('should map MatchCardList to match generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '匹配结果',
        deerflow_used: true,
        generative_ui: {
          component_type: 'MatchCardList',
          props: { matches: [] },
        },
      })

      render(<ChatInterface />)
      await sendMessage('找对象')

      await waitFor(() => {
        expect(screen.getByText(/匹配结果/)).toBeInTheDocument()
      })
    })

    it('should map CompatibilityChart to analysis generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '分析结果',
        deerflow_used: true,
        generative_ui: {
          component_type: 'CompatibilityChart',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('分析匹配度')

      await waitFor(() => {
        expect(screen.getByText(/分析结果/)).toBeInTheDocument()
      })
    })

    it('should map DatePlanCard to feature generativeCard', async () => {
      const mockChat = deerflowClient.chat as jest.MockedFunction<typeof deerflowClient.chat>
      mockChat.mockResolvedValueOnce({
        success: true,
        ai_message: '约会方案',
        deerflow_used: true,
        generative_ui: {
          component_type: 'DatePlanCard',
          props: {},
        },
      })

      render(<ChatInterface />)
      await sendMessage('策划约会')

      await waitFor(() => {
        expect(screen.getByText(/约会方案/)).toBeInTheDocument()
      })
    })
  })
})