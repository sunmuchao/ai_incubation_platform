// 类型定义
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

export interface Alert {
  id: string;
  service_name: string;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  created_at: string;
  acknowledged: boolean;
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

export interface Recommendation {
  id: string;
  service_name: string;
  category: 'performance' | 'resource' | 'cost' | 'reliability';
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  confidence_score: number;
  estimated_improvement: string;
  config_snippet?: string;
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
