import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import App from './App'
import './styles/index.less'

// 国际化配置 - 必须在应用渲染前导入
import './locales/i18n'

// 移动端适配初始化
import { initIOSOptimizations } from './utils/iosUtils'

// 初始化移动端优化
initIOSOptimizations()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#667eea',
          colorBgBase: '#ffffff',
          colorBgContainer: '#ffffff',
          colorTextBase: '#333333',
          colorBorder: '#d9d9d9',
          borderRadius: 12,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
        },
        components: {
          Button: {
            borderRadius: 8,
          },
          Card: {
            borderRadius: 16,
          },
          Input: {
            borderRadius: 8,
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)