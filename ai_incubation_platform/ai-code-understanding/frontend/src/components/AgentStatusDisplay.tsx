// Agent 状态显示组件 - Bento Grid 风格
import React from 'react';
import { Brain, CheckCircle, AlertCircle, Loader2, Sparkles } from 'lucide-react';
import type { AgentStatus } from '@/types/chat';

interface AgentStatusDisplayProps {
  status: AgentStatus;
}

const AgentStatusDisplay: React.FC<AgentStatusDisplayProps> = ({ status }) => {
  const getStepStatus = (stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return (
          <div className="w-5 h-5 rounded-full bg-success/20 border border-success/30 flex items-center justify-center">
            <CheckCircle className="w-3 h-3 text-success" />
          </div>
        );
      case 'running':
        return (
          <div className="w-5 h-5 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center">
            <Loader2 className="w-3 h-3 text-accent animate-spin" />
          </div>
        );
      case 'error':
        return (
          <div className="w-5 h-5 rounded-full bg-error/20 border border-error/30 flex items-center justify-center">
            <AlertCircle className="w-3 h-3 text-error" />
          </div>
        );
      default:
        return (
          <div className="w-5 h-5 rounded-full bg-surface-lighter border border-border-light" />
        );
    }
  };

  const getStatusGradient = () => {
    switch (status.status) {
      case 'thinking':
        return 'from-blue-500/20 to-blue-600/10';
      case 'searching':
        return 'from-success/20 to-success/10';
      case 'analyzing':
        return 'from-purple-500/20 to-purple-600/10';
      case 'generating':
        return 'from-orange-500/20 to-orange-600/10';
      case 'complete':
        return 'from-success/20 to-success/10';
      case 'error':
        return 'from-error/20 to-error/10';
      default:
        return 'from-surface-lighter to-surface-lighter';
    }
  };

  const getStatusIconColor = () => {
    switch (status.status) {
      case 'thinking':
        return 'text-blue-400';
      case 'searching':
        return 'text-success';
      case 'analyzing':
        return 'text-purple-400';
      case 'generating':
        return 'text-orange-400';
      case 'complete':
        return 'text-success';
      case 'error':
        return 'text-error';
      default:
        return 'text-text-muted';
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case 'thinking':
        return 'AI 正在思考';
      case 'searching':
        return 'AI 正在检索代码';
      case 'analyzing':
        return 'AI 正在分析依赖';
      case 'generating':
        return 'AI 正在生成回答';
      case 'complete':
        return '分析完成';
      case 'error':
        return '分析出错';
      default:
        return '等待中';
    }
  };

  return (
    <div className="p-4">
      {/* 状态头部 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${getStatusGradient()} border border-border-light`}>
            <Brain className={`w-5 h-5 ${getStatusIconColor()}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-text-primary">{getStatusText()}</span>
              {status.status === 'complete' && (
                <Sparkles className="w-4 h-4 text-success animate-pulse" />
              )}
            </div>
            <div className="text-xs text-text-muted mt-0.5">{status.current_step}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* 进度百分比 */}
          <div className="text-sm font-mono text-text-secondary">
            <span className={status.progress === 100 ? 'text-success' : 'text-accent'}>
              {status.progress}
            </span>
            <span className="text-text-muted">%</span>
          </div>
        </div>
      </div>

      {/* 进度条 - 精致样式 */}
      <div className="h-2 bg-surface-lighter rounded-full overflow-hidden mb-4 border border-border-light">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-smooth relative overflow-hidden ${
            status.status === 'error'
              ? 'bg-gradient-to-r from-error to-error/60'
              : 'bg-gradient-to-r from-accent to-blue-400'
          }`}
          style={{ width: `${status.progress}%` }}
        >
          {/* 光泽效果 */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
        </div>
      </div>

      {/* 步骤列表 - Bento Grid */}
      <div className="grid grid-cols-4 gap-2">
        {status.steps.map((step, index) => (
          <div
            key={index}
            className={`flex items-center gap-2.5 p-2.5 rounded-lg border transition-all duration-200 ${
              step.status === 'running'
                ? 'bg-accent-glow border-accent/30 shadow-glow-accent'
                : step.status === 'completed'
                ? 'bg-success/10 border-success/30'
                : step.status === 'error'
                ? 'bg-error/10 border-error/30'
                : 'bg-surface-lighter border-border-light'
            }`}
          >
            {getStepStatus(step.status)}
            <span className={`text-xs truncate font-medium ${
              step.status === 'running' ? 'text-accent' :
              step.status === 'completed' ? 'text-success' :
              step.status === 'error' ? 'text-error' :
              'text-text-secondary'
            }`}>
              {step.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentStatusDisplay;
