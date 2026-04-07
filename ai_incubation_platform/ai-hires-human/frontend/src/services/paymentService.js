/**
 * 支付 API 服务
 */
import { api } from './api';
const PAYMENT_BASE_URL = '/api/payment';
const REAL_PAYMENT_BASE_URL = '/api/payment/real';
const ESCROW_BASE_URL = '/api/escrow';
export const paymentService = {
    // ========== 钱包支付 API ==========
    /**
     * 充值
     */
    recharge: async (userId, amount) => {
        const response = await api.post(`${PAYMENT_BASE_URL}/recharge`, { user_id: userId, amount });
        return response.data;
    },
    /**
     * 支付
     */
    pay: async (userId, amount, taskId) => {
        const response = await api.post(`${PAYMENT_BASE_URL}/pay`, { user_id: userId, amount, task_id: taskId });
        return response.data;
    },
    /**
     * 退款
     */
    refund: async (transactionId, reason) => {
        const response = await api.post(`${PAYMENT_BASE_URL}/refund`, { transaction_id: transactionId, reason });
        return response.data;
    },
    /**
     * 结算
     */
    settle: async (taskId, workerId, amount) => {
        const response = await api.post(`${PAYMENT_BASE_URL}/settle`, { task_id: taskId, worker_id: workerId, amount });
        return response.data;
    },
    /**
     * 提现
     */
    withdraw: async (userId, amount, bankAccount) => {
        const response = await api.post(`${PAYMENT_BASE_URL}/withdraw`, { user_id: userId, amount, bank_account: bankAccount });
        return response.data;
    },
    /**
     * 获取交易记录
     */
    getTransactions: async (userId, type, limit = 100) => {
        const params = new URLSearchParams();
        if (userId)
            params.append('user_id', userId);
        if (type)
            params.append('type', type);
        params.append('limit', String(limit));
        const response = await api.get(`${PAYMENT_BASE_URL}/transactions?${params}`);
        return response.data;
    },
    /**
     * 获取钱包余额
     */
    getWallet: async (userId) => {
        const response = await api.get(`${PAYMENT_BASE_URL}/wallet/${userId}`);
        return response.data;
    },
    // ========== 真实支付渠道 API ==========
    /**
     * 真实充值
     */
    realRecharge: async (userId, amount, channel) => {
        const response = await api.post(`${REAL_PAYMENT_BASE_URL}/recharge`, { user_id: userId, amount, channel });
        return response.data;
    },
    /**
     * 真实提现
     */
    realWithdraw: async (userId, amount, bankAccount) => {
        const response = await api.post(`${REAL_PAYMENT_BASE_URL}/withdraw`, {
            user_id: userId,
            amount,
            bank_account: bankAccount,
        });
        return response.data;
    },
    // ========== Escrow 资金托管 API ==========
    /**
     * 创建 Escrow 账户
     */
    createEscrow: async (taskId, employerId, workerId, amount) => {
        const response = await api.post(`${ESCROW_BASE_URL}`, {
            task_id: taskId,
            employer_id: employerId,
            worker_id: workerId,
            amount,
        });
        return response.data;
    },
    /**
     * 获取 Escrow 账户详情
     */
    getEscrow: async (escrowId) => {
        const response = await api.get(`${ESCROW_BASE_URL}/${escrowId}`);
        return response.data;
    },
    /**
     * 释放资金
     */
    releaseEscrow: async (escrowId, reviewerId) => {
        const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/release`, { reviewer_id: reviewerId });
        return response.data;
    },
    /**
     * 退款
     */
    refundEscrow: async (escrowId, reviewerId) => {
        const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/refund`, { reviewer_id: reviewerId });
        return response.data;
    },
    /**
     * 争议处理
     */
    disputeEscrow: async (escrowId, reason, evidence) => {
        const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/dispute`, { reason, evidence });
        return response.data;
    },
};
export default paymentService;
