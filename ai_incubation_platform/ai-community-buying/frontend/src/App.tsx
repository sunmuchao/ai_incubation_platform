import React from 'react'
import { ConfigProvider, theme } from 'antd'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useSettingsStore } from '@/stores'
import { ChatLayout } from '@/components/Layout/ChatLayout'
import { HomePage } from '@/pages'

const App: React.FC = () => {
  const { theme: appTheme } = useSettingsStore()

  return (
    <ConfigProvider
      theme={{
        algorithm: appTheme === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <Routes>
        <Route
          path="/"
          element={
            <ChatLayout>
              <HomePage />
            </ChatLayout>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfigProvider>
  )
}

export default App
