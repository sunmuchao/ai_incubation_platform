/**
 * 远程工作 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { remoteWorkApi } from '@/services/remoteWorkApi';

export const useRemoteWork = () => {
  const queryClient = useQueryClient();

  // === 工作会话 ===
  const activeSessionQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['remoteWork', 'activeSession', employeeId],
      queryFn: () => remoteWorkApi.getActiveSession(employeeId),
      enabled: !!employeeId,
    });

  const startSessionMutation = useMutation({
    mutationFn: ({ employeeId, workMode, location }: { employeeId: string; workMode: string; location?: string }) =>
      remoteWorkApi.startSession(employeeId, workMode, location),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'activeSession'] });
    },
  });

  const endSessionMutation = useMutation({
    mutationFn: ({ sessionId, notes }: { sessionId: string; notes?: string }) =>
      remoteWorkApi.endSession(sessionId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'activeSession'] });
    },
  });

  // === 在线状态 ===
  const presenceQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['remoteWork', 'presence', employeeId],
      queryFn: () => remoteWorkApi.getPresence(employeeId),
      enabled: !!employeeId,
    });

  const allPresenceQuery = useQuery({
    queryKey: ['remoteWork', 'allPresence'],
    queryFn: () => remoteWorkApi.getAllPresence(),
  });

  const availableEmployeesQuery = useQuery({
    queryKey: ['remoteWork', 'availableEmployees'],
    queryFn: () => remoteWorkApi.getAvailableEmployees(),
  });

  const setPresenceMutation = useMutation({
    mutationFn: ({ employeeId, status, workMode, statusMessage }: {
      employeeId: string;
      status: string;
      workMode: string;
      statusMessage?: string;
    }) => remoteWorkApi.setPresence(employeeId, status, workMode, statusMessage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'presence'] });
    },
  });

  // === 虚拟工作空间 ===
  const workspacesQuery = (ownerId?: string, workspaceType?: string) =>
    useQuery({
      queryKey: ['remoteWork', 'workspaces', ownerId, workspaceType],
      queryFn: () => remoteWorkApi.getWorkspaces(ownerId, workspaceType),
    });

  const createWorkspaceMutation = useMutation({
    mutationFn: (data: {
      name: string;
      owner_id: string;
      workspace_type?: string;
      capacity?: number;
      description?: string;
      is_private?: boolean;
    }) => remoteWorkApi.createWorkspace(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'workspaces'] });
    },
  });

  const joinWorkspaceMutation = useMutation({
    mutationFn: ({ workspaceId, employeeId }: { workspaceId: string; employeeId: string }) =>
      remoteWorkApi.joinWorkspace(workspaceId, employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'workspaces'] });
    },
  });

  const leaveWorkspaceMutation = useMutation({
    mutationFn: ({ workspaceId, employeeId }: { workspaceId: string; employeeId: string }) =>
      remoteWorkApi.leaveWorkspace(workspaceId, employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remoteWork', 'workspaces'] });
    },
  });

  // === 团队活动 ===
  const teamEventsQuery = (organizerId?: string, upcomingOnly: boolean = false) =>
    useQuery({
      queryKey: ['remoteWork', 'events', organizerId, upcomingOnly],
      queryFn: () => remoteWorkApi.getTeamEvents(organizerId, upcomingOnly),
    });

  const createEventMutation = useMutation({
    mutationFn: (data: {
      title: string;
      organizer_id: string;
      event_type?: string;
      start_time?: string;
      duration_minutes?: number;
      description?: string;
    }) => remoteWorkApi.createEvent(data),
  });

  const rsvpEventMutation = useMutation({
    mutationFn: ({ eventId, employeeId, status }: {
      eventId: string;
      employeeId: string;
      status: 'going' | 'not_going' | 'maybe';
    }) => remoteWorkApi.rsvpEvent(eventId, employeeId, status),
  });

  // === 虚拟茶水间 ===
  const activeWaterCoolersQuery = useQuery({
    queryKey: ['remoteWork', 'waterCoolers'],
    queryFn: () => remoteWorkApi.getActiveWaterCoolers(),
  });

  const startWaterCoolerMutation = useMutation({
    mutationFn: ({ initiatorId, topic }: { initiatorId: string; topic?: string }) =>
      remoteWorkApi.startWaterCooler(initiatorId, topic),
  });

  // === 仪表盘 ===
  const remoteWorkDashboardQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['remoteWork', 'dashboard', employeeId],
      queryFn: () => remoteWorkApi.getDashboard(employeeId),
      enabled: !!employeeId,
    });

  return {
    // 工作会话
    activeSessionQuery,
    startSessionMutation,
    endSessionMutation,
    // 在线状态
    presenceQuery,
    allPresenceQuery,
    availableEmployeesQuery,
    setPresenceMutation,
    // 虚拟工作空间
    workspacesQuery,
    createWorkspaceMutation,
    joinWorkspaceMutation,
    leaveWorkspaceMutation,
    // 团队活动
    teamEventsQuery,
    createEventMutation,
    rsvpEventMutation,
    // 虚拟茶水间
    activeWaterCoolersQuery,
    startWaterCoolerMutation,
    // 仪表盘
    remoteWorkDashboardQuery,
  };
};
