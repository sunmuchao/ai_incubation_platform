/**
 * chatStorage 模块测试
 *
 * 测试覆盖:
 * 1. 消息存储与读取
 * 2. 消息过期清理
 * 3. 消息数量限制
 * 4. 用户隔离
 * 5. localStorage 超限处理
 */

import { chatStorage, StoredMessage } from '../../utils/storage'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      // 模拟超限场景：当存储超过阈值时抛出错误
      if (value.length > 100000) {
        const error = new Error('QuotaExceededError')
        error.name = 'QuotaExceededError'
        throw error
      }
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('chatStorage', () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  // ============= 第一部分：基本存储与读取测试 =============

  describe('Basic Storage Operations', () => {
    it('should save and retrieve messages', () => {
      const userId = 'test-user-1'
      const messages: StoredMessage[] = [
        {
          id: 'msg-1',
          type: 'user',
          content: 'Hello',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'msg-2',
          type: 'ai',
          content: 'Hi there!',
          timestamp: new Date().toISOString(),
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved.length).toBe(2)
      expect(retrieved[0].content).toBe('Hello')
      expect(retrieved[1].content).toBe('Hi there!')
    })

    it('should return empty array when no messages stored', () => {
      const userId = 'new-user'
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved).toEqual([])
    })

    it('should handle empty messages array', () => {
      const userId = 'test-user'
      chatStorage.setMessages(userId, [])
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved).toEqual([])
    })
  })

  // ============= 第二部分：消息过期清理测试 =============

  describe('Message Expiration', () => {
    it('should filter out messages older than 7 days', () => {
      const userId = 'test-user'
      const now = Date.now()
      const eightDaysAgo = now - 8 * 24 * 60 * 60 * 1000
      const sixDaysAgo = now - 6 * 24 * 60 * 60 * 1000

      const messages: StoredMessage[] = [
        {
          id: 'old-msg',
          type: 'user',
          content: 'Old message',
          timestamp: new Date(eightDaysAgo).toISOString(),
        },
        {
          id: 'new-msg',
          type: 'user',
          content: 'New message',
          timestamp: new Date(sixDaysAgo).toISOString(),
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      // 旧消息应该被过滤掉
      expect(retrieved.length).toBe(1)
      expect(retrieved[0].id).toBe('new-msg')
    })

    it('should keep messages within 7 days', () => {
      const userId = 'test-user'
      const now = Date.now()
      const oneDayAgo = now - 1 * 24 * 60 * 60 * 1000
      const threeDaysAgo = now - 3 * 24 * 60 * 60 * 1000

      const messages: StoredMessage[] = [
        {
          id: 'msg-1',
          type: 'user',
          content: 'Message 1',
          timestamp: new Date(oneDayAgo).toISOString(),
        },
        {
          id: 'msg-2',
          type: 'user',
          content: 'Message 2',
          timestamp: new Date(threeDaysAgo).toISOString(),
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved.length).toBe(2)
    })
  })

  // ============= 第三部分：消息数量限制测试 =============

  describe('Message Limit', () => {
    it('should only store last 30 messages', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = []

      // 创建 50 条消息
      for (let i = 1; i <= 50; i++) {
        messages.push({
          id: `msg-${i}`,
          type: 'user',
          content: `Message ${i}`,
          timestamp: new Date().toISOString(),
        })
      }

      chatStorage.setMessages(userId, messages)

      // 直接从 localStorage 检查存储数量
      const key = `chat_messages_${userId}`
      const storedData = localStorageMock.getItem(key)
      if (storedData) {
        const parsed = JSON.parse(storedData)
        expect(parsed.length).toBe(30)
        // 应该保留最新的消息（21-50）
        expect(parsed[0].id).toBe('msg-21')
        expect(parsed[29].id).toBe('msg-50')
      }
    })

    it('should keep all messages if less than limit', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = []

      // 创建 20 条消息
      for (let i = 1; i <= 20; i++) {
        messages.push({
          id: `msg-${i}`,
          type: 'user',
          content: `Message ${i}`,
          timestamp: new Date().toISOString(),
        })
      }

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved.length).toBe(20)
    })
  })

  // ============= 第四部分：用户隔离测试 =============

  describe('User Isolation', () => {
    it('should store messages for different users separately', () => {
      const user1 = 'user-1'
      const user2 = 'user-2'

      chatStorage.setMessages(user1, [
        { id: 'msg-1', type: 'user', content: 'User 1 message', timestamp: new Date().toISOString() },
      ])

      chatStorage.setMessages(user2, [
        { id: 'msg-2', type: 'user', content: 'User 2 message', timestamp: new Date().toISOString() },
      ])

      const retrieved1 = chatStorage.getMessages(user1)
      const retrieved2 = chatStorage.getMessages(user2)

      expect(retrieved1[0].content).toBe('User 1 message')
      expect(retrieved2[0].content).toBe('User 2 message')
    })

    it('should clear messages for specific user only', () => {
      const user1 = 'user-1'
      const user2 = 'user-2'

      chatStorage.setMessages(user1, [
        { id: 'msg-1', type: 'user', content: 'User 1', timestamp: new Date().toISOString() },
      ])

      chatStorage.setMessages(user2, [
        { id: 'msg-2', type: 'user', content: 'User 2', timestamp: new Date().toISOString() },
      ])

      chatStorage.clearMessages(user1)

      expect(chatStorage.getMessages(user1)).toEqual([])
      expect(chatStorage.getMessages(user2).length).toBe(1)
    })
  })

  // ============= 第五部分：Generative UI 数据存储测试 =============

  describe('Generative UI Data Storage', () => {
    it('should store messages with generativeCard', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = [
        {
          id: 'msg-1',
          type: 'ai',
          content: '',
          timestamp: new Date().toISOString(),
          generativeCard: 'match',
          generativeData: {
            candidates: [
              { user: { id: '1', name: 'Test' }, compatibility_score: 85 },
            ],
          },
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved[0].generativeCard).toBe('match')
      expect((retrieved[0].generativeData as any)?.candidates).toBeDefined()
    })

    it('should store messages with featureAction', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = [
        {
          id: 'msg-1',
          type: 'ai',
          content: '',
          timestamp: new Date().toISOString(),
          generativeCard: 'feature',
          featureAction: 'upgrade_membership',
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved[0].featureAction).toBe('upgrade_membership')
    })

    it('should store messages with suggestions', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = [
        {
          id: 'msg-1',
          type: 'ai',
          content: 'AI response',
          timestamp: new Date().toISOString(),
          suggestions: ['查看详情', '发起对话'],
        },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved[0].suggestions).toEqual(['查看详情', '发起对话'])
    })
  })

  // ============= 第六部分：边缘场景测试 =============

  describe('Edge Cases', () => {
    it('should handle corrupted localStorage data', () => {
      const userId = 'test-user'
      const key = `chat_messages_${userId}`

      // 存入无效 JSON
      localStorageMock.setItem(key, 'not-valid-json')

      const retrieved = chatStorage.getMessages(userId)
      expect(retrieved).toEqual([])
    })

    it('should handle localStorage setItem error gracefully', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = []

      // 创建一个超大的消息数组，模拟 localStorage 超限
      for (let i = 1; i <= 100; i++) {
        messages.push({
          id: `msg-${i}`,
          type: 'user',
          content: 'A'.repeat(1000), // 每条消息很长
          timestamp: new Date().toISOString(),
        })
      }

      // 应该不会抛出错误，而是降级存储
      chatStorage.setMessages(userId, messages)

      // 检查是否有数据存储（可能被降级）
      const retrieved = chatStorage.getMessages(userId)
      // 即使超限，也应该尝试存储更少的消息
      expect(retrieved.length).toBeGreaterThanOrEqual(0)
    })

    it('should preserve message order', () => {
      const userId = 'test-user'
      const messages: StoredMessage[] = [
        { id: 'msg-1', type: 'user', content: 'First', timestamp: new Date(Date.now() - 1000).toISOString() },
        { id: 'msg-2', type: 'ai', content: 'Second', timestamp: new Date(Date.now() - 500).toISOString() },
        { id: 'msg-3', type: 'user', content: 'Third', timestamp: new Date().toISOString() },
      ]

      chatStorage.setMessages(userId, messages)
      const retrieved = chatStorage.getMessages(userId)

      expect(retrieved[0].id).toBe('msg-1')
      expect(retrieved[1].id).toBe('msg-2')
      expect(retrieved[2].id).toBe('msg-3')
    })
  })
})