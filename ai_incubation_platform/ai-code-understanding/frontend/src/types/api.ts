// API 类型定义

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 代码解释相关
export interface ExplainRequest {
  code: string;
  language: string;
  context?: string;
}

export interface ExplainResponse {
  explanation: string;
  confidence: number;
  citations: Citation[];
  symbols?: SymbolInfo[];
}

// 模块摘要相关
export interface SummarizeRequest {
  module_name: string;
  symbols?: string[];
  raw_outline?: string;
}

export interface ModuleSummary {
  summary: string;
  responsibilities: string[];
  dependencies: string[];
  dependents: string[];
  entry_points: SymbolInfo[];
  confidence: number;
  citations: Citation[];
}

// 代码问答相关
export interface AskRequest {
  question: string;
  scope_paths?: string[];
}

export interface AskResponse {
  answer: string;
  confidence: number;
  sources: Source[];
  code_references: CodeReference[];
  follow_up_questions: string[];
}

// 全局地图相关
export interface GlobalMapRequest {
  project_name: string;
  repo_hint?: string;
  stack_hint?: string;
  regenerate?: boolean;
  format?: string;
}

export interface GlobalMap {
  project: string;
  stack: TechStack;
  layers: Layer[];
  entrypoints: Entrypoint[];
  dependencies: Dependency[];
}

export interface TechStack {
  languages: string[];
  frameworks: string[];
  databases?: string[];
  tools?: string[];
}

export interface Layer {
  name: string;
  description: string;
  files: string[];
}

export interface Entrypoint {
  path: string;
  type: string;
  description?: string;
}

// 任务引导相关
export interface TaskGuideRequest {
  task_description: string;
  optional_paths?: string[];
  project_name?: string;
}

export interface TaskGuide {
  task: string;
  task_type: string;
  suggested_reading_order: ReadingOrderItem[];
  questions_to_clarify: string[];
}

export interface ReadingOrderItem {
  file_path: string;
  relevance: number;
  reason: string;
}

// 索引相关
export interface IndexRequest {
  project_name: string;
  repo_path: string;
  incremental?: boolean;
}

export interface IndexResponse {
  status: string;
  files_indexed: number;
  chunks_created: number;
  time_taken: number;
}

// 依赖图相关
export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  name?: string;
  type?: string;
  file_path?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type?: string;
}

// 知识图谱相关
export interface KnowledgeGraph {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface KnowledgeGraphNode {
  id: string;
  name: string;
  node_type: string;
  file_path?: string;
  start_line?: number;
  end_line?: number;
  in_degree: number;
  out_degree: number;
  is_core: boolean;
  display_name?: string;
}

export interface KnowledgeGraphEdge {
  source: string;
  target: string;
  edge_type: string;
}

// 代码导航相关
export interface CodeNavigationRequest {
  file_path: string;
  line: number;
  column: number;
  project_root?: string;
}

export interface SymbolLocation {
  file_path: string;
  line: number;
  column: number;
  end_line?: number;
  end_column?: number;
  content_preview?: string;
}

export interface GoToDefinitionResponse {
  success: boolean;
  symbol_name?: string;
  definition?: SymbolLocation;
  message?: string;
}

export interface FindReferencesResponse {
  success: boolean;
  symbol_name?: string;
  references: SymbolLocation[];
  total_references: number;
  message?: string;
}

// 文档生成相关
export interface GenerateDocsRequest {
  project_path: string;
  source_dirs?: string[];
  format?: string;
}

export interface GeneratedDoc {
  content: string;
  format: string;
  count?: number;
}

// 文档问答相关
export interface SearchDocumentsRequest {
  query: string;
  project_name: string;
  top_k?: number;
  filters?: Record<string, any>;
}

export interface SearchResults {
  query: string;
  results: SearchResult[];
  total_found: number;
  search_time_ms: number;
  suggestions: string[];
}

export interface SearchResult {
  content: string;
  file_path: string;
  start_line: number;
  end_line: number;
  similarity: number;
  chunk_type: string;
  symbols?: string[];
  metadata?: Record<string, any>;
}

// 通用类型
export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  similarity: number;
  content?: string;
}

export interface Source {
  content: string;
  file_path: string;
  start_line: number;
  end_line: number;
  similarity: number;
  chunk_type: string;
}

export interface CodeReference {
  file_path: string;
  line: number;
  code: string;
}

export interface SymbolInfo {
  name: string;
  type: string;
  line?: number;
  end_line?: number;
  signature?: string;
  docstring?: string;
}

export interface Dependency {
  from: string;
  to: string;
  type: string;
}
