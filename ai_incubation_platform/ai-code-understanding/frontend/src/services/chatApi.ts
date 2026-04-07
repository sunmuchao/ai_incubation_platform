// Chat API 服务层 - AI Native 对话式接口
import type { ChatRequest, StreamEvent } from '@/types/chat';

const API_BASE = '/api';

// 获取 API Key
function getApiKey(): string | null {
  return localStorage.getItem('api_key');
}

/**
 * 流式对话
 * 使用 Server-Sent Events (SSE) 接收实时响应
 */
export async function* chatStream(request: ChatRequest): AsyncGenerator<StreamEvent> {
  const apiKey = getApiKey();

  const response = await fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || '',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法获取响应流');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 保留不完整的一行

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6);
          if (data === '[DONE]') continue;

          try {
            const event: StreamEvent = JSON.parse(data);
            yield event;
          } catch (e) {
            console.warn('解析 SSE 数据失败:', e, data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * 同步对话（不使用流式）
 */
export async function chatSync(request: ChatRequest): Promise<{
  success: boolean;
  response: any;
  thinking: string[];
  intent: string;
  confidence: number;
  suggestions: string[];
}> {
  const apiKey = getApiKey();

  const response = await fetch(`${API_BASE}/chat/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || '',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  return response.json();
}

/**
 * 获取聊天历史
 */
export async function getChatHistory(project?: string): Promise<{
  success: boolean;
  history: any[];
  message: string;
}> {
  const apiKey = getApiKey();
  const url = new URL(`${API_BASE}/chat/history`);
  if (project) {
    url.searchParams.set('project', project);
  }

  const response = await fetch(url.toString(), {
    headers: {
      'X-API-Key': apiKey || '',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  return response.json();
}

/**
 * 清除聊天历史
 */
export async function clearChatHistory(project?: string): Promise<{
  success: boolean;
  message: string;
}> {
  const apiKey = getApiKey();
  const url = new URL(`${API_BASE}/chat/clear`);
  if (project) {
    url.searchParams.set('project', project);
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey || '',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  return response.json();
}

/**
 * Generative UI API
 */
export interface UIViewRequest {
  intent: 'explore' | 'understand' | 'modify' | 'debug';
  data_type: 'flow' | 'dependency' | 'call' | 'dataflow';
  context?: Record<string, any>;
}

export interface UIViewResponse {
  success: boolean;
  view_config: {
    view_type: string;
    config: {
      title: string;
      layout: string;
      node_style?: any;
      edge_style?: any;
    };
    data: Record<string, any>;
  };
}

export async function generateUIView(request: UIViewRequest): Promise<UIViewResponse> {
  const apiKey = getApiKey();

  const response = await fetch(`${API_BASE}/generative-ui/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey || '',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  return response.json();
}

/**
 * 获取视图模板配置
 */
export async function getViewTemplate(viewType: string): Promise<{
  success: boolean;
  template: {
    component: string;
    props: string[];
    style: Record<string, string>;
  };
}> {
  const apiKey = getApiKey();

  const response = await fetch(`${API_BASE}/generative-ui/view/${viewType}`, {
    headers: {
      'X-API-Key': apiKey || '',
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API 请求失败：${error}`);
  }

  return response.json();
}
