/**
 * 组件库导出 - Bento Grid 版本
 */

// ============================================
// Bento Grid 核心组件
// ============================================
export { BentoCard, type BentoCardProps, type BentoCardSize } from './bento/BentoCard';
export { BentoGrid, type BentoGridProps } from './bento/BentoGrid';
export { StatMetric, type StatMetricProps } from './bento/StatMetric';
export { TrendIndicator, type TrendIndicatorProps } from './bento/TrendIndicator';
export { MiniChart, type MiniChartProps } from './bento/MiniChart';

// ============================================
// 基础组件
// ============================================
export { Loading } from './Loading';
export { ErrorBoundary } from './ErrorBoundary';
export { CustomEmpty } from './CustomEmpty';
export { EmployeeCard } from './EmployeeCard';
export { StatCard } from './StatCard';
export { SearchBox } from './SearchBox';
export { ChartCard, createBarChartOption, createLineChartOption, createPieChartOption } from './ChartCard';

// ============================================
// AI Native 组件
// ============================================
export { default as ChatMessage } from './ChatMessage';
export { default as GenerativeUIRenderer } from './GenerativeUIRenderer';
export { default as AgentStatusPanel } from './AgentStatusPanel';
export { default as SuggestedActions } from './SuggestedActions';
export { default as OpportunityCards } from './OpportunityCards';
export { default as CareerTimeline } from './CareerTimeline';
export { default as SkillRadar } from './SkillRadar';
export { default as DashboardStats } from './DashboardStats';
export { default as AINotification } from './AINotification';
