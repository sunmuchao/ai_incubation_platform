/**
 * 数据治理 API 服务
 */
import { apiClient } from '../utils/request'
import type {
  Classification,
  DataLabel,
  SensitiveRecord,
  MaskingPolicy,
  GovernanceScore,
} from '../types'
import { API_ENDPOINTS } from '../config/api'

export class GovernanceService {
  /**
   * 获取分类树
   */
  async getClassificationTree(): Promise<Classification[]> {
    const response = await apiClient.get<{ tree: Classification[] }>(
      `${API_ENDPOINTS.GOVERNANCE_CLASSIFICATIONS}/tree`
    )
    return response.data.data?.tree || []
  }

  /**
   * 创建分类
   */
  async createClassification(data: {
    name: string
    description?: string
    parent_id?: string
    level?: number
    tags?: string[]
  }): Promise<{ id: string; status: string }> {
    const response = await apiClient.post(API_ENDPOINTS.GOVERNANCE_CLASSIFICATIONS, data)
    return response.data.data as unknown as { id: string; status: string }
  }

  /**
   * 获取标签列表
   */
  async getLabels(options?: {
    datasource?: string
    table_name?: string
    column_name?: string
    label_type?: string
  }): Promise<DataLabel[]> {
    const params = new URLSearchParams()
    if (options?.datasource) params.append('datasource', options.datasource)
    if (options?.table_name) params.append('table_name', options.table_name)
    if (options?.column_name) params.append('column_name', options.column_name)
    if (options?.label_type) params.append('label_type', options.label_type)

    const response = await apiClient.get<{ labels: DataLabel[] }>(
      `${API_ENDPOINTS.GOVERNANCE_LABELS}?${params}`
    )
    return response.data.data?.labels || []
  }

  /**
   * 扫描敏感数据
   */
  async scanSensitiveData(data: {
    datasource: string
    table_name: string
    columns?: string[]
    sample_size?: number
  }): Promise<SensitiveRecord[]> {
    const response = await apiClient.post<{ results: SensitiveRecord[] }>(
      API_ENDPOINTS.GOVERNANCE_SENSITIVE,
      data
    )
    return response.data.data?.results || []
  }

  /**
   * 获取敏感数据记录
   */
  async getSensitiveRecords(options?: {
    datasource?: string
    table_name?: string
    sensitivity_level?: string
    is_masked?: boolean
    is_reviewed?: boolean
    limit?: number
  }): Promise<SensitiveRecord[]> {
    const params = new URLSearchParams()
    if (options?.datasource) params.append('datasource', options.datasource)
    if (options?.table_name) params.append('table_name', options.table_name)
    if (options?.sensitivity_level) params.append('sensitivity_level', options.sensitivity_level)
    if (options?.is_masked !== undefined) params.append('is_masked', options.is_masked.toString())
    if (options?.is_reviewed !== undefined) params.append('is_reviewed', options.is_reviewed.toString())
    if (options?.limit) params.append('limit', options.limit.toString())

    const response = await apiClient.get<{ records: SensitiveRecord[] }>(
      `${API_ENDPOINTS.GOVERNANCE_SENSITIVE}-records?${params}`
    )
    return response.data.data?.records || []
  }

  /**
   * 获取脱敏策略列表
   */
  async getMaskingPolicies(sensitivityLevel?: string): Promise<MaskingPolicy[]> {
    const params = sensitivityLevel ? `?sensitivity_level=${sensitivityLevel}` : ''
    const response = await apiClient.get<{ policies: MaskingPolicy[] }>(
      `${API_ENDPOINTS.GOVERNANCE_MASKING}${params}`
    )
    return response.data.data?.policies || []
  }

  /**
   * 创建脱敏策略
   */
  async createMaskingPolicy(data: {
    name: string
    description?: string
    masking_type: 'full' | 'partial' | 'hash' | 'encrypt' | 'redact'
    sensitivity_level?: string
    data_type?: string
    column_pattern?: string
    priority?: number
    masking_params?: Record<string, any>
  }): Promise<{ id: string; status: string }> {
    const response = await apiClient.post(API_ENDPOINTS.GOVERNANCE_MASKING, data)
    return response.data.data as unknown as { id: string; status: string }
  }

  /**
   * 应用脱敏
   */
  async applyMasking(policyId: string, value: any): Promise<{
    original: string
    masked: string
    policy: string
  }> {
    const response = await apiClient.post(`${API_ENDPOINTS.GOVERNANCE_MASKING}/apply`, {
      policy_id: policyId,
      value: value,
    })
    return response.data.data as unknown as { original: string; masked: string; policy: string }
  }

  /**
   * 获取治理分数
   */
  async getGovernanceScore(datasource?: string): Promise<GovernanceScore> {
    const params = datasource ? `?datasource=${datasource}` : ''
    const response = await apiClient.get<GovernanceScore>(
      `${API_ENDPOINTS.GOVERNANCE_SCORE}${params}`
    )
    return response.data.data as unknown as GovernanceScore
  }

  /**
   * 获取治理仪表板数据
   */
  async getGovernanceDashboard(datasource?: string): Promise<any> {
    const params = datasource ? `?datasource=${datasource}` : ''
    const response = await apiClient.get(`${API_ENDPOINTS.GOVERNANCE_DASHBOARD}${params}`)
    return response.data.data!
  }
}

export const governanceService = new GovernanceService()
