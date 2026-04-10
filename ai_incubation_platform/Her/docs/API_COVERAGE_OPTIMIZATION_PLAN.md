# Her 前端 API 覆盖优化方案

> **状态更新 (2026-04-09)**：
> - ✅ 已修复：ai_interlocutor 路由已注册
> - ✅ 已修复：前端已删除无效 Skills 引用
> - ✅ 已优化：前端 localStorage 统一为 storage 工具模块

## 一、现状分析

### 1.1 后端 API 概览

| 分类 | 数量 | 说明 |
|------|------|------|
| 核心 API | 8 | 用户、匹配、聊天、对话匹配、AI感知、注册对话 |
| P10 API | 3 | 里程碑、约会建议、双人游戏 |
| P11 API | 4 | 安全守护、内容审核、风险评估、应急响应 |
| P12 API | 6 | 共同经历、沉默检测、破冰话题、情感调解、爱之语翻译、关系气象 |
| P13 API | 4 | 情感调解增强 |
| P14 API | 3 | 实战演习 |
| P15-P17 API | 6 | 虚实结合、圈子融合、终极共振 |
| 其他 API | 15+ | 照片、会员、支付、视频、身份认证等 |

**后端总计：约 50+ 个 API 路由**

### 1.2 前端调用覆盖情况

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 API 覆盖率分析                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 已覆盖（REST + Skill 双通道）  ~5个 (10%)               │
│     • 匹配 API                                                │
│     • 聊天 API                                                │
│     • 对话匹配 API                                            │
│     • 里程碑 API                                              │
│     • 双人游戏 API                                            │
│                                                             │
│  ✅ 已覆盖（仅 REST）              ~15个 (30%)               │
│     • 用户 API                                                │
│     • AI感知 API                                              │
│     • 注册对话 API                                            │
│     • P10-P17 部分 API                                        │
│                                                             │
│  ✅ 已覆盖（仅 Skill）            ~12个 (24%)                │
│     • 匹配助手 Skill                                          │
│     • 聊天助手 Skill                                          │
│     • 关系教练 Skill                                          │
│     • 全知洞察 Skill                                          │
│     • 约会规划 Skill                                          │
│     • 账单分析 Skill                                          │
│                                                             │
│  ❌ 未覆盖                       ~20个 (36%)                 │
│     • 照片管理                                                │
│     • 会员订阅                                                │
│     • 支付功能                                                │
│     • 视频通话                                                │
│     • 身份认证                                                │
│     • P11-P12 高级功能                                        │
│     • 其他预留功能                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、问题识别

### 2.1 严重问题（需立即修复）

#### 问题 1：AI Interlocutor 路由未注册

**现象**：前端调用 `/api/ai/interlocutor` 返回 404

**根因分析**：
- 为什么 1：前端 `aiInterlocutor.ts` 定义了预沟通 API 调用
- 为什么 2：后端 `ai_interlocutor.py` 已实现路由
- 为什么 3：但路由未在 `routers/__init__.py` 中注册
- 为什么 4：路由注册遗漏，缺少注册检查机制
- 为什么 5：缺乏 API 注册与前端调用的双向验证流程

**根本对策**：建立 API 注册检查机制，在启动时验证所有定义的 API 都已注册

#### 问题 2：前端引用已删除的 Skills

**现象**：运行时报错 `Skill not found`

**根因分析**：
- 为什么 1：`skillClient.ts` 导出 `geoLocation`、`giftOrdering`、`relationshipProgress`
- 为什么 2：后端 `registry.py` 已删除这些 Skills
- 为什么 3：删除时未同步更新前端引用
- 为什么 4：前后端 Skills 定义缺乏一致性检查
- 为什么 5：缺乏前后端 Skills 同步机制

**根本对策**：建立前后端 Skills 定义同步检查，删除 Skill 时必须同步删除前端引用

### 2.2 设计问题（需评估优化）

#### 问题 3：部分 API 缺少 Skill 调用通道

