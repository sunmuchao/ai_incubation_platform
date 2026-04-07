<template>
  <div class="dashboard">
    <!-- 日期选择器 -->
    <el-card class="date-filter-card">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="handleDateChange"
        style="width: 240px"
      />
      <el-button type="primary" @click="refreshData" :loading="loading">刷新数据</el-button>
      <el-button @click="exportReport">导出报告</el-button>
    </el-card>

    <!-- 核心指标卡片 -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :span="6">
        <el-card class="metric-card visitors">
          <div class="metric-header">
            <el-icon class="metric-icon"><User /></el-icon>
            <span class="metric-label">访客数</span>
          </div>
          <div class="metric-value">{{ formatNumber(dashboardStore.overview?.traffic?.current_visitors || 0) }}</div>
          <div class="metric-trend" :class="dashboardStore.overview?.traffic?.trend">
            <el-icon><Top /></el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.traffic?.change_percentage || 0) }}%</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card pageviews">
          <div class="metric-header">
            <el-icon class="metric-icon"><Document /></el-icon>
            <span class="metric-label">页面浏览量</span>
          </div>
          <div class="metric-value">{{ formatNumber(dashboardStore.overview?.traffic?.page_views || 0) }}</div>
          <div class="metric-trend" :class="dashboardStore.overview?.traffic?.trend">
            <el-icon><Top /></el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.traffic?.change_percentage || 0) }}%</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card seo">
          <div class="metric-header">
            <el-icon class="metric-icon"><Search /></el-icon>
            <span class="metric-label">平均排名</span>
          </div>
          <div class="metric-value">{{ dashboardStore.overview?.seo?.avg_position || '-' }}</div>
          <div class="metric-trend" :class="dashboardStore.overview?.seo?.position_change >= 0 ? 'up' : 'down'">
            <el-icon><Top v-if="dashboardStore.overview?.seo?.position_change >= 0" /><Bottom v-else /></el-icon>
            <span>{{ Math.abs(dashboardStore.overview?.seo?.position_change || 0) }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card alerts">
          <div class="metric-header">
            <el-icon class="metric-icon"><Bell /></el-icon>
            <span class="metric-label">活跃告警</span>
          </div>
          <div class="metric-value">{{ dashboardStore.overview?.alerts?.active_alerts || 0 }}</div>
          <div class="metric-trend warning">
            <el-icon><Warning /></el-icon>
            <span>{{ dashboardStore.overview?.alerts?.critical_count || 0 }} 严重</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI 洞察卡片 -->
    <el-row :gutter="16" class="insights-section">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><Lightbulb /></el-icon>
                AI 洞察
              </span>
              <el-tag type="info">{{ dashboardStore.insights.length }} 条洞察</el-tag>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col v-for="(insight, index) in dashboardStore.insights" :key="index" :span="8">
              <el-alert
                :title="insight.title"
                :description="insight.description"
                :type="getAlertType(insight.type)"
                :closable="false"
                show-icon
                class="insight-card"
              >
                <template #default>
                  <div class="insight-suggestion">
                    <strong>建议：</strong>{{ insight.suggestion }}
                  </div>
                  <div class="insight-meta">
                    <el-tag size="small" :type="getImpactTagType(insight.impact)">
                      影响：{{ insight.impact }}
                    </el-tag>
                    <span class="confidence">置信度：{{ (insight.confidence * 100).toFixed(0) }}%</span>
                  </div>
                </template>
              </el-alert>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 流量趋势图 -->
    <el-row :gutter="16" class="chart-section">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><TrendCharts /></el-icon>
                流量趋势
              </span>
              <el-badge :value="dashboardStore.anomalyCount" :hidden="dashboardStore.anomalyCount === 0"
                        type="warning">
                <span>异常点</span>
              </el-badge>
            </div>
          </template>
          <div ref="trafficChartRef" class="chart"></div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><PieChart /></el-icon>
                流量来源
              </span>
            </div>
          </template>
          <div ref="sourceChartRef" class="chart chart-small"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 关键词热力图和竞品雷达 -->
    <el-row :gutter="16" class="chart-section">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><Grid /></el-icon>
                关键词热力图
              </span>
            </div>
          </template>
          <div class="keyword-heatmap">
            <div v-for="kw in dashboardStore.keywordHeatmap.slice(0, 10)" :key="kw.keyword"
                 class="keyword-item"
                 :style="{ '--heat-color': getHeatColor(kw.heat) }">
              <div class="keyword-info">
                <span class="keyword-name">{{ kw.keyword }}</span>
                <span class="keyword-position">排名：{{ kw.position }}</span>
              </div>
              <div class="keyword-change" :class="kw.change >= 0 ? 'positive' : 'negative'">
                <el-icon v-if="kw.change >= 0"><Top /></el-icon>
                <el-icon v-else><Bottom /></el-icon>
                {{ Math.abs(kw.change) }}
              </div>
              <div class="heat-bar">
                <div class="heat-fill" :style="{ width: `${kw.heat * 100}%` }"></div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><Compare /></el-icon>
                竞品对比
              </span>
            </div>
          </template>
          <div ref="competitorChartRef" class="chart chart-small"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import dayjs from 'dayjs'
import { useDashboardStore } from '@/store'
import { dashboardApi } from '@/api'

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
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// 获取告警类型
const getAlertType = (type: string) => {
  const map: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
    opportunity: 'success',
    risk: 'warning',
    alert: 'error'
  }
  return map[type] || 'info'
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
  if (heat > 0.7) return '#67c23a'
  if (heat > 0.4) return '#e6a23c'
  return '#909399'
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
    // TODO: 处理文件下载
    console.log('Export result:', res)
  } catch (error) {
    console.error('Export failed:', error)
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
      formatter: (params: any) => {
        const date = params[0].name
        const visitor = params[0].value
        let html = `${date}<br/>访客：${formatNumber(visitor)}`
        if (params[0].data.is_anomaly) {
          html += `<br/><span style="color: ${params[0].data.anomaly_type === 'drop' ? '#f56c6c' : '#67c23a'}">
            ${params[0].data.anomaly_type === 'drop' ? '异常下跌' : '异常上涨'}
          </span>`
        }
        return html
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: '访客数'
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
            return params.data.anomaly_type === 'drop' ? '#f56c6c' : '#67c23a'
          }
          return '#409EFF'
        }
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.01)' }
        ])
      },
      markPoint: {
        data: anomalies.map((item: any) => ({
          coord: [dates[item[0]], item[1]],
          value: item[2] === 'drop' ? '↓' : '↑',
          itemStyle: { color: item[2] === 'drop' ? '#f56c6c' : '#67c23a' }
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
    legend: { bottom: '0%', left: 'center' },
    series: [{
      name: '流量来源',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false, position: 'center' },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' }
      },
      labelLine: { show: false },
      data: [
        { value: 1048, name: '自然搜索' },
        { value: 735, name: '直接访问' },
        { value: 580, name: '引荐' },
        { value: 484, name: '社交媒体' },
        { value: 300, name: '邮件营销' }
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
      indicator: dimensions.map((dim, i) => ({
        name: dim,
        max: 100
      })),
      radius: '65%'
    },
    series: [{
      name: '竞品对比',
      type: 'radar',
      data: competitors.map((c: any, index: number) => ({
        value: Object.values(c.metrics),
        name: c.domain
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
.dashboard {
  .date-filter-card {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .metric-cards {
    margin-bottom: 16px;

    .metric-card {
      position: relative;
      overflow: hidden;

      .metric-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #909399;
        font-size: 14px;

        .metric-icon {
          font-size: 18px;
        }
      }

      .metric-value {
        font-size: 28px;
        font-weight: 600;
        margin: 12px 0;
        color: #303133;
      }

      .metric-trend {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;

        &.up {
          color: #67c23a;
        }

        &.down {
          color: #f56c6c;
        }

        &.warning {
          color: #e6a23c;
        }
      }
    }
  }

  .insights-section {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
    }

    .insight-card {
      margin-bottom: 12px;

      .insight-suggestion {
        margin-top: 8px;
        font-size: 13px;
      }

      .insight-meta {
        margin-top: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .confidence {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }

  .chart-section {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
    }

    .chart {
      height: 300px;

      &.chart-small {
        height: 250px;
      }
    }
  }

  .keyword-heatmap {
    .keyword-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .keyword-info {
        width: 150px;
        display: flex;
        flex-direction: column;

        .keyword-name {
          font-size: 13px;
          font-weight: 500;
        }

        .keyword-position {
          font-size: 12px;
          color: #909399;
        }
      }

      .keyword-change {
        width: 60px;
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;

        &.positive {
          color: #67c23a;
        }

        &.negative {
          color: #f56c6c;
        }
      }

      .heat-bar {
        flex: 1;
        height: 6px;
        background: #f0f0f0;
        border-radius: 3px;
        overflow: hidden;

        .heat-fill {
          height: 100%;
          background: var(--heat-color, #409EFF);
          transition: width 0.3s;
        }
      }
    }
  }
}
</style>
