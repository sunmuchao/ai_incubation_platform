# Her 产品规划文档 (PRODUCT_ROADMAP)

> **版本**: v2.1.0 (L4 增强版)  
> **更新日期**: 2026-04-08  
> **状态**: 活跃

---

## 执行摘要

本文档整合了 Her (红娘 Agent) 的完整产品规划，包括已完成功能、近期优化、中期规划和长期愿景。同时纳入了来自 `her_plan.txt` 的增强建议，涵盖信任体系强化、架构演进、算法迭代三个维度。

**最新更新 (v2.1.0)**:
- ✅ 数字分身预聊：分身模拟相亲、复盘报告生成
- ✅ AI 持续学习：用户偏好记忆、历史行为学习
- ✅ 情境感知渲染：自适应 UI 组件选择

---

## 一、已完成功能总览 (v1.28.0)

### 1.1 AI Native 架构 (v1.28.0)

| 模块 | 状态 | 说明 |
|------|------|------|
| Agent Skill 系统 | ✅ | 8 个核心 Skills |
| LLM 意图理解 | ✅ | 自然语言参数提取 |
| Generative UI | ✅ | 9+ 动态组件 |
| 响应生成器 | ✅ | AI 消息 + UI 选择 |
| 外部服务封装 | ✅ | 账单/地理/礼物 Skill 化 |

### 1.2 核心功能 (P0-P9)

| 阶段 | 功能 | 状态 |
|------|------|------|
| P0 | JWT 认证、AI 匹配、SQLite 持久化 | ✅ |
| P1 | 破冰问题、地理位置、性格分析 | ✅ |
| P2 | 用户举报/封禁、兴趣社区 | ✅ |
| P3 | 动态画像、行为追踪 | ✅ |
| P4 | 照片管理、实名认证、实时聊天 | ✅ |
| P5 | 会员订阅、滑动交互 | ✅ |
| P6 | 视频通话、信任标识、AI 陪伴 | ✅ |
| P7 | 安全风控 AI、对话分析增强 | ✅ |
| P8 | 企业数据看板、绩效管理 | ✅ |
| P9 | 推送通知、分享机制、邀请码 | ✅ |

### 1.3 下一代功能 (P10-P22)

| 阶段 | 主题 | 状态 |
|------|------|------|
| P10 | 深度认知 | ✅ 模型完成 |
| P11 | 感官洞察 | ✅ 模型完成 |
| P12 | 行为实验室 | ✅ 模型完成 |
| P13 | 情感调解 | ✅ 模型完成 |
| P14 | 实战演习 | ✅ 模型完成 |
| P15 | 虚实结合 | ✅ 模型完成 |
| P16 | 圈子融合 | ✅ 模型完成 |
| P17 | 终极共振 | ✅ 模型完成 |
| P18-22 | AI 预沟通等 | ✅ 模型完成 |

---

## 二、增强建议 (来自 her_plan.txt)

### 2.1 信任体系强化

#### 2.1.1 多源身份核验

**现状**: 目前仅有 P6 级实名认证，信任背书单一。

**增强方案**:

| 验证类型 | 数据来源 | 展示形式 |
|---------|---------|---------|
| 学历认证 | 学信网 API | 🎓 学历勋章 |
| 职业认证 | 企业邮箱/LinkedIn | 💼 职业勋章 |
| 收入认证 | 税单/银行流水 | 💰 财力勋章 |
| 房产认证 | 房产证电子凭证 | 🏠 资产勋章 |
| 无犯罪记录 | 公安 API | 🛡️ 安全勋章 |

**Generative UI 展示**:
- 在匹配卡片中以"信任勋章墙"形式直观展示
- 支持勋章筛选（如"只看本科及以上学历"）
- 勋章权重纳入匹配算法

**优先级**: P0 (信任是婚恋产品第一门槛)  
**预计工时**: 3 周

---

#### 2.1.2 AI 行为信用分

**现状**: behavior_events 数据已采集，但未转化为信用评估。

**增强方案**:

