<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="appStore.sidebarCollapsed ? '72px' : '260px'" class="app-aside">
      <div class="logo">
        <div class="logo-icon">
          <el-icon :size="24"><Cpu /></el-icon>
        </div>
        <transition name="fade" mode="out-in">
          <div v-if="!appStore.sidebarCollapsed" class="logo-text-wrapper">
            <span class="logo-text">AI Traffic</span>
            <span class="logo-sub">Booster Platform</span>
          </div>
        </transition>
      </div>

      <el-menu
        :default-active="currentRoute"
        :collapse="appStore.sidebarCollapsed"
        class="app-menu"
        router
      >
        <el-menu-item index="/">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 对话</span>
        </el-menu-item>

        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表板</span>
        </el-menu-item>

        <el-menu-item index="/agents">
          <el-icon><Grid /></el-icon>
          <span>Agent 中心</span>
        </el-menu-item>

        <el-menu-item index="/traffic">
          <el-icon><TrendCharts /></el-icon>
          <span>流量分析</span>
        </el-menu-item>

        <el-menu-item index="/seo">
          <el-icon><Search /></el-icon>
          <span>SEO 分析</span>
        </el-menu-item>

        <el-menu-item index="/competitor">
          <el-icon><Compare /></el-icon>
          <span>竞品分析</span>
        </el-menu-item>

        <el-menu-item index="/automation">
          <el-icon><Finished /></el-icon>
          <span>自动化中心</span>
        </el-menu-item>

        <el-menu-item index="/alerts">
          <el-icon><Bell /></el-icon>
          <span>告警管理</span>
          <el-badge v-if="alertStore.unreadCount > 0" :value="alertStore.unreadCount" class="menu-badge" />
        </el-menu-item>

        <el-menu-item index="/data-sources">
          <el-icon><Database /></el-icon>
          <span>数据源管理</span>
        </el-menu-item>

        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <span>报告中心</span>
        </el-menu-item>
      </el-menu>

      <!-- AI 状态指示器 -->
      <div class="ai-status">
        <div class="status-dot" :class="{ online: aiStatus.online }"></div>
        <transition name="fade" mode="out-in">
          <span v-if="!appStore.sidebarCollapsed" class="status-text">
            {{ aiStatus.online ? 'AI 引擎在线' : 'AI 引擎离线' }}
          </span>
        </transition>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header class="app-header">
        <div class="header-left">
          <el-button class="icon-btn" text @click="appStore.toggleSidebar">
            <el-icon><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <div class="breadcrumb">
            <h1 class="page-title">{{ currentRouteTitle }}</h1>
          </div>
        </div>

        <div class="header-right">
          <!-- 全局搜索 -->
          <div class="search-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索功能、数据或问 AI..."
              @keydown.meta.enter="handleGlobalSearch"
            />
            <kbd class="search-shortcut">
              <span>⌘</span><span>K</span>
            </kbd>
          </div>

          <!-- 告警 -->
          <el-badge :value="alertStore.unreadCount" :hidden="alertStore.unreadCount === 0" class="header-action">
            <el-button class="icon-btn" text @click="$router.push('/alerts')">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>

          <!-- 数据源状态 -->
          <el-tooltip content="数据源状态" placement="bottom">
            <el-button class="icon-btn" text @click="checkDataSources">
              <el-icon :class="{ 'pulse': dataSourceStatus !== 'healthy' }">
                <Connection v-if="dataSourceStatus === 'healthy'" />
                <Warning v-else />
              </el-icon>
            </el-button>
          </el-tooltip>

          <!-- 主题切换 -->
          <el-button class="icon-btn" text @click="toggleTheme">
            <el-icon><Moon v-if="appStore.currentTheme === 'light'" /><Sunny v-else /></el-icon>
          </el-button>

          <!-- 用户菜单 -->
          <el-dropdown trigger="click">
            <div class="user-menu">
              <div class="avatar">
                <el-icon><User /></el-icon>
              </div>
              <span class="username">Admin</span>
            </div>
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
import { useRoute, useRouter } from 'vue-router'
import { useAppStore, useAlertStore, useDataSourceStore } from '@/store'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const alertStore = useAlertStore()
const dataSourceStore = useDataSourceStore()

const currentRoute = computed(() => route.path)
const currentRouteTitle = computed(() => route.meta.title as string || 'AI 对话')
const dataSourceStatus = ref('healthy')
const searchQuery = ref('')
const aiStatus = ref({ online: true })

const checkDataSources = async () => {
  await dataSourceStore.fetchHealth()
  dataSourceStatus.value = dataSourceStore.healthStatus?.overall || 'healthy'
}

const toggleTheme = () => {
  const newTheme = appStore.currentTheme === 'light' ? 'dark' : 'light'
  appStore.setTheme(newTheme)
  document.documentElement.classList.toggle('dark', newTheme === 'dark')
}

const handleGlobalSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ path: '/', query: { q: searchQuery.value } })
  }
}

