/**
 * 任务 API 服务
 */
import { api } from './api';
const TASKS_BASE_URL = '/api/tasks';
export const taskService = {
    /**
     * 搜索任务 - 真人侧浏览可接任务
     */
    searchTasks: async (params) => {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== '') {
                queryParams.append(key, String(value));
            }
        });
        const response = await api.get(`${TASKS_BASE_URL}/search?${queryParams}`);
        return response.data;
    },
    /**
     * 获取任务列表 - 雇主侧查询
     */
    listTasks: async (params) => {
        const queryParams = new URLSearchParams();
        if (params?.status)
            queryParams.append('status', params.status);
        if (params?.interaction_type)
            queryParams.append('interaction_type', params.interaction_type);
        const response = await api.get(`${TASKS_BASE_URL}?${queryParams}`);
        return response.data;
    },
    /**
     * 创建任务
     */
    createTask: async (taskData) => {
        const response = await api.post(TASKS_BASE_URL, taskData);
        return response.data;
    },
    /**
     * 获取任务详情
     */
    getTask: async (taskId) => {
        const response = await api.get(`${TASKS_BASE_URL}/${taskId}`);
        return response.data;
    },
    /**
     * 发布任务
     */
    publishTask: async (taskId) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/publish`);
        return response.data;
    },
    /**
     * 接受任务 - 真人接单
     */
    acceptTask: async (taskId, workerId) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/accept`, { worker_id: workerId });
        return response.data;
    },
    /**
     * 提交工作 - 提交交付物
     */
    submitWork: async (taskId, workerId, content, attachments) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/submit`, {
            worker_id: workerId,
            content,
            attachments,
        });
        return response.data;
    },
    /**
     * 完成任务 - AI 雇主验收
     */
    completeTask: async (taskId, aiEmployerId, approved) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/complete`, {
            ai_employer_id: aiEmployerId,
            approved,
        });
        return response.data;
    },
    /**
     * 取消任务
     */
    cancelTask: async (taskId, operatorId, reason) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/cancel`, {
            operator_id: operatorId,
            reason,
        });
        return response.data;
    },
    /**
     * 开始人工复核
     */
    startManualReview: async (taskId, reviewerId) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/manual-review/start`, null, {
            params: { reviewer_id: reviewerId },
        });
        return response.data;
    },
    /**
     * 人工复核任务
     */
    manualReview: async (taskId, reviewerId, approved, reason, overrideAiDecision) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/manual-review`, {
            reviewer_id: reviewerId,
            approved,
            reason,
            override_ai_decision: overrideAiDecision,
        });
        return response.data;
    },
    /**
     * 申诉任务
     */
    appealTask: async (taskId, appealerId, appealReason, evidence) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/appeal`, {
            appealer_id: appealerId,
            appeal_reason: appealReason,
            evidence,
        });
        return response.data;
    },
    /**
     * 解决争议
     */
    resolveDispute: async (taskId, reviewerId, approved, reason) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/resolve-dispute`, null, {
            params: { reviewer_id: reviewerId, approved, reason },
        });
        return response.data;
    },
    /**
     * 获取工人风险评分
     */
    getWorkerRiskScore: async (workerId) => {
        const response = await api.get(`${TASKS_BASE_URL}/workers/${workerId}/risk-score`);
        return response.data;
    },
    /**
     * 标记任务作弊
     */
    markTaskCheating: async (taskId, reviewerId, reason) => {
        const response = await api.post(`${TASKS_BASE_URL}/${taskId}/mark-cheating`, null, {
            params: { reviewer_id: reviewerId, reason },
        });
        return response.data;
    },
};
export default taskService;
