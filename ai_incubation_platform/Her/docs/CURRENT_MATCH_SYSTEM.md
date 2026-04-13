# 当前匹配系统方案汇总

> 版本：v2.0
> 日期：2026-04-12
> 状态：实际运行
>
> **重要说明**：本文档仅整理**当前实际运行**的匹配逻辑。双引擎架构（rule_engine.py、agentic_engine.py、engine_switch.py）虽然代码已编写，但处于"规划中"状态，尚未启用。

---

## 目录

1. [实际运行状态](#一实际运行状态)
2. [核心匹配算法](#二核心匹配算法)
3. [评分维度详解](#三评分维度详解)
4. [冷启动处理](#四冷启动处理)
5. [AI推荐理由生成](#五ai推荐理由生成)
6. [规划中的双引擎架构](#六规划中的双引擎架构)

---

## 一、实际运行状态

### 1.1 模块入口（__init__.py）

```python
"""
匹配引擎模块

双引擎架构（规划中）：
- RuleMatchEngine: 常规模式（免费，系统主导）
- AgenticMatchEngine: 许愿模式（付费，用户主导）
- EngineSwitch: 引擎切换器

当前状态：使用 matcher.py 中的匹配器
"""

# 当前可用的匹配器
from matching.matcher import matchmaker

__all__ = ["matchmaker"]
```

### 1.2 文件状态

| 文件 | 状态 | 说明 |
|------|------|------|
| `matcher.py` | ✅ **实际运行** | MatchmakerAlgorithm 匹配算法 |
| `engine_base.py` | ⏸️ 规划中 | 引擎基类和数据结构，未导入 |
| `rule_engine.py` | ⏸️ 规划中 | 规则引擎封装，未导入 |
| `agentic_engine.py` | ⏸️ 规划中 | 许愿模式引擎，未导入 |
| `engine_switch.py` | ⏸️ 规划中 | 引擎切换+付费机制，未导入 |

### 1.3 实际架构

```
┌─────────────────────────────────────────────────────────────────┐
│                 当前实际运行的匹配架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   用户发起匹配请求                                               │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────┐                   │
│   │         matcher.py                      │                   │
│   │         MatchmakerAlgorithm             │                   │
│   │                                         │                   │
│   │   • 用户注册/注销                       │                   │
│   │   • find_matches() 匹配                 │                   │
│   │   • 4维度评分                           │                   │
│   │   • 冷启动处理                          │                   │
│   │   • AI推荐理由生成                      │                   │
│   └─────────────────────────────────────────┘                   │
│         │                                                       │
│         ▼                                                       │
│   返回匹配结果                                                   │
│   [{user_id, score, breakdown}, ...]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心匹配算法

### 2.1 MatchmakerAlgorithm 类

**文件位置**：`Her/src/matching/matcher.py`

**核心职责**：
- 用户注册/注销到匹配池
- 查找匹配对象
- 计算匹配度（4维度加权）
- 生成推荐理由（AI驱动）

### 2.2 数据结构

```python
class MatchmakerAlgorithm:
    """红娘匹配算法"""

    def __init__(self):
        self._users: Dict[str, dict] = {}  # 用户池
        # 兴趣流行度统计（用于冷启动）
        self._interest_popularity: Dict[str, int] = defaultdict(int)
        # 全局用户统计数据
        self._global_stats = {
            'avg_age': 28,
            'common_interests': ['阅读', '旅行', '音乐', '电影', '健身', '美食', '摄影'],
            'age_distribution': {18: 10, 25: 50, 30: 30, 40: 10}
        }
```

### 2.3 匹配流程

```python
def find_matches(self, user_id: str, limit: int = 10) -> List[Dict]:
    """查找匹配对象"""
    
    # 1. 获取用户数据
    user = self._users[user_id]
    
    # 2. 判断是否为冷启动用户
    is_cold_start = self._is_cold_start_user(user)
    
    # 3. 遍历候选池
    for candidate_id, candidate in self._users.items():
        if candidate_id == user_id:
            continue
        
        # 3.1 基本兼容性检查（年龄、性别、关系目标）
        if not self._check_basic_compatibility(user, candidate):
            continue
        
        # 3.2 计算匹配度
        if is_cold_start:
            score, breakdown = self._calculate_cold_start_compatibility(user, candidate)
        else:
            score, breakdown = self._calculate_compatibility(user, candidate)
        
        candidates.append({
            'user_id': candidate_id,
            'score': score,
            'breakdown': breakdown
        })
    
    # 4. 排序返回（冷启动加随机扰动）
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:limit]
```

### 2.4 基本兼容性检查

```python
def _check_basic_compatibility(self, user: dict, candidate: dict) -> bool:
    """检查基本兼容性"""
    
    # 1. 年龄偏好检查
    candidate_age = candidate.get('age', 0)
    min_age = user.get('preferred_age_min', 18)
    max_age = user.get('preferred_age_max', 60)
    if candidate_age < min_age or candidate_age > max_age:
        return False
    
    # 2. 性别偏好检查
    preferred_gender = user.get('preferred_gender')
    if preferred_gender and candidate.get('gender') != preferred_gender:
        return False
    
    # 3. 关系目标检查
    if user.get('goal') != candidate.get('goal'):
        # 兼容组合：{serious, marriage} 和 {casual, friendship}
        compatible_goals = [{'serious', 'marriage'}, {'casual', 'friendship'}]
        user_goal = {user.get('goal')}
        candidate_goal = {candidate.get('goal')}
        if not any(user_goal <= cg and candidate_goal <= cg for cg in compatible_goals):
            return False
    
    return True
```

---

## 三、评分维度详解

### 3.1 四维度权重（正常用户）

```
┌─────────────────────────────────────────────────────────────────┐
│                    正常用户评分权重                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   维度              权重      计算方法                          │
│   ─────────────────────────────────────────────────────         │
│   interests(兴趣)    25%      Jaccard相似度                      │
│   values(价值观)     25%      共同价值观占比                     │
│   age(年龄)          15%      与偏好中点的距离                   │
│   location(地点)     35%      同城=1.0, 同省=0.7, 异地=0.1      │
│                                                                 │
│   总分 = Σ(维度分数 × 权重)                                      │
│                                                                 │
│   ⚠️ 地点权重最高(35%)：确保同城优先                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 兴趣匹配（Jaccard相似度）

```python
# 计算兴趣交集与并集的比例
user_interests = set(user.get('interests', []))
candidate_interests = set(candidate.get('interests', []))

common = user_interests & candidate_interests  # 交集
union = user_interests | candidate_interests   # 并集

interests_score = len(common) / len(union) if union else 0

# 示例：
# 用户：[阅读, 旅行, 音乐, 电影]
# 候选人：[旅行, 音乐, 健身, 美食]
# 交集：[旅行, 音乐] = 2
# 并集：6个
# score = 2/6 = 0.33
```

### 3.3 价值观匹配

```python
user_values = user.get('values', {})     # {"家庭观": 重视, "金钱观": 省俭}
candidate_values = candidate.get('values', {})

common_keys = set(user_values.keys()) & set(candidate_values.keys())

if common_keys:
    matches = sum(1 for k in common_keys if user_values.get(k) == candidate_values.get(k))
    values_score = matches / len(common_keys)
else:
    values_score = 0.5  # 默认中等

# 示例：
# 用户：{"家庭观": "重视", "金钱观": "省俭"}
# 候选人：{"家庭观": "重视", "金钱观": "随性"}
# 共同维度：2个
# 匹配：家庭观(匹配), 金钱观(不匹配) = 1个
# score = 1/2 = 0.5
```

### 3.4 年龄匹配

```python
age_mid_user = (preferred_age_min + preferred_age_max) / 2  # 偏好中点
age_range_user = preferred_age_max - preferred_age_min      # 偏好范围

age_diff = abs(candidate_age - age_mid_user)

age_score = max(0, 1 - age_diff / age_range_user)

# 示例：
# 用户偏好：20-30岁，中点=25，范围=10
# 候选人28岁 → diff=3 → score=1-3/10=0.7
# 候选人35岁 → diff=10 → score=0
```

### 3.5 地点匹配

```python
if user_location == candidate_location:
    location_score = 1.0   # 完全同城
elif user_location.split('市')[0] == candidate_location.split('市')[0]:
    location_score = 0.7   # 同省不同市
else:
    location_score = 0.1   # 异地（大幅降低）
```

---

## 四、冷启动处理

### 4.1 冷启动判断标准

```python
def _is_cold_start_user(self, user: dict) -> bool:
    """判断是否为冷启动用户（标签不足）"""
    
    has_interests = len(user.get('interests', [])) >= 2
    has_values = len(user.get('values', {})) >= 3
    has_preferences = (user.get('preferred_age_min') != 18 or
                       user.get('preferred_age_max') != 60 or
                       user.get('preferred_gender') is not None)
    
    # 满足条件少于2个则视为冷启动用户
    satisfied = sum([has_interests, has_values, has_preferences])
    return satisfied < 2
```

### 4.2 冷启动评分权重

```
┌─────────────────────────────────────────────────────────────────┐
│                    冷启动用户评分权重                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   维度              权重      说明                              │
│   ─────────────────────────────────────────────────────         │
│   location(地点)     40%      ⬆️ 权重提升，确保同城              │
│   age(年龄)          30%      ⬆️ 权重提升                       │
│   interests(兴趣)    20%      使用热门兴趣评分                   │
│   values(价值观)     10%      ⬇️ 使用默认值(0.5)                │
│                                                                 │
│   为什么这样调整？                                              │
│   • 新用户标签不足，兴趣/价值观维度可信度低                     │
│   • 地点和年龄是硬条件，更容易判断                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 热门兴趣评分

```python
# 用户无兴趣数据时，使用系统热门兴趣
if candidate_interests:
    top_interests = sorted(
        self._interest_popularity.items(),
        key=lambda x: x[1], reverse=True
    )[:5]
    top_interest_names = {i[0] for i in top_interests}
    common = candidate_interests & top_interest_names
    breakdown['interests'] = len(common) / 5
```

### 4.4 冷启动随机扰动

```python
if is_cold_start:
    top_candidates = candidates[:limit * 2]
    for cand in top_candidates:
        # 加入随机扰动，增加发现多样性
        cand["score"] += random.uniform(-0.05, 0.1)
    top_candidates.sort(key=lambda x: x['score'], reverse=True)
    return top_candidates[:limit]
```

---

## 五、AI推荐理由生成

### 5.1 生成原则

- ❌ 不使用硬编码规则
- ✅ 由AI分析双方资料，动态生成个性化推荐理由
- ✅ LLM不可用时降级到简洁默认理由

### 5.2 AI Prompt 结构

```text
你是一位专业的婚恋顾问，需要为用户生成一段匹配推荐理由。

【用户资料】
{"age": 28, "location": "北京", "interests": ["旅行", "阅读"]}

【推荐对象】
{"name": "小芳", "age": 26, "interests": ["旅行", "音乐"]}

【匹配分析】
- 综合匹配度：78%
- 兴趣匹配：50%
- 共同兴趣：["旅行"]

【任务】
请生成一段简洁、真诚、个性化的推荐理由（100字以内）。

【输出格式】
{"reasoning": "推荐理由文本"}
```

### 5.3 降级默认理由

```python
def _generate_fallback_reasoning(user, candidate, score) -> str:
    """降级方案"""
    
    candidate_name = candidate.get("name", "TA")
    score_percent = round(score * 100)
    
    common_interests = list(
        set(user.get("interests", [])) & set(candidate.get("interests", []))
    )[:2]
    
    parts = [f"与{candidate_name}的匹配度为{score_percent}%"]
    
    if common_interests:
        parts.append(f"你们都对{common_interests[0]}感兴趣")
    
    if user.get("location") == candidate.get("location"):
        parts.append(f"都在{user.get('location')}")
    
    return "，".join(parts) + "。"

# 示例输出："与小芳的匹配度为78%，你们都对旅行感兴趣，都在北京。"
```

---

## 六、规划中的双引擎架构

### 6.1 架构设计（未启用）

以下文件已编写但处于**规划中**状态，未实际导入运行：

| 文件 | 设计职责 | 当前状态 |
|------|---------|---------|
| `engine_base.py` | 引擎基类 MatchEngine、数据结构 MatchRequest/MatchResult | ⏸️ 未导入 |
| `rule_engine.py` | RuleMatchEngine 封装 matcher.py | ⏸️ 未导入 |
| `agentic_engine.py` | AgenticMatchEngine 许愿模式 + WishModeAdvisor | ⏸️ 未导入 |
| `engine_switch.py` | EngineSwitch 双引擎切换 + PaymentChecker 付费检查 | ⏸️ 未导入 |

### 6.2 双引擎对比（设计目标）

| 维度 | 规则引擎（设计） | 许愿引擎（设计） |
|------|-----------------|-----------------|
| 定位 | 主力产品，免费 | 增值服务，付费 |
| 匹配主导方 | 系统算法 | 用户意愿 |
| 抽象概念 | 不支持 | 支持 |
| 响应速度 | <100ms | 1-3s |
| AI角色 | 后台计算 | AI顾问 |

### 6.3 启用双引擎的步骤

若要启用双引擎架构，需要：

1. **修改 __init__.py**
```python
# 取消注释，导入双引擎模块
from matching.engine_base import MatchEngine, MatchRequest, MatchResult
from matching.rule_engine import RuleMatchEngine, get_rule_engine
from matching.agentic_engine import AgenticMatchEngine, get_agentic_engine
from matching.engine_switch import EngineSwitch, get_engine_switch

__all__ = [
    "matchmaker",  # 保留兼容
    "MatchEngine",
    "RuleMatchEngine",
    "AgenticMatchEngine",
    "EngineSwitch",
    "get_rule_engine",
    "get_agentic_engine",
    "get_engine_switch",
]
```

2. **修改 API 调用**
- 从 `matchmaker.find_matches()` 改为 `engine_switch.match()`

3. **接入付费系统**
- PaymentChecker 需要连接真实支付系统

---

## 附录

### A. 相关设计文档

| 文档 | 内容 | 状态 |
|------|------|------|
| DUAL_ENGINE_MATCH_ARCHITECTURE.md | 双引擎架构设计 | 规划中 |
| VECTOR_MATCH_SYSTEM_DESIGN.md | 176维向量匹配 | 规划中 |
| PROGRESSIVE_SMART_MATCHING_SYSTEM.md | 渐进式智能匹配 | ✅ 已实现 |

### B. 当前问题与优化方向

| 问题 | 现状 | 优化方向 |
|------|------|---------|
| 单向打分 | 只计算用户→候选人 | 双向奔赴概率 |
| 固定权重 | 4维度权重固定 | 个性化权重 |
| O(n)遍历 | 遍历所有用户 | ANN向量索引 |
| 维度有限 | 仅4维度 | 176维向量 |

---

> 文档版本：v2.0
> 最后更新：2026-04-12
> 作者：AI Team
>
> **重要**：本文档仅记录当前实际运行的 matcher.py 逻辑，双引擎架构处于规划中状态。