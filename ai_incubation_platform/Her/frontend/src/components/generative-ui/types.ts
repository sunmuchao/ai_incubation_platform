/**
 * Generative UI 类型定义
 */

export interface GenerativeUIConfig {
  component_type: string
  props: Record<string, any>
}

export interface GenerativeUIProps {
  uiConfig: GenerativeUIConfig
  onAction?: (action: { type: string; payload?: any }) => void
}

// 通用 Action 类型
// 使用索引签名允许任意额外属性，适配各种组件场景（match, gift, plan, suggestion 等）
export type GenerativeAction = {
  type: string
  payload?: any
  [key: string]: any  // 允许任意额外属性
}