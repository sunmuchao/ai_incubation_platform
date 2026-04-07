<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/store'

const appStore = useAppStore()

onMounted(() => {
  // 初始化主题
  const savedTheme = localStorage.getItem('theme') || 'light'
  appStore.setTheme(savedTheme)

  // 初始化用户 ID
  if (!localStorage.getItem('user_id')) {
    localStorage.setItem('user_id', `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

#app {
  background-color: #f5f7fa;
}
</style>
