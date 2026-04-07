/**
 * Design Tokens for Bento Grid & Monochromatic Theme
 * 基于 Linear.app 风格的精致设计系统
 */

// ============================================================================
// 颜色系统 - Monochromatic 深蓝色系
// ============================================================================
export const colors = {
  // 主色调 - 深蓝灰色系
  primary: {
    50: '#f0f4f8',
    100: '#d9e2ec',
    200: '#bcccdc',
    300: '#9fb3c8',
    400: '#829ab1',
    500: '#627d98',
    600: '#486581',
    700: '#334e68',
    800: '#243b53',
    900: '#102a43',
  },

  // 中性色 - 用于背景和边框
  neutral: {
    0: '#ffffff',
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },

  // 暗色模式专用背景
  dark: {
    bg: '#0a0a0f',
    bgElevated: '#12121a',
    bgCard: '#1a1a25',
    bgCardHover: '#222230',
    border: 'rgba(255, 255, 255, 0.08)',
    borderHover: 'rgba(255, 255, 255, 0.12)',
  },

  // 功能色
  semantic: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    accent: '#8b5cf6', // 紫色强调色
  },
};

// ============================================================================
// 阴影系统 - Linear.app 风格精致阴影
// ============================================================================
export const shadows = {
  // 轻微阴影 - 用于卡片
  card: '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',

  // 悬浮阴影
  cardHover: '0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.12)',

  // 强调阴影
  elevated: '0 4px 8px rgba(0, 0, 0, 0.08), 0 16px 48px rgba(0, 0, 0, 0.16)',

  // 光晕效果 - 用于强调元素
  glow: '0 0 20px rgba(99, 102, 241, 0.3)',
  glowSuccess: '0 0 20px rgba(16, 185, 129, 0.3)',
  glowWarning: '0 0 20px rgba(245, 158, 11, 0.3)',
  glowError: '0 0 20px rgba(239, 68, 68, 0.3)',

  // 内阴影 - 用于凹陷效果
  inner: 'inset 0 1px 2px rgba(0, 0, 0, 0.12)',
};

// ============================================================================
// 圆角系统 - 统一 8-12px 圆角
// ============================================================================
export const radii = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
};

// ============================================================================
// 间距系统 - 基于 4px 网格
// ============================================================================
export const spacing = {
  0: '0',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  7: '28px',
  8: '32px',
  9: '36px',
  10: '40px',
  11: '44px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
};

// ============================================================================
// Bento Grid 布局配置
// ============================================================================
export const bentoGrid = {
  // 卡片尺寸比例
  sizes: {
    small: { width: '1fr', height: 'auto' },
    medium: { width: '2fr', height: 'auto' },
    large: { width: '2fr', height: '2fr' },
    xl: { width: '4fr', height: 'auto' },
    full: { width: '100%', height: 'auto' },
  },

  // 网格间距
  gap: {
    sm: '12px',
    md: '16px',
    lg: '24px',
  },

  // 最小卡片尺寸
  cardMinWidth: '280px',
  cardMinHeight: '160px',
};

// ============================================================================
// 字体系统
// ============================================================================
export const typography = {
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", monospace',
  },

  fontSize: {
    xs: '11px',
    sm: '12px',
    base: '13px',
    lg: '14px',
    xl: '16px',
    '2xl': '18px',
    '3xl': '20px',
    '4xl': '24px',
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
};

// ============================================================================
// 动画和过渡
// ============================================================================
export const transitions = {
  durations: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
  },

  timing: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

export default {
  colors,
  shadows,
  radii,
  spacing,
  bentoGrid,
  typography,
  transitions,
};
