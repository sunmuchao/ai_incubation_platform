# 双引擎匹配架构设计

> 版本：v1.1
> 日期：2026-04-10
> 状态：设计中
>
> **v1.1 更新说明**：
> - **许愿模式**：将Agentic引擎包装为"许愿模式"，用户可自然语言描述理想类型
> - **开关设计**：用户可通过开关在常规模式和许愿模式间切换
> - **迭代推荐**：许愿模式下AI红娘迭代优化推荐结果

---

## 目录

1. [背景与动机](#一背景与动机)
2. [产品模式设计](#二产品模式设计)
3. [架构概览](#三架构概览)
4. [引擎抽象接口](#四引擎抽象接口)
5. [规则引擎设计（常规模式）](#五规则引擎设计常规模式)
6. [Agentic引擎设计（许愿模式）](#六agentic引擎设计许愿模式)
7. [引擎切换器设计](#七引擎切换器设计)
8. [切换策略设计](#八切换策略设计)
9. [API接口设计](#九api接口设计)
10. [对比分析](#十对比分析)
11. [实施路线](#十一实施路线)

---

## 一、背景与动机

### 1.1 问题背景

现有匹配系统基于规则驱动（176维向量 + 匹配区域规则），虽然性能稳定、延迟低，但在以下场景存在局限：

| 局限场景 | 说明 |
|----------|------|
| 复杂需求表达 | 用户说"我喜欢有书卷气的人"，规则难以直接匹配 |
| 自然语言偏好 | 用户用描述而非标签表达需求 |
| 迭代调整 | 用户反馈"推荐的太外向了"，需要理解语义并调整 |
| 冷启动规则 | 新场景缺少预定义规则 |

### 1.2 新方案动机

引入 **"许愿模式"**（基于 Agentic Search）：
- 用户开启许愿模式，自然语言描述理想类型
- AI红娘理解需求，迭代推荐
- 用户可继续细化需求，系统持续优化
- 类似"向AI许愿找对象"的体验

### 1.3 设计决策

**采用独立双引擎架构，通过"许愿模式"开关切换**：

| 模式 | 引擎 | 体验描述 |
|------|------|----------|
| **常规模式** | 规则引擎 | 快速推荐，基于系统算法匹配 |
| **许愿模式** | Agentic引擎 | 描述理想类型，AI迭代推荐 |

优势：

| 优势 | 说明 |
|------|------|
| 独立演进 | 两套引擎可以独立优化，不互相干扰 |
| A/B对比 | 可以做严格的对比测试，验证效果 |
| 容错隔离 | 某一套出问题，另一套仍可用 |
| 职责清晰 | 边界明确，避免耦合 |
| 用户自主 | 用户可选择适合自己的模式 |

---

## 二、产品模式设计

### 2.1 双模式概念

```
┌─────────────────────────────────────────────────────────────────┐
│                       双模式设计                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    常规模式（默认）                      │    │
│  │                                                         │    │
│  │  特点：                                                  │    │
│  │  ├── 系统算法自动推荐                                    │    │
│  │  ├── 响应快（<100ms）                                   │    │
│  │  ├── 适合日常使用                                       │    │
│  │  └── 基于用户画像+行为自动匹配                          │    │
│  │                                                         │    │
│  │  用户操作：                                              │    │
│  │  点击"推荐" → 系统返回匹配列表 → 滑动选择               │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    许愿模式（需开启）                    │    │
│  │                                                         │    │
│  │  特点：                                                  │    │
│  │  ├── 用户描述理想类型                                    │    │
│  │  ├── AI红娘迭代推荐                                     │    │
│  │  ├── 深度理解需求                                       │    │
│  │  └── 支持抽象概念（书卷气、上进心等）                    │    │
│  │                                                         │    │
│  │  用户操作：                                              │    │
│  │  开启许愿模式 → 描述理想类型 → AI推荐 →                  │    │
│  │  不满意可继续细化 → AI调整推荐 → ...                     │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│                    [许愿模式开关]                               │
│                         ▓▓▓                                    │
│                      关闭 / 开启                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 许愿模式交互流程

```
用户：开启许愿模式
      ↓
系统：请描述你理想中的TA是什么样子？
      ↓
用户：我喜欢有书卷气的，安静温和，喜欢读书，
      最好能跟我聊深度话题，不要太外向
      ↓
AI红娘：我理解你在寻找一位知性温和的伴侣。
       让我为你寻找...
       ↓
AI红娘：为你推荐3位：
       1. 小林 - 教师，喜欢哲学，性格安静
       2. 小陈 - 编辑，书卷气浓，热爱文学
       3. 小王 - 律师，理性温和，喜欢深度讨论
       ↓
用户：小林看起来不错，但能不能再有些上进心？
      ↓
AI红娘：明白了，在知性温和的基础上，增加上进心特质。
       让我重新寻找...
       ↓
AI红娘：为你重新推荐：
       1. 小张 - 创业者，文理兼修，有上进心
       2. 小陈 - 编辑（保留），正在攻读硕士
       ↓
用户：小张看起来不错！
      ↓
AI红娘：太好了！我已经把小张推荐给你。
       你们有几个共同话题可以聊...
```

### 2.3 UI设计建议

```
┌─────────────────────────────────────────────────────────────────┐
│                       匹配页面                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  许愿模式                                     [开关 ○]  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │   [开关关闭时 - 常规模式]                               │    │
│  │                                                         │    │
│  │   ┌─────┐ ┌─────┐ ┌─────┐                              │    │
│  │   │ 推荐 │ │ 推荐 │ │ 推荐 │  ...                       │    │
│  │   │ 卡片 │ │ 卡片 │ │ 卡片 │                            │    │
│  │   └─────┘ └─────┘ └─────┘                              │    │
│  │                                                         │    │
│  │   [刷新推荐]                                            │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │   [开关开启时 - 许愿模式]                               │    │
│  │                                                         │    │
│  │   ┌─────────────────────────────────────────────────┐   │    │
│  │   │ 描述你理想中的TA：                               │   │    │
│  │   │                                                 │   │    │
│  │   │ 我喜欢有书卷气的，安静温和...                    │   │    │
│  │   │                                                 │   │    │
│  │   └─────────────────────────────────────────────────┘   │    │
│  │                                                         │    │
│  │   [开始许愿]                                            │    │
│  │                                                         │    │
│  │   ──────────────────────────────────────────────────    │    │
│  │                                                         │    │
│  │   AI红娘：我理解你在寻找一位知性温和的伴侣...          │    │
│  │                                                         │    │
│  │   为你推荐：                                            │    │
│  │   ┌─────┐ ┌─────┐ ┌─────┐                              │    │
│  │   │ 推荐 │ │ 推荐 │ │ 推荐 │                           │    │
│  │   │ 卡片 │ │ 卡片 │ │ 卡片 │                           │    │
│  │   └─────┘ └─────┘ └─────┘                              │    │
│  │                                                         │    │
│  │   ┌─────────────────────────────────────────────────┐   │    │
│  │   │ 继续调整：我喜欢第1个，但希望能更...             │   │    │
│  │   └─────────────────────────────────────────────────┘   │    │
│  │                                                         │    │
│  │   [调整推荐]                                            │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 模式对比

| 维度 | 常规模式 | 许愿模式 |
|------|----------|----------|
| **触发方式** | 默认开启 | 用户手动开启开关 |
| **交互方式** | 系统推荐→用户滑动 | 用户描述→AI迭代推荐 |
| **需求表达** | 基于用户画像自动 | 用户自然语言描述 |
| **响应速度** | 快（<100ms） | 慢（1-3s） |
| **适用场景** | 日常快速推荐 | 明确特定需求 |
| **迭代能力** | 参数调整 | 语义级迭代 |
| **抽象概念** | 不支持 | 支持（书卷气、上进心等） |
| **成本** | 低 | 高（LLM调用） |
| **目标用户** | 所有用户 | 有明确需求的高端用户 |

---

## 三、架构概览

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     双引擎匹配架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────┐                          │
│                    │   MatchEngine   │                          │
│                    │   (抽象接口)    │                          │
│                    └─────────────────┘                          │
│                           │                                     │
│              ┌────────────┴────────────┐                        │
│              │                         │                        │
│   ┌──────────▼──────────┐   ┌─────────▼─────────┐              │
│   │  RuleMatchEngine    │   │ AgenticMatchEngine │              │
│   │  (常规模式引擎)     │   │ (许愿模式引擎)     │              │
│   │                     │   │                    │              │
│   │  ┌───────────────┐  │   │ ┌────────────────┐ │              │
│   │  │ 176维向量     │  │   │ │ AI红娘扮演     │ │              │
│   │  │ 匹配区域规则  │  │   │ │ 自然语言理解   │ │              │
│   │  │ 双向选择概率  │  │   │ │ 迭代推荐       │ │              │
│   │  │ 市场竞争力    │  │   │ │ 许愿对话       │ │              │
│   │  └───────────────┘  │   │ └────────────────┘ │              │
│   └─────────────────────┘   └────────────────────┘              │
│              │                         │                        │
│              └────────────┬────────────┘                        │
│                           │                                     │
│                    ┌──────▼──────┐                               │
│                    │ VectorDB    │                               │
│                    │ (共用)      │                               │
│                    └──────┬──────┘                               │
│                           │                                     │
│                    ┌──────▼──────┐                               │
│                    │ 许愿模式开关│                               │
│                    │ (EngineSwitch)│                            │
│                    └─────────────┘                               │
│                                                                 │
│  用户界面：                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 许愿模式: [○ 关闭] / [● 开启]                           │   │
│  │                                                         │   │
│  │ 关闭 → 常规模式（规则引擎，快速推荐）                   │   │
│  │ 开启 → 许愿模式（Agentic引擎，AI迭代推荐）              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

| 组件 | 职责 | 对应模式 |
|------|------|----------|
| MatchEngine | 引擎抽象接口 | 通用 |
| RuleMatchEngine | 规则引擎，快速推荐 | 常规模式 |
| AgenticMatchEngine | Agentic引擎，AI迭代推荐 | 许愿模式 |
| VectorDB | 共用的向量数据库 | 通用 |
| EngineSwitch | 许愿模式开关，切换引擎 | 切换控制 |

### 3.3 数据流对比

```
常规模式数据流（开关关闭）：
用户点击推荐 → 向量获取(176维) → 匹配区域计算 → 向量查询 → 市场因素调整 → 推荐列表
（延迟：<100ms，成本：低，无LLM调用）

许愿模式数据流（开关开启）：
用户描述理想类型 → AI红娘理解需求 → 生成推荐描述 → 向量查询 → 
AI验证候选 → (不满意)用户继续调整 → AI调整推荐 → ... → 推荐列表
（延迟：1-3s，成本：高，有LLM调用，支持多轮迭代）
```

---

## 四、引擎抽象接口

### 3.1 数据模型

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MatchRequest:
    """匹配请求"""
    user_id: str
    limit: int = 10
    context: Optional[dict] = None  # 用户反馈、场景信息等

@dataclass
class MatchResult:
    """匹配结果"""
    user_id: str
    candidates: List[dict]      # 推荐候选人列表
    engine_type: str            # "rule" | "agentic"
    reasoning: Optional[str]    # Agentic引擎会返回分析过程
    metadata: Optional[dict]    # 元数据（迭代次数、区域数等）
```

### 3.2 抽象接口定义

```python
from abc import ABC, abstractmethod

class MatchEngine(ABC):
    """匹配引擎抽象接口"""
    
    @abstractmethod
    async def match(self, request: MatchRequest) -> MatchResult:
        """
        执行匹配
        
        Args:
            request: 匹配请求
            
        Returns:
            MatchResult: 匹配结果
        """
        pass
    
    @abstractmethod
    async def adjust(self, request: MatchRequest, feedback: str) -> MatchResult:
        """
        根据反馈调整匹配
        
        Args:
            request: 匹配请求
            feedback: 用户反馈（如"推荐的太外向了"）
            
        Returns:
            MatchResult: 调整后的匹配结果
        """
        pass
    
    @abstractmethod
    def get_engine_name(self) -> str:
        """
        获取引擎名称
        
        Returns:
            str: 引擎名称
        """
        pass
    
    @abstractmethod
    def get_engine_metrics(self) -> dict:
        """
        获取引擎运行指标
        
        Returns:
            dict: 指标数据（延迟、成功率等）
        """
        pass
```

---

## 五、规则引擎设计（常规模式）

### 4.1 引擎概述

规则引擎基于现有的向量匹配系统设计（详见 [VECTOR_MATCH_SYSTEM_DESIGN.md](./VECTOR_MATCH_SYSTEM_DESIGN.md)），核心特点：

| 特点 | 说明 |
|------|------|
| 176维向量 | 用户全面特征量化 |
| 匹配区域规则 | 规则驱动的区域计算（相似+互补） |
| 双向选择概率 | 考虑市场竞争力的双向匹配 |
| 低延迟 | 响应时间 <100ms |
| 高稳定性 | 规则确定性输出 |

### 4.2 引擎实现

```python
class RuleMatchEngine(MatchEngine):
    """规则匹配引擎"""
    
    def __init__(
        self,
        vector_encoder: UserVectorEncoder,
        match_function: MatchFunctionService,
        vector_index: VectorIndexService,
        market_service: MarketDynamicsService,
        elo_service: EloAttractivenessRating
    ):
        self.vector_encoder = vector_encoder
        self.match_function = match_function
        self.vector_index = vector_index
        self.market_service = market_service
        self.elo_service = elo_service
        
        # 运行指标
        self._metrics = {
            "total_calls": 0,
            "avg_latency_ms": 0,
            "success_rate": 1.0
        }
    
    async def match(self, request: MatchRequest) -> MatchResult:
        """
        规则驱动的匹配流程
        
        流程：
        1. 获取用户向量（176维）
        2. 计算匹配区域
        3. 向量索引查询
        4. 双向选择概率计算
        5. 市场竞争力调整
        6. 返回推荐
        """
        start_time = time.time()
        
        # 1. 获取用户向量
        user_vector = await self._get_user_vector(request.user_id)
        
        # 2. 计算匹配区域
        match_regions = self.match_function.compute_match_regions(user_vector)
        
        # 3. 向量索引查询
        candidates = self.vector_index.search_in_regions(
            regions=match_regions,
            exclude_user_ids=[request.user_id],
            limit=request.limit * 3
        )
        
        # 4. 双向选择概率 + 市场竞争力调整
        scored_candidates = await self._apply_market_factors(
            request.user_id, 
            candidates
        )
        
        # 5. 黑名单过滤
        filtered_candidates = self._apply_blacklist_filter(
            user_vector, 
            scored_candidates
        )
        
        # 6. 生成推荐理由
        recommendations = await self._generate_recommendations(
            request.user_id,
            filtered_candidates[:request.limit],
            match_regions
        )
        
        # 更新指标
        latency = (time.time() - start_time) * 1000
        self._update_metrics(latency, success=True)
        
        return MatchResult(
            user_id=request.user_id,
            candidates=recommendations,
            engine_type="rule",
            reasoning=None,  # 规则引擎不返回推理过程
            metadata={
                "regions_count": len(match_regions),
                "vector_dimensions": 176,
                "latency_ms": latency
            }
        )
    
    async def adjust(self, request: MatchRequest, feedback: str) -> MatchResult:
        """
        规则引擎的调整方式：参数级调整
        
        规则引擎通过解析反馈，调整查询参数：
        - 扩大/缩小匹配区域半径
        - 调整维度权重
        - 增加/排除特定维度条件
        """
        # 解析反馈为参数调整
        adjustment = self._parse_feedback_to_params(feedback)
        
        # 调整后的请求
        adjusted_request = MatchRequest(
            user_id=request.user_id,
            limit=request.limit,
            context={
                "original_context": request.context,
                "adjustment": adjustment
            }
        )
        
        # 执行调整后的匹配
        return await self.match(adjusted_request)
    
    def get_engine_name(self) -> str:
        return "RuleMatchEngine"
    
    def get_engine_metrics(self) -> dict:
        return self._metrics
    
    # === 私有方法 ===
    
    def _parse_feedback_to_params(self, feedback: str) -> dict:
        """
        解析用户反馈为参数调整
        
        示例：
        - "推荐的太外向了" → {"extraversion": {"max": 0.5}}
        - "想要更有上进心的" → {"ambition": {"min": 0.6}}
        - "年龄范围太小了" → {"age": {"expand_range": 0.2}}
        """
        # 关键词映射表
        FEEDBACK_KEYWORD_MAP = {
            "外向": {"dimension": "extraversion", "action": "reduce"},
            "内向": {"dimension": "extraversion", "action": "increase"},
            "上进心": {"dimension": "ambition", "action": "increase"},
            "家庭": {"dimension": "family_oriented", "action": "increase"},
            "幽默": {"dimension": "humor", "action": "increase"},
            "稳重": {"dimension": "conscientiousness", "action": "increase"},
            "年龄": {"dimension": "age", "action": "expand"},
        }
        
        adjustment = {}
        
        for keyword, config in FEEDBACK_KEYWORD_MAP.items():
            if keyword in feedback:
                dimension = config["dimension"]
                action = config["action"]
                
                if action == "reduce":
                    adjustment[dimension] = {"max": 0.5}
                elif action == "increase":
                    adjustment[dimension] = {"min": 0.6}
                elif action == "expand":
                    adjustment[dimension] = {"expand_range": 0.2}
        
        return adjustment
    
    async def _apply_market_factors(
        self,
        user_id: str,
        candidates: List[Tuple[str, float]]
    ) -> List[dict]:
        """
        应用市场因素：双向选择概率 + Elo竞争力
        """
        user_vector = await self._get_user_vector(user_id)
        user_score = self.elo_service.get_rating(user_id)
        
        scored = []
        for candidate_id, distance in candidates:
            candidate_vector = await self._get_user_vector(candidate_id)
            candidate_score = self.elo_service.get_rating(candidate_id)
            
            # 双向选择概率
            mutual_prob = self.market_service.compute_mutual_match_probability(
                user_vector, candidate_vector,
                user_score, candidate_score
            )
            
            # 层级差距惩罚
            user_tier = self.elo_service.get_attractiveness_tier(user_score)
            candidate_tier = self.elo_service.get_attractiveness_tier(candidate_score)
            layer_penalty = self.elo_service.compute_layer_gap_penalty(
                user_tier, candidate_tier
            )
            
            # 综合分数
            base_score = 1 - min(distance, 1)
            final_score = base_score * mutual_prob * layer_penalty
            
            scored.append({
                "user_id": candidate_id,
                "score": final_score,
                "distance": distance,
                "mutual_prob": mutual_prob,
                "layer_penalty": layer_penalty
            })
        
        # 按分数排序
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored
    
    def _apply_blacklist_filter(
        self,
        user_vector: np.ndarray,
        candidates: List[dict]
    ) -> List[dict]:
        """
        应用黑名单区域过滤（一票否决）
        """
        filtered = []
        
        for candidate in candidates:
            candidate_vector = await self._get_user_vector(candidate["user_id"])
            
            # 检查黑名单
            is_blacklisted, reason = self.match_function.check_blacklist(
                user_vector, candidate_vector
            )
            
            if not is_blacklisted:
                candidate["blacklist_checked"] = True
                filtered.append(candidate)
            else:
                logger.info(f"Blacklist hit: {candidate['user_id']}, reason: {reason}")
        
        return filtered
```

### 4.3 规则引擎特点总结

```
┌─────────────────────────────────────────────────────────────────┐
│                     规则引擎特点                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  优势：                                                         │
│  ├── 响应延迟低（<100ms）                                       │
│  ├── 计算成本低（无LLM调用）                                    │
│  ├── 输出确定性高（规则稳定）                                   │
│  ├── 可解释性强（规则透明）                                     │
│  └── 已处理市场竞争力、双向选择                                 │
│                                                                 │
│  局限：                                                         │
│  ├── 无法理解自然语言偏好                                       │
│  ├── 复杂需求需要预定义规则                                     │
│  ├── 调整方式为参数级（语义理解弱）                             │
│  └── 冷启动新场景需要规则开发                                   │
│                                                                 │
│  适用场景：                                                     │
│  ├── 大众用户高频匹配                                           │
│  ├── 规则覆盖的常见需求                                         │
│  ├── 对延迟敏感的场景                                           │
│  └── 对成本敏感的场景                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、Agentic引擎设计（许愿模式）

### 6.1 引擎概述

Agentic引擎是**许愿模式**的核心，用户开启许愿模式后：

1. 用户用自然语言描述理想类型（如"我喜欢有书卷气的，安静温和的"）
2. AI红娘理解需求，生成推荐
3. 用户不满意可继续细化描述，AI迭代优化推荐
4. 支持抽象概念理解（书卷气、上进心、气质等）

```
许愿模式交互流程：
用户：描述理想类型 → AI红娘：理解并推荐 → 
用户：继续调整 → AI红娘：优化推荐 → ... → 满意
```

核心特点：

| 特点 | 说明 |
|------|------|
| AI红娘扮演 | 专业红娘视角理解用户需求 |
| 自然语言交互 | 用户直接描述，无需选标签 |
| 迭代推荐 | 不满意可继续调整，AI优化 |
| 抽象概念理解 | 支持"书卷气"、"上进心"等 |
| 对话式体验 | 类似和红娘聊天的体验 |

### 6.2 引擎实现

```python
class AgenticMatchEngine(MatchEngine):
    """Agentic匹配引擎"""
    
    def __init__(
        self,
        llm_service: LLMService,
        vector_db: VectorDBService,
        user_data_service: UserDataService
    ):
        self.llm = llm_service
        self.vector_db = vector_db
        self.user_data_service = user_data_service
        
        # 配置
        self.max_iterations = 3  # 最大迭代次数
        
        # 运行指标
        self._metrics = {
            "total_calls": 0,
            "avg_latency_ms": 0,
            "avg_iterations": 0,
            "convergence_rate": 0,
            "llm_calls_per_match": 0,
            "success_rate": 0
        }
    
    async def match(self, request: MatchRequest) -> MatchResult:
        """
        Agentic Search匹配流程
        
        流程：
        1. 获取用户完整数据
        2. LLM扮演红娘，分析用户，生成理想对象描述
        3. 将描述转化为向量查询条件
        4. 向量数据库查询候选
        5. LLM验证候选是否满足需求
        6. 如不满意，调整描述，重新查询（迭代）
        7. 返回推荐 + 推理过程
        """
        start_time = time.time()
        
        # Step 1: 获取用户数据
        user_data = await self._get_user_data(request.user_id)
        
        # Step 2: LLM生成理想对象描述
        ideal_description = await self._generate_ideal_description(user_data)
        
        # Step 3-5: Agentic Search循环
        iteration = 0
        reasoning_trace = []
        candidates = []
        
        while iteration < self.max_iterations:
            # 转化为向量查询
            query_params = await self._description_to_query(ideal_description)
            
            # 向量查询
            candidates = await self.vector_db.search(
                query_params, 
                limit=request.limit * 2
            )
            
            # LLM验证
            verification = await self._verify_candidates(
                user_data, 
                ideal_description, 
                candidates
            )
            
            reasoning_trace.append({
                "iteration": iteration + 1,
                "description": ideal_description,
                "candidates_count": len(candidates),
                "verification": verification
            })
            
            if verification["satisfied"]:
                # 满足需求，返回结果
                latency = (time.time() - start_time) * 1000
                self._update_metrics(
                    latency=latency,
                    iterations=iteration + 1,
                    converged=True,
                    llm_calls=(iteration + 1) * 2 + 1,
                    success=True
                )
                
                return MatchResult(
                    user_id=request.user_id,
                    candidates=verification["selected_candidates"][:request.limit],
                    engine_type="agentic",
                    reasoning=self._format_reasoning(reasoning_trace),
                    metadata={
                        "iterations": iteration + 1,
                        "converged": True,
                        "llm_calls": (iteration + 1) * 2 + 1,
                        "latency_ms": latency
                    }
                )
            
            # 不满足，调整描述
            ideal_description = await self._adjust_description(
                ideal_description, 
                verification["adjustment_suggestion"]
            )
            iteration += 1
        
        # 迭代结束，返回最佳结果
        latency = (time.time() - start_time) * 1000
        self._update_metrics(
            latency=latency,
            iterations=self.max_iterations,
            converged=False,
            llm_calls=self.max_iterations * 2 + 1,
            success=True
        )
        
        return MatchResult(
            user_id=request.user_id,
            candidates=candidates[:request.limit],
            engine_type="agentic",
            reasoning=self._format_reasoning(reasoning_trace),
            metadata={
                "iterations": self.max_iterations,
                "converged": False,
                "llm_calls": self.max_iterations * 2 + 1,
                "latency_ms": latency
            }
        )
    
    async def adjust(self, request: MatchRequest, feedback: str) -> MatchResult:
        """
        Agentic引擎的调整：LLM理解反馈语义
        
        Agentic引擎的调整是"语义级调整"：
        - LLM理解用户反馈的真实意图
        - 结合用户数据重新生成描述
        - 执行完整匹配流程
        """
        user_data = await self._get_user_data(request.user_id)
        
        # LLM结合反馈生成新描述
        new_description = await self._generate_description_with_feedback(
            user_data, 
            feedback
        )
        
        # 用新描述执行匹配
        request.context = {"feedback": feedback}
        return await self.match(request)
    
    def get_engine_name(self) -> str:
        return "AgenticMatchEngine"
    
    def get_engine_metrics(self) -> dict:
        return self._metrics
    
    # === 私有方法 ===
    
    async def _get_user_data(self, user_id: str) -> dict:
        """
        获取用户完整数据
        
        包含：基本信息、行为数据、对话历史、向量数据
        """
        return await self.user_data_service.get_full_user_data(user_id)
    
    async def _generate_ideal_description(self, user_data: dict) -> dict:
        """
        LLM扮演红娘，生成理想对象描述
        
        Prompt设计重点：
        1. 专业红娘角色设定
        2. 多维度分析（性格、价值观、沟通风格）
        3. 考虑相似匹配和互补匹配
        4. 用自然语言而非向量术语
        """
        prompt = f"""
你是一位专业的婚恋红娘，拥有20年从业经验。
你擅长通过用户数据分析其真实需求，并描述理想伴侣的特征。

## 用户数据

{json.dumps(user_data, ensure_ascii=False, indent=2)}

## 分析要求

1. **性格维度分析**
   - 从大五人格角度分析用户的性格特征
   - 判断用户适合相似型还是互补型伴侣

2. **价值观维度分析**
   - 分析用户的人生观、婚恋观、家庭观
   - 识别关键价值观（如生育意愿、金钱观）

3. **沟通风格分析**
   - 分析用户的表达方式、话题偏好
   - 判断沟通风格是否需要互补

4. **依恋类型分析**
   - 分析用户的依恋倾向（安全型/焦虑型/回避型）
   - 判断匹配策略（如焦虑型适合安全型）

5. **隐性偏好推断**
   - 从行为数据推断用户真实偏好
   - 注意"说的"和"做的"可能不一致

## 输出格式（JSON）

```json
{
    "user_analysis": {
        "personality": "用户性格分析...",
        "values": "价值观分析...",
        "communication": "沟通风格分析...",
        "attachment": "依恋类型分析...",
        "implicit_preference": "隐性偏好推断..."
    },
    "ideal_description": {
        "summary": "理想伴侣的整体描述",
        "key_traits": ["关键特质1", "关键特质2", ...],
        "personality_type": "理想性格类型",
        "values_alignment": "价值观匹配要求",
        "communication_style": "沟通风格要求",
        "attachment_type": "理想依恋类型",
        "match_type": "similar | complementary | mixed"
    },
    "match_strategy": {
        "primary_approach": "主要匹配策略",
        "flexibility": "匹配弹性程度",
        "hard_requirements": ["硬性要求"],
        "soft_requirements": ["软性要求"]
    }
}
```

只返回JSON，不要其他内容。
"""
        response = await self.llm.call(prompt, temperature=0.3)
        return json.loads(response)
    
    async def _description_to_query(self, description: dict) -> dict:
        """
        将自然语言描述转化为向量查询参数
        
        LLM负责将描述映射到向量维度：
        - "外向活泼" → extraversion维度范围 [0.6, 1.0]
        - "重视家庭" → family_oriented维度范围 [0.7, 1.0]
        - "安全型" → attachment_secure维度范围 [0.7, 1.0]
        """
        prompt = f"""
你是一个向量匹配系统的转换器。
请将理想伴侣描述转化为向量查询参数。

## 理想伴侣描述

{json.dumps(description, ensure_ascii=False, indent=2)}

## 向量维度说明

| 维度区间 | 含义 |
|----------|------|
| [0-15]   | 人口统计学（年龄、身高、收入等） |
| [16-31]  | 价值观（家庭观、事业观、金钱观） |
| [32-47]  | 大五人格（开放性、尽责性、外向性等） |
| [48-63]  | 依恋类型（安全型、焦虑型、回避型） |
| [64-71]  | 成长意愿 |
| [72-87]  | 兴趣爱好 |
| [88-103] | 生活方式 |
| [104-111]| 权力分配意愿 |
| [112-127]| 行为模式 |
| [128-143]| 沟通风格 |

## 输出格式（JSON）

```json
{
    "query_regions": [
        {
            "center_description": "区域中心描述",
            "dimension_ranges": {
                "extraversion": {"min": 0.6, "max": 1.0},
                "family_oriented": {"min": 0.7, "max": 1.0},
                ...
            },
            "radius": 0.3,
            "weight": 0.8
        }
    ],
    "must_match_dimensions": ["dimension1", "dimension2"],
    "exclude_dimensions": ["dimension3"]
}
```

只返回JSON。
"""
        response = await self.llm.call(prompt, temperature=0.2)
        return json.loads(response)
    
    async def _verify_candidates(
        self,
        user_data: dict,
        ideal_description: dict,
        candidates: List[dict]
    ) -> dict:
        """
        LLM验证候选是否满足理想描述
        
        验证维度：
        1. 关键特质匹配度
        2. 硬性要求满足度
        3. 整体适配度评估
        4. 不满足时的调整建议
        """
        prompt = f"""
作为专业红娘，请验证这些候选人是否满足用户的理想伴侣描述。

## 用户数据

{json.dumps(user_data.get("basic_info", {}), ensure_ascii=False)}

## 理想伴侣描述

{json.dumps(ideal_description, ensure_ascii=False, indent=2)}

## 候选人列表（前10个）

{json.dumps(candidates[:10], ensure_ascii=False, indent=2)}

## 验证要求

1. **关键特质匹配**
   - 检查候选人是否具备描述中的关键特质
   - 计算特质匹配分数

2. **硬性要求检查**
   - 检查硬性要求是否满足
   - 标记不满足的项

3. **整体适配度**
   - 综合评估适配程度
   - 给出推荐信心度

4. **调整建议**
   - 如果不满意，说明应如何调整理想描述
   - 给出具体的调整方向

## 输出格式（JSON）

```json
{
    "satisfied": true/false,
    "satisfaction_score": 0.0-1.0,
    "selected_candidates": [
        {
            "user_id": "...",
            "match_score": 0.X,
            "matched_traits": ["特质1", "特质2"],
            "missing_traits": ["特质3"],
            "reasoning": "匹配理由"
        }
    ],
    "match_analysis": [
        {
            "candidate_id": "...",
            "trait_matching": {...},
            "requirement_check": {...}
        }
    ],
    "adjustment_suggestion": "如不满意，应该如何调整理想描述"
}
```

只返回JSON。
"""
        response = await self.llm.call(prompt, temperature=0.3)
        return json.loads(response)
    
    async def _adjust_description(
        self,
        ideal_description: dict,
        adjustment_suggestion: str
    ) -> dict:
        """
        根据调整建议修改理想描述
        
        LLM理解调整建议，更新描述内容：
        - "范围太窄" → 扩大维度范围
        - "缺少某特质" → 降低该特质权重
        - "互补不足" → 增加互补维度
        """
        prompt = f"""
根据验证反馈，调整理想伴侣描述。

## 当前理想描述

{json.dumps(ideal_description, ensure_ascii=False, indent=2)}

## 调整建议

{adjustment_suggestion}

## 调整要求

1. 理解调整建议的意图
2. 修改理想描述的相关部分
3. 保持核心需求不变
4. 扩大或缩小匹配范围

## 输出格式（JSON）

返回调整后的完整理想描述（格式与之前相同）。

只返回JSON。
"""
        response = await self.llm.call(prompt, temperature=0.3)
        return json.loads(response)
    
    async def _generate_description_with_feedback(
        self,
        user_data: dict,
        feedback: str
    ) -> dict:
        """
        结合用户反馈生成新描述
        
        用户反馈可能是：
        - "推荐的太外向了，我更喜欢内向安静的"
        - "想要更有上进心和责任感的"
        - "年龄范围太小了，可以放宽一些"
        """
        prompt = f"""
作为专业红娘，请根据用户反馈重新生成理想伴侣描述。

## 用户数据

{json.dumps(user_data, ensure_ascii=False, indent=2)}

## 用户反馈

{feedback}

## 要求

1. 理解用户反馈的真实意图
2. 结合用户原有数据和反馈生成新描述
3. 注意用户可能说的是"不想要的"，需要反向理解
4. 保持核心价值观不变（如生育意愿、金钱观）

## 输出格式（JSON）

返回完整的理想伴侣描述（格式与之前相同）。

只返回JSON。
"""
        response = await self.llm.call(prompt, temperature=0.3)
        return json.loads(response)
    
    def _format_reasoning(self, reasoning_trace: List[dict]) -> str:
        """
        格式化推理过程为可读文本
        
        输出给用户看的推理过程（简化版）
        """
        lines = []
        lines.append("## 匹配推理过程\n")
        
        for trace in reasoning_trace:
            iteration = trace["iteration"]
            desc = trace["description"]
            verification = trace["verification"]
            
            lines.append(f"### 第{iteration}轮分析")
            lines.append(f"理想对象描述：{desc.get('ideal_description', {}).get('summary', '')}")
            lines.append(f"候选人数：{trace['candidates_count']}")
            
            if verification.get("satisfied"):
                lines.append(f"结果：满意（满意度分数：{verification.get('satisfaction_score', 0)}）")
            else:
                lines.append(f"结果：不满意")
                lines.append(f"调整方向：{verification.get('adjustment_suggestion', '')}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _update_metrics(
        self,
        latency: float,
        iterations: int,
        converged: bool,
        llm_calls: int,
        success: bool
    ):
        """更新运行指标"""
        self._metrics["total_calls"] += 1
        
        # 平均延迟（移动平均）
        n = self._metrics["total_calls"]
        self._metrics["avg_latency_ms"] = (
            self._metrics["avg_latency_ms"] * (n - 1) + latency
        ) / n
        
        # 平均迭代次数
        self._metrics["avg_iterations"] = (
            self._metrics["avg_iterations"] * (n - 1) + iterations
        ) / n
        
        # 收敛率
        if converged:
            converged_count = self._metrics.get("converged_count", 0) + 1
            self._metrics["converged_count"] = converged_count
            self._metrics["convergence_rate"] = converged_count / n
        
        # 平均LLM调用次数
        self._metrics["llm_calls_per_match"] = (
            self._metrics["llm_calls_per_match"] * (n - 1) + llm_calls
        ) / n
        
        # 成功率
        if success:
            success_count = self._metrics.get("success_count", 0) + 1
            self._metrics["success_count"] = success_count
            self._metrics["success_rate"] = success_count / n
```

### 5.3 Agentic引擎特点总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic引擎特点                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  优势：                                                         │
│  ├── 深度语义理解（理解"书卷气"、"上进心"等抽象概念）          │
│  ├── 自然语言交互（用户可直接描述需求）                         │
│  ├── 迭代优化（不满意时自动调整）                               │
│  ├── 无需预定义规则（LLM实时生成）                              │
│  ├── 推理过程透明（返回推理Trace）                              │
│  └── 适应复杂多变需求                                           │
│                                                                 │
│  局限：                                                         │
│  ├── 响应延迟高（1-3s，多次LLM调用）                            │
│  ├── 计算成本高（每次匹配需LLM）                                │
│  ├── 输出可能波动（LLM非确定性）                                │
│  ├── 需要LLM服务稳定                                            │
│  └── 需要更多监控和容错                                         │
│                                                                 │
│  适用场景：                                                     │
│  ├── 高端用户（愿意付费等待更好服务）                           │
│  ├── 复杂需求（多维度组合、抽象概念）                           │
│  ├── 自然语言偏好表达                                           │
│  ├── 需要迭代调整的场景                                         │
│  └── 规则难以覆盖的新场景                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、引擎切换器设计

### 6.1 切换器职责

| 职责 | 说明 |
|------|------|
| 策略执行 | 根据配置策略选择引擎 |
| 用户覆盖 | 支持用户级引擎指定 |
| A/B测试 | 支持按比例分配引擎 |
| 失败Fallback | Agentic失败时fallback到规则 |
| 指标收集 | 收集两套引擎的运行指标 |

### 6.2 切换器实现

```python
class EngineSwitch:
    """引擎切换器"""
    
    def __init__(
        self,
        rule_engine: RuleMatchEngine,
        agentic_engine: AgenticMatchEngine
    ):
        self.rule_engine = rule_engine
        self.agentic_engine = agentic_engine
        
        # 切换策略配置
        self.config = {
            # 默认引擎
            "default_engine": "rule",
            
            # 用户级覆盖 {user_id: engine_type}
            "user_override": {},
            
            # Feature Flags
            "feature_flags": {
                "agentic_enabled": True,     # Agentic引擎是否启用
                "ab_test_ratio": 0.1,        # A/B测试比例（10%用户使用Agentic）
                "premium_agentic": True,     # 高端用户强制Agentic
            },
            
            # 失败Fallback
            "fallback": {
                "from": "agentic",
                "to": "rule",
                "max_retries": 2
            },
            
            # 场景触发
            "scene_triggers": {
                "complex_need_keywords": [
                    "书卷气", "上进心", "有内涵", "气质",
                    "幽默风趣", "稳重靠谱", "阳光开朗"
                ],
                "feedback_keywords": [
                    "不满意", "想要", "更喜欢", "希望能"
                ]
            }
        }
        
        # 运行统计
        self._stats = {
            "rule_calls": 0,
            "agentic_calls": 0,
            "agentic_fallbacks": 0,
            "user_overrides": 0
        }
    
    async def match(self, request: MatchRequest) -> MatchResult:
        """
        根据切换策略选择引擎执行匹配
        """
        engine_type = self._determine_engine(request)
        
        try:
            if engine_type == "agentic":
                result = await self.agentic_engine.match(request)
                self._stats["agentic_calls"] += 1
            else:
                result = await self.rule_engine.match(request)
                self._stats["rule_calls"] += 1
            
            return result
            
        except Exception as e:
            # Agentic失败，Fallback到规则引擎
            logger.error(f"Engine {engine_type} failed: {e}")
            
            if engine_type == "agentic":
                self._stats["agentic_fallbacks"] += 1
                return await self.rule_engine.match(request)
            
            raise
    
    async def adjust(self, request: MatchRequest, feedback: str) -> MatchResult:
        """
        根据当前用户使用的引擎类型进行调整
        """
        engine_type = self._get_current_engine(request.user_id)
        
        if engine_type == "agentic":
            return await self.agentic_engine.adjust(request, feedback)
        else:
            return await self.rule_engine.adjust(request, feedback)
    
    def _determine_engine(self, request: MatchRequest) -> str:
        """
        决定使用哪个引擎
        
        决策优先级：
        1. 用户级覆盖（最高优先级）
        2. 复杂需求关键词触发
        3. 高端用户策略
        4. A/B测试分配
        5. 默认引擎
        """
        user_id = request.user_id
        
        # 1. 用户级覆盖
        if user_id in self.config["user_override"]:
            self._stats["user_overrides"] += 1
            return self.config["user_override"][user_id]
        
        # 2. 检查是否有复杂需求关键词
        context = request.context or {}
        user_input = context.get("user_input", "")
        
        if user_input:
            for keyword in self.config["scene_triggers"]["complex_need_keywords"]:
                if keyword in user_input:
                    return "agentic"
        
        # 3. 高端用户策略
        if self.config["feature_flags"]["premium_agentic"]:
            user_level = self._get_user_membership_level(user_id)
            if user_level in ["gold", "platinum", "vip"]:
                return "agentic"
        
        # 4. A/B测试分配
        if self.config["feature_flags"]["agentic_enabled"]:
            ab_ratio = self.config["feature_flags"]["ab_test_ratio"]
            # 使用用户ID hash决定分配（保证同一用户始终使用同一引擎）
            if hash(user_id) % 100 < ab_ratio * 100:
                return "agentic"
        
        # 5. 默认引擎
        return self.config["default_engine"]
    
    def _get_current_engine(self, user_id: str) -> str:
        """获取用户当前使用的引擎类型"""
        if user_id in self.config["user_override"]:
            return self.config["user_override"][user_id]
        
        # A/B测试用户的引擎类型
        ab_ratio = self.config["feature_flags"]["ab_test_ratio"]
        if hash(user_id) % 100 < ab_ratio * 100:
            return "agentic"
        
        return self.config["default_engine"]
    
    def _get_user_membership_level(self, user_id: str) -> str:
        """获取用户会员等级"""
        # TODO: 从会员服务获取
        return "normal"
    
    # === 管理接口 ===
    
    def set_user_engine(self, user_id: str, engine_type: str):
        """
        为特定用户设置引擎
        
        Args:
            user_id: 用户ID
            engine_type: "rule" | "agentic"
        """
        if engine_type not in ["rule", "agentic"]:
            raise ValueError(f"Invalid engine type: {engine_type}")
        
        self.config["user_override"][user_id] = engine_type
        logger.info(f"User {user_id} engine set to {engine_type}")
    
    def remove_user_override(self, user_id: str):
        """移除用户级覆盖，恢复默认策略"""
        if user_id in self.config["user_override"]:
            del self.config["user_override"][user_id]
    
    def set_default_engine(self, engine_type: str):
        """设置默认引擎"""
        self.config["default_engine"] = engine_type
    
    def set_ab_test_ratio(self, ratio: float):
        """设置A/B测试比例（0-1）"""
        if ratio < 0 or ratio > 1:
            raise ValueError("Ratio must be between 0 and 1")
        self.config["feature_flags"]["ab_test_ratio"] = ratio
    
    def enable_agentic(self, enabled: bool):
        """启用/禁用Agentic引擎"""
        self.config["feature_flags"]["agentic_enabled"] = enabled
    
    def get_config(self) -> dict:
        """获取当前配置"""
        return self.config
    
    def get_stats(self) -> dict:
        """获取运行统计"""
        return {
            **self._stats,
            "rule_engine_metrics": self.rule_engine.get_engine_metrics(),
            "agentic_engine_metrics": self.agentic_engine.get_engine_metrics()
        }
    
    def get_comparison_report(self) -> dict:
        """
        获取引擎对比报告
        
        用于A/B测试效果对比
        """
        rule_metrics = self.rule_engine.get_engine_metrics()
        agentic_metrics = self.agentic_engine.get_engine_metrics()
        
        return {
            "rule_engine": {
                "calls": self._stats["rule_calls"],
                "avg_latency_ms": rule_metrics.get("avg_latency_ms", 0),
                "success_rate": rule_metrics.get("success_rate", 1.0)
            },
            "agentic_engine": {
                "calls": self._stats["agentic_calls"],
                "avg_latency_ms": agentic_metrics.get("avg_latency_ms", 0),
                "avg_iterations": agentic_metrics.get("avg_iterations", 0),
                "convergence_rate": agentic_metrics.get("convergence_rate", 0),
                "llm_calls_per_match": agentic_metrics.get("llm_calls_per_match", 0),
                "success_rate": agentic_metrics.get("success_rate", 0),
                "fallbacks": self._stats["agentic_fallbacks"]
            },
            "comparison": {
                "latency_diff_ms": agentic_metrics.get("avg_latency_ms", 0) - rule_metrics.get("avg_latency_ms", 0),
                "call_ratio": self._stats["agentic_calls"] / (self._stats["rule_calls"] + self._stats["agentic_calls"] + 0.01)
            }
        }
```

---

## 八、切换策略设计

### 7.1 策略矩阵

| 维度 | 规则引擎 | Agentic引擎 |
|------|----------|-------------|
| **响应延迟** | <100ms | 1-3s |
| **计算成本** | 低（无LLM） | 高（多次LLM） |
| **输出稳定性** | 高（确定性） | 中（非确定性） |
| **需求灵活性** | 中（需规则） | 高（LLM生成） |
| **语义理解** | 低（关键词） | 高（深度理解） |
| **迭代优化** | 低（参数调整） | 高（语义调整） |
| **适用用户** | 大众用户 | 高端用户 |

### 7.2 推荐切换策略

```yaml
# 切换策略配置
switch_strategy:

  # 1. 默认策略
  default: "rule"  # 默认使用规则引擎（低延迟、低成本）

  # 2. 用户级策略
  user_level:
    # 高端用户强制Agentic
    premium_users:
      trigger: "membership_level in ['gold', 'platinum', 'vip']"
      engine: "agentic"
      reason: "高端用户愿意付费等待更好服务"
    
    # 用户手动选择
    user_choice:
      allow_override: true
      api_param: "engine"
      values: ["rule", "agentic"]

  # 3. 场景触发策略
  scene_trigger:
    # 复杂需求关键词 → Agentic
    complex_need:
      keywords: ["书卷气", "上进心", "有内涵", "气质", "幽默风趣", "稳重靠谱"]
      engine: "agentic"
      reason: "复杂抽象概念需要LLM理解"
    
    # 用户反馈触发 → Agentic
    feedback_trigger:
      keywords: ["不满意", "想要", "更喜欢", "希望能"]
      engine: "agentic"
      reason: "反馈调整需要语义理解"
    
    # 首次深度匹配 → Agentic
    first_deep_match:
      trigger: "user_interaction_count < 5 AND has_explicit_preference"
      engine: "agentic"
      reason: "首次深度匹配需要更精细分析"

  # 4. A/B测试策略
  ab_test:
    enabled: true
    ratio: 0.1  # 10%用户使用Agentic
    log_results: true  # 记录结果用于效果对比
    segment_by: "user_id_hash"  # 按用户ID hash分配（保证一致性）

  # 5. 失败Fallback策略
  fallback:
    from: "agentic"
    to: "rule"
    max_retries: 2
    log_error: true
    notify_user: false  # 不通知用户（静默切换）

  # 6. 时间策略
  time_strategy:
    # 低峰期更多使用Agentic（延迟敏感度低）
    low_traffic_hours: ["22:00-06:00"]
    low_traffic_engine_ratio: 0.3  # 低峰期30%使用Agentic
    
    # 高峰期更多使用规则
    high_traffic_hours: ["18:00-22:00"]
    high_traffic_engine_ratio: 0.05  # 高峰期5%使用Agentic

  # 7. 成本控制策略
  cost_control:
    # Agentic引擎每日调用上限
    agentic_daily_limit: 10000
    # 达到上限后强制切换到规则
    limit_exceeded_action: "force_rule"
```

### 7.3 策略决策流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    引擎选择决策流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入：MatchRequest (user_id, context)                          │
│                                                                 │
│  Step 1: 检查用户级覆盖                                         │
│  ─────────────────────────────────────────────                  │
│  if user_id in user_override:                                   │
│      return user_override[user_id]                              │
│                                                                 │
│  Step 2: 检查场景触发                                           │
│  ─────────────────────────────────────────────                  │
│  if context contains complex_need_keywords:                     │
│      return "agentic"                                           │
│                                                                 │
│  if context contains feedback_keywords:                         │
│      return "agentic"                                           │
│                                                                 │
│  Step 3: 检查高端用户                                           │
│  ─────────────────────────────────────────────                  │
│  if membership_level in ['gold', 'platinum', 'vip']:            │
│      return "agentic"                                           │
│                                                                 │
│  Step 4: A/B测试分配                                            │
│  ─────────────────────────────────────────────                  │
│  if hash(user_id) % 100 < ab_test_ratio * 100:                  │
│      return "agentic"                                           │
│                                                                 │
│  Step 5: 默认引擎                                               │
│  ─────────────────────────────────────────────                  │
│  return default_engine ("rule")                                 │
│                                                                 │
│  输出：engine_type ("rule" | "agentic")                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 九、API接口设计

### 9.1 许愿模式开关接口

```python
# POST /api/match/wish-mode/toggle

@router.post("/api/match/wish-mode/toggle")
async def toggle_wish_mode(
    request: WishModeToggleRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    切换许愿模式开关
    
    Request Body:
    {
        "user_id": "user_123",
        "enabled": true  // true=开启许愿模式，false=关闭（常规模式）
    }
    
    Response:
    {
        "success": true,
        "data": {
            "wish_mode_enabled": true,
            "mode_name": "许愿模式",
            "description": "开启后可描述理想类型，AI红娘将为你迭代推荐"
        }
    }
    """
    engine_type = "agentic" if request.enabled else "rule"
    engine_switch.set_user_engine(request.user_id, engine_type)
    
    return {
        "success": True,
        "data": {
            "wish_mode_enabled": request.enabled,
            "mode_name": "许愿模式" if request.enabled else "常规模式",
            "description": "开启后可描述理想类型，AI红娘将为你迭代推荐" if request.enabled else "系统将根据你的画像自动推荐"
        }
    }


# GET /api/match/wish-mode/status

@router.get("/api/match/wish-mode/status")
async def get_wish_mode_status(
    user_id: str,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取许愿模式状态
    
    Response:
    {
        "success": true,
        "data": {
            "wish_mode_enabled": true,
            "mode_name": "许愿模式",
            "current_engine": "agentic"
        }
    }
    """
    engine_type = engine_switch._get_current_engine(user_id)
    
    return {
        "success": True,
        "data": {
            "wish_mode_enabled": engine_type == "agentic",
            "mode_name": "许愿模式" if engine_type == "agentic" else "常规模式",
            "current_engine": engine_type
        }
    }
```

### 9.2 许愿模式对话接口

```python
# POST /api/match/wish-mode/chat

@router.post("/api/match/wish-mode/chat")
async def wish_mode_chat(
    request: WishModeChatRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    许愿模式对话接口
    
    用户描述理想类型，AI红娘理解并推荐。
    支持多轮对话，用户可不断细化需求。
    
    Request Body:
    {
        "user_id": "user_123",
        "message": "我喜欢有书卷气的，安静温和，喜欢读书，能聊深度话题",
        "conversation_id": "conv_456"  // 可选，多轮对话ID
    }
    
    Response:
    {
        "success": true,
        "data": {
            "conversation_id": "conv_456",
            "ai_response": {
                "understanding": "我理解你在寻找一位知性温和的伴侣...",
                "recommendations": [
                    {
                        "user_id": "user_789",
                        "name": "小林",
                        "match_reason": "教师，喜欢哲学，性格安静，符合你描述的书卷气特质",
                        "score": 0.85,
                        "profile": {...}
                    }
                ],
                "suggestions": ["你是否也希望TA有一定的事业心？", "对年龄有特别偏好吗？"]
            },
            "can_continue": true  // 是否可以继续对话调整
        }
    }
    """
    match_request = MatchRequest(
        user_id=request.user_id,
        limit=5,
        context={
            "user_message": request.message,
            "conversation_id": request.conversation_id
        }
    )
    
    result = await engine_switch.match(match_request)
    
    return {
        "success": True,
        "data": {
            "conversation_id": request.conversation_id or str(uuid.uuid4()),
            "ai_response": {
                "understanding": result.reasoning,
                "recommendations": result.candidates,
                "suggestions": result.metadata.get("suggestions", [])
            },
            "can_continue": True
        }
    }
```

### 9.3 匹配推荐接口

```python
# POST /api/match/recommendations

@router.post("/api/match/recommendations")
async def get_recommendations(
    request: MatchRecommendRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取匹配推荐
    
    - 许愿模式关闭：常规模式，快速推荐
    - 许愿模式开启：许愿模式，AI迭代推荐
    
    Request Body:
    {
        "user_id": "user_123",
        "limit": 10,
        "wish_mode": true,  // 可选，直接指定模式（覆盖用户设置）
        "wish_description": "我喜欢有书卷气的...",  // 许愿模式下的描述
        "context": {       // 可选，上下文信息
            "scene": "first_match"
        }
    }
    
    Response:
    {
        "success": true,
        "data": {
            "candidates": [
                {
                    "user_id": "user_456",
                    "score": 0.85,
                    "match_reasoning": "匹配理由...",
                    "profile": {
                        "name": "小红",
                        "age": 26,
                        ...
                    }
                }
            ],
            "mode": "wish",  // 当前模式
            "engine_type": "agentic",  // 实际使用的引擎
            "reasoning": "...",        // 许愿模式下的AI推理过程
            "metadata": {
                "iterations": 2,
                "latency_ms": 1500
            }
        }
    }
    """
    # 确定模式
    if request.wish_mode is not None:
        engine_type = "agentic" if request.wish_mode else "rule"
        engine_switch.set_user_engine(request.user_id, engine_type)
    
    match_request = MatchRequest(
        user_id=request.user_id,
        limit=request.limit,
        context={
            **(request.context or {}),
            "wish_description": request.wish_description
        }
    )
    
    result = await engine_switch.match(match_request)
    
    # 获取当前模式名称
    engine_type = result.engine_type
    mode_name = "许愿模式" if engine_type == "agentic" else "常规模式"
    
    return {
        "success": True,
        "data": {
            "candidates": result.candidates,
            "mode": "wish" if engine_type == "agentic" else "normal",
            "mode_name": mode_name,
            "engine_type": result.engine_type,
            "reasoning": result.reasoning,
            "metadata": result.metadata
        }
    }
```

### 9.4 反馈调整接口

```python
# POST /api/match/adjust

@router.post("/api/match/adjust")
async def adjust_recommendations(
    request: MatchAdjustRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    根据用户反馈调整推荐
    
    常规模式：参数级调整（扩大/缩小范围）
    许愿模式：语义级调整（理解用户真实意图）
    
    Request Body:
    {
        "user_id": "user_123",
        "feedback": "推荐的太外向了，我更喜欢内向安静的",
        "limit": 10
    }
    
    Response:
    {
        "success": true,
        "data": {
            "candidates": [...],
            "mode": "wish",
            "adjustment_processed": "推荐的太外向了...",
            "ai_understanding": "我理解你更偏好内向安静的伴侣，让我重新寻找..."
        }
    }
    """
    match_request = MatchRequest(
        user_id=request.user_id,
        limit=request.limit,
        context={"feedback": request.feedback}
    )
    
    result = await engine_switch.adjust(match_request, request.feedback)
    
    mode_name = "许愿模式" if result.engine_type == "agentic" else "常规模式"
    
    return {
        "success": True,
        "data": {
            "candidates": result.candidates,
            "mode": "wish" if result.engine_type == "agentic" else "normal",
            "mode_name": mode_name,
            "adjustment_processed": request.feedback,
            "ai_understanding": result.reasoning
        }
    }
```

```python
# GET /api/match/engine/config

@router.get("/api/match/engine/config")
async def get_engine_config(
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取引擎配置
    
    Response:
    {
        "success": true,
        "data": {
            "default_engine": "rule",
            "agentic_enabled": true,
            "ab_test_ratio": 0.1,
            "premium_agentic": true
        }
    }
    """
    return {
        "success": True,
        "data": engine_switch.get_config()
    }


# PUT /api/match/engine/config

@router.put("/api/match/engine/config")
async def update_engine_config(
    request: EngineConfigRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    更新引擎配置（管理员接口）
    
    Request Body:
    {
        "default_engine": "rule",
        "ab_test_ratio": 0.2,
        "agentic_enabled": true
    }
    """
    if request.default_engine:
        engine_switch.set_default_engine(request.default_engine)
    
    if request.ab_test_ratio:
        engine_switch.set_ab_test_ratio(request.ab_test_ratio)
    
    if request.agentic_enabled is not None:
        engine_switch.enable_agentic(request.agentic_enabled)
    
    return {
        "success": True,
        "data": engine_switch.get_config()
    }


# POST /api/match/engine/user-override

@router.post("/api/match/engine/user-override")
async def set_user_engine(
    request: UserEngineOverrideRequest,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    为特定用户设置引擎
    
    Request Body:
    {
        "user_id": "user_123",
        "engine": "agentic"
    }
    """
    engine_switch.set_user_engine(request.user_id, request.engine)
    
    return {
        "success": True,
        "message": f"User {request.user_id} engine set to {request.engine}"
    }


# DELETE /api/match/engine/user-override/{user_id}

@router.delete("/api/match/engine/user-override/{user_id}")
async def remove_user_override(
    user_id: str,
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    移除用户级引擎覆盖
    """
    engine_switch.remove_user_override(user_id)
    
    return {
        "success": True,
        "message": f"User {user_id} override removed"
    }


# GET /api/match/engine/stats

@router.get("/api/match/engine/stats")
async def get_engine_stats(
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取引擎运行统计
    
    Response:
    {
        "success": true,
        "data": {
            "rule_calls": 10000,
            "agentic_calls": 1500,
            "agentic_fallbacks": 50,
            "rule_engine_metrics": {...},
            "agentic_engine_metrics": {...}
        }
    }
    """
    return {
        "success": True,
        "data": engine_switch.get_stats()
    }


# GET /api/match/engine/comparison

@router.get("/api/match/engine/comparison")
async def get_engine_comparison(
    engine_switch: EngineSwitch = Depends(get_engine_switch)
):
    """
    获取引擎对比报告（A/B测试效果）
    
    Response:
    {
        "success": true,
        "data": {
            "rule_engine": {
                "calls": 10000,
                "avg_latency_ms": 80,
                "success_rate": 0.99
            },
            "agentic_engine": {
                "calls": 1500,
                "avg_latency_ms": 2000,
                "avg_iterations": 2.1,
                "convergence_rate": 0.85,
                "fallbacks": 50
            },
            "comparison": {
                "latency_diff_ms": 1920,
                "call_ratio": 0.13
            }
        }
    }
    """
    return {
        "success": True,
        "data": engine_switch.get_comparison_report()
    }
```

---

## 十、对比分析

### 9.1 性能对比

| 指标 | 规则引擎 | Agentic引擎 |
|------|----------|-------------|
| 平均延迟 | <100ms | 1-3s |
| 平均LLM调用 | 0 | 3-7次 |
| 成本（每次匹配） | ~$0.001 | ~$0.05-0.1 |
| 输出稳定性 | 高（确定性） | 中（非确定性） |
| 并发能力 | 高 | 中（LLM限流） |

### 9.2 能力对比

| 能力维度 | 规则引擎 | Agentic引擎 |
|----------|----------|-------------|
| 规则内需求 | ✅ 高效 | ✅ 可用 |
| 复杂需求 | ⚠️ 需预定义规则 | ✅ 实时理解 |
| 自然语言交互 | ❌ 不支持 | ✅ 支持 |
| 迭代调整 | ⚠️ 参数级 | ✅ 语义级 |
| 抽象概念理解 | ❌ 不支持 | ✅ 支持 |
| 推理过程透明 | ⚠️ 规则可解释 | ✅ Trace可解释 |
| 市场竞争力 | ✅ 已集成 | ⚠️ 需额外设计 |
| 双向选择概率 | ✅ 已集成 | ⚠️ 需额外设计 |
| 黑名单过滤 | ✅ 已集成 | ⚠️ 需额外设计 |

### 9.3 适用场景矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│                     适用场景矩阵                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  场景                    │ 规则引擎 │ Agentic引擎 │ 推荐        │
│  ────────────────────────┼──────────┼─────────────┼────────────  │
│  大众用户高频匹配         │ ✅       │ ⚠️         │ 规则         │
│  高端用户深度匹配         │ ⚠️       │ ✅          │ Agentic      │
│  简单需求（年龄/身高）    │ ✅       │ ✅          │ 规则         │
│  复杂需求（抽象概念）     │ ❌       │ ✅          │ Agentic      │
│  自然语言偏好表达         │ ❌       │ ✅          │ Agentic      │
│  用户反馈调整             │ ⚠️       │ ✅          │ Agentic      │
│  首次匹配（冷启动）       │ ⚠️       │ ✅          │ Agentic      │
│  批量推荐                 │ ✅       │ ⚠️         │ 规则         │
│  实时聊天推荐             │ ✅       │ ❌          │ 规则         │
│  深度关系分析             │ ⚠️       │ ✅          │ Agentic      │
│                                                                 │
│  ✅ = 适合  ⚠️ = 可用但不是最佳  ❌ = 不适合                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十一、实施路线

### 10.1 实施阶段

```
┌─────────────────────────────────────────────────────────────────┐
│                      实施路线图                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 基础架构（1周）                                       │
│  ├── Day 1-2: MatchEngine抽象接口设计                           │
│  ├── Day 3-4: EngineSwitch切换器实现                            │
│  ├── Day 5-7: 基础API实现                                       │
│  └── 里程碑: 双引擎框架可运行                                   │
│                                                                 │
│  Phase 2: 规则引擎适配（1周）                                   │
│  ├── Day 1-3: RuleMatchEngine实现（基于现有代码）               │
│  ├── Day 4-5: 调整方法实现                                      │
│  ├── Day 6-7: 单元测试                                          │
│  └── 里程碑: 规则引擎通过测试                                   │
│                                                                 │
│  Phase 3: Agentic引擎实现（2周）                                │
│  ├── Day 1-3: LLM Prompt设计                                    │
│  ├── Day 4-7: AgenticMatchEngine核心实现                        │
│  ├── Day 8-10: 迭代优化逻辑                                     │
│  ├── Day 11-14: 单元测试 + 集成测试                              │
│  └── 里程碑: Agentic引擎通过测试                                │
│                                                                 │
│  Phase 4: 切换策略实现（1周）                                   │
│  ├── Day 1-3: 策略配置实现                                      │
│  ├── Day 4-5: A/B测试机制                                       │
│  ├── Day 6-7: 管理接口实现                                      │
│  └── 里程碑: 切换策略可用                                       │
│                                                                 │
│  Phase 5: 上线与验证（持续）                                    │
│  ├── 灰度发布（10%用户）                                        │
│  ├── 效果监控                                                   │
│  ├── A/B测试对比                                                │
│  ├── 规则学习（Agentic结果用于规则优化）                        │
│  └── 里程碑: 生产环境稳定运行                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 里程碑验收标准

| 阶段 | 里程碑 | 验收标准 |
|------|--------|---------|
| Phase 1 | 框架可运行 | MatchEngine接口定义完成，EngineSwitch可切换 |
| Phase 2 | 规则引擎通过测试 | 单元测试覆盖率 >80%，延迟 <100ms |
| Phase 3 | Agentic引擎通过测试 | 单元测试覆盖率 >80%，迭代成功率 >70% |
| Phase 4 | 切换策略可用 | 管理接口可用，A/B测试可配置 |
| Phase 5 | 生产稳定运行 | 双引擎可用，Fallback正常，监控完善 |

### 10.3 关键风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Agentic延迟过高 | 用户体验下降 | 设置合理超时，Fallback到规则 |
| LLM成本过高 | 运营成本增加 | 设置每日上限，高峰期减少使用 |
| LLM输出不稳定 | 匹配质量波动 | 多轮验证，人工审核 |
| 双引擎维护成本 | 开发资源紧张 | 共用VectorDB，差异最小化 |

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| **许愿模式** | 用户可开启的模式，用自然语言描述理想类型，AI红娘迭代推荐 |
| **常规模式** | 默认模式，系统基于用户画像自动推荐 |
| MatchEngine | 匹配引擎抽象接口 |
| RuleMatchEngine | 规则引擎，对应常规模式 |
| AgenticMatchEngine | Agentic引擎，对应许愿模式 |
| EngineSwitch | 引擎切换器，控制许愿模式开关 |
| AI红娘 | 许愿模式下的AI角色，理解用户需求并推荐 |
| 迭代推荐 | 许愿模式下，用户可不断调整需求，AI持续优化推荐 |
| Fallback | 失败时的降级策略（许愿模式失败→常规模式） |

### B. 用户交互示例

#### 常规模式（许愿模式关闭）

```
用户：[点击推荐按钮]
      ↓
系统：返回推荐列表（<100ms）
      ├── 小红，26岁，北京
      ├── 小李，28岁，上海
      └── 小王，25岁，北京
      ↓
用户：[左滑/右滑选择]
```

#### 许愿模式（许愿模式开启）

```
用户：[开启许愿模式开关]
      ↓
系统：请描述你理想中的TA
      ↓
用户：我喜欢有书卷气的，安静温和，能聊深度话题
      ↓
AI红娘：我理解你在寻找一位知性温和的伴侣。
       让我为你寻找...
       ↓
AI红娘：为你推荐：
       1. 小林 - 教师，喜欢哲学，性格安静
       2. 小陈 - 编辑，书卷气浓，热爱文学
       3. 小王 - 律师，理性温和，喜欢深度讨论
       ↓
用户：小林看起来不错，但能不能再有些上进心？
      ↓
AI红娘：明白了，在知性温和的基础上，增加上进心特质。
       让我重新寻找...
       ↓
AI红娘：为你重新推荐：
       1. 小张 - 创业者，文理兼修，有上进心
       2. 小陈 - 编辑，正在攻读硕士
       ↓
用户：小张看起来不错！
      ↓
AI红娘：太好了！我已把小张推荐给你。
       你们有几个共同话题...
```

### C. 参考文档

- [VECTOR_MATCH_SYSTEM_DESIGN.md](../VECTOR_MATCH_SYSTEM_DESIGN.md) - 规则引擎详细设计（176维向量）

---

> 文档版本：v1.1
> 最后更新：2026-04-10
> 作者：AI Team
>
> **v1.1 更新说明**：
> - **许愿模式**：将Agentic引擎包装为"许愿模式"，用户可自然语言描述理想类型
> - **开关设计**：用户可通过开关在常规模式和许愿模式间切换
> - **迭代推荐**：许愿模式下AI红娘迭代优化推荐结果
> - **对话式交互**：支持多轮对话，用户可不断细化需求