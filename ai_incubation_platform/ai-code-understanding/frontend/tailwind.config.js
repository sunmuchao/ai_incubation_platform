/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Monochromatic 配色方案 - 深蓝灰色系
      colors: {
        // 主色系 - 深蓝灰
        base: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f1419',  // 主背景
          950: '#020617',
        },
        // 表面色
        surface: {
          DEFAULT: '#1a2332',
          light: '#232f3e',
          lighter: '#2d3a4a',
        },
        // 文本色
        text: {
          primary: '#e8ecf1',
          secondary: '#9aa8b8',
          muted: '#64748b',
          disabled: '#475569',
        },
        // 强调色 - 蓝色（不超过 10% 面积）
        accent: {
          DEFAULT: '#3d9cf5',
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // 状态色
        success: {
          DEFAULT: '#4caf50',
          glow: 'rgba(76, 175, 80, 0.3)',
        },
        warning: {
          DEFAULT: '#ff9800',
          glow: 'rgba(255, 152, 0, 0.3)',
        },
        error: {
          DEFAULT: '#f44336',
          glow: 'rgba(244, 67, 54, 0.3)',
        },
        // 边框色
        border: {
          light: 'rgba(255, 255, 255, 0.08)',
          medium: 'rgba(255, 255, 255, 0.12)',
          heavy: 'rgba(255, 255, 255, 0.16)',
        },
      },
      // 间距系统 - Bento Grid 比例
      spacing: {
        'xs': '0.25rem',    // 4px
        'sm': '0.5rem',     // 8px
        'md': '1rem',       // 16px
        'lg': '1.5rem',     // 24px
        'xl': '2rem',       // 32px
        '2xl': '3rem',      // 48px
        '3xl': '4rem',      // 64px
      },
      // Linear.app 风格阴影
      boxShadow: {
        'bento': '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',
        'bento-hover': '0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.12)',
        'bento-active': '0 0 0 1px rgba(61, 156, 245, 0.2), 0 4px 12px rgba(0, 0, 0, 0.08)',
        'glow-accent': '0 0 20px rgba(61, 156, 245, 0.15)',
        'glow-success': '0 0 20px rgba(76, 175, 80, 0.2)',
        'glow-error': '0 0 20px rgba(244, 67, 54, 0.2)',
        'inner-light': 'inset 0 1px 0 rgba(255, 255, 255, 0.06)',
      },
      // 圆角规范 - 8-12px 统一
      borderRadius: {
        'bento': '12px',
        'bento-sm': '8px',
        'bento-lg': '16px',
        'bento-xl': '20px',
      },
      // 背景模糊
      backdropBlur: {
        'xs': '2px',
        'bento': '8px',
      },
      // 动画
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'shimmer': 'shimmer 2s infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'bounce-slow': 'bounce 2s infinite',
        'spin-slow': 'spin 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      // 渐变
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'bento-card': 'linear-gradient(135deg, rgba(26, 35, 50, 0.8) 0%, rgba(35, 47, 62, 0.6) 100%)',
        'bento-card-hover': 'linear-gradient(135deg, rgba(26, 35, 50, 1) 0%, rgba(35, 47, 62, 0.8) 100%)',
        'shimmer': 'linear-gradient(90deg, #1a2332 0%, #232f3e 50%, #1a2332 100%)',
        'accent-glow': 'linear-gradient(135deg, rgba(61, 156, 245, 0.15) 0%, rgba(61, 156, 245, 0.05) 100%)',
      },
      // 过渡
      transitionTimingFunction: {
        'bento': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'smooth': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
      },
      transitionDuration: {
        '150': '150ms',
        '200': '200ms',
        '300': '300ms',
        '400': '400ms',
        '500': '500ms',
      },
      // 字体
      fontFamily: {
        sans: ['SF Pro Text', 'PingFang SC', 'Microsoft YaHei', 'system-ui', 'sans-serif'],
        mono: ['Consolas', 'Monaco', 'Fira Code', 'monospace'],
      },
      // 字体大小
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }], // 10px
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      // 字重
      fontWeight: {
        'normal': 400,
        'medium': 500,
        'semibold': 600,
        'bold': 700,
      },
      // 透明度
      opacity: {
        '2.5': '0.025',
        '7.5': '0.075',
        '12.5': '0.125',
      },
      // 边框宽度
      borderWidth: {
        '3': '3px',
      },
    },
  },
  plugins: [],
};
