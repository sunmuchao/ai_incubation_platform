/**
 * RBAC 权限 API 服务
 */
import { apiClient } from '../utils/request'
import type { Role, PermissionCheck } from '../types'
import { API_ENDPOINTS } from '../config/api'

export class RBACService {
  /**
   * 获取所有角色
   */
  async listRoles(): Promise<Role[]> {
    const response = await apiClient.get<{ roles: Role[] }>(API_ENDPOINTS.RBAC_ROLES)
    return response.data.data?.roles || []
  }

  /**
   * 获取角色详情
   */
  async getRole(roleName: string): Promise<Role | null> {
    const response = await apiClient.get<{ role: Role | null }>(
      `${API_ENDPOINTS.RBAC_ROLES}/${roleName}`
    )
    return response.data.data?.role || null
  }

  /**
   * 创建角色
   */
  async createRole(data: {
    name: string
    description?: string
    permissions: string[]
  }): Promise<{ role: Role }> {
    const response = await apiClient.post(API_ENDPOINTS.RBAC_ROLES, data)
    return response.data.data as unknown as { role: Role }
  }

  /**
   * 更新角色
   */
  async updateRole(
    roleName: string,
    data: Partial<{
      description: string
      permissions: string[]
    }>
  ): Promise<{ role: Role }> {
    const response = await apiClient.put(`${API_ENDPOINTS.RBAC_ROLES}/${roleName}`, data)
    return response.data.data as unknown as { role: Role }
  }

  /**
   * 删除角色
   */
  async deleteRole(roleName: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`${API_ENDPOINTS.RBAC_ROLES}/${roleName}`)
    return response.data.data as unknown as { success: boolean }
  }

  /**
   * 获取用户角色
   */
  async getUserRoles(userId: string): Promise<Role[]> {
    const response = await apiClient.get<{ roles: Role[] }>(
      `${API_ENDPOINTS.RBAC_USERS}/${userId}/roles`
    )
    return response.data.data?.roles || []
  }

  /**
   * 获取用户权限
   */
  async getUserPermissions(userId: string): Promise<string[]> {
    const response = await apiClient.get<{ permissions: string[] }>(
      `${API_ENDPOINTS.RBAC_USERS}/${userId}/permissions`
    )
    return response.data.data?.permissions || []
  }

  /**
   * 分配角色给用户
   */
  async assignRole(userId: string, roleName: string): Promise<{ success: boolean }> {
    const response = await apiClient.post(`${API_ENDPOINTS.RBAC_USERS}/${userId}/roles`, {
      user_id: userId,
      role_name: roleName,
    })
    return response.data.data as unknown as { success: boolean }
  }

  /**
   * 撤销用户角色
   */
  async revokeRole(userId: string, roleName: string): Promise<{ success: boolean }> {
    const response = await apiClient.delete(`${API_ENDPOINTS.RBAC_USERS}/${userId}/roles/${roleName}`)
    return response.data.data as unknown as { success: boolean }
  }

  /**
   * 检查权限
   */
  async checkPermission(data: {
    user_id: string
    resource: string
    operation: string
  }): Promise<PermissionCheck> {
    const response = await apiClient.post<PermissionCheck>(API_ENDPOINTS.RBAC_CHECK, data)
    return response.data.data as unknown as PermissionCheck
  }

  /**
   * 获取审计日志
   */
  async listAudits(options?: {
    user_id?: string
    action?: string
    limit?: number
    offset?: number
  }): Promise<any[]> {
    const params = new URLSearchParams()
    if (options?.user_id) params.append('user_id', options.user_id)
    if (options?.action) params.append('action', options.action)
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.offset) params.append('offset', options.offset.toString())

    const response = await apiClient.get<{ audits: any[] }>(
      `${API_ENDPOINTS.RBAC_AUDIT}?${params}`
    )
    return response.data.data?.audits || []
  }
}

export const rbacService = new RBACService()