**现象**：核心 API 如用户、匹配只有 REST 调用，缺少 AI 增强通道

**分析**：
| API | 当前状态 | 是否需要 Skill |
|-----|---------|---------------|
| 用户 API | 仅 REST | ❌ 不需要（基础 CRUD） |
| 匹配 API | REST + Skill | ✅ 已有 |
| 聊天 API | REST + Skill | ✅ 已有 |
| P10 API | 仅 REST | ⚠️ 可考虑添加 |
| P11 API | 未覆盖 | ⚠️ 安全类应通过 Skill |
| P12 API | 未覆盖 | ⚠️ 情感类应通过 Skill |

#### 问题 4：前端页面缺失导致 API 未调用

**现象**：后端实现完整，但前端没有对应页面

**影响功能**：
- 照片管理（核心功能）
- 会员订阅（收入来源）
- 支付功能（收入来源）
- 身份认证（安全合规）
- 视频通话（核心功能）
- P11-P12 高级功能（差异化功能）

---

## 三、解决方案

### 3.1 立即修复项（P0）

#### 修复 1：注册 AI Interlocutor 路由

**文件**：`src/routers/__init__.py`

```python
# 添加导入
from api.ai_interlocutor import router as ai_interlocutor_router

# 注册路由
app.include_router(ai_interlocutor_router)
```

#### 修复 2：删除前端无效 Skills 引用

**文件**：`frontend/src/api/skillClient.ts`

```typescript
// 删除以下导出（约在第 686-689 行）
// geoLocation: geoLocationSkill,        // 已删除
// giftOrdering: giftOrderingSkill,      // 已删除
// relationshipProgress: relationshipProgressSkill,  // 已删除
```

### 3.2 短期优化项（P1）

#### 优化 1：建立 API 注册检查机制

**新建文件**：`src/utils/api_checker.py`

```python
"""
API 注册检查工具
启动时验证所有定义的 API 路由都已注册
"""
import os
import re

def check_api_registration():
    """检查所有 API 文件的路由是否都已注册"""
    api_dir = "src/api"
    registered_routes = get_registered_routes()
    defined_routes = get_defined_routes(api_dir)

    missing = defined_routes - registered_routes
    if missing:
        raise RuntimeError(f"以下 API 路由未注册: {missing}")
```

#### 优化 2：建立前后端 Skills 同步检查

**新建文件**：`frontend/src/utils/skillsSync.ts`

```typescript
/**
 * Skills 同步检查工具
 * 验证前端 Skills 定义与后端 registry 一致
 */
export async function checkSkillsSync(): Promise<string[]> {
  const backendSkills = await fetch('/api/skills/list').then(r => r.json())
  const frontendSkills = Object.keys(skills)

  const missing = frontendSkills.filter(s => !backendSkills.includes(s))
  const extra = backendSkills.filter(s => !frontendSkills.includes(s))

  return [...missing.map(s => `前端引用已删除的 Skill: ${s}`),
          ...extra.map(s => `前端缺少 Skill: ${s}`)]
}
```

### 3.3 中期开发项（P2）

#### 前端页面开发优先级

| 优先级 | 功能 | API | 业务价值 | 开发工作量 |
|--------|------|-----|---------|-----------|
| P2-1 | 照片管理 | `/api/photos` | 核心功能，用户展示必备 | 2天 |
| P2-2 | 身份认证 | `/api/identity_verification` | 安全合规，信任建立 | 2天 |
| P2-3 | 会员订阅 | `/api/membership` | 收入来源，商业化核心 | 3天 |
| P2-4 | 支付功能 | `/api/payment` | 收入来源，商业化核心 | 3天 |
| P2-5 | 视频通话 | `/api/video` | 核心功能，差异化体验 | 4天 |
| P2-6 | 安全守护 | `/api/p11/*` (via Skill) | 安全保障，品牌价值 | 5天 |
| P2-7 | 情感调解 | `/api/p12/*` (via Skill) | 差异化功能，AI Native 核心 | 5天 |