```python
class BehaviorCreditSystem:
    """行为信用评分系统"""
    
    # 负面行为扣分
    negative_events = {
        "harassment_reported": -50,    # 被举报骚扰
        "fake_info_detected": -30,     # 虚假信息
        "aggressive_language": -20,    # 攻击性语言
        "photo_rejected": -10,         # 照片审核不通过
        "ghosting_after_contact": -5,  # 交换联系方式后消失
    }
    
    # 正面行为加分
    positive_events = {
        "complete_profile": +10,       # 完善资料
        "verified_badge": +20,         # 获得认证标识
        "positive_feedback": +15,      # 获得好评
        "active_response": +5,         # 及时回复
        "successful_date": +25,        # 成功约会
    }
    
    # 信用等级
    credit_levels = {
        "S": (90, 100, "极可信用户"),
        "A": (75, 89, "高度可信"),
        "B": (60, 74, "普通用户"),
        "C": (40, 59, "需谨慎"),
        "D": (0, 39, "高风险"),
    }
```

**应用场景**:
1. **匹配权重调节**: 信用分低于 60 的用户推荐优先级降低
2. **敏感功能限制**: 信用分低于 40 禁止主动发起聊天
3. **AI 提醒**: 向对方展示"该用户信用分较低，请谨慎交往"
4. **申诉机制**: 用户可对扣分行为发起申诉

**API 端点**:
```
GET  /api/credit/score          # 获取我的信用分
GET  /api/credit/history        # 信用记录历史
POST /api/credit/appeal         # 提交申诉
GET  /api/credit/user/{user_id} # 查看他人信用等级 (仅等级，不显示分数)
```

**优先级**: P0  
**预计工时**: 4 周

---

#### 2.1.3 敏感信息过滤

**现状**: AI 预沟通阶段未对敏感信息进行过滤。

**增强方案**:

**AI 信息过滤器**:
```python
class InformationFilter:
    """AI 预沟通信息过滤器"""
    
    # 敏感信息类型
    sensitive_patterns = {
        "phone": r"1[3-9]\d{9}",           # 手机号
        "wechat": r"wxid_[a-zA-Z0-9]+",    # 微信号
        "address": r".*? [省市区县].*?",    # 地址
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "real_name": r"[张王李赵].*?",      # 真实姓名
    }
    
    # 过滤策略
    def filter_message(self, message, relationship_stage):
        if relationship_stage < "contact_exchange":
            # 预沟通阶段：完全屏蔽
            return self.mask_sensitive_info(message)
        elif relationship_stage < "meeting_confirmed":
            # 已确认见面：可透露部分信息
            return self.partial_reveal(message)
        else:
            # 已见面：完全开放
            return message
```

**Generative UI 展示**:
- 当检测到敏感信息时，AI 弹出提示："为了保护您的隐私，建议在双方建立信任后再交换联系方式"
- 提供"AI 代发消息"功能：AI 润色后的高情商版本

**优先级**: P0 (隐私保护是合规要求)  
**预计工时**: 2 周

---

### 2.2 架构演进

#### 2.2.1 感知层 (Perception Layer)

**现状**: 当前架构以 HTTP/REST API 为主，AI 被动响应。

**增强方案**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Perception Layer (新增)                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│  │ Vector Database │ │ Behavior Events │ │ Long-term     │ │
│  │ (Milvus/Pinecone)│ │   Stream       │ │   Memory      │ │
│  └─────────────────┘ └─────────────────┘ └───────────────┘ │
│                            │                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Digital Subconscious Engine                ││
│  │  - 价值观向量偏移追踪                                    ││
│  │  - 兴趣偏好演化分析                                      ││
│  │  - 沟通模式学习                                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**向量数据库 Schema**:
```python
class UserVector:
    """用户向量表示"""
    user_id: str
    # 价值观向量 (128 维)
    values_vector: List[float]
    # 兴趣向量 (64 维)
    interests_vector: List[float]
    # 沟通风格向量 (32 维)
    communication_style_vector: List[float]
    # 行为模式向量 (64 维)
    behavior_pattern_vector: List[float]
    # 时间戳
    updated_at: datetime
```

**实时更新逻辑**:
```python
# 当检测到用户行为事件时
async def on_behavior_event(event):
    # 更新用户向量
    user_vector = await vector_db.get(event.user_id)
    
    # 根据事件类型调整向量
    if event.type == "viewed_profile":
        # 用户浏览了某类资料，调整偏好向量
        user_vector.interests_vector = adjust_interests(
            user_vector.interests_vector,
            event.target_profile_tags
        )
    
    # 异步持久化
    await vector_db.update(event.user_id, user_vector)
```

