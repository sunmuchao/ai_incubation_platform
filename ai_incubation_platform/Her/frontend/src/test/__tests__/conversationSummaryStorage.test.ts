/**
 * conversationSummaryStorage 模块测试
 *
 * 覆盖内容：
 * 1. 基本读写与用户隔离
 * 2. 排序与数量上限
 * 3. upsert 行为
 * 4. TTL 过期清理（读时清理）
 * 5. TTL 配置边界（最小/最大/非法值）
 */

import { conversationSummaryStorage, type ConversationSummary } from '../../utils/storage'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
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

const mkConv = (id: string, minutesAgo: number, unread = 0): ConversationSummary => ({
  id,
  user_id_1: 'u1',
  user_id_2: `u2-${id}`,
  last_message_preview: `msg-${id}`,
  last_message_at: new Date(Date.now() - minutesAgo * 60 * 1000).toISOString(),
  unread_count: unread,
})

describe('conversationSummaryStorage', () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  it('saves and retrieves conversations', () => {
    conversationSummaryStorage.setConversations('u1', [mkConv('c1', 1), mkConv('c2', 2)])
    const rows = conversationSummaryStorage.getConversations('u1')
    expect(rows).toHaveLength(2)
    expect(rows[0].id).toBe('c1')
    expect(rows[1].id).toBe('c2')
  })

  it('isolates conversations by user', () => {
    conversationSummaryStorage.setConversations('u1', [mkConv('c1', 1)])
    conversationSummaryStorage.setConversations('u2', [mkConv('c2', 1)])
    expect(conversationSummaryStorage.getConversations('u1').map((x) => x.id)).toEqual(['c1'])
    expect(conversationSummaryStorage.getConversations('u2').map((x) => x.id)).toEqual(['c2'])
  })

  it('sorts by last_message_at desc and keeps max 50', () => {
    const rows: ConversationSummary[] = []
    for (let i = 0; i < 80; i++) {
      rows.push(mkConv(`c${i}`, i))
    }
    conversationSummaryStorage.setConversations('u1', rows)
    const stored = conversationSummaryStorage.getConversations('u1')
    expect(stored).toHaveLength(50)
    // 最新应该在前
    expect(stored[0].id).toBe('c0')
  })

  it('upsert inserts new conversation', () => {
    conversationSummaryStorage.upsertConversation('u1', mkConv('c1', 5))
    const rows = conversationSummaryStorage.getConversations('u1')
    expect(rows).toHaveLength(1)
    expect(rows[0].id).toBe('c1')
    expect(rows[0].last_sync_at).toBeTruthy()
  })

  it('upsert updates existing conversation fields', () => {
    conversationSummaryStorage.setConversations('u1', [mkConv('c1', 10, 0)])
    conversationSummaryStorage.upsertConversation('u1', {
      ...mkConv('c1', 1, 3),
      last_message_preview: 'new-msg',
    })
    const rows = conversationSummaryStorage.getConversations('u1')
    expect(rows).toHaveLength(1)
    expect(rows[0].last_message_preview).toBe('new-msg')
    expect(rows[0].unread_count).toBe(3)
  })

  it('filters expired rows by TTL and writes back cleaned result', () => {
    conversationSummaryStorage.setCacheTtlHours(24)
    const now = Date.now()
    const fresh: ConversationSummary = {
      ...mkConv('fresh', 1),
      last_sync_at: new Date(now - 2 * 60 * 60 * 1000).toISOString(),
    }
    const expired: ConversationSummary = {
      ...mkConv('expired', 1),
      last_sync_at: new Date(now - 30 * 60 * 60 * 1000).toISOString(),
    }
    conversationSummaryStorage.setConversations('u1', [expired, fresh])
    const rows = conversationSummaryStorage.getConversations('u1')
    expect(rows.map((r) => r.id)).toEqual(['fresh'])
  })

  it('falls back to default TTL when configured value invalid', () => {
    localStorageMock.setItem('chat_conversation_ttl_hours', 'invalid')
    expect(conversationSummaryStorage.getCacheTtlHours()).toBe(24)
  })

  it('clamps TTL to min and max bounds', () => {
    conversationSummaryStorage.setCacheTtlHours(-5)
    expect(conversationSummaryStorage.getCacheTtlHours()).toBe(1)
    conversationSummaryStorage.setCacheTtlHours(9999)
    expect(conversationSummaryStorage.getCacheTtlHours()).toBe(24 * 14)
  })

  it('clears conversations for target user only', () => {
    conversationSummaryStorage.setConversations('u1', [mkConv('c1', 1)])
    conversationSummaryStorage.setConversations('u2', [mkConv('c2', 1)])
    conversationSummaryStorage.clearConversations('u1')
    expect(conversationSummaryStorage.getConversations('u1')).toEqual([])
    expect(conversationSummaryStorage.getConversations('u2')).toHaveLength(1)
  })
})

