<template>
  <div class="ai-chat-home">
    <!-- 主聊天区域 -->
    <div class="chat-section">
      <!-- AI 助手头部 -->
      <div class="ai-header">
        <div class="ai-avatar-pulse">
          <el-avatar :size="64" class="ai-avatar">
            <el-icon :size="32"><Cpu /></el-icon>
          </el-avatar>
          <div class="pulse-ring"></div>
        </div>
        <div class="ai-intro">
          <h2>AI 流量增长顾问</h2>
          <p>您的专属 AI Native 增长团队 - 我可以帮助您分析流量、发现机会、执行优化</p>
          <div class="ai-status">
            <el-tag :type="aiStatus.available ? 'success' : 'warning'" size="small">
              <el-icon><Connection /></el-icon>
              {{ aiStatus.available ? 'AI 在线' : 'AI 离线' }}
            </el-tag>
            <span class="confidence-info">
              自主执行阈值：{{ aiConfig.autoThreshold * 100 }}%
            </span>
          </div>
        </div>
      </div>

      <!-- 消息流区域 -->
      <div class="message-stream" ref="messageStreamRef">
        <!-- 欢迎界面 - 当没有对话时显示 -->
        <div v-if="messages.length === 0" class="welcome-cards">
          <el-row :gutter="20">
            <el-col :span="8" v-for="(card, index) in capabilityCards" :key="index">
              <el-card class="capability-card" @click="useSuggestion(card.action)">
                <div class="card-icon" :style="{ background: card.color }">
                  <el-icon :size="28"><component :is="card.icon" /></el-icon>
                </div>
                <h4>{{ card.title }}</h4>
                <p>{{ card.description }}</p>
                <el-tag size="small" effect="plain">{{ card.action }}</el-tag>
              </el-card>
            </el-col>
          </el-row>

          <!-- 快捷指令 -->
          <div class="quick-actions">
            <h4>试试这样说：</h4>
            <div class="action-tags">
              <el-tag
                v-for="(suggestion, index) in suggestions"
                :key="index"
                class="action-tag"
                @click="useSuggestion(suggestion)"
              >
                {{ suggestion }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-else class="messages-container">
          <div
            v-for="(message, index) in messages"
            :key="message.id"
            class="message-wrapper"
            :class="message.role"
          >
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="message-bubble user">
              <div class="message-content">{{ message.content }}</div>
              <el-avatar :size="36">
                <el-icon><User /></el-icon>
              </el-avatar>
            </div>

            <!-- AI 消息 -->
            <div v-else class="message-bubble assistant">
              <el-avatar :size="36" class="ai-avatar-small">
                <el-icon><Cpu /></el-icon>
              </el-avatar>
              <div class="message-content">
                <!-- 文本回复 -->
                <div class="text-response">{{ message.content }}</div>

                <!-- 执行的操作展示 -->
                <div v-if="message.action_taken" class="action-executed">
                  <el-tag :type="message.confidence > 0.8 ? 'success' : 'warning'" size="small">
                    <el-icon><Check /></el-icon>
                    {{ message.action_taken }}
                  </el-tag>
                  <span class="confidence-badge" v-if="message.confidence">
                    置信度：{{ (message.confidence * 100).toFixed(0) }}%
                  </span>
                </div>

                <!-- Generative UI 组件容器 -->
                <div v-if="message.ui_components?.length" class="generative-ui-container">
                  <component
                    v-for="(ui, uiIndex) in message.ui_components"
                    :key="uiIndex"
                    :is="getUiComponent(ui.type)"
                    :data="ui.data"
                    :config="ui.config"
                  />
                </div>

                <!-- 建议操作 -->
                <div v-if="message.suggestions?.length" class="suggestion-actions">
                  <el-button
                    v-for="(suggestion, sIndex) in message.suggestions"
                    :key="sIndex"
                    size="small"
                    @click="useSuggestion(suggestion)"
                  >
                    {{ suggestion }}
                  </el-button>
                </div>

                <!-- 时间戳 -->
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
            </div>
          </div>

          <!-- 加载中状态 -->
          <div v-if="isLoading" class="message-wrapper assistant">
            <div class="message-bubble assistant">
              <el-avatar :size="36" class="ai-avatar-small">
                <el-icon><Cpu /></el-icon>
              </el-avatar>
              <div class="message-content thinking">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
                <p>{{ thinkingText }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-section">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="告诉我您想要什么... 例如：'帮我分析上周流量为什么下跌'、'发现增长机会'、'执行 SEO 优化'"
            @keydown.ctrl.enter="sendMessage"
            @keydown.meta.enter="sendMessage"
            :disabled="isLoading"
          />
          <div class="input-actions">
            <div class="voice-input" v-if="false">
              <el-button circle :disabled="true">
                <el-icon><Microphone /></el-icon>
              </el-button>
            </div>
            <el-button
              type="primary"
              :loading="isLoading"
              @click="sendMessage"
              class="send-button"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
        <p class="input-tip">按 Enter 发送，Ctrl/Cmd + Enter 换行</p>
      </div>
    </div>

    <!-- 右侧 Agent 可视化面板 -->
    <div class="agent-panel">
      <!-- Agent 状态 -->
      <el-card class="agent-status-card">
        <template #header>
          <span class="card-title">
            <el-icon><Grid /></el-icon>
            Agent 工作区
          </span>
        </template>
        <div class="agent-grid">
          <div
            v-for="(agent, key) in agents"
            :key="key"
            class="agent-item"
            :class="{ active: agent.active, working: agent.working }"
          >
            <div class="agent-icon" :style="{ background: agent.color }">
              <el-icon :size="24"><component :is="agent.icon" /></el-icon>
            </div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-status">
                <el-tag :type="agent.working ? 'success' : 'info'" size="small">
                  {{ agent.working ? '工作中...' : agent.active ? '就绪' : '离线' }}
                </el-tag>
              </div>
              <div v-if="agent.currentTask" class="agent-task">
                {{ agent.currentTask }}
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 主动推送洞察 -->
      <el-card class="insights-card">
        <template #header>
          <span class="card-title">
            <el-icon><Bell /></el-icon>
            AI 主动发现
            <el-badge :value="insights.length" :hidden="insights.length === 0" />
          </span>
        </template>
        <div class="insights-list">
          <div
            v-for="(insight, index) in insights"
            :key="index"
            class="insight-item"
            :class="insight.priority"
          >
            <div class="insight-icon">
              <el-icon v-if="insight.type === 'anomaly'"><Warning /></el-icon>
              <el-icon v-else-if="insight.type === 'opportunity'"><Star /></el-icon>
              <el-icon v-else><Document /></el-icon>
            </div>
            <div class="insight-content">
              <div class="insight-title">{{ insight.title }}</div>
              <div class="insight-desc">{{ insight.content }}</div>
              <div class="insight-actions">
                <el-button
                  v-for="(action, aIndex) in insight.actions"
                  :key="aIndex"
                  size="small"
                  text
                  @click="handleInsightAction(insight, action)"
                >
                  {{ action.label }}
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-if="insights.length === 0" description="暂无新发现" :image-size="60" />
        </div>
      </el-card>

      <!-- 最近执行记录 -->
      <el-card class="execution-history-card">
        <template #header>
          <span class="card-title">
            <el-icon><Clock /></el-icon>
            执行历史
          </span>
        </template>
        <div class="history-list">
          <div
            v-for="(item, index) in executionHistory"
            :key="index"
            class="history-item"
          >
            <div class="history-icon" :class="item.status">
              <el-icon v-if="item.status === 'success'"><CircleCheck /></el-icon>
              <el-icon v-else-if="item.status === 'running'"><Loading /></el-icon>
              <el-icon v-else><CircleClose /></el-icon>
            </div>
            <div class="history-info">
              <div class="history-action">{{ item.action }}</div>
              <div class="history-time">{{ formatTime(item.timestamp) }}</div>
            </div>
          </div>
          <el-empty v-if="executionHistory.length === 0" description="暂无执行记录" :image-size="60" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { chatApi, insightApi } from '@/api/chat'

// ==================== 状态定义 ====================

const messageStreamRef = ref<HTMLElement>()
const inputMessage = ref('')
const isLoading = ref(false)
const thinkingText = ref('思考中...')

// 消息列表
const messages = ref<Array<{
  id: string
  role: 'user' | 'assistant'
  content: string
  action_taken?: string
  confidence?: number
  requires_approval?: boolean
  data?: any
  suggestions?: string[]
  ui_components?: Array<{ type: string; data: any; config?: any }>
  timestamp: string
}>>([])

// AI 状态
const aiStatus = ref({ available: true, fallback: false })
const aiConfig = ref({ autoThreshold: 0.8, requestApprovalThreshold: 0.5 })

// 能力卡片
const capabilityCards = [
  {
    title: '流量分析',
    description: '分析流量趋势、异常检测和归因分析',
    icon: 'TrendCharts',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    action: '帮我分析最近的流量趋势'
  },
  {
    title: 'SEO 优化',
    description: '关键词排名分析、页面优化建议',
    icon: 'Search',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    action: '帮我优化 SEO 排名'
  },
  {
    title: '机会发现',
    description: '发现增长机会和竞品弱点',
    icon: 'Lightbulb',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    action: '发现增长机会'
  },
  {
    title: 'A/B 测试',
    description: '自动设计和执行 A/B 测试',
    icon: 'Compare',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    action: '设计一个 A/B 测试'
  },
  {
    title: '异常诊断',
    description: '自动检测并诊断流量异常',
    icon: 'Warning',
    color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    action: '检测有什么异常'
  },
  {
    title: '生成报告',
    description: '自动生成分析报告和洞察',
    icon: 'Document',
    color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    action: '生成一份周报'
  }
]

// 快捷建议
const suggestions = ref([
  '分析上周流量为什么下跌',
  '帮我发现增长机会',
  '执行 SEO 优化策略',
  '上周哪个页面表现最好',
  '有什么需要我关注的异常',
  '如何提升关键词排名'
])

// Agent 状态
const agents = ref({
  seo: {
    name: 'SEO Agent',
    icon: 'Search',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    active: true,
    working: false,
    currentTask: ''
  },
  content: {
    name: '内容 Agent',
    icon: 'Document',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    active: true,
    working: false,
    currentTask: ''
  },
  abtest: {
    name: 'A/B 测试 Agent',
    icon: 'Compare',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    active: true,
    working: false,
    currentTask: ''
  },
  analysis: {
    name: '分析 Agent',
    icon: 'DataAnalysis',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    active: true,
    working: false,
    currentTask: ''
  }
})

// 主动推送洞察
const insights = ref<any[]>([])

// 执行历史
const executionHistory = ref<any[]>([])

// 当前会话 ID
const sessionId = ref('')

// ==================== 方法定义 ====================

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleString('zh-CN')
}

// 获取 UI 组件
const getUiComponent = (type: string) => {
  const componentMap: Record<string, string> = {
    'chart': 'GenerativeChart',
    'metric-card': 'MetricCard',
    'table': 'DataTable',
    'insight': 'InsightCard',
    'progress': 'WorkflowProgress'
  }
  return componentMap[type] || 'div'
}

// 使用建议
const useSuggestion = async (suggestion: string) => {
  inputMessage.value = suggestion
  await sendMessage()
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()

  // 添加用户消息
  messages.value.push({
    id: `msg_${Date.now()}`,
    role: 'user',
    content: userMessage,
    timestamp: new Date().toISOString()
  })

  inputMessage.value = ''
  isLoading.value = true
  thinkingText.value = '思考中...'

  try {
    // 调用 Chat API
    const response = await chatApi.sendMessage({
      message: userMessage,
      session_id: sessionId.value || undefined,
      user_id: localStorage.getItem('user_id') || 'guest'
    })

    // 更新会话 ID
    sessionId.value = response.session_id

    // 添加 AI 回复
    messages.value.push({
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: response.message,
      action_taken: response.action_taken,
      confidence: response.confidence,
      requires_approval: response.requires_approval,
      data: response.data,
      suggestions: response.suggestions,
      ui_components: generateUiComponents(response.data),
      timestamp: new Date().toISOString()
    })

    // 记录执行历史
    if (response.action_taken) {
      executionHistory.value.unshift({
        action: response.action_taken,
        status: 'success',
        timestamp: new Date().toISOString()
      })
      // 限制历史记录长度
      if (executionHistory.value.length > 10) {
        executionHistory.value = executionHistory.value.slice(0, 10)
      }
    }

    // 滚动到底部
    scrollToBottom()
  } catch (error: any) {
    ElMessage.error(`发送失败：${error.message}`)
  } finally {
    isLoading.value = false
  }
}

// 根据响应生成 UI 组件
const generateUiComponents = (data: any) => {
  const components = []

  if (data?.chart) {
    components.push({
      type: 'chart',
      data: data.chart,
      config: { height: 300 }
    })
  }

  if (data?.metrics) {
    components.push({
      type: 'metric-card',
      data: data.metrics
    })
  }

  if (data?.table) {
    components.push({
      type: 'table',
      data: data.table
    })
  }

  return components
}

// 处理洞察操作
const handleInsightAction = (insight: any, action: any) => {
  if (action.action === 'analyze') {
    useSuggestion(`分析：${insight.title}`)
  } else if (action.action === 'optimize') {
    useSuggestion(`执行优化：${insight.title}`)
  } else if (action.action === 'fix') {
    useSuggestion(`修复：${insight.title}`)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messageStreamRef.value) {
      messageStreamRef.value.scrollTop = messageStreamRef.value.scrollHeight
    }
  })
}

