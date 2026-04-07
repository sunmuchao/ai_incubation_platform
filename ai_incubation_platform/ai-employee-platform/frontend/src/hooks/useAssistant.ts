/**
 * 智能助手 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { assistantApi } from '@/services/assistantApi';

export const useAssistant = () => {
  const queryClient = useQueryClient();

  // === 任务推荐 ===
  const taskRecommendationsQuery = (employeeId: string, limit: number = 5) =>
    useQuery({
      queryKey: ['assistant', 'taskRecommendations', employeeId],
      queryFn: () => assistantApi.getTaskRecommendations(employeeId, limit),
      enabled: !!employeeId,
    });

  const scheduledTasksQuery = (employeeId: string, date?: string) =>
    useQuery({
      queryKey: ['assistant', 'scheduledTasks', employeeId, date],
      queryFn: () => assistantApi.getScheduledTasks(employeeId, date),
      enabled: !!employeeId,
    });

  const completeTaskMutation = useMutation({
    mutationFn: ({ taskId, employeeId, notes }: { taskId: string; employeeId: string; notes?: string }) =>
      assistantApi.completeTask(taskId, employeeId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assistant'] });
    },
  });

  // === 智能日程 ===
  const optimizedScheduleQuery = (employeeId: string, date: string) =>
    useQuery({
      queryKey: ['assistant', 'optimizedSchedule', employeeId, date],
      queryFn: () => assistantApi.getOptimizedSchedule(employeeId, date),
      enabled: !!employeeId && !!date,
    });

  const suggestFocusTimeMutation = useMutation({
    mutationFn: ({ employeeId, duration }: { employeeId: string; duration: number }) =>
      assistantApi.suggestFocusTime(employeeId, duration),
  });

  // === 会议管理 ===
  const upcomingMeetingsQuery = (employeeId: string, hours: number = 24) =>
    useQuery({
      queryKey: ['assistant', 'upcomingMeetings', employeeId],
      queryFn: () => assistantApi.getUpcomingMeetings(employeeId, hours),
      enabled: !!employeeId,
    });

  const prepareMeetingAgendaMutation = useMutation({
    mutationFn: (meetingId: string) => assistantApi.prepareMeetingAgenda(meetingId),
  });

  // === 会议摘要 ===
  const meetingSummariesQuery = (employeeId: string, limit: number = 10) =>
    useQuery({
      queryKey: ['assistant', 'meetingSummaries', employeeId],
      queryFn: () => assistantApi.getMeetingSummaries(employeeId, limit),
      enabled: !!employeeId,
    });

  const generateMeetingSummaryMutation = useMutation({
    mutationFn: (data: { meeting_id: string; transcript?: string; notes?: string }) =>
      assistantApi.generateMeetingSummary(data),
  });

  // === 工作简报 ===
  const dailyReportsQuery = (employeeId: string, limit: number = 10) =>
    useQuery({
      queryKey: ['assistant', 'dailyReports', employeeId],
      queryFn: () => assistantApi.getDailyReports(employeeId, limit),
      enabled: !!employeeId,
    });

  const generateDailyReportMutation = useMutation({
    mutationFn: ({ employeeId, date }: { employeeId: string; date?: string }) =>
      assistantApi.generateDailyReport(employeeId, date),
  });

  // === 智能洞察 ===
  const insightsQuery = (employeeId: string, category?: string) =>
    useQuery({
      queryKey: ['assistant', 'insights', employeeId, category],
      queryFn: () => assistantApi.getInsights(employeeId, category),
      enabled: !!employeeId,
    });

  return {
    // 任务推荐
    taskRecommendationsQuery,
    scheduledTasksQuery,
    completeTaskMutation,
    // 智能日程
    optimizedScheduleQuery,
    suggestFocusTimeMutation,
    // 会议管理
    upcomingMeetingsQuery,
    prepareMeetingAgendaMutation,
    // 会议摘要
    meetingSummariesQuery,
    generateMeetingSummaryMutation,
    // 工作简报
    dailyReportsQuery,
    generateDailyReportMutation,
    // 智能洞察
    insightsQuery,
  };
};
