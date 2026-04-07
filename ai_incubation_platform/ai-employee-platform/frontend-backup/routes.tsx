/**
 * 路由配置
 */
import React, { lazy, Suspense } from 'react';
import { Navigate } from 'react-router-dom';
import { Loading } from '@/components';
import BasicLayout from '@/layouts/BasicLayout';
import UserLayout from '@/layouts/UserLayout';

// 懒加载页面组件
const Login = lazy(() => import('@/pages/Login'));
const Register = lazy(() => import('@/pages/Register'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Marketplace = lazy(() => import('@/pages/Marketplace'));
const EmployeeDetail = lazy(() => import('@/pages/EmployeeDetail'));
const Performance = lazy(() => import('@/pages/Performance'));
const CareerDevelopment = lazy(() => import('@/pages/CareerDevelopment'));
const RemoteWork = lazy(() => import('@/pages/RemoteWork'));
const Culture = lazy(() => import('@/pages/Culture'));
const Wellness = lazy(() => import('@/pages/Wellness'));
const Assistant = lazy(() => import('@/pages/Assistant'));
const Settings = lazy(() => import('@/pages/Settings'));
const NotFound = lazy(() => import('@/pages/NotFound'));

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
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/login',
    element: <UserLayout>{LazyLoad(Login)}</UserLayout>,
  },
  {
    path: '/register',
    element: <UserLayout>{LazyLoad(Register)}</UserLayout>,
  },
  {
    path: '/',
    element: <BasicLayout>{LazyLoad(Dashboard)}</BasicLayout>,
    children: [
      {
        path: 'dashboard',
        element: LazyLoad(Dashboard),
      },
      {
        path: 'marketplace',
        element: LazyLoad(Marketplace),
      },
      {
        path: 'marketplace/:id',
        element: LazyLoad(EmployeeDetail),
      },
      {
        path: 'performance',
        element: LazyLoad(Performance),
      },
      {
        path: 'career',
        element: LazyLoad(CareerDevelopment),
      },
      {
        path: 'remote-work',
        element: LazyLoad(RemoteWork),
      },
      {
        path: 'culture',
        element: LazyLoad(Culture),
      },
      {
        path: 'wellness',
        element: LazyLoad(Wellness),
      },
      {
        path: 'assistant',
        element: LazyLoad(Assistant),
      },
      {
        path: 'settings',
        element: LazyLoad(Settings),
      },
    ],
  },
  {
    path: '*',
    element: LazyLoad(NotFound),
  },
];

export default routes;
