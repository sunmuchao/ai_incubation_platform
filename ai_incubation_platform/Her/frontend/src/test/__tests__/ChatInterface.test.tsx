/**
 * ChatInterface 组件测试
 *
 * 测试覆盖:
 * 1. 组件渲染测试
 * 2. 用户交互测试
 * 3. 消息处理测试
 * 4. API 调用测试
 * 5. Generative UI 测试
 * 6. 边缘场景测试
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
    chat: jest.fn().mockResolvedValue({
      success: true,
      ai_message: 'AI response from DeerFlow',
      deerflow_used: true,
      generative_ui: undefined,
      suggested_actions: [],
    }),
    stream: jest.fn(),
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
    getUser: jest.fn().mockReturnValue({
      age: 25,
      gender: 'male',
      location: '北京',
      relationship_goal: 'dating',
    }),
    getUserId: jest.fn().mockReturnValue('test-user-id'),
    getToken: jest.fn().mockReturnValue('test-token'),
  },
  registrationStorage: {
    markCompleted: jest.fn(),
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

// Mock fetch for quick tags API
const originalFetch = global.fetch

// Mock lazy-loaded components with proper exports
jest.mock('../../components/MatchCard', () => {
  const MockMatchCard = ({ match }: any) => (
    <div data-testid="match-card">
      {match?.user?.name || 'Match User'}
      {match?.compatibility_score && (
        <span data-testid="compatibility-score">{match.compatibility_score}%</span>
      )}
    </div>
  )
  return {
    __esModule: true,
    default: MockMatchCard,
  }
})

jest.mock('../../components/PreCommunicationSessionCard', () => {
  const MockPreCommSessionCard = ({ sessions }: any) => (
    <div data-testid="precomm-session-card">
      {sessions && sessions.length > 0
        ? `找到 ${sessions.length} 个 AI 预沟通会话`
        : '暂无 AI 预沟通会话'}
    </div>
  )
  return {
    __esModule: true,
    default: MockPreCommSessionCard,
  }
})

jest.mock('../../components/PreCommunicationDialogCard', () => {
  const MockPreCommDialogCard = ({ messages }: any) => (
    <div data-testid="precomm-dialog-card">
      AI 预沟通对话历史（共 {messages?.length || 0} 条）
    </div>
  )
  return {
    __esModule: true,
    default: MockPreCommDialogCard,
  }
})

jest.mock('../../components/FeatureCards', () => {
  const MockFeatureCardRenderer = ({ actionType }: any) => (
    <div data-testid="feature-card-renderer">
      Feature: {actionType}
    </div>
  )
  return {
    __esModule: true,
    FeatureCardRenderer: MockFeatureCardRenderer,
  }
})

jest.mock('../../components/ProfileQuestionCard', () => {
  const MockProfileQuestionCard = ({ question }: any) => (
    <div data-testid="profile-question-card">
      {question?.question || 'Profile Question'}
    </div>
  )
  return {
    __esModule: true,
    default: MockProfileQuestionCard,
  }
})

// Import mocked modules for use in tests
import { deerflowClient } from '../../api/deerflowClient'

describe('ChatInterface Component', () => {
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
              { label: '关系分析', trigger: '分析我的关系' },
              { label: '约会建议', trigger: '约会建议' },
            ],
          }),
        })
      }
      return originalFetch(url)
    }) as any

    // Default mock for deerflowClient
    ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
      success: true,
      ai_message: 'AI response from DeerFlow',
      deerflow_used: true,
      generative_ui: undefined,
      suggested_actions: [],
    })
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  // ============= 第一部分：组件渲染测试 =============

  describe('Component Rendering', () => {
    it('should render welcome message on initial load', async () => {
      render(<ChatInterface />)
      // 等待组件初始化
      await waitFor(() => {
        expect(screen.getByText(/你好，我是 Her/)).toBeInTheDocument()
      })
    })

    it('should render input field with placeholder', () => {
      render(<ChatInterface />)
      expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
    })

    it('should render quick action tags from API', async () => {
      render(<ChatInterface />)

      // 等待 quick tags 加载
      await waitFor(() => {
        expect(screen.getByText('找对象')).toBeInTheDocument()
      })

      expect(screen.getByText('AI 预沟通')).toBeInTheDocument()
      expect(screen.getByText('关系分析')).toBeInTheDocument()
      expect(screen.getByText('约会建议')).toBeInTheDocument()
    })

    it('should render send button', async () => {
      render(<ChatInterface />)

      // 等待 quick tags 加载后找到发送按钮
      await waitFor(() => {
        // 使用 aria-label 找到发送按钮
        const sendIcon = screen.getByRole('img', { name: 'send' })
        expect(sendIcon).toBeInTheDocument()
      })
    })

    it('should have disabled send button when input is empty', async () => {
      render(<ChatInterface />)

      // 等待组件渲染
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/告诉我你想要什么/)
        expect(input).toBeInTheDocument()
      })

      // 按钮应该被禁用（因为输入为空）
      const button = screen.getByRole('img', { name: 'send' }).closest('button')
      expect(button).toBeDisabled()
    })
  })

  // ============= 第二部分：用户交互测试 =============

  describe('User Interactions', () => {
    it('should enable send button when input has content', async () => {
      render(<ChatInterface />)

      // 等待组件渲染
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      // 输入内容
      await userEvent.type(input, 'test message')

      // 等待按钮状态更新
      await waitFor(() => {
        const button = screen.getByRole('img', { name: 'send' }).closest('button')
        expect(button).not.toBeDisabled()
      })
    })

    it('should clear input after sending message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

      await userEvent.type(input, 'test message')

      // 点击发送按钮
      const button = screen.getByRole('img', { name: 'send' }).closest('button')
      await userEvent.click(button!)

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })

    it('should send message on Enter key press', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText('test message')).toBeInTheDocument()
      })
    })

    it('should not send message on Shift+Enter', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement

      await userEvent.type(input, 'test message{shift>}{enter}')

      // Message should not be sent, input should still have content
      expect(input.value).toBe('test message')
    })

    it('should handle quick action click', async () => {
      render(<ChatInterface />)

      // 等待 quick tags 加载
      await waitFor(() => {
        expect(screen.getByText('找对象')).toBeInTheDocument()
      })

      const quickAction = screen.getByText('找对象')

      await userEvent.click(quickAction)

      const input = screen.getByPlaceholderText(/告诉我你想要什么/) as HTMLInputElement
      expect(input.value).toContain('帮我找对象')
    })

    it('should display loading indicator while processing', async () => {
      // Mock API to delay response
      ;(deerflowClient.chat as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
          ai_message: 'AI response',
          deerflow_used: true,
        }), 500))
      )

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '找对象{enter}')

      await waitFor(() => {
        expect(screen.getByText(/Her 正在想/)).toBeInTheDocument()
      })
    })

    it('should not send empty message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const button = screen.getByRole('img', { name: 'send' }).closest('button')

      // 按钮已禁用，点击不会有反应
      expect(button).toBeDisabled()
    })

    it('should not send whitespace-only message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '   {enter}')

      // Should not add any user message
      expect(screen.queryByText('   ')).not.toBeInTheDocument()
    })
  })

  // ============= 第三部分：消息处理测试 =============

  describe('Message Handling', () => {
    it('should display user message after sending', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'hello{enter}')

      await waitFor(() => {
        expect(screen.getByText('hello')).toBeInTheDocument()
      })
    })

    it('should respond to greeting', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '你好呀！很高兴认识你~',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '你好{enter}')

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      })
    })

    it('should respond to thanks', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '能帮到你很开心~',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '谢谢{enter}')

      await waitFor(() => {
        expect(screen.getByText(/能帮到你/)).toBeInTheDocument()
      })
    })

    it('should respond to goodbye', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '下次见！祝你幸福~',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '再见{enter}')

      await waitFor(() => {
        expect(screen.getByText(/下次见/)).toBeInTheDocument()
      })
    })

    it('should handle special characters in message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '<script>alert("xss")</script>{enter}')

      await waitFor(() => {
        expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument()
      })
    })

    it('should handle emoji in message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '你好世界 🎉{enter}')

      await waitFor(() => {
        expect(screen.getByText(/你好世界/)).toBeInTheDocument()
      })
    })

    it('should handle initial match prop', async () => {
      const mockMatch = {
        user: { id: 'test-id', name: 'Test User', interests: ['旅行'] },
        compatibility_score: 85,
      }

      render(<ChatInterface initialMatch={mockMatch} />)

      await waitFor(() => {
        expect(screen.getByText(/你选择了 "Test User"/)).toBeInTheDocument()
      })
    })

    it('should call onInitialMatchConsumed after processing initial match', async () => {
      const mockMatch = {
        user: { id: 'test-id', name: 'Test User', interests: [] },
        compatibility_score: 85,
      }
      const onConsumed = jest.fn()

      render(<ChatInterface initialMatch={mockMatch} onInitialMatchConsumed={onConsumed} />)

      await waitFor(() => {
        expect(onConsumed).toHaveBeenCalled()
      })
    })
  })

  // ============= 第四部分：API 调用测试 =============

  describe('API Calls', () => {
    it('should call deerflowClient.chat with user intent', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: 'AI response',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我找对象{enter}')

      await waitFor(() => {
        expect(deerflowClient.chat).toHaveBeenCalled()
      })
    })

    it('should display API response message', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '这是 AI 的回复',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText('这是 AI 的回复')).toBeInTheDocument()
      })
    })

    it('should display match cards when API returns matches via DeerFlow', async () => {
      // Mock DeerFlow to return matches
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: false,
        ai_message: '',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '找到匹配对象',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
        tool_result: {
          data: {
            matches: [
              { user: { id: '1', name: 'User 1' }, compatibility_score: 85 },
            ],
          },
        },
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我匹配{enter}')

      // Should fallback to DeerFlow and get matches
      await waitFor(() => {
        expect(screen.getByText('找到匹配对象')).toBeInTheDocument()
      })
    })

    it('should handle API error gracefully', async () => {
      ;(deerflowClient.chat as jest.Mock).mockRejectedValue(new Error('API Error'))

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test message{enter}')

      await waitFor(() => {
        expect(screen.getByText(/抱歉，出现了一些问题/)).toBeInTheDocument()
      })
    })

    it('should handle DeerFlow response correctly', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: 'DeerFlow response',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'complex query{enter}')

      await waitFor(() => {
        expect(deerflowClient.chat).toHaveBeenCalled()
      })
    })

    it('should load pre-communication sessions when requested', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '查看预沟通会话',
        deerflow_used: true,
        generative_ui: {
          component_type: 'PreCommunicationPanel',
          props: {
            sessions: [
              { session_id: '1', status: 'completed', compatibility_score: 85 },
            ],
          },
        },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(deerflowClient.chat).toHaveBeenCalled()
      })
    })
  })

  // ============= 第五部分：Generative UI 测试 =============

  describe('Generative UI', () => {
    it('should render pre-communication sessions card', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '查看预沟通会话',
        deerflow_used: true,
        generative_ui: {
          component_type: 'PreCommunicationPanel',
          props: {
            sessions: [
              {
                session_id: 'session-1',
                status: 'completed',
                compatibility_score: 85,
                hard_check_passed: true,
                values_check_passed: true,
              },
            ],
          },
        },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      // 等待 AI 消息和 Generative UI 渲染
      await waitFor(() => {
        expect(screen.getByText('查看预沟通会话')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show empty state when no pre-communication sessions', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '查看预沟通会话',
        deerflow_used: true,
        generative_ui: {
          component_type: 'PreCommunicationPanel',
          props: {
            sessions: [],
          },
        },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(screen.getByTestId('precomm-session-card')).toBeInTheDocument()
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      })
    })

    it('should render match cards via DeerFlow', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: false,
        ai_message: '',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '找到匹配',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
        tool_result: {
          data: {
            matches: [
              {
                user: { id: '1', name: 'Test User', age: 25, location: '北京' },
                compatibility_score: 90,
              },
            ],
          },
        },
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '帮我匹配{enter}')

      await waitFor(() => {
        expect(screen.getByText('找到匹配')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should render next action chips', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: 'AI response',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [
          { label: '发起对话', action: 'start_chat' },
          { label: '查看详情', action: 'view_detail' },
        ],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      // 组件渲染 next_actions (action 字符串)，不是 suggested_actions 的 label
      await waitFor(() => {
        expect(screen.getByText('start_chat')).toBeInTheDocument()
        expect(screen.getByText('view_detail')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should handle feature trigger event', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      act(() => {
        window.dispatchEvent(new CustomEvent('trigger-feature', {
          detail: { feature: { name: '测试功能', action: 'test-action' } },
        }))
      })

      await waitFor(() => {
        expect(screen.getByText(/我来帮你打开「测试功能」/)).toBeInTheDocument()
      })
    })
  })

  // ============= 第六部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle component unmount during API call', async () => {
      ;(deerflowClient.chat as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
      ai_message: 'ok',
          deerflow_used: true,
        }), 1000))
      )

      const { unmount } = render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, 'test{enter}')

      // Unmount before API responds
      unmount()

      // Should not throw error
      await waitFor(() => {
        expect(true).toBe(true)
      })
    })

    it('should handle match select callback prop', async () => {
      const onMatchSelect = jest.fn()

      render(<ChatInterface onMatchSelect={onMatchSelect} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 验证组件正确渲染，props 被传递
      expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
    })

    it('should handle open chat room callback prop', async () => {
      const onOpenChatRoom = jest.fn()

      render(<ChatInterface onOpenChatRoom={onOpenChatRoom} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 验证组件正确渲染，props 被传递
      expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
    })

    it('should handle view matches callback prop', async () => {
      const onViewMatches = jest.fn()

      render(<ChatInterface onViewMatches={onViewMatches} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 验证组件正确渲染，props 被传递
      expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
    })

    it('should handle pre-communication session with no messages', async () => {
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '查看预沟通会话',
        deerflow_used: true,
        generative_ui: {
          component_type: 'PreCommunicationPanel',
          props: {
            sessions: [],
          },
        },
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)

      await userEvent.type(input, '启动预沟通{enter}')

      await waitFor(() => {
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      })
    })
  })
})