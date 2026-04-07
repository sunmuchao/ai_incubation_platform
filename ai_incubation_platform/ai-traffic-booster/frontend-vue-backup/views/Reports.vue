<template>
  <div class="reports">
    <!-- 报告模板快捷入口 -->
    <el-card class="templates-card">
      <template #header>
        <span class="card-title">
          <el-icon><Document /></el-icon>
          报告模板
        </span>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="template in reportTemplates" :key="template.id">
          <el-card shadow="hover" class="template-card" @click="createReport(template)">
            <div class="template-icon">
              <el-icon :size="40"><Document /></el-icon>
            </div>
            <div class="template-info">
              <div class="template-name">{{ template.name }}</div>
              <div class="template-desc">{{ template.description }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 报告列表 -->
    <el-card class="reports-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">历史报告</span>
          <el-radio-group v-model="reportFilter" size="small" @change="filterReports">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="weekly">周报</el-radio-button>
            <el-radio-button label="monthly">月报</el-radio-button>
            <el-radio-button label="custom">自定义</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="filteredReports" stripe>
        <el-table-column prop="title" label="报告标题" min-width="200" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ getReportTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date_range" label="数据范围" width="180" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">
              {{ row.status === 'completed' ? '已完成' : '生成中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" text @click="viewReport(row)" :disabled="row.status !== 'completed'">
              查看
            </el-button>
            <el-button size="small" text @click="downloadReport(row, 'pdf')" :disabled="row.status !== 'completed'">
              PDF
            </el-button>
            <el-button size="small" text @click="downloadReport(row, 'excel')" :disabled="row.status !== 'completed'">
              Excel
            </el-button>
            <el-button size="small" text type="danger" @click="deleteReport(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 报告预览对话框 -->
    <el-dialog v-model="showReportPreview" title="报告预览" width="900px" class="report-preview-dialog">
      <div class="report-preview">
        <!-- 报告头部 -->
        <div class="report-header">
          <h2>{{ currentReport?.title }}</h2>
          <p class="report-meta">
            数据范围：{{ currentReport?.date_range }} | 生成时间：{{ currentReport?.created_at }}
          </p>
        </div>

        <!-- 执行摘要 -->
        <el-card class="report-section">
          <h3>执行摘要</h3>
          <ul>
            <li>本周总访客数：128,450，环比上升 12.5%</li>
            <li>平均排名提升至 12.3 位，上升 2.1 位</li>
            <li>发现 3 个流量增长机会，预期可提升 15% 流量</li>
            <li>2 个严重告警已处理，1 个待跟进</li>
          </ul>
        </el-card>

        <!-- 流量趋势 -->
        <el-card class="report-section">
          <h3>流量趋势</h3>
          <div ref="reportTrendChartRef" class="report-chart"></div>
        </el-card>

        <!-- AI 洞察 -->
        <el-card class="report-section">
          <h3>AI 洞察</h3>
          <el-alert title="发现流量增长机会" type="success" show-icon class="report-insight">
            <template #default>
              关键词 "SEO tools" 搜索量上升 25%，建议优化相关页面内容
            </template>
          </el-alert>
          <el-alert title="竞品流量接近超越" type="warning" show-icon class="report-insight">
            <template #default>
              Competitor A 本周流量增长 15%，需加强核心关键词排名
            </template>
          </el-alert>
        </el-card>

        <!-- 建议行动 -->
        <el-card class="report-section">
          <h3>建议行动</h3>
          <el-table :data="reportActions" stripe size="small">
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }">
                <el-tag :type="row.priority === 'high' ? 'danger' : 'warning'" size="small">
                  {{ row.priority === 'high' ? '高' : '中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="行动项" min-width="300" />
            <el-table-column prop="expected_impact" label="预期影响" width="100" />
          </el-table>
        </el-card>
      </div>
      <template #footer>
        <el-button @click="showReportPreview = false">关闭</el-button>
        <el-button type="primary" @click="exportCurrentReport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { queryAssistantApi } from '@/api'

const reportTemplates = ref([
  { id: 'weekly', name: '周报', description: '每周流量和 SEO 表现总结' },
  { id: 'monthly', name: '月报', description: '月度综合分析报告' },
  { id: 'anomaly', name: '异常分析报告', description: '流量异常深度分析' },
  { id: 'competitor', name: '竞品分析报告', description: '竞品对比和策略分析' },
])

const reports = ref<any[]>([
  { id: '1', title: '周报 - 2024 年第 2 周', type: 'weekly', date_range: '2024-01-08 ~ 2024-01-14', created_at: '2024-01-15 09:00', status: 'completed' },
  { id: '2', title: '月报 - 2023 年 12 月', type: 'monthly', date_range: '2023-12-01 ~ 2023-12-31', created_at: '2024-01-02 10:00', status: 'completed' },
  { id: '3', title: '异常分析报告 - 流量下跌', type: 'anomaly', date_range: '2024-01-10 ~ 2024-01-12', created_at: '2024-01-12 15:30', status: 'completed' },
  { id: '4', title: '竞品分析报告 - Q4', type: 'competitor', date_range: '2023-10-01 ~ 2023-12-31', created_at: '2024-01-05 14:00', status: 'completed' },
  { id: '5', title: '周报 - 2024 年第 3 周', type: 'weekly', date_range: '2024-01-15 ~ 2024-01-21', created_at: '-', status: 'pending' },
])

const reportFilter = ref('all')
const showReportPreview = ref(false)
const currentReport = ref<any>(null)

const reportActions = ref([
  { priority: 'high', action: '优化关键词 "SEO tools" 相关页面内容，提升排名', expected_impact: '+15%' },
  { priority: 'high', action: '检查移动端页面加载速度，解决 LCP 超时问题', expected_impact: '+8%' },
  { priority: 'medium', action: '增加视频教程内容，提升用户参与度', expected_impact: '+12%' },
  { priority: 'medium', action: '优化定价页面布局，提升转化率', expected_impact: '+18%' },
])

const filteredReports = computed(() => {
  if (reportFilter.value === 'all') return reports.value
  return reports.value.filter(r => r.type === reportFilter.value)
})

let reportTrendChart: echarts.ECharts | null = null

const getReportTypeText = (type: string) => {
  const map: Record<string, string> = {
    weekly: '周报',
    monthly: '月报',
    anomaly: '异常分析',
    competitor: '竞品分析',
    custom: '自定义'
  }
  return map[type] || type
}

const filterReports = () => {
  // computed handles this
}

const createReport = (template: any) => {
  console.log('Create report:', template)
  ElMessage.info(`开始生成 ${template.name}...`)
  // TODO: 调用生成报告 API
}

const viewReport = (row: any) => {
  currentReport.value = row
  showReportPreview.value = true
  nextTick(() => {
    initReportChart()
  })
}

const initReportChart = () => {
  const chartRef = document.querySelector('.report-chart')
  if (!chartRef) return

  reportTrendChart = echarts.init(chartRef)
  reportTrendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    },
    yAxis: { type: 'value' },
    series: [{
      name: '访客数',
      type: 'line',
      smooth: true,
      data: [820, 932, 901, 934, 1290, 1330, 1320],
      itemStyle: { color: '#409EFF' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.01)' }
        ])
      }
    }]
  })
}

