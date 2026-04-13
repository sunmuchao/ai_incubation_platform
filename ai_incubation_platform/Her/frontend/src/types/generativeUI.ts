/**
 * Generative UI Schema - 前后端共享映射定义
 *
 * 这个文件定义了所有 Generative UI 组件的映射关系。
 * 必须与后端 generative_ui_schema.py 保持同步。
 *
 * 维护规则：
 * 1. 新增组件必须在此注册
 * 2. backend_type 必须与后端一致
 * 3. frontend_card 必须与 ChatInterface.tsx 中的 generativeCard 类型一致
 */

/**
 * 组件 Schema 定义
 */
export interface ComponentSchema {
  backend_type: string       // 后端返回的 component_type
  frontend_card: string | null  // 前端对应的 generativeCard 值
  required_props: string[]   // 必填 props
  description: string        // 组件描述
}

/**
 * Generative UI Schema 映射表
 *
 * key: backend_type（后端返回的 component_type）
 */
export const GENERATIVE_UI_SCHEMA: Record<string, ComponentSchema> = {
  // ===== 匹配相关 =====
  MatchCardList: {
    backend_type: 'MatchCardList',
    frontend_card: 'match',
    required_props: ['matches'],
    description: '匹配结果列表，展示候选人卡片',
  },
  DailyRecommendCard: {
    backend_type: 'DailyRecommendCard',
    frontend_card: 'match',
    required_props: ['matches', 'is_daily'],
    description: '每日推荐卡片',
  },

  // ===== 信息收集 =====
  ProfileQuestionCard: {
    backend_type: 'ProfileQuestionCard',
    frontend_card: 'profile_question',
    required_props: ['question', 'question_type', 'options', 'dimension'],
    description: '用户画像问题卡片',
  },
  QuickStartCard: {
    backend_type: 'QuickStartCard',
    frontend_card: 'quick_start',
    required_props: ['question', 'question_type', 'options', 'dimension'],
    description: '快速入门问题卡片（本地处理）',
  },

  // ===== 预沟通相关 =====
  PreCommunicationPanel: {
    backend_type: 'PreCommunicationPanel',
    frontend_card: 'precommunication',
    required_props: ['sessions'],
    description: 'AI 预沟通会话列表',
  },
  PreCommunicationDialog: {
    backend_type: 'PreCommunicationDialog',
    frontend_card: 'precommunication-dialog',
    required_props: ['messages'],
    description: 'AI 预沟通对话历史',
  },

  // ===== 约会相关 =====
  DatePlanCard: {
    backend_type: 'DatePlanCard',
    frontend_card: 'feature',
    required_props: ['plans'],
    description: '约会方案卡片',
  },
  DateSuggestionCard: {
    backend_type: 'DateSuggestionCard',
    frontend_card: 'feature',
    required_props: ['suggestions'],
    description: '约会建议卡片',
  },

  // ===== 分析相关 =====
  CompatibilityChart: {
    backend_type: 'CompatibilityChart',
    frontend_card: 'analysis',
    required_props: ['overall_score', 'dimensions'],
    description: '兼容性分析图表',
  },
  RelationshipHealthCard: {
    backend_type: 'RelationshipHealthCard',
    frontend_card: 'analysis',
    required_props: ['health_score'],
    description: '关系健康度卡片',
  },
  RelationshipReportCard: {
    backend_type: 'RelationshipReportCard',
    frontend_card: 'analysis',
    required_props: ['report_data'],
    description: '关系分析报告',
  },

  // ===== 功能展示 =====
  CapabilityCard: {
    backend_type: 'CapabilityCard',
    frontend_card: 'feature',
    required_props: ['intro', 'features'],
    description: '能力介绍卡片',
  },
  TopicsCard: {
    backend_type: 'TopicsCard',
    frontend_card: 'feature',
    required_props: ['topics'],
    description: '话题推荐卡片',
  },
  IcebreakerCard: {
    backend_type: 'IcebreakerCard',
    frontend_card: 'feature',
    required_props: ['icebreakers'],
    description: '破冰建议卡片',
  },

  // ===== 简单响应 =====
  SimpleResponse: {
    backend_type: 'SimpleResponse',
    frontend_card: null,
    required_props: [],
    description: '简单文本响应',
  },
  AIResponseCard: {
    backend_type: 'AIResponseCard',
    frontend_card: null,
    required_props: [],
    description: 'AI 响应卡片（纯文本）',
  },

  // ===== 学习结果确认 =====
  LearningConfirmationCard: {
    backend_type: 'LearningConfirmationCard',
    frontend_card: 'learning_confirmation',
    required_props: ['insights'],
    description: 'AI 学习结果确认卡片（用户确认是否更新画像）',
  },
}

/**
 * 根据 backend_type 获取 frontend_card 值
 *
 * @param backendType 后端返回的 component_type
 * @returns 前端对应的 generativeCard 值，如果没有则返回 undefined
 */
export function getFrontendCard(backendType: string): string | null | undefined {
  const schema = GENERATIVE_UI_SCHEMA[backendType]
  return schema?.frontend_card
}

/**
 * 校验 props 是否满足必填要求
 *
 * @param backendType 后端返回的 component_type
 * @param props 实际传入的 props
 * @returns [是否有效, 缺失的 props 列表]
 */
export function validateProps(
  backendType: string,
  props: Record<string, unknown>
): [boolean, string[]] {
  const schema = GENERATIVE_UI_SCHEMA[backendType]
  if (!schema) {
    return [false, [`未知的 component_type: ${backendType}`]]
  }

  const required = schema.required_props
  const missing = required.filter(p => !(p in props))

  return [missing.length === 0, missing]
}

/**
 * 列出所有已注册的组件
 */
export function listAllComponents(): ComponentSchema[] {
  return Object.values(GENERATIVE_UI_SCHEMA)
}

export default GENERATIVE_UI_SCHEMA