// 设置页面
import React, { useState } from 'react';
import { Key, Database, Bell, Palette, Trash2, Save, AlertTriangle, FileIcon } from 'lucide-react';
import { authApi } from '@/services/api';
import { toast } from 'sonner';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'api' | 'appearance' | 'notifications' | 'data'>('api');
  const [apiKey, setApiKey] = useState(localStorage.getItem('api_key') || '');
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [notifications, setNotifications] = useState({
    emailDigest: false,
    pushNotifications: true,
    codeReviewAlerts: true,
    indexCompletion: true,
  });

  const handleGenerateKey = async () => {
    try {
      const response = await authApi.manage('create', { name: newKeyName || 'New Key', expires_in_days: 30 });
      if (response.success) {
        const apiKeyValue = (response as any).api_key || (response as any).data?.api_key;
        setGeneratedKey(apiKeyValue || '');
        localStorage.setItem('api_key', apiKeyValue || '');
        setApiKey(apiKeyValue || '');
        toast.success('API Key 生成成功，请妥善保管');
      }
    } catch (error: any) {
      toast.error('生成失败：' + error.message);
    }
  };

  const handleSaveKey = () => {
    localStorage.setItem('api_key', apiKey);
    toast.success('API Key 已保存');
  };

  const handleClearKey = () => {
    localStorage.removeItem('api_key');
    setApiKey('');
    setGeneratedKey('');
    toast.success('API Key 已清除');
  };

  const handleCopyKey = async () => {
    if (apiKey) {
      await navigator.clipboard.writeText(apiKey);
      toast.success('已复制到剪贴板');
    }
  };

  const tabs = [
    { id: 'api', label: 'API 配置', icon: Key },
    { id: 'appearance', label: '外观', icon: Palette },
    { id: 'notifications', label: '通知', icon: Bell },
    { id: 'data', label: '数据管理', icon: Database },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">设置</h2>

      {/* 标签页 */}
      <div className="flex gap-2 mb-6 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-accent text-white'
                : 'bg-surface text-muted hover:text-text hover:bg-card'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div className="bg-surface border border-border rounded-xl p-6">
        {activeTab === 'api' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4">API Key 管理</h3>

              {/* 当前 Key */}
              <div className="mb-6">
                <label className="block text-sm text-muted mb-2">当前 API Key</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="flex-1 bg-background border border-border rounded-lg px-4 py-2 font-mono text-sm focus:border-accent"
                    placeholder="sk-..."
                  />
                  <button
                    onClick={handleCopyKey}
                    className="px-4 py-2 bg-card hover:bg-card/80 rounded-lg transition-colors"
                  >
                    复制
                  </button>
                  <button
                    onClick={handleSaveKey}
                    className="px-4 py-2 bg-accent hover:bg-accent/90 text-white rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    保存
                  </button>
                </div>
              </div>

              {/* 生成新 Key */}
              <div>
                <label className="block text-sm text-muted mb-2">生成新 API Key</label>
                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="flex-1 bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-accent"
                    placeholder="Key 名称（可选）"
                  />
                  <button
                    onClick={handleGenerateKey}
                    className="px-4 py-2 bg-accent hover:bg-accent/90 text-white rounded-lg transition-colors"
                  >
                    生成
                  </button>
                </div>

                {generatedKey && (
                  <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-warning font-medium mb-2">请妥善保管此 API Key</p>
                        <p className="text-sm text-muted mb-2">此 Key 只会显示一次，刷新页面后将无法查看</p>
                        <div className="flex gap-2">
                          <code className="block bg-black/30 rounded px-3 py-2 text-sm font-mono break-all">
                            {generatedKey}
                          </code>
                          <button
                            onClick={handleCopyKey}
                            className="px-3 py-2 bg-warning/20 hover:bg-warning/30 rounded transition-colors"
                          >
                            复制
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-6 border-t border-border">
              <button
                onClick={handleClearKey}
                className="px-4 py-2 bg-error/20 text-error hover:bg-error/30 rounded-lg transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                清除 API Key
              </button>
            </div>
          </div>
        )}

        {activeTab === 'appearance' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4">主题设置</h3>
              <div className="flex gap-4">
                <button
                  onClick={() => setTheme('dark')}
                  className={`flex-1 p-4 rounded-xl border-2 transition-colors ${
                    theme === 'dark'
                      ? 'border-accent bg-card'
                      : 'border-border bg-background hover:border-accent/50'
                  }`}
                >
                  <div className="w-full h-20 bg-gray-900 rounded-lg mb-2" />
                  <p className="font-medium">暗色主题</p>
                  <p className="text-sm text-muted">适合低光环境</p>
                </button>
                <button
                  onClick={() => setTheme('light')}
                  className={`flex-1 p-4 rounded-xl border-2 transition-colors ${
                    theme === 'light'
                      ? 'border-accent bg-card'
                      : 'border-border bg-background hover:border-accent/50'
                  }`}
                >
                  <div className="w-full h-20 bg-gray-100 rounded-lg mb-2" />
                  <p className="font-medium">亮色主题</p>
                  <p className="text-sm text-muted">适合日间使用</p>
                </button>
              </div>
            </div>

            <div className="pt-6 border-t border-border">
              <h3 className="text-lg font-semibold mb-4">语言设置</h3>
              <select className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-accent">
                <option value="zh-CN">简体中文</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold mb-4">通知偏好</h3>

            {[
              { key: 'emailDigest', label: '邮件摘要', desc: '每周发送使用报告和功能更新' },
              { key: 'pushNotifications', label: '推送通知', desc: '在浏览器中接收实时通知' },
              { key: 'codeReviewAlerts', label: '代码审查提醒', desc: '发现严重问题时通知' },
              { key: 'indexCompletion', label: '索引完成通知', desc: '项目索引完成后通知' },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between py-3 border-b border-border last:border-0">
                <div>
                  <p className="font-medium">{item.label}</p>
                  <p className="text-sm text-muted">{item.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifications[item.key as keyof typeof notifications]}
                    onChange={(e) => setNotifications({ ...notifications, [item.key]: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-card peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent"></div>
                </label>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4">缓存管理</h3>
              <div className="bg-background rounded-lg p-4 mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-muted">本地缓存大小</span>
                  <span className="font-mono">24.5 MB</span>
                </div>
                <div className="w-full bg-card rounded-full h-2">
                  <div className="bg-accent h-2 rounded-full" style={{ width: '35%' }} />
                </div>
              </div>
              <button className="px-4 py-2 bg-card hover:bg-card/80 rounded-lg transition-colors">
                清除缓存
              </button>
            </div>

            <div className="pt-6 border-t border-border">
              <h3 className="text-lg font-semibold mb-4">数据导出</h3>
              <div className="flex gap-2">
                <button className="px-4 py-2 bg-card hover:bg-card/80 rounded-lg transition-colors flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  导出项目数据
                </button>
                <button className="px-4 py-2 bg-card hover:bg-card/80 rounded-lg transition-colors flex items-center gap-2">
                  <FileIcon className="w-4 h-4" />
                  导出配置
                </button>
              </div>
            </div>

            <div className="pt-6 border-t border-border">
              <h3 className="text-lg font-semibold mb-4 text-error">危险区域</h3>
              <button className="px-4 py-2 bg-error/20 text-error hover:bg-error/30 rounded-lg transition-colors">
                重置所有设置
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;