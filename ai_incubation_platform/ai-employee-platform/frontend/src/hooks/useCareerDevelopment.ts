/**
 * 职业发展 Hook
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { careerDevelopmentApi } from '@/services/careerDevelopmentApi';

export const useCareerDevelopment = () => {
  const queryClient = useQueryClient();

  // === 技能图谱 ===
  const skillsQuery = (category?: string, parent_skill_id?: string, search?: string, limit: number = 100) =>
    useQuery({
      queryKey: ['career', 'skills', category, parent_skill_id, search, limit],
      queryFn: () => careerDevelopmentApi.getSkills(category, parent_skill_id, search, limit),
    });

  const skillTreeQuery = (root_skill_id?: string) =>
    useQuery({
      queryKey: ['career', 'skillTree', root_skill_id],
      queryFn: () => careerDevelopmentApi.getSkillTree(root_skill_id),
    });

  const learningPathQuery = (from_skill_id: string, to_skill_id: string) =>
    useQuery({
      queryKey: ['career', 'learningPath', from_skill_id, to_skill_id],
      queryFn: () => careerDevelopmentApi.getLearningPath(from_skill_id, to_skill_id),
      enabled: !!from_skill_id && !!to_skill_id,
    });

  // === 员工技能 ===
  const employeeSkillsQuery = (employeeId: string, level?: string, category?: string) =>
    useQuery({
      queryKey: ['career', 'employeeSkills', employeeId, level, category],
      queryFn: () => careerDevelopmentApi.getEmployeeSkills(employeeId, level, category),
      enabled: !!employeeId,
    });

  const addEmployeeSkillMutation = useMutation({
    mutationFn: (data: {
      employee_id: string;
      skill_id: string;
      level: string;
      years_of_experience?: number;
    }) => careerDevelopmentApi.addEmployeeSkill(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['career', 'employeeSkills'] });
    },
  });

  // === 职业角色 ===
  const careerRolesQuery = (path_type?: string, level?: number, search?: string, limit: number = 100) =>
    useQuery({
      queryKey: ['career', 'careerRoles', path_type, level, search, limit],
      queryFn: () => careerDevelopmentApi.getCareerRoles(path_type, level, search, limit),
    });

  const recommendCareerPathsQuery = (employeeId: string, limit: number = 5) =>
    useQuery({
      queryKey: ['career', 'recommendPaths', employeeId],
      queryFn: () => careerDevelopmentApi.recommendCareerPaths(employeeId, limit),
      enabled: !!employeeId,
    });

  // === 发展计划 ===
  const developmentPlansQuery = (employeeId: string, status?: string, limit: number = 100) =>
    useQuery({
      queryKey: ['career', 'developmentPlans', employeeId, status, limit],
      queryFn: () => careerDevelopmentApi.getDevelopmentPlans(employeeId, status, limit),
      enabled: !!employeeId,
    });

  const createDevelopmentPlanMutation = useMutation({
    mutationFn: (data: {
      employee_id: string;
      plan_name: string;
      target_role_id?: string;
      start_date?: string;
      target_completion_date?: string;
    }) => careerDevelopmentApi.createDevelopmentPlan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['career', 'developmentPlans'] });
    },
  });

  const planProgressQuery = (planId: string) =>
    useQuery({
      queryKey: ['career', 'planProgress', planId],
      queryFn: () => careerDevelopmentApi.getPlanProgress(planId),
      enabled: !!planId,
    });

  // === 导师匹配 ===
  const mentorMatchesQuery = (menteeId: string, limit: number = 3) =>
    useQuery({
      queryKey: ['career', 'mentorMatches', menteeId],
      queryFn: () => careerDevelopmentApi.getMentorMatches(menteeId, limit),
      enabled: !!menteeId,
    });

  // === 仪表盘 ===
  const careerDashboardQuery = (employeeId: string) =>
    useQuery({
      queryKey: ['career', 'dashboard', employeeId],
      queryFn: () => careerDevelopmentApi.getDashboard(employeeId),
      enabled: !!employeeId,
    });

  return {
    // 技能图谱
    skillsQuery,
    skillTreeQuery,
    learningPathQuery,
    // 员工技能
    employeeSkillsQuery,
    addEmployeeSkillMutation,
    // 职业角色
    careerRolesQuery,
    recommendCareerPathsQuery,
    // 发展计划
    developmentPlansQuery,
    createDevelopmentPlanMutation,
    planProgressQuery,
    // 导师匹配
    mentorMatchesQuery,
    // 仪表盘
    careerDashboardQuery,
  };
};
