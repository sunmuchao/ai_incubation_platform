/**
 * Generative UI 组件库 - 模块化导出
 *
 * AI Native 设计原则:
 * 1. 界面由 AI 动态生成，而非固定布局
 * 2. 根据任务类型/用户意图动态重组
 * 3. 可视化组件由 AI 选择并生成
 * 4. 支持所有 Agent Skills 的 UI 渲染
 */

// 类型导出
export * from './types'

// 匹配组件导出
export * from './MatchComponents'

// 礼物组件导出
export * from './GiftComponents'

// 约会组件导出
export * from './DateComponents'

// 安全组件导出
export * from './SafetyComponents'

// 共享组件导出
export * from './SharedComponents'

// 情感分析组件导出
export * from './EmotionComponents'

// 关系进展组件导出
export * from './RelationshipComponents'

// 聊天助手组件导出
export * from './ChatComponents'

// 话题建议与关系策展组件导出
export * from './TopicComponents'

// 教练与模拟组件导出
export * from './CoachingComponents'

// 活动准备与约会助手组件导出
export * from './PrepComponents'

// 仪表板组件导出
export * from './DashboardComponents'

// 关系趋势组件导出
export * from './TrendComponents'

// 注：GenerativeUIRenderer 已废弃
// 原因：GenerativeUI.tsx 文件不存在，导出会导致运行时错误
// 替代方案：直接使用 ChatInterface.tsx 中的动态渲染逻辑
// export { GenerativeUIRenderer } from '../GenerativeUI'
// export { default as GenerativeUIRendererDefault } from '../GenerativeUI'