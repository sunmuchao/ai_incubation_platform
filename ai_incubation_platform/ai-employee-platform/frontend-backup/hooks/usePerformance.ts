/**
 * 绩效管理 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { performanceApi } from '@/services/performanceApi';

export const usePerformance = () => {
  const queryClient = useQueryClient();

  // === 评估周期 ===
  const reviewCyclesQuery = (status?: string, limit: number = 20) =>
    useQuery({
      queryKey: ['performance', 'reviewCycles', status, limit],
      queryFn: () => performanceApi.getReviewCycles(status, limit),
    });

  const createReviewCycleMutation = useMutation({
    mutationFn: (data: {
      name: string;
      start_date: string;
      end_date: string;
      review_type: string;
      target_employee_ids?: string[];
    }) => performanceApi.createReviewCycle(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'reviewCycles'] });
    },
  });

  const launchReviewCycleMutation = useMutation({
    mutationFn: (cycleId: string) => performanceApi.launchReviewCycle(cycleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'reviewCycles'] });
    },
  });

  const completeReviewCycleMutation = useMutation({
    mutationFn: (cycleId: string) => performanceApi.completeReviewCycle(cycleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'reviewCycles'] });
    },
  });

  // === 绩效评估 ===
  const employeeReviewsQuery = (employeeId: string, status?: string, limit: number = 20) =>
    useQuery({
      queryKey: ['performance', 'reviews', employeeId, status],
      queryFn: () => performanceApi.getEmployeeReviews(employeeId, status, limit),
      enabled: !!employeeId,
    });

  const createReviewMutation = useMutation({
    mutationFn: (data: {
      employee_id: string;
      reviewer_id: string;
      review_type: string;
      cycle_id?: string;
      due_date?: string;
    }) => performanceApi.createReview(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'reviews'] });
    },
  });

  const updateReviewMutation = useMutation({
    mutationFn: ({ reviewId, data }: {
      reviewId: string;
      data: {
        scores?: Record<string, number>;
        comments?: string;
        strengths?: string[];
        areas_for_improvement?: string[];
        goals?: string[];
      };
    }) => performanceApi.updateReview(reviewId, data),
  });

  const submitReviewMutation = useMutation({
    mutationFn: (reviewId: string) => performanceApi.submitReview(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'reviews'] });
    },
  });

  // === OKR 目标 ===
  const employeeObjectivesQuery = (employeeId: string, status?: string) =>
    useQuery({
      queryKey: ['performance', 'objectives', employeeId, status],
      queryFn: () => performanceApi.getEmployeeObjectives(employeeId, status),
      enabled: !!employeeId,
    });

  const createObjectiveMutation = useMutation({
    mutationFn: (data: {
      title: string;
      description?: string;
      start_date: string;
      due_date: string;
      employee_id?: string;
      parent_objective_id?: string;
    }) => performanceApi.createObjective(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'objectives'] });
    },
  });

  const updateObjectiveMutation = useMutation({
    mutationFn: ({ objectiveId, data }: {
      objectiveId: string;
      data: {
        title?: string;
        progress?: number;
        status?: string;
        confidence_level?: number;
      };
    }) => performanceApi.updateObjective(objectiveId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['performance', 'objectives'] });
    },
  });

  const createKeyResultMutation = useMutation({
    mutationFn: ({ objectiveId, data }: {
      objectiveId: string;
      data: {
        title: string;
        target_value: number;
        start_value?: number;
        unit?: string;
      };
    }) => performanceApi.createKeyResult(objectiveId, data),
  });

  const updateKeyResultProgressMutation = useMutation({
    mutationFn: ({ krId, currentValue }: { krId: string; currentValue: number }) =>
      performanceApi.updateKeyResultProgress(krId, currentValue),
  });

  // === 仪表盘 ===
  const performanceDashboardQuery = (employeeIds?: string[]) =>
    useQuery({
      queryKey: ['performance', 'dashboard', employeeIds],
      queryFn: () => performanceApi.getDashboard(employeeIds),
    });

  const benchmarksQuery = useQuery({
    queryKey: ['performance', 'benchmarks'],
    queryFn: () => performanceApi.getBenchmarks(),
  });

  // === 1 对 1 会议 ===
  const employeeMeetingsQuery = (employeeId: string, limit: number = 20) =>
    useQuery({
      queryKey: ['performance', 'meetings', employeeId],
      queryFn: () => performanceApi.getEmployeeMeetings(employeeId, limit),
      enabled: !!employeeId,
    });

  const createMeetingMutation = useMutation({
    mutationFn: (data: {
      employee_id: string;
      manager_id: string;
      meeting_date: string;
      agenda?: string;
      meeting_type?: string;
    }) => performanceApi.createMeeting(data),
  });

  return {
    // 评估周期
    reviewCyclesQuery,
    createReviewCycleMutation,
    launchReviewCycleMutation,
    completeReviewCycleMutation,
    // 绩效评估
    employeeReviewsQuery,
    createReviewMutation,
    updateReviewMutation,
    submitReviewMutation,
    // OKR 目标
    employeeObjectivesQuery,
    createObjectiveMutation,
    updateObjectiveMutation,
    createKeyResultMutation,
    updateKeyResultProgressMutation,
    // 仪表盘
    performanceDashboardQuery,
    benchmarksQuery,
    // 1 对 1 会议
    employeeMeetingsQuery,
    createMeetingMutation,
  };
};
