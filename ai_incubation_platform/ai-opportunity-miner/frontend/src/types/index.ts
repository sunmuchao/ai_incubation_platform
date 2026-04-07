/**
 * AI Opportunity Miner - 类型定义
 */

// 商机类型
export type OpportunityType = 'market' | 'product' | 'partnership' | 'investment';

// 商机状态
export type OpportunityStatus = 'new' | 'validated' | 'expired';

// 风险标签
export type RiskLabel = 'low_risk' | 'medium_risk' | 'high_risk' | 'regulatory' | 'competitive' | 'technological' | 'market';

// 数据来源类型
export type SourceType = 'news' | 'social_media' | 'patent' | 'recruitment' | 'industry_report' | 'government_data' | 'internal_data' | 'ai_analysis';

// 商机数据模型
export interface BusinessOpportunity {
  id: string;
  title: string;
  description: string;
  type: OpportunityType;
  confidence_score: number;  // AI 置信度 0-1
  potential_value: number;   // 潜在价值
  potential_value_currency: string;
  source_type: SourceType;
  source_name: string;
  source_url: string;
  source_publish_date?: string;
  risk_labels: RiskLabel[];
  risk_score: number;
  risk_description: string;
  validation_steps: string[];
  validation_status: string;
  validation_notes: string;
  related_entities: Array<{ [key: string]: string }>;
  tags: string[];
  status: OpportunityStatus;
  created_at: string;
  updated_at: string;
}

// 市场趋势模型
export interface MarketTrend {
  id: string;
  keyword: string;
  trend_score: number;
  growth_rate: number;
  related_keywords: string[];
  data_points: Array<{ [key: string]: any }>;
  extra: { [key: string]: any };
  created_at: string;
}

// 对话消息
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  data?: ChatData;
  suggestions?: string[];
}

// 对话数据
export interface ChatData {
  opportunities?: BusinessOpportunity[];
  trends?: MarketTrend[];
  intent?: string;
  [key: string]: any;
}

// Agent 状态
export interface AgentStatus {
  deerflow_available: boolean;
  tools_registered: number;
  audit_logs_count: number;
  tools_schema: ToolSchema[];
  push_callbacks_registered: number;
}

// 工具 Schema
export interface ToolSchema {
  name: string;
  description: string;
  input_schema: { [key: string]: any };
}

// Agent 工作流步骤
export interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  description: string;
  startTime?: string;
  endTime?: string;
  result?: { [key: string]: any };
}

// 主动推送警报
export interface Alert {
  alert_id: string;
  alert_type: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  opportunity: BusinessOpportunity;
  timestamp: string;
  message: string;
}

// 仪表板概览
export interface DashboardOverview {
  summary: {
    total_opportunities: number;
    new_this_week: number;
    validated_opportunities: number;
    high_confidence_count: number;
    total_trends_tracked: number;
    active_alerts: number;
  };
  data_sources: {
    [key: string]: {
      count: number;
      status: string;
    };
  };
  trend_chart: {
    labels: string[];
    datasets: {
      opportunities_discovered: number[];
      news_analyzed: number[];
      social_mentions: number[];
    };
  };
}