---

## 四、前端交互设计方案

### 4.1 设计原则：AI Native 交互

**核心理念**：用户不需要知道有哪些功能，AI 在合适时机主动推送

```
传统软件：用户必须知道有功能 → 找到功能入口 → 点击使用
AI Native：AI 感知用户场景 → 判断用户需要 → 适时推送功能入口
```

### 4.2 主交互：AI 主动感知 + 适时推送

#### 4.2.1 场景触发机制

| 用户场景 | AI 判断 | 推送内容 | 触发方式 |
|---------|--------|---------|---------|
| 新注册完成 | 用户需要完善资料 | 照片上传引导卡片 | 对话中推送 |
| 第一次匹配成功 | 用户想了解对方 | 查看详细资料按钮 | 匹配成功后 |
| 聊天超过 7 天 | 关系有进展 | 记录里程碑建议 | 对话中推送 |
| 聊天中提到约会 | 用户想见面 | 约会规划卡片 + 身份认证提醒 | 意图识别 |
| 提到礼物/节日 | 用户想送礼 | 礼物推荐卡片 | 意图识别 |
| 检测到沉默/尴尬 | 需要破冰 | 话题建议卡片 | 后台监控 |
| 检测到冲突情绪 | 需要调解 | 爱之语翻译卡片 | 情感分析 |
| 用户问"有什么功能" | 用户想了解 | 功能概览卡片 | 意图识别 |

#### 4.2.2 对话流示例

**场景 1：新用户注册完成**

```
AI: "你好，我是 Her 🤍

     我可以帮你遇见懂你的 TA，记录你们的重要时刻，
     在你需要时帮你破冰、调解...

     首先，要不要上传一张照片让大家认识你？"

     ┌─────────────────────────────────┐
     │ 📷 上传照片                      │
     │ 让更多人看到真实的你             │
     │                                 │
     │ [➕ 选择照片] [稍后再说]         │
     └─────────────────────────────────┘
```

**场景 2：匹配成功后**

```
AI: "你和 小美 匹配成功了！🎉

     你们有 3 个共同兴趣：旅行、音乐、美食
     匹配度 85%，非常不错哦~

     要不要看看她的详细资料？"

     ┌─────────────────────────────────┐
     │ 👤 小美的资料                    │
     │ ─────────────────────────────── │
     │ 📍 北京 · 25岁                   │
     │ 💬 "热爱生活，期待遇见有趣的人"  │
     │ ─────────────────────────────── │
     │ [查看详细资料] [开始聊天]        │
     └─────────────────────────────────┘
```

**场景 3：聊天一段时间后**

```
用户: "我们聊了两周了，感觉还不错"

AI: "看你们聊得很开心！要不要记录一下这个里程碑？"

     ┌─────────────────────────────────┐
     │ 🎉 记录里程碑                    │
     │ ─────────────────────────────── │
     │ 你们已经认识 14 天了！           │
     │                                 │
     │ 📝 添加备注：第一次感觉心动...   │
     │                                 │
     │ [记录这个时刻] [查看关系进展]    │
     └─────────────────────────────────┘
```

**场景 4：用户提到约会**

```
用户: "周末想约她出来"

AI: "我来帮你规划一下！根据你们的共同兴趣，我推荐..."

     ┌─────────────────────────────────┐
     │ 📅 约会规划                      │
     │ ─────────────────────────────── │
     │ 推荐 1：美食探店                 │
     │ 她喜欢日料，这有家不错的店...    │
     │                                 │
     │ 推荐 2：展览约会                 │
     │ 最近有个艺术展你们可能喜欢...    │
     │                                 │
     │ [查看详情] [换个建议]            │
     └─────────────────────────────────┘

AI: "另外，第一次约会前建议先完成身份认证，
     这样对方会更放心哦~"

     [开始认证] [稍后再说]
```

### 4.3 辅助入口：轻量级功能卡片

#### 4.3.1 设计理念

