/**
 * API 服务 - 与后端 AI Code Understanding 服务通信
 */

import axios, { AxiosInstance } from 'axios';

export interface IndexResult {
    success: boolean;
    stats: {
        total_files: number;
        total_chunks: number;
        total_symbols: number;
    };
}

export interface ExplainResult {
    explanation: string;
    citations: Array<{
        file: string;
        line: number;
        content: string;
    }>;
    validation: {
        confidence: number;
        verified: boolean;
    };
}

export interface TaskGuideResult {
    task: string;
    reading_order: Array<{
        file: string;
        reason: string;
        key_concepts: string[];
    }>;
    citations: string[];
}

export interface DependencyGraphResult {
    nodes: { [key: string]: any };
    edges: Array<{
        source: string;
        target: string;
        edge_type: string;
        symbols: string[];
    }>;
    cycle_count: number;
}

export interface SymbolReferenceResult {
    symbol: string;
    references: Array<{
        file: string;
        line: number;
        context: string;
    }>;
}

export class ApiService {
    private client: AxiosInstance;

    constructor(baseUrl: string) {
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 60000, // 60 秒超时
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    /**
     * 索引项目
     */
    async indexProject(projectName: string, projectPath: string): Promise<IndexResult> {
        const response = await this.client.post('/api/index', {
            project_name: projectName,
            project_path: projectPath,
        });
        return response.data;
    }

    /**
     * 解释代码
     */
    async explainCode(
        code: string,
        filePath: string,
        language: string
    ): Promise<ExplainResult> {
        const response = await this.client.post('/api/explain', {
            code,
            file_path: filePath,
            language,
        });
        return response.data;
    }

    /**
     * 获取任务引导
     */
    async getTaskGuide(task: string): Promise<TaskGuideResult> {
        const response = await this.client.post('/api/task-guide', {
            task,
        });
        return response.data;
    }

    /**
     * 获取依赖关系图
     */
    async getDependencyGraph(filePath?: string): Promise<DependencyGraphResult> {
        const params = filePath ? { file: filePath } : {};
        const response = await this.client.get('/api/dependency-graph', { params });
        return response.data;
    }

    /**
     * 查找符号引用
     */
    async findSymbolReferences(
        symbol: string,
        filePath?: string
    ): Promise<SymbolReferenceResult> {
        const response = await this.client.post('/api/symbol-references', {
            symbol,
            file_path: filePath,
        });
        return response.data;
    }

    /**
     * 语义搜索
     */
    async searchCode(query: string, topK: number = 10): Promise<any> {
        const response = await this.client.post('/api/search', {
            query,
            top_k: topK,
        });
        return response.data;
    }

    /**
     * 获取全局地图
     */
    async getGlobalMap(): Promise<any> {
        const response = await this.client.get('/api/global-map');
        return response.data;
    }
}
