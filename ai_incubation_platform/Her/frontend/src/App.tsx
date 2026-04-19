// AI Native App 入口

import { useState, useEffect } from 'react'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import IOSTestPage from './pages/IOSTestPage'
import MatchFilterTest from './test/MatchFilterTest'
import { authStorage } from './utils/storage'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [checking, setChecking] = useState(true)

  // 检查是否是测试页面模式
  const urlParams = new URLSearchParams(window.location.search)
  const isIOSTestMode = urlParams.get('ios-test') === 'true'
  const isMatchFilterTest = urlParams.get('match-filter-test') === 'true'

  useEffect(() => {
    // 检查用户是否已登录
    const hasToken = authStorage.isAuthenticated()
    setIsLoggedIn(hasToken)
    setChecking(false)
  }, [])

  // 监听 auth:expired 事件，当 token 过期时跳转到登录页
  useEffect(() => {
    const handleAuthExpired = () => {
      console.info('[App] Token expired, redirecting to login')
      authStorage.clear()
      setIsLoggedIn(false)
    }

    window.addEventListener('auth:expired', handleAuthExpired)
    return () => window.removeEventListener('auth:expired', handleAuthExpired)
  }, [])

  const handleLoginSuccess = () => {
    setIsLoggedIn(true)
  }

  const handleLogout = () => {
    authStorage.clear()
    setIsLoggedIn(false)
  }

  if (checking) {
    return null
  }

  // iOS 测试页面（开发模式下通过 ?ios-test=true 访问）
  if (isIOSTestMode && process.env.NODE_ENV === 'development') {
    return <IOSTestPage />
  }

  // 篛选功能测试页面（开发模式下通过 ?match-filter-test=true 访问）
  if (isMatchFilterTest && process.env.NODE_ENV === 'development') {
    return <MatchFilterTest />
  }

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  // 新用户直接进入 HomePage，通过对话收集信息（AI Native 设计）
  return <HomePage onLogout={handleLogout} />
}

export default App
