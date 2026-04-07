/**
 * 工人画像 API 服务
 */
import { api } from './api';
import type { WorkerProfile, WorkerStats } from '@/types';

const WORKERS_BASE_URL = '/api/workers';

export const workerService = {
  /**
   * 获取工人列表
   */
  listWorkers: async (skip: number = 0, limit: number = 100) => {
    const response = await api.get<{ workers: WorkerProfile[]; total: number; skip: number; limit: number }>(
      `${WORKERS_BASE_URL}?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  /**
   * 搜索工人
   */
  searchWorkers: async (params: {
    skills?: string;
    location?: string;
    min_level?: number;
    min_rating?: number;
    min_success_rate?: number;
    skip?: number;
    limit?: number;
  }) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        queryParams.append(key, String(value));
      }
    });
    const response = await api.get<WorkerProfile[]>(`${WORKERS_BASE_URL}/search?${queryParams}`);
    return response.data;
  },

  /**
   * 获取工人详情
   */
  getWorker: async (workerId: string) => {
    const response = await api.get<WorkerProfile>(`${WORKERS_BASE_URL}/${workerId}`);
    return response.data;
  },

  /**
   * 创建或更新工人画像
   */
  createOrUpdateWorker: async (workerId: string, profileData: {
    name: string;
    avatar?: string;
    phone?: string;
    email?: string;
    location?: string;
    skills: string[];
    level: number;
    tags: string[];
    external_profile_id?: string;
  }) => {
    const response = await api.post<WorkerProfile>(`${WORKERS_BASE_URL}/${workerId}`, profileData);
    return response.data;
  },

  /**
   * 部分更新工人画像
   */
  updateWorker: async (workerId: string, profileData: Partial<{
    name: string;
    avatar: string;
    phone: string;
    email: string;
    location: string;
    skills: string[];
    level: number;
    tags: string[];
    external_profile_id: string;
  }>) => {
    const response = await api.patch<WorkerProfile>(`${WORKERS_BASE_URL}/${workerId}`, profileData);
    return response.data;
  },

  /**
   * 删除工人画像
   */
  deleteWorker: async (workerId: string) => {
    const response = await api.delete<{ message: string; worker_id: string }>(
      `${WORKERS_BASE_URL}/${workerId}`
    );
    return response.data;
  },

  /**
   * 获取工人统计数据
   */
  getWorkerStats: async (workerId: string) => {
    const response = await api.get<WorkerStats>(`${WORKERS_BASE_URL}/${workerId}/stats`);
    return response.data;
  },

  /**
   * 记录任务完成
   */
  recordTaskCompletion: async (
    workerId: string,
    taskId: string,
    reward: number,
    rating?: number,
    success: boolean = true
  ) => {
    const response = await api.post(
      `${WORKERS_BASE_URL}/${workerId}/task-complete`,
      { task_id: taskId, reward, rating, success }
    );
    return response.data;
  },

  /**
   * 从外部系统同步工人画像
   */
  syncExternalProfile: async (workerId: string, externalData: Record<string, unknown>) => {
    const response = await api.post(`${WORKERS_BASE_URL}/sync-external`, externalData, {
      params: { worker_id: workerId },
    });
    return response.data;
  },
};

export default workerService;
