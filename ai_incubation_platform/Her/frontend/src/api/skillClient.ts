/**
 * DeerFlow Skill Client
 *
 * 提供 Skill 元数据查询接口。
 *
 * **重要说明**：
 * - DeerFlow 的 Skill 是注入到 Agent system prompt 的能力描述
 * - Skill 执行通过 DeerFlow Agent 完成，不是独立的 REST API
 * - 前端应使用 deerflowClient.chat() 与 Agent 对话来触发 Skill
 *
 * 使用方式：
 *   // 查询 Skill 列表（调用 DeerFlow Gateway API）
 *   const skills = await skillRegistry.listSkills();
 *
 *   // 执行 Skill（通过 Agent 对话）
 *   const response = await deerflowClient.chat("帮我找对象", threadId);
 */

import { getAuthHeaders } from './apiClient'

const DEERFLOW_API_BASE_URL = '/api'

/**
 * Skill 元数据类型
 */
export interface SkillMetadata {
  name: string
  description: string
  license?: string
  category: string // 'public' | 'custom'
  enabled: boolean
}

/**
 * Skill 注册表客户端
 *
 * 调用 DeerFlow Gateway API 查询 Skill 元数据
 */
export const skillRegistry = {
  /**
   * 获取所有可用 Skill 列表
   *
   * 调用 DeerFlow Gateway: GET /api/skills
   */
  async listSkills(): Promise<SkillMetadata[]> {
    const response = await fetch(`${DEERFLOW_API_BASE_URL}/skills`, {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error('Failed to list skills')
    }

    const data = await response.json()
    return data.skills || []
  },

  /**
   * 获取 Skill 详细信息
   *
   * 调用 DeerFlow Gateway: GET /api/skills/{name}
   */
  async getSkillInfo(name: string): Promise<SkillMetadata> {
    const response = await fetch(`${DEERFLOW_API_BASE_URL}/skills/${name}`, {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error(`Skill not found: ${name}`)
    }

    return response.json()
  },

  /**
   * 启用/禁用 Skill
   *
   * 调用 DeerFlow Gateway: PUT /api/skills/{name}
   */
  async updateSkill(name: string, enabled: boolean): Promise<SkillMetadata> {
    const response = await fetch(`${DEERFLOW_API_BASE_URL}/skills/${name}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ enabled })
    })

    if (!response.ok) {
      throw new Error(`Failed to update skill: ${name}`)
    }

    return response.json()
  },

  /**
   * 获取自定义 Skill 内容
   *
   * 调用 DeerFlow Gateway: GET /api/skills/custom/{name}
   */
  async getCustomSkillContent(name: string): Promise<{ name: string; description: string; content: string }> {
    const response = await fetch(`${DEERFLOW_API_BASE_URL}/skills/custom/${name}`, {
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error(`Custom skill not found: ${name}`)
    }

    return response.json()
  }
}

/**
 * P0 Skills - 这些是 DeerFlow 已注册的 Skill 名称
 *
 * 前端不再硬编码执行逻辑，而是通过 Agent 对话触发。
 * Skill 定义见：Her/deerflow/skills/public/{skill_name}/SKILL.md
 *
 * 可用的 Her Skills:
 * - her_matchmaking - 匹配助手
 * - her_chat_assistant - 聊天助手
 * - her_date_planning - 约会策划
 * - her_relationship_coach - 关系教练
 *
 * 使用示例:
 *   // 通过 Agent 对话触发 Skill
 *   const response = await deerflowClient.chat("帮我找个爱旅行的人", threadId);
 *   // Agent 会自动识别意图并调用 her_matchmaking Skill 的工具
 */

// Skill 名称常量（用于日志、调试）
export const SKILL_NAMES = {
  MATCHMAKING: 'her_matchmaking',
  CHAT_ASSISTANT: 'her_chat_assistant',
  DATE_PLANNING: 'her_date_planning',
  RELATIONSHIP_COACH: 'her_relationship_coach',
} as const

export default skillRegistry