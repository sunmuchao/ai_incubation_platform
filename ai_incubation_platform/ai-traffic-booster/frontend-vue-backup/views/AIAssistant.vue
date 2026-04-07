<template>
  <div class="ai-assistant">
    <el-row :gutter="16">
      <!-- 左侧聊天区 -->
      <el-col :span="16">
        <el-card class="chat-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><ChatDotRound /></el-icon>
                AI 查询助手
              </span>
              <el-button text @click="clearChat">
                <el-icon><Delete /></el-icon>
                清空对话
              </el-button>
            </div>
          </template>

          <div class="chat-container">
            <!-- 欢迎消息 -->
            <div v-if="aiStore.queries.length === 0" class="welcome-message">
              <el-empty description="向我提问吧，例如：">
                <el-button type="primary" size="small" @click="useTemplate('上周哪个页面流量最高？')">
                  上周哪个页面流量最高？
                </el-button>
                <el-button type="primary" size="small" @click="useTemplate('最近 30 天的流量趋势如何？')">
                  最近 30 天的流量趋势如何？
                </el-button>
                <el-button type="primary" size="small" @click="useTemplate('为什么流量下跌了？')">
                  为什么流量下跌了？
                </el-button>
              </el-empty>
            </div>

            <!-- 消息列表 -->
            <div v-else class="message-list">
              <div v-for="(query, index) in aiStore.queries" :key="query.query_id" class="message-item">
                <!-- 用户消息 -->
                <div class="user-message">
                  <el-avatar :size="36">
                    <el-icon><User /></el-icon>
                  </el-avatar>
                  <div class="message-content">
                    <div class="message-text">{{ query.query_text }}</div>
                    <div class="message-time">{{ formatTime(query.created_at) }}</div>
                  </div>
                </div>

                <!-- AI 回复 -->
                <div class="ai-message">
                  <el-avatar :size="36" class="ai-avatar">
                    <el-icon><Cpu /></el-icon>
                  </el-avatar>
                  <div class="message-content">
                    <div class="message-response">
                      <!-- 数据可视化 -->
                      <div v-if="query.response?.data?.chart" class="response-chart"
                           :id="`chart-${index}`"></div>

                      <!-- AI 解读 -->
                      <div v-if="query.response?.interpretation" class="response-text">
                        <strong>AI 解读：</strong>
                        <p>{{ query.response.interpretation }}</p>
                      </div>

                      <!-- 建议列表 -->
                      <div v-if="query.response?.suggestions?.length" class="response-suggestions">
                        <strong>建议：</strong>
                        <ul>
                          <li v-for="(suggestion, i) in query.response.suggestions" :key="i">
                            {{ suggestion }}
                          </li>
                        </ul>
                      </div>

                      <!-- 操作按钮 -->
                      <div class="response-actions">
                        <el-button size="small" text @click="copyResponse(query.response)">
                          <el-icon><DocumentCopy /></el-icon>
                          复制
                        </el-button>
                        <el-button size="small" text @click="addToFavorites(query)">
                          <el-icon><Star /></el-icon>
                          收藏
                        </el-button>
                        <el-button size="small" text @click="exportQuery(query)">
                          <el-icon><Download /></el-icon>
                          导出
                        </el-button>
                      </div>
                    </div>
                    <div class="message-time">{{ formatTime(query.created_at) }}</div>
                  </div>
                </div>
              </div>

              <!-- 加载中 -->
              <div v-if="aiStore.isChatLoading" class="loading-message">
                <el-avatar :size="36" class="ai-avatar">
                  <el-icon><Cpu /></el-icon>
                </el-avatar>
                <div class="message-content">
                  <el-skeleton :rows="2" animated />
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区 -->
          <div class="input-area">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="输入您的问题，例如：'上周哪个页面流量最高？'、'为什么流量下跌了？'、'我该如何提升流量？'"
              @keydown.ctrl.enter="sendMessage"
              @keydown.meta.enter="sendMessage"
            />
            <div class="input-actions">
              <div class="quick-templates">
                <el-tag
                  v-for="(template, index) in quickTemplates"
                  :key="index"
                  size="small"
                  class="template-tag"
                  @click="inputText = template"
                >
                  {{ template }}
                </el-tag>
              </div>
              <el-button type="primary" @click="sendMessage" :loading="aiStore.isChatLoading">
                <el-icon><Promotion /></el-icon>
                发送
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧功能区 -->
      <el-col :span="8">
        <!-- 查询模板 -->
        <el-card class="templates-card">
          <template #header>
            <span class="card-title">
              <el-icon><Collection /></el-icon>
              查询模板
            </span>
          </template>
          <el-collapse accordion>
            <el-collapse-item
              v-for="(group, groupName) in templateGroups"
              :key="groupName"
              :title="groupName"
            >
              <div
                v-for="(template, index) in group"
                :key="index"
                class="template-item"
                @click="useTemplate(template)"
              >
                {{ template }}
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <!-- 查询历史 -->
        <el-card class="history-card">
          <template #header>
            <span class="card-title">
              <el-icon><Clock /></el-icon>
              查询历史
            </span>
          </template>
          <div class="history-list">
            <div
              v-for="(query, index) in recentQueries"
              :key="index"
              class="history-item"
              @click="useTemplate(query.query_text)"
            >
              <div class="history-text">{{ query.query_text }}</div>
              <div class="history-time">{{ formatTime(query.created_at) }}</div>
            </div>
            <el-empty v-if="recentQueries.length === 0" description="暂无查询历史" :image-size="60" />
          </div>
        </el-card>

        <!-- 收藏列表 -->
        <el-card class="favorites-card">
          <template #header>
            <span class="card-title">
              <el-icon><Star /></el-icon>
              我的收藏
            </span>
          </template>
          <div class="favorites-list">
            <div
              v-for="(fav, index) in aiStore.favorites"
              :key="index"
              class="favorites-item"
            >
              <div class="favorites-text">{{ fav.query_text }}</div>
              <el-button size="small" text @click="useTemplate(fav.query_text)">
                使用
              </el-button>
            </div>
            <el-empty v-if="aiStore.favorites.length === 0" description="暂无收藏" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 生成报告对话框 -->
    <el-dialog v-model="reportDialogVisible" title="生成报告" width="500px">
      <el-form :model="reportForm" label-width="80px">
        <el-form-item label="报告标题">
          <el-input v-model="reportForm.title" placeholder="请输入报告标题" />
        </el-form-item>
        <el-form-item label="报告类型">
          <el-select v-model="reportForm.type" placeholder="请选择报告类型">
            <el-option label="周报" value="weekly" />
            <el-option label="月报" value="monthly" />
            <el-option label="自定义报告" value="custom" />
            <el-option label="异常分析报告" value="anomaly" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="generateReport">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useAIAssistantStore } from '@/store'

