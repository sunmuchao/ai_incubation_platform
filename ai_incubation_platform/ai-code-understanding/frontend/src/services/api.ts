// API 服务层
import axios from 'axios';
import type {
  ApiResponse,
  ExplainRequest,
  ExplainResponse,
  SummarizeRequest,
  ModuleSummary,
  AskRequest,
  AskResponse,
  GlobalMapRequest,
  GlobalMap,
  TaskGuideRequest,
  TaskGuide,
  IndexRequest,
  IndexResponse,
  DependencyGraph,
  KnowledgeGraph,
  CodeNavigationRequest,
  GoToDefinitionResponse,
  FindReferencesResponse,
  SearchDocumentsRequest,
  SearchResults,
  GenerateDocsRequest,
  GeneratedDoc,
} from '@/types/api';

// KnowledgeGraphVizRequest 类型
interface KnowledgeGraphVizRequest {
  project_name: string;
  repo_path: string;
  layout?: string;
  max_nodes?: number;
}

// ReviewCodeRequest 类型
interface ReviewCodeRequest {
  code: string;
  language: string;
  file_path?: string;
  config?: Record<string, any>;
}

const API_BASE = '/api';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60 秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 API Key
    const apiKey = localStorage.getItem('api_key');
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // API Key 无效
      localStorage.removeItem('api_key');
      window.dispatchEvent(new CustomEvent('auth-error'));
    }
    return Promise.reject(error);
  }
);

// Understanding API
export const understandingApi = {
  // 解释代码
  async explain(request: ExplainRequest): Promise<ApiResponse<ExplainResponse>> {
    return apiClient.post('/understanding/explain', request);
  },

  // 模块摘要
  async summarize(request: SummarizeRequest): Promise<ApiResponse<ModuleSummary>> {
    return apiClient.post('/understanding/summarize', request);
  },

  // 代码问答
  async ask(request: AskRequest): Promise<ApiResponse<AskResponse>> {
    return apiClient.post('/understanding/ask', request);
  },

  // 全局地图
  async globalMap(request: GlobalMapRequest): Promise<ApiResponse<GlobalMap>> {
    return apiClient.post('/understanding/global-map', request);
  },

  // 任务引导
  async taskGuide(request: TaskGuideRequest): Promise<ApiResponse<TaskGuide>> {
    return apiClient.post('/understanding/task-guide', request);
  },

  // 索引项目
  async indexProject(request: IndexRequest): Promise<ApiResponse<IndexResponse>> {
    return apiClient.post('/understanding/index-project', request);
  },

  // 依赖关系图
  async dependencyGraph(project_name: string, repo_path: string): Promise<ApiResponse<DependencyGraph>> {
    return apiClient.post('/understanding/dependency-graph', { project_name, repo_path });
  },

  // 构建知识图谱
  async buildKnowledgeGraph(project_name: string, repo_path: string): Promise<ApiResponse<KnowledgeGraph>> {
    return apiClient.post('/understanding/build-knowledge-graph', { project_name, repo_path, save: true });
  },

  // 知识图谱可视化数据
  async knowledgeGraphViz(request: KnowledgeGraphVizRequest): Promise<ApiResponse<KnowledgeGraph>> {
    return apiClient.post('/understanding/knowledge-graph-viz', request);
  },

  // 分析变更影响
  async analyzeChangeImpact(project_name: string, repo_path: string, base: string = 'HEAD~1', target: string = 'HEAD'): Promise<ApiResponse<any>> {
    return apiClient.post('/understanding/analyze-change-impact', { project_name, repo_path, base, target });
  },

  // 查找符号引用
  async findSymbolReferences(project_name: string, repo_path: string, symbol_name: string): Promise<ApiResponse<any>> {
    return apiClient.post('/understanding/find-symbol-references', { project_name, repo_path, symbol_name });
  },

  // 审查代码
  async reviewCode(request: ReviewCodeRequest): Promise<ApiResponse<any>> {
    return apiClient.post('/understanding/review-code', request);
  },
};

// Code Navigation API
export const codeNavigationApi = {
  // 跳转定义
  async goToDefinition(request: CodeNavigationRequest): Promise<ApiResponse<GoToDefinitionResponse>> {
    return apiClient.post('/code-nav/go-to-definition', request);
  },

  // 查找引用
  async findReferences(request: CodeNavigationRequest): Promise<ApiResponse<FindReferencesResponse>> {
    return apiClient.post('/code-nav/find-references', request);
  },

  // 重命名符号
  async renameSymbol(request: CodeNavigationRequest & { new_name: string; dry_run?: boolean }): Promise<ApiResponse<any>> {
    return apiClient.post('/code-nav/rename-symbol', request);
  },

  // 文档符号
  async documentSymbols(file_path: string): Promise<ApiResponse<any>> {
    return apiClient.post('/code-nav/document-symbols', { file_path });
  },

  // 文件概览
  async fileOverview(file_path: string): Promise<ApiResponse<any>> {
    return apiClient.post('/code-nav/file-overview', { file_path });
  },
};

// Document QA API
export const docQaApi = {
  // 搜索文档
  async search(request: SearchDocumentsRequest): Promise<ApiResponse<SearchResults>> {
    return apiClient.post('/doc-qa/search', request);
  },

  // 问答
  async ask(request: AskRequest & { project_name: string; max_context_chunks?: number }): Promise<ApiResponse<AskResponse>> {
    return apiClient.post('/doc-qa/ask', request);
  },

  // 解释代码
  async explain(request: ExplainRequest): Promise<ApiResponse<ExplainResponse>> {
    return apiClient.post('/doc-qa/explain', request);
  },

  // 代码导航
  async navigate(file_path: string, symbol_name?: string, project_name?: string): Promise<ApiResponse<any>> {
    return apiClient.post('/doc-qa/navigate', { file_path, symbol_name, project_name });
  },
};

// Docs Generation API
export const docsApi = {
  // 生成 API 文档
  async generateApiDocs(request: GenerateDocsRequest): Promise<ApiResponse<GeneratedDoc>> {
    return apiClient.post('/docs/generate/api', request);
  },

  // 生成架构图
  async generateArchitecture(project_path: string, format: string = 'mermaid'): Promise<ApiResponse<any>> {
    return apiClient.post('/docs/generate/architecture', { project_path, format, include_details: true });
  },

  // 生成数据流图
  async generateDataflow(project_path: string, format: string = 'mermaid'): Promise<ApiResponse<any>> {
    return apiClient.post('/docs/generate/dataflow', { project_path, format });
  },

  // 生成 README
  async generateReadme(project_path: string): Promise<ApiResponse<GeneratedDoc>> {
    return apiClient.post('/docs/generate/readme', { project_path });
  },

  // 导出所有文档
  async exportAll(project_path: string, output_dir: string = 'docs/generated'): Promise<ApiResponse<any>> {
    return apiClient.post('/docs/export/all', { project_path, output_dir });
  },
};

// Auth API
export const authApi = {
  // 健康检查
  async health(): Promise<ApiResponse<any>> {
    return apiClient.get('/auth/health');
  },

  // 管理 API Key
  async manage(action: string, params?: Record<string, any>): Promise<ApiResponse<any>> {
    return apiClient.post('/auth/manage', { action, ...params });
  },
};

// Metrics API
export const metricsApi = {
  async getMetrics(): Promise<ApiResponse<any>> {
    return apiClient.get('/metrics');
  },
};

// Health check
export async function healthCheck(): Promise<ApiResponse<any>> {
  return apiClient.get('/health');
}

export default apiClient;
