// AI Native 主应用 - Chat-first 界面
import React, { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { Bot, Code2, Network, Settings, Menu, X, Sparkles, Zap } from 'lucide-react';
import ChatInterface from '@components/ChatInterface';
import CodeExplorer from '@pages/CodeExplorer';
import SettingsPage from '@pages/SettingsPage';

// 主布局组件
const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedProject, setSelectedProject] = useState('default');
  const location = useLocation();

  const navItems = [
    { icon: Bot, label: 'AI 对话', path: '/', active: true },
    { icon: Code2, label: '代码探索', path: '/explorer' },
    { icon: Network, label: '依赖图', path: '/graph' },
    { icon: Settings, label: '设置', path: '/settings' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="h-screen flex bg-base-900">
      {/* 侧边栏 */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-[72px]'
        } bg-surface border-r border-border-light transition-all duration-300 ease-smooth flex flex-col`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border-light">
          {sidebarOpen && (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg gradient-accent flex items-center justify-center shadow-glow-accent">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold text-base text-text-primary">AI Code</span>
            </div>
          )}
          {!sidebarOpen && (
            <div className="w-8 h-8 rounded-lg gradient-accent flex items-center justify-center mx-auto">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-surface-lighter text-text-secondary hover:text-text-primary transition-all duration-200"
            aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* 导航 */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                isActive(item.path)
                  ? 'bg-accent/20 text-white shadow-inner'
                  : 'text-text-secondary hover:bg-surface-light hover:text-text-primary'
              }`}
            >
              <item.icon
                className={`w-5 h-5 flex-shrink-0 transition-colors ${
                  isActive(item.path) ? 'text-accent' : 'text-text-secondary group-hover:text-text-primary'
                }`}
              />
              {sidebarOpen && (
                <>
                  <span className="text-sm font-medium">{item.label}</span>
                  {isActive(item.path) && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent shadow-glow-accent" />
                  )}
                </>
              )}
            </a>
          ))}
        </nav>

        {/* 项目选择器 */}
        {sidebarOpen && (
          <div className="p-4 border-t border-border-light">
            <div className="text-xs text-text-muted mb-2 font-medium">当前项目</div>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full bg-surface-lighter border border-border-light rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition-all duration-200"
            >
              <option value="default">默认项目</option>
              <option value="ai-code-understanding">ai-code-understanding</option>
              <option value="ai-employee-platform">ai-employee-platform</option>
              <option value="human-ai-community">human-ai-community</option>
            </select>
          </div>
        )}

        {/* 底部 - AI 状态 */}
        <div className="p-4 border-t border-border-light">
          {sidebarOpen && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 px-3 py-2 bg-accent-glow rounded-lg border border-border-light">
                <Zap className="w-4 h-4 text-accent" />
                <span className="text-xs text-text-secondary">AI 就绪</span>
              </div>
              <div className="text-xs text-text-muted">
                <p className="font-medium">v3.0 AI Native</p>
                <p className="text-xs text-text-muted/70 mt-0.5">对话式代码理解</p>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <header className="h-16 bg-surface border-b border-border-light flex items-center justify-between px-6 backdrop-blur-bento">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-text-primary">
              {navItems.find(item => item.path === location.pathname)?.label || 'AI 对话'}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {/* AI 状态指示器 */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-lighter rounded-full border border-border-light">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse shadow-glow-success" />
              <span className="text-xs text-text-secondary font-medium">AI 就绪</span>
            </div>
          </div>
        </header>

        {/* 页面内容 */}
        <div className="flex-1 overflow-hidden bg-gradient-to-br from-base-900 to-base-950">
          {children}
        </div>
      </main>
    </div>
  );
};

// 聊天首页
const ChatHome: React.FC = () => {
  return (
    <div className="h-full">
      <ChatInterface />
    </div>
  );
};

// 代码探索页面
const CodeExplorerPage: React.FC = () => {
  return (
    <div className="h-full p-6 overflow-auto">
      <CodeExplorer />
    </div>
  );
};

// 依赖图页面
const GraphPage: React.FC = () => {
  return (
    <div className="h-full p-6 overflow-auto">
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-text-secondary">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-surface-lighter border border-border-light flex items-center justify-center">
            <Network className="w-10 h-10 text-text-muted" />
          </div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">依赖关系图</h2>
          <p className="text-text-muted">通过对话让 AI 生成依赖图</p>
          <p className="text-sm text-text-muted/70 mt-2">例如："帮我画出这个项目的模块依赖关系"</p>
        </div>
      </div>
    </div>
  );
};

// 设置页面
const SettingsPageWrapper: React.FC = () => {
  return (
    <div className="h-full p-6 overflow-auto">
      <SettingsPage />
    </div>
  );
};

// 主应用
const App: React.FC = () => {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <MainLayout>
            <ChatHome />
          </MainLayout>
        }
      />
      <Route
        path="/explorer"
        element={
          <MainLayout>
            <CodeExplorerPage />
          </MainLayout>
        }
      />
      <Route
        path="/graph"
        element={
          <MainLayout>
            <GraphPage />
          </MainLayout>
        }
      />
      <Route
        path="/settings"
        element={
          <MainLayout>
            <SettingsPageWrapper />
          </MainLayout>
        }
      />
    </Routes>
  );
};

export default App;
