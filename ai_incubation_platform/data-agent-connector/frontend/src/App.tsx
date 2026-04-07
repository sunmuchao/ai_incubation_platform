/**
 * AI Native 主应用 - Bento Grid 布局重构
 * 采用模块化卡片设计，Monochromatic 配色
 */
import React, { useState } from 'react'
import { Layout, Typography, Avatar, Badge, Dropdown, Drawer, Button } from 'antd'
import {
  DatabaseOutlined,
  LineChartOutlined,
  MenuOutlined,
  BellOutlined,
  SearchOutlined,
  CloudServerOutlined,
  SafetyOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { AIChat } from './components/AIChat'
import { LineageGraph } from './components/LineageGraph'
import { AgentVisualization } from './components/AgentVisualization'
import { QuickQueryPanel } from './components/QuickQueryPanel'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

// 侧边栏菜单项
const menuItems = [
  { key: 'chat', icon: <RobotOutlined />, label: 'AI 对话' },
  { key: 'dashboard', icon: <FireOutlined />, label: '仪表板' },
  { key: 'lineage', icon: <LineChartOutlined />, label: '血缘图谱' },
  { key: 'templates', icon: <DatabaseOutlined />, label: '查询模板' },
  { key: 'connectors', icon: <CloudServerOutlined />, label: '数据源' },
  { key: 'governance', icon: <SafetyOutlined />, label: '数据治理' },
  { key: 'history', icon: <HistoryOutlined />, label: '查询历史' },
]

/**
 * AI Native 主应用 - Bento Grid 版本
 */
const App: React.FC = () => {
  const [selectedKey, setSelectedKey] = useState('dashboard')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)
  const [currentQuery, setCurrentQuery] = useState('')

  // 处理查询变化
  const handleQueryChange = (query: string) => {
    setCurrentQuery(query)
  }

  // 渲染内容区域
  const renderContent = () => {
    switch (selectedKey) {
      case 'chat':
        return (
          <div className="h-full p-4">
            <div className="bento-card h-full flex flex-col">
              <AIChat onQueryChange={handleQueryChange} />
            </div>
          </div>
        )
      case 'dashboard':
        return <DashboardView currentQuery={currentQuery} onQueryChange={handleQueryChange} />
      case 'lineage':
        return (
          <div className="h-full p-4">
            <div className="bento-card h-full">
              <LineageGraph />
            </div>
          </div>
        )
      case 'templates':
        return (
          <div className="h-full p-4">
            <div className="bento-card p-4 h-full overflow-auto">
              <QuickQueryPanel onSelectQuery={handleQueryChange} />
            </div>
          </div>
        )
      case 'connectors':
        return (
          <div className="p-6">
            <div className="bento-card p-6">
              <Title level={3} className="flex items-center mb-4">
                <CloudServerOutlined className="mr-2 text-indigo-500" />
                数据源管理
              </Title>
              <Text className="text-slate-500 block mb-2">
                请通过 AI 助手管理数据源连接
              </Text>
              <Text className="text-slate-400 text-sm italic">
                示例："连接一个 MySQL 数据库，名叫 test_db"
              </Text>
            </div>
          </div>
        )
      case 'governance':
        return (
          <div className="p-6">
            <div className="bento-card p-6">
              <Title level={3} className="flex items-center mb-4">
                <SafetyOutlined className="mr-2 text-indigo-500" />
                数据治理
              </Title>
              <Text className="text-slate-500">
                数据分类、敏感数据识别、脱敏策略等功能
              </Text>
            </div>
          </div>
        )
      case 'history':
        return (
          <div className="p-6">
            <div className="bento-card p-6">
              <Title level={3} className="flex items-center mb-4">
                <HistoryOutlined className="mr-2 text-indigo-500" />
                查询历史
              </Title>
              <Text className="text-slate-500">
                查询历史记录将在 AI 对话后自动保存
              </Text>
            </div>
          </div>
        )
      default:
        return (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Title level={3}>功能开发中</Title>
              <Text className="text-slate-500">该功能正在开发中，敬请期待...</Text>
            </div>
          </div>
        )
    }
  }

  return (
    <Layout className="h-screen bg-slate-50">
      {/* 桌面端侧边栏 - 精简设计 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        className="hidden md:block bg-white border-r border-slate-200"
        width={260}
        theme="light"
      >
        {/* Logo 区域 */}
        <div className="h-16 flex items-center justify-center border-b border-slate-100">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-linear">
              <RobotOutlined className="text-white text-lg" />
            </div>
            {!collapsed && (
              <span className="ml-3 font-semibold text-slate-800">
                Data-Agent AI
              </span>
            )}
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className="p-3 space-y-1">
          {menuItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setSelectedKey(item.key)}
              className={`
                w-full flex items-center px-3 py-2.5 rounded-linear
                transition-all duration-200 group
                ${
                  selectedKey === item.key
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }
              `}
            >
              <span
                className={`
                  text-lg transition-transform duration-200
                  ${selectedKey === item.key ? 'scale-110' : 'group-hover:scale-110'}
                `}
              >
                {item.icon}
              </span>
              {!collapsed && (
                <span className="ml-3 text-sm font-medium">{item.label}</span>
              )}
              {selectedKey === item.key && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500" />
              )}
            </button>
          ))}
        </nav>
      </Sider>

      {/* 移动端侧边栏 */}
      <Drawer
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        width={280}
        className="md:hidden"
        styles={{ body: { padding: 0 } }}
      >
        <div className="h-full bg-white">
          {/* Logo */}
          <div className="h-16 flex items-center justify-center border-b border-slate-100">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
                <RobotOutlined className="text-white text-lg" />
              </div>
              <span className="ml-3 font-semibold text-slate-800">Data-Agent AI</span>
            </div>
          </div>

          {/* 导航菜单 */}
          <nav className="p-3 space-y-1">
            {menuItems.map((item) => (
              <button
                key={item.key}
                onClick={() => {
                  setSelectedKey(item.key)
                  setMobileDrawerOpen(false)
                }}
                className={`
                  w-full flex items-center px-3 py-3 rounded-linear
                  transition-all duration-200
                  ${
                    selectedKey === item.key
                      ? 'bg-indigo-50 text-indigo-600'
                      : 'text-slate-600 hover:bg-slate-50'
                  }
                `}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="ml-3 text-sm font-medium">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </Drawer>

      {/* 主内容区 */}
      <Layout>
        {/* 顶部导航栏 */}
        <Header className="h-16 bg-white border-b border-slate-200 px-4 flex items-center justify-between shadow-linear-sm">
          <div className="flex items-center space-x-4">
            {/* 移动端菜单按钮 */}
            <Button
              type="text"
              icon={<MenuOutlined />}
              className="md:hidden text-slate-600 hover:text-slate-900"
              onClick={() => setMobileDrawerOpen(true)}
            />

            {/* 标题 - 移动端 */}
            <div className="md:hidden flex items-center">
              <div className="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
                <RobotOutlined className="text-white text-sm" />
              </div>
            </div>

            {/* 搜索框 - 桌面端 */}
            <div className="hidden md:flex items-center">
              <div className="relative">
                <SearchOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="搜索数据、表、字段..."
                  className="input-linear pl-10 w-72"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* 通知 */}
            <div className="relative">
              <Badge count={3} size="small" offset={[-2, -2]}>
                <button className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-slate-100 transition-colors">
                  <BellOutlined className="text-slate-500" />
                </button>
              </Badge>
            </div>

            {/* 分隔线 */}
            <div className="w-px h-6 bg-slate-200" />

            {/* 用户头像 */}
            <Dropdown
              menu={{
                items: [
                  { key: 'profile', label: '个人中心' },
                  { key: 'settings', label: '账号设置' },
                  { type: 'divider' },
                  { key: 'logout', label: '退出登录', danger: true },
                ],
              }}
            >
              <div className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity">
                <Avatar
                  size={32}
                  className="bg-gradient-to-br from-indigo-400 to-indigo-600 border-2 border-white shadow-linear-sm"
                >
                  <span className="text-sm font-medium">U</span>
                </Avatar>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 主内容区域 */}
        <Content className="overflow-hidden">{renderContent()}</Content>
      </Layout>
    </Layout>
  )
}

