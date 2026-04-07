// 代码探索器页面 - Bento Grid 风格
import React, { useState } from 'react';
import { Folder, FileCode, ChevronRight, ChevronDown, Search, FileJson, FileBox, Hash } from 'lucide-react';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  language?: string;
}

// 模拟文件树数据
const mockFileTree: FileNode[] = [
  {
    name: 'src',
    path: '/src',
    type: 'directory',
    children: [
      {
        name: 'api',
        path: '/src/api',
        type: 'directory',
        children: [
          { name: 'chat.py', path: '/src/api/chat.py', type: 'file', language: 'python' },
          { name: 'understanding.py', path: '/src/api/understanding.py', type: 'file', language: 'python' },
          { name: 'generative_ui.py', path: '/src/api/generative_ui.py', type: 'file', language: 'python' },
        ],
      },
      {
        name: 'agents',
        path: '/src/agents',
        type: 'directory',
        children: [
          { name: 'code_agent.py', path: '/src/agents/code_agent.py', type: 'file', language: 'python' },
          { name: 'explorer_agent.py', path: '/src/agents/explorer_agent.py', type: 'file', language: 'python' },
        ],
      },
      {
        name: 'services',
        path: '/src/services',
        type: 'directory',
        children: [
          { name: 'indexer.py', path: '/src/services/indexer.py', type: 'file', language: 'python' },
          { name: 'search.py', path: '/src/services/search.py', type: 'file', language: 'python' },
        ],
      },
      { name: 'main.py', path: '/src/main.py', type: 'file', language: 'python' },
    ],
  },
  {
    name: 'frontend',
    path: '/frontend',
    type: 'directory',
    children: [
      {
        name: 'src',
        path: '/frontend/src',
        type: 'directory',
        children: [
          { name: 'App.tsx', path: '/frontend/src/App.tsx', type: 'file', language: 'typescript' },
          { name: 'main.tsx', path: '/frontend/src/main.tsx', type: 'file', language: 'typescript' },
        ],
      },
      { name: 'package.json', path: '/frontend/package.json', type: 'file', language: 'json' },
    ],
  },
  { name: 'README.md', path: '/README.md', type: 'file', language: 'markdown' },
  { name: 'requirements.txt', path: '/requirements.txt', type: 'file', language: 'text' },
];

