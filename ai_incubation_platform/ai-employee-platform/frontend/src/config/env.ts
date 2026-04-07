/**
 * 环境配置
 */
export const env = {
  // API 配置
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8003',

  // 应用配置
  APP_TITLE: import.meta.env.VITE_APP_TITLE || 'AI Employee Platform',
  APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',

  // 功能开关
  ENABLE_MOCK: import.meta.env.VITE_ENABLE_MOCK === 'true',
  ENABLE_DEVTOOLS: import.meta.env.VITE_ENABLE_DEVTOOLS !== 'false',

  // 认证配置
  TOKEN_KEY: import.meta.env.VITE_TOKEN_KEY || 'ai_employee_token',
  REFRESH_TOKEN_KEY: import.meta.env.VITE_REFRESH_TOKEN_KEY || 'ai_employee_refresh_token',

  // 分页配置
  DEFAULT_PAGE_SIZE: Number(import.meta.env.VITE_DEFAULT_PAGE_SIZE) || 20,
  PAGE_SIZE_OPTIONS: (import.meta.env.VITE_PAGE_SIZE_OPTIONS || '10,20,50,100').split(',').map(Number),

  // 开发环境判断
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
};
