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
        // 主色调：深蓝灰 (Slate)
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        // 强调色：靛蓝 (用于少量点缀)
        indigo: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        // 语义色
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
        info: '#3b82f6',
      },

      // Linear.app 风格阴影
      boxShadow: {
        // 精致细腻的阴影
        'linear-sm': '0 1px 2px rgba(0,0,0,0.04)',
        'linear': '0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.08)',
        'linear-md': '0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.12)',
        'linear-lg': '0 4px 16px rgba(0,0,0,0.08), 0 12px 32px rgba(0,0,0,0.16)',
        'linear-xl': '0 8px 24px rgba(0,0,0,0.12), 0 16px 48px rgba(0,0,0,0.20)',
        // 悬浮效果
        'float': '0 4px 12px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.02)',
        'float-hover': '0 8px 24px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04)',
        // 内阴影
        'inner-sm': 'inset 0 1px 2px rgba(0,0,0,0.04)',
        'inner': 'inset 0 2px 4px rgba(0,0,0,0.06)',
      },

      // 边框样式
      borderWidth: {
        'hairline': '0.5px',
      },

      // 圆角
      borderRadius: {
        'linear-sm': '6px',
        'linear': '8px',
        'linear-md': '10px',
        'linear-lg': '12px',
        'linear-xl': '16px',
      },

      // 动画
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },

      // 渐变
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'bento-highlight': 'linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%)',
      },

      // Bento Grid 布局相关
      gridTemplateColumns: {
        'bento-1': 'repeat(1, minmax(0, 1fr))',
        'bento-2': 'repeat(2, minmax(0, 1fr))',
        'bento-3': 'repeat(3, minmax(0, 1fr))',
        'bento-4': 'repeat(4, minmax(0, 1fr))',
        'bento-5': 'repeat(5, minmax(0, 1fr))',
      },
    },
  },
  plugins: [],
}
