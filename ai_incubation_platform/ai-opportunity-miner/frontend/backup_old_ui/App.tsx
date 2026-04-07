import { Layout, Menu, theme } from 'antd'
import { useState } from 'react'
import {
  DashboardOutlined,
  BuildOutlined,
  FileTextOutlined,
  BellOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import Dashboard from './pages/Dashboard'
import EnterpriseStream from './pages/EnterpriseStream'
import PatentStream from './pages/PatentStream'
import NewsStream from './pages/NewsStream'
import Settings from './pages/Settings'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表板' },
  { key: 'enterprise', icon: <BuildOutlined />, label: '企业数据流' },
  { key: 'patent', icon: <FileTextOutlined />, label: '专利数据流' },
  { key: 'news', icon: <BellOutlined />, label: '新闻数据流' },
  { key: 'settings', icon: <SettingOutlined />, label: '设置' },
]

function App() {
  const [selectedKey, setSelectedKey] = useState('dashboard')
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const renderContent = () => {
    switch (selectedKey) {
      case 'dashboard':
        return <Dashboard />
      case 'enterprise':
        return <EnterpriseStream />
      case 'patent':
        return <PatentStream />
      case 'news':
        return <NewsStream />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard />
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={220}>
        <div style={{ height: 32, margin: 16, background: 'rgba(114, 46, 209, 0.3)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold', border: '1px solid rgba(114, 46, 209, 0.5)' }}>
          AI Opportunity Miner
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => setSelectedKey(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: colorBgContainer, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0, color: 'rgba(255, 255, 255, 0.85)' }}>
            {menuItems.find(item => item.key === selectedKey)?.label}
          </h2>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG, minHeight: 280 }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  )
}

export default App
