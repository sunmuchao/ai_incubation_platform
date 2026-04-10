/**
 * 注册对话页面组件测试
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import RegistrationConversationPage from '../../pages/RegistrationConversationPage'
import { registrationConversationApi, userApi } from '../../api'

// Mock API 调用
jest.mock('../../api', () => ({
  registrationConversationApi: {
    startConversation: jest.fn(),
    sendMessage: jest.fn(),
    getSession: jest.fn(),
    completeConversation: jest.fn(),
  },
  userApi: {
    getCurrentUser: jest.fn(),
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

// Mock Ant Design 组件
jest.mock('antd', () => {
  const actualAntd = jest.requireActual('antd')
  return {
    ...actualAntd,
    Spin: ({ tip }: { tip?: string }) => <div data-testid="spinner">{tip}</div>,
    Alert: ({ message }: { message?: string }) => <div data-testid="alert">{message}</div>,
  }
})

describe('RegistrationConversationPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
    mockLocalStorage.setItem.mockClear()
  })

  describe('初始化加载', () => {
    it('显示加载状态', () => {
      ;(userApi.getCurrentUser as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // 永远不 resolve，保持加载状态
      )

      render(<RegistrationConversationPage />)

      expect(screen.getByTestId('spinner')).toBeInTheDocument()
      expect(screen.getByText('正在准备对话...')).toBeInTheDocument()
    })

    it('成功获取用户信息后开始对话', async () => {
      const mockUser = { id: 'user-123', name: '张三', username: 'zhangsan' }
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，张三～ 我是你的 AI 红娘助手🌸',
        current_stage: 'welcome',
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/你好，张三/)).toBeInTheDocument()
      })

      expect(userApi.getCurrentUser).toHaveBeenCalled()
      expect(registrationConversationApi.startConversation).toHaveBeenCalledWith(
        'user-123',
        '张三'
      )
    })

    it('从 localStorage 获取用户信息当 API 失败', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockRejectedValue(new Error('API Error'))
      mockLocalStorage.getItem.mockImplementation((key: string) => {
        if (key === 'user_info') {
          return JSON.stringify({ id: 'local-user', name: '李四' })
        }
        return null
      })
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好，李四～',
        current_stage: 'welcome',
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/你好，李四/)).toBeInTheDocument()
      })
    })

    it('API 失败且无 localStorage 时显示欢迎界面', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockRejectedValue(new Error('API Error'))
      mockLocalStorage.getItem.mockReturnValue(null)

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByTestId('spinner')).not.toBeInTheDocument()
      })
    })
  })

  describe('对话界面', () => {
    const mockUser = { id: 'user-123', name: '测试用户' }
    const mockStartResponse = {
      ai_message: '很高兴认识你，测试用户～ 我想先了解一下，你希望通过这个平台找到什么样的关系呢？',
      current_stage: 'relationship_goal',
    }

    beforeEach(async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue(mockStartResponse)
    })

    it('显示 AI 消息', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText(/很高兴认识你/)).toBeInTheDocument()
      })
    })

    it('显示进度条', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText('对话进度')).toBeInTheDocument()
      })
    })

    it('显示阶段指示器', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText('欢迎破冰')).toBeInTheDocument()
        expect(screen.getByText('关系期望')).toBeInTheDocument()
      })
    })

    it('显示跳过按钮', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText('跳过')).toBeInTheDocument()
      })
    })

    it('可以输入消息', async () => {
      render(<RegistrationConversationPage />)

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        fireEvent.change(textarea, { target: { value: '我想找认真恋爱的对象' } })
        expect(textarea).toHaveValue('我想找认真恋爱的对象')
      })
    })

    it('点击发送按钮发送消息', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '我懂你～ 认真的感情最让人安心 💕',
        current_stage: 'ideal_partner',
        is_completed: false,
        collected_data_summary: { goal: 'serious' },
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '我想找认真恋爱的对象' } })
        fireEvent.click(sendButton)
      })

      expect(registrationConversationApi.sendMessage).toHaveBeenCalledWith(
        'user-123',
        '我想找认真恋爱的对象'
      )
    })

    it('按 Enter 键发送消息', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '好的～',
        current_stage: 'ideal_partner',
        is_completed: false,
      })

      render(<RegistrationConversationPage />)

      await waitFor(async () => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        fireEvent.change(textarea, { target: { value: '测试消息' } })
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })
      })

      expect(registrationConversationApi.sendMessage).toHaveBeenCalledWith(
        'user-123',
        '测试消息'
      )
    })

    it('Shift+Enter 换行而不发送', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '好的～',
        current_stage: 'ideal_partner',
        is_completed: false,
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        fireEvent.change(textarea, { target: { value: '第一行' } })
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true })
        expect(textarea).toHaveValue('第一行')
        expect(registrationConversationApi.sendMessage).not.toHaveBeenCalled()
      })
    })

    it('发送消息后显示 AI 回复', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '明白了～ 那你能描述一下你理想中的另一半是什么样的吗？',
        current_stage: 'ideal_partner',
        is_completed: false,
      })

      render(<RegistrationConversationPage />)

      await waitFor(async () => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '认真恋爱' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/明白了/)).toBeInTheDocument()
        expect(screen.getByText(/理想中的另一半/)).toBeInTheDocument()
      })
    })

    it('发送消息时显示 loading 状态', async () => {
      ;(registrationConversationApi.sendMessage as jest.Mock).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          ai_message: '好的～',
          current_stage: 'ideal_partner',
          is_completed: false,
        }), 100))
      )

      render(<RegistrationConversationPage />)

      await waitFor(async () => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '测试' } })
        fireEvent.click(sendButton)
      })

      expect(screen.getByText('AI 思考中...')).toBeInTheDocument()
    })
  })

  describe('对话完成', () => {
    const mockUser = { id: 'user-123', name: '完成用户' }

    it('对话完成后显示摘要', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'welcome',
      })
      ;(registrationConversationApi.sendMessage as jest.Mock)
        .mockResolvedValueOnce({
          ai_message: '好的',
          current_stage: 'relationship_goal',
          is_completed: false,
          collected_data_summary: { goal: 'serious' },
        })
        .mockResolvedValueOnce({
          ai_message: '明白了',
          current_stage: 'ideal_partner',
          is_completed: false,
          collected_data_summary: { goal: 'serious', has_values: false },
        })
        .mockResolvedValueOnce({
          ai_message: '很好',
          current_stage: 'values',
          is_completed: false,
          collected_data_summary: { goal: 'serious', has_values: true },
        })
        .mockResolvedValueOnce({
          ai_message: '不错',
          current_stage: 'lifestyle',
          is_completed: false,
          collected_data_summary: { goal: 'serious', has_ideal_partner: true },
        })
        .mockResolvedValueOnce({
          ai_message: '太好了～ 我已经对你有了初步的了解',
          current_stage: 'final',
          is_completed: true,
          collected_data_summary: { goal: 'serious', has_values: true, has_ideal_partner: true },
        })

      render(<RegistrationConversationPage />)

      // 发送所有阶段的消息
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '认真恋爱' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '温柔' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '家庭' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '旅行' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '好的' } })
        fireEvent.click(sendButton)
      })

      // 验证完成界面
      await waitFor(() => {
        expect(screen.getByText('对话完成 🎉')).toBeInTheDocument()
        expect(screen.getByText('开始探索')).toBeInTheDocument()
        expect(screen.getByText('稍后再说')).toBeInTheDocument()
      })
    })

    it('点击开始探索调用 onComplete', async () => {
      const onCompleteMock = jest.fn()
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'final',
      })

      render(<RegistrationConversationPage onComplete={onCompleteMock} />)

      await waitFor(() => {
        expect(screen.getByText('对话完成 🎉')).toBeInTheDocument()
      })

      const exploreButton = screen.getByText('开始探索')
      fireEvent.click(exploreButton)

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'has_completed_registration_conversation',
        'true'
      )
      expect(onCompleteMock).toHaveBeenCalled()
    })

    it('点击稍后再说调用 onComplete', async () => {
      const onCompleteMock = jest.fn()
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'final',
      })

      render(<RegistrationConversationPage onComplete={onCompleteMock} />)

      await waitFor(() => {
        expect(screen.getByText('对话完成 🎉')).toBeInTheDocument()
      })

      const skipButton = screen.getByText('稍后再说')
      fireEvent.click(skipButton)

      expect(onCompleteMock).toHaveBeenCalled()
    })
  })

  describe('跳过功能', () => {
    const mockUser = { id: 'user-123', name: '跳过用户' }

    it('点击跳过按钮结束对话', async () => {
      const onCompleteMock = jest.fn()
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'welcome',
      })
      ;(registrationConversationApi.completeConversation as jest.Mock).mockResolvedValue({
        success: true,
      })

      render(<RegistrationConversationPage onComplete={onCompleteMock} />)

      await waitFor(() => {
        expect(screen.getByText('跳过')).toBeInTheDocument()
      })

      const skipButton = screen.getByText('跳过')
      fireEvent.click(skipButton)

      expect(registrationConversationApi.completeConversation).toHaveBeenCalledWith('user-123')
      expect(onCompleteMock).toHaveBeenCalled()
    })
  })

  describe('错误处理', () => {
    const mockUser = { id: 'user-123', name: '错误用户' }

    it('发送消息失败时显示错误消息', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'welcome',
      })
      ;(registrationConversationApi.sendMessage as jest.Mock).mockRejectedValue(
        new Error('网络错误')
      )

      render(<RegistrationConversationPage />)

      await waitFor(async () => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '测试' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })

    it('完成对话失败时不崩溃', async () => {
      const onCompleteMock = jest.fn()
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'final',
      })
      ;(registrationConversationApi.completeConversation as jest.Mock).mockRejectedValue(
        new Error('完成失败')
      )

      render(<RegistrationConversationPage onComplete={onCompleteMock} />)

      await waitFor(() => {
        expect(screen.getByText('对话完成 🎉')).toBeInTheDocument()
      })

      const exploreButton = screen.getByText('开始探索')
      fireEvent.click(exploreButton)

      // 不应该调用 onComplete
      expect(onCompleteMock).not.toHaveBeenCalled()
    })
  })

  describe('辅助功能', () => {
    const mockUser = { id: 'user-123', name: '辅助用户' }

    it('显示提示信息', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '欢迎',
        current_stage: 'welcome',
      })

      render(<RegistrationConversationPage />)

      await waitFor(() => {
        expect(screen.getByText('真诚回答有助于找到更匹配的对象哦～')).toBeInTheDocument()
      })
    })

    it('消息历史正确显示用户和 AI 消息', async () => {
      ;(userApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser)
      ;(registrationConversationApi.startConversation as jest.Mock).mockResolvedValue({
        ai_message: '你好',
        current_stage: 'relationship_goal',
      })
      ;(registrationConversationApi.sendMessage as jest.Mock).mockResolvedValue({
        ai_message: '好的',
        current_stage: 'ideal_partner',
        is_completed: false,
      })

      render(<RegistrationConversationPage />)

      await waitFor(async () => {
        const textarea = screen.getByPlaceholderText('输入你的回答...')
        const sendButton = screen.getByText('发送')
        fireEvent.change(textarea, { target: { value: '用户消息' } })
        fireEvent.click(sendButton)
      })

      await waitFor(() => {
        expect(screen.getByText('你好')).toBeInTheDocument()
        expect(screen.getByText('用户消息')).toBeInTheDocument()
        expect(screen.getByText('好的')).toBeInTheDocument()
      })
    })
  })
})