```
主交互：AI 适时推送（90% 的场景，用户自然发现功能）
辅助入口：轻量级功能卡片（10% 的场景，用户主动查找）
```

#### 4.3.2 入口设计

**位置**：顶部右侧，和通知、用户图标并列

```
┌─────────────────────────────────────────────────┐
│  🤍 Her                    🔔  👤  ⚡           │
└─────────────────────────────────────────────────┘
                                                  ↑
                                           点击展开功能卡片
```

#### 4.3.3 展开样式

点击后弹出卡片式功能列表，**不是传统菜单**

```
┌─────────────────────────────────┐
│  我能帮你做的事                  │
├─────────────────────────────────┤
│                                 │
│  📷 照片管理                     │
│  ✓ 身份认证                     │
│  💎 会员订阅                     │
│  💝 关系里程碑                   │
│  🎁 礼物推荐                     │
│  🛡️ 安全守护                     │
│  📊 关系分析                     │
│                                 │
│  ─────────────────────────────  │
│  💡 小提示：我会主动提醒你使用   │
│  这些功能，无需刻意来找          │
│                                 │
└─────────────────────────────────┘
```

#### 4.3.4 点击行为

点击某个功能后，**不跳转页面**，而是在对话区生成对应卡片：

```
用户点击「📷 照片管理」

→ 对话区出现：

┌─────────────────────────────────┐
│ AI: 好的，我来帮你管理照片~      │
│                                 │
│     📷 照片管理                  │
│     ─────────────────────────── │
│     当前照片：3 张               │
│                                 │
│     [➕ 上传新照片]              │
│                                 │
│     💡 建议：上传更多照片能让更  │
│     多人了解你，匹配成功率提升   │
│     40%                         │
│                                 │
└─────────────────────────────────┘
```

### 4.4 和传统菜单的对比

```
┌────────────────────────────────────────────────────────────┐
│                      传统菜单（重）                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  顶部导航：首页 | 匹配 | 消息 | 我的                        │
│                                                            │
│  左侧菜单：个人中心                                         │
│           照片管理                                         │
│           身份认证                                         │
│           会员订阅                                         │
│           设置                                             │
│                                                            │
│  问题：                                                     │
│  • 占用大量屏幕空间                                         │
│  • 用户必须主动找功能                                       │
│  • 页面跳转打断对话流                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                  AI Native 轻量级入口                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  顶部：🤍 Her                    🔔 👤 ⚡                   │
│                                                            │
│  主区域：对话界面（全屏）                                    │
│                                                            │
│  优势：                                                     │
│  • 只有一个图标入口，不占空间                               │
│  • AI 主动推送，用户自然发现功能                            │
│  • 功能卡片融入对话流，不打断                               │
│  • 用户主动查找时也能快速找到                               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4.5 功能发现路径

#### 方式 1：自然场景触发（主要，90%）

```
用户正常使用 → AI 感知场景 → 适时推送功能入口
```

用户在日常对话中自然发现所有功能，无需刻意寻找。

#### 方式 2：AI 自我介绍（首次进入）

```
AI: "你好，我是 Her 🤍

     我可以帮你：
     • 遇见懂你的 TA
     • 记录你们的重要时刻
     • 策划浪漫约会
     • 在你需要时帮你破冰、调解...

     有什么想聊的，随时告诉我~"
```

#### 方式 3：用户主动查找（辅助，10%）

```
用户点击右上角「⚡」图标 → 查看功能卡片列表 → 点击某功能
```

#### 方式 4：直接询问 AI

```
用户: "你还能帮我做什么？"
AI: 生成功能概览卡片
```

### 4.6 代码实现示意

#### 4.6.1 顶部 Header 添加功能入口

```tsx
// HomePage.tsx
<Header className="home-header">
  <div className="header-left">
    <HerLogo />
  </div>
  <div className="header-right">
    <Badge count={unreadCount}>
      <PushNotifications />
    </Badge>
    <UserMenu />
    <FeaturesButton />  {/* 新增：轻量级功能入口 */}
  </div>
