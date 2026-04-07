// 代码审查页面
import React, { useState } from 'react';
import { FileCheck, AlertTriangle, Shield, Zap, BookOpen, XCircle } from 'lucide-react';
import { understandingApi } from '@/services/api';
import Editor from '@monaco-editor/react';
import { toast } from 'sonner';

interface CodeIssue {
  type: 'smell' | 'security' | 'performance' | 'style';
  severity: 'error' | 'warning' | 'info';
  line?: number;
  message: string;
  suggestion?: string;
  rule?: string;
}

interface ReviewResult {
  summary: string;
  issues: CodeIssue[];
  score: number;
}

const CodeReview: React.FC = () => {
  const [code, setCode] = useState(`def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total

def process_user_input(user_input):
    # 潜在的安全风险：直接使用 eval
    result = eval(user_input)
    return result

def fetch_data(url):
    import requests
    # 缺少超时设置
    response = requests.get(url)
    return response.json()`);
  const [language, setLanguage] = useState('python');
  const [loading, setLoading] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);

  const handleReview = async () => {
    setLoading(true);
    try {
      const response = await understandingApi.reviewCode({
        code,
        language,
        config: {
          enable_smell_detection: true,
          enable_security_check: true,
          enable_performance_check: true,
          enable_style_check: true,
        },
      });

      if (response.success && response.data) {
        setReviewResult(response.data);
        toast.success('代码审查完成');
      }
    } catch (error: any) {
      // 使用演示数据
      const demoResult: ReviewResult = {
        summary: '代码审查完成，发现 3 个问题需要关注',
        issues: [
          {
            type: 'security',
            severity: 'error',
            line: 9,
            message: '使用 eval() 执行用户输入存在严重安全风险',
            suggestion: '使用 ast.literal_eval() 或明确的解析逻辑替代 eval()',
            rule: 'SEC001',
          },
          {
            type: 'smell',
            severity: 'warning',
            line: 3,
            message: '使用 range(len(items)) 不是 Pythonic 的写法',
            suggestion: '改用 enumerate() 或直接迭代：for item in items:',
            rule: 'SMELL002',
          },
          {
            type: 'performance',
            severity: 'warning',
            line: 15,
            message: 'HTTP 请求缺少超时设置，可能导致程序挂起',
            suggestion: '添加 timeout 参数：requests.get(url, timeout=30)',
            rule: 'PERF001',
          },
        ],
        score: 72,
      };
      setReviewResult(demoResult);
      toast.warning('使用演示数据（服务未响应）');
    } finally {
      setLoading(false);
    }
  };

  const getIssueIcon = (type: string) => {
    switch (type) {
      case 'security':
        return <Shield className="w-4 h-4" />;
      case 'smell':
        return <AlertTriangle className="w-4 h-4" />;
      case 'performance':
        return <Zap className="w-4 h-4" />;
      case 'style':
        return <BookOpen className="w-4 h-4" />;
      default:
        return <FileCheck className="w-4 h-4" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'info':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      default:
        return 'text-muted';
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：代码编辑器 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold">代码输入</h3>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="go">Go</option>
          </select>
        </div>
        <div className="flex-1 overflow-hidden">
          <Editor
            height="100%"
            language={language}
            value={code}
            onChange={(value) => setCode(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </div>
        <div className="p-4 border-t border-border">
          <button
            onClick={handleReview}
            disabled={loading || !code.trim()}
            className="w-full bg-accent hover:bg-accent/90 text-white rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
          >
            {loading ? '审查中...' : '开始代码审查'}
          </button>
        </div>
      </div>

      {/* 右侧：审查结果 */}
      <div className="w-96 bg-surface border border-border rounded-xl flex flex-col">
        {reviewResult ? (
          <>
            {/* 分数概览 */}
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">审查结果</h3>
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg ${
                    reviewResult.score >= 80
                      ? 'bg-green-500/20 text-green-400'
                      : reviewResult.score >= 60
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {reviewResult.score}
                </div>
              </div>
              <p className="text-sm text-muted">{reviewResult.summary}</p>
            </div>

            {/* 问题列表 */}
            <div className="flex-1 overflow-auto p-4 space-y-3">
              {reviewResult.issues.map((issue, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border ${getSeverityColor(issue.severity)}`}
                >
                  <div className="flex items-start gap-2 mb-2">
                    <div className="flex-shrink-0 mt-0.5">
                      {issue.severity === 'error' ? (
                        <XCircle className="w-4 h-4" />
                      ) : (
                        <AlertTriangle className="w-4 h-4" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getIssueIcon(issue.type)}
                        <span className="text-xs uppercase font-medium">{issue.type}</span>
                        {issue.line && (
                          <span className="text-xs opacity-70">行 {issue.line}</span>
                        )}
                      </div>
                      <p className="text-sm mb-2">{issue.message}</p>
                      {issue.suggestion && (
                        <div className="bg-black/20 rounded p-2 text-xs">
                          <p className="text-green-400 mb-1">建议:</p>
                          <p>{issue.suggestion}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted p-8">
            <FileCheck className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-center">点击"开始代码审查"</p>
            <p className="text-center text-sm">检测代码异味、安全风险、性能问题</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CodeReview;
