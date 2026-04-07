/**
 * 连接器 API 服务
 */
import { apiClient } from '../utils/request'
import type { DataSource, ConnectorType, ConnectorSchema } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class ConnectorService {
  /**
   * 获取支持的连接器类型
   */
  async getConnectorTypes(): Promise<ConnectorType[]> {
    const response = await apiClient.get<{ types: string[] }>(API_ENDPOINTS.CONNECTORS_TYPES)
    const types = response.data.data?.types || []
    return types.map((type: string) => ({
      name: type,
      display_name: type,
      description: `${type} 连接器`,
      icon: 'database',
      category: 'database',
    }))
  }

  /**
   * 获取活跃的连接器列表
   */
  async getActiveConnectors(): Promise<DataSource[]> {
    const response = await apiClient.get<{ active: DataSource[] }>(API_ENDPOINTS.CONNECTORS_ACTIVE)
    return response.data.data?.active || []
  }

  /**
   * 创建连接器
   */
  async createConnector(
    connectorType: string,
    config: {
      name: string
      datasource_name: string
      connection_string?: string
    }
  ): Promise<{ message: string; status: string }> {
    const response = await apiClient.post(
      API_ENDPOINTS.CONNECTORS_CONNECT.replace('{connector_id}', connectorType),
      config
    )
    return response.data.data as unknown as { message: string; status: string }
  }

  /**
   * 断开连接器
   */
  async disconnectConnector(name: string): Promise<{ message: string }> {
    const response = await apiClient.post(`${API_ENDPOINTS.CONNECTORS_DISCONNECT}?name=${name}`)
    return response.data.data as unknown as { message: string }
  }

  /**
   * 获取连接器 Schema
   */
  async getConnectorSchema(name: string): Promise<ConnectorSchema> {
    const response = await apiClient.get<ConnectorSchema>(
      API_ENDPOINTS.CONNECTORS_SCHEMA.replace('{name}', name)
    )
    return response.data.data || ({} as ConnectorSchema)
  }
}

export const connectorService = new ConnectorService()