</Header>
```

#### 4.6.2 功能卡片组件

```tsx
// components/FeaturesDrawer.tsx
import { Drawer, List, Space, Typography, Divider } from 'antd'

const { Text } = Typography

interface Feature {
  icon: string
  name: string
  description: string
  action: string
}

const features: Feature[] = [
  { icon: '📷', name: '照片管理', description: '上传和管理你的照片', action: 'photos' },
  { icon: '✓', name: '身份认证', description: '完成认证增加信任度', action: 'verify' },
  { icon: '💎', name: '会员订阅', description: '解锁更多高级功能', action: 'membership' },
  { icon: '💝', name: '关系里程碑', description: '记录重要时刻', action: 'milestones' },
  { icon: '🎁', name: '礼物推荐', description: '挑选合适的礼物', action: 'gifts' },
  { icon: '🛡️', name: '安全守护', description: '保护你的安全', action: 'safety' },
  { icon: '📊', name: '关系分析', description: '了解关系健康度', action: 'analysis' },
]

interface FeaturesDrawerProps {
  open: boolean
  onClose: () => void
  onFeatureSelect: (action: string) => void
}

export const FeaturesDrawer: React.FC<FeaturesDrawerProps> = ({
  open,
  onClose,
  onFeatureSelect
}) => {
  return (
    <Drawer
      title="我能帮你做的事"
      placement="right"
      width={320}
      open={open}
      onClose={onClose}
      closable
    >
      <List
        dataSource={features}
        renderItem={(feature) => (
          <List.Item
            onClick={() => {
              onFeatureSelect(feature.action)
              onClose()
            }}
            style={{
              cursor: 'pointer',
              padding: '12px 0'
            }}
          >
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Space>
                <Text style={{ fontSize: 20 }}>{feature.icon}</Text>
                <Text strong>{feature.name}</Text>
              </Space>
              <Text type="secondary" style={{ fontSize: 12, marginLeft: 28 }}>
                {feature.description}
              </Text>
            </Space>
          </List.Item>
        )}
      />
      <Divider />
      <Text type="secondary" style={{ fontSize: 12 }}>
        💡 小提示：我会主动提醒你使用这些功能，无需刻意来找
      </Text>
    </Drawer>
  )
}
```

#### 4.6.3 触发功能生成对话卡片

```tsx
// 在 ChatInterface 中处理功能触发
const triggerFeature = (action: string) => {
  const featureNames: Record<string, string> = {
    photos: '照片管理',
    verify: '身份认证',
    membership: '会员订阅',
    milestones: '关系里程碑',
    gifts: '礼物推荐',
    safety: '安全守护',
    analysis: '关系分析',
  }

  // 添加 AI 消息
  const aiMessage: Message = {
    id: `ai-${Date.now()}`,
    type: 'ai',
    content: `好的，我来帮你处理${featureNames[action]}~`,
    timestamp: new Date(),
  }
  setMessages(prev => [...prev, aiMessage])

  // 添加功能卡片
  const cardMessage: Message = {
    id: `card-${Date.now()}`,
    type: 'ai',
    content: '',
    timestamp: new Date(),
    generativeCard: getCardType(action),
    generativeData: getDataForAction(action),
  }
  setMessages(prev => [...prev, cardMessage])
}

// 映射功能到 GenerativeUI 组件
const getCardType = (action: string): string => {
  const cardMap: Record<string, string> = {
    photos: 'photo_upload_card',
    verify: 'identity_verify_card',
    membership: 'membership_card',
    milestones: 'milestone_card',
    gifts: 'gift_grid',
    safety: 'safety_status',
    analysis: 'health_score_card',
  }
  return cardMap[action] || 'empty_state'
}
```

### 4.7 场景触发服务

#### 4.7.1 后端场景检测

```python
# services/scene_detection_service.py

