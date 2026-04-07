/**
 * Chat API - AI 对话接口
 */
import { http } from '@/utils/http'

// ==================== 类型定义 ====================

export interface ChatMessageRequest {
  message: string
  session_id?: string
  user_id?: string
}

export interface ChatMessageResponse {
  message: string
  action_taken?: string
  confidence: number
  requires_approval: boolean
  data: any
  suggestions: string[]
  session_id: string
  timestamp: string
}

export interface Insight {
  id: string
  type: 'anomaly' | 'opportunity' | 'report'
  title: string
  content: string
  priority: 'low' | 'normal' | 'high' | 'critical'
  data: any
  timestamp: string
  actions: Array<{ action: string; label: string }>
}

export interface WorkflowResult {
  status: string
  result: any
  execution_id?: string
  message?: string
}

export interface AIStatus {
  status: string
  deerflow_available: boolean
  fallback_mode: boolean
  auto_execute_threshold: number
  request_approval_threshold: number
  active_sessions: number
  timestamp: string
}

// ==================== API 接口 ====================

export const chatApi = {
  /** 发送消息 */
  sendMessage: (data: ChatMessageRequest) =>
    http.post<ChatMessageResponse>('/chat/message', data),

  /** 获取 AI 状态 */
  getStatus: () => http.get<AIStatus>('/chat/status'),

  /** 运行诊断工作流 */
  runDiagnosisWorkflow: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/diagnosis', params || {}),

  /** 运行机会发现工作流 */
  runOpportunitiesWorkflow: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/opportunities', params || {}),

  /** 创建策略工作流 */
  runCreateStrategyWorkflow: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/strategy/create', params || {}),

  /** 获取会话历史 */
  getSessionHistory: (sessionId: string, limit = 50) =>
    http.get<any[]>(`/chat/sessions/${sessionId}/history`, { limit }),

  /** 删除会话 */
  deleteSession: (sessionId: string) =>
    http.delete(`/chat/sessions/${sessionId}`),
}

export const insightApi = {
  /** 获取洞察列表 */
  getInsights: (params?: { session_id?: string; limit?: number; insight_type?: string }) =>
    http.get<Insight[]>('/chat/insights', params),

  /** 批准洞察操作 */
  approveInsight: (insightId: string, action: string, sessionId?: string) =>
    http.post('/chat/insights/approve', { insight_id: insightId, action, session_id: sessionId }),

  /** 订阅推送 */
  subscribePush: (userId: string, insightTypes: string[] = ['anomaly', 'opportunity']) =>
    http.get('/chat/push/subscribe', { user_id: userId, insight_types: insightTypes }),
}

export const workflowApi = {
  /** 运行自动诊断 */
  runAutoDiagnosis: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/diagnosis', params || {}),

  /** 运行机会发现 */
  runOpportunityDiscovery: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/opportunities', params || {}),

  /** 创建策略 */
  createStrategy: (params?: any) =>
    http.post<WorkflowResult>('/chat/workflows/strategy/create', params || {}),
}
