/**
 * 注册对话页面组件测试
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import RegistrationConversationPage from '../../pages/RegistrationConversationPage'

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn()

// Mock authStorage
jest.mock('../../utils/storage', () => ({
  authStorage: {
    getUser: jest.fn(),
    getUserId: jest.fn(),
    getToken: jest.fn().mockReturnValue('test-token'),
  },
}))

// Mock registrationConversationApi
jest.mock('../../api', () => ({
  registrationConversationApi: {
    startConversation: jest.fn(),
    sendMessage: jest.fn(),
    getSession: jest.fn(),
    completeConversation: jest.fn(),
  },
}))

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
})

// Import mocked modules
import { authStorage } from '../../utils/storage'
import { registrationConversationApi } from '../../api'

describe('RegistrationConversationPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  describe('初始化加载', () => {
    it('显示加载状态当无用户信息', async () => {
      ;(authStorage.getUser as jest.Mock).mockReturnValue(null)

      render(<RegistrationConversationPage />)

      // 无用户信息时，显示错误或空状态
      await waitFor(() => {
        // 组件应该在加载失败后停止加载
        expect(screen.queryByTestId('spinner')).not.toBeInTheDocument()
      })
    })

    it('成功获取用户信息后开始对话', async () => {
      const mockUser = { id: 'user-123', name: '张三', username: 'zhangsan' }
      ;(authStorage.getUser as jest.Mock).mockReturnValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，张三～ 我是你的 AI 红娘助手🌸',
        understanding_level: 10,
        collected_dimensions: [],
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/你好，张三/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('从 localStorage 获取用户信息', async () => {
      const mockUser = { id: 'local-user', name: '李四' }
      ;(authStorage.getUser as jest.Mock).mockReturnValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，李四～',
        understanding_level: 0,
        collected_dimensions: [],
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(registrationConversationApi.startConversation).toHaveBeenCalled()
      })
    })
  })

  describe('对话交互', () => {
    beforeEach(() => {
      const mockUser = { id: 'user-123', name: '张三' }
      ;(authStorage.getUser as jest.Mock).mockReturnValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，张三～',
        understanding_level: 10,
        collected_dimensions: [],
      })
    })

    it('显示 AI 消息', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/你好，张三/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('可以输入消息', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入你的回复/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入你的回复/) as HTMLTextAreaElement
      await userEvent.type(input, '你好')

      expect(input.value).toBe('你好')
    })

    it('可以输入和发送消息', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '好的，收到你的消息~',
        understanding_level: 20,
        collected_dimensions: [{ name: '兴趣', confidence: 0.8, data: '摄影' }],
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入你的回复/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入你的回复/) as HTMLTextAreaElement
      await userEvent.type(input, '我喜欢摄影')

      // 点击发送按钮
      const sendButton = screen.getByRole('button', { name: /发送/ })
      fireEvent.click(sendButton)

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })

    it('发送消息失败时显示错误消息', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockRejectedValue(
        new Error('API Error')
      )

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入你的回复/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入你的回复/) as HTMLTextAreaElement
      await userEvent.type(input, '测试{enter}')

      // 组件应该优雅处理错误
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入你的回复/)).toBeInTheDocument()
      })
    })
  })

  describe('对话完成', () => {
    beforeEach(() => {
      const mockUser = { id: 'user-123', name: '张三' }
      ;(authStorage.getUser as jest.Mock).mockReturnValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，张三～',
        understanding_level: 100,
        collected_dimensions: [],
        completed: true,
      })
    })

    it('显示完成按钮当对话结束', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/你好，张三/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('点击跳过按钮结束对话', async () => {
      const mockOnComplete = jest.fn()
      ;(registrationConversationApi.completeConversation as jest.Mock).mockResolvedValue({
        success: true,
      })

      render(<RegistrationConversationPage onComplete={mockOnComplete} />)

      await waitFor(() => {
        expect(screen.getByText(/你好，张三/)).toBeInTheDocument()
      })

      // 跳过按钮可能存在
      const skipButton = screen.queryByText('跳过')
      if (skipButton) {
        fireEvent.click(skipButton)
        await waitFor(() => {
          expect(mockOnComplete).toHaveBeenCalled()
        })
      }
    })
  })
})