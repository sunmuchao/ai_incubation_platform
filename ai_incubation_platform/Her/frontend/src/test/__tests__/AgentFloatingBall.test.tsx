/**
 * AI 红娘悬浮球组件测试
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

jest.mock('../../api/deerflowClient', () => ({
  deerflowClient: {
    chat: jest.fn().mockResolvedValue({
      success: true,
      ai_message: '测试回复',
    }),
  },
}))

jest.mock('../../utils/storage', () => ({
  authStorage: {
    getUser: jest.fn().mockReturnValue({
      id: 'test-user',
      name: '测试用户',
      age: 25,
      gender: 'male',
      location: '北京',
    }),
    getUserId: jest.fn().mockReturnValue('test-user'),
    getToken: jest.fn().mockReturnValue('token'),
  },
}))

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

// Mock requestAnimationFrame
window.requestAnimationFrame = (cb: any) => setTimeout(cb, 0)

// Mock Ant Design Avatar
jest.mock('antd', () => {
  const actualAntd = jest.requireActual('antd')
  return {
    ...actualAntd,
    Avatar: ({ src, size, className, style, onClick }: any) => (
      <div
        data-testid="avatar"
        data-src={src}
        data-size={size}
        className={className}
        style={style}
        onClick={onClick}
      >
        Avatar
      </div>
    ),
    Button: ({ icon, onClick, className }: any) => (
      <button
        data-testid="button"
        className={className}
        onClick={onClick}
      >
        {icon}
      </button>
    ),
    Typography: {
      Text: ({ children, strong, type, className }: any) => (
        <span
          data-testid="text"
          data-strong={strong}
          data-type={type}
          className={className}
        >
          {children}
        </span>
      ),
    },
  }
})

// 从组件导入常量
const BALL_SIZE = 56
const PADDING = 16

/** 组件用 mousedown + window mouseup 切换展开，单纯 click(avatar) 不会挂上 window 监听 */
function expandFloatingBallPanel() {
  const root = document.querySelector('.agent-floating-ball') as HTMLElement
  expect(root).toBeTruthy()
  fireEvent.mouseDown(root, { clientX: 100, clientY: 100, bubbles: true })
  fireEvent.mouseUp(window, { clientX: 100, clientY: 100, bubbles: true })
}

describe('AgentFloatingBall Component', () => {
  const defaultProps = {
    visible: true,
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
      expect(screen.getByTestId('avatar')).toBeInTheDocument()
    })
  })

  describe('消息状态测试', () => {
    it('显示在线状态', async () => {
      render(<AgentFloatingBall {...defaultProps} hasNewMessage={false} />)

      expandFloatingBallPanel()

      await waitFor(() => {
        expect(screen.getByText('在线')).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('显示新消息状态', async () => {
      render(<AgentFloatingBall {...defaultProps} hasNewMessage={true} />)

      expandFloatingBallPanel()

      await waitFor(() => {
        expect(screen.getByText('有新消息')).toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('展开/收起测试', () => {
    it('点击悬浮球展开面板', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      expandFloatingBallPanel()

      // 等待面板展开
      await waitFor(() => {
        expect(screen.getByText('Her')).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('点击关闭按钮收起面板', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      expandFloatingBallPanel()

      await waitFor(() => {
        expect(screen.getByText('Her')).toBeInTheDocument()
      }, { timeout: 1000 })

      // 关闭 - 查找关闭按钮
      const closeButtons = screen.getAllByTestId('button')
      const closeButton = closeButtons.find(btn => btn.className.includes('close-btn'))

      if (closeButton) {
        fireEvent.click(closeButton)
      }

      // 面板应该收起
      await waitFor(() => {
        expect(screen.queryByText('在线')).not.toBeInTheDocument()
      }, { timeout: 1000 })
    })
  })

  describe('位置测试', () => {
    it('初始位置在屏幕右侧', () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const avatar = screen.getByTestId('avatar')
      const ball = avatar.closest('.agent-floating-ball') as HTMLDivElement
      expect(ball).toBeInTheDocument()
      // 初始 x 位置应该是 screen width - BALL_SIZE - PADDING = 1920 - 56 - 16 = 1848
      const expectedX = 1920 - BALL_SIZE - PADDING
      expect(ball.style.left).toBe(`${expectedX}px`)
    })
  })

  describe('样式类测试', () => {
    it('悬浮球容器应该存在', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const avatar = screen.getByTestId('avatar')
      const ball = avatar.closest('.agent-floating-ball')

      // 初始状态容器存在
      expect(ball).toBeInTheDocument()
    })

    it('has-message 类应该根据 hasNewMessage 添加', () => {
      render(<AgentFloatingBall {...defaultProps} hasNewMessage={true} />)

      const avatar = screen.getByTestId('avatar')
      const ball = avatar.closest('.agent-floating-ball')
      expect(ball?.className).toContain('has-message')
    })
  })

  describe('无障碍测试', () => {
    it('悬浮球应该可点击', () => {
      render(<AgentFloatingBall {...defaultProps} />)

      const avatar = screen.getByTestId('avatar')
      expect(avatar).toBeInTheDocument()
    })

    it('按钮应该可访问', async () => {
      render(<AgentFloatingBall {...defaultProps} />)

      expandFloatingBallPanel()

      await waitFor(() => {
        const buttons = screen.getAllByTestId('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 1000 })
    })
  })
})
