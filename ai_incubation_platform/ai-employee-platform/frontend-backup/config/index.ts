/**
 * 配置导出
 */
export { env } from './env';

export const API_ENDPOINTS = {
  // 员工管理
  EMPLOYEES: '/api/employees',
  MARKETPLACE: '/api/marketplace',

  // 提案系统
  PROPOSALS: '/api/proposals',

  // 时间追踪
  TIME_TRACKING: '/api/time-tracking',

  // 托管支付
  ESCROW: '/api/escrow',

  // 消息系统
  MESSAGING: '/api/messaging',

  // 争议解决
  DISPUTES: '/api/disputes',

  // 文件服务
  FILES: '/api/files',

  // 可观测性
  OBSERVABILITY: '/api/observability',

  // 培训
  TRAINING: '/api/training',

  // 支付
  PAYMENT: '/api/payment',

  // 匹配
  MATCHING: '/api/matching',

  // 认证
  CERTIFICATIONS: '/api/certifications',

  // 培训效果
  TRAINING_EFFECTIVENESS: '/api/training-effectiveness',

  // 企业功能
  ENTERPRISE: '/api/enterprise',
  PERFORMANCE: '/api/performance',
  DEPARTMENTS: '/api/departments',
  WEBHOOKS: '/api/webhooks',

  // 钱包
  WALLET: '/api/wallet',

  // 能力图谱
  CAPABILITY_GRAPH: '/api/ai-capability-graph',

  // 工作流
  WORKFLOWS: '/api/workflows',

  // 远程工作
  REMOTE_WORK: '/api/remote-work',

  // 组织文化
  CULTURE: '/api/culture',

  // 职业发展
  CAREER_DEVELOPMENT: '/api/career-development',

  // 员工福祉
  WELLNESS: '/api/wellness',

  // 助手
  ASSISTANT: '/api/assistant',

  // 通用
  HEALTH: '/health',
  LOGIN: '/api/employees/auth/login',
};

export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  MESSAGE: 'message',
  NOTIFICATION: 'notification',
  ORDER_UPDATE: 'order_update',
  PROPOSAL_UPDATE: 'proposal_update',
};
