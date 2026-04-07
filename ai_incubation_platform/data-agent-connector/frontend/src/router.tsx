/**
 * 路由配置
 */
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import ConversationPage from './pages/ConversationPage'

/**
 * 路由组件
 */
const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* 主应用 - 多页面导航 */}
        <Route path="/" element={<App />} />

        {/* 对话页面 - 全屏 AI 交互 */}
        <Route path="/chat" element={<ConversationPage />} />

        {/* 默认重定向 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default AppRouter
