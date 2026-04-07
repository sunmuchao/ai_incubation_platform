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
  document.documentElement.classList.toggle('dark', savedTheme === 'dark')

  // 初始化用户 ID
  if (!localStorage.getItem('user_id')) {
    localStorage.setItem('user_id', `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }
})
</script>

<style>
/* 全局基础样式已移至 assets/styles.scss */
</style>
