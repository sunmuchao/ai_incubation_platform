/**
 * 路由配置 - AI Native 版本
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'AIChatHome',
        component: () => import('@/views/AIChatHome.vue'),
        meta: { title: 'AI 对话', icon: 'ChatDotRound' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表板', icon: 'DataAnalysis' },
      },
      {
        path: 'traffic',
        name: 'TrafficAnalysis',
        component: () => import('@/views/TrafficAnalysis.vue'),
        meta: { title: '流量分析', icon: 'TrendCharts' },
      },
      {
        path: 'seo',
        name: 'SEOAnalysis',
        component: () => import('@/views/SEOAnalysis.vue'),
        meta: { title: 'SEO 分析', icon: 'Search' },
      },
      {
        path: 'competitor',
        name: 'CompetitorAnalysis',
        component: () => import('@/views/CompetitorAnalysis.vue'),
        meta: { title: '竞品分析', icon: 'Compare' },
      },
      {
        path: 'agents',
        name: 'Agents',
        component: () => import('@/views/AgentsOverview.vue'),
        meta: { title: 'Agent 中心', icon: 'Grid' },
      },
      {
        path: 'automation',
        name: 'Automation',
        component: () => import('@/views/Automation.vue'),
        meta: { title: '自动化中心', icon: 'Finished' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/Alerts.vue'),
        meta: { title: '告警管理', icon: 'Warning' },
      },
      {
        path: 'data-sources',
        name: 'DataSources',
        component: () => import('@/views/DataSources.vue'),
        meta: { title: '数据源管理', icon: 'Database' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '报告中心', icon: 'Document' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'AI Traffic Booster'} - AI Native 增长顾问`
  next()
})

export default router
