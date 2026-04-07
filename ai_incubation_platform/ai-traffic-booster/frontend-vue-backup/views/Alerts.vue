<template>
  <div class="alerts">
    <!-- 告警统计卡片 -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :span="6">
        <el-card class="metric-card critical">
          <div class="metric-header">严重告警</div>
          <div class="metric-value">{{ alertStats.critical }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card warning">
          <div class="metric-header">警告</div>
          <div class="metric-value">{{ alertStats.warning }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card info">
          <div class="metric-header">提示</div>
          <div class="metric-value">{{ alertStats.info }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">已确认</div>
          <div class="metric-value">{{ alertStats.acknowledged }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选和操作 -->
    <el-card class="filter-card">
      <el-radio-group v-model="filterSeverity" @change="filterAlerts">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="critical">严重</el-radio-button>
        <el-radio-button label="warning">警告</el-radio-button>
        <el-radio-button label="info">提示</el-radio-button>
      </el-radio-group>
      <el-radio-group v-model="filterStatus" @change="filterAlerts" style="margin-left: 16px">
        <el-radio-button label="all">全部状态</el-radio-button>
        <el-radio-button label="active">未处理</el-radio-button>
        <el-radio-button label="acknowledged">已确认</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="showCreateAlert = true" style="margin-left: 16px">
        <el-icon><Plus /></el-icon>
        创建告警规则
      </el-button>
    </el-card>

    <!-- 告警列表 -->
    <el-card>
      <el-table :data="filteredAlerts" stripe>
        <el-table-column prop="severity" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="large">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="created_at" label="触发时间" width="160" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.acknowledged ? 'success' : 'danger'">
              {{ row.acknowledged ? '已确认' : '未处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text @click="acknowledgeAlert(row)" v-if="!row.acknowledged">
              确认
            </el-button>
            <el-button size="small" text @click="viewAlertDetail(row)">
              详情
            </el-button>
            <el-button size="small" text type="danger" @click="deleteAlert(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建告警规则对话框 -->
    <el-dialog v-model="showCreateAlert" title="创建告警规则" width="600px">
      <el-form :model="newAlert" label-width="100px">
        <el-form-item label="规则名称" required>
          <el-input v-model="newAlert.name" placeholder="例如：流量异常告警" />
        </el-form-item>
        <el-form-item label="监控指标" required>
          <el-select v-model="newAlert.metric" placeholder="请选择指标" style="width: 100%">
            <el-option label="访客数" value="visitors" />
            <el-option label="页面浏览量" value="page_views" />
            <el-option label="跳出率" value="bounce_rate" />
            <el-option label="转化率" value="conversion_rate" />
            <el-option label="关键词排名" value="keyword_rank" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件" required>
          <el-row :gutter="8">
            <el-col :span="8">
              <el-select v-model="newAlert.condition" placeholder="条件" style="width: 100%">
                <el-option label="大于" value=">" />
                <el-option label="小于" value="<" />
                <el-option label="变化超过" value="change" />
                <el-option label="异常检测" value="anomaly" />
              </el-select>
            </el-col>
            <el-col :span="16">
              <el-input-number v-model="newAlert.threshold" :precision="2" :step="1" style="width: 100%" />
            </el-col>
          </el-row>
        </el-form-item>
        <el-form-item label="通知渠道" required>
          <el-checkbox-group v-model="newAlert.notification_channels">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="slack">Slack</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
            <el-checkbox label="dingtalk">钉钉</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateAlert = false">取消</el-button>
        <el-button type="primary" @click="createAlert">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { alertsApi } from '@/api'

const alertStats = reactive({
  critical: 2,
  warning: 5,
  info: 8,
  acknowledged: 15
})

const alerts = ref<any[]>([
  {
    alert_id: '1',
    severity: 'critical',
    type: '流量异常',
    title: '流量异常下跌 25%',
    description: '今日访客数较昨日下跌 25%，超出正常波动范围',
    created_at: '2024-01-15 10:30:00',
    acknowledged: false
  },
  {
    alert_id: '2',
    severity: 'critical',
    type: 'SEO 告警',
    title: '核心关键词排名下降',
    description: '关键词 "SEO tools" 从第 3 名下降至第 8 名',
    created_at: '2024-01-15 09:15:00',
    acknowledged: false
  },
  {
    alert_id: '3',
    severity: 'warning',
    type: '性能告警',
    title: '页面加载速度过慢',
    description: '核心页面 LCP 超过 4 秒，影响用户体验和 SEO',
    created_at: '2024-01-14 16:45:00',
    acknowledged: true
  },
  {
    alert_id: '4',
    severity: 'warning',
    type: '竞品监控',
    title: '竞品流量接近超越',
    description: 'Competitor A 本周流量增长 15%，差距正在缩小',
    created_at: '2024-01-14 14:20:00',
    acknowledged: false
  },
  {
    alert_id: '5',
    severity: 'info',
    type: '数据同步',
    title: 'GA4 数据同步延迟',
    description: 'Google Analytics 4 数据同步出现延迟，当前延迟约 2 小时',
    created_at: '2024-01-14 11:00:00',
    acknowledged: true
  },
])

const filterSeverity = ref('all')
const filterStatus = ref('all')
const showCreateAlert = ref(false)

const newAlert = reactive({
  name: '',
  metric: '',
  condition: '>',
  threshold: 0,
  notification_channels: ['email']
})

const filteredAlerts = computed(() => {
  return alerts.value.filter(alert => {
    if (filterSeverity.value !== 'all' && alert.severity !== filterSeverity.value) return false
    if (filterStatus.value === 'active' && alert.acknowledged) return false
    if (filterStatus.value === 'acknowledged' && !alert.acknowledged) return false
    return true
  })
})

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

const filterAlerts = () => {
  // 筛选逻辑由 computed 处理
}

const acknowledgeAlert = async (row: any) => {
  row.acknowledged = true
  alertStats.acknowledged++
  alertStats[row.severity]--
  ElMessage.success('已确认告警')
}

const viewAlertDetail = (row: any) => {
  console.log('View alert detail:', row)
}

const deleteAlert = (row: any) => {
  alerts.value = alerts.value.filter(a => a.alert_id !== row.alert_id)
  ElMessage.success('已删除告警')
}

const createAlert = () => {
  if (!newAlert.name || !newAlert.metric) {
    ElMessage.warning('请填写完整信息')
    return
  }
  alerts.value.unshift({
    alert_id: String(Date.now()),
    severity: 'info',
    type: newAlert.metric,
    title: newAlert.name,
    description: `当 ${newAlert.metric} ${newAlert.condition} ${newAlert.threshold} 时触发`,
    created_at: new Date().toLocaleString('zh-CN'),
    acknowledged: false
  })
  showCreateAlert.value = false
  ElMessage.success('告警规则创建成功')
}
</script>

<style scoped lang="scss">
.alerts {
  .metric-cards {
    margin-bottom: 16px;

    .metric-card {
      text-align: center;

      .metric-header {
        color: #909399;
        font-size: 14px;
        margin-bottom: 8px;
      }

      .metric-value {
        font-size: 32px;
        font-weight: 600;
      }

      &.critical .metric-value {
        color: #f56c6c;
      }

      &.warning .metric-value {
        color: #e6a23c;
      }

      &.info .metric-value {
        color: #909399;
      }
    }
  }

  .filter-card {
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
}
</style>
