/**
 * 应用主路由配置
 */
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ROUTES } from './config/routes'
import MainLayout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ConnectorsPage from './pages/ConnectorsPage'
import DataQueryPage from './pages/DataQueryPage'
import LineagePage from './pages/LineagePage'
import GovernancePage from './pages/GovernancePage'
import MonitoringPage from './pages/MonitoringPage'

// 占位页面组件
const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div className="flex flex-col items-center justify-center h-96">
    <div className="text-6xl mb-4">🚧</div>
    <h2 className="text-2xl font-bold text-gray-700">{title}</h2>
    <p className="text-gray-500 mt-2">页面开发中，敬请期待...</p>
  </div>
)

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* 重定向根路径到仪表盘 */}
        <Route path="/" element={<Navigate to={ROUTES.DASHBOARD} replace />} />

        {/* 主应用路由 */}
        <Route element={<MainLayout />}>
          {/* 仪表盘 */}
          <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />

          {/* 连接器管理 */}
          <Route path={ROUTES.CONNECTORS} element={<ConnectorsPage />} />

          {/* 数据查询 */}
          <Route path={ROUTES.DATA_QUERY} element={<DataQueryPage />} />
          <Route path={ROUTES.SQL_EDITOR} element={<DataQueryPage />} />
          <Route path={ROUTES.QUERY_HISTORY} element={<PlaceholderPage title="查询历史" />} />

          {/* 血缘图谱 */}
          <Route path={ROUTES.LINEAGE} element={<LineagePage />} />
          <Route path={ROUTES.LINEAGE_GRAPH} element={<LineagePage />} />

          {/* 数据治理 */}
          <Route path={ROUTES.GOVERNANCE} element={<GovernancePage />} />
          <Route path={ROUTES.GOVERNANCE_CLASSIFICATION} element={<PlaceholderPage title="数据分类" />} />
          <Route path={ROUTES.GOVERNANCE_SENSITIVE} element={<PlaceholderPage title="敏感数据" />} />
          <Route path={ROUTES.GOVERNANCE_MASKING} element={<PlaceholderPage title="脱敏策略" />} />

          {/* 权限管理 */}
          <Route path={ROUTES.PERMISSIONS} element={<PlaceholderPage title="权限管理" />} />
          <Route path={ROUTES.PERMISSIONS_ROLES} element={<PlaceholderPage title="角色管理" />} />
          <Route path={ROUTES.PERMISSIONS_USERS} element={<PlaceholderPage title="用户管理" />} />
          <Route path={ROUTES.PERMISSIONS_AUDIT} element={<PlaceholderPage title="权限审计" />} />

          {/* API 管理 */}
          <Route path={ROUTES.API_MANAGEMENT} element={<PlaceholderPage title="API 管理" />} />
          <Route path={ROUTES.API_DOCS} element={<PlaceholderPage title="API 文档" />} />
          <Route path={ROUTES.API_KEYS} element={<PlaceholderPage title="密钥管理" />} />
          <Route path={ROUTES.API_USAGE} element={<PlaceholderPage title="用量统计" />} />

          {/* 监控中心 */}
          <Route path={ROUTES.MONITORING} element={<MonitoringPage />} />
          <Route path={ROUTES.MONITORING_METRICS} element={<PlaceholderPage title="性能监控" />} />
          <Route path={ROUTES.MONITORING_ALERTS} element={<PlaceholderPage title="告警管理" />} />

          {/* 日志审计 */}
          <Route path={ROUTES.LOGS} element={<PlaceholderPage title="日志审计" />} />
          <Route path={ROUTES.LOGS_AUDIT} element={<PlaceholderPage title="审计日志" />} />
          <Route path={ROUTES.LOGS_QUERY} element={<PlaceholderPage title="查询日志" />} />

          {/* 连接器市场 */}
          <Route path={ROUTES.MARKETPLACE} element={<PlaceholderPage title="连接器市场" />} />

          {/* 管理后台 */}
          <Route path={ROUTES.ADMIN} element={<PlaceholderPage title="管理后台" />} />
        </Route>

        {/* 登录页面 */}
        <Route path="/login" element={<PlaceholderPage title="登录" />} />

        {/* 404 重定向 */}
        <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