// 键盘快捷键
onMounted(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      const searchInput = document.querySelector('.search-box input') as HTMLInputElement
      searchInput?.focus()
    }
  }
  window.addEventListener('keydown', handleKeyDown)

  alertStore.fetchAlerts()
  checkDataSources()
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.app-container {
  height: 100vh;
  overflow: hidden;
}

.app-aside {
  background: $slate-900;
  transition: width $transition-slow $ease-out;
  display: flex;
  flex-direction: column;
  border-right: $border-dark-subtle;

  .logo {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-3;
    border-bottom: $border-dark-subtle;
    padding: 0 $spacing-4;

    .logo-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, $indigo-500 0%, $indigo-600 100%);
      border-radius: $radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      flex-shrink: 0;
      box-shadow: $glow-indigo;
    }

    .logo-text-wrapper {
      display: flex;
      flex-direction: column;
      white-space: nowrap;
      overflow: hidden;

      .logo-text {
        color: #fff;
        font-size: $font-size-lg;
        font-weight: $font-weight-bold;
        letter-spacing: -0.02em;
      }

      .logo-sub {
        font-size: $font-size-xs;
        color: $slate-400;
        font-weight: $font-weight-normal;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }
    }
  }

  .app-menu {
    flex: 1;
    border-right: none;
    background: transparent;
    padding: $spacing-3;
    overflow-y: auto;

    .el-menu-item {
      height: 44px;
      margin-bottom: $spacing-1;
      border-radius: $radius-md;
      color: $slate-400;

      &:hover {
        background-color: rgba(255, 255, 255, 0.06) !important;
        color: #fff !important;
      }

      &.is-active {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, transparent 100%) !important;
        border-left: 3px solid $indigo-500;
        color: #fff !important;
      }

      .el-icon {
        margin-right: $spacing-3;
      }

      .menu-badge {
        margin-left: auto;
      }
    }
  }

  .ai-status {
    padding: $spacing-4;
    border-top: $border-dark-subtle;
    display: flex;
    align-items: center;
    gap: $spacing-3;
    color: $slate-400;
    font-size: $font-size-sm;

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: $slate-500;
      flex-shrink: 0;

      &.online {
        background: $success;
        box-shadow: 0 0 8px rgba($success, 0.5);
      }
    }

    .status-text {
      white-space: nowrap;
      overflow: hidden;
    }
  }
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, $bg-secondary 0%, $bg-primary 100%);
}

.app-header {
  height: 64px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: $border-subtle;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-6;
  position: sticky;
  top: 0;
  z-index: $z-sticky;

  .header-left {
    display: flex;
    align-items: center;
    gap: $spacing-4;

    .icon-btn {
      width: 36px;
      height: 36px;
      border-radius: $radius-md;
      color: $slate-500;

      &:hover {
        background: $slate-100;
        color: $slate-700;
      }
    }

    .breadcrumb {
      .page-title {
        font-size: $font-size-xl;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        margin: 0;
        letter-spacing: -0.01em;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-3;

    .search-box {
      position: relative;
      display: flex;
      align-items: center;

      .search-icon {
        position: absolute;
        left: $spacing-3;
        color: $slate-400;
        pointer-events: none;
      }

      input {
        width: 320px;
        height: 40px;
        padding: 0 $spacing-3 0 40px;
        border: $border-subtle;
        border-radius: $radius-lg;
        background: $bg-secondary;
        font-size: $font-size-sm;
        color: $text-primary;
        transition: all $transition-base $ease-out;

        &::placeholder {
          color: $slate-400;
        }

        &:hover {
          border-color: $border-medium;
        }

        &:focus {
          outline: none;
          border-color: $indigo-500;
          background: #fff;
          box-shadow: 0 0 0 3px rgba($indigo-500, 0.1);
        }
      }

      .search-shortcut {
        position: absolute;
        right: $spacing-2;
        display: flex;
        gap: 2px;

        span {
          background: $slate-100;
          border-radius: $radius-sm;
          padding: 2px 6px;
          font-size: 10px;
          font-family: $font-family;
          color: $slate-500;
          border: 1px solid $slate-200;
        }
      }
    }

    .header-action {
      .icon-btn {
        width: 36px;
        height: 36px;
        border-radius: $radius-md;
        color: $slate-500;

        &:hover {
          background: $slate-100;
          color: $slate-700;
        }
      }
    }

    .user-menu {
      display: flex;
      align-items: center;
      gap: $spacing-2;
      cursor: pointer;
      padding: $spacing-2 $spacing-3;
      border-radius: $radius-lg;
      transition: all $transition-base $ease-out;

      &:hover {
        background: $slate-100;
      }

      .avatar {
        width: 32px;
        height: 32px;
        border-radius: $radius-md;
        background: linear-gradient(135deg, $indigo-500 0%, $indigo-600 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
      }

      .username {
        font-size: $font-size-sm;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }
    }
  }
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 0;
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
  transition: opacity $transition-base ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