const CodeExplorer: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['/src', '/src/api', '/src/agents', '/src/services', '/frontend', '/frontend/src']));

  const toggleExpand = (path: string) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedPaths(newExpanded);
  };

  const filterTree = (nodes: FileNode[], query: string): FileNode[] => {
    if (!query) return nodes;

    return nodes.reduce<FileNode[]>((acc, node) => {
      const matches = node.name.toLowerCase().includes(query.toLowerCase());
      if (node.type === 'file' && matches) {
        acc.push(node);
      } else if (node.type === 'directory') {
        const filteredChildren = filterTree(node.children || [], query);
        if (filteredChildren.length > 0 || matches) {
          acc.push({ ...node, children: filteredChildren });
        }
      }
      return acc;
    }, []);
  };

  const filteredTree = filterTree(mockFileTree, searchQuery);

  const getFileIcon = (language?: string) => {
    switch (language) {
      case 'python':
        return <Hash className="w-4 h-4" />;
      case 'typescript':
      case 'javascript':
        return <FileJson className="w-4 h-4" />;
      case 'json':
        return <FileJson className="w-4 h-4" />;
      default:
        return <FileCode className="w-4 h-4" />;
    }
  };

  const getFileIconColor = (language?: string) => {
    switch (language) {
      case 'python':
        return 'text-blue-400';
      case 'typescript':
        return 'text-cyan-400';
      case 'javascript':
        return 'text-yellow-400';
      case 'json':
        return 'text-green-400';
      case 'markdown':
        return 'text-purple-400';
      default:
        return 'text-text-secondary';
    }
  };

  return (
    <div className="h-full flex gap-4">
      {/* 文件树 - Bento Grid 左侧 */}
      <div className="w-80 flex flex-col gap-4">
        {/* 搜索卡片 */}
        <div className="bento-card p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="搜索文件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-lighter border border-border-light rounded-lg pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder-text-muted focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition-all duration-200"
            />
          </div>
        </div>

        {/* 文件列表卡片 */}
        <div className="bento-card flex-1 overflow-hidden flex flex-col">
          <div className="p-3 border-b border-border-light flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary">项目文件</span>
            <span className="text-xs text-text-muted">{countFiles(filteredTree)} 个文件</span>
          </div>
          <div className="flex-1 overflow-auto p-2">
            <FileTree
              nodes={filteredTree}
              expandedPaths={expandedPaths}
              onToggle={toggleExpand}
              onSelect={setSelectedFile}
              selectedFile={selectedFile}
              getFileIcon={getFileIcon}
              getFileIconColor={getFileIconColor}
            />
          </div>
        </div>
      </div>

      {/* 代码预览区 - Bento Grid 右侧 */}
      <div className="flex-1 bento-card p-6 flex flex-col">
        {selectedFile ? (
          <div className="flex-1 flex flex-col">
            <div className="flex items-center gap-3 mb-4 pb-4 border-b border-border-light">
              <div className="w-10 h-10 rounded-lg bg-surface-lighter border border-border-light flex items-center justify-center">
                {getFileIcon(mockFileTree.find(f => f.path === selectedFile)?.language)}
              </div>
              <div>
                <h3 className="text-base font-semibold text-text-primary">{selectedFile.split('/').pop()}</h3>
                <p className="text-xs text-text-muted">{selectedFile}</p>
              </div>
            </div>
            <div className="flex-1 bg-base-950 rounded-lg border border-border-light p-4 overflow-auto">
              <pre className="text-sm text-text-secondary font-mono">
                <code>// 选择文件后显示代码内容...</code>
              </pre>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 mb-6 rounded-2xl bg-surface-lighter border border-border-light flex items-center justify-center float">
              <FileBox className="w-10 h-10 text-text-muted" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">选择一个文件查看</h3>
            <p className="text-text-muted text-sm mb-6">或者让 AI 帮你分析代码</p>
            <div className="bento-card p-4 max-w-md">
              <p className="text-xs text-text-secondary">
                <span className="text-accent font-medium">提示：</span>
                在对话中输入 "帮我看看 src/main.py 是怎么工作的"
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// 文件树组件
const FileTree: React.FC<{
  nodes: FileNode[];
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (path: string) => void;
  selectedFile: string | null;
  getFileIcon: (language?: string) => React.ReactNode;
  getFileIconColor: (language?: string) => string;
  depth?: number;
}> = ({ nodes, expandedPaths, onToggle, onSelect, selectedFile, getFileIcon, getFileIconColor, depth = 0 }) => {
  return (
    <div className="space-y-0.5">
      {nodes.map((node) => (
        <div key={node.path}>
          <div
            onClick={() => {
              if (node.type === 'directory') {
                onToggle(node.path);
              } else {
                onSelect(node.path);
              }
            }}
            className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all duration-200 ${
              selectedFile === node.path
                ? 'bg-accent/20 border border-accent/30'
                : 'hover:bg-surface-lighter border border-transparent'
            }`}
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
          >
            {node.type === 'directory' ? (
              <>
                {expandedPaths.has(node.path) ? (
                  <ChevronDown className="w-4 h-4 text-text-muted" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-text-muted" />
                )}
                <Folder className="w-4 h-4 text-success" />
              </>
            ) : (
              <>
                <span className="w-4" />
                <div className={getFileIconColor(node.language)}>
                  {getFileIcon(node.language)}
                </div>
              </>
            )}
            <span className={`text-sm truncate ${
              selectedFile === node.path ? 'text-accent font-medium' : 'text-text-primary'
            }`}>
              {node.name}
            </span>
          </div>
          {node.type === 'directory' && expandedPaths.has(node.path) && node.children && (
            <FileTree
              nodes={node.children}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              onSelect={onSelect}
              selectedFile={selectedFile}
              getFileIcon={getFileIcon}
              getFileIconColor={getFileIconColor}
              depth={depth + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
};

// 辅助函数：计算文件数量
const countFiles = (nodes: FileNode[]): number => {
  let count = 0;
  nodes.forEach(node => {
    if (node.type === 'file') {
      count++;
    } else if (node.children) {
      count += countFiles(node.children);
    }
  });
  return count;
};

export default CodeExplorer;
