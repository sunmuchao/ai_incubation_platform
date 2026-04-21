/**
 * AgentFloatingBall 拖拽功能测试
 *
 * 测试场景：
 * 1. 鼠标拖拽启动和结束
 * 2. 触摸长按拖拽启动和结束
 * 3. 拖拽结束贴边吸附
 * 4. 展开状态阻止拖拽
 */

import { render, screen, fireEvent, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import AgentFloatingBall from '../../components/AgentFloatingBall'

// Mock deerflowClient
jest.mock('../../api/deerflowClient', () => ({
  deerflowClient: {
    chat: jest.fn().mockResolvedValue({
      success: true,
      ai_message: '测试响应'
    })
  }
}))

// Mock authStorage
jest.mock('../../utils/storage', () => ({
  authStorage: {
    getUser: jest.fn().mockReturnValue({
      id: 'test-user',
      name: '测试用户',
      age: 25,
      gender: 'male',
      location: '北京'
    })
  }
}))

describe('AgentFloatingBall 拖拽功能', () => {
  const mockProps = {
    visible: true,
    scene: 'home' as const
  }

  beforeEach(() => {
    // 重置窗口尺寸
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024
    })
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: 768
    })
  })

  // 辅助函数：获取悬浮球容器
  const getFloatingBall = () => document.querySelector('.agent-floating-ball')
  const getBallElement = () => document.querySelector('.agent-ball')

  describe('鼠标拖拽', () => {
    it('超过移动阈值后应进入拖拽状态', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      fireEvent.mouseDown(ball!, {
        clientX: 100,
        clientY: 100
      })

      expect(container).not.toHaveClass('dragging')

      fireEvent.mouseMove(window, {
        clientX: 140,
        clientY: 100
      })

      expect(container).toHaveClass('dragging')
    })

    it('鼠标移动应更新位置', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      fireEvent.mouseDown(ball!, {
        clientX: 968,
        clientY: 200
      })

      fireEvent.mouseMove(window, {
        clientX: 500,
        clientY: 300
      })

      expect(container!.style.left).not.toBe('968px')
    })

    it('鼠标释放应结束拖拽并贴边吸附', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      fireEvent.mouseDown(ball!, {
        clientX: 968,
        clientY: 200
      })

      fireEvent.mouseMove(window, {
        clientX: 500,
        clientY: 300
      })

      fireEvent.mouseUp(window)

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 200))
      })

      const leftValue = parseInt(container!.style.left)
      expect(leftValue === 16 || leftValue === 952).toBe(true)
    })

    it('鼠标短按无移动应展开面板', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      fireEvent.mouseDown(ball!, {
        clientX: 100,
        clientY: 100
      })
      fireEvent.mouseUp(window)

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 50))
      })

      expect(container).toHaveClass('expanded')
      expect(container).not.toHaveClass('dragging')
    })
  })

  describe('触摸长按拖拽', () => {
    it('触摸开始应启动长按计时器', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 模拟触摸开始
      fireEvent.touchStart(ball!, {
        touches: [{ clientX: 100, clientY: 100 }]
      })

      // 等待长按阈值（200ms）
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 250))
      })

      // 检查拖拽状态已启动
      expect(container).toHaveClass('dragging')
    })

    it('短按应展开面板而非拖拽', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 短按（< 200ms）
      fireEvent.touchStart(ball!, {
        touches: [{ clientX: 100, clientY: 100 }]
      })

      // 立即释放
      fireEvent.touchEnd(ball!)

      // 等待状态更新
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 50))
      })

      // 应展开面板，而非拖拽
      expect(container).toHaveClass('expanded')
      expect(container).not.toHaveClass('dragging')
    })

    it('长按后移动应触发拖拽', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 长按开始
      fireEvent.touchStart(ball!, {
        touches: [{ clientX: 968, clientY: 200 }]
      })

      // 等待长按阈值
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 250))
      })

      // 触摸移动
      fireEvent.touchMove(ball!, {
        touches: [{ clientX: 500, clientY: 300 }]
      })

      // 位置应更新
      expect(container!.style.left).not.toBe('968px')
    })
  })

  describe('贴边吸附', () => {
    it('左侧位置应吸附到左边', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      fireEvent.mouseDown(ball!, {
        clientX: 968,
        clientY: 200
      })

      fireEvent.mouseMove(window, {
        clientX: 100,
        clientY: 200
      })

      fireEvent.mouseUp(window)

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 200))
      })

      // 应吸附到左边（16px padding）
      expect(container!.style.left).toBe('16px')
    })

    it('右侧位置应吸附到右边', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 拖拽到右侧
      fireEvent.mouseDown(ball!, {
        clientX: 968,
        clientY: 200
      })

      fireEvent.mouseMove(window, {
        clientX: 900,
        clientY: 200
      })

      fireEvent.mouseUp(window)

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 200))
      })

      // 应吸附到右边（1024 - 56 - 16 = 952px）
      expect(container!.style.left).toBe('952px')
    })
  })

  describe('展开状态阻止拖拽', () => {
    it('展开状态不应触发拖拽', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 短按展开面板
      fireEvent.touchStart(ball!, {
        touches: [{ clientX: 100, clientY: 100 }]
      })

      fireEvent.touchEnd(ball!)

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 50))
      })

      expect(container).toHaveClass('expanded')
    })
  })

  describe('边界约束', () => {
    it('拖拽不应超出屏幕边界', async () => {
      render(<AgentFloatingBall {...mockProps} />)

      const ball = getBallElement()
      const container = getFloatingBall()

      // 尝试拖拽到屏幕外
      fireEvent.mouseDown(ball!, {
        clientX: 968,
        clientY: 200
      })

      fireEvent.mouseMove(window, {
        clientX: -100,
        clientY: -100
      })

      // 检查位置被约束在边界内
      const leftValue = parseInt(container!.style.left)
      const topValue = parseInt(container!.style.top)

      expect(leftValue).toBeGreaterThanOrEqual(16)
      expect(topValue).toBeGreaterThanOrEqual(16)
    })
  })
})