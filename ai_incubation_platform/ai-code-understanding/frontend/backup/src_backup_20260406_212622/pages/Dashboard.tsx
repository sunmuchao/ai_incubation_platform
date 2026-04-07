// Dashboard 页面
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Code2,
  Map,
  Search,
  MessageSquare,
  FileCheck,
  Network,
  Zap,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [serviceStatus, setServiceStatus] = useState<'healthy' | 'unhealthy' | 'checking'>('checking');
  const recentProjects = [
    { name: 'ai-code-understanding', files: 48, lastIndexed: '2 小时前', status: 'ready' },
    { name: 'ai-employee-platform', files: 156, lastIndexed: '1 天前', status: 'ready' },
    { name: 'human-ai-community', files: 89, lastIndexed: '3 天前', status: 'needs-update' },
  ];

  useEffect(() => {
    checkServiceHealth();
  }, []);

  const checkServiceHealth = async () => {
    try {
      // 服务健康检查功能暂时注释
      setServiceStatus('healthy');
    } catch (error) {
      setServiceStatus('unhealthy');
    }
  };

  const quickActions = [
    {
      icon: Map,
      title: '生成代码地图',
      description: '分析项目架构和分层',
      action: () => navigate('/code-map'),
      color: 'text-blue-400'
    },
    {
      icon: Search,
      title: '代码搜索',
      description: '语义搜索和符号查找',
      action: () => navigate('/code-search'),
      color: 'text-green-400'
    },
    {
      icon: MessageSquare,
      title: '智能问答',
      description: '询问关于代码库的问题',
      action: () => navigate('/code-qa'),
      color: 'text-purple-400'
    },
    {
      icon: FileCheck,
      title: '代码审查',
      description: '检测代码异味和安全风险',
      action: () => navigate('/code-review'),
      color: 'text-orange-400'
    },
  ];

  const features = [
    { icon: Code2, title: '代码理解', desc: '解释代码片段和模块' },
    { icon: Map, title: '全局地图', desc: '可视化项目架构分层' },
    { icon: Network, title: '知识图谱', desc: '探索代码实体关系' },
    { icon: Zap, title: '任务引导', desc: '生成学习路径' },
  ];

  return (
    <div className="space-y-8">
      {/* 欢迎区域 */}
      <div className="bg-gradient-to-r from-surface to-card rounded-xl p-6 border border-border">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold mb-2">
              欢迎使用 AI Code Understanding
            </h2>
            <p className="text-muted max-w-2xl">
              让任何开发者都能在 5 分钟内理解一个陌生代码库的全局结构、核心架构和关键依赖
            </p>
          </div>
          <div className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
            serviceStatus === 'healthy'
              ? 'bg-success/20 text-success'
              : 'bg-error/20 text-error'
          }`}>
            {serviceStatus === 'healthy' ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <AlertCircle className="w-5 h-5" />
            )}
            <span>{serviceStatus === 'healthy' ? '服务正常' : '服务异常'}</span>
          </div>
        </div>
      </div>

      {/* 快速操作 */}
      <div>
        <h3 className="text-lg font-semibold mb-4">快速开始</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <button
              key={index}
              onClick={action.action}
              className="bg-surface border border-border rounded-xl p-5 text-left hover:bg-card hover:border-accent/50 transition-all group"
            >
              <action.icon className={`w-8 h-8 ${action.color} mb-3`} />
              <h4 className="font-semibold mb-1">{action.title}</h4>
              <p className="text-sm text-muted">{action.description}</p>
              <ArrowRight className="w-4 h-4 mt-3 text-muted group-hover:text-accent transition-colors" />
            </button>
          ))}
        </div>
      </div>

      {/* 最近项目 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">最近项目</h3>
          <button
            onClick={() => navigate('/code-map')}
            className="text-sm text-accent hover:underline"
          >
            查看全部
          </button>
        </div>
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-card border-b border-border">
              <tr>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted">项目名称</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted">文件数</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted">最后索引</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted">状态</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-muted">操作</th>
              </tr>
            </thead>
            <tbody>
              {recentProjects.map((project, index) => (
                <tr key={index} className="border-b border-border last:border-0 hover:bg-card/50">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <Code2 className="w-4 h-4 text-accent" />
                      <span>{project.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-muted">{project.files}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1 text-muted text-sm">
                      <Clock className="w-3 h-3" />
                      {project.lastIndexed}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded text-xs ${
                      project.status === 'ready'
                        ? 'bg-success/20 text-success'
                        : 'bg-warning/20 text-warning'
                    }`}>
                      {project.status === 'ready' ? '就绪' : '需更新'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <button
                      onClick={() => navigate('/code-map')}
                      className="text-accent hover:underline text-sm"
                    >
                      查看
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 核心功能 */}
      <div>
        <h3 className="text-lg font-semibold mb-4">核心功能</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-surface border border-border rounded-xl p-4 text-center hover:bg-card transition-colors"
            >
              <feature.icon className="w-8 h-8 text-accent mx-auto mb-2" />
              <h4 className="font-semibold">{feature.title}</h4>
              <p className="text-sm text-muted mt-1">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
