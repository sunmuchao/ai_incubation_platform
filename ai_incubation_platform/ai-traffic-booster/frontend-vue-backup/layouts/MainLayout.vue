<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '240px'" class="app-aside">
      <div class="logo">
        <el-icon :size="28" color="#409EFF"><DataLine /></el-icon>
        <span v-if="!appStore.sidebarCollapsed">AI Traffic Booster</span>
      </div>

      <el-menu
        :default-active="currentRoute"
        :collapse="appStore.sidebarCollapsed"
        background-color="#001529"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>仪表板</template>
        </el-menu-item>

        <el-menu-item index="/traffic">
          <el-icon><TrendCharts /></el-icon>
          <template #title>流量分析</template>
        </el-menu-item>

        <el-menu-item index="/seo">
          <el-icon><Search /></el-icon>
          <template #title>SEO 分析</template>
        </el-menu-item>

        <el-menu-item index="/competitor">
          <el-icon><Compare /></el-icon>
          <template #title>竞品分析</template>
        </el-menu-item>

        <el-menu-item index="/ai-assistant">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>AI 助手</template>
        </el-menu-item>

        <el-menu-item index="/automation">
          <el-icon><Finished /></el-icon>
          <template #title>自动化中心</template>
        </el-menu-item>

        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <template #title>
            告警管理
            <el-badge v-if="alertStore.unreadCount > 0" :value="alertStore.unreadCount" style="margin-left: 8px" />
          </template>
        </el-menu-item>

        <el-menu-item index="/data-sources">
          <el-icon><Database /></el-icon>
          <template #title>数据源管理</template>
        </el-menu-item>

        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <template #title>报告中心</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="app-header">
        <div class="header-left">
          <el-button text @click="appStore.toggleSidebar">
            <el-icon><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ currentRouteTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 告警快捷入口 -->
          <el-badge :value="alertStore.unreadCount" :hidden="alertStore.unreadCount === 0" class="header-icon">
            <el-button text @click="$router.push('/alerts')">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>

          <!-- 数据源状态 -->
          <el-tooltip content="数据源状态" placement="bottom">
            <el-button text @click="checkDataSources">
              <el-icon :class="{ 'pulse': dataSourceStatus !== 'healthy' }">
                <Connection v-if="dataSourceStatus === 'healthy'" />
                <Warning v-else />
              </el-icon>
            </el-button>
          </el-tooltip>

          <!-- 主题切换 -->
          <el-button text @click="toggleTheme">
            <el-icon><Moon v-if="appStore.currentTheme === 'light'" /><Sunny v-else /></el-icon>
          </el-button>

          <!-- 用户菜单 -->
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32">
                <el-icon><User /></el-icon>
              </el-avatar>
              <span class="username">Admin</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, useAlertStore, useDataSourceStore } from '@/store'

const route = useRoute()
const appStore = useAppStore()
const alertStore = useAlertStore()
const dataSourceStore = useDataSourceStore()

const currentRoute = computed(() => route.path)
const currentRouteTitle = computed(() => route.meta.title as string || '仪表板')
const dataSourceStatus = ref('healthy')

const checkDataSources = async () => {
  await dataSourceStore.fetchHealth()
  dataSourceStatus.value = dataSourceStore.healthStatus?.overall || 'healthy'
}

const toggleTheme = () => {
  const newTheme = appStore.currentTheme === 'light' ? 'dark' : 'light'
  appStore.setTheme(newTheme)
  document.documentElement.classList.toggle('dark', newTheme === 'dark')
}

onMounted(() => {
  alertStore.fetchAlerts()
  checkDataSources()
})
</script>

<style scoped lang="scss">
.app-container {
  height: 100vh;
}

.app-aside {
  background-color: #001529;
  transition: width 0.3s;
  overflow: hidden;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: #fff;
    font-size: 18px;
    font-weight: 600;
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }

  :deep(.el-menu) {
    border-right: none;

    .el-menu-item {
      &:hover {
        background-color: rgba(255,255,255,0.08) !important;
      }

      &.is-active {
        background-color: #409EFF !important;
      }
    }
  }
}

.app-header {
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;

    .header-icon {
      margin-right: 8px;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;

      .username {
        font-size: 14px;
        color: #333;
      }
    }
  }
}

.app-main {
  background-color: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}

.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
