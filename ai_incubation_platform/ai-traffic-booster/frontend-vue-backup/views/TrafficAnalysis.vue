<template>
  <div class="traffic-analysis">
    <!-- 日期筛选和快捷操作 -->
    <el-card class="filter-card">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="refreshData"
        style="width: 240px"
      />
      <el-radio-group v-model="timeGranularity" size="small" @change="refreshData">
        <el-radio-button label="hour">小时</el-radio-button>
        <el-radio-button label="day">天</el-radio-button>
        <el-radio-button label="week">周</el-radio-button>
        <el-radio-button label="month">月</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="refreshData" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
      <el-button @click="exportData">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
    </el-card>

    <!-- 流量趋势主图 -->
    <el-card class="trend-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">流量趋势分析</span>
          <el-checkbox-group v-model="displayMetrics" @change="updateChart">
            <el-checkbox label="visitors">访客数</el-checkbox>
            <el-checkbox label="page_views">页面浏览量</el-checkbox>
            <el-checkbox label="sessions">会话数</el-checkbox>
          </el-checkbox-group>
        </div>
      </template>
      <div ref="trendChartRef" class="chart"></div>
    </el-card>

    <!-- 流量来源分析 -->
    <el-row :gutter="16" class="row-card">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">流量来源分布</span>
          </template>
          <div ref="sourceChartRef" class="chart chart-medium"></div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">设备分布</span>
          </template>
          <div ref="deviceChartRef" class="chart chart-medium"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 地理分布 -->
    <el-card class="geo-card">
      <template #header>
        <span class="card-title">地理分布热力图</span>
      </template>
      <div ref="geoChartRef" class="chart"></div>
    </el-card>

    <!-- 页面排行 -->
    <el-card class="pages-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">页面排行</span>
          <el-radio-group v-model="pageRankType" size="small" @change="fetchPageRanking">
            <el-radio-button label="visitors">访客数</el-radio-button>
            <el-radio-button label="page_views">浏览量</el-radio-button>
            <el-radio-button label="bounce_rate">跳出率</el-radio-button>
            <el-radio-button label="duration">停留时长</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <el-table :data="pageRanking" stripe style="width: 100%">
        <el-table-column type="index" label="排名" width="60" />
        <el-table-column prop="path" label="页面路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="visitors" label="访客数" width="100" sortable />
        <el-table-column prop="page_views" label="浏览量" width="100" sortable />
        <el-table-column prop="bounce_rate" label="跳出率" width="100" sortable>
          <template #default="{ row }">
            {{ (row.bounce_rate * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="avg_duration" label="平均停留时长" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.avg_duration) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 异常检测 -->
    <el-card class="anomaly-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Warning /></el-icon>
            异常检测
          </span>
          <el-tag :type="anomalyCount > 0 ? 'danger' : 'success'">
            {{ anomalyCount }} 个异常点
          </el-tag>
        </div>
      </template>
      <el-timeline v-if="anomalies.length > 0">
        <el-timeline-item
          v-for="(anomaly, index) in anomalies"
          :key="index"
          :type="anomaly.anomaly_type === 'drop' ? 'danger' : 'success'"
          :timestamp="anomaly.date"
        >
          <el-card>
            <p><strong>{{ anomaly.anomaly_type === 'drop' ? '流量异常下跌' : '流量异常上涨' }}</strong></p>
            <p>幅度：{{ Math.abs(anomaly.deviation).toFixed(1) }}%</p>
            <p v-if="anomaly.root_cause">可能原因：{{ anomaly.root_cause }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="未发现异常" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { dashboardApi, realtimeApi } from '@/api'
import { useDashboardStore } from '@/store'

const dashboardStore = useDashboardStore()
const loading = ref(false)
const dateRange = ref<[Date, Date]>([
  dayjs().subtract(30, 'day').toDate(),
  dayjs().toDate()
])
const timeGranularity = ref('day')
const displayMetrics = ref(['visitors'])
const pageRankType = ref('visitors')

// 图表引用
const trendChartRef = ref<HTMLElement>()
const sourceChartRef = ref<HTMLElement>()
const deviceChartRef = ref<HTMLElement>()
const geoChartRef = ref<HTMLElement>()

// 数据
const pageRanking = ref<any[]>([])
const anomalies = ref<any[]>([])

// 图表实例
let trendChart: echarts.ECharts | null = null
let sourceChart: echarts.ECharts | null = null
let deviceChart: echarts.ECharts | null = null
let geoChart: echarts.ECharts | null = null

const anomalyCount = ref(0)

// 格式化时长
const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}分${secs}秒`
}

// 刷新数据
const refreshData = async () => {
  loading.value = true
  const startDate = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
  const endDate = dayjs(dateRange.value[1]).format('YYYY-MM-DD')

  await dashboardStore.fetchTrafficTrend(startDate, endDate)

  // 计算异常点
  anomalies.value = dashboardStore.trafficTrend
    .filter((item: any) => item.is_anomaly)
    .map((item: any) => ({
      date: item.date,
      anomaly_type: item.anomaly_type,
      deviation: ((item.visitors - item.expected) / item.expected) * 100,
      root_cause: item.root_cause
    }))
  anomalyCount.value = anomalies.value.length

  nextTick(() => {
    initCharts()
  })
  loading.value = false
}

// 获取页面排行
const fetchPageRanking = async () => {
  // TODO: 调用 API 获取页面排行数据
  pageRanking.value = [
    { path: '/products/seo-tools', visitors: 12580, page_views: 45200, bounce_rate: 0.35, avg_duration: 185 },
    { path: '/blog/seo-guide-2024', visitors: 9840, page_views: 28500, bounce_rate: 0.42, avg_duration: 245 },
    { path: '/pricing', visitors: 8520, page_views: 18900, bounce_rate: 0.28, avg_duration: 125 },
    { path: '/', visitors: 7200, page_views: 15600, bounce_rate: 0.45, avg_duration: 95 },
    { path: '/features', visitors: 5800, page_views: 12400, bounce_rate: 0.38, avg_duration: 165 },
  ]
}

// 导出
const exportData = async () => {
  // TODO: 实现导出功能
  console.log('Export data...')
}

// 初始化图表
const initCharts = () => {
  initTrendChart()
  initSourceChart()
  initDeviceChart()
  initGeoChart()
}

// 流量趋势图
const initTrendChart = () => {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const trend = dashboardStore.trafficTrend
  const dates = trend.map((item: any) => item.date)

  const series = []
  if (displayMetrics.value.includes('visitors')) {
    series.push({
      name: '访客数',
      type: 'line',
      smooth: true,
      data: trend.map((item: any) => item.visitors),
      itemStyle: { color: '#409EFF' }
    })
  }
  if (displayMetrics.value.includes('page_views')) {
    series.push({
      name: '页面浏览量',
      type: 'line',
      smooth: true,
      data: trend.map((item: any) => item.page_views),
      itemStyle: { color: '#67c23a' }
    })
  }
  if (displayMetrics.value.includes('sessions')) {
    series.push({
      name: '会话数',
      type: 'line',
      smooth: true,
      data: trend.map((item: any) => item.sessions),
      itemStyle: { color: '#e6a23c' }
    })
  }

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: displayMetrics.value.map(m => ({ name: m === 'visitors' ? '访客数' : m === 'page_views' ? '页面浏览量' : '会话数' })) },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: dates },
    yAxis: { type: 'value' },
    series
  }

  trendChart.setOption(option)
}

// 流量来源图
const initSourceChart = () => {
  if (!sourceChartRef.value) return
  if (!sourceChart) sourceChart = echarts.init(sourceChartRef.value)

  const option = {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [{
      name: '流量来源',
      type: 'pie',
      radius: ['40%', '70%'],
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
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

// 设备分布图
const initDeviceChart = () => {
  if (!deviceChartRef.value) return
  if (!deviceChart) deviceChart = echarts.init(deviceChartRef.value)

  const option = {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [{
      name: '设备类型',
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 65, name: '桌面端' },
        { value: 30, name: '移动端' },
        { value: 5, name: '平板' }
      ]
    }]
  }
  deviceChart.setOption(option)
}

// 地理分布图
const initGeoChart = () => {
  if (!geoChartRef.value) return
  if (!geoChart) geoChart = echarts.init(geoChartRef.value)

  // 简化的地理分布数据
  const geoData = [
    { name: '北京', value: 1200 },
    { name: '上海', value: 980 },
    { name: '广东', value: 850 },
    { name: '浙江', value: 720 },
    { name: '江苏', value: 650 },
  ]

  const option = {
    tooltip: { trigger: 'item' },
    visualMap: {
      min: 0,
      max: 1500,
      left: 'left',
      top: 'bottom',
      text: ['高', '低'],
      calculable: true,
      inRange: { color: ['#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] }
    },
    series: [{
      name: '访客数',
      type: 'map',
      mapType: 'china',
      data: geoData
    }]
  }
  geoChart.setOption(option)
}

// 更新图表
const updateChart = () => {
  initTrendChart()
}

onMounted(() => {
  refreshData()
  fetchPageRanking()
})
</script>

<style scoped lang="scss">
.traffic-analysis {
  .filter-card {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .trend-card {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chart {
      height: 350px;
    }
  }

  .row-card {
    margin-bottom: 16px;

    .chart-medium {
      height: 250px;
    }
  }

  .geo-card {
    margin-bottom: 16px;

    .chart {
      height: 400px;
    }
  }

  .pages-card {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .anomaly-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
