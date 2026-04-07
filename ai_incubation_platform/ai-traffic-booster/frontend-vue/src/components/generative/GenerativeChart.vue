<template>
  <div class="generative-chart" :style="{ height: config?.height || 300 }">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'

const props = defineProps<{
  data: any
  config?: {
    height?: number
    type?: string
    title?: string
  }
}>()

const chartRef = ref<HTMLElement>()
let chart: ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option = {
    title: props.config?.title ? { text: props.config.title } : undefined,
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    ...props.data
  }

  chart.setOption(option)
}

watch(() => props.data, () => {
  if (chart) {
    chart.setOption(props.data)
  }
}, { deep: true })

onMounted(() => {
  initChart()

  window.addEventListener('resize', () => {
    chart?.resize()
  })
})
</script>

<style scoped lang="scss">
.generative-chart {
  width: 100%;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .chart-container {
    width: 100%;
    height: 100%;
  }
}
</style>