class SceneDetectionService:
    """场景检测服务 - 识别用户当前场景，决定是否推送功能"""

    # 场景触发规则
    SCENE_RULES = {
        'new_user': {
            'trigger': 'user_registered',
            'delay': 0,
            'push': 'photo_upload',
        },
        'first_match': {
            'trigger': 'match_created',
            'condition': lambda ctx: ctx.get('match_count', 0) == 1,
            'push': 'view_profile',
        },
        'chat_milestone': {
            'trigger': 'chat_duration',
            'condition': lambda ctx: ctx.get('days', 0) >= 7,
            'push': 'record_milestone',
        },
        'dating_intent': {
            'trigger': 'intent_detected',
            'condition': lambda ctx: ctx.get('intent') == 'dating',
            'push': ['date_planning', 'identity_verify'],
        },
        'silence_detected': {
            'trigger': 'silence_duration',
            'condition': lambda ctx: ctx.get('seconds', 0) > 300,
            'push': 'icebreaker_topics',
        },
    }

    def detect_scene(self, user_id: str, event: str, context: dict) -> Optional[dict]:
        """检测场景并返回推送建议"""
        rule = self.SCENE_RULES.get(event)
        if not rule:
            return None

        # 检查条件
        condition = rule.get('condition')
        if condition and not condition(context):
            return None

        # 返回推送内容
        push = rule.get('push')
        if isinstance(push, str):
            push = [push]

        return {
            'scene': event,
            'push_features': push,
            'context': context,
        }
```

#### 4.7.2 前端场景监听

```typescript
// services/sceneListener.ts

/**
 * 场景监听服务
 * 监听用户行为，触发场景检测
 */
export class SceneListener {
  private userId: string

  constructor(userId: string) {
    this.userId = userId
  }

  // 监听聊天时长
  onChatDuration(partnerId: string, days: number) {
    if (days >= 7 && days % 7 === 0) {
      this.checkAndPush('chat_milestone', { partner_id: partnerId, days })
    }
  }

  // 监听匹配成功
  onMatchCreated(matchId: string, matchCount: number) {
    this.checkAndPush('first_match', { match_id: matchId, match_count: matchCount })
  }

  // 监听用户意图
  onIntentDetected(intent: string, context: dict) {
    this.checkAndPush('dating_intent', { intent, ...context })
  }

  // 调用后端场景检测
  private async checkAndPush(scene: string, context: dict) {
    const result = await api.post('/api/scene/detect', {
      user_id: this.userId,
      scene,
      context,
    })

    if (result.push_features) {
      this.pushFeatureCards(result.push_features)
    }
  }

  // 推送功能卡片
  private pushFeatureCards(features: string[]) {
    features.forEach(feature => {
      // 通过事件通知 ChatInterface 添加卡片
      window.dispatchEvent(new CustomEvent('push-feature-card', {
        detail: { feature }
      }))
    })
  }
}
```

---

## 五、架构优化建议

### 5.1 API 与 Skill 调用策略

```
┌─────────────────────────────────────────────────────────────┐
│                   调用策略决策树                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  问：这个功能需要 AI 增强？                                   │
│                                                             │
│  ┌─────────────YES─────────────┐    ┌──────NO────────────┐ │
│  │                             │    │                    │ │
│  │  问：用户主动触发还是AI主动？ │    │  直接调用 REST API │ │
│  │                             │    │                    │ │
│  │  ┌──用户主动──┐  ┌─AI主动─┐ │    │  • 用户 CRUD      │ │
│  │  │           │  │        │ │    │  • 简单查询       │ │
│  │  │ Skill +   │  │ Skill  │ │    │  • 基础操作       │ │
│  │  │ REST API  │  │ 自主触发│ │    │                    │ │
│  │  │ 双通道    │  │        │ │    └────────────────────┘ │
│  │  │           │  │        │ │                           │
│  │  │ • 聊天    │  │ • 每日  │ │                           │
│  │  │ • 匹配    │  │   推荐  │ │                           │
│  │  │ • 约会    │  │ • 未读  │ │                           │
│  │  │           │  │   提醒  │ │                           │
│  │  └───────────┘  └────────┘ │                           │
│  │                             │                           │
│  └─────────────────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 新增 Skill 建议

