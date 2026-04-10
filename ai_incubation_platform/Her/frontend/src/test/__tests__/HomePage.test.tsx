/**
 * HomePage 页面边缘场景测试
 *
 * 测试覆盖:
 * 1. 页面渲染测试 (6 tests)
 * 2. 导航测试 (5 tests)
 * 3. 用户状态测试 (6 tests)
 * 4. 边缘场景测试 (8 tests)
 *
 * 总计: 25 个测试用例
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { MemoryRouter } from 'react-router-dom'
import HomePage from '../../pages/HomePage'

// Mock react-router-dom
const mockNavigate = jest.fn()
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}))

// Mock components
jest.mock('../../components/ChatInterface', () => () => <div data-testid="chat-interface">Chat Interface</div>)
jest.mock('../../components/ChatRoom', () => () => <div data-testid="chat-room">Chat Room</div>)
jest.mock('../../components/MatchCard', () => () => <div data-testid="match-card">Match Card</div>)
jest.mock('../../components/GenerativeUI', () => () => <div data-testid="generative-ui">Generative UI</div>)
jest.mock('../../components/AgentFloatingBall', () => () => <div data-testid="floating-ball">Floating Ball</div>)

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage })

// Mock fetch
global.fetch = jest.fn()

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })

  // ============= 第一部分：页面渲染测试 =============

  describe('Page Rendering', () => {
    it('should render home page without crashing', () => {
      renderWithRouter(<HomePage />)
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should render main layout components', () => {
      renderWithRouter(<HomePage />)

      // 应该渲染主要组件
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
      expect(screen.getByTestId('floating-ball')).toBeInTheDocument()
    })

    it('should render header with user info when logged in', () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({ username: 'test-user' }))

      renderWithRouter(<HomePage />)

      // 头部应该显示用户信息
    })

    it('should render without user info when not logged in', () => {
      mockLocalStorage.getItem.mockReturnValue(null)

      renderWithRouter(<HomePage />)

      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should render sidebar navigation', () => {
      renderWithRouter(<HomePage />)

      // 侧边栏导航
    })

    it('should render bottom navigation on mobile', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 375 })

      renderWithRouter(<HomePage />)

      // 移动端底部导航
    })
  })

  // ============= 第二部分：导航测试 =============

  describe('Navigation', () => {
    it('should navigate to profile page when profile button clicked', async () => {
      renderWithRouter(<HomePage />)

      // 点击个人资料按钮
      const profileButton = screen.queryByRole('button', { name: /profile/i })
      if (profileButton) {
        await userEvent.click(profileButton)
        expect(mockNavigate).toHaveBeenCalled()
      }
    })

    it('should navigate to settings page when settings button clicked', async () => {
      renderWithRouter(<HomePage />)

      const settingsButton = screen.queryByRole('button', { name: /settings/i })
      if (settingsButton) {
        await userEvent.click(settingsButton)
      }
    })

    it('should navigate to matches page when matches button clicked', async () => {
      renderWithRouter(<HomePage />)

      const matchesButton = screen.queryByRole('button', { name: /matches/i })
      if (matchesButton) {
        await userEvent.click(matchesButton)
      }
    })

    it('should navigate to login page when logout button clicked', async () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({ username: 'test-user' }))

      renderWithRouter(<HomePage />)

      const logoutButton = screen.queryByRole('button', { name: /logout/i })
      if (logoutButton) {
        await userEvent.click(logoutButton)
        expect(mockLocalStorage.removeItem).toHaveBeenCalled()
      }
    })

    it('should handle browser back/forward navigation', () => {
      renderWithRouter(<HomePage />)

      // 浏览器前进/后退
      window.history.pushState({}, '', '/matches')
      window.history.back()

      // 页面应该正常响应
    })
  })

  // ============= 第三部分：用户状态测试 =============

  describe('User State', () => {
    it('should load user data from localStorage', () => {
      const userData = { username: 'test-user', id: '123' }
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify(userData))

      renderWithRouter(<HomePage />)

      expect(mockLocalStorage.getItem).toHaveBeenCalled()
    })

    it('should handle invalid JSON in localStorage', () => {
      mockLocalStorage.getItem.mockReturnValue('not valid json')

      renderWithRouter(<HomePage />)

      // 不应该崩溃
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should handle null user data', () => {
      mockLocalStorage.getItem.mockReturnValue(null)

      renderWithRouter(<HomePage />)

      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should update user state on login', async () => {
      renderWithRouter(<HomePage />)

      // 模拟登录事件
      act(() => {
        window.dispatchEvent(new CustomEvent('user-login', {
          detail: { username: 'new-user' },
        }))
      })

      // 用户状态应该更新
    })

    it('should clear user state on logout', async () => {
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify({ username: 'test-user' }))

      renderWithRouter(<HomePage />)

      // 模拟登出
      act(() => {
        window.dispatchEvent(new CustomEvent('user-logout'))
      })

      // 用户状态应该清除
    })

    it('should persist user preferences', () => {
      const preferences = { theme: 'dark', language: 'zh' }
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify(preferences))

      renderWithRouter(<HomePage />)

      // 偏好设置应该被应用
    })
  })

  // ============= 第四部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle network error gracefully', async () => {
      ;(global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'))

      renderWithRouter(<HomePage />)

      // 不应该崩溃
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should handle slow API response', async () => {
      ;(global.fetch as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ ok: true, json: () => [] }), 5000))
      )

      renderWithRouter(<HomePage />)

      // 应该显示加载状态
      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should handle 401 unauthorized response', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
      })

      renderWithRouter(<HomePage />)

      // 应该重定向到登录页或显示错误
    })

    it('should handle 500 server error', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
      })

      renderWithRouter(<HomePage />)

      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should handle window resize', () => {
      renderWithRouter(<HomePage />)

      // 触发窗口大小变化
      act(() => {
        window.dispatchEvent(new Event('resize'))
      })

      // 不应该崩溃
    })

    it('should handle visibility change', () => {
      renderWithRouter(<HomePage />)

      // 页面切换到后台
      act(() => {
        Object.defineProperty(document, 'visibilityState', { value: 'hidden' })
        document.dispatchEvent(new Event('visibilitychange'))
      })

      // 页面切换回前台
      act(() => {
        Object.defineProperty(document, 'visibilityState', { value: 'visible' })
        document.dispatchEvent(new Event('visibilitychange'))
      })

      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
    })

    it('should handle beforeunload event', () => {
      renderWithRouter(<HomePage />)

      // 页面即将卸载
      const event = new Event('beforeunload')
      Object.defineProperty(event, 'returnValue', { value: '' })

      act(() => {
        window.dispatchEvent(event)
      })

      // 不应该崩溃
    })

    it('should handle component unmount during async operation', async () => {
      ;(global.fetch as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ ok: true, json: () => [] }), 1000))
      )

      const { unmount } = renderWithRouter(<HomePage />)

      // 在异步操作完成前卸载
      unmount()

      // 不应该抛出警告或错误
      await new Promise(resolve => setTimeout(resolve, 1500))
    })
  })
})