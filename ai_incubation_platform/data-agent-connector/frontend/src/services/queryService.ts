/**
 * 数据查询 API 服务
 */
import { apiClient } from '../utils/request'
import type { QueryResponse, AIQueryResponse, DataSource } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class QueryService {
  /**
   * 执行 SQL 查询
   */
  async executeQuery(
    connectorName: string,
    query: string,
    params?: Record<string, any>
  ): Promise<QueryResponse> {
    const response = await apiClient.post<QueryResponse>(API_ENDPOINTS.QUERY_EXECUTE, {
      connector_name: connectorName,
      query: query,
      params: params,
    })
    return response.data.data || {} as QueryResponse
  }

  /**
   * 自然语言查询
   */
  async nlQuery(
    connectorName: string,
    naturalLanguage: string
  ): Promise<QueryResponse> {
    const response = await apiClient.post<QueryResponse>(API_ENDPOINTS.QUERY_NL, {
      connector_name: connectorName,
      natural_language: naturalLanguage,
    })
    return response.data.data || {} as QueryResponse
  }

  /**
   * AI 增强查询 (NL2SQL)
   */
  async aiQuery(
    connectorName: string,
    naturalLanguage: string,
    options?: {
      use_llm?: boolean
      use_enhanced?: boolean
      enable_self_correction?: boolean
    }
  ): Promise<AIQueryResponse> {
    const response = await apiClient.post<AIQueryResponse>(API_ENDPOINTS.AI_QUERY_V2, {
      connector_name: connectorName,
      natural_language: naturalLanguage,
      ...options,
    })
    return response.data.data || {} as AIQueryResponse
  }

  /**
   * 获取数据源列表
   */
  async getDataSources(): Promise<DataSource[]> {
    const response = await apiClient.get<{ sources: DataSource[] }>(API_ENDPOINTS.QUERY_SOURCES)
    return response.data.data?.sources || []
  }

  /**
   * 刷新 Schema
   */
  async refreshSchema(connectorName: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`${API_ENDPOINTS.QUERY_REFRESH_SCHEMA}/${connectorName}`)
    return response.data.data as unknown as { success: boolean; message: string }
  }

  /**
   * 获取 AI 查询历史
   */
  async getQueryHistory(limit: number = 100): Promise<any[]> {
    const response = await apiClient.get<{ history: any[]; count: number }>(
      `${API_ENDPOINTS.AI_HISTORY}?limit=${limit}`
    )
    return response.data.data?.history || []
  }

  /**
   * 获取查询示例
   */
  async getExamples(naturalLanguage?: string, limit: number = 10): Promise<any[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (naturalLanguage) {
      params.append('natural_language', naturalLanguage)
    }
    const response = await apiClient.get<{ examples: any[]; count: number }>(
      `${API_ENDPOINTS.AI_EXAMPLES}?${params}`
    )
    return response.data.data?.examples || []
  }
}

export const queryService = new QueryService()
