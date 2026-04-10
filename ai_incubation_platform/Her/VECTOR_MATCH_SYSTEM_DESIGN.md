# 用户向量匹配系统设计方案

> 版本：v2.2
> 日期：2026-04-10
> 状态：设计中
> 
> **v2.2 更新说明**：
> - **依恋互补因子**：主动增加"焦虑型"与"安全型"匹配权重（治愈型关系），而非简单排除
> - **价值观硬性约束**：关键价值观（生育意愿v17、金钱观v27）差异触发直接分值扣减
> - **冲突修复能力子维度**：沟通维度新增v132-v135，识别"双冷模式"并预警
> - **隐性特征LLM重点**：让LLM分析"声明与行为背离"的成功案例，实现"比你更懂你"
> - **互动深度增长率**：72小时内聊天深度无提升则触发匹配规则复盘
> 
> **v2.1 更新说明**：
> - 依恋类型维度扩展为16维（含压力状态下表现），更新频率调整为"中"
> - 新增成长意愿维度（8维）：匹配不仅是"当下的截面"，更是"未来的轨迹"
> - 新增黑名单区域机制：对不可调和组合实行一票否决
> - 隐性特征向量权重策略：初次匹配时保持克制（0.1-0.2），用于后期复盘
> - 推荐理由改为心理疏导式风格：包含挑战预见和解决方案

---

## 目录

