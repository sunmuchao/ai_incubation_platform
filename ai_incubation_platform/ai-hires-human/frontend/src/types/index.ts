// 任务相关类型
export type TaskStatus = 'pending' | 'published' | 'open' | 'in_progress' | 'submitted' | 'review' | 'completed' | 'cancelled' | 'disputed';
export type TaskPriority = 'normal' | 'high' | 'urgent';
export type InteractionType = 'digital' | 'physical' | 'hybrid';

export interface Task {
  id: string;
  title: string;
  description: string;
  type: string;
  status: TaskStatus;
  priority: TaskPriority;
  interaction_type: InteractionType;
  reward: number;
  currency: string;
  ai_employer_id: string;
  worker_id?: string;
  skill_requirements?: string[];
  location_requirement?: string;
  deadline?: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  completed_at?: string;
  delivery_content?: string;
  delivery_attachments?: string[];
  callback_url?: string;
  capability_gap?: string;
  submission_count: number;
  reviewer_id?: string;
  appeal_reason?: string;
  evidence?: string[];
}

export interface TaskCreate {
  title: string;
  description: string;
  type: string;
  priority?: TaskPriority;
  interaction_type?: InteractionType;
  reward: number;
  currency?: string;
  skill_requirements?: string[];
  location_requirement?: string;
  deadline?: string;
  callback_url?: string;
  capability_gap: string;
}

export interface TaskFilter {
  status?: TaskStatus;
  priority?: TaskPriority;
  interaction_type?: InteractionType;
  keyword?: string;
  min_reward?: number;
  max_reward?: number;
  location?: string;
  sort_by?: 'created_at' | 'reward' | 'priority' | 'deadline';
  sort_order?: 'asc' | 'desc';
}

// 工人画像相关类型
export interface WorkerProfile {
  worker_id: string;
  name: string;
  avatar?: string;
  phone?: string;
  email?: string;
  location?: string;
  skills: string[];
  level: number;
  tags: string[];
  rating: number;
  completed_tasks: number;
  acceptance_rate: number;
  success_rate: number;
  total_earnings: number;
  external_profile_id?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkerStats {
  worker_id: string;
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  total_earnings: number;
  average_rating: number;
  success_rate: number;
  level: number;
  level_progress: number;
}

// 雇主相关类型
export interface EmployerProfile {
  employer_id: string;
  name: string;
  company?: string;
  email?: string;
  phone?: string;
  avatar?: string;
  total_tasks_posted: number;
  total_spent: number;
  average_rating: number;
  created_at: string;
}

// 支付相关类型
export type PaymentType = 'recharge' | 'payment' | 'refund' | 'settlement' | 'withdrawal';
export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface PaymentTransaction {
  id: string;
  user_id: string;
  type: PaymentType;
  amount: number;
  currency: string;
  status: PaymentStatus;
  task_id?: string;
  description?: string;
  created_at: string;
  completed_at?: string;
}

export interface Wallet {
  user_id: string;
  balance: number;
  currency: string;
  frozen_balance: number;
  total_recharged: number;
  total_spent: number;
  total_earned: number;
  total_withdrawn: number;
}

// Escrow 相关类型
export interface EscrowAccount {
  id: string;
  task_id: string;
  employer_id: string;
  worker_id: string;
  amount: number;
  currency: string;
  status: 'funded' | 'locked' | 'released' | 'refunded' | 'disputed';
  created_at: string;
  released_at?: string;
}

// 质量相关类型
export interface QualityMetrics {
  task_id: string;
  approval_rate: number;
  rejection_rate: number;
  average_rating: number;
  defect_rate: number;
  rework_rate: number;
}

export interface QualityPrediction {
  task_id: string;
  predicted_quality_score: number;
  risk_level: 'low' | 'medium' | 'high';
  risk_factors: string[];
  recommendations: string[];
}

// 声誉相关类型
export interface ReputationScore {
  user_id: string;
  overall_score: number;
  trust_score: number;
  quality_score: number;
  responsiveness_score: number;
  professionalism_score: number;
  level: 'bronze' | 'silver' | 'gold' | 'platinum' | 'diamond';
  badges: string[];
}

// 团队相关类型
export interface Team {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  members: TeamMember[];
  skills: string[];
  created_at: string;
}

export interface TeamMember {
  user_id: string;
  role: 'owner' | 'admin' | 'member';
  joined_at: string;
}

// 证书相关类型
export interface Certification {
  id: string;
  worker_id: string;
  certification_type: string;
  name: string;
  description?: string;
  issued_by: string;
  issued_at: string;
  expires_at?: string;
  status: 'active' | 'expired' | 'revoked';
  verification_url?: string;
}

// 争议相关类型
export interface Dispute {
  id: string;
  task_id: string;
  requester_id: string;
  reason: string;
  description: string;
  evidence: string[];
  status: 'pending' | 'under_review' | 'resolved' | 'escalated';
  resolution?: string;
  resolved_by?: string;
  resolved_at?: string;
  created_at: string;
}

// 通知相关类型
export interface Notification {
  id: string;
  user_id: string;
  type: 'task' | 'payment' | 'message' | 'system' | 'quality' | 'dispute';
  title: string;
  content: string;
  is_read: boolean;
  related_id?: string;
  created_at: string;
}

// 仪表板相关类型
export interface DashboardOverview {
  time_range: string;
  end_time: string;
  total_tasks: number;
  tasks_by_status: Record<string, number>;
  task_completion_rate: number;
  avg_completion_time_hours: number;
  active_workers: number;
  total_workers: number;
  avg_worker_rating: number;
  approval_rate: number;
  dispute_rate: number;
  total_gmv: number;
  platform_fees: number;
  pending_manual_review?: number;
}

export interface TrendDataPoint {
  date: string;
  value: number;
}

// 推荐相关类型
export interface TaskRecommendation {
  task_id: string;
  task: Task;
  match_score: number;
  match_reasons: string[];
}

export interface WorkerRecommendation {
  worker_id: string;
  worker: WorkerProfile;
  match_score: number;
  match_reasons: string[];
}

// 分页相关类型
export interface PaginationParams {
  page: number;
  page_size: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// 用户角色类型
export type UserRole = 'worker' | 'employer' | 'admin' | 'reviewer';

// 通用 API 响应类型
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
