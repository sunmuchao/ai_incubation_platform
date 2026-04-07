// AI Native Chat 类型定义

// 消息类型
export type MessageType =
  | 'user'           // 用户消息
  | 'thinking'       // AI 思考中
  | 'discovery'      // 发现相关代码
  | 'explanation'    // 解释内容
  | 'visualization'  // 可视化数据
  | 'suggestion'     // 建议
  | 'error';         // 错误

// 置信度等级
export type ConfidenceLevel = 'high' | 'medium' | 'low';

// 引用信息
export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  content?: string;
  similarity?: number;
}

// 代码片段
export interface CodeSnippet {
  file_path: string;
  code: string;
  language: string;
  start_line: number;
  end_line: number;
}

// 可视化数据
export interface VisualizationData {
  view_type: string;
  data: {
    nodes?: Array<{
      id: string;
      label: string;
      type: string;
      size?: number;
      x?: number;
      y?: number;
    }>;
    edges?: Array<{
      source: string;
      target: string;
      type: string;
      label?: string;
    }>;
    steps?: Array<{
      order: number;
      name: string;
      description: string;
      file_path?: string;
    }>;
    [key: string]: any;
  };
  config?: {
    title: string;
    layout: string;
    node_style?: any;
    edge_style?: any;
  };
}

// 聊天消息
export interface ChatMessage {
  id: string;
  type: MessageType;
  content: string | any;
  timestamp: number;
  metadata?: {
    confidence?: number;
    citations?: Citation[];
    code_snippets?: CodeSnippet[];
    visualization?: VisualizationData;
    thinking_steps?: string[];
  };
}

// 聊天请求
export interface ChatRequest {
  message: string;
  project?: string;
  context?: {
    file_path?: string;
    selected_code?: string;
    repo_path?: string;
    conversation_history?: Array<{
      role: 'user' | 'assistant';
      content: string;
    }>;
  };
}

// 流式响应事件
export interface StreamEvent {
  type: MessageType;
  content: any;
  metadata?: {
    confidence?: number;
    citations?: Citation[];
    [key: string]: any;
  };
}

// Agent 状态
export interface AgentStatus {
  status: 'idle' | 'thinking' | 'searching' | 'analyzing' | 'generating' | 'complete' | 'error';
  current_step: string;
  progress: number; // 0-100
  steps: Array<{
    name: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    duration_ms?: number;
  }>;
}

// 置信度转换
export function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

// 置信度颜色
export function getConfidenceColor(level: ConfidenceLevel): string {
  switch (level) {
    case 'high': return 'text-green-400';
    case 'medium': return 'text-yellow-400';
    case 'low': return 'text-red-400';
  }
}
