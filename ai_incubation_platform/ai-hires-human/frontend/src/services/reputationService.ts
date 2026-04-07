/**
 * 声誉 API 服务
 */
import { api } from './api';
import type { ReputationScore } from '@/types';

const REPUTATION_BASE_URL = '/api/reputation';

export const reputationService = {
  /**
   * 获取用户声誉评分
   */
  getReputation: async (userId: string) => {
    const response = await api.get<ReputationScore>(`${REPUTATION_BASE_URL}/${userId}`);
    return response.data;
  },

  /**
   * 更新用户声誉评分
   */
  updateReputation: async (userId: string, scores: {
    trust_score?: number;
    quality_score?: number;
    responsiveness_score?: number;
    professionalism_score?: number;
  }) => {
    const response = await api.put<ReputationScore>(`${REPUTATION_BASE_URL}/${userId}`, scores);
    return response.data;
  },

  /**
   * 添加徽章
   */
  addBadge: async (userId: string, badge: string) => {
    const response = await api.post(`${REPUTATION_BASE_URL}/${userId}/badges`, { badge });
    return response.data;
  },

  /**
   * 移除徽章
   */
  removeBadge: async (userId: string, badge: string) => {
    const response = await api.delete(`${REPUTATION_BASE_URL}/${userId}/badges/${badge}`);
    return response.data;
  },
};

export default reputationService;
