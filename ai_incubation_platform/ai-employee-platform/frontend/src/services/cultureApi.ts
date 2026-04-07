/**
 * 组织文化 API 服务
 */
import { httpClient } from './http';
import { API_ENDPOINTS } from '@/config';
import type { ApiResponse } from '@/types';

export interface CultureValue {
  id: string;
  name: string;
  description: string;
  value_type: 'core' | 'behavioral' | 'operational' | 'aspirational';
  behavioral_indicators: string[];
  priority: number;
}

export interface Recognition {
  id: string;
  recipient_id: string;
  giver_id: string;
  recognition_type: 'peer' | 'manager' | 'team' | 'company';
  category: string;
  title: string;
  description: string;
  points: number;
  created_at: string;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  category: string;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum' | 'diamond';
  icon_url: string;
  criteria: Record<string, unknown>;
}

export interface TeamEvent {
  id: string;
  team_id: string;
  organizer_id: string;
  event_type: 'team_building' | 'celebration' | 'workshop' | 'social';
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  location: string;
  status: 'scheduled' | 'ongoing' | 'completed' | 'cancelled';
}

export const cultureApi = {
  // === 文化价值观 ===
  getCultureValues: async (tenantId: string, activeOnly: boolean = true): Promise<CultureValue[]> => {
    const response = await httpClient.get<CultureValue[]>(`${API_ENDPOINTS.CULTURE}/values`, {
      params: { tenant_id: tenantId, active_only: activeOnly },
    });
    return response.data;
  },

  createCultureValue: async (data: {
    tenant_id: string;
    name: string;
    description: string;
    value_type: string;
    behavioral_indicators?: string[];
    priority?: number;
  }): Promise<CultureValue> => {
    const response = await httpClient.post<CultureValue>(`${API_ENDPOINTS.CULTURE}/values`, data);
    return response.data;
  },

  assessEmployeeAlignment: async (data: {
    value_id: string;
    employee_id: string;
    alignment_score: number;
    assessor_id: string;
    evidence_examples?: string[];
    comments?: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(
      `${API_ENDPOINTS.CULTURE}/values/${data.value_id}/alignments`,
      data.evidence_examples,
      {
        params: {
          employee_id: data.employee_id,
          alignment_score: data.alignment_score,
          assessor_id: data.assessor_id,
          comments: data.comments,
        },
      }
    );
    return response.data;
  },

  // === 员工认可 ===
  giveRecognition: async (data: {
    tenant_id: string;
    recipient_id: string;
    giver_id: string;
    recognition_type: string;
    category: string;
    title: string;
    description: string;
    points?: number;
  }): Promise<Recognition> => {
    const response = await httpClient.post<Recognition>(`${API_ENDPOINTS.CULTURE}/recognitions`, data);
    return response.data;
  },

  getEmployeeRecognitions: async (employeeId: string, tenantId: string, limit: number = 50): Promise<Recognition[]> => {
    const response = await httpClient.get<Recognition[]>(
      `${API_ENDPOINTS.CULTURE}/employees/${employeeId}/recognitions`,
      { params: { tenant_id: tenantId, limit } }
    );
    return response.data;
  },

  // === 徽章系统 ===
  getBadges: async (tenantId: string, activeOnly: boolean = true): Promise<Badge[]> => {
    const response = await httpClient.get<Badge[]>(`${API_ENDPOINTS.CULTURE}/badges`, {
      params: { tenant_id: tenantId, active_only: activeOnly },
    });
    return response.data;
  },

  createBadge: async (data: {
    tenant_id: string;
    name: string;
    description: string;
    category: string;
    tier: string;
    icon_url?: string;
    criteria?: Record<string, unknown>;
    points_value?: number;
  }): Promise<Badge> => {
    const response = await httpClient.post<Badge>(`${API_ENDPOINTS.CULTURE}/badges`, data);
    return response.data;
  },

  awardBadge: async (data: {
    tenant_id: string;
    employee_id: string;
    badge_id: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.CULTURE}/badges/award`, data);
    return response.data;
  },

  getEmployeeBadges: async (employeeId: string): Promise<Badge[]> => {
    const response = await httpClient.get<Badge[]>(`${API_ENDPOINTS.CULTURE}/employees/${employeeId}/badges`);
    return response.data;
  },

  // === 团队活动 ===
  getTeamEvents: async (tenantId: string, teamId?: string): Promise<TeamEvent[]> => {
    const params: Record<string, unknown> = { tenant_id: tenantId };
    if (teamId) params.team_id = teamId;
    const response = await httpClient.get<TeamEvent[]>(`${API_ENDPOINTS.CULTURE}/team-events`, { params });
    return response.data;
  },

  createTeamEvent: async (data: {
    tenant_id: string;
    team_id: string;
    organizer_id: string;
    event_type: string;
    title: string;
    description: string;
    start_time: string;
    end_time: string;
    location?: string;
  }): Promise<TeamEvent> => {
    const response = await httpClient.post<TeamEvent>(`${API_ENDPOINTS.CULTURE}/team-events`, data);
    return response.data;
  },

  joinTeamEvent: async (eventId: string, employeeId: string): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.CULTURE}/team-events/${eventId}/join`, null, {
      params: { employee_id: employeeId },
    });
    return response.data;
  },

  // === 文化脉冲调查 ===
  getPulses: async (tenantId: string, activeOnly: boolean = true): Promise<ApiResponse[]> => {
    const response = await httpClient.get<ApiResponse[]>(`${API_ENDPOINTS.CULTURE}/pulses`, {
      params: { tenant_id: tenantId, active_only: activeOnly },
    });
    return response.data;
  },

  submitPulseResponse: async (data: {
    pulse_id: string;
    respondent_id: string;
    response_value?: number;
    response_text?: string;
  }): Promise<ApiResponse> => {
    const response = await httpClient.post<ApiResponse>(`${API_ENDPOINTS.CULTURE}/pulses/${data.pulse_id}/responses`, {
      response_text: data.response_text,
    }, {
      params: {
        respondent_id: data.respondent_id,
        response_value: data.response_value,
      },
    });
    return response.data;
  },

  // === 仪表盘 ===
  getDashboard: async (tenantId: string, days: number = 30): Promise<ApiResponse> => {
    const response = await httpClient.get<ApiResponse>(`${API_ENDPOINTS.CULTURE}/dashboard`, {
      params: { tenant_id: tenantId, days },
    });
    return response.data;
  },
};
