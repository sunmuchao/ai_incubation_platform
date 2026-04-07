import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3009,
    proxy: {
      '/api': {
        target: 'http://localhost:8009',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      less: {
        javascriptEnabled: true,
        modifyVars: {
          // Bento Grid & Monochromatic Theme
          '@primary-color': '#627d98',
          '@body-background': '#0a0a0f',
          '@component-background': '#1a1a25',
          '@text-color': 'rgba(243, 244, 246, 0.85)',
          '@text-color-secondary': 'rgba(243, 244, 246, 0.45)',
          '@border-color-base': 'rgba(255, 255, 255, 0.08)',
          '@bg-color-base': '#12121a',
          '@border-radius-base': '8px',
          '@border-radius-lg': '12px',
          '@box-shadow': '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.08)',
          '@box-shadow-secondary': '0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.12)',
        },
      },
    },
  },
})
