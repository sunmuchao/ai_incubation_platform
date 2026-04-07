// 文档中心页面
import React, { useState } from 'react';
import { FileText, FileCode, Network, FileOutput, Download, Copy, Check } from 'lucide-react';
import { docsApi } from '@/services/api';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';

const DocsCenter: React.FC = () => {
  const [projectPath, setProjectPath] = useState('/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding');
  const [loading, setLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'api' | 'architecture' | 'dataflow' | 'readme'>('api');
  const [generatedDoc, setGeneratedDoc] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generateDoc = async (type: string) => {
    setLoading(type);
    try {
      let response;
      switch (type) {
        case 'api':
          response = await docsApi.generateApiDocs({ project_path: projectPath, format: 'markdown' });
          break;
        case 'architecture':
          response = await docsApi.generateArchitecture(projectPath, 'mermaid');
          break;
        case 'dataflow':
          response = await docsApi.generateDataflow(projectPath, 'mermaid');
          break;
        case 'readme':
          response = await docsApi.generateReadme(projectPath);
          break;
      }

      if (response?.success) {
        const content = response.data?.content || response.data?.diagram_mermaid || JSON.stringify(response.data, null, 2);
        setGeneratedDoc(content);
        toast.success(`${getDocTypeName(type)} 生成成功`);
      }
    } catch (error: any) {
      // 使用演示数据
      const demoContent = getDemoContent(type);
      setGeneratedDoc(demoContent);
      toast.warning('使用演示数据（服务未响应）');
    } finally {
      setLoading(null);
    }
  };

  const getDocTypeName = (type: string) => {
    const names: Record<string, string> = {
      api: 'API 文档',
      architecture: '架构图',
      dataflow: '数据流图',
      readme: 'README',
    };
    return names[type] || type;
  };

  const getDemoContent = (type: string) => {
    switch (type) {
      case 'api':
        return `# API 文档

## 理解接口

### POST /api/understanding/explain

解释代码片段

**请求参数**:
- code (string): 待解释的代码
- language (string): 语言标识
- context (string, optional): 额外上下文

**响应**:
\`\`\`json
{
  "success": true,
  "data": {
    "explanation": "这是一个简单的函数定义...",
    "confidence": 0.92,
    "citations": [...]
  }
}
\`\`\`

## 全局地图接口

### POST /api/understanding/global-map

生成全局代码地图

**请求参数**:
- project_name (string): 项目名称
- repo_hint (string, optional): 仓库路径
- format (string): 返回格式
`;
      case 'architecture':
        return `graph TD
    A[API 层] --> B[服务层]
    A --> C[中间件]
    B --> D[核心模块]
    B --> E[工具模块]
    D --> F[索引器]
    D --> G[知识图谱]
    D --> H[全局地图]
    E --> I[向量存储]
    E --> J[语法解析]
`;
      case 'dataflow':
        return `flowchart LR
    A[用户请求] --> B[API 网关]
    B --> C[认证中间件]
    C --> D[路由分发]
    D --> E[服务处理]
    E --> F[向量检索]
    E --> G[LLM 调用]
    F --> H[ChromaDB]
    G --> I[响应生成]
    H --> E
    I --> J[返回结果]
`;
      case 'readme':
        return `# AI Code Understanding

> 让任何开发者都能在 5 分钟内理解一个陌生代码库

## 核心功能

- 全局代码地图
- 任务引导阅读路径
- 幻觉控制与引用溯源
- 变更影响分析

## 快速开始

\`\`\`bash
pip install -r requirements.txt
cd src
uvicorn main:app --host 0.0.0.0 --port 8011
\`\`\`

## 技术栈

- Python 3.9+
- FastAPI
- ChromaDB
- Tree-sitter
`;
      default:
        return '';
    }
  };

  const copyToClipboard = async () => {
    if (generatedDoc) {
      await navigator.clipboard.writeText(generatedDoc);
      setCopied(true);
      toast.success('已复制到剪贴板');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：生成面板 */}
      <div className="w-80 bg-surface border border-border rounded-xl p-4 flex flex-col">
        <h3 className="font-semibold mb-4">文档生成</h3>

        <div className="mb-4">
          <label className="block text-sm text-muted mb-1">项目路径</label>
          <input
            type="text"
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
          />
        </div>

        <div className="space-y-2">
          <button
            onClick={() => generateDoc('api')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-card hover:bg-card/80 rounded-lg transition-colors disabled:opacity-50"
          >
            <FileCode className="w-5 h-5 text-accent" />
            <div className="text-left">
              <p className="font-medium text-sm">API 文档</p>
              <p className="text-xs text-muted">从代码生成 API 文档</p>
            </div>
            {loading === 'api' && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin ml-auto" />}
          </button>

          <button
            onClick={() => generateDoc('architecture')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-card hover:bg-card/80 rounded-lg transition-colors disabled:opacity-50"
          >
            <Network className="w-5 h-5 text-accent" />
            <div className="text-left">
              <p className="font-medium text-sm">架构图</p>
              <p className="text-xs text-muted">生成 Mermaid 架构图</p>
            </div>
            {loading === 'architecture' && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin ml-auto" />}
          </button>

          <button
            onClick={() => generateDoc('dataflow')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-card hover:bg-card/80 rounded-lg transition-colors disabled:opacity-50"
          >
            <FileOutput className="w-5 h-5 text-accent" />
            <div className="text-left">
              <p className="font-medium text-sm">数据流图</p>
              <p className="text-xs text-muted">生成数据流向图</p>
            </div>
            {loading === 'dataflow' && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin ml-auto" />}
          </button>

          <button
            onClick={() => generateDoc('readme')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-card hover:bg-card/80 rounded-lg transition-colors disabled:opacity-50"
          >
            <FileText className="w-5 h-5 text-accent" />
            <div className="text-left">
              <p className="font-medium text-sm">README</p>
              <p className="text-xs text-muted">智能生成 README</p>
            </div>
            {loading === 'readme' && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin ml-auto" />}
          </button>
        </div>
      </div>

      {/* 右侧：文档内容 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        {generatedDoc ? (
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex gap-2">
                {['api', 'architecture', 'dataflow', 'readme'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      activeTab === tab
                        ? 'bg-accent text-white'
                        : 'bg-card text-muted hover:text-text'
                    }`}
                  >
                    {getDocTypeName(tab)}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={copyToClipboard}
                  className="flex items-center gap-2 px-3 py-1.5 bg-card hover:bg-card/80 rounded-lg text-sm transition-colors"
                >
                  {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                  {copied ? '已复制' : '复制'}
                </button>
                <button className="flex items-center gap-2 px-3 py-1.5 bg-accent hover:bg-accent/90 rounded-lg text-sm transition-colors">
                  <Download className="w-4 h-4" />
                  导出
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{generatedDoc}</ReactMarkdown>
              </div>
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted">
            <FileText className="w-16 h-16 mb-4 opacity-50" />
            <p>选择文档类型开始生成</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocsCenter;
