<template>
  <div class="agents-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1>
          <el-icon :size="28"><Grid /></el-icon>
          Agent 中心
        </h1>
        <p>管理和监控所有 AI Agent 的工作状态</p>
      </div>
      <div class="header-actions">
        <el-button @click="refreshAll" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
          刷新全部
        </el-button>
      </div>
    </div>

    <!-- Bento Grid 布局 -->
    <div class="bento-grid">
      <!-- Agent 卡片 -->
      <div
        v-for="(agent, key) in agents"
        :key="key"
        class="bento-card bento-sm agent-card"
        :class="{ active: agent.active, working: agent.working }"
      >
        <div class="bento-card-header agent-card-header">
          <div class="agent-icon-wrapper" :style="{ background: agent.color }">
            <el-icon :size="24"><component :is="agent.icon" /></el-icon>
          </div>
          <el-switch
            v-model="agent.active"
            size="small"
            @change="toggleAgent(key)"
          />
        </div>

        <div class="agent-body">
          <h3>{{ agent.name }}</h3>
          <p class="agent-desc">{{ agent.description }}</p>

          <div class="agent-stats">
            <div class="stat-item">
              <span class="stat-label">任务数</span>
              <span class="stat-value">{{ agent.stats.tasks }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">成功率</span>
              <span class="stat-value">{{ agent.stats.successRate }}%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均耗时</span>
              <span class="stat-value">{{ agent.stats.avgTime }}s</span>
            </div>
          </div>

          <div class="agent-status">
            <el-tag :type="agent.working ? 'success' : agent.active ? 'info' : 'danger'" size="small" round>
              <el-icon v-if="agent.working" class="spinning"><Loading /></el-icon>
              {{ agent.working ? '执行中' : agent.active ? '就绪' : '已停用' }}
            </el-tag>
            <span v-if="agent.currentTask" class="current-task">{{ agent.currentTask }}</span>
          </div>
        </div>

        <div class="bento-card-footer agent-footer">
          <el-button size="small" text @click="viewAgentDetail(key)">
            查看详情
          </el-button>
          <el-button size="small" @click="triggerAgentTask(key)" :loading="agent.working">
            执行任务
          </el-button>
        </div>
      </div>

      <!-- 最近任务执行记录 - 横跨多列 -->
      <div class="bento-card bento-lg" style="grid-row: span 2;">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon tasks-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <span>最近任务执行</span>
          </div>
          <el-button text size="small" @click="viewAllTasks">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="bento-card-body tasks-body">
          <el-table :data="recentTasks" style="width: 100%" :header-cell-style="{ background: '#f8fafc' }">
            <el-table-column prop="agent" label="Agent" width="120">
              <template #default="{ row }">
                <el-tag size="small" :style="{ background: getAgentColor(row.agent), color: '#fff', border: 'none' }">
                  {{ row.agent }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="task" label="任务" min-width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small" round>
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="70" />
            <el-table-column prop="timestamp" label="时间" width="160" />
          </el-table>
        </div>
      </div>

      <!-- Agent 性能对比图表 -->
      <div class="bento-card bento-sm">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon chart-icon">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <span>任务完成率</span>
          </div>
        </div>
        <div class="bento-card-body chart-body">
          <div ref="successRateChartRef" class="chart"></div>
        </div>
      </div>

      <div class="bento-card bento-sm">
        <div class="bento-card-header">
          <div class="card-title">
            <div class="title-icon pie-icon">
              <el-icon><PieChart /></el-icon>
            </div>
            <span>任务类型分布</span>
          </div>
        </div>
        <div class="bento-card-body chart-body">
          <div ref="taskTypeChartRef" class="chart"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { ElMessage } from 'element-plus'

// Agent 状态
const agents = ref({
  seo: {
    name: 'SEO Agent',
    icon: 'Search',
    description: '负责关键词分析、排名追踪、SEO 优化建议',
    color: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 128, successRate: 96, avgTime: 3.2 }
  },
  content: {
    name: '内容 Agent',
    icon: 'Document',
    description: '负责内容生成、优化建议、A/B 测试文案',
    color: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 86, successRate: 94, avgTime: 5.1 }
  },
  abtest: {
    name: 'A/B 测试 Agent',
    icon: 'Compare',
    description: '负责 A/B 测试设计、执行和结果分析',
    color: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
    active: true,
    working: true,
    currentTask: '正在分析测试组数据...',
    stats: { tasks: 45, successRate: 98, avgTime: 8.3 }
  },
  analysis: {
    name: '分析 Agent',
    icon: 'DataAnalysis',
    description: '负责流量分析、异常检测、归因分析',
    color: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 256, successRate: 99, avgTime: 2.1 }
  },
  competitor: {
    name: '竞品 Agent',
    icon: 'Monitor',
    description: '负责竞品监控、市场份额分析',
    color: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 67, successRate: 95, avgTime: 4.5 }
  },
  optimization: {
    name: '优化 Agent',
    icon: 'MagicStick',
    description: '负责自动优化策略生成和执行',
    color: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 92, successRate: 93, avgTime: 6.8 }
  }
})

