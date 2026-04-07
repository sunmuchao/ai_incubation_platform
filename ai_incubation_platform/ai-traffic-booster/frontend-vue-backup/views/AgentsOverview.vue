<template>
  <div class="agents-overview">
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
        <el-button @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新全部
        </el-button>
      </div>
    </div>

    <!-- Agent 状态概览 -->
    <el-row :gutter="20" class="agents-grid">
      <el-col :span="8" v-for="(agent, key) in agents" :key="key">
        <el-card class="agent-card" :class="{ active: agent.active, working: agent.working }">
          <div class="agent-header">
            <div class="agent-icon-wrapper" :style="{ background: agent.color }">
              <el-icon :size="32"><component :is="agent.icon" /></el-icon>
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
              <el-tag :type="agent.working ? 'success' : agent.active ? 'info' : 'danger'" size="small">
                <el-icon v-if="agent.working" class="spinning"><Loading /></el-icon>
                {{ agent.working ? '执行中' : agent.active ? '就绪' : '已停用' }}
              </el-tag>
              <span v-if="agent.currentTask" class="current-task">{{ agent.currentTask }}</span>
            </div>
          </div>

          <div class="agent-footer">
            <el-button size="small" text @click="viewAgentDetail(key)">
              查看详情
            </el-button>
            <el-button size="small" text @click="triggerAgentTask(key)">
              执行任务
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近任务执行记录 -->
    <el-card class="tasks-card">
      <template #header>
        <div class="card-header">
          <span>
            <el-icon><Clock /></el-icon>
            最近任务执行
          </span>
          <el-button text size="small" @click="viewAllTasks">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>

      <el-table :data="recentTasks" style="width: 100%">
        <el-table-column prop="agent" label="Agent" width="120">
          <template #default="{ row }">
            <el-tag size="small" :style="{ background: getAgentColor(row.agent) }">
              {{ row.agent }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="task" label="任务" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="80" />
        <el-table-column prop="timestamp" label="时间" width="180" />
      </el-table>
    </el-card>

    <!-- Agent 性能对比 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>
              <el-icon><TrendCharts /></el-icon>
              Agent 任务完成率
            </span>
          </template>
          <div ref="successRateChartRef" class="chart"></div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>
              <el-icon><PieChart /></el-icon>
              任务类型分布
            </span>
          </template>
          <div ref="taskTypeChartRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { ElMessage } from 'element-plus'

// Agent 状态
const agents = ref({
  seo: {
    name: 'SEO Agent',
    icon: 'Search',
    description: '负责关键词分析、排名追踪、SEO 优化建议',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 128, successRate: 96, avgTime: 3.2 }
  },
  content: {
    name: '内容 Agent',
    icon: 'Document',
    description: '负责内容生成、优化建议、A/B 测试文案',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 86, successRate: 94, avgTime: 5.1 }
  },
  abtest: {
    name: 'A/B 测试 Agent',
    icon: 'Compare',
    description: '负责 A/B 测试设计、执行和结果分析',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    active: true,
    working: true,
    currentTask: '正在分析测试组数据...',
    stats: { tasks: 45, successRate: 98, avgTime: 8.3 }
  },
  analysis: {
    name: '分析 Agent',
    icon: 'DataAnalysis',
    description: '负责流量分析、异常检测、归因分析',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 256, successRate: 99, avgTime: 2.1 }
  },
  competitor: {
    name: '竞品 Agent',
    icon: 'Monitor',
    description: '负责竞品监控、市场份额分析',
    color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    active: true,
    working: false,
    currentTask: '',
    stats: { tasks: 67, successRate: 95, avgTime: 4.5 }
  },
  optimization: {
    name: '优化 Agent',
    icon: 'MagicStick',
    description: '负责自动优化策略生成和执行',
    color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
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

// 图表引用
const successRateChartRef = ref<HTMLElement>()
const taskTypeChartRef = ref<HTMLElement>()
let successRateChart: ECharts | null = null
let taskTypeChart: ECharts | null = null

// 方法
const refreshAll = () => {
  ElMessage.success('数据已刷新')
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
    'SEO Agent': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'A/B 测试 Agent': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    '分析 Agent': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    '内容 Agent': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    '竞品 Agent': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
  }
  return colors[agentName] || '#909399'
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
        data: ['SEO', '内容', 'A/B 测试', '分析', '竞品', '优化']
      },
      yAxis: {
        type: 'value',
        min: 80,
        max: 100,
        axisLabel: { formatter: '{value}%' }
      },
      series: [{
        data: [96, 94, 98, 99, 95, 93],
        type: 'bar',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%'
        }
      }]
    })
  }

  // 任务类型分布
  if (taskTypeChartRef.value) {
    taskTypeChart = echarts.init(taskTypeChartRef.value)
    taskTypeChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: 128, name: 'SEO 分析' },
          { value: 86, name: '内容生成' },
          { value: 45, name: 'A/B 测试' },
          { value: 256, name: '数据分析' },
          { value: 67, name: '竞品监控' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
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
.agents-overview {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .header-content {
      h1 {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 24px;
        color: #303133;
        margin: 0 0 8px 0;
      }

      p {
        font-size: 14px;
        color: #909399;
        margin: 0;
      }
    }
  }

  .agents-grid {
    margin-bottom: 24px;

    .agent-card {
      transition: all 0.3s;
      cursor: pointer;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
      }

      &.active {
        border-top: 3px solid #67c23a;
      }

      &.working {
        border-top: 3px solid #409EFF;
        animation: working-pulse 2s infinite;
      }

      .agent-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;

        .agent-icon-wrapper {
          width: 56px;
          height: 56px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
        }
      }

      .agent-body {
        h3 {
          font-size: 16px;
          color: #303133;
          margin: 0 0 8px 0;
        }

        .agent-desc {
          font-size: 13px;
          color: #909399;
          margin: 0 0 16px 0;
          line-height: 1.5;
        }

        .agent-stats {
          display: flex;
          gap: 16px;
          margin-bottom: 16px;
          padding: 12px;
          background: #f5f7fa;
          border-radius: 8px;

          .stat-item {
            flex: 1;
            text-align: center;

            .stat-label {
              font-size: 11px;
              color: #909399;
              display: block;
              margin-bottom: 4px;
            }

            .stat-value {
              font-size: 18px;
              font-weight: 600;
              color: #303133;
            }
          }
        }

        .agent-status {
          display: flex;
          align-items: center;
          gap: 8px;

          .current-task {
            font-size: 12px;
            color: #909399;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
        }
      }

      .agent-footer {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding-top: 12px;
        border-top: 1px solid #f0f0f0;
      }
    }
  }

  .tasks-card {
    margin-bottom: 24px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      span {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
    }
  }

  .charts-row {
    .chart-card {
      .chart {
        height: 300px;
      }
    }
  }
}

@keyframes working-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.2);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(64, 158, 255, 0);
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
