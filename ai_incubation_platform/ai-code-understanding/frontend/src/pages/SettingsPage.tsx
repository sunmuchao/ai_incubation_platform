// 设置页面 - Bento Grid 风格
import React, { useState, useEffect } from 'react';
import { Key, Trash2, Plus, CheckCircle, AlertCircle, Copy, Shield, Info } from 'lucide-react';
import { authApi } from '@/services/api';
import { copyToClipboard } from '@/utils';

interface ApiKeyInfo {
  key: string;
  name: string;
  created_at: string;
  expires_at?: string;
  is_active: boolean;
}

const SettingsPage: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [expiresDays, setExpiresDays] = useState(30);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 加载 API Keys
  const loadApiKeys = async () => {
    try {
      const result = await authApi.manage('list');
      if (result.success && result.data) {
        setApiKeys(result.data.keys || []);
      }
    } catch (error: any) {
      console.error('加载 API Keys 失败:', error);
    }
  };

  useEffect(() => {
    loadApiKeys();
  }, []);

  // 创建新的 API Key
  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      setMessage({ type: 'error', text: '请输入密钥名称' });
      return;
    }

    setLoading(true);
    try {
      const result = await authApi.manage('create', {
        name: newKeyName,
        expires_in_days: expiresDays,
      });

      if (result.success && result.data) {
        setGeneratedKey(result.data.api_key);
        setMessage({ type: 'success', text: 'API Key 创建成功，请妥善保管' });
        setNewKeyName('');
        loadApiKeys();
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '创建失败' });
    } finally {
      setLoading(false);
    }
  };

  // 撤销 API Key
  const handleRevokeKey = async (key: string) => {
    if (!confirm('确定要撤销这个 API Key 吗？此操作不可恢复。')) return;

    try {
      const result = await authApi.manage('revoke', { key });
      if (result.success) {
        setMessage({ type: 'success', text: 'API Key 已撤销' });
        loadApiKeys();
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || '撤销失败' });
    }
  };

  // 复制 API Key
  const handleCopyKey = async (key: string) => {
    const success = await copyToClipboard(key);
    if (success) {
      setMessage({ type: 'success', text: '已复制到剪贴板' });
    }
  };

  // 设置当前使用的 API Key
  const handleSetCurrentKey = (key: string) => {
    localStorage.setItem('api_key', key);
    setMessage({ type: 'success', text: '已设置当前使用的 API Key' });
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl gradient-accent flex items-center justify-center shadow-glow-accent">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-text-primary">设置</h2>
          <p className="text-xs text-text-muted">管理 API 密钥和系统配置</p>
        </div>
      </div>

      {/* 消息提示 */}
      {message && (
        <div
          className={`bento-card p-4 flex items-center gap-3 ${
            message.type === 'success'
              ? 'border-success/30 bg-success/10'
              : 'border-error/30 bg-error/10'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-success" />
          ) : (
            <AlertCircle className="w-5 h-5 text-error" />
          )}
          <span className={`text-sm ${
            message.type === 'success' ? 'text-success' : 'text-error'
          }`}>
            {message.text}
          </span>
        </div>
      )}

      {/* Bento Grid 布局 */}
      <div className="bento-grid">
        {/* API Key 管理 - 主卡片 */}
        <div className="bento-card p-6 bento-span-8">
          <div className="flex items-center gap-2 mb-6">
            <Key className="w-5 h-5 text-accent" />
            <h3 className="text-lg font-semibold text-text-primary">API Key 管理</h3>
          </div>

          {/* 创建新密钥 */}
          <div className="mb-6 p-4 bg-surface-lighter rounded-lg border border-border-light">
            <h4 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              创建新密钥
            </h4>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="block text-xs text-text-muted mb-1.5 font-medium">密钥名称</label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="例如：开发密钥"
                  className="w-full bg-surface border border-border-light rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition-all duration-200"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1.5 font-medium">有效期（天）</label>
                <input
                  type="number"
                  value={expiresDays}
                  onChange={(e) => setExpiresDays(Number(e.target.value))}
                  min={1}
                  max={365}
                  className="w-28 bg-surface border border-border-light rounded-lg px-3 py-2.5 text-sm text-text-primary focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition-all duration-200"
                />
              </div>
              <button
                onClick={handleCreateKey}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium text-sm shadow-glow-accent hover:shadow-lg"
              >
                <Plus className="w-4 h-4" />
                创建
              </button>
            </div>
          </div>

          {/* 新生成的密钥显示 */}
          {generatedKey && (
            <div className="mb-6 p-4 rounded-lg border border-success/30 bg-success/10">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-success font-semibold flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  新密钥已生成
                </span>
                <button
                  onClick={() => handleCopyKey(generatedKey)}
                  className="text-xs text-success hover:underline flex items-center gap-1 font-medium"
                >
                  <Copy className="w-3 h-3" />
                  复制
                </button>
              </div>
              <code className="block p-3 bg-surface border border-border-light rounded text-xs break-all font-mono text-text-secondary">
                {generatedKey}
              </code>
              <p className="text-xs text-text-muted mt-2 flex items-center gap-1">
                <Info className="w-3 h-3" />
                请妥善保管此密钥，它只会显示一次
              </p>
            </div>
          )}

          {/* 密钥列表 */}
          <div>
            <h4 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <Key className="w-4 h-4" />
              已创建的密钥
            </h4>
            {apiKeys.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <Key className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">暂无密钥</p>
              </div>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((keyInfo, index) => (
                  <div
                    key={index}
                    className="group flex items-center justify-between p-4 bg-surface-lighter border border-border-light rounded-lg hover:border-accent/30 transition-all duration-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        keyInfo.is_active
                          ? 'bg-success/10 border border-success/30'
                          : 'bg-surface border border-border-light'
                      }`}>
                        <Key className={`w-5 h-5 ${
                          keyInfo.is_active ? 'text-success' : 'text-text-muted'
                        }`} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-text-primary">{keyInfo.name}</div>
                        <div className="text-xs text-text-muted mt-0.5">
                          创建于 {keyInfo.created_at}
                          {keyInfo.expires_at && (
                            <span className="ml-2">
                              · 过期：{keyInfo.expires_at}
                            </span>
                          )}
                          {!keyInfo.is_active && (
                            <span className="ml-2 text-error">· 已失效</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <button
                        onClick={() => handleSetCurrentKey(keyInfo.key)}
                        className="px-4 py-2 text-xs bg-accent/20 text-accent rounded-lg hover:bg-accent/30 transition-colors font-medium"
                      >
                        使用此密钥
                      </button>
                      <button
                        onClick={() => handleRevokeKey(keyInfo.key)}
                        className="p-2 text-text-muted hover:text-error transition-colors rounded-lg hover:bg-error/10"
                        title="撤销"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 右侧信息卡片 */}
        <div className="space-y-4 bento-span-4">
          {/* 关于卡片 */}
          <div className="bento-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-accent" />
              <h3 className="text-base font-semibold text-text-primary">关于</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between py-2 border-b border-border-light">
                <span className="text-text-muted">版本</span>
                <span className="text-text-primary font-medium">v3.0 AI Native</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-border-light">
                <span className="text-text-muted">架构</span>
                <span className="text-text-primary font-medium">Multi-Agent</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-text-muted">模式</span>
                <span className="text-text-primary font-medium">对话式</span>
              </div>
            </div>
          </div>

          {/* 核心功能 */}
          <div className="bento-card p-5">
            <h3 className="text-base font-semibold text-text-primary mb-4">核心功能</h3>
            <ul className="space-y-2">
              {['对话式交互', '动态生成 UI', '多 Agent 协作', '自主代码探索'].map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <CheckCircle className="w-4 h-4 text-success" />
                  <span className="text-text-secondary">{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 快速提示 */}
          <div className="bento-card p-5 gradient-subtle">
            <h3 className="text-base font-semibold text-text-primary mb-3">💡 提示</h3>
            <p className="text-xs text-text-secondary leading-relaxed">
              AI 代码理解助手 - 让任何开发者都能在 5 分钟内理解一个陌生代码库
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