**优先级**: P1  
**预计工时**: 4 周

---

#### 2.2.2 流式 Skill 执行 (SSE)

**现状**: `/api/agent/skill/execute` 等待完整执行后返回 JSON，延迟高。

**增强方案**:

**Server-Sent Events 实现**:

```python
@app.get("/api/agent/skill/execute/stream")
async def execute_skill_stream(skill_name: str, params: str):
    """流式执行 Skill，降低用户感知延迟"""
    
    async def generate():
        # 阶段 1: 意图理解中
        yield sse_event("status", "理解您的需求中...")
        intent = await parse_intent(skill_name, params)
        yield sse_event("intent", json.dumps(intent))
        
        # 阶段 2: 执行 Skill
        yield sse_event("status", "正在为您匹配...")
        result = await skill.execute(**intent)
        
        # 阶段 3: 生成响应
        yield sse_event("status", "正在生成建议...")
        response = await generate_response(result)
        yield sse_event("response", json.dumps(response))
        
        # 阶段 4: 生成 UI
        ui_config = select_ui_component(result)
        yield sse_event("ui", json.dumps(ui_config))
        
        # 完成
        yield sse_event("done", "complete")
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**前端消费**:
```typescript
const eventSource = new EventSource(
  `/api/agent/skill/execute/stream?skill_name=${skill}&params=${params}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (event.type) {
    case "status":
      setLoadingMessage(data);
      break;
    case "intent":
      // 显示已理解的意图
      setIntent(data);
      break;
    case "response":
      // 显示 AI 响应
      addAIMessage(data);
      break;
    case "ui":
      // 渲染 Generative UI
      renderGenerativeUI(data);
      break;
  }
};
```

**优先级**: P0 (接入真实 LLM 后延迟会大幅增加)  
**预计工时**: 2 周

---

#### 2.2.3 自适应 UI (Adaptive Component Rendering)

**现状**: Generative UI 仅根据数据类型选择组件，不够智能。

**增强方案**:

**情境感知渲染**:
```python
class AdaptiveUIRenderer:
    """自适应 UI 渲染器"""
    
    def select_component(self, context: dict) -> dict:
        # 情境 1: 检测到双方尴尬沉默
        if context.get("silence_duration", 0) > 30:
            return {
                "component_type": "ai_translator",
                "props": {
                    "suggested_replies": [
                        "我猜你现在可能有点紧张，其实我也一样 😊",
                        "不如我们聊聊各自最近看过的一部电影？",
                        "AI 观察到你们都提到了喜欢旅行，要不要深入聊聊？"
                    ]
                }
            }
        
        # 情境 2: 检测到观点冲突
        elif context.get("conflict_detected"):
            return {
                "component_type": "conflict_mediator",
                "props": {
                    "mediation_tips": [
                        "尝试从对方的角度理解这个问题",
                        "这个话题可能比较敏感，先换个轻松的话题吧"
                    ]
                }
            }
        
        # 默认：正常对话
        else:
            return {
                "component_type": "chat_input",
                "props": {}
            }
```

**优先级**: P1  
**预计工时**: 3 周

---

#### 2.2.4 多模态预沟通 (P11 增强版)

**现状**: AI 预沟通仅限于文字对话。

**增强方案**:

**数字分身预聊**:
```python
class DigitalTwinPreCommunication:
    """数字分身预沟通"""
    
    async def simulate_date(self, user_a_id: str, user_b_id: str):
        # 加载用户历史数据和性格画像
        user_a_profile = await self.get_user_profile(user_a_id)
        user_b_profile = await self.get_user_profile(user_b_id)
        
        # 创建 AI 分身
        user_a_twin = await self.create_digital_twin(user_a_profile)
        user_b_twin = await self.create_digital_twin(user_b_profile)
        
        # 分身进行 10 轮对话模拟
        conversation = []
        for i in range(10):
            if i % 2 == 0:
                response = await user_a_twin.respond(conversation, user_b_profile)
            else:
                response = await user_b_twin.respond(conversation, user_a_profile)
            conversation.append(response)
        
        # 生成复盘报告
        report = await self.generate_report(conversation, user_a_profile, user_b_profile)
        return {
            "conversation_highlights": conversation[:5],  # 精选片段
            "compatibility_score": report["score"],
            "potential_conflicts": report["conflicts"],
            "suggestions": report["suggestions"]
        }
```

**报告展示 UI**:
```
┌────────────────────────────────────────────────────┐
│   《数字分身相亲复盘报告》                          │
├────────────────────────────────────────────────────┤
│  兼容性评分：85/100                                 │
│                                                    │
│  ✅ 高度契合点:                                     │
│  • 你们都热爱旅行，且偏好自然风光                   │
│  • 沟通风格都很直接，避免猜来猜去                   │
│  • 对家庭价值观的理解一致                           │
│                                                    │
│  ⚠️ 潜在冲突点:                                     │
│  • 消费观念差异较大（用户 A 偏向节俭，用户 B 偏向享受）│
│  • 周末活动偏好不同（宅家 vs 外出）                 │
│                                                    │
│  💡 AI 建议:                                        │
│  • 初次约会建议选择户外活动，平衡双方偏好           │
│  • 避免过早讨论消费相关话题                         │
└────────────────────────────────────────────────────┘
```

**优先级**: P2 (差异化功能)  
**预计工时**: 5 周

---

#### 2.2.5 LLM 缓存层 (Semantic Cache)

**现状**: 每次请求都调用 LLM，成本高、延迟大。

**增强方案**:

```python
class SemanticCache:
    """语义缓存层"""
    
    def __init__(self):
        self.vector_store = ChromaDB()
        self.cache_ttl = 3600  # 1 小时
    
    async def get(self, query: str, context: dict) -> Optional[dict]:
        # 将查询转换为向量
        query_vector = await self.embed(query)
        
        # 检索相似查询
        similar = self.vector_store.search(query_vector, threshold=0.95)
        
        if similar:
            # 检查缓存是否过期
            if time.time() - similar[0]["timestamp"] < self.cache_ttl:
                return similar[0]["response"]
        
        return None
    
    async def set(self, query: str, response: dict, context: dict):
        # 存储查询向量和响应
        query_vector = await self.embed(query)
        self.vector_store.add({
            "vector": query_vector,
            "response": response,
            "timestamp": time.time()
        })

# 使用示例
async def execute_skill_with_cache(skill_name: str, params: dict):
    cache_key = f"{skill_name}:{hash(str(params))}"
    
    # 尝试命中缓存
    cached = await semantic_cache.get(cache_key, params)
    if cached:
        return cached
    
    # 执行 Skill
    result = await skill.execute(**params)
    
    # 写入缓存
    await semantic_cache.set(cache_key, result, params)
    return result
```

**缓存命中率目标**: 60%+ (相似查询场景)  
**优先级**: P1  
**预计工时**: 2 周

---

### 2.3 算法迭代

#### 2.3.1 从"静态标签匹配"转向"动态共鸣演算法"

**现状**: 匹配逻辑基于年龄、兴趣等硬指标。

**增强方案**:

**冲突处理模型**:
```python
class ConflictCompatibilityModel:
    """冲突兼容性模型"""
    
    async def analyze_conflict_patterns(self, user_a_id: str, user_b_id: str):
        # 获取历史纠纷处理数据
        user_a_conflicts = await self.get_conflict_history(user_a_id)
        user_b_conflicts = await self.get_conflict_history(user_b_id)
        
        # 分析冲突处理风格
        user_a_style = self.analyze_style(user_a_conflicts)  # 回避型/对抗型/协商型
        user_b_style = self.analyze_style(user_b_conflicts)
        
        # 评估风格兼容性
        compatibility_matrix = {
            ("回避型", "回避型"): 0.4,  # 问题累积
            ("回避型", "对抗型"): 0.3,  # 矛盾升级
            ("回避型", "协商型"): 0.7,  # 可调和
            ("对抗型", "对抗型"): 0.2,  # 激烈冲突
            ("对抗型", "协商型"): 0.6,  # 可调和
            ("协商型", "协商型"): 0.9,  # 理想组合
        }
        
        return compatibility_matrix.get((user_a_style, user_b_style), 0.5)
```

**优先级**: P1  
**预计工时**: 4 周

---

#### 2.3.2 价值观向量偏移追踪

**现状**: 用户价值观是静态的，不随行为更新。

**增强方案**:

```python
class ValuesEvolutionTracker:
    """价值观演化追踪器"""
    
    async def track_values_shift(self, user_id: str):
        # 获取用户声明的价值观
        declared_values = await self.get_declared_values(user_id)
        
        # 分析近期行为（过去 30 天）
        recent_behaviors = await self.get_recent_behaviors(user_id, days=30)
        
        # 推断实际价值观
        inferred_values = await self.infer_values_from_behavior(recent_behaviors)
        
        # 计算偏移
        drift = self.calculate_drift(declared_values, inferred_values)
        
        # 更新匹配权重
        if drift["significant"]:
            # 用户价值观发生显著变化，重新计算匹配权重
            await self.update_matching_weights(user_id, inferred_values)
            
            # 通知用户
            await self.notify_user(user_id, {
                "type": "values_shift_detected",
                "message": f"AI 发现您的择偶偏好有所变化，是否更新推荐策略？"
            })
        
        return {
            "original": declared_values,
            "current": inferred_values,
            "drift_score": drift["score"]
        }
```

**示例场景**:
- 用户 A 声称"向往自由"，但近期频繁搜索"稳定工作"、"有房有车"的候选人
- AI 检测到偏移，调整推荐策略，优先推荐稳定型候选人

**优先级**: P1  
**预计工时**: 3 周

---

#### 2.3.3 礼物闭环分成模式

**现状**: gift_ordering Skill 使用 Mock 数据，未实现真实交易。

**增强方案**:

**电商平台对接**:
```python
class GiftOrderingIntegration:
    """礼物订购集成"""
    
    def __init__(self):
        self.jd_client = JDClients(api_key=JD_API_KEY)
        self.taobao_client = TaobaoClient(api_key=TAOBAO_API_KEY)
    
    async def get_gift_suggestions(self, occasion: str, budget: str, preferences: dict):
        # 根据场合和预算选品
        if occasion == "birthday":
            products = await self.jd_client.search(
                keyword="生日礼物",
                min_price=int(budget.split("-")[0]),
                max_price=int(budget.split("-")[1])
            )
        
        # AI 排序（基于接收人画像）
        ranked = await self.ai_rank_products(products, preferences)
        
        return [
            {
                "name": p["name"],
                "price": p["price"],
                "platform": p["platform"],
                "affiliate_link": p["affiliate_link"],  # 推广链接
                "commission_rate": p["commission_rate"]  # 佣金比例 (5-15%)
            }
            for p in ranked[:10]
        ]
    
    async def place_order(self, product_id: str, delivery_info: dict):
        # 下单并追踪物流
        order = await self.jd_client.place_order(product_id, delivery_info)
        return {
            "order_id": order["id"],
            "tracking_no": order["tracking_no"],
            "estimated_delivery": order["estimated_delivery"]
        }
```

**商业模式**:
- 平台佣金：商品价格的 5-15%
- 预计 ARPU：¥50/年/用户（礼物订购）

**优先级**: P2 (收入来源)  
**预计工时**: 4 周

---

#### 2.3.4 Agent 自主权管控

**现状**: AI 自主触发时没有用户授权等级控制。

**增强方案**:

```python
class AgentInterventionControl:
    """AI 介入管控"""
    
    INTERVENTION_LEVELS = {
        "silent": 0,      # 仅记录，不提醒
        "private": 1,     # 私下提醒用户
        "suggestion": 2,  # 在对话中暗示
        "active": 3,      # 主动推送建议
        "emergency": 4,   # 紧急情况，立即干预
    }
    
    async def check_intervention(self, user_id: str, event_type: str, event_data: dict):
        # 获取用户授权等级
        user_settings = await self.get_user_settings(user_id)
        allowed_level = user_settings.get("ai_intervention_level", 2)
        
        # 评估事件严重程度
        severity = self.evaluate_severity(event_type, event_data)
        
        # 决定介入方式
        if severity > allowed_level:
            # 用户设置的授权等级低于事件严重程度，采用默认策略
            return self.get_default_intervention(event_type)
        
        if severity == self.INTERVENTION_LEVELS["silent"]:
            return None  # 不打扰
        elif severity == self.INTERVENTION_LEVELS["private"]:
            return {"type": "private_notification", "content": "..."}
        elif severity == self.INTERVENTION_LEVELS["suggestion"]:
            return {"type": "chat_suggestion", "content": "..."}
        elif severity == self.INTERVENTION_LEVELS["active"]:
            return {"type": "push_notification", "content": "..."}
        elif severity == self.INTERVENTION_LEVELS["emergency"]:
            # 紧急情况（如安全威胁），立即干预并通知平台
            await self.notify_platform_admin(event_data)
            return {"type": "emergency_intervention", "content": "..."}
```

**用户设置界面**:
```
AI 介入程度设置:

○ minimal    仅在紧急情况下提醒（如安全风险）
○ balanced   适度提醒（默认）
○ proactive  主动提供建议（推荐）
○ intensive  全方位指导（适合恋爱新手）
```

**优先级**: P1  
**预计工时**: 2 周

---

## 三、产品规划时间表

### 3.1 近期优化 (1-2 个月)

| 任务 | 优先级 | 预计工时 | 依赖 | 状态 |
|------|--------|---------|------|------|
| **信任体系强化** | | | | |
| 多源身份核验 | P0 | 3 周 | 第三方 API | ✅ 已完成 |
| AI 行为信用分 | P0 | 4 周 | behavior_events | ✅ 已完成 |
| 敏感信息过滤 | P0 | 2 周 | AI 预沟通 | ✅ 已完成 |
| **架构演进** | | | | |
| 感知层 (向量数据库) | P1 | 4 周 | - | ✅ 已完成 |
| 流式 Skill 执行 (SSE) | P0 | 2 周 | - | ✅ 已完成 |
| LLM 缓存层 | P1 | 2 周 | 向量数据库 | ✅ 已完成 |
| **算法迭代** | | | | |
| 冲突处理模型 | P1 | 4 周 | - | ✅ 已完成 |
| 价值观偏移追踪 | P1 | 3 周 | - | ✅ 已完成 |
| 礼物闭环集成 | P2 | 4 周 | 外部 API | ✅ 已完成 |
| Agent 自主权管控 | P1 | 2 周 | - | ✅ 已完成 |

### 3.2 中期规划 (3-4 个月)

| 阶段 | 目标 | 关键交付 | 时间 | 状态 |
|------|------|---------|------|------|
| L4 迁移 | AI 持续学习 | 用户偏好记忆系统、历史行为学习 | Month 3 | ✅ 已完成 |
| P10-P12 实现 | 深度认知 | 数字潜意识、AI 视频面诊、双人游戏 | Month 3-4 | 📋 待开始 |
| 自适应 UI | 情境感知渲染 | AI 传声筒、冲突调解组件 | Month 3 | ✅ 已完成 |
| 数字分身预聊 | 差异化功能 | 分身模拟相亲、复盘报告 | Month 4 | ✅ 已完成 |

### 3.3 长期愿景 (5-6 个月)

| 方向 | 目标 | 说明 |
|------|------|------|
| L5 专家级 | AI 领域超越人类 | 长期愿景，需持续投入研发 |
| 移动端应用 | iOS/Android | React Native 跨平台应用 |
| 语音交互 | 语音输入输出 | 更自然的交互方式 |
| AR 约会 | AR 导航 | 增强现实约会体验 |
| 情感计算增强 | 微表情识别 | 更精细的情感分析 |

---

## 四、技术债务追踪

### 4.1 当前债务

| 债务项 | 影响 | 优先级 | 修复方案 | 状态 |
|--------|------|--------|---------|------|
| LLM 降级方案 | 功能受限 | P0 | 语义缓存 + 本地规则引擎 | ✅ 已修复 |
| 外部 API Mock | 数据不真实 | P0 | 代码已实现，待配置 API 密钥 | ⚠️ 配置待完善 |
| 测试覆盖 37% | 质量风险 | P1 | 修复失败测试 + 新增用例 | 📋 进行中 (46% → 80%) |
| Skill 注册缺陷 | 10 个技能未注册 | P0 | 修复 registry.py 缩进问题 | ✅ 已修复 |
| 无流式输出 | 用户体验差 | P0 | SSE 实现 | ✅ 已修复 |
| 无向量缓存 | 成本高 | P1 | Semantic Cache | ✅ 已修复 |

### 4.2 质量目标

| 指标 | 当前值 | 目标值 | 时间 |
|------|--------|--------|------|
| 测试覆盖率 | 46% | >80% | Month 2 |
| API 响应时间 | ~200ms | <100ms | Month 2 |
| LLM 缓存命中率 | 0% | >60% | Month 3 |
| 用户满意度 | - | >4.5/5 | Month 4 |

### 4.3 已完成修复 (v2.2.0)

| 修复项 | 说明 | 日期 |
|--------|------|------|
| LLM 降级方案 | 实现三级降级：API → 语义缓存 → 本地规则引擎 → Mock 数据 | 2026-04-08 |
| Skill 注册缺陷 | 修复 registry.py 函数体外代码块问题，33 个技能全部注册成功 | 2026-04-08 |
| 外部 API 配置 | 在 config.py 中添加完整的外部 API 配置字段 | 2026-04-08 |

---

## 五、商业模式

### 5.1 收入来源

| 来源 | 说明 | 预计占比 |
|------|------|---------|
| 会员订阅 | 三级会员体系（标准/高级/旗舰） | 60% |
| 礼物佣金 | 电商平台分成 (5-15%) | 20% |
| 企业版 | 企业数据看板、员工福利 | 10% |
| 广告 | 品牌合作（谨慎控制） | 10% |

### 5.2 成本结构

| 项目 | 说明 | 占比 |
|------|------|------|
| LLM API | OpenAI/Qwen/GLM调用费用 | 40% |
| 基础设施 | 服务器、数据库、CDN | 30% |
| 第三方 API | 实名认证、地理、礼物 API | 15% |
| 人力成本 | 研发、运营、客服 | 15% |

---

## 六、风险与应对

### 6.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 成本超支 | 中 | 高 | 设置每日 token 限额、语义缓存 |
| 向量数据库性能 | 低 | 中 | 索引优化、定期维护 |
| 第三方 API 不稳定 | 中 | 中 | 降级机制、多供应商备份 |
| 数据泄露 | 低 | 高 | 加密存储、敏感信息过滤 |

### 6.2 合规风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 隐私保护 | 中 | 高 | GDPR 合规、用户授权、信息过滤 |
| 内容安全 | 中 | 高 | AI 内容审核、用户举报机制 |
| 虚假宣传 | 低 | 高 | 实名认证、信用分体系 |

---

## 七、成功指标

### 7.1 产品指标

| 指标 | 当前值 | 目标值 (6 个月) |
|------|--------|------------|
| MAU (月活) | TBD | 100,000 |
| 匹配成功率 | TBD | 30% |
| 付费转化率 | TBD | 10% |
| 用户留存 (30 天) | TBD | 50% |
| NPS (净推荐值) | TBD | >50 |

### 7.2 技术指标

| 指标 | 当前值 | 目标值 (6 个月) |
|------|--------|------------|
| API 响应时间 | ~200ms | <100ms |
| LLM 缓存命中率 | 0% | >60% |
| 测试覆盖率 | 37% | >80% |
| 系统可用性 | 99% | 99.9% |

---

## 附录

### A. 相关文件

- [README.md](./README.md) - 项目入门指南
- [SYSTEM_DOC.md](./SYSTEM_DOC.md) - 系统文档
- [EXTERNAL_API_CONFIG.md](./EXTERNAL_API_CONFIG.md) - 外部 API 配置
- [her_plan.txt](../../../her_plan.txt) - 增强建议来源

### B. 术语表

| 术语 | 定义 |
|------|------|
| SSE | Server-Sent Events，服务器推送事件 |
| 向量数据库 | 用于存储和检索向量数据的数据库（如 Milvus、Pinecone） |
| 数字分身 | 基于用户数据训练的 AI 代理，可模拟用户行为 |
| 语义缓存 | 基于语义相似度而非精确匹配的缓存机制 |
| 冲突处理模型 | 分析用户处理冲突方式的兼容性评估模型 |

---

*让每一次匹配都有意义，让每一段关系都值得期待。*

**最后更新**: 2026-04-08
