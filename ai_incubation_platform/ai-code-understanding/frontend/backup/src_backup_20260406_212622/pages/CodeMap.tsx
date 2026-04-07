// 代码地图页面
import React, { useState } from 'react';
import { Folder, FileCode, ChevronRight, ChevronDown, Box, Layers } from 'lucide-react';
import { understandingApi } from '@/services/api';
import { toast } from 'sonner';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  symbols?: SymbolInfo[];
}

interface SymbolInfo {
  name: string;
  type: 'function' | 'class' | 'variable' | 'import';
  line?: number;
}

const CodeMap: React.FC = () => {
  const [projectName, setProjectName] = useState('ai-code-understanding');
  const [repoPath, setRepoPath] = useState('/Users/sunmuchao/Downloads/ai_incubation_platform/ai-code-understanding');
  const [loading, setLoading] = useState(false);
  const [fileTree, setFileTree] = useState<FileNode[] | null>(null);
  const [architecture, setArchitecture] = useState<any>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'tree' | 'architecture'>('tree');

  const loadProjectMap = async () => {
    setLoading(true);
    try {
      const response = await understandingApi.globalMap({
        project_name: projectName,
        repo_hint: repoPath,
        format: 'json'
      });

      if (response.success && response.data) {
        setArchitecture(response.data);
        // 从架构数据构建文件树
        const tree = buildFileTree(response.data.layers || []);
        setFileTree(tree);
        toast.success('代码地图加载成功');
      }
    } catch (error: any) {
      toast.error('加载失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const buildFileTree = (layers: any[]): FileNode[] => {
    // 简化实现，实际应该根据 API 返回构建完整的树结构
    return layers.map(layer => ({
      name: layer.name,
      path: `layer/${layer.name}`,
      type: 'directory',
      children: layer.files?.map((file: string) => ({
        name: file.split('/').pop() || file,
        path: file,
        type: 'file'
      })) || []
    }));
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：加载面板 */}
      <div className="w-80 bg-surface border border-border rounded-xl p-4 flex flex-col">
        <h3 className="font-semibold mb-4">加载项目</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">项目名称</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
              placeholder="my-project"
            />
          </div>

          <div>
            <label className="block text-sm text-muted mb-1">仓库路径</label>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
              placeholder="/path/to/repo"
            />
          </div>

          <button
            onClick={loadProjectMap}
            disabled={loading}
            className="w-full bg-accent hover:bg-accent/90 text-white rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
          >
            {loading ? '加载中...' : '加载代码地图'}
          </button>
        </div>

        {architecture && (
          <div className="mt-6 pt-6 border-t border-border">
            <h4 className="text-sm font-medium mb-3">项目信息</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">技术栈</span>
                <span>{architecture.stack?.languages?.join(', ') || '未知'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">架构层</span>
                <span>{architecture.layers?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">入口点</span>
                <span>{architecture.entrypoints?.length || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 右侧：地图内容 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        {/* 标签页 */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab('tree')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'tree'
                ? 'text-accent border-b-2 border-accent'
                : 'text-muted hover:text-text'
            }`}
          >
            <div className="flex items-center gap-2">
              <Folder className="w-4 h-4" />
              文件树
            </div>
          </button>
          <button
            onClick={() => setActiveTab('architecture')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'architecture'
                ? 'text-accent border-b-2 border-accent'
                : 'text-muted hover:text-text'
            }`}
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              架构分层
            </div>
          </button>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-auto p-4">
          {activeTab === 'tree' && (
            <div>
              {fileTree ? (
                <div className="space-y-2">
                  {fileTree.map((node) => (
                    <FileTreeNode
                      key={node.path}
                      node={node}
                      depth={0}
                      onSelect={setSelectedFile}
                      selectedFile={selectedFile}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState message="点击 &quot;加载代码地图&quot; 开始" />
              )}
            </div>
          )}

          {activeTab === 'architecture' && architecture ? (
            <div className="space-y-4">
              {architecture.layers?.map((layer: any, index: number) => (
                <div
                  key={index}
                  className="bg-background border border-border rounded-lg p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Box className="w-5 h-5 text-accent" />
                    <h4 className="font-semibold">{layer.name}</h4>
                  </div>
                  <p className="text-sm text-muted mb-3">{layer.description}</p>
                  <div className="flex flex-wrap gap-2">
                    {layer.files?.slice(0, 10).map((file: string, i: number) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-card rounded text-xs text-muted"
                      >
                        {file.split('/').pop()}
                      </span>
                    ))}
                    {layer.files?.length > 10 && (
                      <span className="px-2 py-1 text-xs text-muted">
                        +{layer.files.length - 10} 更多
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : activeTab === 'architecture' ? (
            <EmptyState message="请先加载代码地图" />
          ) : null}
        </div>
      </div>
    </div>
  );
};

// 文件树节点组件
const FileTreeNode: React.FC<{
  node: FileNode;
  depth: number;
  onSelect: (path: string) => void;
  selectedFile: string | null;
}> = ({ node, depth, onSelect, selectedFile }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1 px-2 rounded hover:bg-card cursor-pointer ${
          selectedFile === node.path ? 'bg-card' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          if (node.type === 'directory') {
            setExpanded(!expanded);
          } else {
            onSelect(node.path);
          }
        }}
      >
        {node.type === 'directory' && (
          expanded ? <ChevronDown className="w-4 h-4 text-muted" /> : <ChevronRight className="w-4 h-4 text-muted" />
        )}
        {node.type === 'directory' ? (
          <Folder className="w-4 h-4 text-accent" />
        ) : (
          <FileCode className="w-4 h-4 text-muted" />
        )}
        <span className="text-sm">{node.name}</span>
      </div>
      {expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
              selectedFile={selectedFile}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// 空状态组件
const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="h-full flex items-center justify-center text-muted">
    <p>{message}</p>
  </div>
);

export default CodeMap;
