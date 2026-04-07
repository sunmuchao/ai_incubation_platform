<template>
  <div class="competitor-analysis">
    <!-- 竞品追踪列表 -->
    <el-card class="tracking-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Monitor /></el-icon>
            竞品追踪
          </span>
          <el-button type="primary" @click="showAddCompetitor = true">
            <el-icon><Plus /></el-icon>
            添加竞品
          </el-button>
        </div>
      </template>

      <el-table :data="competitors" stripe>
        <el-table-column prop="domain" label="域名" min-width="150" />
        <el-table-column prop="traffic" label="月流量" width="120" sortable>
          <template #default="{ row }">{{ formatNumber(row.traffic) }}</template>
        </el-table-column>
        <el-table-column prop="traffic_change" label="变化" width="100" sortable>
          <template #default="{ row }">
            <span :class="row.traffic_change >= 0 ? 'positive' : 'negative'">
              {{ row.traffic_change >= 0 ? '+' : '' }}{{ row.traffic_change }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="keywords" label="关键词数" width="100" sortable />
        <el-table-column prop="backlinks" label="外链数" width="100" sortable>
          <template #default="{ row }">{{ formatNumber(row.backlinks) }}</template>
        </el-table-column>
        <el-table-column prop="authority" label="域名权重" width="100">
          <template #default="{ row }">
            <el-progress :percentage="row.authority" :stroke-width="6" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text @click="viewCompetitorDetail(row)">详情</el-button>
            <el-button size="small" text @click="compareCompetitor(row)">对比</el-button>
            <el-button size="small" text type="danger" @click="removeCompetitor(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 竞品雷达图 -->
    <el-row :gutter="16" class="row-card">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">多维对比</span>
          </template>
          <div ref="radarChartRef" class="chart"></div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">流量趋势对比</span>
          </template>
          <div ref="trendChartRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 市场份额 -->
    <el-card class="market-share-card">
      <template #header>
        <span class="card-title">
          <el-icon><PieChart /></el-icon>
          市场份额
        </span>
      </template>
      <div ref="marketShareChartRef" class="chart"></div>
    </el-card>

    <!-- 竞品策略洞察 -->
    <el-card class="insights-card">
      <template #header>
        <span class="card-title">
          <el-icon><Lightbulb /></el-icon>
          竞品策略洞察
        </span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="内容策略">
          竞品 A 最近增加了视频教程内容，互动率提升 35%
        </el-descriptions-item>
        <el-descriptions-item label="关键词策略">
          竞品 B 重点布局长尾关键词，获取大量精准流量
        </el-descriptions-item>
        <el-descriptions-item label="外链策略">
          竞品 C 通过行业报告获取高质量外链
        </el-descriptions-item>
        <el-descriptions-item label="社交媒体">
          竞品 D 在 LinkedIn 平台表现突出，B2B 流量增长明显
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 添加竞品对话框 -->
    <el-dialog v-model="showAddCompetitor" title="添加竞品" width="500px">
      <el-form :model="newCompetitor" label-width="80px">
        <el-form-item label="域名" required>
          <el-input v-model="newCompetitor.domain" placeholder="example.com" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newCompetitor.note" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddCompetitor = false">取消</el-button>
        <el-button type="primary" @click="addCompetitor">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { competitorApi } from '@/api'

const competitors = ref<any[]>([
  { domain: 'competitor-a.com', traffic: 580000, traffic_change: 12.5, keywords: 15800, backlinks: 45000, authority: 72 },
  { domain: 'competitor-b.com', traffic: 420000, traffic_change: -3.2, keywords: 12500, backlinks: 32000, authority: 65 },
  { domain: 'competitor-c.com', traffic: 350000, traffic_change: 8.7, keywords: 9800, backlinks: 28000, authority: 58 },
])

const showAddCompetitor = ref(false)
const newCompetitor = reactive({
  domain: '',
  note: ''
})

// 图表引用
const radarChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const marketShareChartRef = ref<HTMLElement>()

let radarChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let marketShareChart: echarts.ECharts | null = null

const formatNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(0) + 'K'
  return num.toString()
}

const viewCompetitorDetail = (row: any) => {
  console.log('View detail:', row)
}

const compareCompetitor = (row: any) => {
  console.log('Compare:', row)
}

const removeCompetitor = (row: any) => {
  competitors.value = competitors.value.filter(c => c.domain !== row.domain)
  ElMessage.success('已移除竞品')
}

const addCompetitor = () => {
  if (!newCompetitor.domain) {
    ElMessage.warning('请输入域名')
    return
  }
  competitors.value.push({
    domain: newCompetitor.domain,
    traffic: 0,
    traffic_change: 0,
    keywords: 0,
    backlinks: 0,
    authority: 0
  })
  showAddCompetitor.value = false
  ElMessage.success('添加成功')
}

const initCharts = () => {
  // 雷达图
  if (radarChartRef.value) {
    radarChart = echarts.init(radarChartRef.value)
    radarChart.setOption({
      tooltip: { trigger: 'item' },
      radar: {
        indicator: [
          { name: '流量规模', max: 100 },
          { name: '域名权威', max: 100 },
          { name: '内容质量', max: 100 },
          { name: '外链数量', max: 100 },
          { name: '关键词覆盖', max: 100 },
          { name: '社交媒体', max: 100 }
        ]
      },
      series: [{
        name: '竞品对比',
        type: 'radar',
        data: [
          { value: [75, 72, 80, 65, 70, 60], name: '我方' },
          { value: [85, 82, 75, 80, 78, 70], name: 'Competitor A' },
          { value: [70, 65, 78, 68, 65, 75], name: 'Competitor B' }
        ]
      }]
    })
  }

  // 趋势对比图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['我方', 'Competitor A', 'Competitor B'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: ['1 月', '2 月', '3 月', '4 月', '5 月', '6 月']
      },
      yAxis: { type: 'value' },
      series: [
        { name: '我方', type: 'line', smooth: true, data: [820, 932, 901, 934, 1290, 1330] },
        { name: 'Competitor A', type: 'line', smooth: true, data: [920, 1032, 1101, 1134, 1390, 1530] },
        { name: 'Competitor B', type: 'line', smooth: true, data: [720, 832, 801, 834, 1090, 1130] }
      ]
    })
  }

  // 市场份额图
  if (marketShareChartRef.value) {
    marketShareChart = echarts.init(marketShareChartRef.value)
    marketShareChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        name: '市场份额',
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: 28, name: 'Competitor A' },
          { value: 22, name: 'Competitor B' },
          { value: 18, name: '我方' },
          { value: 15, name: 'Competitor C' },
          { value: 17, name: '其他' }
        ]
      }]
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
.competitor-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .card-title {
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .positive {
    color: #67c23a;
  }

  .negative {
    color: #f56c6c;
  }

  .row-card {
    margin-bottom: 16px;

    .chart {
      height: 300px;
    }
  }

  .market-share-card {
    margin-bottom: 16px;

    .chart {
      height: 350px;
    }
  }

  .insights-card {
    .card-title {
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }
}
</style>
