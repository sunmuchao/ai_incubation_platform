/**
 * AI Native 对话首页 - Bento Grid 风格重构
 * 主要交互界面
 */
import React, { useState } from 'react'
import { Layout, Typography, Badge, Space, Avatar, Dropdown, Button, Drawer } from 'antd'
import {
  MenuOutlined,
  BellOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  StarOutlined,
  SettingOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { AIChat } from '../components/AIChat'
import { AgentVisualization } from '../components/AgentVisualization'

const { Header, Content, Sider } = Layout
const { Title, Text } = Typography

const ConversationPage: React.FC = () => {
  const [currentQuery, setCurrentQuery] = useState('')
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  // 处理查询变化
  const handleQueryChange = (query: string) => {
    setCurrentQuery(query)
  }

  // 侧边栏菜单项配置
  const sidebarItems = [
    { icon: <ThunderboltOutlined />, active: true, tooltip: 'AI 对话' },
    { icon: <HistoryOutlined />, onClick: () => setShowHistory(true), tooltip: '查询历史' },
    { icon: <StarOutlined />, tooltip: '收藏' },
  ]

  return (
    <Layout className="h-screen bg-slate-50">
      {/* 左侧边栏 - 功能导航 */}
      <Sider
        width={64}
        className="bg-white border-r border-slate-200 flex flex-col items-center py-4"
        theme="light"
      >
        {/* Logo */}
        <div className="mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-linear">
            <RobotOutlined className="text-lg text-white" />
          </div>
        </div>

        {/* 菜单项 */}
        <div className="flex-1 space-y-3">
          {sidebarItems.map((item, index) => (
            <Badge dot={item.active && !item.onClick} key={index}>
              <div
                className={`
                  w-10 h-10 flex items-center justify-center rounded-xl
                  transition-all duration-200 cursor-pointer
                  ${
                    item.active
                      ? 'bg-indigo-50 text-indigo-600'
                      : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                  }
                `}
                onClick={item.onClick}
              >
                <span className="text-lg">{item.icon}</span>
              </div>
            </Badge>
          ))}
        </div>

        {/* 底部设置 */}
        <div className="w-10 h-10 flex items-center justify-center rounded-xl cursor-pointer text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-all duration-200">
          <SettingOutlined className="text-lg" />
        </div>
      </Sider>

      {/* 主内容区 */}
      <Layout>
        {/* 顶部栏 */}
        <Header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-linear-sm">
          <div className="flex items-center space-x-4">
            <Button
              type="text"
              icon={<MenuOutlined />}
              className="md:hidden text-slate-600"
              onClick={() => setMobileDrawerOpen(true)}
            />
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
                <FireOutlined className="text-white text-sm" />
              </div>
              <div>
                <Title level={5} style={{ margin: 0 }} className="text-slate-800">
                  AI 数据助手
                </Title>
                <Text className="text-slate-400" style={{ fontSize: 11 }}>
                  用自然语言与数据对话
                </Text>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="relative">
              <Badge count={5} size="small" offset={[-2, -2]}>
                <button className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-slate-50 transition-colors">
                  <BellOutlined className="text-slate-500" />
                </button>
              </Badge>
            </div>

            <div className="w-px h-6 bg-slate-200" />

            <Dropdown
              menu={{
                items: [
                  { key: 'profile', label: '个人资料' },
                  { key: 'settings', label: '设置' },
                  { type: 'divider' },
                  { key: 'logout', label: '退出', danger: true },
                ],
              }}
            >
              <div className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity">
                <Avatar
                  size={32}
                  className="bg-gradient-to-br from-indigo-400 to-indigo-600 border-2 border-white shadow-linear-sm"
                >
                  <span className="text-xs font-medium">U</span>
                </Avatar>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 内容区 - 左右分栏 */}
        <Content className="flex overflow-hidden">
          {/* 左侧：AI Chat */}
          <div className="flex-1 border-r border-slate-200">
            <AIChat onQueryChange={handleQueryChange} />
          </div>

          {/* 右侧：Agent 可视化 */}
          <div className="w-80 bg-slate-50/50 overflow-y-auto">
            <div className="p-4">
              {/* Agent 可视化卡片 */}
              <div className="bento-card p-4">
                <AgentVisualization
                  currentQuery={currentQuery}
                  showDetails={true}
                />
              </div>

              {/* 快速操作卡片 */}
              <div className="mt-4 bento-card p-4">
                <Text strong className="text-slate-700 text-sm block mb-3">
                  快捷操作
                </Text>
                <Space direction="vertical" className="w-full" size="small">
                  <Button
                    block
                    size="small"
                    className="btn-linear justify-start"
                    onClick={() => handleQueryChange('查看当前有哪些数据源')}
                  >
                    <ThunderboltOutlined className="mr-2 text-indigo-500" />
                    查看数据源
                  </Button>
                  <Button
                    block
                    size="small"
                    className="btn-linear justify-start"
                    onClick={() => handleQueryChange('显示所有表结构')}
                  >
                    <HistoryOutlined className="mr-2 text-emerald-500" />
                    查看表结构
                  </Button>
                  <Button
                    block
                    size="small"
                    className="btn-linear justify-start"
                    onClick={() => handleQueryChange('查询最新的数据')}
                  >
                    <FireOutlined className="mr-2 text-amber-500" />
                    查询最新数据
                  </Button>
                </Space>
              </div>
            </div>
          </div>
        </Content>
      </Layout>

      {/* 历史抽屉 */}
      <Drawer
        placement="left"
        onClose={() => setShowHistory(false)}
        open={showHistory}
        width={320}
        styles={{
          header: { borderBottom: '1px solid #e2e8f0', padding: '16px 24px' },
          body: { padding: 0 },
        }}
        title={
          <div className="flex items-center space-x-2">
            <HistoryOutlined className="text-indigo-500" />
            <span className="font-medium text-slate-800">查询历史</span>
          </div>
        }
      >
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <HistoryOutlined className="text-2xl text-slate-400" />
            </div>
            <Text className="text-slate-500 block">暂无查询历史</Text>
            <Text className="text-slate-400 text-xs block mt-1">
              查询记录将在此处显示
            </Text>
          </div>
        </div>
      </Drawer>

      {/* 移动端抽屉 */}
      <Drawer
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        width={280}
        styles={{
          header: { borderBottom: '1px solid #e2e8f0', padding: '16px 24px' },
          body: { padding: 0 },
        }}
        title={
          <div className="flex items-center space-x-2">
            <RobotOutlined className="text-indigo-500" />
            <span className="font-medium text-slate-800">菜单</span>
          </div>
        }
      >
        <div className="p-3 space-y-1">
          {['AI 对话', '查询历史', '收藏', '设置'].map((item) => (
            <Button
              key={item}
              block
              size="large"
              className="justify-start py-3 px-4 text-slate-700 hover:bg-slate-50"
            >
              {item}
            </Button>
          ))}
        </div>
      </Drawer>
    </Layout>
  )
}

export default ConversationPage