const downloadReport = (row: any, format: string) => {
  ElMessage.success(`开始下载 ${row.title}.${format}`)
}

const deleteReport = (row: any) => {
  reports.value = reports.value.filter(r => r.id !== row.id)
  ElMessage.success('已删除报告')
}

const exportCurrentReport = () => {
  ElMessage.success('报告导出成功')
}
</script>

<style scoped lang="scss">
.reports {
  .templates-card {
    margin-bottom: 16px;

    .card-title {
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .template-card {
      cursor: pointer;
      transition: all 0.3s;
      text-align: center;
      padding: 16px;

      &:hover {
        transform: translateY(-4px);
      }

      .template-icon {
        display: flex;
        justify-content: center;
        margin-bottom: 12px;
        color: #409EFF;
      }

      .template-info {
        .template-name {
          font-weight: 600;
          margin-bottom: 4px;
        }

        .template-desc {
          font-size: 12px;
          color: #909399;
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

  .report-preview-dialog {
    .report-preview {
      .report-header {
        text-align: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #f0f0f0;

        h2 {
          margin-bottom: 8px;
        }

        .report-meta {
          color: #909399;
          font-size: 14px;
        }
      }

      .report-section {
        margin-bottom: 16px;

        h3 {
          margin-bottom: 16px;
          padding-left: 12px;
          border-left: 4px solid #409EFF;
        }

        .report-chart {
          height: 250px;
        }

        .report-insight {
          margin-bottom: 12px;
        }
      }
    }
  }
}
</style>
