/**
 * AI Native 路由配置
 *
 * 重构为对话式界面:
 * - 主页面：Chat 对话界面
 * - Generative UI 页面：动态生成的界面
 * - Agent 状态页面：显示 AI 工作状态
 * - AI Native 演示页面：综合展示所有 AI Native 特性
 */
import React, { lazy, Suspense } from 'react';
import { Navigate } from 'react-router-dom';
import { Loading } from '@/components';

// 懒加载页面组件
const ChatInterface = lazy(() => import('@/pages/ChatInterface'));
const GenerativeUI = lazy(() => import('@/pages/GenerativeUI'));
const AgentStatus = lazy(() => import('@/pages/AgentStatus'));
const OpportunityMatch = lazy(() => import('@/pages/OpportunityMatch'));
const CareerPlan = lazy(() => import('@/pages/CareerPlan'));
const PerformanceReview = lazy(() => import('@/pages/PerformanceReview'));
const Login = lazy(() => import('@/pages/Login'));
const NotFound = lazy(() => import('@/pages/NotFound'));
const AINativeDemo = lazy(() => import('@/pages/AINativeDemo'));

// 路由懒加载包装器
const LazyLoad = (Component: React.LazyExoticComponent<React.FC>) => (
  <Suspense fallback={<Loading fullScreen />}>
    <Component />
  </Suspense>
);

// 路由定义
const routes = [
  {
    path: '/',
    element: <Navigate to="/chat" replace />,
  },
  {
    path: '/login',
    element: LazyLoad(Login),
  },
  {
    path: '/chat',
    element: LazyLoad(ChatInterface),
  },
  {
    path: '/generative-ui',
    element: LazyLoad(GenerativeUI),
  },
  {
    path: '/agent-status',
    element: LazyLoad(AgentStatus),
  },
  {
    path: '/opportunities',
    element: LazyLoad(OpportunityMatch),
  },
  {
    path: '/career-plan',
    element: LazyLoad(CareerPlan),
  },
  {
    path: '/performance-review',
    element: LazyLoad(PerformanceReview),
  },
  {
    path: '/ai-native-demo',
    element: LazyLoad(AINativeDemo),
  },
  {
    path: '*',
    element: LazyLoad(NotFound),
  },
];

export default routes;
