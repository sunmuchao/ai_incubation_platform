<template>
  <div class="dashboard-page">
    <!-- 顶部工具栏 -->
    <div class="dashboard-toolbar">
      <div class="toolbar-left">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="handleDateChange"
          size="default"
        />
      </div>
      <div class="toolbar-right">
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
      </div>
    </div>

    <!-- Bento Grid 布局 -->
    <div class="bento-grid">
      <!-- 核心指标卡片 - 第一行 -->
      <div class="bento-card bento-sm" style="animation-delay: 0ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon visitors-icon">
              <el-icon><User /></el-icon>
            </div>
            <span>访客数</span>
          </div>
          <el-tag size="small" type="success">实时</el-tag>
        </div>
        <div class="bento-card-body metric-body">
          <div class="metric-value">
            {{ formatNumber(dashboardStore.overview?.traffic?.current_visitors || 0) }}
          </div>
          <div class="metric-trend" :class="dashboardStore.overview?.traffic?.trend">
            <el-icon class="trend-icon"><Top /></el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.traffic?.change_percentage || 0) }}%</span>
            <span class="trend-label">较上期</span>
          </div>
        </div>
      </div>

      <div class="bento-card bento-sm" style="animation-delay: 50ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon pageviews-icon">
              <el-icon><Document /></el-icon>
            </div>
            <span>页面浏览量</span>
          </div>
        </div>
        <div class="bento-card-body metric-body">
          <div class="metric-value">
            {{ formatNumber(dashboardStore.overview?.traffic?.page_views || 0) }}
          </div>
          <div class="metric-trend" :class="dashboardStore.overview?.traffic?.trend">
            <el-icon class="trend-icon"><Top /></el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.traffic?.change_percentage || 0) }}%</span>
            <span class="trend-label">较上期</span>
          </div>
        </div>
      </div>

      <div class="bento-card bento-sm" style="animation-delay: 100ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon seo-icon">
              <el-icon><Search /></el-icon>
            </div>
            <span>平均排名</span>
          </div>
        </div>
        <div class="bento-card-body metric-body">
          <div class="metric-value">
            {{ dashboardStore.overview?.seo?.avg_position || '-' }}
          </div>
          <div class="metric-trend" :class="dashboardStore.overview?.seo?.position_change >= 0 ? 'up' : 'down'">
            <el-icon class="trend-icon">
              <Top v-if="dashboardStore.overview?.seo?.position_change >= 0" />
              <Bottom v-else />
            </el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.seo?.position_change || 0) }}</span>
            <span class="trend-label">名</span>
          </div>
        </div>
      </div>

      <div class="bento-card bento-sm" style="animation-delay: 150ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon alerts-icon">
              <el-icon><Bell /></el-icon>
            </div>
            <span>活跃告警</span>
          </div>
          <el-badge :value="dashboardStore.overview?.alerts?.critical_count || 0" type="danger" />
        </div>
        <div class="bento-card-body metric-body">
          <div class="metric-value">
            {{ dashboardStore.overview?.alerts?.active_alerts || 0 }}
          </div>
          <div class="metric-trend warning">
            <el-icon class="trend-icon"><Warning /></el-icon>
            <span>{{ dashboardStore.overview?.alerts?.critical_count || 0 }} 严重</span>
          </div>
        </div>
      </div>

      <!-- AI 洞察 - 横跨 3 列 -->
      <div class="bento-card bento-lg" style="grid-row: span 2; animation-delay: 200ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon insights-icon">
              <el-icon><Lightbulb /></el-icon>
            </div>
            <span>AI 智能洞察</span>
          </div>
          <el-tag size="small" type="info">{{ dashboardStore.insights.length }} 条</el-tag>
        </div>
        <div class="bento-card-body insights-body">
          <div v-for="(insight, index) in dashboardStore.insights" :key="index" class="insight-item">
            <div class="insight-dot" :class="insight.type"></div>
            <div class="insight-content">
              <div class="insight-title">{{ insight.title }}</div>
              <div class="insight-desc">{{ insight.description }}</div>
              <div class="insight-footer">
                <el-tag size="small" :type="getImpactTagType(insight.impact)">
                  {{ insight.impact }}影响
                </el-tag>
                <span class="confidence">置信度 {{ (insight.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          <div v-if="dashboardStore.insights.length === 0" class="empty-state">
            <el-icon :size="48" color="#cbd5e1"><Lightbulb /></el-icon>
            <p>暂无 AI 洞察</p>
          </div>
        </div>
      </div>

      <!-- 流量趋势图 - 2x2 -->
      <div class="bento-card bento-lg" style="animation-delay: 250ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon trend-icon">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <span>流量趋势</span>
          </div>
          <el-badge :value="dashboardStore.anomalyCount" :hidden="dashboardStore.anomalyCount === 0" type="warning" />
        </div>
        <div class="bento-card-body chart-body">
          <div ref="trafficChartRef" class="chart"></div>
        </div>
      </div>

      <!-- 流量来源饼图 -->
      <div class="bento-card bento-sm" style="animation-delay: 300ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon source-icon">
              <el-icon><PieChart /></el-icon>
            </div>
            <span>流量来源</span>
          </div>
        </div>
        <div class="bento-card-body chart-body">
          <div ref="sourceChartRef" class="chart chart-small"></div>
        </div>
      </div>

      <!-- 关键词热力图 -->
      <div class="bento-card bento-md" style="animation-delay: 350ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon keyword-icon">
              <el-icon><Grid /></el-icon>
            </div>
            <span>关键词热力图</span>
          </div>
        </div>
        <div class="bento-card-body keyword-body">
          <div v-for="kw in dashboardStore.keywordHeatmap.slice(0, 8)" :key="kw.keyword" class="keyword-item">
            <div class="keyword-info">
              <span class="keyword-name">{{ kw.keyword }}</span>
              <span class="keyword-position">#{{ kw.position }}</span>
            </div>
            <div class="keyword-change" :class="kw.change >= 0 ? 'positive' : 'negative'">
              <el-icon v-if="kw.change >= 0"><Top /></el-icon>
              <el-icon v-else><Bottom /></el-icon>
              {{ Math.abs(kw.change) }}
            </div>
            <div class="heat-bar">
              <div class="heat-fill" :style="{ width: `${kw.heat * 100}%`, background: getHeatColor(kw.heat) }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 竞品雷达图 -->
      <div class="bento-card bento-sm" style="animation-delay: 400ms">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon competitor-icon">
              <el-icon><Compare /></el-icon>
            </div>
            <span>竞品分析</span>
          </div>
        </div>
        <div class="bento-card-body chart-body">
          <div ref="competitorChartRef" class="chart chart-small"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import dayjs from 'dayjs'
import { useDashboardStore } from '@/store'
import { dashboardApi } from '@/api'
import { ElMessage } from 'element-plus'

const dashboardStore = useDashboardStore()
const loading = ref(false)
const dateRange = ref<[Date, Date]>([
  dayjs().subtract(30, 'day').toDate(),
  dayjs().toDate()
])

// 图表引用
const trafficChartRef = ref<HTMLElement>()
const sourceChartRef = ref<HTMLElement>()
const competitorChartRef = ref<HTMLElement>()

// 图表实例
let trafficChart: ECharts | null = null
let sourceChart: ECharts | null = null
let competitorChart: ECharts | null = null

// 格式化数字
const formatNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

// 获取影响程度标签类型
const getImpactTagType = (impact: string) => {
  const map: Record<string, 'success' | 'warning' | 'danger'> = {
    '高': 'danger',
    '中': 'warning',
    '低': 'success'
  }
  return map[impact] || 'info'
}

// 获取热力颜色
const getHeatColor = (heat: number) => {
  if (heat > 0.7) return '#22c55e'
  if (heat > 0.4) return '#f59e0b'
  return '#64748b'
}

// 处理日期变化
const handleDateChange = () => {
  refreshData()
}

// 刷新数据
const refreshData = async () => {
  loading.value = true
  const startDate = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
  const endDate = dayjs(dateRange.value[1]).format('YYYY-MM-DD')

  await Promise.all([
    dashboardStore.fetchOverview(),
    dashboardStore.fetchInsights(startDate, endDate),
    dashboardStore.fetchTrafficTrend(startDate, endDate),
    dashboardStore.fetchKeywordHeatmap(startDate, endDate),
    dashboardStore.fetchCompetitorRadar(['example.com', 'competitor1.com', 'competitor2.com'])
  ])

  nextTick(() => {
    initCharts()
  })
  loading.value = false
}

// 导出报告
const exportReport = async () => {
  const startDate = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
  const endDate = dayjs(dateRange.value[1]).format('YYYY-MM-DD')

  try {
    const res = await dashboardApi.exportData({
      export_type: 'dashboard',
      format: 'pdf',
      start_date: startDate,
      end_date: endDate,
      include_charts: true,
      include_insights: true
    })
    ElMessage.success('报告导出成功')
    console.log('Export result:', res)
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败，请稍后重试')
  }
}

// 初始化图表
const initCharts = () => {
  initTrafficChart()
  initSourceChart()
  initCompetitorChart()
}

// 流量趋势图
const initTrafficChart = () => {
  if (!trafficChartRef.value) return

  if (!trafficChart) {
    trafficChart = echarts.init(trafficChartRef.value)
  }

  const trend = dashboardStore.trafficTrend
  const dates = trend.map((item: any) => item.date)
  const visitors = trend.map((item: any) => item.visitors)
  const anomalies = trend.map((item: any, index: number) => {
    if (item.is_anomaly) {
      return [index, item.visitors, item.anomaly_type]
    }
    return null
  }).filter((item: any) => item !== null)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#334155',
      textStyle: { color: '#f1f5f9' }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      name: '访客数',
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series: [{
      name: '访客数',
      type: 'line',
      smooth: true,
      data: trend.map((item: any) => ({
        value: item.visitors,
        is_anomaly: item.is_anomaly,
        anomaly_type: item.anomaly_type
      })),
      itemStyle: {
        color: (params: any) => {
          if (params.data.is_anomaly) {
            return params.data.anomaly_type === 'drop' ? '#ef4444' : '#22c55e'
          }
          return '#6366f1'
        }
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
          { offset: 1, color: 'rgba(99, 102, 241, 0.02)' }
        ])
      },
      markPoint: {
        data: anomalies.map((item: any) => ({
          coord: [dates[item[0]], item[1]],
          value: item[2] === 'drop' ? '↓' : '↑',
          itemStyle: { color: item[2] === 'drop' ? '#ef4444' : '#22c55e' }
        }))
      }
    }]
  }

  trafficChart.setOption(option)

  window.addEventListener('resize', () => {
    trafficChart?.resize()
  })
}

