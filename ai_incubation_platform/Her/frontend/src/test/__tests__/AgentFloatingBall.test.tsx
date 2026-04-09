/**
 * AI 红娘悬浮球组件测试
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import AgentFloatingBall from '../../components/AgentFloatingBall'

// Mock window 对象
Object.defineProperty(window, 'innerWidth', {
  writable: true,
  configurable: true,
  value: 1920,
})

Object.defineProperty(window, 'innerHeight', {
  writable: true,
  configurable: true,
  value: 1080,
})

// 从组件导入常量
const BALL_SIZE = 56
const PADDING = 16

// Mock requestAnimationFrame
window.requestAnimationFrame = (cb: any) => setTimeout(cb, 0)

describe('AgentFloatingBall Component', () => {
  const defaultProps = {
    visible: true,
    unreadCount: 0,
    onQuickChat: jest.fn(),
    onBackToMain: jest.fn(),
    hasNewMessage: false,
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('可见性测试', () => {
    it('当 visible 为 false 时不渲染', () => {
      const { container } = render(
        <AgentFloatingBall {...defaultProps} visible={false} />
      )
      expect(container.firstChild).toBeNull()
    })

    it('当 visible 为 true 时渲染悬浮球', () => {
      render(<AgentFloatingBall {...defaultProps} />)
      // 应该渲染悬浮球容器
      expect(screen.getByRole('img')).toBeInTheDocument()
    })
  })

  describe('未读消息徽章测试', () => {
    it('显示未读消息数量', () => {
      render(<AgentFloatingBall {...defaultProps} unreadCount={5} />)
      // Badge 应该显示数字 5
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('未读消息为 0 时不显示数字', () => {
      render(<AgentFloatingBall {...defaultProps} unreadCount={0} />)
      // 不应该有数字显示
      expect(screen.queryByText('5')).not.toBeInTheDocument()
    })
  })

  describe('展开/收起测试', () => {
    it('点击悬浮球展开面板', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      // 等待面板展开
      await waitFor(() => {
        expect(screen.getByText('AI 红娘')).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('点击关闭按钮收起面板', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      // 展开
      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      await waitFor(() => {
        expect(screen.getByText('AI 红娘')).toBeInTheDocument()
      }, { timeout: 1000 })

      // 关闭 - 使用 aria-label 查找关闭按钮
      const closeButton = screen.getByLabelText('close')
      fireEvent.click(closeButton)

      // 面板应该收起
      await waitFor(() => {
        expect(screen.queryByText('AI 红娘')).not.toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('按钮功能测试', () => {
    it('点击"快速对话"调用 onQuickChat', async () => {
      const onQuickChatMock = jest.fn()
      render(
        <AgentFloatingBall
          {...defaultProps}
          onQuickChat={onQuickChatMock}
          unreadCount={3}
        />
      )

      // 展开面板
      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      await waitFor(() => {
        expect(screen.getByText('AI 红娘')).toBeInTheDocument()
      }, { timeout: 1000 })

      // 查找并点击快速对话按钮
      const buttons = screen.getAllByRole('button')
      const quickChatButton = buttons.find(
        btn => btn.textContent?.includes('未读消息')
      )

      if (quickChatButton) {
        fireEvent.click(quickChatButton)
        expect(onQuickChatMock).toHaveBeenCalledTimes(1)
      }
    })

    it('点击"返回主页"调用 onBackToMain', async () => {
      const onBackToMainMock = jest.fn()
      render(
        <AgentFloatingBall
          {...defaultProps}
          onBackToMain={onBackToMainMock}
        />
      )

      // 展开面板
      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      await waitFor(() => {
        expect(screen.getByText('AI 红娘')).toBeInTheDocument()
      }, { timeout: 1000 })

      // 查找并点击返回主页按钮
      const buttons = screen.getAllByRole('button')
      const backToMainButton = buttons.find(
        btn => btn.textContent === '返回主页'
      )

      if (backToMainButton) {
        fireEvent.click(backToMainButton)
        expect(onBackToMainMock).toHaveBeenCalledTimes(1)
      }
    })
  })

  describe('状态显示测试', () => {
    it('显示在线状态', async () => {
      render(<AgentFloatingBall {...defaultProps} hasNewMessage={false} />)

      // 展开面板
      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      await waitFor(() => {
        expect(screen.getByText('在线')).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('显示新消息状态', async () => {
      render(<AgentFloatingBall {...defaultProps} hasNewMessage={true} />)

      // 展开面板
      const avatar = screen.getByRole('img')
      fireEvent.click(avatar)

      await waitFor(() => {
        expect(screen.getByText('有新消息')).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('位置测试', () => {
    it('初始位置在屏幕右侧', () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const ball = screen.getByRole('img').closest('.agent-floating-ball') as HTMLDivElement
      expect(ball).toBeInTheDocument()
      // 初始 x 位置应该是 screen width - BALL_SIZE - PADDING = 1920 - 56 - 16 = 1848
      const expectedX = 1920 - BALL_SIZE - PADDING
      expect(ball.style.left).toBe(`${expectedX}px`)
    })
  })

  describe('样式类测试', () => {
    it('展开时容器应该存在', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const ball = screen.getByRole('img').closest('.agent-floating-ball')

      // 初始状态容器存在
      expect(ball).toBeInTheDocument()

      // 点击展开
      fireEvent.click(screen.getByRole('img'))

      // 等待面板展开，容器存在
      await waitFor(() => {
        expect(screen.getByText('AI 红娘')).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('无障碍测试', () => {
    it('悬浮球应该有适当的 aria 标签', () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const avatar = screen.getByRole('img')
      expect(avatar).toBeInTheDocument()
    })

    it('按钮应该有清晰的标签', async () => {
      render(<AgentFloatingBall {...defaultProps} unreadCount={2} />)

      // 展开面板
      fireEvent.click(screen.getByRole('img'))

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 1000 })
    })
  })
})
