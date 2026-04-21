import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
/** Her 仓库根目录下的 static（与 FastAPI app.mount("/static") 一致） */
const HER_STATIC_ROOT = path.resolve(__dirname, '../static')

/**
 * 开发态直接提供 /static/*，避免仅开 Vite 时 /static/avatars 404；
 * 构建时复制到 dist/static，保证纯静态部署也能加载默认头像。
 */
function herStaticAssetsPlugin(): Plugin {
  return {
    name: 'her-static-assets',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.method !== 'GET' && req.method !== 'HEAD') {
          next()
          return
        }
        const raw = (req.url || '').split('?')[0]
        if (!raw.startsWith('/static/')) {
          next()
          return
        }
        const rel = raw.replace(/^\/static\/?/, '')
        if (!rel || rel.includes('..')) {
          next()
          return
        }
        const file = path.join(HER_STATIC_ROOT, rel)
        if (!file.startsWith(path.resolve(HER_STATIC_ROOT))) {
          next()
          return
        }
        fs.stat(file, (err, st) => {
          if (err || !st.isFile()) {
            next()
            return
          }
          const ext = path.extname(file).toLowerCase()
          const ct =
            ext === '.svg'
              ? 'image/svg+xml'
              : ext === '.png'
                ? 'image/png'
                : ext === '.jpg' || ext === '.jpeg'
                  ? 'image/jpeg'
                  : 'application/octet-stream'
          res.setHeader('Content-Type', ct)
          if (req.method === 'HEAD') {
            res.end()
            return
          }
          fs.createReadStream(file).pipe(res)
        })
      })
    },
    writeBundle() {
      if (!fs.existsSync(HER_STATIC_ROOT)) return
      const outDir = path.resolve(__dirname, 'dist/static')
      fs.mkdirSync(outDir, { recursive: true })
      fs.cpSync(HER_STATIC_ROOT, outDir, { recursive: true })
    },
  }
}

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
    herStaticAssetsPlugin(),
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
        // 默认头像数量多，不必全部预缓存进 SW（仍可按 URL 网络加载）
        globIgnores: ['**/static/avatars/**'],
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
      // 用户头像等若走后端静态路径，与 dev 插件互补（插件优先处理 /static）
      '/static': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3005,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        ws: true,
      },
      '/static': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
})
