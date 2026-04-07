/**
 * 远程工作 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface WorkSession {
  id: string;
  employee_id: string;
  work_mode: 'remote' | 'office' | 'hybrid';
  start_time: string;
  end_time?: string;
  location?: string;
  notes?: string;
}

export interface PresenceStatus {
  employee_id: string;
  status: 'available' | 'busy' | 'away' | 'offline';
  work_mode: 'remote' | 'office' | 'hybrid';
  status_message?: string;
  last_heartbeat: string;
}

export interface VirtualWorkspace {
  id: string;
  name: string;
  workspace_type: string;
  capacity: number;
  current_occupants: number;
  description?: string;
  is_private: boolean;
}

export const remoteWorkApi = {
  // === 工作会话 ===
  startSession: async (employeeId: string, workMode: string, location?: string): Promise<WorkSession> => {
    const response = await httpClient.post<WorkSession>(`${API_ENDPOINTS.REMOTE_WORK}/sessions/start`, {
      work_mode: workMode,
      location,
    }, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  endSession: async (sessionId: string, notes?: string): Promise<WorkSession> => {
    const response = await httpClient.post<WorkSession>(`${API_ENDPOINTS.REMOTE_WORK}/sessions/${sessionId}/end`, {
      notes,
    });
    return response.data;
  },

  getActiveSession: async (employeeId: string): Promise<WorkSession | null> => {
    const response = await httpClient.get<WorkSession | null>(`${API_ENDPOINTS.REMOTE_WORK}/sessions/employee/${employeeId}/active`);
    return response.data;
  },

  // === 在线状态 ===
  setPresence: async (employeeId: string, status: string, workMode: string, statusMessage?: string): Promise<PresenceStatus> => {
    const response = await httpClient.post<PresenceStatus>(`${API_ENDPOINTS.REMOTE_WORK}/presence/set`, {
      status,
      work_mode: workMode,
      status_message: statusMessage,
    }, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  getPresence: async (employeeId: string): Promise<PresenceStatus | null> => {
    const response = await httpClient.get<PresenceStatus | null>(`${API_ENDPOINTS.REMOTE_WORK}/presence/${employeeId}`);
    return response.data;
  },

  getAllPresence: async (): Promise<PresenceStatus[]> => {
    const response = await httpClient.get<PresenceStatus[]>(`${API_ENDPOINTS.REMOTE_WORK}/presence`);
    return response.data;
  },

  getAvailableEmployees: async (): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.REMOTE_WORK}/presence/available`);
    return response.data;
  },

  // === 虚拟工作空间 ===
  getWorkspaces: async (ownerId?: string, workspaceType?: string): Promise<VirtualWorkspace[]> => {
    const params: Record<string, unknown> = {};
    if (ownerId) params.owner_id = ownerId;
    if (workspaceType) params.workspace_type = workspaceType;
    const response = await httpClient.get<VirtualWorkspace[]>(`${API_ENDPOINTS.REMOTE_WORK}/workspaces`, { params });
    return response.data;
  },

  createWorkspace: async (data: {
    name: string;
    owner_id: string;
    workspace_type?: string;
    capacity?: number;
    description?: string;
    is_private?: boolean;
  }): Promise<VirtualWorkspace> => {
    const response = await httpClient.post<VirtualWorkspace>(`${API_ENDPOINTS.REMOTE_WORK}/workspaces`, data);
    return response.data;
  },

  joinWorkspace: async (workspaceId: string, employeeId: string): Promise<VirtualWorkspace> => {
    const response = await httpClient.post<VirtualWorkspace>(`${API_ENDPOINTS.REMOTE_WORK}/workspaces/${workspaceId}/join`, null, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  leaveWorkspace: async (workspaceId: string, employeeId: string): Promise<VirtualWorkspace> => {
    const response = await httpClient.post<VirtualWorkspace>(`${API_ENDPOINTS.REMOTE_WORK}/workspaces/${workspaceId}/leave`, null, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  // === 团队活动 ===
  getTeamEvents: async (organizerId?: string, upcomingOnly: boolean = false): Promise<ApiResponse[]> => {
    const params: Record<string, unknown> = { upcoming_only: upcomingOnly };
    if (organizerId) params.organizer_id = organizerId;
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.REMOTE_WORK}/events`, { params });
    return response.data;
  },

  createEvent: async (data: {
    title: string;
    organizer_id: string;
    event_type?: string;
    start_time?: string;
    duration_minutes?: number;
    description?: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.REMOTE_WORK}/events`, data);
    return response.data;
  },

  rsvpEvent: async (eventId: string, employeeId: string, status: 'going' | 'not_going' | 'maybe'): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.REMOTE_WORK}/events/${eventId}/rsvp`, {
      status,
    }, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  // === 虚拟茶水间 ===
  getActiveWaterCoolers: async (): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.REMOTE_WORK}/water-cooler`);
    return response.data;
  },

  startWaterCooler: async (initiatorId: string, topic?: string): Promise<ApiResponse> => {
    const params: Record<string, unknown> = { initiator_id: initiatorId };
    if (topic) params.topic = topic;
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.REMOTE_WORK}/water-cooler/start`, null, { params });
    return response.data;
  },

  // === 仪表盘 ===
  getDashboard: async (employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.REMOTE_WORK}/dashboard/${employeeId}`);
    return response.data;
  },
};
