import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppRouter from './router'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#10b981',
          borderRadius: 8,
        },
        components: {
          Layout: {
            headerBg: '#ffffff',
            headerHeight: 64,
          },
          Menu: {
            darkItemBg: '#1f2937',
            darkItemSelectedBg: '#10b981',
          },
        },
      }}
    >
      <AppRouter />
    </ConfigProvider>
  </React.StrictMode>,
)
