// 代码搜索页面
import React, { useState } from 'react';
import { Search, FileCode, Hash, Type, Sparkles } from 'lucide-react';
import { docQaApi } from '@/services/api';
import { toast } from 'sonner';

interface SearchResult {
  content: string;
  file_path: string;
  start_line: number;
  end_line: number;
  similarity: number;
  chunk_type: string;
  symbols?: string[];
}

const CodeSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [projectName, setProjectName] = useState('ai-code-understanding');
  const [searchType, setSearchType] = useState<'semantic' | 'symbol' | 'fulltext'>('semantic');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.warning('请输入搜索内容');
      return;
    }

    setLoading(true);
    try {
      const response = await docQaApi.search({
        query,
        project_name: projectName,
        top_k: 20,
      });

      if (response.success && response.data) {
        setResults(response.data.results);
        toast.success(`找到 ${response.data.total_found} 个结果`);
      }
    } catch (error: any) {
      toast.error('搜索失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* 左侧：搜索面板 */}
      <div className="w-96 bg-surface border border-border rounded-xl p-4 flex flex-col">
        <h3 className="font-semibold mb-4">代码搜索</h3>

        {/* 搜索框 */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full bg-background border border-border rounded-lg pl-10 pr-4 py-3 focus:border-accent"
            placeholder="搜索代码、符号、文档..."
          />
        </div>

        {/* 搜索类型 */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setSearchType('semantic')}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              searchType === 'semantic'
                ? 'bg-accent text-white'
                : 'bg-card text-muted hover:text-text'
            }`}
          >
            <div className="flex items-center justify-center gap-1">
              <Sparkles className="w-4 h-4" />
              语义
            </div>
          </button>
          <button
            onClick={() => setSearchType('symbol')}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              searchType === 'symbol'
                ? 'bg-accent text-white'
                : 'bg-card text-muted hover:text-text'
            }`}
          >
            <div className="flex items-center justify-center gap-1">
              <Hash className="w-4 h-4" />
              符号
            </div>
          </button>
          <button
            onClick={() => setSearchType('fulltext')}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              searchType === 'fulltext'
                ? 'bg-accent text-white'
                : 'bg-card text-muted hover:text-text'
            }`}
          >
            <div className="flex items-center justify-center gap-1">
              <Type className="w-4 h-4" />
              全文
            </div>
          </button>
        </div>

        {/* 项目名称 */}
        <div className="mb-4">
          <label className="block text-sm text-muted mb-1">项目名称</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-accent"
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={loading}
          className="w-full bg-accent hover:bg-accent/90 text-white rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>

        {/* 搜索结果列表 */}
        <div className="flex-1 overflow-auto mt-4 border-t border-border pt-4">
          {results && results.length > 0 ? (
            <div className="space-y-2">
              {results.map((result, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedResult(result)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedResult === result
                      ? 'bg-card border-accent'
                      : 'bg-background border-border hover:bg-card'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <FileCode className="w-4 h-4 text-accent" />
                    <span className="text-sm font-mono truncate">
                      {result.file_path.split('/').pop()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <span>L{result.start_line}-{result.end_line}</span>
                    <span>•</span>
                    <span>{Math.round(result.similarity * 100)}% 匹配</span>
                  </div>
                </button>
              ))}
            </div>
          ) : results ? (
            <p className="text-center text-muted py-8">未找到结果</p>
          ) : null}
        </div>
      </div>

      {/* 右侧：代码预览 */}
      <div className="flex-1 bg-surface border border-border rounded-xl flex flex-col">
        {selectedResult ? (
          <>
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-accent" />
                  <span className="font-mono text-sm">{selectedResult.file_path}</span>
                </div>
                <span className="text-xs text-muted px-2 py-1 bg-card rounded">
                  L{selectedResult.start_line}-{selectedResult.end_line}
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <pre className="font-mono text-sm text-muted whitespace-pre-wrap">
                {selectedResult.content}
              </pre>
            </div>
          </>
        ) : (
          <EmptyState message="选择一个搜索结果查看代码" />
        )}
      </div>
    </div>
  );
};

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="h-full flex items-center justify-center text-muted">
    <p>{message}</p>
  </div>
);

export default CodeSearch;
