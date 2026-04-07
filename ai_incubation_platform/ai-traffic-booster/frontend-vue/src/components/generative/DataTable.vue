<template>
  <div class="data-table-component">
    <el-table :data="data.rows || []" style="width: 100%" :height="config?.height">
      <el-table-column
        v-for="(column, index) in data.columns"
        :key="index"
        :prop="column.key"
        :label="column.label"
        :width="column.width"
      >
        <template #default="{ row }">
          <span v-if="column.format === 'percent'">{{ (row[column.key] * 100).toFixed(1) }}%</span>
          <el-tag v-else-if="column.type === 'tag'" :type="getColumnTagType(row[column.key], column)">
            {{ row[column.key] }}
          </el-tag>
          <span v-else>{{ row[column.key] }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  data: {
    columns: Array<{
      key: string
      label: string
      width?: number | string
      type?: string
      format?: string
    }>
    rows: any[]
  }
  config?: {
    height?: number
  }
}>()

const getColumnTagType = (value: any, column: any) => {
  if (column.key.includes('status') || column.key.includes('state')) {
    const map: Record<string, string> = {
      success: 'success',
      completed: 'success',
      active: 'success',
      warning: 'warning',
      pending: 'warning',
      error: 'danger',
      failed: 'danger'
    }
    return map[String(value).toLowerCase()] || 'info'
  }
  return 'info'
}
</script>

<style scoped lang="scss">
.data-table-component {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>
