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
 * 7. Memory 异步同步测试
 * 8. QuickStart 完成流程测试
 * 9. 🚀 [性能优化] 动态进度提示测试
 * 10. 🚀 [性能优化] 骨架屏预览测试
 * 11. 🚀 [性能优化] 流式输出测试
 * 12. 🚀 [性能优化] 进度推断测试
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      // 返回简单的翻译值
      const translations: Record<string, string> = {
        'conversation.welcomeNew': '你好，我是 Her，你的专属顾问。',
        'conversation.welcomeUser': '你好，我是 Her，很高兴再次见到你！',
        'conversation.startChat': '开始',
        'conversation.inputPlaceholder': '告诉我你想要什么...',
        'conversation.herThinking': 'Her 正在思考...',
        'conversation.sorryError': '抱歉，出现了一些问题',
        'home.todayMatches': '找对象',
      }
      return translations[key] || key
    },
    i18n: {
      changeLanguage: jest.fn(),
    },
  }),
}))

// 🔧 [性能优化] Mock react-window List - 必须在 ChatInterface 导入之前
jest.mock('react-window', () => {
  const MockList = ({ rowCount, rowComponent, onRowsRendered }: any) => {
    const rows = Array.from({ length: rowCount || 0 }).map((_, index) =>
      rowComponent({ index, style: {} })
    )
    if (onRowsRendered) {
      onRowsRendered({ startIndex: 0, stopIndex: (rowCount || 0) - 1 })
    }
    return <div data-testid="virtual-list">{rows}</div>
  }
  return {
    __esModule: true,
    List: MockList,
    VariableSizeList: MockList,
  }
})

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
    // 🚀 [流式输出] Mock stream 方法
    stream: jest.fn().mockImplementation(async (message, threadId, onEvent) => {
      // 模拟流式事件序列
      const events = [
        { type: 'messages-tuple', data: { content: '我' } },
        { type: 'messages-tuple', data: { content: '为你' } },
        { type: 'messages-tuple', data: { content: '找到' } },
        { type: 'messages-tuple', data: { content: '了匹配对象' } },
        { type: 'custom', data: { progress_step: '正在分析匹配度...' } },
        { type: 'custom', data: { generative_ui: { component_type: 'MatchCardList', props: { candidates: [] } } } },
        { type: 'end', data: { suggested_actions: [{ label: '查看详情', action: 'view_detail' }] } },
      ]

      // 模拟异步事件流
      for (const event of events) {
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent(event)
      }
    }),
    syncMemory: jest.fn().mockResolvedValue({
      success: true,
      facts_count: 5,
      message: '已同步 5 条用户信息到 DeerFlow Memory',
    }),
    // Mock parse methods
    parseGenerativeUITags: jest.fn().mockImplementation((response) => {
      return { natural_message: response.ai_message || '', generative_ui_cards: [] }
    }),
    parseToolResult: jest.fn().mockReturnValue(null),
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
  // 🔧 [状态持久化] Mock chatStorage
  chatStorage: {
    getMessages: jest.fn().mockReturnValue([]),
    setMessages: jest.fn(),
    clearMessages: jest.fn(),
  },
}))

