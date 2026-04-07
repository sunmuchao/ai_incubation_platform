/**
 * AI Native 首页 - Chat First 界面
 */
import React from 'react'
import { theme } from 'antd'
import { ChatInterface } from '@/components/ChatInterface'

const HomePage: React.FC = () => {
  const { token } = theme.useToken()

  return (
    <div style={{ height: 'calc(100vh - 112px)', background: token.colorBgContainer }}>
      <ChatInterface />
    </div>
  )
}

export default HomePage
