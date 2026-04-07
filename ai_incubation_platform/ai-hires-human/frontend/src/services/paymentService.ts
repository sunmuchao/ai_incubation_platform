/**
 * 支付 API 服务
 */
import { api } from './api';
import type { PaymentTransaction, Wallet, EscrowAccount } from '@/types';

const PAYMENT_BASE_URL = '/api/payment';
const REAL_PAYMENT_BASE_URL = '/api/payment/real';
const ESCROW_BASE_URL = '/api/escrow';

export const paymentService = {
  // ========== 钱包支付 API ==========
  /**
   * 充值
   */
  recharge: async (userId: string, amount: number) => {
    const response = await api.post(`${PAYMENT_BASE_URL}/recharge`, { user_id: userId, amount });
    return response.data;
  },

  /**
   * 支付
   */
  pay: async (userId: string, amount: number, taskId: string) => {
    const response = await api.post(`${PAYMENT_BASE_URL}/pay`, { user_id: userId, amount, task_id: taskId });
    return response.data;
  },

  /**
   * 退款
   */
  refund: async (transactionId: string, reason: string) => {
    const response = await api.post(`${PAYMENT_BASE_URL}/refund`, { transaction_id: transactionId, reason });
    return response.data;
  },

  /**
   * 结算
   */
  settle: async (taskId: string, workerId: string, amount: number) => {
    const response = await api.post(`${PAYMENT_BASE_URL}/settle`, { task_id: taskId, worker_id: workerId, amount });
    return response.data;
  },

  /**
   * 提现
   */
  withdraw: async (userId: string, amount: number, bankAccount?: string) => {
    const response = await api.post(`${PAYMENT_BASE_URL}/withdraw`, { user_id: userId, amount, bank_account: bankAccount });
    return response.data;
  },

  /**
   * 获取交易记录
   */
  getTransactions: async (userId?: string, type?: string, limit: number = 100) => {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (type) params.append('type', type);
    params.append('limit', String(limit));
    const response = await api.get<PaymentTransaction[]>(`${PAYMENT_BASE_URL}/transactions?${params}`);
    return response.data;
  },

  /**
   * 获取钱包余额
   */
  getWallet: async (userId: string) => {
    const response = await api.get<Wallet>(`${PAYMENT_BASE_URL}/wallet/${userId}`);
    return response.data;
  },

  // ========== 真实支付渠道 API ==========
  /**
   * 真实充值
   */
  realRecharge: async (userId: string, amount: number, channel: string) => {
    const response = await api.post(`${REAL_PAYMENT_BASE_URL}/recharge`, { user_id: userId, amount, channel });
    return response.data;
  },

  /**
   * 真实提现
   */
  realWithdraw: async (userId: string, amount: number, bankAccount: {
    bank_name: string;
    account_number: string;
    account_holder: string;
  }) => {
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
  createEscrow: async (taskId: string, employerId: string, workerId: string, amount: number) => {
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
  getEscrow: async (escrowId: string) => {
    const response = await api.get<EscrowAccount>(`${ESCROW_BASE_URL}/${escrowId}`);
    return response.data;
  },

  /**
   * 释放资金
   */
  releaseEscrow: async (escrowId: string, reviewerId: string) => {
    const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/release`, { reviewer_id: reviewerId });
    return response.data;
  },

  /**
   * 退款
   */
  refundEscrow: async (escrowId: string, reviewerId: string) => {
    const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/refund`, { reviewer_id: reviewerId });
    return response.data;
  },

  /**
   * 争议处理
   */
  disputeEscrow: async (escrowId: string, reason: string, evidence: string[]) => {
    const response = await api.post(`${ESCROW_BASE_URL}/${escrowId}/dispute`, { reason, evidence });
    return response.data;
  },
};

export default paymentService;
