// AI Native App 入口

import { useState, useEffect } from 'react'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegistrationConversationPage from './pages/RegistrationConversationPage'
import IOSTestPage from './pages/IOSTestPage'
import { authStorage, registrationStorage } from './utils/storage'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [checking, setChecking] = useState(true)
  const [showRegistrationConversation, setShowRegistrationConversation] = useState(false)

  // 检查是否是 iOS 测试页面模式
  const urlParams = new URLSearchParams(window.location.search)
  const isIOSTestMode = urlParams.get('ios-test') === 'true'

  useEffect(() => {
    // 检查用户是否已登录
    const hasToken = authStorage.isAuthenticated()
    const hasCompletedConversation = registrationStorage.isCompleted()
    setIsLoggedIn(hasToken)
    // 如果是新用户（未完成注册对话），显示对话页面
    setShowRegistrationConversation(hasToken && !hasCompletedConversation)
    setChecking(false)
  }, [])

  const handleLoginSuccess = () => {
    const hasCompletedConversation = registrationStorage.isCompleted()
    setIsLoggedIn(true)
    // 如果未完成对话，显示对话页面
    setShowRegistrationConversation(!hasCompletedConversation)
  }

  const handleConversationComplete = () => {
    registrationStorage.markCompleted()
    setShowRegistrationConversation(false)
  }

  const handleLogout = () => {
    authStorage.clear()
    setIsLoggedIn(false)
    setShowRegistrationConversation(false)
  }

  if (checking) {
    return null
  }

  // iOS 测试页面（开发模式下通过 ?ios-test=true 访问）
  if (isIOSTestMode && process.env.NODE_ENV === 'development') {
    return <IOSTestPage />
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
