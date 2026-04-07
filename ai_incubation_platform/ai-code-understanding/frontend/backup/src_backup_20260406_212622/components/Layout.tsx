// 布局组件
import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Code2,
  Map,
  Search,
  MessageSquare,
  FileCheck,
  FileText,
  Network,
  Settings,
  Menu,
  X,
  Github,
  Zap
} from 'lucide-react';

const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  const navItems = [
    { icon: Code2, label: 'Dashboard', path: '/' },
    { icon: Map, label: '代码地图', path: '/code-map' },
    { icon: Search, label: '代码搜索', path: '/code-search' },
    { icon: MessageSquare, label: '智能问答', path: '/code-qa' },
    { icon: FileCheck, label: '代码审查', path: '/code-review' },
    { icon: FileText, label: '文档中心', path: '/docs' },
    { icon: Network, label: '知识图谱', path: '/knowledge-graph' },
    { icon: Settings, label: '设置', path: '/settings' },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* 侧边栏 */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-surface border-r border-border transition-all duration-300 flex flex-col`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <Zap className="w-6 h-6 text-accent" />
              <span className="font-bold text-lg">AI Code</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-card rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* 导航 */}
        <nav className="flex-1 py-4 px-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-all ${
                isActive(item.path)
                  ? 'bg-accent text-white'
                  : 'text-muted hover:bg-card hover:text-text'
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* 底部 */}
        <div className="p-4 border-t border-border">
          {sidebarOpen && (
            <div className="text-xs text-muted">
              <p>v2.1.0</p>
              <p className="mt-1">代码认知基础设施层</p>
            </div>
          )}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-2 mt-3 px-3 py-2 rounded-lg bg-card hover:bg-border transition-colors ${
              !sidebarOpen && 'justify-center'
            }`}
          >
            <Github className="w-5 h-5" />
            {sidebarOpen && <span>GitHub</span>}
          </a>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        {/* 顶部栏 */}
        <header className="h-16 bg-surface border-b border-border flex items-center justify-between px-6">
          <h1 className="text-xl font-semibold">
            {navItems.find(item => item.path === location.pathname)?.label || 'Dashboard'}
          </h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-card rounded-full">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse"></div>
              <span className="text-sm text-muted">API 正常</span>
            </div>
          </div>
        </header>

        {/* 页面内容 */}
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
