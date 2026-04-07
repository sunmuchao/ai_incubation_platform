<template>
  <div class="automation">
    <!-- 自动化概览 -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><Finished /></el-icon>
            <span>活跃任务</span>
          </div>
          <div class="metric-value">{{ automationStats.active }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><Clock /></el-icon>
            <span>待执行</span>
          </div>
          <div class="metric-value">{{ automationStats.pending }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><CircleCheck /></el-icon>
            <span>本周完成</span>
          </div>
          <div class="metric-value">{{ automationStats.completed }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <el-icon><TrendCharts /></el-icon>
            <span>平均效果提升</span>
          </div>
          <div class="metric-value">+{{ automationStats.avgImprovement }}%</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- A/B 测试 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><MagicStick /></el-icon>
            A/B 测试自动化
          </span>
          <el-button type="primary" @click="showCreateTest = true">
            <el-icon><Plus /></el-icon>
            创建测试
          </el-button>
        </div>
      </template>

      <el-table :data="abTests" stripe>
        <el-table-column prop="name" label="测试名称" min-width="180" />
        <el-table-column prop="page" label="测试页面" min-width="150" show-overflow-tooltip />
        <el-table-column prop="hypothesis" label="假设" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="row.status === 'completed' ? 'success' : ''" />
          </template>
        </el-table-column>
        <el-table-column prop="winner" label="胜出方案" width="120">
          <template #default="{ row }">
            {{ row.winner || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="improvement" label="提升幅度" width="100" sortable>
          <template #default="{ row }">
            <span v-if="row.improvement" :class="row.improvement >= 0 ? 'positive' : 'negative'">
              {{ row.improvement >= 0 ? '+' : '' }}{{ row.improvement }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text @click="viewTestDetail(row)">详情</el-button>
            <el-button size="small" text v-if="row.status === 'running'" @click="stopTest(row)">停止</el-button>
            <el-button size="small" text v-if="row.status === 'completed'" @click="applyWinner(row)">应用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 代码优化建议 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><CodeStyle /></el-icon>
            AI 代码优化建议
          </span>
        </div>
      </template>

      <el-table :data="codeSuggestions" stripe>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="建议" min-width="250" />
        <el-table-column prop="page" label="影响页面" min-width="150" show-overflow-tooltip />
        <el-table-column prop="effort" label="工作量" width="100">
          <template #default="{ row }">
            <el-tag :type="getEffortType(row.effort)" size="small">{{ row.effort }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expected_impact" label="预期提升" width="100" sortable>
          <template #default="{ row }">
            <span class="positive">+{{ row.expected_impact }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text @click="viewCodeSuggestion(row)">查看代码</el-button>
            <el-button size="small" text type="primary" @click="applyCodeSuggestion(row)">应用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学习洞察 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Lightbulb /></el-icon>
            AI 学习洞察
          </span>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="最有效的优化类型">
          <el-tag type="success">标题优化</el-tag>
          <span style="margin-left: 8px; color: #909399">平均提升 23% CTR</span>
        </el-descriptions-item>
        <el-descriptions-item label="最佳执行时段">
          周二至周四上午 10 点
        </el-descriptions-item>
        <el-descriptions-item label="高成功率的页面类型">
          产品页面（成功率 78%）
        </el-descriptions-item>
        <el-descriptions-item label="建议优先关注">
          移动端性能优化
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 创建 A/B 测试对话框 -->
    <el-dialog v-model="showCreateTest" title="创建 A/B 测试" width="700px">
      <el-form :model="newTest" label-width="120px">
        <el-form-item label="测试名称" required>
          <el-input v-model="newTest.name" placeholder="例如：CTA 按钮颜色测试" />
        </el-form-item>
        <el-form-item label="测试页面" required>
          <el-input v-model="newTest.page" placeholder="/products/seo-tools" />
        </el-form-item>
        <el-form-item label="测试假设" required>
          <el-input v-model="newTest.hypothesis" type="textarea" :rows="3"
                    placeholder="描述你的测试假设，例如：将 CTA 按钮从蓝色改为红色将提升点击率" />
        </el-form-item>
        <el-form-item label="变体方案" required>
          <el-row :gutter="8" v-for="(variant, index) in newTest.variants" :key="index" style="margin-bottom: 8px">
            <el-col :span="10">
              <el-input v-model="variant.name" placeholder="变体名称（如：对照组、实验组 A）" />
            </el-col>
            <el-col :span="12">
              <el-input v-model="variant.description" placeholder="变体描述" />
            </el-col>
            <el-col :span="2">
              <el-button text type="danger" @click="removeVariant(index)" v-if="index > 0">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
          <el-button size="small" @click="addVariant">
            <el-icon><Plus /></el-icon>
            添加变体
          </el-button>
        </el-form-item>
        <el-form-item label="主要指标" required>
          <el-select v-model="newTest.primary_metric" style="width: 100%">
            <el-option label="点击率 (CTR)" value="ctr" />
            <el-option label="转化率 (CVR)" value="cvr" />
            <el-option label="平均订单价值 (AOV)" value="aov" />
            <el-option label="页面停留时长" value="duration" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateTest = false">取消</el-button>
        <el-button type="primary" @click="createTest">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { aiOptimizationApi } from '@/api'

const automationStats = reactive({
  active: 5,
  pending: 3,
  completed: 28,
  avgImprovement: 15.5
})

const abTests = ref<any[]>([
  { name: 'CTA 按钮颜色测试', page: '/products/seo-tools', hypothesis: '红色按钮比蓝色按钮更醒目，提升点击率', status: 'running', progress: 65, winner: null, improvement: null },
  { name: '定价页面布局优化', page: '/pricing', hypothesis: '三栏布局比单栏布局转化率更高', status: 'completed', progress: 100, winner: '变体 A', improvement: 18.5 },
  { name: '首页 Hero 文案测试', page: '/', hypothesis: '强调价值的文案比强调功能的文案转化更好', status: 'running', progress: 32, winner: null, improvement: null },
  { name: '结账流程简化测试', page: '/checkout', hypothesis: '减少表单字段将提升完成率', status: 'completed', progress: 100, winner: '变体 B', improvement: 25.3 },
])

const codeSuggestions = ref<any[]>([
  { type: 'SEO', title: '优化页面 Title 标签，包含核心关键词', page: '/blog/seo-guide', effort: '低', expected_impact: 12 },
  { type: '性能', title: '启用图片懒加载，提升首屏速度', page: '/products', effort: '中', expected_impact: 8 },
  { type: '转化', title: '在首屏添加社会证明元素', page: '/pricing', effort: '低', expected_impact: 15 },
  { type: 'SEO', title: '添加结构化数据标记', page: '/products/*', effort: '中', expected_impact: 5 },
])

const showCreateTest = ref(false)
const newTest = reactive({
  name: '',
  page: '',
  hypothesis: '',
  variants: [{ name: '对照组', description: '原始版本' }, { name: '实验组 A', description: '' }],
  primary_metric: 'ctr'
})

const getStatusType = (status: string) => {
  const map: Record<string, '' | 'success' | 'warning' | 'info'> = {
    running: 'warning',
    completed: 'success',
    draft: 'info'
  }
  return map[status] || ''
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    running: '进行中',
    completed: '已完成',
    draft: '草稿'
  }
  return map[status] || status
}

const getEffortType = (effort: string) => {
  const map: Record<string, 'success' | 'warning' | 'danger'> = {
    '低': 'success',
    '中': 'warning',
    '高': 'danger'
  }
  return map[effort] || 'info'
}

const addVariant = () => {
  newTest.variants.push({ name: '', description: '' })
}

const removeVariant = (index: number) => {
  newTest.variants.splice(index, 1)
}

const viewTestDetail = (row: any) => {
  console.log('View test detail:', row)
}

const stopTest = (row: any) => {
  row.status = 'completed'
  ElMessage.success('测试已停止')
}

const applyWinner = (row: any) => {
  ElMessage.success(`已应用胜出方案：${row.winner}`)
}

const viewCodeSuggestion = (row: any) => {
  console.log('View code suggestion:', row)
}

const applyCodeSuggestion = (row: any) => {
  ElMessage.success('代码优化已应用')
}

const createTest = () => {
  if (!newTest.name || !newTest.page) {
    ElMessage.warning('请填写完整信息')
    return
  }
  abTests.value.unshift({
    name: newTest.name,
    page: newTest.page,
    hypothesis: newTest.hypothesis,
    status: 'running',
    progress: 0,
    winner: null,
    improvement: null
  })
  showCreateTest.value = false
  ElMessage.success('A/B 测试创建成功')
}
</script>

<style scoped lang="scss">
.automation {
  .metric-cards {
    margin-bottom: 16px;

    .metric-card {
      text-align: center;

      .metric-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        color: #909399;
        margin-bottom: 8px;
      }

      .metric-value {
        font-size: 28px;
        font-weight: 600;
      }
    }
  }

  .section-card {
    margin-bottom: 16px;

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
  }

  .positive {
    color: #67c23a;
  }

  .negative {
    color: #f56c6c;
  }
}
</style>
