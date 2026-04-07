import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import App from './App'
import './styles/index.less'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorBgBase: '#000000',
          colorBgContainer: '#141414',
          colorTextBase: 'rgba(255, 255, 255, 0.85)',
          colorBorder: '#303030',
          colorPrimary: '#722ed1',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