1. [背景与问题](#一背景与问题)
2. [核心思想](#二核心思想)
3. [系统架构](#三系统架构)
4. [用户向量设计](#四用户向量设计)
5. [匹配函数设计](#五匹配函数设计)
6. [向量索引设计](#六向量索引设计)
7. [LLM学习服务](#七llm学习服务)
8. [匹配推荐服务](#八匹配推荐服务)
9. [数据模型设计](#九数据模型设计)
10. [接口设计](#十接口设计)
11. [实现路线图](#十一实现路线图)
12. [效果评估](#十二效果评估)

---

## 一、背景与问题

### 1.1 当前匹配系统的问题

现有匹配系统基于"相似度"假设：两个用户越相似，匹配度越高。这种假设存在根本性缺陷：

```
问题1：相似不等于匹配
├── 两个强势的人 → 相似但会冲突
├── 两个内向的人 → 相似但可能没话聊
└── 焦虑型 × 回避型 → 可能相似但最差组合

问题2：忽略了互补匹配
├── 内向 + 外向 → 可能是完美互补
├── 理性 + 感性 → 可能互补决策
└── 强势 + 温和 → 可能相处和谐

问题3：规则僵化
├── 无法从数据中学习
├── 无法适应不同用户的偏好
└── 无法持续优化
```

### 1.2 多学科匹配理论

根据心理学、社会学、生物学等多学科研究，匹配是多维度的：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  维度分类                                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【必须相似】                                                            │
│  ├── 价值观（人生目标、婚恋观、家庭观）                                  │
│  ├── 依恋类型（安全型最佳）                                              │
│  └── 消费观念                                                            │
│                                                                         │
│  【相似更好】                                                            │
│  ├── 教育背景                                                            │
│  ├── 生活节奏                                                            │
│  └── 沟通风格                                                            │
│                                                                         │
│  【可以互补】                                                            │
│  ├── 性格（内向+外向）                                                   │
│  ├── 技能（你会的我不会）                                                │
│  └── 社交风格                                                            │
│                                                                         │
│  【不能太相似】                                                           │
│  ├── 强势程度（两个都强势会冲突）                                        │
│  └── 控制欲（都太强会互相折磨）                                          │
│                                                                         │
│  【有交集即可】                                                           │
│  ├── 兴趣爱好                                                            │
│  └── 话题偏好                                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心思想

### 2.1 范式转变

```
传统匹配：相似度 = distance(A, B) 越小越好
─────────────────────────────────────────────
问题：假设"越近越好"，忽略互补匹配

新匹配：  匹配 = B ∈ f(A)
─────────────────────────────────────────────
含义：B 是否在 A 的匹配区域内
优势：不假设"越近越好"，支持相似和互补
```

### 2.2 核心概念

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  用户向量：                                                              │
│  将用户映射到 N 维向量空间中的一个点                                     │
│  用户 = [v1, v2, v3, ..., vN]                                          │
│                                                                         │
│  匹配区域：                                                              │
│  一个或多个"球体"区域，区域内的人都可能匹配                              │
│  区域 = {center, radius, weight, type}                                  │
│                                                                         │
│  匹配函数：                                                              │
│  f(用户向量) → [匹配区域1, 匹配区域2, ...]                              │
│  由 LLM 从成功/失败案例中学习得到                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 图解对比

```
旧方案：找相似的人

              用户A
               ●
              ╱│╲
             ╱ │ ╲
            ╱  │  ╲
           ●   ●   ●  ← 只找附近的人
           
           
新方案：找匹配区域的人

              用户A
               ●
               
          ●           ← 匹配区域1（互补型）
          
          
               ●      ← 匹配区域2（相似型）
               
               
                    ● ← 匹配区域3（混合型）
                    
这些区域可能离用户A很远，但里面的人才是适合的！
```

---

## 三、系统架构

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         用户向量匹配系统                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    第一层：用户向量化                            │    │
│  │                                                                   │    │
│  │   用户数据（资料+行为+对话）→ 向量编码器 → 用户向量              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第二层：匹配区域计算                              │    │
│  │                                                                   │    │
│  │   用户向量 → 匹配函数 f() → 匹配区域列表                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第三层：候选查询                                  │    │
│  │                                                                   │    │
│  │   匹配区域 → 向量索引（ANN）→ 候选用户列表                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 第四层：LLM 深度判断                              │    │
│  │                                                                   │    │
│  │   候选用户 → LLM 分析 → 最终推荐 + 匹配理由                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 离线：LLM 学习服务                                │    │
│  │                                                                   │    │
│  │   成功/失败案例 → LLM 分析 → 匹配规则/模型参数                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块划分

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| VectorEncoder | 用户向量化 | 用户资料、行为、对话 | 128维向量 |
| MatchFunctionService | 计算匹配区域 | 用户向量 | 匹配区域列表 |
| VectorIndexService | 区域查询 | 匹配区域 | 候选用户 |
| LLMLearningService | 学习匹配规则 | 成功/失败案例 | 匹配规则表 |
| MatchRecommendService | 整合推荐 | 用户ID | 推荐列表+理由 |
| CaseCollectionService | 案例收集 | 用户行为、反馈 | 案例数据 |

---

## 四、用户向量设计

### 4.1 向量维度定义（144维）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      用户向量 = 144 维                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  维度区间        │ 含义              │ 数据来源           │ 更新频率    │
│  ───────────────┼───────────────────┼────────────────────┼────────────  │
│  [0-15]         │ 人口统计学         │ 注册资料           │ 低          │
│  [16-31]        │ 价值观             │ 问卷/行为推断      │ 中          │
│  [32-47]        │ 大五人格           │ 问卷/行为推断      │ 中          │
│  [48-63]        │ 依恋类型           │ 问卷/行为推断      │ 中          │
│  [64-71]        │ 成长意愿           │ 行为反馈/冲突处理  │ 中          │
│  [72-87]        │ 兴趣爱好           │ 选择/行为          │ 中          │
│  [88-103]       │ 生活方式           │ 选择/行为          │ 中          │
│  [104-119]      │ 行为模式           │ 滑动/浏览行为      │ 高          │
│  [120-135]      │ 沟通风格           │ 聊天内容           │ 高          │
│  [136-143]      │ 隐性特征           │ 行为-资料差异      │ 高          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 各维度详细定义

#### 4.2.1 人口统计学维度 [0-15]

```
维度 0-2: 年龄相关
├── v0: 年龄归一化 (age / 100)
├── v1: 年龄偏好下限归一化
└── v2: 年龄偏好上限归一化

维度 3-5: 性别相关
├── v3: 性别编码 (男=0, 女=1, 其他=0.5)
├── v4: 性取向编码
└── v5: 性别偏好编码

维度 6-9: 地理相关
├── v6: 城市层级 (一线=1.0, 二线=0.7, ...)
├── v7: 是否接受异地 (0/1)
├── v8: 经度归一化
└── v9: 纬度归一化

维度 10-15: 基础属性
├── v10: 教育程度归一化
├── v11: 身高归一化
├── v12: 收入区间编码
├── v13: 职业类型编码
├── v14: 是否有房
└── v15: 是否有车
```

#### 4.2.2 价值观维度 [16-31]

> **设计说明**：价值观相似是底线，但其重要程度是不等的。例如，**"是否要孩子"（v17）和"金钱观"（v27）往往具有"一票否决"的效力**。对于这些关键价值观维度，如果差异超过阈值，无论其他维度（如兴趣、性格）多匹配，都应直接大幅降低整体匹配分值，而非简单的距离加权。

```
维度 16-21: 家庭观念
├── v16: 家庭重要程度 (0-1)
├── v17: 是否想要孩子 (0-1)           【一票否决维度】
├── v18: 孩子数量偏好
├── v19: 与父母同住意愿
├── v20: 家务分配观念
└── v21: 传统观念程度

维度 22-26: 事业观念
├── v22: 事业重要程度
├── v23: 工作生活平衡偏好
├── v24: 职业稳定性偏好
├── v25: 创业意愿
└── v26: 职业发展优先级

维度 27-31: 金钱观念
├── v27: 消费观念 (节俭-享受)        【一票否决维度】
├── v28: 理财意识
├── v29: 风险偏好
├── v30: 储蓄习惯
└── v31: 消费决策风格
```

**价值观硬性约束规则示例**：

```python
# 价值观一票否决规则
VALUE_VETO_RULES = [
    {
        "dimension": "v17",  # 是否想要孩子
        "dimension_idx": 17,
        "veto_threshold": 0.5,  # 差异超过0.5触发
        "veto_action": "score_penalty",  # 直接扣减50%匹配分
        "penalty_factor": 0.5,
        "reason": "生育意愿分歧是根本性冲突，无法调和"
    },
    {
        "dimension": "v27",  # 消费观念
        "dimension_idx": 27,
        "veto_threshold": 0.7,  # 差异超过0.7触发
        "veto_action": "score_penalty",
        "penalty_factor": 0.4,
        "reason": "金钱观分歧会导致持续的日常冲突"
    }
]

def apply_value_veto(user_a_vector, user_b_vector, base_score):
    """应用价值观硬性约束"""
    for rule in VALUE_VETO_RULES:
        dim_idx = rule["dimension_idx"]
        diff = abs(user_a_vector[dim_idx] - user_b_vector[dim_idx])
        
        if diff > rule["veto_threshold"]:
            base_score *= rule["penalty_factor"]
            # 记录否决原因
            logger.info(f"Value veto triggered: {rule['reason']}")
    
    return base_score
```

#### 4.2.3 大五人格维度 [32-47]

```
维度 32-35: 开放性 (Openness)
├── v32: 新事物接受程度
├── v33: 好奇心强度
├── v34: 创造力
└── v35: 审美敏感度

维度 36-39: 尽责性 (Conscientiousness)
├── v36: 计划性
├── v37: 自律程度
├── v38: 可靠性
└── v39: 目标导向

维度 40-43: 外向性 (Extraversion)
├── v40: 社交活跃度
├── v41: 精力水平
├── v42: 乐观程度
└── v43: 自信程度

维度 44-47: 宜人性 (Agreeableness) + 神经质 (Neuroticism)
├── v44: 信任程度
├── v45: 合作意愿
├── v46: 情绪稳定性
└── v47: 抗压能力
```

#### 4.2.4 依恋类型维度 [48-63]

> **设计说明**：依恋类型在实际心理学观测中具有**动态流动性**。一个"焦虑型"用户在遇到极其稳定的"安全型"伴侣后，可能会表现出安全倾向；反之，两个"焦虑型"相遇会触发严重的防御机制。此外，人在热恋期（数据采集初期）往往都会伪装成"安全型"，只有在冲突（行为数据）发生后，真实的依恋底色才会显露。因此，依恋维度的更新频率调整为"中"，并引入"压力状态下的依恋表现"子维度。
>
> **依恋互补因子**：匹配函数不应只看当前得分，更应加入"依恋互补因子"。**主动增加"焦虑型"与"安全型"的匹配权重**，因为安全型伴侣能帮助焦虑型逐步向安全型转化，这是正向的"治愈关系"。而不是简单地排除回避型。

```
维度 48-51: 依恋类型编码（基础）
├── v48: 安全型得分
├── v49: 焦虑型得分
├── v50: 回避型得分
└── v51: 恐惧型得分

维度 52-55: 关系模式
├── v52: 亲密需求程度
├── v53: 独立需求程度
├── v54: 安全感需求
└── v55: 承诺意愿

维度 56-63: 压力状态下的依恋表现（动态）
├── v56: 冲突时的情绪反应模式（冷静/激动/回避）
├── v57: 冲突时的沟通倾向（主动解决/被动等待/逃避）
├── v58: 被拒绝时的反应（接受/焦虑追问/冷漠）
├── v59: 伴侣忙碌时的反应（独立等待/焦虑需求/抱怨）
├── v60: 长期分离时的状态（稳定/焦虑波动/疏离）
├── v61: 争吵后的恢复速度
├── v62: 对伴侣负面情绪的容忍度
└── v63: 依恋类型的实测置信度（问卷 vs 行为一致性）
```

**依恋互补规则示例**：

```python
# 焦虑型 + 安全型：正向治愈组合（加分）
ATTACHMENT_HEALING_COMBO = {
    "trigger": {"attachment_anxious": "> 0.6"},
    "match_bonus": {
        "condition": {"attachment_secure": "> 0.7"},
        "bonus_factor": 1.3,  # 增加30%匹配权重
        "healing_potential": "high",  # 标记为"治愈型"关系
    },
    "reason": "安全型伴侣能帮助焦虑型逐步建立安全感"
}

# 焦虑型 + 回避型：恶性循环组合（一票否决）
# 已在黑名单区域中定义
```

#### 4.2.5 成长意愿维度 [64-71]

> **设计说明**：婚姻是一场长跑，匹配不仅是"当下的截面"，更是"未来的轨迹"。两个价值观 80% 匹配但都拒绝改变的人，未必比得上两个价值观 60% 匹配但都愿意为了对方磨合的人。此维度通过用户对"冲突处理方式"的反馈数据来提取。

```
维度 64-71: 成长意愿编码
├── v64: 自我改变意愿（愿意为关系调整自己）
├── v65: 接纳差异意愿（愿意理解并接纳伴侣的不同）
├── v66: 学习意愿（愿意学习关系技巧、沟通方法）
├── v67: 反思能力（冲突后能否自我反思）
├── v68: 妥协意愿（愿意在非核心问题上妥协）
├── v69: 持续成长意识（认为关系需要持续经营）
├── v70: 危机应对信心（相信两人能共同度过困难）
└── v71: 成长轨迹一致性（希望和伴侣一起成长的方向）
```

#### 4.2.6 兴趣爱好维度 [72-87]

```
维度 72-87: 兴趣嵌入向量
└── 从用户选择的兴趣标签和实际行为中学习得到
    使用 One-Hot 编码 + 降维 或 预训练兴趣嵌入
```

#### 4.2.7 生活方式维度 [88-103]

```
维度 88-95: 日常习惯
├── v88: 作息类型 (早鸟-夜猫)
├── v89: 运动频率
├── v90: 社交频率
├── v91: 独处需求
├── v92: 娱乐偏好
├── v93: 饮食偏好
├── v94: 旅行频率
└── v95: 周末活动偏好

维度 96-103: 生活态度
├── v96: 生活节奏
├── v97: 压力应对方式
├── v98: 决策风格
├── v99: 冲突处理方式
├── v100: 沟通偏好
├── v101: 表达风格
├── v102: 情感表达方式
└── v103: 承诺态度
```

#### 4.2.8 行为模式维度 [104-119]

```
维度 104-111: 滑动行为模式
├── v104-v107: 喜欢的用户类型特征（从滑动历史学习）
├── v108-v111: 滑动偏好特征（喜欢率、浏览时长等）

维度 112-119: 互动行为模式
├── v112-v115: 主动/被动模式
└── v116-v119: 互动频率、深度特征
```

#### 4.2.9 沟通风格维度 [120-135]

> **设计说明**：关系能否长久，不取决于"不吵架"，而取决于"吵架后如何修复"。两个沟通风格都偏向"冷战/回避"的人即便相似度再高，一旦产生矛盾就是毁灭性的。系统需要识别这种**"双冷模式"**并预警。

```
维度 120-127: 语言风格
├── v120-v123: 正式/随意程度
├── v124-v127: 幽默/严肃程度

维度 128-135: 沟通模式 + 冲突修复能力
├── v128-v131: 话题偏好
├── v132: 冲突时的沟通方式（主动沟通/冷战/回避）
├── v133: 冷战倾向度（高=易陷入冷战）
├── v134: 冲突修复意愿（愿意主动修复关系）
├── v135: 冲突修复能力（道歉/妥协/寻求第三方帮助）
```

**"双冷模式"预警规则**：

```python
# 双冷模式预警：双方都是冷战倾向者
COLD_MODE_WARNING = {
    "trigger_conditions": [
        {"dimension": "v132", "operator": "==", "value": "cold_war"},  # 双方都是冷战型
        {"dimension": "v133", "operator": ">", "value": 0.6},  # 双方冷战倾向都高
    ],
    "action": "warning",  # 不是一票否决，而是预警
    "warning_message": "你们都倾向于冷战回避，一旦产生矛盾可能难以修复。建议你们在学习如何主动沟通后再尝试匹配。",
    "score_penalty": 0.3,  # 降低匹配分30%
    "alternative_recommendation": "建议匹配一个冲突修复能力强、主动沟通型的伴侣"
}

def check_cold_mode(user_a_vector, user_b_vector):
    """检查是否为双冷模式"""
    a_cold = user_a_vector[133] > 0.6  # 冷战倾向
    b_cold = user_b_vector[133] > 0.6
    
    a_avoid = user_a_vector[132] in ["cold_war", "avoid"]  # 冲突沟通方式
    b_avoid = user_b_vector[132] in ["cold_war", "avoid"]
    
    if a_cold and b_cold and a_avoid and b_avoid:
        return True, COLD_MODE_WARNING["warning_message"]
    return False, None
```

#### 4.2.10 隐性特征维度 [136-143]

> **伦理与准确性说明**：从"说的"和"做的"差异中推断隐性偏好（例如嘴上说喜欢安静，实际喜欢活跃型）存在"社会期许偏差"风险。用户可能因为自卑或外界压力而否定自己的真实渴望。如果 LLM 强行将其归类为"口是心非"，可能会引发用户的反感，甚至造成"信息茧房"，让用户困在自己潜意识的欲望里无法成长。
>
> **权重策略**：隐性特征向量在初次匹配时应**保持克制**，权重设置为 0.1-0.2，更多用于后期复盘和推荐理由的微调，而非主导匹配决策。
>
> **LLM学习重点**：隐性特征挖掘应作为 LLMLearningService 的核心任务。让 LLM **重点分析那些"实际行为背离注册标签"的成功案例**——这往往是算法实现"比你更懂你"的关键突破口。例如：用户声明喜欢安静内向型，但实际滑动行为显示偏好外向活跃型，且与外向型用户匹配后关系持续良好。这种案例揭示了用户的潜意识需求，是比问卷更真实的匹配依据。

```
维度 136-143: 隐性偏好
├── v136: 声明偏好 vs 实际行为差异度（整体）
├── v137: 实际偏好的性格类型（从行为推断）
├── v138: 实际偏好的生活方式类型
├── v139: 实际偏好的沟通风格类型
├── v140: 潜意识需求推断（可能未意识到的）
├── v141: 社会期许偏差修正系数
├── v142: 隐性特征置信度（行为样本量 vs 声明一致性）
└── v143: 隐性特征的推荐权重（系统控制，默认 0.1）
```

**隐性特征学习示例**：

```python
# LLM 分析"声明与行为背离"的成功案例
IMPLICIT_LEARNING_PROMPT = """
请分析这个案例中用户的隐性偏好：

## 用户声明偏好
- 喜欢安静内向型
- 重视事业
- 不喜欢太强势的人

## 用户实际行为
- 滑动历史：70%选择了外向活跃型
- 实际互动：与外向型用户的聊天时长是内向型的3倍
- 匹配结果：与一位"事业优先但性格外向"的用户关系持续良好

## 分析要求
1. 为什么用户的声明与行为存在差异？
2. 这种差异揭示了什么潜意识需求？
3. 如何在匹配中安全地利用这一发现？

## 输出格式
{
  "implicit_preference": "...",
  "preference_reason": "...",
  "safe_usage_strategy": "...",
  "confidence": 0.85
}
"""
```

### 4.3 向量编码器实现

```python
class UserVectorEncoder:
    """用户向量编码器"""
    
    def encode(self, user_data: dict) -> np.ndarray:
        """
        将用户数据编码为144维向量
        
        Args:
            user_data: 用户资料、行为、对话数据
            
        Returns:
            144维向量
        """
        vector = np.zeros(144)
        
        # 1. 人口统计学编码 (规则映射)
        vector[0:16] = self._encode_demographics(user_data)
        
        # 2. 价值观编码 (问卷 + 行为推断)
        vector[16:32] = self._encode_values(user_data)
        
        # 3. 大五人格编码 (问卷)
        vector[32:48] = self._encode_personality(user_data)
        
        # 4. 依恋类型编码 (问卷 + 行为推断)
        vector[48:64] = self._encode_attachment(user_data)
        
        # 5. 成长意愿编码 (行为反馈)
        vector[64:72] = self._encode_growth_willingness(user_data)
        
        # 6. 兴趣编码 (嵌入模型)
        vector[72:88] = self._encode_interests(user_data)
        
        # 7. 生活方式编码 (选择 + 行为)
        vector[88:104] = self._encode_lifestyle(user_data)
        
        # 8. 行为模式编码 (神经网络)
        vector[104:120] = self._encode_behavior(user_data)
        
        # 9. 沟通风格编码 (NLP模型)
        vector[120:136] = self._encode_communication(user_data)
        
        # 10. 隐性特征编码 (反向推断，低权重)
        vector[136:144] = self._encode_implicit(user_data)
        
        return vector
```

---

## 五、匹配函数设计

### 5.1 匹配区域定义

```python
@dataclass
class MatchRegion:
    """匹配区域"""
    center: np.ndarray      # 区域中心点 (128维)
    radius: float           # 区域半径
    weight: float           # 区域权重 (0-1)
    region_type: str        # 区域类型: "similar" | "complementary" | "mixed"
    description: str        # 区域描述
```

### 5.2 匹配规则定义

> **设计说明**：在婚恋匹配中，有些组合是"剧毒"的，例如"严重的自恋倾向 × 极度低自尊"或"焦虑型 × 回避型"。如果仅仅是降低权重或增加距离，系统仍可能将其匹配。因此，在 MatchRule 中增加 **BlacklistRegion（黑名单区域）**，对于某些特定的向量组合实行一票否决制，而非加权计算。

```python
@dataclass
class MatchRule:
    """匹配规则"""
    rule_id: str                    # 规则ID
    trigger_condition: dict         # 触发条件
    region_definition: dict         # 区域定义
    blacklist_regions: List[dict]   # 黑名单区域（一票否决）
    confidence: float               # 规则置信度
    support_count: int              # 支持案例数
    learned_from: List[str]         # 学习来源


@dataclass
class BlacklistRegion:
    """黑名单区域：一票否决的不可调和组合"""
    dimension_conditions: List[dict]  # 维度条件组合
    reason: str                       # 黑名单原因（心理学依据）
    severity: str                     # 严重程度：critical, high, medium
    learned_from: List[str]           # 学习来源案例
```

### 5.3 黑名单区域定义示例

```python
# 黑名单区域1：焦虑型 × 回避型（最差依恋组合）
BlacklistRegion(
    dimension_conditions=[
        {"dimension": "attachment_anxious", "operator": ">", "value": 0.6},
        {"dimension": "attachment_avoidant", "operator": ">", "value": 0.6},
    ],
    reason="焦虑型与回避型组合会触发'追逐-逃避'恶性循环，导致双方持续消耗",
    severity="critical",
    learned_from=["case_001", "case_002", ...]
)

# 黑名单区域2：高自恋倾向 × 低自尊
BlacklistRegion(
    dimension_conditions=[
        {"dimension": "narcissism", "operator": ">", "value": 0.7},
        {"dimension": "self_esteem", "operator": "<", "value": 0.3},
    ],
    reason="高自恋倾向者倾向于利用和贬低低自尊者，形成不平等的控制关系",
    severity="critical",
    learned_from=["case_003", "case_004", ...]
)

# 黑名单区域3：极端控制欲 × 高独立需求
BlacklistRegion(
    dimension_conditions=[
        {"dimension": "control_need", "operator": ">", "value": 0.8},
        {"dimension": "independence_need", "operator": ">", "value": 0.7},
    ],
    reason="极端控制欲与高独立需求是根本性冲突，无法调和",
    severity="high",
    learned_from=["case_005", "case_006", ...]
)
```

### 5.3 示例规则

```python
# 规则1: 内向者匹配规则
MatchRule(
    rule_id="rule_001",
    trigger_condition={
        "dimension": "extraversion",  # 外向性维度
        "operator": "<",
        "value": 0.3,                 # 内向
    },
    region_definition={
        "region_1": {                 # 互补区域
            "type": "complementary",
            "conditions": [
                {"dimension": "extraversion", "range": [0.6, 1.0]},  # 外向
                {"dimension": "dominance", "range": [0.0, 0.5]},     # 温和
            ],
            "weight": 0.5,
        },
        "region_2": {                 # 相似区域
            "type": "similar",
            "conditions": [
                {"dimension": "extraversion", "range": [0.0, 0.4]},  # 也内向
                {"dimension": "shared_interests", "operator": ">=", "value": 2},  # 有共同兴趣
            ],
            "weight": 0.3,
        },
    },
    confidence=0.85,
    support_count=1500,
)

# 规则2: 强势者匹配规则
MatchRule(
    rule_id="rule_002",
    trigger_condition={
        "dimension": "dominance",
        "operator": ">",
        "value": 0.7,
    },
    region_definition={
        "region_1": {                 # 只有一个区域
            "type": "complementary",
            "conditions": [
                {"dimension": "dominance", "range": [0.0, 0.4]},  # 必须温和
            ],
            "weight": 1.0,            # 权重100%
        },
    },
    confidence=0.92,
    support_count=800,
)

# 规则3: 焦虑型依恋匹配规则
MatchRule(
    rule_id="rule_003",
    trigger_condition={
        "dimension": "attachment_anxious",
        "operator": ">",
        "value": 0.6,
    },
    region_definition={
        "region_1": {
            "type": "complementary",
            "conditions": [
                {"dimension": "attachment_secure", "operator": ">", "value": 0.7},  # 安全型
            ],
            "weight": 0.8,
        },
    },
    exclude_conditions=[              # 排除条件
        {"dimension": "attachment_avoidant", "operator": ">", "value": 0.6},  # 不能是回避型
    ],
    confidence=0.88,
    support_count=600,
)
```

### 5.4 匹配函数实现

```python
class MatchFunctionService:
    """匹配函数服务"""
    
    def __init__(self):
        self.rules: List[MatchRule] = []
        self.load_rules()
    
    def compute_match_regions(self, user_vector: np.ndarray) -> List[MatchRegion]:
        """
        计算用户的匹配区域
        
        Args:
            user_vector: 用户向量
            
        Returns:
            匹配区域列表
        """
        regions = []
        
        # 遍历所有规则，找到触发的规则
        for rule in self.rules:
            if self._check_trigger(rule.trigger_condition, user_vector):
                # 生成匹配区域
                for region_def in rule.region_definition.values():
                    region = self._build_region(region_def, user_vector)
                    regions.append(region)
        
        # 如果没有规则触发，使用默认区域
        if not regions:
            regions = self._get_default_regions(user_vector)
        
        return regions
    
    def _check_trigger(self, condition: dict, vector: np.ndarray) -> bool:
        """检查是否触发规则"""
        dimension = condition["dimension"]
        operator = condition["operator"]
        value = condition["value"]
        
        dim_value = self._get_dimension_value(dimension, vector)
        
        if operator == ">":
            return dim_value > value
        elif operator == "<":
            return dim_value < value
        elif operator == ">=":
            return dim_value >= value
        elif operator == "<=":
            return dim_value <= value
        elif operator == "==":
            return abs(dim_value - value) < 0.1
        return False
    
    def _build_region(self, region_def: dict, user_vector: np.ndarray) -> MatchRegion:
        """构建匹配区域"""
        # 根据条件计算区域中心点
        center = np.zeros(144)
        
        for condition in region_def.get("conditions", []):
            dimension = condition["dimension"]
            if "range" in condition:
                # 区域中心取范围中点
                value = (condition["range"][0] + condition["range"][1]) / 2
            elif "value" in condition:
                value = condition["value"]
            else:
                continue
            
            # 设置对应维度
            self._set_dimension_value(dimension, value, center)
        
        # 其他维度继承用户向量的值（相似部分）
        for i in range(144):
            if center[i] == 0:
                center[i] = user_vector[i]
        
        return MatchRegion(
            center=center,
            radius=region_def.get("radius", 0.2),
            weight=region_def.get("weight", 0.5),
            region_type=region_def.get("type", "mixed"),
            description=region_def.get("description", ""),
        )
    
    def check_blacklist(self, user_a_vector: np.ndarray, user_b_vector: np.ndarray) -> Tuple[bool, Optional[str]]:
        """
        检查是否命中黑名单区域（一票否决）
        
        Args:
            user_a_vector: 用户A向量
            user_b_vector: 用户B向量
            
        Returns:
            (是否命中黑名单, 原因说明)
        """
        for blacklist in self.blacklist_regions:
            # 检查两个用户的向量是否都满足黑名单条件
            a_matches = self._check_blacklist_conditions(blacklist.dimension_conditions, user_a_vector)
            b_matches = self._check_blacklist_conditions(blacklist.dimension_conditions, user_b_vector)
            
            # 如果两个用户都命中黑名单条件，则一票否决
            if a_matches and b_matches:
                return True, blacklist.reason
            
            # 交叉检查：A命中某个条件，B命中另一个条件
            if self._check_cross_blacklist(blacklist.dimension_conditions, user_a_vector, user_b_vector):
                return True, blacklist.reason
        
        return False, None
    
    def _check_blacklist_conditions(self, conditions: List[dict], vector: np.ndarray) -> bool:
        """检查向量是否满足所有黑名单条件"""
        matches = 0
        for condition in conditions:
            if self._check_trigger(condition, vector):
                matches += 1
        return matches == len(conditions)
    
    def _check_cross_blacklist(self, conditions: List[dict], vec_a: np.ndarray, vec_b: np.ndarray) -> bool:
        """交叉检查黑名单：A命中某条件，B命中另一条件"""
        a_hits = [self._check_trigger(c, vec_a) for c in conditions]
        b_hits = [self._check_trigger(c, vec_b) for c in conditions]
        
        # 至少各命中一个条件，且合计命中所有条件
        return any(a_hits) and any(b_hits) and (sum(a_hits) + sum(b_hits) >= len(conditions))
```

---

## 六、向量索引设计

### 6.1 索引选型

```
┌─────────────────────────────────────────────────────────────────────────┐
│  向量索引选型对比                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  方案          │ 优点                    │ 缺点            │ 推荐度     │
│  ─────────────┼─────────────────────────┼─────────────────┼───────────  │
│  FAISS        │ 快速、开源、可本地部署   │ 需要自己管理     │ ⭐⭐⭐⭐    │
│  Milvus       │ 分布式、功能全          │ 运维复杂         │ ⭐⭐⭐⭐    │
│  Pinecone     │ 托管服务、简单          │ 收费、数据出境   │ ⭐⭐⭐     │
│  pgvector     │ 与PostgreSQL集成        │ 性能一般         │ ⭐⭐⭐     │
│                                                                         │
│  推荐：FAISS（初期）+ Milvus（规模化后）                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 区域查询实现

```python
class VectorIndexService:
    """向量索引服务"""
    
    def __init__(self, dimension: int = 144):
        self.dimension = dimension
        self.index = None
        self.user_id_map = {}  # 向量索引 -> 用户ID
    
    def build_index(self, user_vectors: Dict[str, np.ndarray]):
        """构建向量索引"""
        import faiss
        
        # 收集所有向量
        vectors = []
        user_ids = []
        for user_id, vector in user_vectors.items():
            vectors.append(vector)
            user_ids.append(user_id)
        
        vectors = np.array(vectors).astype('float32')
        
        # 创建 FAISS 索引
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(vectors)
        
        # 建立映射
        self.user_id_map = {i: user_ids[i] for i in range(len(user_ids))}
    
    def search_in_regions(
        self,
        regions: List[MatchRegion],
        exclude_user_ids: List[str] = None,
        limit: int = 100
    ) -> List[Tuple[str, float]]:
        """
        在匹配区域内搜索用户
        
        Args:
            regions: 匹配区域列表
            exclude_user_ids: 排除的用户ID
            limit: 返回数量上限
            
        Returns:
            [(用户ID, 距离), ...]
        """
        results = []
        exclude_set = set(exclude_user_ids or [])
        
        for region in regions:
            # 区域查询：距离中心点不超过半径
            distances, indices = self.index.range_search(
                region.center.reshape(1, -1).astype('float32'),
                region.radius ** 2  # FAISS 使用距离平方
            )
            
            for idx, dist in zip(indices, distances):
                user_id = self.user_id_map.get(idx)
                if user_id and user_id not in exclude_set:
                    # 加权距离
                    weighted_dist = dist * (1 - region.weight)
                    results.append((user_id, weighted_dist))
        
        # 去重，保留最小距离
        unique_results = {}
        for user_id, dist in results:
            if user_id not in unique_results or unique_results[user_id] > dist:
                unique_results[user_id] = dist
        
        # 按距离排序
        sorted_results = sorted(unique_results.items(), key=lambda x: x[1])
        
        return sorted_results[:limit]
```

---

## 七、LLM学习服务

### 7.1 学习流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      LLM 学习匹配规则                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  步骤1：收集案例                                                        │
│  ─────────────────────────────────────────────────────                  │
│  成功案例：已婚、长期恋爱、互相匹配+聊天活跃                             │
│  失败案例：短期分手、互相匹配但无互动、投诉拉黑                          │
│                                                                         │
│  步骤2：LLM 分析                                                        │
│  ─────────────────────────────────────────────────────                  │
│  对每对案例，让 LLM 分析：                                              │
│  - 他们的向量特征                                                       │
│  - 为什么成功/失败                                                      │
│  - 哪些维度关键                                                         │
│                                                                         │
│  步骤3：总结规则                                                        │
│  ─────────────────────────────────────────────────────                  │
│  让 LLM 总结规律：                                                      │
│  - 对于某类用户，匹配区域在哪                                           │
│  - 哪些组合要避免                                                       │
│  - 哪些维度最重要                                                       │
│                                                                         │
│  步骤4：验证与审核                                                      │
│  ─────────────────────────────────────────────────────                  │
│  人工审核规则合理性                                                     │
│  在测试集上验证效果                                                     │
│  上线新规则                                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 LLM Prompt 设计

```python
LEARN_RULES_PROMPT = """
你是一位拥有20年经验的专业婚恋顾问，精通心理学、社会学和人际关系学。

请分析以下成功和失败案例，总结出匹配规则。

## 成功案例 (100对)

{success_cases}

## 失败案例 (50对)

{failure_cases}

## 分析要求

请从以下维度分析每对案例：
1. 心理学维度：大五人格、依恋类型、情绪模式
2. 社会学维度：教育背景、家庭背景、职业发展
3. 价值观维度：人生目标、婚恋观念、金钱观
4. 沟通维度：表达风格、话题偏好

## 输出格式

请返回 JSON 格式的匹配规则列表：

```json
{
  "rules": [
    {
      "rule_name": "内向者匹配规则",
      "trigger_condition": {
        "dimension": "extraversion",
        "operator": "<",
        "value": 0.3
      },
      "match_regions": [
        {
          "type": "complementary",
          "conditions": [
            {"dimension": "extraversion", "range": [0.6, 1.0]},
            {"dimension": "dominance", "range": [0.0, 0.5]}
          ],
          "weight": 0.5
        },
        {
          "type": "similar",
          "conditions": [
            {"dimension": "extraversion", "range": [0.0, 0.4]},
            {"dimension": "shared_interests", "operator": ">=", "value": 2}
          ],
          "weight": 0.3
        }
      ],
      "exclude_conditions": [],
      "confidence": 0.85,
      "reasoning": "分析理由..."
    }
  ]
}
```

只返回 JSON，不要其他内容。
"""

ANALYZE_CASE_PROMPT = """
请分析这对用户为什么成功/失败。

## 用户A资料

{user_a_profile}

## 用户B资料

{user_b_profile}

## 结果

{outcome}

## 分析要求

1. 从向量维度分析两人的特征
2. 分析匹配/不匹配的原因
3. 指出关键维度

## 输出格式

```json
{
  "user_a_vector_summary": {
    "personality": "内向、温和...",
    "values": "重视家庭...",
    "attachment": "安全型"
  },
  "user_b_vector_summary": {
    "personality": "外向、活泼...",
    "values": "重视事业...",
    "attachment": "安全型"
  },
  "match_analysis": {
    "complementary_dimensions": ["性格互补"],
    "similar_dimensions": ["价值观相似"],
    "conflict_dimensions": []
  },
  "key_success_factors": ["性格互补", "价值观一致"],
  "key_failure_factors": [],
  "lesson": "内向温和的人适合外向活泼的人..."
}
```

只返回 JSON。
"""
```

### 7.3 学习服务实现

```python
class LLMLearningService:
    """LLM 学习服务"""
    
    def __init__(self, llm_service):
        self.llm = llm_service
    
    async def learn_match_rules(
        self,
        success_cases: List[MatchCase],
        failure_cases: List[MatchCase]
    ) -> List[MatchRule]:
        """
        从案例中学习匹配规则
        
        Args:
            success_cases: 成功案例列表
            failure_cases: 失败案例列表
            
        Returns:
            匹配规则列表
        """
        # 1. 构建案例摘要
        success_summaries = await self._summarize_cases(success_cases)
        failure_summaries = await self._summarize_cases(failure_cases)
        
        # 2. 调用 LLM 学习规则
        prompt = LEARN_RULES_PROMPT.format(
            success_cases=json.dumps(success_summaries, ensure_ascii=False, indent=2),
            failure_cases=json.dumps(failure_summaries, ensure_ascii=False, indent=2)
        )
        
        response = await self.llm.call(prompt)
        rules_data = json.loads(response)
        
        # 3. 解析规则
        rules = []
        for rule_data in rules_data.get("rules", []):
            rule = MatchRule(
                rule_id=f"rule_{uuid.uuid4().hex[:8]}",
                trigger_condition=rule_data["trigger_condition"],
                region_definition=rule_data["match_regions"],
                confidence=rule_data.get("confidence", 0.5),
                support_count=len(success_cases),
                learned_from=[c.case_id for c in success_cases[:100]],
            )
            rules.append(rule)
        
        return rules
    
    async def _summarize_cases(self, cases: List[MatchCase]) -> List[dict]:
        """总结案例"""
        summaries = []
        for case in cases:
            summary = {
                "user_a_id": case.user_a_id,
                "user_b_id": case.user_b_id,
                "user_a_vector_summary": self._summarize_vector(case.user_a_vector),
                "user_b_vector_summary": self._summarize_vector(case.user_b_vector),
                "outcome": case.outcome,
                "duration_days": case.duration_days,
            }
            summaries.append(summary)
        return summaries
    
    def _summarize_vector(self, vector: np.ndarray) -> dict:
        """总结向量特征"""
        return {
            "age": vector[0],
            "extraversion": vector[40],
            "dominance": self._get_dimension("dominance", vector),
            "attachment_style": self._get_attachment_style(vector),
            "family_oriented": vector[16],
            # ... 其他关键维度
        }
```

---

## 八、匹配推荐服务

### 8.1 服务实现

```python
class MatchRecommendService:
    """匹配推荐服务"""
    
    def __init__(self):
        self.vector_encoder = UserVectorEncoder()
        self.match_function = MatchFunctionService()
        self.vector_index = VectorIndexService()
        self.llm_service = None  # LLM 服务
    
    async def get_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        use_llm_analysis: bool = True
    ) -> List[Recommendation]:
        """
        获取匹配推荐
        
        Args:
            user_id: 用户ID
            limit: 推荐数量
            use_llm_analysis: 是否使用 LLM 深度分析
            
        Returns:
            推荐列表
        """
        # 1. 获取用户向量
        user_vector = await self._get_user_vector(user_id)
        if user_vector is None:
            raise ValueError(f"User vector not found: {user_id}")
        
        # 2. 计算匹配区域
        match_regions = self.match_function.compute_match_regions(user_vector)
        
        # 3. 在区域内搜索候选
        candidates = self.vector_index.search_in_regions(
            regions=match_regions,
            exclude_user_ids=[user_id],
            limit=limit * 5  # 多取一些，后面还要过滤
        )
        
        # 4. 硬条件过滤
        filtered_candidates = await self._apply_hard_filters(
            user_id=user_id,
            candidates=candidates
        )
        
        # 5. LLM 深度分析（可选）
        if use_llm_analysis and len(filtered_candidates) > limit:
            final_candidates = await self._llm_analyze(
                user_id=user_id,
                user_vector=user_vector,
                candidates=filtered_candidates[:limit * 2]
            )
        else:
            final_candidates = filtered_candidates[:limit]
        
        # 6. 生成推荐理由
        recommendations = await self._generate_recommendations(
            user_id=user_id,
            candidates=final_candidates,
            match_regions=match_regions
        )
        
        return recommendations[:limit]
    
    async def _get_user_vector(self, user_id: str) -> np.ndarray:
        """获取用户向量"""
        # 从缓存或数据库获取
        pass
    
    async def _apply_hard_filters(
        self,
        user_id: str,
        candidates: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """应用硬条件过滤"""
        # 获取用户的硬条件偏好
        user_preferences = await self._get_user_preferences(user_id)
        
        filtered = []
        for candidate_id, distance in candidates:
            candidate = await self._get_user_profile(candidate_id)
            
            # 年龄过滤
            if not self._check_age_range(candidate, user_preferences):
                continue
            
            # 地点过滤
            if not self._check_location(candidate, user_preferences):
                continue
            
            # 关系目标过滤
            if not self._check_relationship_goal(candidate, user_preferences):
                continue
            
            filtered.append((candidate_id, distance))
        
        return filtered
    
    async def _llm_analyze(
        self,
        user_id: str,
        user_vector: np.ndarray,
        candidates: List[Tuple[str, float]]
    ) -> List[Tuple[str, float]]:
        """LLM 深度分析"""
        user_profile = await self._get_user_profile(user_id)
        
        analyzed = []
        for candidate_id, distance in candidates:
            candidate_profile = await self._get_user_profile(candidate_id)
            
            # LLM 分析
            analysis = await self._call_llm_match_analysis(
                user_profile, candidate_profile
            )
            
            if analysis.get("recommend", True):
                # 调整距离（基于 LLM 评分）
                llm_score = analysis.get("score", 0.5)
                adjusted_distance = distance * (2 - llm_score)  # 分数越高，距离越近
                analyzed.append((candidate_id, adjusted_distance, analysis))
        
        # 按调整后距离排序
        analyzed.sort(key=lambda x: x[1])
        
        return [(c[0], c[1]) for c in analyzed]
    
    async def _generate_recommendations(
        self,
        user_id: str,
        candidates: List[Tuple[str, float]],
        match_regions: List[MatchRegion]
    ) -> List[Recommendation]:
        """生成推荐结果"""
        recommendations = []
        
        for candidate_id, distance in candidates:
            candidate_profile = await self._get_user_profile(candidate_id)
            
            # 确定匹配区域类型
            region_type = self._determine_region_type(
                candidate_id, match_regions
            )
            
            # 生成匹配理由
            reasoning = await self._generate_reasoning(
                user_id, candidate_id, region_type
            )
            
            recommendation = Recommendation(
                user_id=candidate_id,
                score=1 - min(distance, 1),  # 距离转分数
                match_type=region_type,
                reasoning=reasoning,
                user_profile=candidate_profile,
            )
            recommendations.append(recommendation)
        
        return recommendations
```

### 8.2 匹配理由生成（心理疏导式）

> **设计说明**：推荐理由不仅仅是说"你们很配"，更要起到心理疏导作用。理由应该说明"你们在一起可能会面临什么挑战，以及为什么你们能共同解决它"。这种带有预见性的理由能极大地提高用户的容错率，让用户在遇到问题时不至于立刻放弃，而是意识到这是系统已预见、可共同克服的挑战。

```python
GENERATE_REASONING_PROMPT = """
请为以下匹配生成一段具有心理疏导作用的推荐理由。

## 用户A资料

{user_a_profile}

## 用户B资料

{user_b_profile}

## 匹配类型

{match_type}

## 分析结果

{analysis}

## 要求

1. 语言自然亲切，像有经验的朋友在介绍
2. 突出最匹配的地方，但不要过度美化
3. **必须预见性指出可能的挑战点**（例如："你们都比较内向，可能初期需要时间打开话题"）
4. **必须说明为什么你们能共同解决这个挑战**（例如："但你们对家庭的共同渴望会成为你们沟通的桥梁"）
5. 如果有互补，说明互补如何形成平衡
6. 不要超过150字

## 输出格式

```json
{
  "reasoning": "推荐理由...",
  "highlights": ["亮点1", "亮点2"],
  "potential_challenges": ["可能的挑战1"],
  "challenge_solutions": ["为什么能共同解决"],
  "confidence_level": "high/medium"
}
```

只返回 JSON。
"""

# 示例输出
EXAMPLE_REASONING = {
    "reasoning": "你们都重视家庭，这是你们最大的共同点。虽然你们都比较内向，可能初期需要一些时间打开话题，但你们对家庭的共同渴望会成为你们沟通的桥梁。当遇到分歧时，你们都愿意为了对方调整自己，这种成长意愿比价值观的完美匹配更重要。",
    "highlights": ["家庭观一致", "愿意为关系成长"],
    "potential_challenges": ["初期沟通可能需要时间打开话题", "都内向可能社交圈重叠较少"],
    "challenge_solutions": ["家庭是共同话题的桥梁", "愿意为对方调整的态度能化解沉默"],
    "confidence_level": "high"
}
```

---

## 九、数据模型设计

### 9.1 用户向量表

```sql
CREATE TABLE user_vectors (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    
    -- 完整向量
    vector JSON NOT NULL,  -- 144维向量，JSON数组
    
    -- 子向量（用于调试和分析）
    attribute_vector JSON,      -- 属性向量 [0-63]
    growth_vector JSON,         -- 成长意愿向量 [64-71]
    interest_vector JSON,       -- 兴趣向量 [72-87]
    lifestyle_vector JSON,      -- 生活方式向量 [88-103]
    behavior_vector JSON,       -- 行为向量 [104-119]
    conversation_vector JSON,   -- 对话向量 [120-135]
    implicit_vector JSON,       -- 隐性向量 [136-143]
    
    -- 元数据
    vector_version VARCHAR(20) DEFAULT 'v1',
    data_quality_score FLOAT DEFAULT 0.0,
    
    -- 统计信息
    behavior_events_count INTEGER DEFAULT 0,
    conversation_messages_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
);
```

### 9.2 匹配区域缓存表

```sql
CREATE TABLE match_region_cache (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    
    -- 匹配区域
    regions JSON NOT NULL,  -- 匹配区域列表
    
    -- 元数据
    model_version VARCHAR(20) NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

### 9.3 匹配规则表

```sql
CREATE TABLE match_rules (
    id VARCHAR(36) PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL UNIQUE,
    
    -- 规则定义
    rule_name VARCHAR(100) NOT NULL,
    trigger_condition JSON NOT NULL,
    region_definition JSON NOT NULL,
    exclude_conditions JSON,
    
    -- 黑名单区域（一票否决）
    blacklist_regions JSON,  -- 黑名单区域列表
    
    -- 统计信息
    confidence FLOAT DEFAULT 0.5,
    support_count INTEGER DEFAULT 0,
    learned_from JSON,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_rule_id (rule_id),
    INDEX idx_is_active (is_active)
);
```

### 9.4 黑名单区域表

```sql
CREATE TABLE blacklist_regions (
    id VARCHAR(36) PRIMARY KEY,
    
    -- 黑名单定义
    dimension_conditions JSON NOT NULL,  -- 维度条件组合
    reason TEXT NOT NULL,                -- 黑名单原因（心理学依据）
    severity ENUM('critical', 'high', 'medium') NOT NULL,
    
    -- 统计信息
    hit_count INTEGER DEFAULT 0,         -- 命中次数
    prevented_matches INTEGER DEFAULT 0, -- 阻止的匹配数
    
    -- 学习来源
    learned_from JSON,                   -- 学习来源案例
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_severity (severity),
    INDEX idx_is_active (is_active)
);
```

### 9.5 匹配案例表

```sql
CREATE TABLE match_cases (
    id VARCHAR(36) PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL UNIQUE,
    
    -- 用户对
    user_a_id VARCHAR(36) NOT NULL,
    user_b_id VARCHAR(36) NOT NULL,
    
    -- 向量快照（144维）
    user_a_vector JSON NOT NULL,
    user_b_vector JSON NOT NULL,
    
    -- 结果
    outcome ENUM('success', 'failure') NOT NULL,
    outcome_type VARCHAR(50),  -- married, long_term, short_term, etc.
    duration_days INTEGER,
    
    -- 反馈
    feedback TEXT,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_a (user_a_id),
    INDEX idx_user_b (user_b_id),
    INDEX idx_outcome (outcome)
);
```

### 9.6 推荐记录表

```sql
CREATE TABLE match_recommendations (
    id VARCHAR(36) PRIMARY KEY,
    
    -- 推荐信息
    user_id VARCHAR(36) NOT NULL,
    candidate_id VARCHAR(36) NOT NULL,
    score FLOAT NOT NULL,
    match_type VARCHAR(50),
    reasoning TEXT,
    
    -- 心理疏导式推荐理由扩展
    potential_challenges JSON,      -- 预见性挑战点列表
    challenge_solutions JSON,       -- 挑战解决方案列表
    confidence_level VARCHAR(20),   -- high, medium, low
    
    -- 匹配区域信息
    matched_region_type VARCHAR(50),
    
    -- 用户反馈
    user_action VARCHAR(20),  -- like, pass, none
    action_at TIMESTAMP,
    
    -- 实际挑战验证（用户反馈后填写）
    actual_challenges TEXT,         -- 实际遇到的挑战
    challenge_resolved BOOLEAN,     -- 挑战是否解决
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_candidate_id (candidate_id),
    INDEX idx_created_at (created_at)
);
```

---

## 十、接口设计

### 10.1 匹配推荐接口

```python
# POST /api/match/recommendations
# 请求
{
    "user_id": "user_123",
    "limit": 10,
    "use_llm_analysis": true
}

# 响应
{
    "success": true,
    "data": {
        "recommendations": [
            {
                "user_id": "user_456",
                "score": 0.85,
                "match_type": "complementary",
                "reasoning": "你们都重视家庭，这是你们最大的共同点。虽然你们都比较内向，可能初期需要一些时间打开话题，但你们对家庭的共同渴望会成为你们沟通的桥梁。当遇到分歧时，你们都愿意为了对方调整自己，这种成长意愿比价值观的完美匹配更重要。",
                "highlights": ["家庭观一致", "愿意为关系成长"],
                "potential_challenges": ["初期沟通可能需要时间打开话题"],
                "challenge_solutions": ["家庭是共同话题的桥梁"],
                "confidence_level": "high",
                "user_profile": {
                    "name": "小红",
                    "age": 26,
                    "location": "北京",
                    "avatar_url": "..."
                }
            }
        ],
        "total": 10,
        "regions_count": 2
    }
}
```

### 10.2 向量更新接口

```python
# POST /api/vector/update
# 请求
{
    "user_id": "user_123",
    "trigger": "profile_update"  # profile_update, behavior_update, conversation_update
}

# 响应
{
    "success": true,
    "data": {
        "user_id": "user_123",
        "vector_updated": true,
        "quality_score": 0.75
    }
}
```

### 10.3 案例上报接口

```python
# POST /api/cases/report
# 请求
{
    "user_a_id": "user_123",
    "user_b_id": "user_456",
    "outcome": "success",
    "outcome_type": "long_term",
    "duration_days": 365,
    "feedback": "我们很合得来"
}

# 响应
{
    "success": true,
    "data": {
        "case_id": "case_789"
    }
}
```

### 10.4 规则学习接口

```python
# POST /api/rules/learn
# 请求
{
    "success_case_limit": 1000,
    "failure_case_limit": 500
}

# 响应
{
    "success": true,
    "data": {
        "rules_learned": 15,
        "rules_active": 12,
        "confidence_avg": 0.82
    }
}
```

---

## 十一、实现路线图

### 11.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           实现路线图                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1：基础架构（2周）                                               │
│  ├── Day 1-3: 数据模型设计与创建                                        │
│  ├── Day 4-7: 向量编码器实现                                           │
│  ├── Day 8-10: 向量存储（PostgreSQL + pgvector）                       │
│  └── Day 11-14: 基础 API 实现                                          │
│                                                                         │
│  Phase 2：匹配函数（2周）                                               │
│  ├── Day 1-4: 匹配规则表设计与实现                                      │
│  ├── Day 5-8: 规则型匹配函数实现                                       │
│  ├── Day 9-12: 匹配区域缓存实现                                        │
│  └── Day 13-14: 推荐服务整合                                           │
│                                                                         │
│  Phase 3：向量索引（1周）                                               │
│  ├── Day 1-3: FAISS 索引集成                                           │
│  ├── Day 4-5: 区域查询实现                                             │
│  └── Day 6-7: 性能优化                                                 │
│                                                                         │
│  Phase 4：LLM学习（2周）                                                │
│  ├── Day 1-3: 案例收集服务                                             │
│  ├── Day 4-7: LLM 学习 Prompt 设计                                     │
│  ├── Day 8-10: 离线学习流程                                            │
│  └── Day 11-14: 规则验证与审核                                         │
│                                                                         │
│  Phase 5：集成测试（1周）                                               │
│  ├── Day 1-3: 单元测试                                                 │
│  ├── Day 4-5: 集成测试                                                 │
│  └── Day 6-7: 性能测试                                                 │
│                                                                         │
│  Phase 6：上线与迭代（持续）                                            │
│  ├── 灰度发布                                                           │
│  ├── 效果监控                                                           │
│  ├── 持续学习                                                           │
│  └── 模型迭代                                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 里程碑

| 阶段 | 里程碑 | 验收标准 |
|------|--------|---------|
| Phase 1 | 向量化上线 | 用户可查询自己的向量 |
| Phase 2 | 匹配函数上线 | 可基于规则生成推荐 |
| Phase 3 | 索引上线 | 区域查询响应 < 200ms |
| Phase 4 | LLM学习上线 | 可自动学习新规则 |
| Phase 5 | 系统上线 | 完整推荐流程可用 |
| Phase 6 | 效果达标 | 匹配成功率提升 20% |

---

## 十二、效果评估

### 12.1 评估指标

> **设计说明**：匹配不是一次性的"买卖"，而是长期的过程。目前的方案侧重于"起初的匹配"，需要补充**关系阶段的动态评估**。如果一对匹配对象在匹配后的 72 小时内聊天深度（通过 NLP 分析沟通维度 (120-135)）没有显著提升，系统应反馈给 CaseCollectionService 重新复盘该匹配规则的有效性。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          效果评估指标                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  离线指标（模型层面）                                                    │
│  ├── 匹配准确率：成功案例被正确预测的比例                                │
│  ├── 匹配召回率：成功案例被正确召回的比例                                │
│  ├── 规则覆盖率：规则覆盖的用户比例                                     │
│  └── 区域命中率：候选在匹配区域内的比例                                  │
│                                                                         │
│  在线指标（业务层面）                                                    │
│  ├── 互相匹配率：双方都选择对方的比例                                    │
│  ├── 聊天转化率：匹配后发起聊天的比例                                    │
│  ├── 关系持续率：关系持续超过3个月的比例                                 │
│  ├── 用户满意度：用户反馈评分                                           │
│  └── **互动深度增长率**：匹配后72小时内聊天深度提升程度                  │
│                                                                         │
│  关系阶段动态指标                                                        │
│  ├── 72小时深度检测：聊天深度无提升则触发复盘                            │
│  ├── 7天活跃度检测：双方互动频率是否维持                                │
│  ├── 30天关系稳定性：是否出现冷战/拉黑/投诉                             │
│  └── 90天关系转化：是否发展为长期关系或分手                              │
│                                                                         │
│  对比指标（A/B测试）                                                     │
│  ├── 新方案 vs 旧方案                                                   │
│  ├── 规则型 vs 神经网络型                                               │
│  ├── 有LLM分析 vs 无LLM分析                                             │
│  └── 有隐性特征利用 vs 无隐性特征利用                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 互动深度增长率计算

```python
class InteractionDepthMonitor:
    """互动深度监控服务"""
    
    async def check_72h_depth_growth(
        self,
        match_record_id: str,
        user_a_id: str,
        user_b_id: str
    ) -> DepthGrowthResult:
        """
        检查匹配后72小时的互动深度增长
        
        匹配不是一次性的"买卖"，而是长期的过程。
        如果72小时内聊天深度没有显著提升，系统应反馈复盘。
        
        Args:
            match_record_id: 匹配记录ID
            user_a_id: 用户A ID
            user_b_id: 用户B ID
            
        Returns:
            深度增长检测结果
        """
        # 获取匹配后72小时内的聊天数据
        messages = await self._get_messages_since_match(
            user_a_id, user_b_id, hours=72
        )
        
        if len(messages) < 10:  # 消息太少，无法判断
            return DepthGrowthResult(
                match_record_id=match_record_id,
                status="insufficient_data",
                action="extend_monitoring"  # 继续监控
            )
        
        # NLP分析聊天深度（基于沟通维度120-135）
        depth_metrics = await self._analyze_conversation_depth(messages)
        
        # 计算深度增长率
        initial_depth = depth_metrics["first_24h_depth"]
        current_depth = depth_metrics["current_depth"]
        growth_rate = (current_depth - initial_depth) / initial_depth
        
        # 判断是否需要复盘
        if growth_rate < 0.2:  # 增长率低于20%
            # 反馈给 CaseCollectionService 进行复盘
            await self._trigger_rule_review(
                match_record_id=match_record_id,
                reason="72h_interaction_depth_stagnant",
                depth_metrics=depth_metrics
            )
            
            return DepthGrowthResult(
                match_record_id=match_record_id,
                status="depth_stagnant",
                growth_rate=growth_rate,
                action="review_match_rule"  # 触发规则复盘
            )
        
        return DepthGrowthResult(
            match_record_id=match_record_id,
            status="healthy_growth",
            growth_rate=growth_rate,
            action="continue_monitoring"
        )
    
    async def _analyze_conversation_depth(self, messages: List[dict]) -> dict:
        """
        NLP分析聊天深度
        
        基于沟通维度 (120-135):
        - v128-v131: 话题偏好（话题多样性）
        - v132-v135: 冲突修复能力、沟通主动性
        """
        # 话题多样性（涉猎的话题种类）
        topic_diversity = self._calculate_topic_diversity(messages)
        
        # 情感深度（是否涉及情感、价值观等深层话题）
        emotional_depth = self._calculate_emotional_depth(messages)
        
        # 互动主动性（双方是否都主动发起话题）
        initiative_balance = self._calculate_initiative_balance(messages)
        
        # 整体深度评分
        overall_depth = (
            topic_diversity * 0.3 +
            emotional_depth * 0.4 +
            initiative_balance * 0.3
        )
        
        return {
            "first_24h_depth": overall_depth,  # 前24小时深度
            "current_depth": overall_depth,
            "topic_diversity": topic_diversity,
            "emotional_depth": emotional_depth,
            "initiative_balance": initiative_balance
        }
```

### 12.3 评估流程

```python
class MatchEvaluator:
    """匹配效果评估"""
    
    async def evaluate(self, test_cases: List[MatchCase]) -> EvalResult:
        """
        评估匹配效果
        
        Args:
            test_cases: 测试案例
            
        Returns:
            评估结果
        """
        correct = 0
        total = len(test_cases)
        
        for case in test_cases:
            # 预测
            regions = self.match_function.compute_match_regions(case.user_a_vector)
            is_match = self._is_in_regions(case.user_b_vector, regions)
            
            # 对比真实结果
            if is_match == (case.outcome == "success"):
                correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return EvalResult(
            accuracy=accuracy,
            total_cases=total,
            correct_cases=correct,
        )
```

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| 用户向量 | 将用户映射到144维向量空间中的一个点 |
| 匹配区域 | 一个或多个"球体"区域，区域内的人都可能匹配 |
| 匹配函数 | f(用户向量) → 匹配区域列表 |
| 黑名单区域 | 一票否决的不可调和组合，命中则直接排除 |
| 成长意愿维度 | 衡量用户为关系调整和成长的意愿程度 |
| 压力状态依恋 | 用户在冲突、压力情境下的依恋表现模式 |
| 隐性特征向量 | 从用户行为与声明差异中推断的潜意识偏好 |
| 心理疏导式推荐 | 包含挑战预见和解决方案的推荐理由风格 |
| **依恋互补因子** | 焦虑型与安全型组合的匹配加分，促进"治愈关系" |
| **价值观硬性约束** | 关键价值观维度差异触发匹配分值直接扣减 |
| **冲突修复能力** | 吵架后主动修复关系的意愿和能力 |
| **双冷模式** | 双方都是冷战倾向者的毁灭性组合模式 |
| **互动深度增长率** | 匹配后72小时内聊天深度提升程度 |
| 互补匹配 | 性格、技能等维度相反但匹配 |
| 相似匹配 | 性格、价值观等维度相似而匹配 |
| 规则型 | 基于明确规则的匹配函数 |
| 神经网络型 | 基于神经网络的匹配函数 |

### B. 参考资料

1. 大五人格模型 (Big Five Personality Traits)
2. 依恋理论 (Attachment Theory) - 含动态依恋研究、依恋转化机制
3. 社会交换理论 (Social Exchange Theory)
4. 婚恋匹配心理学研究 - 成长意愿与关系持久性
5. 冲突修复与关系持久性研究
6. FAISS 向量索引文档
7. Milvus 向量数据库文档
8. 社会期许偏差研究 (Social Desirability Bias)
9. 价值观匹配与婚姻稳定性研究

---

> 文档版本：v2.2
> 最后更新：2026-04-10
> 作者：AI Team
> 
> **v2.2 更新说明**：
> - **依恋互补因子**：主动增加"焦虑型"与"安全型"匹配权重（治愈型关系）
> - **价值观硬性约束**：关键价值观（生育意愿、金钱观）差异触发直接分值扣减
> - **冲突修复能力子维度**：新增v132-v135，识别"双冷模式"并预警
> - **隐性特征LLM重点**：让LLM分析"声明与行为背离"的成功案例
> - **互动深度增长率**：72小时深度无提升触发匹配规则复盘
> 
> **v2.1 更新说明**：
> - 依恋类型维度扩展为16维（含压力状态下表现）
> - 新增成长意愿维度（8维）
> - 新增黑名单区域机制（一票否决）
> - 隐性特征向量权重策略调整（初次匹配克制）
> - 推荐理由改为心理疏导式风格