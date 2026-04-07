// 代码高亮组件 - Bento Grid 风格
import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, FileCode, ChevronDown, ChevronRight, Code2 } from 'lucide-react';
import type { CodeSnippet } from '@/types/chat';
import { copyToClipboard } from '@/utils';

interface CodeBlockProps {
  snippet: CodeSnippet;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  maxLines?: number;
}

const CodeBlock: React.FC<CodeBlockProps> = ({
  snippet,
  collapsible = true,
  defaultExpanded = true,
  maxLines = 100,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const codeLines = snippet.code.split('\n');
  const isTruncated = codeLines.length > maxLines;
  const displayCode = isTruncated && !expanded
    ? codeLines.slice(0, maxLines).join('\n')
    : snippet.code;

  const handleCopy = async () => {
    const success = await copyToClipboard(snippet.code);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getLanguage = () => {
    const langMap: Record<string, string> = {
      'python': 'python',
      'py': 'python',
      'javascript': 'javascript',
      'js': 'javascript',
      'typescript': 'typescript',
      'ts': 'typescript',
      'tsx': 'tsx',
      'jsx': 'jsx',
      'java': 'java',
      'go': 'go',
      'rust': 'rust',
      'cpp': 'cpp',
      'c': 'c',
      'css': 'css',
      'html': 'html',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'markdown': 'markdown',
      'md': 'markdown',
      'sql': 'sql',
      'shell': 'shell',
      'bash': 'bash',
    };
    return langMap[snippet.language] || snippet.language || 'text';
  };

  const getLanguageLabel = () => {
    const langMap: Record<string, string> = {
      'python': 'Python',
      'javascript': 'JavaScript',
      'typescript': 'TypeScript',
      'tsx': 'TSX',
      'jsx': 'JSX',
      'java': 'Java',
      'go': 'Go',
      'rust': 'Rust',
      'cpp': 'C++',
      'css': 'CSS',
      'html': 'HTML',
      'json': 'JSON',
      'yaml': 'YAML',
      'markdown': 'Markdown',
      'sql': 'SQL',
      'shell': 'Shell',
    };
    return langMap[getLanguage()] || getLanguage();
  };

  return (
    <div className="bento-card overflow-hidden group">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-lighter/80 border-b border-border-light">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center flex-shrink-0">
            <Code2 className="w-4 h-4 text-accent" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-primary truncate">
                {snippet.file_path?.split('/').pop() || '代码片段'}
              </span>
              <span className="text-xs px-2 py-0.5 bg-accent/20 text-accent rounded-md font-medium">
                {getLanguageLabel()}
              </span>
            </div>
            <div className="text-xs text-text-muted truncate font-mono">
              {snippet.file_path}
              <span className="mx-1">•</span>
              行 {snippet.start_line} - {snippet.end_line}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {collapsible && isTruncated && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-surface-lighter hover:bg-surface rounded-lg transition-all duration-200"
            >
              {expanded ? (
                <>
                  <ChevronDown className="w-3 h-3" />
                  收起
                </>
              ) : (
                <>
                  <ChevronRight className="w-3 h-3" />
                  展开 ({codeLines.length} 行)
                </>
              )}
            </button>
          )}
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition-all duration-200 ${
              copied
                ? 'bg-success/20 text-success border border-success/30'
                : 'bg-surface-lighter text-text-secondary hover:text-text-primary hover:bg-surface border border-border-light'
            }`}
            title="复制代码"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>复制</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 代码内容 */}
      <div className="relative">
        <SyntaxHighlighter
          language={getLanguage()}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1.25rem',
            fontSize: '0.825rem',
            borderRadius: 0,
            background: 'transparent',
            lineHeight: 1.6,
          }}
          showLineNumbers={!isTruncated || expanded}
          startingLineNumber={snippet.start_line}
          wrapLines
          codeTagProps={{
            style: {
              color: '#e8ecf1',
              fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
            }
          }}
        >
          {displayCode}
        </SyntaxHighlighter>

        {/* 底部渐变（截断时） */}
        {isTruncated && !expanded && (
          <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-base-900 to-transparent pointer-events-none" />
        )}
      </div>

      {/* 截断提示 */}
      {isTruncated && !expanded && (
        <div className="px-4 py-3 bg-surface-lighter/80 border-t border-border-light text-center">
          <button
            onClick={() => setExpanded(true)}
            className="text-xs text-accent hover:text-accent/80 font-medium transition-colors inline-flex items-center gap-1.5 px-4 py-2 rounded-lg hover:bg-accent/10"
          >
            <ChevronDown className="w-3 h-3" />
            显示全部 {codeLines.length} 行代码
          </button>
        </div>
      )}
    </div>
  );
};

export default CodeBlock;
