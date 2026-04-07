<template>
  <div class="workflow-progress">
    <div class="progress-header">
      <span class="title">{{ data.title || '工作流执行中' }}</span>
      <el-tag :type="statusType">{{ statusText }}</el-tag>
    </div>

    <div class="steps-container">
      <div
        v-for="(step, index) in data.steps"
        :key="index"
        class="step-item"
        :class="getStepClass(index)"
      >
        <div class="step-indicator">
          <el-icon v-if="step.status === 'completed'"><CircleCheck /></el-icon>
          <el-icon v-else-if="step.status === 'running'"><Loading /></el-icon>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="step-content">
          <div class="step-name">{{ step.name }}</div>
          <div v-if="step.description" class="step-desc">{{ step.description }}</div>
          <div v-if="step.progress !== undefined" class="step-progress">
            <el-progress :percentage="step.progress" :stroke-width="4" :show-text="false" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: {
    title?: string
    steps: Array<{
      name: string
      description?: string
      status: 'pending' | 'running' | 'completed'
      progress?: number
    }>
    overallStatus?: 'pending' | 'running' | 'completed' | 'failed'
  }
}>()

const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '执行失败'
  }
  return map[props.data.overallStatus || 'running']
})

const statusType = computed(() => {
  const map: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[props.data.overallStatus || 'warning']
})

const getStepClass = (index: number) => {
  const step = props.data.steps[index]
  return {
    completed: step.status === 'completed',
    running: step.status === 'running',
    pending: step.status === 'pending'
  }
}
</script>

<style scoped lang="scss">
.workflow-progress {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  .steps-container {
    .step-item {
      display: flex;
      gap: 16px;
      padding: 16px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      &.completed .step-indicator {
        background: #67c23a;
        color: #fff;
      }

      &.running .step-indicator {
        background: #409EFF;
        color: #fff;
        animation: pulse 1.5s infinite;
      }

      .step-indicator {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #f0f2f5;
        color: #909399;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 14px;
        font-weight: 600;
      }

      .step-content {
        flex: 1;

        .step-name {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 4px;
        }

        .step-desc {
          font-size: 12px;
          color: #909399;
          margin-bottom: 8px;
        }

        .step-progress {
          width: 100%;
        }
      }
    }
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(64, 158, 255, 0);
  }
}
</style>
