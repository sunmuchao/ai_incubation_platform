/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Monochromatic 深蓝灰配色方案
        mono: {
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
        // 主色调 - 深蓝
        primary: {
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
        // 强调色 - 少量点缀
        accent: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        // 暗色主题专用
        dark: {
          bg: '#0f1419',
          surface: '#1a2332',
          surface2: '#232f3e',
          card: '#1e293b',
          border: 'rgba(255, 255, 255, 0.08)',
        }
      },
      // Bento Grid 间距系统
      spacing: {
        'bento-xs': '4px',
        'bento-sm': '8px',
        'bento-md': '12px',
        'bento-lg': '16px',
        'bento-xl': '24px',
        'bento-2xl': '32px',
      },
      // Linear 风格阴影
      boxShadow: {
        'linear-sm': '0 1px 2px rgba(0, 0, 0, 0.04), 0 1px 4px rgba(0, 0, 0, 0.04)',
        'linear-md': '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',
        'linear-lg': '0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.12)',
        'linear-xl': '0 4px 8px rgba(0, 0, 0, 0.08), 0 16px 48px rgba(0, 0, 0, 0.12)',
        'bento': '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',
        'bento-hover': '0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.12)',
      },
      // 统一圆角
      borderRadius: {
        'bento': '12px',
        'bento-sm': '8px',
        'bento-lg': '16px',
        'bento-xl': '20px',
      },
      // 动画
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'bounce-slow': 'bounce 3s infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      // Bento Grid 列配置
      gridTemplateColumns: {
        'bento-1': 'repeat(1, minmax(0, 1fr))',
        'bento-2': 'repeat(2, minmax(0, 1fr))',
        'bento-3': 'repeat(3, minmax(0, 1fr))',
        'bento-4': 'repeat(4, minmax(0, 1fr))',
        'bento-5': 'repeat(5, minmax(0, 1fr))',
        'bento-6': 'repeat(6, minmax(0, 1fr))',
      },
      // Bento Grid 行高
      gridRow: {
        'span-2': 'span 2 / span 2',
        'span-3': 'span 3 / span 3',
      },
      // Bento Grid 列跨度
      gridColumn: {
        'span-2': 'span 2 / span 2',
        'span-3': 'span 3 / span 3',
        'span-4': 'span 4 / span 4',
      },
    },
  },
  plugins: [],
}
