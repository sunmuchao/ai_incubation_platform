/**
 * 员工福祉 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wellnessApi } from '@/services/wellnessApi';

export const useWellness = () => {
  const queryClient = useQueryClient();

  // === 心理健康评估 ===
  const employeeAssessmentsQuery = (employeeId: string, assessmentType?: string, limit: number = 10) =>
    useQuery({
      queryKey: ['wellness', 'assessments', employeeId, assessmentType],
      queryFn: () => wellnessApi.getEmployeeAssessments(employeeId, assessmentType, limit),
      enabled: !!employeeId,
    });

  const createAssessmentMutation = useMutation({
    mutationFn: (data: { employee_id: string; assessment_type: string; responses: Record<string, unknown> }) =>
      wellnessApi.createAssessment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wellness', 'assessments'] });
    },
  });

  // === 压力水平追踪 ===
  const logStressLevelMutation = useMutation({
    mutationFn: ({ employeeId, level, notes }: { employeeId: string; level: number; notes?: string }) =>
      wellnessApi.logStressLevel(employeeId, level, notes),
  });

  const stressTrendQuery = (employeeId: string, days: number = 30) =>
    useQuery({
      queryKey: ['wellness', 'stressTrend', employeeId, days],
      queryFn: () => wellnessApi.getStressTrend(employeeId, days),
      enabled: !!employeeId,
    });

  // === 心理咨询 ===
  const employeeSessionsQuery = (employeeId: string, status?: string) =>
    useQuery({
      queryKey: ['wellness', 'sessions', employeeId, status],
      queryFn: () => wellnessApi.getEmployeeSessions(employeeId, status),
      enabled: !!employeeId,
    });

  const bookCounselingSessionMutation = useMutation({
    mutationFn: (data: { employee_id: string; counselor_id: string; session_date: string; duration_minutes?: number }) =>
      wellnessApi.bookCounselingSession(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wellness', 'sessions'] });
    },
  });

  // === 请假管理 ===
  const employeeLeavesQuery = (employeeId: string, status?: string) =>
    useQuery({
      queryKey: ['wellness', 'leaves', employeeId, status],
      queryFn: () => wellnessApi.getEmployeeLeaves(employeeId, status),
      enabled: !!employeeId,
    });

  const requestLeaveMutation = useMutation({
    mutationFn: (data: { employee_id: string; leave_type: string; start_date: string; end_date: string; reason?: string }) =>
      wellnessApi.requestLeave(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wellness', 'leaves'] });
    },
  });

  const approveLeaveMutation = useMutation({
    mutationFn: ({ leaveId, approverId }: { leaveId: string; approverId: string }) =>
      wellnessApi.approveLeave(leaveId, approverId),
  });

  // === 仪表盘 ===
  const wellnessDashboardQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['wellness', 'dashboard', employeeId],
      queryFn: () => wellnessApi.getWellnessDashboard(employeeId),
      enabled: !!employeeId,
    });

  const organizationWellnessQuery = (tenantId: string) =>
    useQuery({
      queryKey: ['wellness', 'organization', tenantId],
      queryFn: () => wellnessApi.getOrganizationWellness(tenantId),
      enabled: !!tenantId,
    });

  // === 离职风险预测 ===
  const turnoverRiskQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['wellness', 'turnoverRisk', employeeId],
      queryFn: () => wellnessApi.getTurnoverRisk(employeeId),
      enabled: !!employeeId,
    });

  return {
    // 心理健康评估
    employeeAssessmentsQuery,
    createAssessmentMutation,
    // 压力水平追踪
    logStressLevelMutation,
    stressTrendQuery,
    // 心理咨询
    employeeSessionsQuery,
    bookCounselingSessionMutation,
    // 请假管理
    employeeLeavesQuery,
    requestLeaveMutation,
    approveLeaveMutation,
    // 仪表盘
    wellnessDashboardQuery,
    organizationWellnessQuery,
    // 离职风险
    turnoverRiskQuery,
  };
};
