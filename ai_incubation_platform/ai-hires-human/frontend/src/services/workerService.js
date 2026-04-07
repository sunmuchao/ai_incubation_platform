/**
 * 工人画像 API 服务
 */
import { api } from './api';
const WORKERS_BASE_URL = '/api/workers';
export const workerService = {
    /**
     * 获取工人列表
     */
    listWorkers: async (skip = 0, limit = 100) => {
        const response = await api.get(`${WORKERS_BASE_URL}?skip=${skip}&limit=${limit}`);
        return response.data;
    },
    /**
     * 搜索工人
     */
    searchWorkers: async (params) => {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== '') {
                queryParams.append(key, String(value));
            }
        });
        const response = await api.get(`${WORKERS_BASE_URL}/search?${queryParams}`);
        return response.data;
    },
    /**
     * 获取工人详情
     */
    getWorker: async (workerId) => {
        const response = await api.get(`${WORKERS_BASE_URL}/${workerId}`);
        return response.data;
    },
    /**
     * 创建或更新工人画像
     */
    createOrUpdateWorker: async (workerId, profileData) => {
        const response = await api.post(`${WORKERS_BASE_URL}/${workerId}`, profileData);
        return response.data;
    },
    /**
     * 部分更新工人画像
     */
    updateWorker: async (workerId, profileData) => {
        const response = await api.patch(`${WORKERS_BASE_URL}/${workerId}`, profileData);
        return response.data;
    },
    /**
     * 删除工人画像
     */
    deleteWorker: async (workerId) => {
        const response = await api.delete(`${WORKERS_BASE_URL}/${workerId}`);
        return response.data;
    },
    /**
     * 获取工人统计数据
     */
    getWorkerStats: async (workerId) => {
        const response = await api.get(`${WORKERS_BASE_URL}/${workerId}/stats`);
        return response.data;
    },
    /**
     * 记录任务完成
     */
    recordTaskCompletion: async (workerId, taskId, reward, rating, success = true) => {
        const response = await api.post(`${WORKERS_BASE_URL}/${workerId}/task-complete`, { task_id: taskId, reward, rating, success });
        return response.data;
    },
    /**
     * 从外部系统同步工人画像
     */
    syncExternalProfile: async (workerId, externalData) => {
        const response = await api.post(`${WORKERS_BASE_URL}/sync-external`, externalData, {
            params: { worker_id: workerId },
        });
        return response.data;
    },
};
export default workerService;