const aiStore = useAIAssistantStore()

const inputText = ref('')
const reportDialogVisible = ref(false)
const reportForm = ref({
  title: '',
  type: 'weekly'
})

// 快捷模板
const quickTemplates = [
  '上周哪个页面流量最高？',
  '最近 30 天的流量趋势如何？',
  '为什么流量下跌了？',
  '我该如何提升流量？'
]

// 模板分组
const templateGroups = {
  '流量分析': [
    '上周哪个页面流量最高？',
    '最近 7 天的流量趋势如何？',
    '最近 30 天的流量趋势如何？',
    '这个月和上个月比怎么样？',
    '周末和工作日的流量有什么不同？'
  ],
  '异常检测': [
    '为什么流量下跌了？',
    '今天流量有什么异常？',
    '哪个渠道的流量下降了？',
    '流量波动的原因是什么？'
  ],
  '优化建议': [
    '我该如何提升流量？',
    '有哪些 SEO 优化建议？',
    '如何提升页面转化率？',
    '哪些关键词有提升空间？'
  ],
  '用户分析': [
    '用户留存率如何？',
    '新用户和老用户的比例？',
    '用户的设备分布如何？',
    '用户的地理分布如何？'
  ]
}

// 最近查询
const recentQueries = computed(() => {
  return aiStore.queries.slice(0, 10)
})

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleDateString('zh-CN')
}

// 使用模板
const useTemplate = (template: string) => {
  inputText.value = template
}

