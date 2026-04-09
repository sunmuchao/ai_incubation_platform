// AI Native App 入口

import { useState, useEffect } from 'react'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegistrationConversationPage from './pages/RegistrationConversationPage'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [checking, setChecking] = useState(true)
  const [showRegistrationConversation, setShowRegistrationConversation] = useState(false)

  useEffect(() => {
    // 检查用户是否已登录
    const token = localStorage.getItem('jwt_token')
    const hasCompletedConversation = localStorage.getItem('has_completed_registration_conversation')
    setIsLoggedIn(!!token)
    // 如果是新用户（未完成注册对话），显示对话页面
    setShowRegistrationConversation(!!token && !hasCompletedConversation)
    setChecking(false)
  }, [])

  const handleLoginSuccess = () => {
    const hasCompletedConversation = localStorage.getItem('has_completed_registration_conversation')
    setIsLoggedIn(true)
    // 如果未完成对话，显示对话页面
    setShowRegistrationConversation(!hasCompletedConversation)
  }

  const handleConversationComplete = () => {
    localStorage.setItem('has_completed_registration_conversation', 'true')
    setShowRegistrationConversation(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('has_completed_registration_conversation')
    setIsLoggedIn(false)
    setShowRegistrationConversation(false)
  }

  if (checking) {
    return null
  }

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  if (showRegistrationConversation) {
    return <RegistrationConversationPage onComplete={handleConversationComplete} />
  }

  return <HomePage onLogout={handleLogout} />
}

export default App