// 流量来源图
const initSourceChart = () => {
  if (!sourceChartRef.value) return

  if (!sourceChart) {
    sourceChart = echarts.init(sourceChartRef.value)
  }

  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%', left: 'center', textStyle: { color: '#64748b' } },
    series: [{
      name: '流量来源',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false, position: 'center' },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: '600', color: '#0f172a' }
      },
      labelLine: { show: false },
      data: [
        { value: 1048, name: '自然搜索', itemStyle: { color: '#6366f1' } },
        { value: 735, name: '直接访问', itemStyle: { color: '#818cf8' } },
        { value: 580, name: '引荐', itemStyle: { color: '#a5b4fc' } },
        { value: 484, name: '社交媒体', itemStyle: { color: '#22c55e' } },
        { value: 300, name: '邮件营销', itemStyle: { color: '#10b981' } }
      ]
    }]
  }

  sourceChart.setOption(option)
}

// 竞品雷达图
const initCompetitorChart = () => {
  if (!competitorChartRef.value) return

  if (!competitorChart) {
    competitorChart = echarts.init(competitorChartRef.value)
  }

  const competitors = dashboardStore.competitorRadar
  if (competitors.length === 0) return

  const dimensions = ['流量规模', '域名权威', '内容质量', '外链数量', '关键词覆盖', '社交媒体']

  const option = {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: dimensions.map((dim) => ({
        name: dim,
        max: 100
      })),
      radius: '60%',
      axisName: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: '#e2e8f0' } }
    },
    series: [{
      name: '竞品对比',
      type: 'radar',
      lineStyle: { width: 2 },
      data: competitors.map((c: any, index: number) => ({
        value: Object.values(c.metrics),
        name: c.domain,
        itemStyle: { color: index === 0 ? '#6366f1' : '#f59e0b' },
        areaStyle: { opacity: 0.2 }
      }))
    }]
  }

  competitorChart.setOption(option)
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';
@import '@/styles/bento.scss';

