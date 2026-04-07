import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import App from './App'
import i18n from './i18n'
import zhCN from 'antd/locale/zh_CN'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 分钟
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nextProvider i18n={i18n}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#3b82f6',
            borderRadius: 8,
            colorBgContainer: 'var(--color-bg-card)',
            colorText: 'var(--color-text-primary)',
          },
        }}
      >
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ConfigProvider>
    </I18nextProvider>
  </React.StrictMode>,
)
