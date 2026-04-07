/**
 * 监控告警 API 服务
 */
import { apiClient } from '../utils/request'
import type { MetricData, AlertRule, Alert, SystemHealth } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class MonitoringService {
  /**
   * 获取监控指标
   */
  async getMetrics(options?: {
    name?: string
    hours?: number
    limit?: number
  }): Promise<MetricData[]> {
    const params = new URLSearchParams()
    if (options?.name) params.append('name', options.name)
    if (options?.hours) params.append('hours', options.hours.toString())
    if (options?.limit) params.append('limit', options.limit.toString())

    const response = await apiClient.get<{ metrics: MetricData[] }>(
      `${API_ENDPOINTS.MONITORING_METRICS}?${params}`
    )
    return response.data.data?.metrics || []
  }

  /**
   * 获取监控大盘数据
   */
  async getDashboard(): Promise<any> {
    const response = await apiClient.get(API_ENDPOINTS.MONITORING_DASHBOARD)
    return response.data.data!
  }

  /**
   * 获取告警规则列表
   */
  async getAlertRules(enabled?: boolean): Promise<AlertRule[]> {
    const params = enabled !== undefined ? `?enabled=${enabled}` : ''
    const response = await apiClient.get<{ rules: AlertRule[] }>(
      `${API_ENDPOINTS.MONITORING_ALERTS}-rules${params}`
    )
    return response.data.data?.rules || []
  }

  /**
   * 创建告警规则
   */
  async createAlertRule(data: {
    name: string
    description?: string
    metric_name: string
    operator: '>' | '<' | '>=' | '<=' | '==' | '!='
    threshold: number
    duration_seconds?: number
    severity?: 'critical' | 'warning' | 'info'
    notify_channels?: string[]
    notify_receivers?: string[]
  }): Promise<{ rule: AlertRule }> {
    const response = await apiClient.post(`${API_ENDPOINTS.MONITORING_ALERTS}-rules`, data)
    return response.data.data as unknown as { rule: AlertRule }
  }

  /**
   * 更新告警规则
   */
  async updateAlertRule(
    ruleId: string,
    data: Partial<{
      name: string
      description: string
      metric_name: string
      operator: string
      threshold: number
      enabled: boolean
      silenced: boolean
    }>
  ): Promise<{ rule: AlertRule }> {
    const response = await apiClient.put(`${API_ENDPOINTS.MONITORING_ALERTS}-rules/${ruleId}`, data)
    return response.data.data as unknown as { rule: AlertRule }
  }

  /**
   * 删除告警规则
   */
  async deleteAlertRule(ruleId: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`${API_ENDPOINTS.MONITORING_ALERTS}-rules/${ruleId}`)
    return response.data.data as unknown as { success: boolean }
  }

  /**
   * 静默告警规则
   */
  async silenceAlertRule(ruleId: string, durationMinutes: number = 60): Promise<{ rule: AlertRule }> {
    const response = await apiClient.post(
      `${API_ENDPOINTS.MONITORING_ALERTS}-rules/${ruleId}/silence?duration_minutes=${durationMinutes}`
    )
    return response.data.data as unknown as { rule: AlertRule }
  }

  /**
   * 获取告警记录
   */
  async getAlerts(options?: {
    status?: 'firing' | 'resolved' | 'acknowledged'
    severity?: string
    rule_id?: string
    hours?: number
    limit?: number
  }): Promise<Alert[]> {
    const params = new URLSearchParams()
    if (options?.status) params.append('status', options.status)
    if (options?.severity) params.append('severity', options.severity)
    if (options?.rule_id) params.append('rule_id', options.rule_id)
    if (options?.hours) params.append('hours', options.hours.toString())
    if (options?.limit) params.append('limit', options.limit.toString())

    const response = await apiClient.get<{ alerts: Alert[] }>(
      `${API_ENDPOINTS.MONITORING_ALERTS}?${params}`
    )
    return response.data.data?.alerts || []
  }

  /**
   * 确认告警
   */
  async acknowledgeAlert(alertId: string, userId: string): Promise<{ alert: Alert }> {
    const response = await apiClient.post(`${API_ENDPOINTS.MONITORING_ALERTS}/${alertId}/acknowledge`, {
      user_id: userId,
    })
    return response.data.data as unknown as { alert: Alert }
  }

  /**
   * 获取系统健康状态
   */
  async getSystemHealth(): Promise<SystemHealth | null> {
    const response = await apiClient.get<{ health: SystemHealth | null }>(
      `${API_ENDPOINTS.MONITORING_DASHBOARD}/health`
    )
    return response.data.data?.health || null
  }
}

export const monitoringService = new MonitoringService()