// 获取 AI 状态
const fetchAiStatus = async () => {
  try {
    const status = await chatApi.getStatus()
    aiStatus.value = {
      available: status.deerflow_available,
      fallback: status.fallback_mode
    }
    aiConfig.value = {
      autoThreshold: status.auto_execute_threshold,
      requestApprovalThreshold: status.request_approval_threshold
    }
  } catch (error) {
    console.error('Failed to fetch AI status:', error)
  }
}

// 获取主动推送洞察
const fetchInsights = async () => {
  try {
    const result = await insightApi.getInsights()
    insights.value = result.slice(0, 5) // 限制显示数量
  } catch (error) {
    console.error('Failed to fetch insights:', error)
  }
}

// 初始化用户 ID
const initUserId = () => {
  if (!localStorage.getItem('user_id')) {
    localStorage.setItem('user_id', `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  }
}

// 生命周期
onMounted(() => {
  initUserId()
  fetchAiStatus()
  fetchInsights()

  // 定时刷新洞察
  const interval = setInterval(fetchInsights, 60000) // 每分钟刷新
  onUnmounted(() => clearInterval(interval))
})
</script>

<style scoped lang="scss">
.ai-chat-home {
  display: flex;
  height: calc(100vh - 120px);
  gap: 20px;
  padding: 20px;

  .chat-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;

    .ai-header {
      padding: 32px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      align-items: center;
      gap: 24px;

      .ai-avatar-pulse {
        position: relative;

        .ai-avatar {
          background: #fff;
          color: #667eea;
        }

        .pulse-ring {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 80px;
          height: 80px;
          border-radius: 50%;
          border: 2px solid rgba(255, 255, 255, 0.5);
          animation: pulse-ring 2s infinite;
        }
      }

      .ai-intro {
        h2 {
          color: #fff;
          font-size: 24px;
          margin: 0 0 8px 0;
        }

        p {
          color: rgba(255, 255, 255, 0.8);
          font-size: 14px;
          margin: 0 0 12px 0;
        }

        .ai-status {
          display: flex;
          align-items: center;
          gap: 12px;

          .confidence-info {
            color: rgba(255, 255, 255, 0.7);
            font-size: 12px;
          }
        }
      }
    }

    .message-stream {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      background: #fafbfc;

      .welcome-cards {
        max-width: 1200px;
        margin: 0 auto;

        .capability-card {
          cursor: pointer;
          transition: all 0.3s;
          text-align: center;
          padding: 24px 16px;

          &:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
          }

          .card-icon {
            width: 64px;
            height: 64px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            color: #fff;
          }

          h4 {
            font-size: 16px;
            margin: 0 0 8px 0;
            color: #303133;
          }

          p {
            font-size: 13px;
            color: #909399;
            margin: 0 0 12px 0;
            line-height: 1.5;
          }
        }

        .quick-actions {
          margin-top: 40px;

          h4 {
            font-size: 14px;
            color: #606266;
            margin: 0 0 16px 0;
          }

          .action-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;

            .action-tag {
              cursor: pointer;
              padding: 8px 16px;
              transition: all 0.3s;

              &:hover {
                background: #409EFF;
                color: #fff;
              }
            }
          }
        }
      }

      .messages-container {
        .message-wrapper {
          display: flex;
          margin-bottom: 24px;

          &.user {
            justify-content: flex-end;

            .message-bubble {
              .message-content {
                background: #409EFF;
                color: #fff;
                border-radius: 16px 16px 0 16px;
              }
            }
          }

          &.assistant {
            .message-bubble {
              .ai-avatar-small {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #fff;
              }
            }
          }

          .message-bubble {
            display: flex;
            gap: 12px;
            max-width: 80%;

            .message-content {
              padding: 16px 20px;
              background: #f0f2f5;
              border-radius: 16px 16px 16px 0;
              font-size: 14px;
              line-height: 1.6;

              .action-executed {
                margin-top: 12px;
                display: flex;
                align-items: center;
                gap: 8px;

                .confidence-badge {
                  font-size: 12px;
                  color: #909399;
                }
              }

              .generative-ui-container {
                margin-top: 16px;
              }

              .suggestion-actions {
                margin-top: 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
              }

              .message-time {
                font-size: 11px;
                color: #909399;
                margin-top: 8px;
              }

              &.thinking {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;

                .thinking-dots {
                  display: flex;
                  gap: 4px;

                  span {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #409EFF;
                    animation: thinking-bounce 1.4s infinite ease-in-out;

                    &:nth-child(1) { animation-delay: -0.32s; }
                    &:nth-child(2) { animation-delay: -0.16s; }
                  }
                }

                p {
                  font-size: 13px;
                  color: #909399;
                  margin: 0;
                }
              }
            }
          }
        }
      }
    }

    .input-section {
      padding: 20px 24px;
      border-top: 1px solid #e4e7ed;
      background: #fff;

      .input-wrapper {
        .input-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 12px;

          .voice-input {
            display: flex;
          }

          .send-button {
            min-width: 100px;
          }
        }
      }

      .input-tip {
        font-size: 12px;
        color: #909399;
        margin: 8px 0 0 0;
      }
    }
  }

  .agent-panel {
    width: 320px;
    display: flex;
    flex-direction: column;
    gap: 16px;

    .agent-status-card,
    .insights-card,
    .execution-history-card {
      .card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
    }

    .agent-status-card {
      .agent-grid {
        .agent-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 8px;
          background: #f5f7fa;
          transition: all 0.3s;

          &.active {
            background: rgba(64, 158, 255, 0.1);
          }

          &.working {
            background: rgba(103, 194, 58, 0.1);
            animation: working-pulse 2s infinite;
          }

          .agent-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            flex-shrink: 0;
          }

          .agent-info {
            flex: 1;
            min-width: 0;

            .agent-name {
              font-size: 14px;
              font-weight: 500;
              color: #303133;
            }

            .agent-task {
              font-size: 12px;
              color: #909399;
              margin-top: 4px;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }
          }
        }
      }
    }

    .insights-card {
      .insights-list {
        .insight-item {
          display: flex;
          gap: 12px;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 8px;
          background: #f5f7fa;

          &.critical {
            background: rgba(245, 108, 108, 0.1);
            border-left: 3px solid #f56c6c;
          }

          &.high {
            background: rgba(230, 162, 60, 0.1);
            border-left: 3px solid #e6a23c;
          }

          &.normal {
            background: rgba(103, 194, 58, 0.1);
            border-left: 3px solid #67c23a;
          }

          .insight-icon {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.05);
            color: #606266;
            flex-shrink: 0;
          }

          .insight-content {
            flex: 1;
            min-width: 0;

            .insight-title {
              font-size: 13px;
              font-weight: 500;
              color: #303133;
              margin-bottom: 4px;
            }

            .insight-desc {
              font-size: 12px;
              color: #909399;
              margin-bottom: 8px;
              display: -webkit-box;
              -webkit-line-clamp: 2;
              -webkit-box-orient: vertical;
              overflow: hidden;
            }

            .insight-actions {
              display: flex;
              gap: 8px;
            }
          }
        }
      }
    }

    .execution-history-card {
      flex: 1;
      overflow: hidden;

      .history-list {
        max-height: 300px;
        overflow-y: auto;

        .history-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px;
          border-radius: 6px;
          margin-bottom: 6px;

          &:hover {
            background: #f5f7fa;
          }

          .history-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;

            &.success {
              background: rgba(103, 194, 58, 0.1);
              color: #67c23a;
            }

            &.running {
              background: rgba(64, 158, 255, 0.1);
              color: #409EFF;
              animation: spin 1s linear infinite;
            }

            &.error {
              background: rgba(245, 108, 108, 0.1);
              color: #f56c6c;
            }
          }

          .history-info {
            flex: 1;
            min-width: 0;

            .history-action {
              font-size: 13px;
              color: #303133;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .history-time {
              font-size: 11px;
              color: #909399;
            }
          }
        }
      }
    }
  }
}

// 动画
@keyframes pulse-ring {
  0% {
    width: 80px;
    height: 80px;
    opacity: 1;
  }
  100% {
    width: 120px;
    height: 120px;
    opacity: 0;
  }
}

@keyframes thinking-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes working-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.4);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(103, 194, 58, 0);
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
