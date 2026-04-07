/**
 * 血缘图谱 API 服务
 */
import { apiClient } from '../utils/request'
import type { LineageGraph, LineageNode, LineageStatistics } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class LineageService {
  /**
   * 获取节点列表
   */
  async listNodes(options?: {
    datasource?: string
    node_type?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<{ nodes: LineageNode[]; total: number }> {
    const params = new URLSearchParams()
    if (options?.datasource) params.append('datasource', options.datasource)
    if (options?.node_type) params.append('node_type', options.node_type)
    if (options?.search) params.append('search', options.search)
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.offset) params.append('offset', options.offset.toString())

    const response = await apiClient.get<{ nodes: LineageNode[]; total: number }>(
      `${API_ENDPOINTS.LINEAGE_NODES}?${params}`
    )
    return response.data.data || { nodes: [], total: 0 }
  }

  /**
   * 获取血缘关系图
   */
  async getLineageGraph(
    nodeId: string,
    options?: {
      direction?: 'upstream' | 'downstream' | 'both'
      depth?: number
    }
  ): Promise<LineageGraph> {
    const params = new URLSearchParams()
    if (options?.direction) params.append('direction', options.direction)
    if (options?.depth) params.append('depth', options.depth.toString())

    const response = await apiClient.get<LineageGraph>(
      `${API_ENDPOINTS.LINEAGE_GRAPH}/${nodeId}?${params}`
    )
    return response.data.data || {} as LineageGraph
  }

  /**
   * 获取完整血缘图
   */
  async getFullLineageGraph(datasource?: string): Promise<LineageGraph> {
    const params = datasource ? `?datasource=${datasource}` : ''
    const response = await apiClient.get<LineageGraph>(
      `${API_ENDPOINTS.LINEAGE_GRAPH}${params}`
    )
    return response.data.data || {} as LineageGraph
  }

  /**
   * 分析影响范围（下游血缘）
   */
  async analyzeImpact(nodeId: string, includeDetails: boolean = false): Promise<{
    source_node: LineageNode
    impacted_nodes: LineageNode[]
    impact_count: number
    impact_level: string
  }> {
    const params = `?include_details=${includeDetails}`
    const response = await apiClient.get(
      `${API_ENDPOINTS.LINEAGE_IMPACT}/${nodeId}${params}`
    )
    return response.data.data as unknown as {
      source_node: LineageNode
      impacted_nodes: LineageNode[]
      impact_count: number
      impact_level: string
    }
  }

  /**
   * 分析数据来源（上游血缘）
   */
  async analyzeLineage(nodeId: string, includeDetails: boolean = false): Promise<{
    target_node: LineageNode
    source_nodes: LineageNode[]
    source_count: number
  }> {
    const params = `?include_details=${includeDetails}`
    const response = await apiClient.get(
      `${API_ENDPOINTS.LINEAGE_LINEAGE}/${nodeId}${params}`
    )
    return response.data.data as unknown as {
      target_node: LineageNode
      source_nodes: LineageNode[]
      source_count: number
    }
  }

  /**
   * 获取血缘统计信息
   */
  async getStatistics(datasource?: string): Promise<LineageStatistics> {
    const params = datasource ? `?datasource=${datasource}` : ''
    const response = await apiClient.get<{ statistics: LineageStatistics }>(
      `${API_ENDPOINTS.LINEAGE_STATISTICS}${params}`
    )
    return response.data.data!.statistics
  }

  /**
   * 获取查询历史
   */
  async getQueryHistory(options?: {
    datasource?: string
    user_id?: string
    start_time?: string
    end_time?: string
    limit?: number
  }): Promise<any[]> {
    const params = new URLSearchParams()
    if (options?.datasource) params.append('datasource', options.datasource)
    if (options?.user_id) params.append('user_id', options.user_id)
    if (options?.start_time) params.append('start_time', options.start_time)
    if (options?.end_time) params.append('end_time', options.end_time)
    if (options?.limit) params.append('limit', options.limit.toString())

    const response = await apiClient.get<{ history: any[] }>(
      `${API_ENDPOINTS.LINEAGE_HISTORY}?${params}`
    )
    return response.data.data?.history || []
  }
}

export const lineageService = new LineageService()