/**
 * 仪表板视图组件 - Bento Grid 布局
 */
interface DashboardViewProps {
  currentQuery?: string
  onQueryChange?: (query: string) => void
}

const DashboardView: React.FC<DashboardViewProps> = ({ currentQuery, onQueryChange }) => {
  return (
    <div className="p-4 h-full overflow-auto">
      {/* 顶部标题栏 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">
          <FireOutlined className="mr-2 text-indigo-500" />
          AI Native 数据平台
        </h1>
        <p className="text-slate-500 text-sm">让数据对话，获得深度洞察</p>
      </div>

      {/* Bento Grid 布局 */}
      <div className="bento-grid bento-grid-auto pb-4">
        {/* 统计卡片行 */}
        <StatCard
          title="活跃数据源"
          value="3"
          icon={<DatabaseOutlined />}
          color="indigo"
          trend="+1 本周"
        />
        <StatCard
          title="24h 查询"
          value="1,234"
          icon={<ThunderboltOutlined />}
          color="emerald"
          trend="+12.5%"
        />
        <StatCard
          title="平均延迟"
          value="45ms"
          icon={<LineChartOutlined />}
          color="amber"
          trend="-8ms"
        />
        <StatCard
          title="治理评分"
          value="85"
          icon={<SafetyOutlined />}
          color="violet"
          progress={85}
        />

        {/* AI Chat - 大卡片 */}
        <div className="bento-xl bento-card overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800 flex items-center">
              <RobotOutlined className="mr-2 text-indigo-500" />
              AI 数据助手
            </h3>
            <p className="text-xs text-slate-500 mt-1">通过自然语言查询和分析数据</p>
          </div>
          <div className="flex-1 min-h-0">
            <AIChat onQueryChange={onQueryChange} />
          </div>
        </div>

        {/* Agent 可视化 */}
        <div className="bento-md bento-card">
          <AgentVisualization currentQuery={currentQuery} showDetails />
        </div>

        {/* 查询模板 */}
        <div className="bento-sm bento-card">
          <div className="p-4 h-full">
            <h3 className="font-semibold text-slate-800 mb-3 flex items-center">
              <ThunderboltOutlined className="mr-2 text-amber-500" />
              快速查询
            </h3>
            <QuickQueryPanel onSelectQuery={onQueryChange} />
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * 统计卡片组件
 */
interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  color: 'indigo' | 'emerald' | 'amber' | 'violet'
  trend?: string
  progress?: number
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, trend, progress }) => {
  const colorMap = {
    indigo: {
      bg: 'from-indigo-50 to-indigo-100',
      text: 'text-indigo-600',
      icon: 'bg-indigo-500',
    },
    emerald: {
      bg: 'from-emerald-50 to-emerald-100',
      text: 'text-emerald-600',
      icon: 'bg-emerald-500',
    },
    amber: {
      bg: 'from-amber-50 to-amber-100',
      text: 'text-amber-600',
      icon: 'bg-amber-500',
    },
    violet: {
      bg: 'from-violet-50 to-violet-100',
      text: 'text-violet-600',
      icon: 'bg-violet-500',
    },
  }

  const colors = colorMap[color]

  return (
    <div className="bento-sm stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{title}</p>
          <p className={`text-3xl font-bold mt-2 ${colors.text}`}>{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.startsWith('+') ? 'text-emerald-600' : 'text-slate-400'}`}>
              {trend}
            </p>
          )}
        </div>
        <div className={`stat-card-icon ${colors.bg}`}>
          <span className={colors.text}>{icon}</span>
        </div>
      </div>
      {progress !== undefined && (
        <div className="mt-3">
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${colors.bg}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default App
