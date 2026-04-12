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
export type GenerativeAction = {
  type: string
  payload?: any
}