.dashboard-page {
  padding: $spacing-6;
  max-width: 1600px;
  margin: 0 auto;
}

.dashboard-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;
  padding: $spacing-4 $spacing-5;
  background: #fff;
  border-radius: $radius-lg;
  border: $border-subtle;
  box-shadow: $shadow-sm;

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: $spacing-3;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-2;

    .el-button {
      display: flex;
      align-items: center;
      gap: $spacing-1;
    }
  }
}

.bento-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: minmax(140px, auto);
  gap: $spacing-4;

  @media (max-width: 1280px) {
    grid-template-columns: repeat(6, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
  }
}

.bento-card {
  background: #fff;
  border-radius: $radius-lg;
  border: $border-subtle;
  box-shadow: $shadow-sm;
  padding: $spacing-5;
  transition: all $transition-base $ease-out;
  overflow: hidden;
  animation: card-entrance $transition-slow $ease-out forwards;
  opacity: 0;

  @keyframes card-entrance {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  &:hover {
    box-shadow: $shadow-md;
    border-color: $border-medium;
    transform: translateY(-2px);
  }

  // Bento 尺寸
  &.bento-sm {
    grid-column: span 3;

    @media (max-width: 1280px) {
      grid-column: span 3;
    }

    @media (max-width: 768px) {
      grid-column: span 1;
    }
  }

  &.bento-md {
    grid-column: span 6;

    @media (max-width: 768px) {
      grid-column: span 1;
    }
  }

  &.bento-lg {
    grid-column: span 6;
    grid-row: span 2;

    @media (max-width: 1280px) {
      grid-column: span 3;
    }

    @media (max-width: 768px) {
      grid-column: span 1;
      grid-row: auto;
    }
  }
}

.bento-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-4;
  padding-bottom: $spacing-3;
  border-bottom: $border-subtle;

  .card-title {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: $text-secondary;
  }
}