// 最近任务
const recentTasks = ref([
  { agent: 'SEO Agent', task: '关键词排名分析', status: 'completed', duration: '2.3s', timestamp: '2024-01-15 10:30:00' },
  { agent: 'A/B 测试 Agent', task: '测试组数据收集', status: 'running', duration: '-', timestamp: '2024-01-15 10:28:00' },
  { agent: '分析 Agent', task: '流量异常检测', status: 'completed', duration: '1.8s', timestamp: '2024-01-15 10:25:00' },
  { agent: '内容 Agent', task: '生成优化文案', status: 'completed', duration: '4.2s', timestamp: '2024-01-15 10:20:00' },
  { agent: '竞品 Agent', task: '竞品价格监控', status: 'failed', duration: '3.1s', timestamp: '2024-01-15 10:15:00' }
])

// 刷新状态
const refreshing = ref(false)

// 图表引用
const successRateChartRef = ref<HTMLElement>()
const taskTypeChartRef = ref<HTMLElement>()
let successRateChart: ECharts | null = null
let taskTypeChart: ECharts | null = null

// 方法
const refreshAll = () => {
  refreshing.value = true
  setTimeout(() => {
    refreshing.value = false
    ElMessage.success('数据已刷新')
  }, 1000)
}

const toggleAgent = (key: string) => {
  const agent = agents.value[key]
  ElMessage.success(`${agent.name} 已${agent.active ? '启用' : '停用'}`)
}

const viewAgentDetail = (key: string) => {
  ElMessage.info('查看详情功能开发中')
}

const triggerAgentTask = (key: string) => {
  const agent = agents.value[key]
  agent.working = true
  agent.currentTask = '正在执行任务...'

  setTimeout(() => {
    agent.working = false
    agent.currentTask = ''
    agent.stats.tasks += 1
    ElMessage.success(`${agent.name} 任务执行完成`)
  }, 3000)
}

const viewAllTasks = () => {
  ElMessage.info('查看全部功能开发中')
}

const getAgentColor = (agentName: string) => {
  const colors: Record<string, string> = {
    'SEO Agent': '#6366f1',
    'A/B 测试 Agent': '#06b6d4',
    '分析 Agent': '#22c55e',
    '内容 Agent': '#ec4899',
    '竞品 Agent': '#f97316'
  }
  return colors[agentName] || '#64748b'
}

const getStatusType = (status: string) => {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    completed: 'success',
    running: 'warning',
    failed: 'danger',
    pending: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    running: '执行中',
    failed: '失败',
    pending: '等待中'
  }
  return map[status] || status
}

