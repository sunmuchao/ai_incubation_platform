<template>
  <div class="metric-cards-container">
    <el-row :gutter="16">
      <el-col
        v-for="(metric, index) in data.metrics"
        :key="index"
        :span="data.span || 6"
      >
        <div class="metric-card" :style="{ background: metric.color || getDefaultColor(index) }">
          <div class="metric-icon">
            <el-icon :size="24"><component :is="metric.icon || 'DataLine'" /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value">{{ formatValue(metric.value) }}</div>
            <div class="metric-trend" :class="metric.trend">
              <el-icon><Top v-if="metric.trend === 'up'" /><Bottom v-else /></el-icon>
              <span>{{ metric.change }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  data: {
    metrics: Array<{
      label: string
      value: number | string
      trend?: 'up' | 'down'
      change?: string
      icon?: string
      color?: string
    }>
    span?: number
  }
}>()

// 使用新的 Monochromatic 配色方案
const colors = [
  'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
  'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
  'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
]

const getDefaultColor = (index: number) => colors[index % colors.length]

const formatValue = (value: number | string) => {
  if (typeof value === 'number') {
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
    if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
    return value.toString()
  }
  return value
}
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.metric-cards-container {
  .metric-card {
    padding: $spacing-5;
    border-radius: $radius-lg;
    color: #fff;
    display: flex;
    align-items: center;
    gap: $spacing-4;
    transition: all $transition-base $ease-out;
    box-shadow: $shadow-sm;
    border: 1px solid rgba(255, 255, 255, 0.1);

    &:hover {
      transform: translateY(-4px);
      box-shadow: $shadow-lg;
    }

    .metric-icon {
      width: 52px;
      height: 52px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: $radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      backdrop-filter: blur(10px);
    }

    .metric-info {
      flex: 1;
      min-width: 0;

      .metric-label {
        font-size: $font-size-sm;
        opacity: 0.85;
        margin-bottom: $spacing-1;
        font-weight: $font-weight-medium;
      }

      .metric-value {
        font-size: $font-size-2xl;
        font-weight: $font-weight-bold;
        margin-bottom: $spacing-1;
        letter-spacing: -0.02em;
      }

      .metric-trend {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: $font-size-xs;
        font-weight: $font-weight-medium;

        &.up {
          color: rgba(255, 255, 255, 0.95);
        }

        &.down {
          color: rgba(255, 255, 255, 0.7);
        }
      }
    }
  }
}
</style>