.bento-card-body {
  flex: 1;
  min-height: 0;
}

// 标题图标
.title-icon {
  width: 28px;
  height: 28px;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;

  &.visitors-icon { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
  &.pageviews-icon { background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%); }
  &.seo-icon { background: linear-gradient(135deg, #22c55e 0%, #10b981 100%); }
  &.alerts-icon { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
  &.insights-icon { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
  &.trend-icon { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
  &.source-icon { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
  &.keyword-icon { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
  &.competitor-icon { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); }
}

// 指标卡片样式
.metric-body {
  .metric-value {
    font-size: 32px;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin: $spacing-3 0;
    letter-spacing: -0.02em;
  }

  .metric-trend {
    display: flex;
    align-items: center;
    gap: $spacing-1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;

    .trend-icon {
      font-size: 14px;
    }

    .trend-label {
      color: $text-tertiary;
      font-weight: $font-weight-normal;
    }

    &.up {
      color: $success;
    }

    &.down {
      color: $error;
    }

    &.warning {
      color: $warning;
    }
  }
}

// AI 洞察样式
.insights-body {
  display: flex;
  flex-direction: column;
  gap: $spacing-4;
  overflow-y: auto;
  max-height: 500px;

  .insight-item {
    display: flex;
    gap: $spacing-3;
    padding: $spacing-3;
    background: $bg-secondary;
    border-radius: $radius-md;
    transition: all $transition-base $ease-out;

    &:hover {
      background: $slate-100;
    }

    .insight-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 4px;

      &.opportunity { background: $success; }
      &.risk { background: $warning; }
      &.alert { background: $error; }
    }

    .insight-content {
      flex: 1;
      min-width: 0;

      .insight-title {
        font-size: $font-size-sm;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        margin-bottom: 4px;
      }

      .insight-desc {
        font-size: $font-size-xs;
        color: $text-secondary;
        line-height: 1.5;
        margin-bottom: $spacing-2;
      }

      .insight-footer {
        display: flex;
        align-items: center;
        gap: $spacing-2;

        .confidence {
          font-size: $font-size-xs;
          color: $text-tertiary;
        }
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: $spacing-3;
    padding: $spacing-10;
    color: $text-tertiary;

    p {
      margin: 0;
      font-size: $font-size-sm;
    }
  }
}

// 图表样式
.chart-body {
  height: 280px;

  .chart {
    width: 100%;
    height: 100%;

    &.chart-small {
      height: 180px;
    }
  }
}

// 关键词热力图
.keyword-body {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;

  .keyword-item {
    display: flex;
    align-items: center;
    gap: $spacing-3;

    .keyword-info {
      width: 140px;
      display: flex;
      flex-direction: column;
      gap: 2px;

      .keyword-name {
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }

      .keyword-position {
        font-size: $font-size-xs;
        color: $text-tertiary;
      }
    }

    .keyword-change {
      width: 50px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 2px;
      font-size: $font-size-xs;
      font-weight: $font-weight-medium;

      &.positive { color: $success; }
      &.negative { color: $error; }
    }

    .heat-bar {
      flex: 1;
      height: 6px;
      background: $slate-100;
      border-radius: $radius-full;
      overflow: hidden;

      .heat-fill {
        height: 100%;
        border-radius: $radius-full;
        transition: width $transition-slow $ease-out;
      }
    }
  }
}
</style>
