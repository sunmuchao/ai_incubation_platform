<template>
  <div class="seo-analysis">
    <!-- 概览指标 -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><Rank /></el-icon>
            <span>平均排名</span>
          </div>
          <div class="metric-value">{{ seoMetrics.avg_position }}</div>
          <div class="metric-trend positive">
            <el-icon><Top /></el-icon>
            {{ seoMetrics.position_change }} 位
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><Document /></el-icon>
            <span>收录页数</span>
          </div>
          <div class="metric-value">{{ formatNumber(seoMetrics.indexed_pages) }}</div>
          <div class="metric-trend positive">
            <el-icon><Top /></el-icon>
            {{ seoMetrics.indexed_change }}%
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><Link /></el-icon>
            <span>外链数量</span>
          </div>
          <div class="metric-value">{{ formatNumber(seoMetrics.backlinks) }}</div>
          <div class="metric-trend positive">
            <el-icon><Top /></el-icon>
            {{ seoMetrics.backlinks_change }}%
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><CircleCheck /></el-icon>
            <span>SEO 健康度</span>
          </div>
          <div class="metric-value">{{ seoMetrics.health_score }}</div>
          <div class="metric-trend">
            <el-progress :percentage="seoMetrics.health_score" :stroke-width="4" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 关键词排名 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span class="card-title">关键词排名</span>
              <el-input
                v-model="keywordSearch"
                placeholder="搜索关键词"
                prefix-icon="Search"
                style="width: 200px"
                clearable
              />
            </div>
          </template>
          <el-table :data="filteredKeywords" stripe style="width: 100%">
            <el-table-column prop="keyword" label="关键词" min-width="150" />
            <el-table-column prop="position" label="当前排名" width="90" sortable>
              <template #default="{ row }">
                <el-tag :type="getPositionType(row.position)">
                  {{ row.position }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="previous_position" label="上次排名" width="90" />
            <el-table-column prop="change" label="变化" width="80" sortable>
              <template #default="{ row }">
                <span :class="row.change >= 0 ? 'positive' : 'negative'">
                  <el-icon v-if="row.change >= 0"><Top /></el-icon>
                  <el-icon v-else><Bottom /></el-icon>
                  {{ Math.abs(row.change) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="search_volume" label="搜索量" width="100" sortable />
            <el-table-column prop="difficulty" label="难度" width="80">
              <template #default="{ row }">
                <el-tag :type="getDifficultyType(row.difficulty)" size="small">
                  {{ row.difficulty }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="url" label="目标 URL" min-width="200" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span class="card-title">排名分布</span>
          </template>
          <div ref="distributionChartRef" class="chart"></div>
        </el-card>

        <el-card class="top-movers-card">
          <template #header>
            <span class="card-title">上升最快关键词</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(kw, index) in topGainers"
              :key="index"
              type="success"
              :timestamp="kw.keyword"
            >
              <span class="positive">+{{ kw.change }} 位</span>
              <span class="current-position">→ 第 {{ kw.position }} 名</span>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- SEO 审计问题 -->
    <el-card class="audit-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Warning /></el-icon>
            SEO 审计问题
          </span>
          <el-radio-group v-model="auditFilter" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="critical">严重</el-radio-button>
            <el-radio-button label="warning">警告</el-radio-button>
            <el-radio-button label="info">提示</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="filteredAuditIssues" stripe>
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="issue" label="问题描述" min-width="250" />
        <el-table-column prop="affected_pages" label="影响页数" width="100" />
        <el-table-column prop="impact" label="影响程度" width="100">
          <template #default="{ row }">
            <el-progress :percentage="row.impact * 100" :stroke-width="6"
                         :color="getImpactColor(row.impact)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" text>查看详情</el-button>
            <el-button size="small" type="primary" text>修复建议</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 竞品对比 -->
    <el-card class="competitor-card">
      <template #header>
        <span class="card-title">
          <el-icon><Compare /></el-icon>
          SEO 竞品对比
        </span>
      </template>
      <div ref="competitorChartRef" class="chart"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { seoApi } from '@/api'

// SEO 指标
const seoMetrics = reactive({
  avg_position: 12.5,
  position_change: 2.3,
  indexed_pages: 1580,
  indexed_change: 5.2,
  backlinks: 8420,
  backlinks_change: 12.5,
  health_score: 85
})

// 关键词数据
const keywords = ref<any[]>([
  { keyword: 'SEO tools', position: 3, previous_position: 5, change: 2, search_volume: 12000, difficulty: 65, url: '/products/seo-tools' },
  { keyword: 'keyword research', position: 7, previous_position: 6, change: -1, search_volume: 8500, difficulty: 58, url: '/blog/keyword-research' },
  { keyword: 'analytics platform', position: 12, previous_position: 15, change: 3, search_volume: 5200, difficulty: 72, url: '/products/analytics' },
  { keyword: 'digital marketing', position: 25, previous_position: 22, change: -3, search_volume: 18000, difficulty: 85, url: '/blog/digital-marketing' },
  { keyword: 'traffic analysis', position: 5, previous_position: 8, change: 3, search_volume: 6800, difficulty: 55, url: '/features/traffic-analysis' },
])

const keywordSearch = ref('')

// 审计问题
const auditIssues = ref<any[]>([
  { severity: 'critical', issue: '页面加载速度过慢 (LCP > 4s)', affected_pages: 15, impact: 0.85 },
  { severity: 'critical', issue: '移动端适配问题', affected_pages: 8, impact: 0.75 },
  { severity: 'warning', issue: '缺少 meta 描述', affected_pages: 32, impact: 0.45 },
  { severity: 'warning', issue: '图片缺少 alt 属性', affected_pages: 56, impact: 0.35 },
  { severity: 'info', issue: 'H1 标签使用不规范', affected_pages: 12, impact: 0.2 },
])

const auditFilter = ref('all')

// 图表引用
const distributionChartRef = ref<HTMLElement>()
const competitorChartRef = ref<HTMLElement>()

let distributionChart: echarts.ECharts | null = null
let competitorChart: echarts.ECharts | null = null

// 计算属性
const filteredKeywords = computed(() => {
  if (!keywordSearch.value) return keywords.value
  return keywords.value.filter(kw =>
    kw.keyword.toLowerCase().includes(keywordSearch.value.toLowerCase())
  )
})

const topGainers = computed(() => {
  return [...keywords.value]
    .filter(kw => kw.change > 0)
    .sort((a, b) => b.change - a.change)
    .slice(0, 5)
})

const filteredAuditIssues = computed(() => {
  if (auditFilter.value === 'all') return auditIssues.value
  return auditIssues.value.filter(issue => issue.severity === auditFilter.value)
})

// 辅助函数
const formatNumber = (num: number) => {
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

const getPositionType = (position: number) => {
  if (position <= 3) return 'success'
  if (position <= 10) return ''
  return 'info'
}

const getDifficultyType = (difficulty: number) => {
  if (difficulty <= 30) return 'success'
  if (difficulty <= 60) return 'warning'
  return 'danger'
}

const getSeverityType = (severity: string) => {
  const map: Record<string, 'danger' | 'warning' | 'info'> = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return map[severity] || 'info'
}

const getSeverityText = (severity: string) => {
  const map: Record<string, string> = {
    critical: '严重',
    warning: '警告',
    info: '提示'
  }
  return map[severity] || severity
}

const getImpactColor = (impact: number) => {
  if (impact >= 0.7) return '#f56c6c'
  if (impact >= 0.4) return '#e6a23c'
  return '#67c23a'
}

// 初始化图表
const initCharts = () => {
  // 排名分布图
  if (distributionChartRef.value) {
    distributionChart = echarts.init(distributionChartRef.value)
    distributionChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ['1-3 名', '4-10 名', '11-20 名', '21-50 名', '50+ 名']
      },
      yAxis: { type: 'value' },
      series: [{
        data: [15, 45, 82, 120, 85],
        type: 'bar',
        itemStyle: {
          color: (params: any) => {
            const colors = ['#67c23a', '#91cc75', '#fac858', '#ee6666', '#73c0de']
            return colors[params.dataIndex]
          }
        }
      }]
    })
  }

  // 竞品对比图
  if (competitorChartRef.value) {
    competitorChart = echarts.init(competitorChartRef.value)
    competitorChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['我方', 'Competitor A', 'Competitor B'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'value',
        name: '关键词数量'
      },
      yAxis: {
        type: 'category',
        data: ['前 3 名', '前 10 名', '前 20 名', '前 50 名']
      },
      series: [
        { name: '我方', type: 'bar', data: [15, 45, 82, 150] },
        { name: 'Competitor A', type: 'bar', data: [22, 58, 95, 180] },
        { name: 'Competitor B', type: 'bar', data: [18, 52, 88, 165] }
      ]
    })
  }
}

onMounted(() => {
  nextTick(() => {
    initCharts()
  })
})
</script>

<style scoped lang="scss">
.seo-analysis {
  .metric-cards {
    margin-bottom: 16px;

    .metric-card {
      .metric-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #909399;
        font-size: 14px;
      }

      .metric-value {
        font-size: 28px;
        font-weight: 600;
        margin: 12px 0;
      }

      .metric-trend {
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
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .card-title {
      font-weight: 600;
    }
  }

  .positive {
    color: #67c23a;
  }

  .negative {
    color: #f56c6c;
  }

  .chart {
    height: 300px;
  }

  .top-movers-card {
    margin-top: 16px;

    .current-position {
      color: #909399;
      font-size: 12px;
      margin-left: 8px;
    }
  }

  .audit-card {
    margin-top: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .competitor-card {
    margin-top: 16px;
  }
}
</style>