// 发送消息
const sendMessage = async () => {
  if (!inputText.value.trim() || aiStore.isChatLoading) return

  try {
    await aiStore.sendMessage(inputText.value.trim())
    inputText.value = ''

    // 渲染图表
    nextTick(() => {
      renderResponseChart()
    })
  } catch (error) {
    console.error('Send message failed:', error)
  }
}

// 清空对话
const clearChat = () => {
  aiStore.queries = []
  aiStore.initSession()
}

// 复制到剪贴板
const copyResponse = async (response: any) => {
  const text = response.interpretation + '\n\n建议：\n' + (response.suggestions || []).join('\n')
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

// 添加收藏
const addToFavorites = async (query: any) => {
  await aiStore.addToFavorites(query.query_id, query.query_text)
  ElMessage.success('已添加到收藏')
}

// 导出查询
const exportQuery = (query: any) => {
  // TODO: 实现导出功能
  ElMessage.info('导出功能开发中')
}

// 渲染响应图表
const renderResponseChart = () => {
  aiStore.queries.forEach((query, index) => {
    const chartContainer = document.getElementById(`chart-${index}`)
    if (!chartContainer || !query.response?.data?.chart) return

    const chart = echarts.init(chartContainer)
    chart.setOption(query.response.data.chart)
  })
}

// 生成报告
const generateReport = async () => {
  if (!reportForm.value.title) {
    ElMessage.warning('请输入报告标题')
    return
  }

  try {
    // TODO: 调用生成报告 API
    ElMessage.success('报告生成成功')
    reportDialogVisible.value = false
  } catch (error) {
    ElMessage.error('报告生成失败')
  }
}

onMounted(() => {
  aiStore.fetchTemplates()
  aiStore.fetchFavorites()
  aiStore.fetchSuggestions()
})
</script>

<style scoped lang="scss">
.ai-assistant {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
  }

  .chat-card {
    height: calc(100vh - 160px);
    display: flex;
    flex-direction: column;

    .chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 16px 0;

      .welcome-message {
        text-align: center;
        padding: 40px 0;
      }

      .message-list {
        .message-item {
          margin-bottom: 24px;

          .user-message,
          .ai-message {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;

            .ai-avatar {
              background-color: #409EFF;
              color: #fff;
            }

            .message-content {
              flex: 1;
              max-width: 80%;

              .message-text {
                background-color: #f0f0f0;
                padding: 12px 16px;
                border-radius: 8px;
                display: inline-block;
              }

              .message-response {
                background-color: #f5f7fa;
                padding: 16px;
                border-radius: 8px;
                border-left: 4px solid #409EFF;

                .response-chart {
                  height: 200px;
                  margin: 12px 0;
                }

                .response-text,
                .response-suggestions {
                  margin: 12px 0;
                  font-size: 14px;
                  line-height: 1.6;

                  ul {
                    margin: 8px 0;
                    padding-left: 20px;
                  }

                  li {
                    margin: 4px 0;
                  }
                }

                .response-actions {
                  margin-top: 12px;
                  display: flex;
                  gap: 8px;
                }
              }

              .message-time {
                font-size: 12px;
                color: #909399;
                margin-top: 8px;
              }
            }
          }

          .loading-message {
            display: flex;
            gap: 12px;
          }
        }
      }
    }

    .input-area {
      border-top: 1px solid #f0f0f0;
      padding-top: 16px;

      .input-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;

        .quick-templates {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;

          .template-tag {
            cursor: pointer;
            transition: all 0.3s;

            &:hover {
              background-color: #409EFF;
              color: #fff;
            }
          }
        }
      }
    }
  }

  .templates-card,
  .history-card,
  .favorites-card {
    margin-bottom: 16px;

    .template-item,
    .history-item,
    .favorites-item {
      padding: 8px 12px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s;

      &:hover {
        background-color: #f5f7fa;
      }

      &:not(:last-child) {
        border-bottom: 1px solid #f0f0f0;
      }
    }

    .history-text,
    .favorites-text {
      font-size: 13px;
      margin-bottom: 4px;
    }

    .history-time {
      font-size: 12px;
      color: #909399;
    }
  }
}
</style>
