<template>
  <div class="insight-card-component" :class="data.priority">
    <div class="insight-header">
      <div class="insight-icon" :style="{ background: iconColor }">
        <el-icon :size="20"><component :is="data.icon || 'Lightbulb'" /></el-icon>
      </div>
      <div class="insight-title-section">
        <div class="insight-title">{{ data.title }}</div>
        <el-tag :type="priorityType" size="small" round>{{ priorityText }}</el-tag>
      </div>
    </div>

    <div class="insight-body">
      <p class="insight-content">{{ data.content }}</p>

      <div v-if="data.metrics?.length" class="insight-metrics">
        <div
          v-for="(metric, index) in data.metrics"
          :key="index"
          class="metric-item"
        >
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value" :class="metric.trend">
            {{ metric.value }}
            <el-icon v-if="metric.trend === 'up'"><Top /></el-icon>
            <el-icon v-else-if="metric.trend === 'down'"><Bottom /></el-icon>
          </div>
        </div>
      </div>

      <div v-if="data.suggestions?.length" class="insight-suggestions">
        <strong>建议：</strong>
        <ul>
          <li v-for="(suggestion, index) in data.suggestions" :key="index">
            {{ suggestion }}
          </li>
        </ul>
      </div>
    </div>

    <div v-if="data.actions?.length" class="insight-footer">
      <el-button
        v-for="(action, index) in data.actions"
        :key="index"
        :type="action.type || 'default'"
        size="small"
        round
        @click="$emit('action', action)"
      >
        {{ action.label }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: {
    title: string
    content: string
    priority?: 'low' | 'normal' | 'high' | 'critical'
    icon?: string
    metrics?: Array<{
      label: string
      value: string | number
      trend?: 'up' | 'down' | 'neutral'
    }>
    suggestions?: string[]
    actions?: Array<{
      label: string
      type?: 'primary' | 'success' | 'warning' | 'danger' | 'default'
      action?: string
    }>
  }
}>()

defineEmits<{
  (e: 'action', action: any): void
}>()

const priorityType = computed(() => {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    low: 'info',
    normal: 'success',
    high: 'warning',
    critical: 'danger'
  }
  return map[props.data.priority || 'normal']
})

const priorityText = computed(() => {
  const map: Record<string, string> = {
    low: '低优先级',
    normal: '普通',
    high: '高优先级',
    critical: '紧急'
  }
  return map[props.data.priority || '普通']
})

const iconColor = computed(() => {
  const map: Record<string, string> = {
    low: '#64748b',
    normal: '#22c55e',
    high: '#f59e0b',
    critical: '#ef4444'
  }
  return map[props.data.priority || 'normal']
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.insight-card-component {
  background: #fff;
  border-radius: $radius-lg;
  padding: $spacing-5;
  box-shadow: $shadow-sm;
  border: $border-subtle;
  border-left: 4px solid transparent;
  transition: all $transition-base $ease-out;

  &:hover {
    box-shadow: $shadow-md;
  }

  &.critical {
    border-left-color: #ef4444;
    background: linear-gradient(to right, rgba(239, 68, 68, 0.04), #fff);
  }

  &.high {
    border-left-color: #f59e0b;
    background: linear-gradient(to right, rgba(245, 158, 11, 0.04), #fff);
  }

  &.normal {
    border-left-color: #22c55e;
  }

  &.low {
    border-left-color: #64748b;
  }

  .insight-header {
    display: flex;
    align-items: center;
    gap: $spacing-4;
    margin-bottom: $spacing-4;

    .insight-icon {
      width: 44px;
      height: 44px;
      border-radius: $radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      flex-shrink: 0;
      box-shadow: $shadow-md;
    }

    .insight-title-section {
      flex: 1;
      display: flex;
      justify-content: space-between;
      align-items: center;

      .insight-title {
        font-size: $font-size-base;
        font-weight: $font-weight-semibold;
        color: $text-primary;
      }
    }
  }

  .insight-body {
    .insight-content {
      font-size: $font-size-sm;
      color: $text-secondary;
      line-height: $line-height-relaxed;
      margin-bottom: $spacing-4;
    }

    .insight-metrics {
      display: flex;
      gap: $spacing-3;
      margin-bottom: $spacing-4;
      flex-wrap: wrap;

      .metric-item {
        background: $bg-secondary;
        padding: $spacing-3 $spacing-4;
        border-radius: $radius-md;
        border: $border-subtle;

        .metric-label {
          font-size: $font-size-xs;
          color: $text-tertiary;
          margin-bottom: 4px;
          display: block;
        }

        .metric-value {
          font-size: $font-size-lg;
          font-weight: $font-weight-semibold;
          color: $text-primary;
          display: flex;
          align-items: center;
          gap: 4px;

          &.up {
            color: $success;
          }

          &.down {
            color: $error;
          }
        }
      }
    }

    .insight-suggestions {
      font-size: $font-size-sm;
      color: $text-secondary;
      background: $bg-secondary;
      padding: $spacing-3 $spacing-4;
      border-radius: $radius-md;
      border: $border-subtle;

      strong {
        color: $text-primary;
        font-weight: $font-weight-semibold;
      }

      ul {
        margin: $spacing-2 0 0 0;
        padding-left: $spacing-4;

        li {
          margin: 4px 0;
          line-height: $line-height-relaxed;
          color: $text-secondary;
        }
      }
    }
  }

  .insight-footer {
    margin-top: $spacing-4;
    padding-top: $spacing-3;
    border-top: $border-subtle;
    display: flex;
    gap: $spacing-2;
    flex-wrap: wrap;
  }
}
</style>