| API | 建议 Skill | AI 能力 |
|-----|-----------|--------|
| P10 里程碑 | `milestone_insight_skill` | AI 分析关系进展，生成洞察 |
| P11 安全 | `safety_guardian_skill` | AI 实时监控，预警干预 |
| P12 情感 | `emotion_mediator_skill` | AI 情感分析，调解建议 |
| 照片管理 | `photo_assistant_skill` | AI 照片评分，优化建议 |

### 5.3 API 覆盖检查流程

```python
# 启动时检查
def startup_check():
    # 1. 检查所有 API 路由已注册
    check_api_registration()

    # 2. 检查前后端 Skills 同步
    check_skills_sync()

    # 3. 生成 API 覆盖报告
    generate_coverage_report()
```

---

## 六、实施计划

### 6.1 阶段划分

| 阶段 | 时间 | 内容 | 验收标准 |
|------|------|------|---------|
| **P0 紧急修复** | 1天 | 修复路由注册、删除无效引用 | 前端调用无 404 |
| **P1 检查机制** | 2天 | 建立 API/Skills 检查工具 | 启动时自动检查 |
| **P2 核心页面** | 1周 | 照片、认证、会员、支付 | 核心功能可用 |
| **P3 高级功能** | 2周 | 视频通话、P11-P12 | AI Native 功能完整 |

### 6.2 详细任务清单

#### P0 任务（立即执行）

- [x] 在 `routers/__init__.py` 注册 `ai_interlocutor_router` ✅ 已完成
- [x] 删除 `skillClient.ts` 中已删除 Skills 的引用 ✅ 已完成
- [x] 运行前端测试验证修复 ✅ 构建通过

#### P1 任务（本周完成）

- [x] 创建 `api_checker.py` 检查工具 ✅ 已完成
- [x] 创建 `skills_checker.py` 同步检查工具 ✅ 已完成
- [x] 在 `main.py` 启动时调用检查 ✅ 已完成
- [ ] 添加 CI 检查步骤

#### P2 任务（进行中）

- [x] 创建 `FeaturesDrawer.tsx` 组件 ✅ 已完成
- [x] 创建 `FeatureCards.tsx` 功能卡片组件库 ✅ 已完成
- [x] 在 `HomePage.tsx` 集成功能入口 ✅ 已完成
- [x] 在 `ChatInterface.tsx` 添加功能卡片渲染 ✅ 已完成
- [x] 创建后端场景检测服务 `scene_detection_service.py` ✅ 已完成
- [x] 创建前端场景监听服务 `sceneListener.ts` ✅ 已完成
- [x] 创建前端 API 调用文件 ✅ 已完成
  - `photosApi.ts` - 照片管理 API
  - `identityApi.ts` - 身份认证 API
  - `membershipApi.ts` - 会员订阅 API
- [x] 完善功能卡片组件 ✅ 已完成
  - PhotoManageCard - 照片管理（支持上传、删除、预览）
  - IdentityVerifyCard - 身份认证（支持认证流程）
  - MembershipCard - 会员订阅（支持套餐选择）
  - GiftRecommendCard - 礼物推荐
  - RelationshipAnalysisCard - 关系分析
  - SafetyGuardianCard - 安全守护
- [x] 修复 Vite 路径别名配置 ✅ 已完成
- [ ] 开发支付功能页面
- [ ] 添加对应 API 调用

#### P3 任务（后续规划）

- [ ] 开发视频通话功能
- [ ] 开发 P11 安全守护功能
- [ ] 开发 P12 情感调解功能
- [ ] 添加对应 Skill 调用

---

## 七、验收标准

### 7.1 功能验收

