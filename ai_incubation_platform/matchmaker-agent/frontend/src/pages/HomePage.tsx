// AI Native 主页面 - 对话式匹配首页

import React, { useState, useEffect } from 'react'
import { Layout, Typography, Space, Button, Avatar, Drawer, Card } from 'antd'
import {
  BellOutlined,
  UserOutlined,
  MessageFilled,
  HomeOutlined,
  AppstoreOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import ChatInterface from '../components/ChatInterface'
import MatchCard from '../components/MatchCard'
import AgentVisualization from '../components/AgentVisualization'
import PushNotifications from '../components/PushNotifications'
import type { MatchCandidate, AgentStatus } from '../types'
import './HomePage.less'

const { Header, Content } = Layout
const { Title, Text } = Typography

const HomePage: React.FC = () => {
  const [currentView, setCurrentView] = useState<'chat' | 'discover'>('chat')
  const [selectedMatch, setSelectedMatch] = useState<MatchCandidate | null>(null)
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    status: 'idle',
    progress: 0,
    message: 'AI 红娘已就绪',
  })
  const [notificationsVisible, setNotificationsVisible] = useState(false)

  // 模拟 Agent 状态更新
  useEffect(() => {
    const interval = setInterval(() => {
      // 实际应用中应该从后端获取真实状态
      setAgentStatus((prev) => ({
        ...prev,
        progress: prev.status === 'idle' ? 0 : Math.min(prev.progress + 10, 100),
      }))
    }, 500)

    return () => clearInterval(interval)
  }, [])

  const handleMatchSelect = (match: MatchCandidate) => {
    setSelectedMatch(match)
  }

  const handleCloseMatchDetail = () => {
    setSelectedMatch(null)
  }

  const handleLike = () => {
    console.log('Liked match')
    // 调用 API
  }

  const handlePass = () => {
    console.log('Passed match')
    // 调用 API
  }

  const handleSuperLike = () => {
    console.log('Super liked match')
    // 调用 API
  }

  const handleMessage = () => {
    console.log('Start conversation')
    // 导航到聊天页面
  }

  const renderContent = () => {
    switch (currentView) {
      case 'chat':
        return (
          <div className="chat-view">
            <div className="agent-status-container">
              <AgentVisualization status={agentStatus} />
            </div>
            <div className="chat-container">
              <ChatInterface onMatchSelect={handleMatchSelect} />
            </div>
          </div>
        )
      case 'discover':
        return (
          <div className="discover-view">
            <div className="discover-header">
              <Title level={4} style={{ margin: 0, color: 'white' }}>
                发现
              </Title>
              <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                探索更多可能的缘分
              </Text>
            </div>
            <div className="match-cards-container">
              {/* 这里可以展示多个匹配卡片 */}
              <Card title="今日推荐" size="small">
                <Text style={{ color: '#999' }}>更多匹配功能开发中...</Text>
              </Card>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <Layout className="home-layout">
      <Header className="home-header">
        <div className="header-left">
          <Avatar
            size={40}
            icon={<HeartOutlined />}
            style={{ backgroundColor: '#ff4d4f' }}
          />
          <Title level={4} style={{ margin: '0 12px', color: 'white' }}>
            AI Matchmaker
          </Title>
        </div>
        <div className="header-right">
          <Space size="large">
            <PushNotifications
              onNotificationClick={(notification) => {
                console.log('Notification clicked:', notification)
              }}
              onMatchSelect={handleMatchSelect}
            />
            <Button type="text" icon={<UserOutlined />} style={{ color: 'white' }} />
          </Space>
        </div>
      </Header>

      <Content className="home-content">
        <div className="content-wrapper">
          {renderContent()}
        </div>
      </Content>

      {/* 底部导航栏 */}
      <div className="bottom-nav">
        <Button
          type={currentView === 'chat' ? 'primary' : 'text'}
          icon={<MessageFilled />}
          onClick={() => setCurrentView('chat')}
          className="nav-item"
        >
          对话
        </Button>
        <Button
          type={currentView === 'discover' ? 'primary' : 'text'}
          icon={<AppstoreOutlined />}
          onClick={() => setCurrentView('discover')}
          className="nav-item"
        >
          发现
        </Button>
      </div>

      {/* 匹配详情 Drawer */}
      {selectedMatch && (
        <Drawer
          title="匹配详情"
          placement="right"
          width={400}
          open={!!selectedMatch}
          onClose={handleCloseMatchDetail}
        >
          <MatchCard
            match={selectedMatch}
            onLike={handleLike}
            onPass={handlePass}
            onSuperLike={handleSuperLike}
            onMessage={handleMessage}
          />
        </Drawer>
      )}
    </Layout>
  )
}

export default HomePage
