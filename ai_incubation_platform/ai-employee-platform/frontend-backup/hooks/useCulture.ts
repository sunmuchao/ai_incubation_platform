/**
 * 组织文化 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cultureApi } from '@/services/cultureApi';

export const useCulture = () => {
  const queryClient = useQueryClient();

  // === 文化价值观 ===
  const cultureValuesQuery = (tenantId: string, activeOnly: boolean = true) =>
    useQuery({
      queryKey: ['culture', 'values', tenantId],
      queryFn: () => cultureApi.getCultureValues(tenantId, activeOnly),
      enabled: !!tenantId,
    });

  const createCultureValueMutation = useMutation({
    mutationFn: (data: {
      tenant_id: string;
      name: string;
      description: string;
      value_type: string;
      behavioral_indicators?: string[];
      priority?: number;
    }) => cultureApi.createCultureValue(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['culture', 'values'] });
    },
  });

  const assessEmployeeAlignmentMutation = useMutation({
    mutationFn: (data: {
      value_id: string;
      employee_id: string;
      alignment_score: number;
      assessor_id: string;
      evidence_examples?: string[];
      comments?: string;
    }) => cultureApi.assessEmployeeAlignment(data),
  });

  // === 员工认可 ===
  const employeeRecognitionsQuery = (employeeId: string, tenantId: string, limit: number = 50) =>
    useQuery({
      queryKey: ['culture', 'recognitions', employeeId, tenantId],
      queryFn: () => cultureApi.getEmployeeRecognitions(employeeId, tenantId, limit),
      enabled: !!employeeId && !!tenantId,
    });

  const giveRecognitionMutation = useMutation({
    mutationFn: (data: {
      tenant_id: string;
      recipient_id: string;
      giver_id: string;
      recognition_type: string;
      category: string;
      title: string;
      description: string;
      points?: number;
    }) => cultureApi.giveRecognition(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['culture', 'recognitions'] });
    },
  });

  // === 徽章系统 ===
  const badgesQuery = (tenantId: string, activeOnly: boolean = true) =>
    useQuery({
      queryKey: ['culture', 'badges', tenantId],
      queryFn: () => cultureApi.getBadges(tenantId, activeOnly),
      enabled: !!tenantId,
    });

  const employeeBadgesQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['culture', 'employeeBadges', employeeId],
      queryFn: () => cultureApi.getEmployeeBadges(employeeId),
      enabled: !!employeeId,
    });

  const createBadgeMutation = useMutation({
    mutationFn: (data: {
      tenant_id: string;
      name: string;
      description: string;
      category: string;
      tier: string;
      icon_url?: string;
      criteria?: Record<string, unknown>;
      points_value?: number;
    }) => cultureApi.createBadge(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['culture', 'badges'] });
    },
  });

  const awardBadgeMutation = useMutation({
    mutationFn: (data: { tenant_id: string; employee_id: string; badge_id: string }) =>
      cultureApi.awardBadge(data),
  });

  // === 团队活动 ===
  const teamEventsQuery = (tenantId: string, teamId?: string) =>
    useQuery({
      queryKey: ['culture', 'teamEvents', tenantId, teamId],
      queryFn: () => cultureApi.getTeamEvents(tenantId, teamId),
      enabled: !!tenantId,
    });

  const createTeamEventMutation = useMutation({
    mutationFn: (data: {
      tenant_id: string;
      team_id: string;
      organizer_id: string;
      event_type: string;
      title: string;
      description: string;
      start_time: string;
      end_time: string;
      location?: string;
    }) => cultureApi.createTeamEvent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['culture', 'teamEvents'] });
    },
  });

  const joinTeamEventMutation = useMutation({
    mutationFn: ({ eventId, employeeId }: { eventId: string; employeeId: string }) =>
      cultureApi.joinTeamEvent(eventId, employeeId),
  });

  // === 文化脉冲调查 ===
  const pulsesQuery = (tenantId: string, activeOnly: boolean = true) =>
    useQuery({
      queryKey: ['culture', 'pulses', tenantId],
      queryFn: () => cultureApi.getPulses(tenantId, activeOnly),
      enabled: !!tenantId,
    });

  const submitPulseResponseMutation = useMutation({
    mutationFn: (data: { pulse_id: string; respondent_id: string; response_value?: number; response_text?: string }) =>
      cultureApi.submitPulseResponse(data),
  });

  // === 仪表盘 ===
  const cultureDashboardQuery = (tenantId: string, days: number = 30) =>
    useQuery({
      queryKey: ['culture', 'dashboard', tenantId, days],
      queryFn: () => cultureApi.getDashboard(tenantId, days),
      enabled: !!tenantId,
    });

  return {
    // 文化价值观
    cultureValuesQuery,
    createCultureValueMutation,
    assessEmployeeAlignmentMutation,
    // 员工认可
    employeeRecognitionsQuery,
    giveRecognitionMutation,
    // 徽章系统
    badgesQuery,
    employeeBadgesQuery,
    createBadgeMutation,
    awardBadgeMutation,
    // 团队活动
    teamEventsQuery,
    createTeamEventMutation,
    joinTeamEventMutation,
    // 文化脉冲调查
    pulsesQuery,
    submitPulseResponseMutation,
    // 仪表盘
    cultureDashboardQuery,
  };
};
