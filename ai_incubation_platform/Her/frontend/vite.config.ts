import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // 🚀 [性能优化] build 配置 - 拆分大型第三方库
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Ant Design 组件库单独打包
          'antd': ['antd'],
          // React 核心库
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // 国际化
          'i18n': ['i18next', 'react-i18next'],
          // HTTP 请求库
          'axios': ['axios'],
        },
      },
    },
    // 提高 chunk 大小警告阈值，因为 antd 本身就很大
    chunkSizeWarningLimit: 600,
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.svg'],
      manifest: {
        name: 'Her - AI 情感顾问',
        short_name: 'Her',
        description: '你的 AI 情感顾问和关系教练',
        theme_color: '#FDFBFD',
        background_color: '#FDFBFD',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        id: '/',
        icons: [
          {
            src: 'favicon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any'
          },
          {
            src: 'apple-touch-icon.svg',
            sizes: '180x180',
            type: 'image/svg+xml',
            purpose: 'any'
          }
        ],
        ios: {
          safari_web_app_capable: 'yes',
          status_bar_style: 'default'
        }
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    })
  ],
  server: {
    host: '0.0.0.0',
    port: 3005,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',  // Her 后端端口（与 .env SERVER_PORT 一致）
        changeOrigin: true,
        ws: true,  // 启用 WebSocket 代理
      },
    },
  },
})
