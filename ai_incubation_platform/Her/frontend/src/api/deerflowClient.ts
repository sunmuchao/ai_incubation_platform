/**
 * DeerFlow Client for Her Frontend
 *
 * 提供直接调用 DeerFlow Agent 的接口，替代原有的 skillClient。
 *
 * 设计原则（AI Native）：
 * - DeerFlow 是 Agent 运行时，负责意图识别、工具编排、状态管理
 * - Her 只提供业务 Tools（匹配、关系分析、约会策划等）
 * - 返回结构化数据，前端根据 component_type 动态渲染
 *
 * 使用方式：
 *   import { deerflowClient } from './deerflowClient';
 *   const response = await deerflowClient.chat("帮我找对象", threadId);
 */

import { authStorage } from '../utils/storage';

const API_BASE_URL = '/api';

// 获取认证头
const getAuthHeaders = (): Record<string, string> => {
  const token = authStorage.getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
};

// 获取用户 ID
const getUserId = (): string => {
  const user = authStorage.getUser();
  return user?.id || 'user-anonymous-dev';
};

/**
 * DeerFlow 响应类型
 */
export interface DeerFlowResponse {
  success: boolean;
  ai_message: string;
  intent?: {
    type: string;
    confidence: number;
  };
  generative_ui?: GenerativeUI;
  suggested_actions?: Array<{
    label: string;
    action: string;
  }>;
  deerflow_used?: boolean;
  tool_result?: ToolResult;  // 工具返回的结构化数据
}

/**
 * Generative UI 类型
 */
export interface GenerativeUI {
  component_type: string;
  props: Record<string, any>;
}

/**
 * 工具返回的结构化数据
 */
export interface ToolResult {
  success: boolean;
  data: Record<string, any>;
  summary: string;
  error?: string;
}

/**
 * 匹配结果类型
 */
export interface MatchResult {
  user_id: string;
  name: string;
  age: number;
  location: string;
  score: number;
  interests: string[];
  reason: string;
}

/**
 * 兼容性分析结果类型
 */
export interface CompatibilityResult {
  overall_score: number;
  dimensions: Array<{
    name: string;
    score: number;
    description: string;
  }>;
  conflicts: string[];
  strengths: string[];
  recommendation: string;
}

/**
 * 约会方案类型
 */
export interface DatePlan {
  name: string;
  description: string;
  location: string;
  estimated_cost: string;
  duration: string;
  tips: string[];
}

/**
 * 破冰建议类型
 */
export interface Icebreaker {
  text: string;
  style: string;
  confidence: number;
}

/**
 * DeerFlow Stream Event
 */
export interface DeerFlowStreamEvent {
  type: 'values' | 'messages-tuple' | 'custom' | 'end';
  data: Record<string, any>;
}

/**
 * DeerFlow Client
 */
export const deerflowClient = {
  /**
   * 发送消息并获取响应
   *
   * @param message 用户消息
   * @param threadId 对话线程 ID（用于保持对话上下文）
   * @returns DeerFlow 响应
   */
  async chat(message: string, threadId?: string): Promise<DeerFlowResponse> {
    const userId = getUserId();
    const actualThreadId = threadId || `her-${userId}-${Date.now()}`;

    try {
      const response = await fetch(`${API_BASE_URL}/deerflow/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message,
          thread_id: actualThreadId,
          user_id: userId,
        }),
      });

      if (!response.ok) {
        throw new Error(`DeerFlow chat failed: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('DeerFlow client error:', error);
      // 降级到原有 skillClient
      return {
        success: false,
        ai_message: '抱歉，DeerFlow 服务暂时不可用，请稍后再试~',
        deerflow_used: false,
      };
    }
  },

  /**
   * 流式发送消息
   *
   * @param message 用户消息
   * @param threadId 对话线程 ID
   * @param onEvent 事件回调
   */
  async stream(
    message: string,
    threadId: string,
    onEvent: (event: DeerFlowStreamEvent) => void
  ): Promise<void> {
    const userId = getUserId();

    try {
      const response = await fetch(`${API_BASE_URL}/deerflow/stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message,
          thread_id: threadId,
          user_id: userId,
        }),
      });

      if (!response.ok) {
        throw new Error(`DeerFlow stream failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 事件
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('DeerFlow stream error:', error);
      onEvent({
        type: 'end',
        data: { error: 'Stream failed' },
      });
    }
  },

  /**
   * 同步用户画像到 DeerFlow Memory
   *
   * 将用户的年龄、性别、所在地、兴趣爱好等信息注入到 DeerFlow
   * 让 Agent 了解用户背景，做更精准的推荐
   *
   * @returns 同步的 facts 数量
   */
  async syncMemory(): Promise<{ success: boolean; facts_count: number; message: string }> {
    const userId = getUserId();

    try {
      const response = await fetch(`${API_BASE_URL}/deerflow/memory/sync`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        return {
          success: false,
          facts_count: 0,
          message: '同步失败',
        };
      }

      return await response.json();
    } catch (error) {
      console.error('Memory sync error:', error);
      return {
        success: false,
        facts_count: 0,
        message: '同步失败',
      };
    }
  },

  /**
   * 获取 DeerFlow 状态
   */
  async getStatus(): Promise<{
    available: boolean;
    path: string;
    config_path: string;
    config_exists: boolean;
    memory_enabled: boolean;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/deerflow/status`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        return {
          available: false,
          path: '',
          config_path: '',
          config_exists: false,
          memory_enabled: false,
        };
      }

      return await response.json();
    } catch (error) {
      return {
        available: false,
        path: '',
        config_path: '',
        config_exists: false,
        memory_enabled: false,
      };
    }
  },

  /**
   * 解析工具返回的结构化数据
   *
   * 根据 component_type 返回对应类型的数据
   */
  parseToolResult(response: DeerFlowResponse): {
    type: string;
    data: any;
  } | null {
    if (!response.tool_result?.success) {
      return null;
    }

    const data = response.tool_result.data;

    // 匹配结果
    if (data.matches || data.recommendations) {
      return {
        type: 'matches',
        data: {
          matches: (data.matches || data.recommendations) as MatchResult[],
          total: data.total,
        },
      };
    }

    // 兼容性分析
    if (data.overall_score && data.dimensions) {
      return {
        type: 'compatibility',
        data: data as CompatibilityResult,
      };
    }

    // 约会方案
    if (data.plans) {
      return {
        type: 'date_plans',
        data: {
          plans: data.plans as DatePlan[],
          best_pick: data.best_pick,
          tips: data.tips,
        },
      };
    }

    // 破冰建议
    if (data.icebreakers) {
      return {
        type: 'icebreakers',
        data: {
          icebreakers: data.icebreakers as Icebreaker[],
          best_pick: data.best_pick,
          tips: data.tips,
        },
      };
    }

    // 话题推荐
    if (data.topics) {
      return {
        type: 'topics',
        data: {
          topics: data.topics,
          total: data.total,
        },
      };
    }

    // 关系健康度
    if (data.health_score) {
      return {
        type: 'relationship_health',
        data: {
          health_score: data.health_score,
          strengths: data.strengths,
          issues: data.issues,
          suggestions: data.suggestions,
        },
      };
    }

    return null;
  },
};

export default deerflowClient;