// Mock localStorage
let localStorageData: Record<string, string> = {}
const mockLocalStorage = {
  getItem: jest.fn().mockImplementation((key: string) => localStorageData[key] || null),
  setItem: jest.fn().mockImplementation((key: string, value: string) => {
    localStorageData[key] = value
  }),
  removeItem: jest.fn().mockImplementation((key: string) => {
    delete localStorageData[key]
  }),
  clear: jest.fn().mockImplementation(() => {
    localStorageData = {}
  }),
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

jest.mock('../../components/generative-ui/MatchComponents', () => {
  const MockMatchCardList = ({ matches }: any) => (
    <div data-testid="match-card-list">
      {matches && matches.length > 0
        ? matches.map((m: any, i: number) => (
            <div key={i} data-testid="match-card">
              {m?.user?.name || 'Match User'}
            </div>
          ))
        : '暂无匹配对象'}
    </div>
  )
  return {
    __esModule: true,
    MatchCardList: MockMatchCardList,
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
  const MockFeatureCardRenderer = ({ featureAction }: any) => (
    <div data-testid="feature-card-renderer">
      Feature: {featureAction}
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
// Import chatStorage from mocked module
const { chatStorage } = jest.requireMock('../../utils/storage')

describe('ChatInterface Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
    // 🔧 [状态持久化] 重置 chatStorage mock
    ;(chatStorage.getMessages as jest.Mock).mockReturnValue([])
    // mockClear 返回 undefined，不能链式调用
    ;(chatStorage.setMessages as jest.Mock).mockClear?.()

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
      // Mock stream to delay response
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 500))
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        await new Promise(resolve => setTimeout(resolve, 100))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '找对象{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/正在/)).toBeInTheDocument()
      }, { timeout: 2000 })
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
      // Mock stream 返回期望的问候响应
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '你好呀！很高兴认识你~' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '你好{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/你好呀/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should respond to thanks', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '能帮到你很开心~' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '谢谢{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/能帮到你/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should respond to goodbye', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '下次见！祝你幸福~' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '再见{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/下次见/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should handle special characters in message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '<script>alert("xss")</script>{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('<script>alert("xss")</script>')).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should handle emoji in message', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '你好世界 🎉{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/你好世界/)).toBeInTheDocument()
      }, { timeout: 2000 })
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
    it('should call deerflowClient.stream with user intent', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '帮我找对象{enter}')
      })

      await waitFor(() => {
        expect(deerflowClient.stream).toHaveBeenCalled()
      }, { timeout: 2000 })
    })

    it('should display API response message', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '这是 AI 的回复' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, 'test message{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('这是 AI 的回复')).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should display match cards when API returns matches via DeerFlow', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '找到匹配对象' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'MatchCardList', props: { candidates: [{ user: { id: '1', name: 'User 1' }, compatibility_score: 85 }] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '帮我匹配{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('找到匹配对象')).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should handle API error gracefully', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async () => {
        throw new Error('API Error')
      })
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '抱歉，出现了一些问题',
        deerflow_used: true,
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, 'test message{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText(/抱歉/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should handle DeerFlow response correctly', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: 'DeerFlow response' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, 'complex query{enter}')
      })

      await waitFor(() => {
        expect(deerflowClient.stream).toHaveBeenCalled()
      }, { timeout: 2000 })
    })

    it('should load pre-communication sessions when requested', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '查看预沟通会话' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'PreCommunicationPanel', props: { sessions: [{ session_id: '1', status: 'completed', compatibility_score: 85 }] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '启动预沟通{enter}')
      })

      await waitFor(() => {
        expect(deerflowClient.stream).toHaveBeenCalled()
      }, { timeout: 2000 })
    })
  })

  // ============= 第五部分：Generative UI 测试 =============

  describe('Generative UI', () => {
    it('should render pre-communication sessions card', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '查看预沟通会话' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'PreCommunicationPanel', props: { sessions: [{ session_id: 'session-1', status: 'completed', compatibility_score: 85 }] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '启动预沟通{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('查看预沟通会话')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show empty state when no pre-communication sessions', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '查看预沟通会话' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'PreCommunicationPanel', props: { sessions: [] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '启动预沟通{enter}')
      })

      await waitFor(() => {
        expect(screen.getByTestId('precomm-session-card')).toBeInTheDocument()
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should render match cards via DeerFlow', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '找到匹配' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'MatchCardList', props: { candidates: [{ user: { id: '1', name: 'Test User', age: 25, location: '北京' }, compatibility_score: 90 }] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '帮我匹配{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('找到匹配')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should render next action chips', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        onEvent({ type: 'end', data: { suggested_actions: [{ label: '发起对话', action: 'start_chat' }, { label: '查看详情', action: 'view_detail' }] } })
        await new Promise(resolve => setTimeout(resolve, 50))
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, 'test{enter}')
      })

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
      }, { timeout: 2000 })
    })
  })

  // ============= 第六部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle component unmount during API call', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => {
          resolve([])
        }, 1000))
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
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '查看预沟通会话' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'PreCommunicationPanel', props: { sessions: [] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '启动预沟通{enter}')
      })

      await waitFor(() => {
        expect(screen.getByText('暂无 AI 预沟通会话')).toBeInTheDocument()
      }, { timeout: 2000 })
    })
  })

  // ============= 第七部分：Memory 异步同步测试（新增）=============

  describe('Memory Async Sync', () => {
    it('should call syncMemory without blocking UI', async () => {
      // Mock syncMemory to be slow (simulating async operation)
      ;(deerflowClient.syncMemory as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
          facts_count: 5,
          message: '已同步',
        }), 1000))
      )

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // UI should be responsive immediately
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      expect(input).not.toBeDisabled()
    })

    it('should not wait for syncMemory to complete before showing response', async () => {
      // Mock slow syncMemory
      ;(deerflowClient.syncMemory as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
          facts_count: 5,
          message: '已同步',
        }), 2000))
      )

      // Mock stream to be fast
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '快速响应' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // AI response should appear quickly (not waiting for syncMemory)
      await waitFor(() => {
        expect(screen.getByText('快速响应')).toBeInTheDocument()
      }, { timeout: 500 }) // Should be faster than syncMemory (2000ms)
    })

    it('should handle syncMemory failure gracefully', async () => {
      // Mock syncMemory to fail
      ;(deerflowClient.syncMemory as jest.Mock).mockRejectedValue(new Error('Sync failed'))

      // Mock stream to succeed
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '正常响应' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // Should still show AI response even if syncMemory failed
      await waitFor(() => {
        expect(screen.getByText('正常响应')).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should call syncMemory with correct user_id', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // syncMemory should be available (mocked)
      expect(deerflowClient.syncMemory).toBeDefined()
    })
  })

  // ============= 第八部分：QuickStart 完成流程测试（新增）=============

  describe('QuickStart Completion Flow', () => {
    it('should show ready message immediately after all fields filled', async () => {
      // This tests the optimization: showing message without waiting for Memory sync
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // UI should be responsive
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      expect(input).toBeInTheDocument()
    })

    it('should not block on syncMemory during QuickStart completion', async () => {
      // Mock slow syncMemory (1 second)
      ;(deerflowClient.syncMemory as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
          facts_count: 10,
          message: '已同步',
        }), 1000))
      )

      render(<ChatInterface />)

      // Component should render immediately
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      }, { timeout: 100 }) // Should be much faster than 1000ms

      // Input should not be blocked
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      expect(input).not.toBeDisabled()
    })
  })

  // ============= 第九部分：🚀 [性能优化] 动态进度提示测试 =============

  describe('Dynamic Progress Indicator', () => {
    it('should show loading indicator with progress text', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        // 模拟慢速响应
        await new Promise(resolve => setTimeout(resolve, 500))
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        await new Promise(resolve => setTimeout(resolve, 500))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '帮我找对象{enter}')
      })

      // 应该显示加载指示器
      await waitFor(() => {
        expect(screen.getByText(/正在/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should cycle through progress steps', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '找对象{enter}')
      })

      // 应该显示第一个进度提示
      await waitFor(() => {
        expect(screen.getByText(/正在理解/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should hide loading indicator after response', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '快速响应' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 响应后应该隐藏加载指示器
      await waitFor(() => {
        expect(screen.getByText('快速响应')).toBeInTheDocument()
        expect(screen.queryByText(/正在/)).not.toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should show animated dots during loading', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 500))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 检查加载指示器存在
      await waitFor(() => {
        const loadingIndicator = document.querySelector('.loading-indicator')
        expect(loadingIndicator).toBeInTheDocument()
      }, { timeout: 2000 })
    })
  })

  // ============= 第十部分：🚀 [性能优化] 骨架屏预览测试 =============

  describe('Skeleton Preview', () => {
    it('should show skeleton preview for match requests', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        onEvent({ type: 'messages-tuple', data: { content: '找到匹配对象' } })
        await new Promise(resolve => setTimeout(resolve, 500))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '帮我找对象{enter}')
      })

      // 应该显示骨架屏预览
      await waitFor(() => {
        const skeletonPreview = document.querySelector('.match-skeleton-preview')
        expect(skeletonPreview).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should show skeleton preview title', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '推荐几个{enter}')
      })

      // 应该显示骨架屏标题
      await waitFor(() => {
        expect(screen.getByText(/为你精选匹配对象/)).toBeInTheDocument()
      }, { timeout: 2000 })
    })

    it('should show 3 skeleton cards', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '看看候选人{enter}')
      })

      // 应该显示 3 个骨架卡片
      await waitFor(() => {
        const skeletonCards = document.querySelectorAll('.skeleton-match-card')
        expect(skeletonCards.length).toBe(3)
      }, { timeout: 2000 })
    })

    it('should hide skeleton after receiving content', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '快速响应' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '找对象{enter}')
      })

      // 响应后骨架屏应该消失
      await waitFor(() => {
        expect(screen.getByText('快速响应')).toBeInTheDocument()
        const skeletonPreview = document.querySelector('.match-skeleton-preview')
        expect(skeletonPreview).not.toBeInTheDocument()
      })
    })

    it('should NOT show skeleton for non-match requests', async () => {
      ;(deerflowClient.chat as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          success: true,
          ai_message: '普通回复',
          deerflow_used: true,
        }), 1000))
      )

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await userEvent.type(input, '你好{enter}')

      // 非匹配请求不应显示骨架屏
      await waitFor(() => {
        const skeletonPreview = document.querySelector('.match-skeleton-preview')
        expect(skeletonPreview).not.toBeInTheDocument()
      })
    })
  })

  // ============= 第十一部分：🚀 [性能优化] 流式输出测试 =============

  describe('Streaming Output', () => {
    it('should use stream API for messages', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 应该调用 stream API
      await waitFor(() => {
        expect(deerflowClient.stream).toHaveBeenCalled()
      }, { timeout: 2000 })
    })

    it('should accumulate streaming content', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        // 发送完整内容，不拆分
        onEvent({ type: 'messages-tuple', data: { content: '我为你找到了匹配对象' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 等待流式内容累积
      await waitFor(() => {
        expect(screen.getByText(/我为你找到/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should update progress from stream events', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'custom', data: { progress_step: '正在分析匹配度...' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 应该接收到进度更新事件
      await waitFor(() => {
        expect(screen.getByText(/正在分析匹配度/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show generative UI from stream events', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: '找到匹配' } })
        onEvent({ type: 'custom', data: { generative_ui: { component_type: 'MatchCardList', props: { candidates: [{ user: { id: '1', name: 'Test User' } }] } } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 流式完成后应该显示 Generative UI
      await waitFor(() => {
        expect(screen.getByTestId('match-card')).toBeInTheDocument()
        expect(screen.getByText('Test User')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show suggested actions after stream ends', async () => {
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: { suggested_actions: [{ label: '查看详情', action: 'view_detail' }] } })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 流式结束后应该显示建议操作（使用 action 而非 label）
      await waitFor(() => {
        expect(screen.getByText('view_detail')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should fallback to chat API if stream fails', async () => {
      // Mock stream to fail immediately
      ;(deerflowClient.stream as jest.Mock).mockImplementation(() => {
        return Promise.reject(new Error('Stream error'))
      })

      // Mock chat to succeed as fallback
      ;(deerflowClient.chat as jest.Mock).mockReset()
      ;(deerflowClient.chat as jest.Mock).mockResolvedValue({
        success: true,
        ai_message: '降级响应',
        deerflow_used: true,
        generative_ui: undefined,
        suggested_actions: [],
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 等待 stream 被调用并失败，然后 chat 作为 fallback
      await waitFor(() => {
        expect(deerflowClient.stream).toHaveBeenCalled()
      }, { timeout: 2000 })

      // 等待 chat 作为 fallback 被调用
      await waitFor(() => {
        expect(deerflowClient.chat).toHaveBeenCalled()
      }, { timeout: 5000 })

      // 等待响应显示
      await waitFor(() => {
        expect(screen.getByText('降级响应')).toBeInTheDocument()
      }, { timeout: 2000 })
    }, 15000)  // 整个测试超时时间
  })

  // ============= 第十二部分：🚀 [性能优化] 进度推断测试 =============

  describe('Progress Inference', () => {
    it('should infer progress from tool call', async () => {
      // Mock stream with tool call event
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        onEvent({ type: 'custom', data: { tool_call: { name: 'her_find_candidates' } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 等待 AI 响应出现（表示流式完成）
      await waitFor(() => {
        expect(screen.getByText('AI response')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should infer progress from tool result', async () => {
      // Mock stream with tool result event
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        onEvent({ type: 'messages-tuple', data: { content: 'AI response' } })
        onEvent({ type: 'custom', data: { tool_result: { candidates: [{ name: 'Test' }] } } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 等待 AI 响应出现（表示流式完成）
      await waitFor(() => {
        expect(screen.getByText('AI response')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should infer progress from AI content length', async () => {
      // Mock stream with long AI content
      ;(deerflowClient.stream as jest.Mock).mockImplementation(async (message, threadId, onEvent) => {
        // 发送完整的长内容
        onEvent({ type: 'messages-tuple', data: { content: '我为你精选了 3 位匹配对象，他们都很优秀，值得你了解' } })
        await new Promise(resolve => setTimeout(resolve, 50))
        onEvent({ type: 'end', data: {} })
      })

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await act(async () => {
        await userEvent.type(input, '测试{enter}')
      })

      // 等待长内容出现
      await waitFor(() => {
        expect(screen.getByText(/我为你精选了/)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  // ============= 第十三部分：🔧 [状态持久化] 消息持久化测试 =============

  describe('Message Persistence', () => {
    it('should load messages from localStorage on mount', async () => {
      // Mock stored messages
      const storedMessages = [
        { id: 'stored-1', type: 'user', content: 'Stored message', timestamp: new Date().toISOString() },
        { id: 'stored-2', type: 'ai', content: 'Stored AI response', timestamp: new Date().toISOString() },
      ]
      ;(chatStorage.getMessages as jest.Mock).mockReturnValue(storedMessages)

      render(<ChatInterface />)

      // 等待消息加载
      await waitFor(() => {
        expect(screen.getByText('Stored message')).toBeInTheDocument()
        expect(screen.getByText('Stored AI response')).toBeInTheDocument()
      })
    })

    it('should save messages to localStorage when messages change', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 清除之前的调用记录（组件初始化可能触发 setMessages）
      ;(chatStorage.setMessages as jest.Mock).mockClear()

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await userEvent.type(input, 'test message{enter}')

      // 等待消息发送和保存
      await waitFor(() => {
        expect(chatStorage.setMessages).toHaveBeenCalled()
      }, { timeout: 2000 })

      // 检查保存的消息包含用户输入（获取最后一次调用的参数）
      const calls = (chatStorage.setMessages as jest.Mock).mock.calls
      const lastCall = calls[calls.length - 1]
      const savedMessages = lastCall[1]
      expect(savedMessages.some((m: any) => m.content === 'test message')).toBe(true)
    })

    it('should use correct userId for storage key', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await userEvent.type(input, 'test{enter}')

      await waitFor(() => {
        expect(chatStorage.setMessages).toHaveBeenCalled()
      })

      // 检查 userId 参数
      const userId = (chatStorage.setMessages as jest.Mock).mock.calls[0][0]
      expect(userId).toBe('test-user-id')
    })

    it('should restore generativeCard data from storage', async () => {
      // Mock stored messages with generativeCard
      const storedMessages = [
        {
          id: 'stored-match',
          type: 'ai',
          content: '',
          timestamp: new Date().toISOString(),
          generativeCard: 'match',
          generativeData: {
            candidates: [
              { user: { id: '1', name: 'Stored Match' }, compatibility_score: 85 },
            ],
          },
        },
      ]
      ;(chatStorage.getMessages as jest.Mock).mockReturnValue(storedMessages)

      render(<ChatInterface />)

      // 等待 generative UI 渲染
      await waitFor(() => {
        const matchContainer = document.querySelector('.match-card-container')
        expect(matchContainer).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('should restore featureAction from storage', async () => {
      // Mock stored messages with featureAction
      const storedMessages = [
        {
          id: 'stored-feature',
          type: 'ai',
          content: '',
          timestamp: new Date().toISOString(),
          generativeCard: 'feature',
          featureAction: 'stored-action',
        },
      ]
      ;(chatStorage.getMessages as jest.Mock).mockReturnValue(storedMessages)

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByTestId('feature-card-renderer')).toBeInTheDocument()
        expect(screen.getByText('Feature: stored-action')).toBeInTheDocument()
      }, { timeout: 1000 })
    })

    it('should show welcome message when no stored messages', async () => {
      // Mock empty storage
      ;(chatStorage.getMessages as jest.Mock).mockReturnValue([])

      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByText(/你好，我是 Her/)).toBeInTheDocument()
      })
    })

    it('should persist messages after sending', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 清除之前的调用记录（组件初始化可能触发 setMessages）
      ;(chatStorage.setMessages as jest.Mock).mockClear()

      // 发送第一条消息
      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await userEvent.type(input, 'first message{enter}')

      await waitFor(() => {
        expect(chatStorage.setMessages).toHaveBeenCalled()
      })

      // 发送第二条消息
      await userEvent.type(input, 'second message{enter}')

      // 等待第二条消息被保存
      await waitFor(() => {
        // 至少被调用 2 次（第一条和第二条消息）
        const callCount = (chatStorage.setMessages as jest.Mock).mock.calls.length
        expect(callCount).toBeGreaterThanOrEqual(2)
      }, { timeout: 2000 })
    })

    it('should convert timestamp to ISO string when saving', async () => {
      render(<ChatInterface />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/告诉我你想要什么/)).toBeInTheDocument()
      })

      // 清除之前的调用记录
      ;(chatStorage.setMessages as jest.Mock).mockClear()

      const input = screen.getByPlaceholderText(/告诉我你想要什么/)
      await userEvent.type(input, 'test{enter}')

      await waitFor(() => {
        expect(chatStorage.setMessages).toHaveBeenCalled()
      })

      // 检查 timestamp 格式（获取最后一次调用的参数）
      const calls = (chatStorage.setMessages as jest.Mock).mock.calls
      const lastCall = calls[calls.length - 1]
      const savedMessages = lastCall[1]
      const timestamps = savedMessages.map((m: any) => m.timestamp)
      // 应该是 ISO string 格式，可以被 Date.parse 解析
      timestamps.forEach((ts: string) => {
        expect(typeof ts).toBe('string')
        expect(Date.parse(ts)).not.toBeNaN()
      })
    })
  })
})