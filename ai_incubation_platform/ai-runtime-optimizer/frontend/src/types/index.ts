/**
 * AI Native 类型定义
 */

// ============================================================================
// AI 对话相关类型
// ============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  attachments?: MessageAttachment[];
  actions?: ChatAction[];
  confidence?: number;
}

export interface MessageAttachment {
  type: 'chart' | 'table' | 'diagram' | 'metric' | 'alert';
  title: string;
  data: unknown;
}

export interface ChatAction {
  id: string;
  label: string;
  type: 'navigate' | 'execute' | 'confirm' | 'cancel';
  payload?: unknown;
}

// ============================================================================
// AI 诊断相关类型
// ============================================================================

export interface Diagnosis {
  id: string;
  root_cause: string;
  confidence: number;
  evidence_chain: EvidenceItem[];
  impact_assessment: ImpactAssessment;
  recommended_actions: RecommendedAction[];
  natural_language_report: string;
  timestamp: Date;
}

export interface EvidenceItem {
  id: string;
  type: 'metric' | 'log' | 'trace' | 'pattern';
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  data: Record<string, unknown>;
  timestamp: Date;
}

export interface ImpactAssessment {
  affected_services: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  estimated_impact: string;
  users_affected?: number;
  revenue_impact?: number;
}

export interface RecommendedAction {
  id: string;
  name: string;
  description: string;
  type: 'remediate' | 'optimize' | 'investigate';
  confidence: number;
  risk_level: 'low' | 'medium' | 'high';
  estimated_impact: string;
  auto_executable: boolean;
}

// ============================================================================
// 服务健康相关类型
// ============================================================================

export interface ServiceHealth {
  service_name: string;
  health_score: number;
  health_status: 'healthy' | 'warning' | 'critical' | 'unknown';
  last_seen: string | null;
  error_count: number;
  warning_count: number;
  issues: ServiceIssue[];
  recommendations: ServiceRecommendation[];
}

export interface ServiceIssue {
  id: string;
  type: string;
  severity: string;
  description: string;
  detected_at: string;
}

export interface ServiceRecommendation {
  id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  estimated_effort: string;
}

// ============================================================================
// 指标和监控类型
// ============================================================================

export interface MetricPoint {
  timestamp: string;
  value: number;
  labels?: Record<string, string>;
}

export interface MetricSeries {
  name: string;
  unit: string;
  data: MetricPoint[];
}

export interface DashboardMetrics {
  latency: MetricSeries;
  error_rate: MetricSeries;
  throughput: MetricSeries;
  cpu_usage: MetricSeries;
  memory_usage: MetricSeries;
}

// ============================================================================
// Agent 和工具类型
// ============================================================================

export interface AgentState {
  name: string;
  status: 'idle' | 'perceiving' | 'diagnosing' | 'remediating' | 'optimizing' | 'error';
  current_task?: string;
  progress?: number;
  last_activity: Date;
}

export interface AgentTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  tags: string[];
}

export interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: Date;
  completed_at?: Date;
  result?: unknown;
  error?: string;
}

export interface WorkflowExecution {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  steps: WorkflowStep[];
  started_at: Date;
  completed_at?: Date;
  result?: unknown;
}

// ============================================================================
// 告警类型
// ============================================================================

export interface Alert {
  id: string;
  service: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  detected_at: Date;
  acknowledged: boolean;
  acknowledged_at?: Date;
  acknowledged_by?: string;
}

// ============================================================================
// Generative UI 类型
// ============================================================================

export interface UIComponent {
  id: string;
  type: 'metric_card' | 'chart' | 'table' | 'alert_banner' | 'action_panel' | 'agent_status' | 'workflow_viewer';
  props: Record<string, unknown>;
  layout?: {
    span?: number;
    order?: number;
  };
}

export interface DashboardLayout {
  id: string;
  name: string;
  components: UIComponent[];
  generated_at: Date;
  context: {
    service?: string;
    focus?: string;
    status?: string;
  };
}

// ============================================================================
// API 响应类型
// ============================================================================

export interface AIAskResponse {
  answer: string;
  evidence: Record<string, unknown>[];
  actions: ChatAction[];
  confidence: number;
}

export interface AIDiagnoseResponse {
  diagnosis_id: string;
  root_cause: string;
  confidence: number;
  evidence_chain: EvidenceItem[];
  impact_assessment: ImpactAssessment;
  recommended_actions: RecommendedAction[];
  natural_language_report: string;
}

export interface AIDashboardResponse {
  status: string;
  health_score: number;
  active_alerts: Alert[];
  key_metrics: Record<string, unknown>;
  ai_insights: string[];
  suggested_actions: RecommendedAction[];
}

export interface AutonomousLoopResult {
  trace_id: string;
  timestamp: string;
  service?: string;
  signals: unknown[];
  diagnosis: unknown | null;
  remediation: unknown | null;
  optimization: unknown | null;
  error?: string;
}

// ============================================================================
// 保留旧类型用于兼容
// ============================================================================

export interface Service {
  id: string;
  name: string;
  type: string;
  health_status: string;
  metrics: Record<string, number>;
}

export interface Metric {
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  timestamp: string;
}

export interface LogEntry {
  trace_id: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  service_name: string;
  message: string;
  timestamp: string;
  attributes?: Record<string, unknown>;
}

export interface Bottleneck {
  id: string;
  service_name: string;
  bottleneck_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  impact: string;
  created_at: string;
}

export interface HealthScore {
  service_name: string;
  overall_score: number;
  status: 'healthy' | 'warning' | 'critical';
  dimensions: Array<{
    dimension: string;
    score: number;
    trend: 'improving' | 'stable' | 'degrading';
  }>;
  trend: string;
  risk_factors: string[];
  recommendations: string[];
}

export interface RootCause {
  hypothesis_id: string;
  candidate_service: string;
  root_cause_type: string;
  posterior_probability: number;
  confidence_score: number;
  evidence: Array<{ type: string; description: string }>;
}

export interface PredictiveAlert {
  alert_id: string;
  service_name: string;
  alert_type: string;
  predicted_event: string;
  predicted_time: string;
  hours_until_event: number;
  probability: number;
  severity: string;
  priority: string;
  title: string;
  description: string;
  recommended_actions: string[];
}

export interface ExecutionRecord {
  execution_id: string;
  script_id: string;
  service_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rolled_back';
  result: string;
  logs: string[];
  started_at: string;
  completed_at?: string;
}

export interface DashboardOverview {
  total_services: number;
  healthy_services: number;
  warning_services: number;
  critical_services: number;
  total_alerts: number;
  active_alerts: number;
  avg_health_score: number;
  total_bottlenecks: number;
  total_recommendations: number;
}
