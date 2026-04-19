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

import { getAuthHeaders, getCurrentUserId } from './apiClient'

const API_BASE_URL = '/api'

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
    const userId = getCurrentUserId()
    const actualThreadId = threadId || `her-${userId}-${Date.now()}`

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
    const userId = getCurrentUserId()

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
    const userId = getCurrentUserId()

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
   * 从 Agent 的 ai_message 中解析 JSON 代码块
   *
   * Agent Native 架构中，Agent 在 markdown 中输出结构化数据：
   * ```json
   * {"topics": [...]}
   * ```
   *
   * 此方法提取并解析这些 JSON 代码块
   */
  parseAgentJsonOutput(response: DeerFlowResponse): {
    type: string;
    data: any;
    natural_message: string;
  } | null {
    if (!response.ai_message) {
      return null;
    }

    // 提取 markdown JSON 代码块
    const jsonMatch = response.ai_message.match(/```json\s*([\s\S]*?)\s*```/);
    if (!jsonMatch) {
      return null;
    }

    try {
      const jsonData = JSON.parse(jsonMatch[1]);
      // 提取自然语言部分（JSON 代码块之前的内容）
      const naturalMessage = response.ai_message.split('```json')[0].trim();

      // 根据 JSON 结构判断类型
      if (jsonData.topics) {
        return {
          type: 'topics',
          data: {
            topics: jsonData.topics,
            total: jsonData.total,
            context_analysis: jsonData.context_analysis,
          },
          natural_message: naturalMessage,
        };
      }

      if (jsonData.icebreakers) {
        return {
          type: 'icebreakers',
          data: {
            icebreakers: jsonData.icebreakers,
            best_pick: jsonData.best_pick,
          },
          natural_message: naturalMessage,
        };
      }

      if (jsonData.plans) {
        return {
          type: 'date_plans',
          data: {
            plans: jsonData.plans,
            best_pick: jsonData.best_pick,
          },
          natural_message: naturalMessage,
        };
      }

      if (jsonData.matches) {
        return {
          type: 'matches',
          data: {
            matches: jsonData.matches,
            total: jsonData.total,
          },
          natural_message: naturalMessage,
        };
      }

      // 未知 JSON 结构，返回原始数据
      return {
        type: 'unknown',
        data: jsonData,
        natural_message: naturalMessage,
      };
    } catch (error) {
      console.error('Failed to parse Agent JSON output:', error);
      return null;
    }
  },

  /**
   * 🚀 [新增] 从 Agent 的 ai_message 中解析 [GENERATIVE_UI] 标签
   *
   * Agent 输出格式：
   * ```
   * [GENERATIVE_UI]
   * {"component_type": "UserProfileCard", "props": {...}}
   * [/GENERATIVE_UI]
   * ```
   *
   * 返回：
   * - natural_message: 纯文本部分（去掉标签后的内容）
   * - generative_ui_cards: 解析后的 UI 卡片数组
   */
  parseGenerativeUITags(response: DeerFlowResponse): {
    natural_message: string;
    generative_ui_cards: GenerativeUI[];
  } {
    if (!response.ai_message) {
      return { natural_message: '', generative_ui_cards: [] };
    }

    const message = response.ai_message;
    const cards: GenerativeUI[] = [];

    // 正则匹配 [GENERATIVE_UI]...[/GENERATIVE_UI] 标签
    const tagRegex = /\[GENERATIVE_UI\]\s*([\s\S]*?)\s*\[\/GENERATIVE_UI\]/g;
    let match;
    let cleanMessage = message;

    while ((match = tagRegex.exec(message)) !== null) {
      try {
        const cardJson = JSON.parse(match[1].trim());
        cards.push({
          component_type: cardJson.component_type || 'UserProfileCard',
          props: cardJson.props || cardJson,  // 支持 {component_type, props} 和直接 {name, age...}
        });
        // 从消息中移除标签
        cleanMessage = cleanMessage.replace(match[0], '');
      } catch (e) {
        console.warn('[parseGenerativeUITags] Failed to parse card JSON:', match[1], e);
      }
    }

    // 清理多余空行（保留单个换行）
    cleanMessage = cleanMessage.replace(/\n{3,}/g, '\n\n').trim();

    return {
      natural_message: cleanMessage,
      generative_ui_cards: cards,
    };
  },

  /**
   * 解析工具返回的结构化数据（兼容旧架构）
   *
   * 根据 component_type 返回对应类型的数据
   */
  parseToolResult(response: DeerFlowResponse): {
    type: string;
    data: any;
  } | null {
    // Agent Native 架构：优先从 ai_message 解析 JSON
    const agentOutput = this.parseAgentJsonOutput(response);
    if (agentOutput) {
      return {
        type: agentOutput.type,
        data: agentOutput.data,
      };
    }

    // 降级：从 tool_result.data 解析（兼容旧架构）
    if (!response.tool_result?.success) {
      return null;
    }

    const data = response.tool_result.data;

    // 匹配结果
    // Agent Native：兼容 candidates（工具返回）、matches、recommendations 三种字段名
    if (data.candidates || data.matches || data.recommendations) {
      return {
        type: 'matches',
        data: {
          // 字段名兼容：candidates → matches（统一为前端期望的字段名）
          matches: (data.candidates || data.matches || data.recommendations) as MatchResult[],
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

    // Agent Native：对话引导卡片（话题推荐、破冰建议）
    if (data.intent_type && data.component_type === 'ConversationGuideCard') {
      return {
        type: data.intent_type,  // 'topic_request' 或 'icebreaker_request'
        data: {
          intent_type: data.intent_type,
          user_profile: data.user_profile,
          target_profile: data.target_profile,
          selected_user: data.selected_user,
          match_points: data.match_points,
          analysis: data.analysis,
          conversation_history: data.conversation_history,
        },
      };
    }

    // 兼容性分析（Agent Native：comparison_factors）
    if (data.comparison_factors) {
      return {
        type: 'compatibility',
        data: {
          user_a: data.user_a,
          user_b: data.user_b,
          comparison_factors: data.comparison_factors,
        },
      };
    }

    // 用户画像查询
    if (data.user_profile && !data.target_profile) {
      return {
        type: 'user_profile',
        data: {
          user_profile: data.user_profile,
        },
      };
    }

    // 目标用户画像查询（UserProfileCard）
    if (data.selected_user || (data.user_profile && data.target_profile)) {
      return {
        type: 'target_user',
        data: {
          selected_user: data.selected_user || data.user_profile,
          user_profile: data.user_profile,
        },
      };
    }

    // 对话历史查询
    if (data.messages && data.silence_info) {
      return {
        type: 'conversation_history',
        data: {
          messages: data.messages,
          total: data.total,
          silence_info: data.silence_info,
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