// 初始化图表
const initCharts = () => {
  // 成功率图表
  if (successRateChartRef.value) {
    successRateChart = echarts.init(successRateChartRef.value)
    successRateChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['SEO', '内容', 'A/B', '分析', '竞品', '优化'],
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#64748b' }
      },
      yAxis: {
        type: 'value',
        min: 80,
        max: 100,
        axisLabel: { formatter: '{value}%', color: '#64748b' },
        splitLine: { lineStyle: { color: '#f1f5f9' } }
      },
      series: [{
        data: [96, 94, 98, 99, 95, 93],
        type: 'bar',
        barWidth: '60%',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#6366f1' },
            { offset: 1, color: '#4f46e5' }
          ])
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          color: '#64748b'
        }
      }]
    })
  }

  // 任务类型分布
  if (taskTypeChartRef.value) {
    taskTypeChart = echarts.init(taskTypeChartRef.value)
    taskTypeChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center', textStyle: { color: '#64748b' } },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: '600' }
        },
        data: [
          { value: 128, name: 'SEO 分析', itemStyle: { color: '#6366f1' } },
          { value: 86, name: '内容生成', itemStyle: { color: '#ec4899' } },
          { value: 45, name: 'A/B 测试', itemStyle: { color: '#06b6d4' } },
          { value: 256, name: '数据分析', itemStyle: { color: '#22c55e' } },
          { value: 67, name: '竞品监控', itemStyle: { color: '#f97316' } }
        ]
      }]
    })
  }
}

onMounted(() => {
  nextTick(() => {
    initCharts()
  })

  window.addEventListener('resize', () => {
    successRateChart?.resize()
    taskTypeChart?.resize()
  })
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';
@import '@/styles/bento.scss';

.agents-page {
  padding: $spacing-6;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;

  .header-content {
    h1 {
      display: flex;
      align-items: center;
      gap: $spacing-3;
      font-size: $font-size-2xl;
      color: $text-primary;
      margin: 0 0 $spacing-2 0;
      font-weight: $font-weight-bold;
    }

    p {
      font-size: $font-size-sm;
      color: $text-tertiary;
      margin: 0;
    }
  }

  .header-actions {
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
  grid-auto-rows: minmax(200px, auto);
  gap: $spacing-4;

  @media (max-width: 1280px) {
    grid-template-columns: repeat(6, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
  }
}

// Agent 卡片
.agent-card {
  grid-row: span 1;
  display: flex;
  flex-direction: column;

  @media (max-width: 1280px) {
    grid-column: span 3;
  }

  @media (max-width: 768px) {
    grid-column: span 1;
  }

  &.active {
    border-top: 3px solid $success;
  }

  &.working {
    border-top: 3px solid $indigo-500;
    animation: working-pulse 2s infinite;
  }
}

.agent-card-header {
  .agent-icon-wrapper {
    width: 44px;
    height: 44px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    box-shadow: $shadow-md;
  }
}

.agent-body {
  flex: 1;

  h3 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: $spacing-3 0 $spacing-2 0;
  }

  .agent-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
    line-height: 1.5;
    margin: 0 0 $spacing-4 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .agent-stats {
    display: flex;
    gap: $spacing-2;
    margin-bottom: $spacing-4;
    padding: $spacing-3;
    background: $bg-secondary;
    border-radius: $radius-md;

    .stat-item {
      flex: 1;
      text-align: center;

      .stat-label {
        font-size: $font-size-xs;
        color: $text-tertiary;
        display: block;
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: $font-size-lg;
        font-weight: $font-weight-semibold;
        color: $text-primary;
      }
    }
  }

  .agent-status {
    display: flex;
    align-items: center;
    gap: $spacing-2;

    .current-task {
      font-size: $font-size-xs;
      color: $text-tertiary;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.agent-footer {
  justify-content: flex-end;
}

// 任务列表
.tasks-body {
  :deep(.el-table) {
    font-size: $font-size-sm;

    th.el-table__cell {
      background: #f8fafc;
      color: $text-secondary;
      font-weight: $font-weight-medium;
    }

    td.el-table__cell {
      padding: $spacing-3;
    }

    .el-table__body tr:hover {
      background: $slate-50;
    }
  }
}

// 图表卡片
.chart-body {
  height: 220px;

  .chart {
    width: 100%;
    height: 100%;
  }
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

  &.tasks-icon { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
  &.chart-icon { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
  &.pie-icon { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); }
}

@keyframes working-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.2);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(99, 102, 241, 0);
  }
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