- [x] 所有前端 API 调用返回正确响应（无 404）✅ P0 已修复
- [x] 所有 Skills 调用能正确执行 ✅ 无效引用已删除
- [x] 轻量级功能入口已实现 ✅
- [x] 功能卡片组件已实现 ✅
- [x] 场景触发服务已实现 ✅
- [x] API 注册检查工具已实现 ✅
- [x] Skills 同步检查工具已实现 ✅
- [x] 照片管理功能卡片可用 ✅
- [x] 身份认证功能卡片可用 ✅
- [x] 会员订阅功能卡片可用 ✅
- [ ] 支付功能可用

### 7.2 代码验收

- [x] 无无效 API 引用 ✅
- [x] 无无效 Skills 引用 ✅
- [x] 启动检查通过 ✅
- [x] 前端构建通过 ✅
- [ ] CI 检查通过

### 7.3 架构验收

- [ ] 需要 AI 增强的功能有 Skill 调用通道
- [ ] REST API 和 Skill 调用职责清晰
- [ ] API 覆盖率 ≥ 80%

---

## 八、附录

### 附录 A：当前 API 覆盖详细清单

| API 路径 | REST 调用 | Skill 调用 | 状态 |
|----------|----------|-----------|------|
| `/api/users` | ✅ | ❌ | ✅ 合理 |
| `/api/matching` | ✅ | ✅ | ✅ 合理 |
| `/api/chat` | ✅ | ✅ | ✅ 合理 |
| `/api/conversation-matching` | ✅ | ✅ | ✅ 合理 |
| `/api/ai/awareness` | ✅ | ✅ | ✅ 合理 |
| `/api/registration-conversation` | ✅ | ❌ | ✅ 合理 |
| `/api/ai/interlocutor` | ✅ | ❌ | ❌ 路由未注册 |
| `/api/photos` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/membership` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/payment` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/video` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/identity_verification` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/p11/*` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/p12/*` | ❌ | ❌ | ❌ 前端未开发 |
| `/api/p13/*` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/p14/*` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/p15-p17/*` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/milestones` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/date-suggestions` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/couple-games` | ✅ | ❌ | ⚠️ 可添加 Skill |
| `/api/safety` | ❌ | ✅ | ✅ Skill 内部调用 |
| `/api/performance` | ❌ | ❌ | ✅ 后台服务 |
| `/api/credit` | ❌ | ❌ | ✅ 内部服务 |
| `/api/agent-intervention` | ❌ | ❌ | ✅ 后台服务 |
| `/api/llm-cache` | ❌ | ❌ | ✅ 后台服务 |

### 附录 B：前后端 Skills 对照表

| 后端 Skill 名称 | 前端引用 | 状态 |
|----------------|---------|------|
| `matchmaking_assistant` | ✅ `matchmakingSkill` | ✅ 同步 |
| `pre_communication` | ✅ `preCommunicationSkill` | ✅ 同步 |
| `omniscient_insight` | ✅ `omniscientInsightSkill` | ✅ 同步 |
| `relationship_coach` | ✅ `relationshipCoachSkill` | ✅ 同步 |
| `date_planning` | ✅ `datePlanningSkill` | ✅ 同步 |
| `bill_analysis` | ✅ `billAnalysisSkill` | ✅ 同步 |
| `chat_assistant` | ✅ `chatAssistantSkill` | ✅ 同步 |
| `safety_guardian` | ✅ `safetyGuardianSkill` | ✅ 同步 |
| `geo_location` | ❌ 已删除 | ❌ 前端残留引用 |
| `gift_ordering` | ❌ 已删除 | ❌ 前端残留引用 |
| `relationship_progress` | ❌ 已删除 | ❌ 前端残留引用 |

---

**文档版本**：v2.3
**更新日期**：2026-04-09
**更新内容**：
- v2.3: 完善功能卡片组件 + 前端 API 调用文件
- v2.2: 完成 P1 检查机制 + 场景触发服务实现
- v2.1: 完成 P0 紧急修复 + P2 前端交互基础实现
- v2.0: 新增前端交互设计方案（第四章）
**负责人**：开发团队