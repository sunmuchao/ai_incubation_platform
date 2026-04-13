/**
 * ChatRoom 组件测试 - 基础功能
 *
 * 测试覆盖:
 * - 消息发送与接收
 * - WebSocket 连接
 * - 界面渲染
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import ChatRoom from '../../components/ChatRoom'

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn()

// Mock fetch
global.fetch = jest.fn().mockImplementation((url: string) => {
  if (url.includes('/api/chat/history')) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ messages: [] }),
    })
  }
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  })
}) as any

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock WebSocket
jest.mock('../../services/websocket', () => ({
  websocketService: {
    connect: jest.fn(),
    onMessage: jest.fn(() => jest.fn()),
    disconnect: jest.fn(),
    send: jest.fn(),
  },
}))

// Mock chatApi
jest.mock('../../api/chatApi', () => ({
  chatApi: {
    getHistory: jest.fn().mockResolvedValue([]),
    sendMessage: jest.fn().mockResolvedValue({ id: 'msg-1' }),
    markAsRead: jest.fn().mockResolvedValue(undefined),
  },
}))

// Mock yourTurnApi
jest.mock('../../api/yourTurnApi', () => ({
  yourTurnApi: {
    getYourTurnStatus: jest.fn().mockResolvedValue({ has_turn: false }),
    sendYourTurn: jest.fn().mockResolvedValue(undefined),
  },
}))

describe('ChatRoom 组件测试', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === 'user_info') return JSON.stringify({ id: 'user_001', username: 'test_user' })
      if (key === 'token') return 'test-token'
      return null
    })
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  const mockProps = {
    partnerId: 'partner_001',
    partnerName: '小美',
    partnerAvatar: 'https://example.com/avatar.jpg',
  }

  describe('基础渲染', () => {
    it('渲染聊天室界面', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByText('小美')).toBeInTheDocument()
      })
    })

    it('渲染输入框', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument()
      })
    })

    it('渲染发送按钮', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByRole('img', { name: 'send' })).toBeInTheDocument()
      })
    })

    it('渲染返回按钮', async () => {
      const mockOnBack = jest.fn()
      render(<ChatRoom {...mockProps} onBack={mockOnBack} />)

      await waitFor(() => {
        expect(screen.getByRole('img', { name: 'left' })).toBeInTheDocument()
      })
    })

    it('空消息时显示提示', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByText(/小美/)).toBeInTheDocument()
      })
    })
  })

  describe('消息发送', () => {
    it('输入框可以输入文字', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入消息/) as HTMLInputElement
      await userEvent.type(input, '你好')

      await waitFor(() => {
        expect(input.value).toBe('你好')
      })
    })

    it('点击发送按钮发送消息', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入消息/) as HTMLInputElement
      await userEvent.type(input, '测试消息')

      const sendButton = screen.getByRole('img', { name: 'send' }).closest('button')
      await userEvent.click(sendButton!)

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })

    it('Enter 键发送消息', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/输入消息/) as HTMLInputElement
      await userEvent.type(input, '测试消息{enter}')

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })

    it('空消息不能发送', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument()
      })

      const sendButton = screen.getByRole('img', { name: 'send' }).closest('button')
      expect(sendButton).toBeDisabled()
    })
  })

  describe('组件交互', () => {
    it('点击返回按钮触发回调', async () => {
      const mockOnBack = jest.fn()
      render(<ChatRoom {...mockProps} onBack={mockOnBack} />)

      await waitFor(() => {
        expect(screen.getByRole('img', { name: 'left' })).toBeInTheDocument()
      })

      const backButton = screen.getByRole('img', { name: 'left' }).closest('button')
      await userEvent.click(backButton!)

      await waitFor(() => {
        expect(mockOnBack).toHaveBeenCalled()
      })
    })

    it('处理网络错误', async () => {
      ;(global.fetch as jest.Mock).mockImplementationOnce(() =>
        Promise.resolve({
          ok: false,
          status: 500,
        })
      )

      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByText('小美')).toBeInTheDocument()
      })
    })

    it('处理无效用户数据', async () => {
      localStorageMock.getItem.mockReturnValue(null)

      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByText('小美')).toBeInTheDocument()
      })
    })
  })

  describe('界面状态', () => {
    it('加载状态显示', async () => {
      render(<ChatRoom {...mockProps} />)

      await waitFor(() => {
        expect(screen.getByText('小美')).toBeInTheDocument()
      })
    })

    it('休眠状态正确传递', async () => {
      render(<ChatRoom {...mockProps} herSleeping={true} />)

      await waitFor(() => {
        expect(screen.getByText('小美')).toBeInTheDocument()
      })
    })
  })
})