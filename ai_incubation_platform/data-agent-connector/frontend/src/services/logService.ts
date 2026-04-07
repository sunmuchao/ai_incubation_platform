/**
 * 日志审计 API 服务
 */
import { apiClient } from '../utils/request'
import type { AuditLog, QueryLog, AccessLog } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class LogService {
  /**
   * 查询审计日志
   */
  async queryAuditLogs(options?: {
    tenant_id?: string
    user_id?: string
    action_type?: string
    resource_type?: string
    resource_id?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<{ logs: AuditLog[]; total: number }> {
    const params = new URLSearchParams()
    if (options?.tenant_id) params.append('tenant_id', options.tenant_id)
    if (options?.user_id) params.append('user_id', options.user_id)
    if (options?.action_type) params.append('action_type', options.action_type)
    if (options?.resource_type) params.append('resource_type', options.resource_type)
    if (options?.resource_id) params.append('resource_id', options.resource_id)
    if (options?.start_date) params.append('start_date', options.start_date)
    if (options?.end_date) params.append('end_date', options.end_date)
    if (options?.page) params.append('page', options.page.toString())
    if (options?.page_size) params.append('page_size', options.page_size.toString())

    const response = await apiClient.get<{ logs: AuditLog[]; total: number }>(
      `${API_ENDPOINTS.LOGS_AUDIT}?${params}`
    )
    return response.data.data || { logs: [], total: 0 }
  }

  /**
   * 查询查询日志
   */
  async queryQueryLogs(options?: {
    datasource?: string
    connector_name?: string
    status?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<{ logs: QueryLog[]; total: number }> {
    const params = new URLSearchParams()
    if (options?.datasource) params.append('datasource', options.datasource)
    if (options?.connector_name) params.append('connector_name', options.connector_name)
    if (options?.status) params.append('status', options.status)
    if (options?.start_date) params.append('start_date', options.start_date)
    if (options?.end_date) params.append('end_date', options.end_date)
    if (options?.page) params.append('page', options.page.toString())
    if (options?.page_size) params.append('page_size', options.page_size.toString())

    const response = await apiClient.get<{ logs: QueryLog[]; total: number }>(
      `${API_ENDPOINTS.LOGS_QUERY}?${params}`
    )
    return response.data.data || { logs: [], total: 0 }
  }

  /**
   * 查询访问日志
   */
  async queryAccessLogs(options?: {
    tenant_id?: string
    user_id?: string
    granted?: boolean
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }): Promise<{ logs: AccessLog[]; total: number }> {
    const params = new URLSearchParams()
    if (options?.tenant_id) params.append('tenant_id', options.tenant_id)
    if (options?.user_id) params.append('user_id', options.user_id)
    if (options?.granted !== undefined) params.append('granted', options.granted.toString())
    if (options?.start_date) params.append('start_date', options.start_date)
    if (options?.end_date) params.append('end_date', options.end_date)
    if (options?.page) params.append('page', options.page.toString())
    if (options?.page_size) params.append('page_size', options.page_size.toString())

    const response = await apiClient.get<{ logs: AccessLog[]; total: number }>(
      `${API_ENDPOINTS.LOGS_ACCESS}?${params}`
    )
    return response.data.data || { logs: [], total: 0 }
  }

  /**
   * 获取日志统计信息
   */
  async getLogStatistics(hours: number = 24): Promise<any> {
    const response = await apiClient.get(
      `${API_ENDPOINTS.LOGS_STATISTICS}?hours=${hours}`
    )
    return response.data.data || {}
  }

  /**
   * 获取用户活动分析
   */
  async analyzeUserActivity(userId: string, hours: number = 24): Promise<any> {
    const response = await apiClient.get(
      `${API_ENDPOINTS.LOGS_AUDIT}/analyze/activity?user_id=${userId}&hours=${hours}`
    )
    return response.data.data || {}
  }

  /**
   * 检测异常
   */
  async detectAnomalies(hours: number = 24): Promise<any[]> {
    const response = await apiClient.get(
      `${API_ENDPOINTS.LOGS_AUDIT}/analyze/anomalies?hours=${hours}`
    )
    return (response.data.data as any)?.anomalies || []
  }

  /**
   * 获取资源审计轨迹
   */
  async getAuditTrail(
    resourceType: string,
    resourceId: string,
    options?: {
      tenant_id?: string
      hours?: number
    }
  ): Promise<AuditLog[]> {
    const params = new URLSearchParams()
    if (options?.tenant_id) params.append('tenant_id', options.tenant_id)
    if (options?.hours) params.append('hours', options.hours.toString())

    const response = await apiClient.get<{ logs: AuditLog[] }>(
      `${API_ENDPOINTS.LOGS_AUDIT}/audit-trail/${resourceType}/${resourceId}?${params}`
    )
    return response.data.data?.logs || []
  }
}

export const logService = new LogService()
