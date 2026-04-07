<template>
  <div class="data-sources">
    <!-- 数据源概览 -->
    <el-row :gutter="16" class="overview-cards">
      <el-col :span="6">
        <el-card class="source-card">
          <div class="source-header">
            <el-icon :size="24" color="#67c23a"><CircleCheck /></el-icon>
            <span>健康状态</span>
          </div>
          <div class="source-value">全部正常</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="source-card">
          <div class="source-header">
            <el-icon :size="24" color="#409EFF"><Database /></el-icon>
            <span>数据源数量</span>
          </div>
          <div class="source-value">{{ dataSources.length }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="source-card">
          <div class="source-header">
            <el-icon :size="24" color="#e6a23c"><Clock /></el-icon>
            <span>最后同步</span>
          </div>
          <div class="source-value">10 分钟前</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="source-card">
          <div class="source-header">
            <el-icon :size="24" color="#909399"><DataLine /></el-icon>
            <span>API 调用</span>
          </div>
          <div class="source-value">1,248 / 5,000</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据源列表 -->
    <el-card class="sources-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">数据源管理</span>
          <el-button type="primary" @click="showAddSource = true">
            <el-icon><Plus /></el-icon>
            添加数据源
          </el-button>
        </div>
      </template>

      <el-table :data="dataSources" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'healthy' ? 'success' : 'danger'">
              {{ row.status === 'healthy' ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_sync" label="最后同步" width="160" />
        <el-table-column prop="quota" label="API 配额" width="150">
          <template #default="{ row }">
            <el-progress :percentage="(row.quota_used / row.quota_limit) * 100"
                         :status="(row.quota_used / row.quota_limit) > 0.8 ? 'warning' : ''" />
            <span style="font-size: 12px; color: #909399">
              {{ row.quota_used }} / {{ row.quota_limit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sync_frequency" label="同步频率" width="120" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" text @click="syncSource(row)">
              <el-icon><Refresh /></el-icon>
              同步
            </el-button>
            <el-button size="small" text @click="editSource(row)">
              编辑
            </el-button>
            <el-button size="small" text type="danger" @click="deleteSource(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 配额监控 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">API 配额使用</span>
          </template>
          <div class="quota-list">
            <div v-for="source in quotaSources" :key="source.name" class="quota-item">
              <div class="quota-header">
                <span>{{ source.name }}</span>
                <span class="quota-value">{{ source.used }} / {{ source.limit }}</span>
              </div>
              <el-progress :percentage="(source.used / source.limit) * 100"
                           :status="(source.used / source.limit) > 0.8 ? 'warning' : ''" />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span class="card-title">同步历史</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in syncHistory"
              :key="index"
              :type="item.status === 'success' ? 'success' : 'danger'"
              :timestamp="item.time"
            >
              {{ item.source }} - {{ item.status === 'success' ? '同步成功' : '同步失败' }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加数据源对话框 -->
    <el-dialog v-model="showAddSource" title="添加数据源" width="600px">
      <el-form :model="newSource" label-width="100px">
        <el-form-item label="数据源类型" required>
          <el-select v-model="newSource.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="Google Analytics 4" value="ga4" />
            <el-option label="Google Search Console" value="gsc" />
            <el-option label="Ahrefs" value="ahrefs" />
            <el-option label="SEMrush" value="semrush" />
            <el-option label="自定义 API" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="newSource.name" placeholder="例如：主站 GA4" />
        </el-form-item>
        <el-form-item label="认证信息" required>
          <el-input v-model="newSource.credentials" type="password" placeholder="API Key / Credentials" />
        </el-form-item>
        <el-form-item label="同步频率">
          <el-select v-model="newSource.sync_frequency" style="width: 100%">
            <el-option label="每小时" value="hourly" />
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSource = false">取消</el-button>
        <el-button type="primary" @click="addSource">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { dataSourcesApi } from '@/api'

const dataSources = ref<any[]>([
  { name: 'Google Analytics 4', type: '分析工具', status: 'healthy', last_sync: '2024-01-15 10:00:00', quota_used: 850, quota_limit: 5000, sync_frequency: '每小时' },
  { name: 'Search Console', type: 'SEO 工具', status: 'healthy', last_sync: '2024-01-15 09:30:00', quota_used: 120, quota_limit: 2000, sync_frequency: '每天' },
  { name: 'Ahrefs API', type: 'SEO 工具', status: 'healthy', last_sync: '2024-01-15 08:00:00', quota_used: 280, quota_limit: 1000, sync_frequency: '每天' },
  { name: 'SEMrush API', type: 'SEO 工具', status: 'error', last_sync: '2024-01-14 18:00:00', quota_used: 450, quota_limit: 500, sync_frequency: '每天' },
])

const quotaSources = ref([
  { name: 'Google Analytics 4', used: 850, limit: 5000 },
  { name: 'Search Console', used: 120, limit: 2000 },
  { name: 'Ahrefs', used: 280, limit: 1000 },
  { name: 'SEMrush', used: 450, limit: 500 },
])

const syncHistory = ref([
  { source: 'GA4', time: '2024-01-15 10:00:00', status: 'success' },
  { source: 'Search Console', time: '2024-01-15 09:30:00', status: 'success' },
  { source: 'Ahrefs', time: '2024-01-15 08:00:00', status: 'success' },
  { source: 'SEMrush', time: '2024-01-14 18:00:00', status: 'error' },
])

const showAddSource = ref(false)
const newSource = reactive({
  type: '',
  name: '',
  credentials: '',
  sync_frequency: 'daily'
})

const syncSource = async (row: any) => {
  ElMessage.info(`开始同步 ${row.name}...`)
  // TODO: 调用同步 API
}

const editSource = (row: any) => {
  console.log('Edit source:', row)
}

const deleteSource = (row: any) => {
  dataSources.value = dataSources.value.filter(s => s.name !== row.name)
  ElMessage.success('已删除数据源')
}

const addSource = () => {
  if (!newSource.name || !newSource.type) {
    ElMessage.warning('请填写完整信息')
    return
  }
  dataSources.value.push({
    name: newSource.name,
    type: newSource.type,
    status: 'healthy',
    last_sync: '从未',
    quota_used: 0,
    quota_limit: 1000,
    sync_frequency: newSource.sync_frequency
  })
  showAddSource.value = false
  ElMessage.success('数据源添加成功')
}
</script>

<style scoped lang="scss">
.data-sources {
  .overview-cards {
    margin-bottom: 16px;

    .source-card {
      .source-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #909399;
        margin-bottom: 8px;
      }

      .source-value {
        font-size: 24px;
        font-weight: 600;
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

  .quota-list {
    .quota-item {
      margin-bottom: 16px;

      .quota-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;
      }

      .quota-value {
        color: #909399;
      }
    }
  }
}
</style>
