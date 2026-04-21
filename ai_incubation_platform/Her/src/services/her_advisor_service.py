"""
Her 顾问服务 - 核心大脑

职责：
1. 认知偏差识别（LLM自主判断，不硬编码）
2. 匹配建议生成
3. 主动建议输出

Her 的定位：拥有20年经验的专业婚恋顾问
- 心理学知识：依恋理论、人格类型、权力动态、情感需求
- 社会学知识：社会阶层匹配、文化背景差异、人生阶段匹配
- 人际关系学知识：沟通风格、冲突处理、相处节奏
- 婚恋经验：典型案例推理能力

性能优化（v1.30.0）：
- LLM 调用并行化：使用 asyncio.gather 并行执行多维度分析
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio

from utils.logger import logger
from services.llm_semantic_service import get_llm_semantic_service, call_llm_sync
from models.her_advisor_models import (
    CognitiveBiasAnalysisDB,
    MatchAdviceDB,
    HerKnowledgeCaseDB,
)
from services.profile_dataclasses import DesireProfile, SelfProfile

# ============= Her 知识框架 =============

HER_KNOWLEDGE_FRAMEWORK = {
    "心理学": {
        "依恋理论": {
            "类型": ["安全型", "焦虑型", "回避型", "混乱型"],
            "匹配规律": {
                "安全型+安全型": "理想匹配，稳定和谐",
                "安全型+焦虑型": "安全型能稳定焦虑型",
                "焦虑型+回避型": "痛苦循环，焦虑型追，回避型逃",
                "回避型+回避型": "可能缺乏深度连接",
            }
        },
        "人格类型": {
            "关注维度": ["外向/内向", "理性/感性", "控制/顺从"],
            "匹配规律": {
                "双强势": "容易产生权力斗争",
                "双内向": "可能缺乏火花",
                "强势+温和有主见": "平衡互补",
            }
        },
        "权力动态": {
            "类型": ["控制型", "顺从型", "平等型", "竞争型"],
            "匹配规律": {
                "控制型+控制型": "持续冲突",
                "控制型+顺从型": "短期和谐，长期可能失衡",
                "控制型+平等型": "需要调整相处模式",
            }
        },
        "情感需求": {
            "类型": ["需要被照顾", "需要被尊重", "需要被理解", "需要被认可"],
            "匹配规律": {
                "需求错配": "一方需要照顾，另一方独立 → 矛盾",
                "需求互补": "一方需要认可，另一方善于给予认可 → 匹配",
            }
        },
    },
    "社会学": {
        "人生阶段": {
            "阶段": ["单身探索期", "稳定恋爱期", "婚姻准备期", "育儿期"],
            "匹配规律": "阶段相近更易理解彼此",
        },
        "价值观差异": {
            "关注维度": ["家庭观念", "金钱观念", "事业观念"],
            "匹配规律": "核心价值观冲突 → 长期矛盾",
        },
    },
    "人际关系学": {
        "沟通风格": {
            "类型": ["直接型", "间接型", "情感型", "逻辑型"],
            "匹配规律": {
                "直接型+间接型": "需要适应彼此的表达方式",
                "情感型+逻辑型": "互补但需要理解差异",
            }
        },
        "冲突处理": {
            "类型": ["回避型", "竞争型", "妥协型", "合作型"],
            "匹配规律": {
                "双回避型": "问题积累不解决",
                "双竞争型": "持续争吵",
                "合作型+任何型": "能促进问题解决",
            }
        },
    },
}


@dataclass
class CognitiveBiasAnalysis:
    """
    认知偏差分析结果

    Her 自主判断：用户想要的 ≠ 用户适合的
    """
    has_bias: bool = False
    bias_type: str = ""
    bias_description: str = ""
    actual_suitable_type: str = ""
    potential_risks: List[str] = field(default_factory=list)
    adjustment_suggestion: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_bias": self.has_bias,
            "bias_type": self.bias_type,
            "bias_description": self.bias_description,
            "actual_suitable_type": self.actual_suitable_type,
            "potential_risks": self.potential_risks,
            "adjustment_suggestion": self.adjustment_suggestion,
            "confidence": self.confidence,
        }


@dataclass
class MatchAdvice:
    """
    匹配建议

    Her 专业判断：是否推荐 + 原因 + 建议
    """
    advice_type: str = ""  # strongly_recommend, recommend_with_caution, not_recommended
    advice_content: str = ""
    reasoning: str = ""
    suggestions_for_user: List[str] = field(default_factory=list)
    potential_issues: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "advice_type": self.advice_type,
            "advice_content": self.advice_content,
            "reasoning": self.reasoning,
            "suggestions_for_user": self.suggestions_for_user,
            "potential_issues": self.potential_issues,
            "compatibility_score": self.compatibility_score,
        }


@dataclass
class ProactiveSuggestion:
    """
    主动建议

    Her 在用户搜索时主动给出意见
    """
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    has_critical_suggestion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestions": self.suggestions,
            "has_critical_suggestion": self.has_critical_suggestion,
        }


# ============= CognitiveBiasDetector - 认知偏差识别器 =============

class CognitiveBiasDetector:
    """
    认知偏差识别器

    关键设计：不硬编码规则，由 LLM 自主判断
    """

    def __init__(self):
        self._llm_service = get_llm_semantic_service()

    async def detect_cognitive_bias(
        self,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
    ) -> CognitiveBiasAnalysis:
        """
        让 Her 自主分析认知偏差

        LLM Prompt 框架：
        - 告知用户画像（SelfProfile + DesireProfile）
        - 告知 Her 的专业知识框架
        - 让 Her 自主判断是否存在偏差
        """
        logger.info(f"[Her] 开始认知偏差分析")

        # 构建 Prompt
        prompt = self._build_bias_analysis_prompt(self_profile, desire_profile)

        # 调用 LLM
        try:
            llm_response = await self._call_llm_async(prompt)
            bias_analysis = self._parse_bias_analysis(llm_response)

            logger.info(f"[Her] 认知偏差分析完成: has_bias={bias_analysis.has_bias}, type={bias_analysis.bias_type}")
            return bias_analysis

        except Exception as e:
            logger.error(f"[Her] 认知偏差分析失败: {e}")
            # 返回默认结果（无偏差）
            return CognitiveBiasAnalysis(
                has_bias=False,
                confidence=0.0,
            )

    def _build_bias_analysis_prompt(
        self,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
    ) -> str:
        """构建认知偏差分析 Prompt"""

        # 构建知识框架提示
        knowledge_prompt = """
【Her 的专业知识框架】

心理学知识：
- 依恋理论：安全型、焦虑型、回避型、混乱型
  * 焦虑型+回避型 = 痛苦循环（焦虑型追，回避型逃）
  * 安全型能稳定其他类型

- 权力动态：控制型、顺从型、平等型、竞争型
  * 双强势（控制型+控制型） = 持续权力斗争
  * 强势+温和有主见 = 平衡互补

- 情感需求：需要被照顾、需要被尊重、需要被理解、需要被认可
  * 需求错配 = 矛盾（如需要照顾 vs 独立型）

社会学知识：
- 人生阶段匹配：单身探索期、稳定恋爱期、婚姻准备期、育儿期
- 价值观冲突：家庭观念、金钱观念、事业观念差异 → 长期矛盾

人际关系学知识：
- 沟通风格：直接型、间接型、情感型、逻辑型
- 冲突处理：回避型、竞争型、妥协型、合作型
  * 双回避型 = 问题积累不解决
  * 双竞争型 = 持续争吵

典型案例：
- 双强势 → 持续冲突
- 双内向 → 缺乏火花
- 焦虑型+回避型 → 持续痛苦
- 控制型+独立型 → 权力斗争
- 需要照顾+独立型 → 需求错配

成功模式：
- 强势+温和有主见 → 平衡互补
- 内向+温暖外向 → 相互带动
- 焦虑型+安全型 → 稳定陪伴
"""

        return f'''你是一位拥有20年经验的专业婚恋顾问 Her。

{knowledge_prompt}

【用户画像 - 这个人是什么样的】
{json.dumps(self_profile.to_dict(), ensure_ascii=False, indent=2)}

关键维度：
- 实际性格：{self_profile.actual_personality}（基于行为分析，而非用户自称）
- 沟通风格：{self_profile.communication_style}
- 情感需求：{self_profile.emotional_needs}
- 权力倾向：{self_profile.power_dynamic}
- 依恋类型：{self_profile.attachment_style}

【用户偏好 - 这个人想要什么】
{json.dumps(desire_profile.to_dict(), ensure_ascii=False, indent=2)}

关键维度：
- 表面偏好：{desire_profile.surface_preference}（用户自称想要的）
- 实际偏好：{desire_profile.actual_preference}（基于搜索/点击行为推断）
- 偏好差距：{desire_profile.preference_gap}

【任务】
请自主分析这个用户是否存在"认知偏差"：
1. 用户想要的类型，和用户实际适合的类型是否一致？
2. 如果不一致，用心理学知识解释原因
3. 用户实际适合什么类型的人？
4. 如果用户坚持当前偏好，可能遇到什么问题？

【输出格式】
返回 JSON 格式：
{{
    "has_bias": true/false,
    "bias_type": "偏差类型（如：双强势偏差、依恋错配、需求错配等）",
    "bias_description": "偏差的心理学解释（为什么想要的和适合的不一致）",
    "actual_suitable_type": "用户实际适合的类型描述",
    "potential_risks": ["如果坚持当前偏好可能遇到的问题"],
    "adjustment_suggestion": "Her 的调整建议",
    "confidence": 0.0-1.0
}}

只返回 JSON，不要其他文字。'''

    def _parse_bias_analysis(self, response: str) -> CognitiveBiasAnalysis:
        """解析 LLM 返回的认知偏差分析"""
        try:
            # 清理响应
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            data = json.loads(response)

            return CognitiveBiasAnalysis(
                has_bias=data.get("has_bias", False),
                bias_type=data.get("bias_type", ""),
                bias_description=data.get("bias_description", ""),
                actual_suitable_type=data.get("actual_suitable_type", ""),
                potential_risks=data.get("potential_risks", []),
                adjustment_suggestion=data.get("adjustment_suggestion", ""),
                confidence=data.get("confidence", 0.0),
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Her] 解析认知偏差分析失败: {e}")
            return CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

    async def _call_llm_async(self, prompt: str) -> str:
        """异步调用 LLM"""
        llm_service = get_llm_semantic_service()
        return await llm_service._call_llm(prompt)


# ============= MatchAdvisor - 匹配建议生成器 =============

class MatchAdvisor:
    """
    匹配建议生成器

    四层匹配架构：
    1. 意向匹配（双向）
    2. 认知偏差识别（Her 专业判断）
    3. 双向适配度分析
    4. Her 专业建议
    """

    def __init__(self):
        self._bias_detector = CognitiveBiasDetector()
        self._llm_service = get_llm_semantic_service()

    async def generate_match_advice(
        self,
        user_a_profile: Tuple[SelfProfile, DesireProfile],
        user_b_profile: Tuple[SelfProfile, DesireProfile],
        compatibility_score: float,
    ) -> MatchAdvice:
        """
        让 Her 生成匹配建议

        性能优化版本：
        - 并行化 LLM 调用（偏差检测 + 适配度分析）
        - 使用 asyncio.gather 并行执行

        四种情况：
        ① 双向意向匹配 + 双向实际适合 → "很合适，推荐"
        ② 双向意向匹配 + 单/双向不适合 → "表面匹配但有隐患，建议..."
        ③ 单向意向匹配 → "对方可能更适合你，但意向不对称，建议..."
        ④ 意向不匹配但实际适合 → "你们实际很合适，建议调整期待..."
        """
        logger.info(f"[Her] 开始生成匹配建议（并行化版本）")

        self_a, desire_a = user_a_profile
        self_b, desire_b = user_b_profile

        # Step 1: 检查双向意向匹配（本地计算，无 LLM）
        intent_match = self._check_intent_match(desire_a, desire_b, self_a, self_b)

        # Step 2 & 3: 并行执行认知偏差检测和适配度分析
        bias_a_task = self._bias_detector.detect_cognitive_bias(self_a, desire_a)
        bias_b_task = self._bias_detector.detect_cognitive_bias(self_b, desire_b)

        # 并行等待两个偏差检测结果
        bias_a, bias_b = await asyncio.gather(bias_a_task, bias_b_task)

        # 适配度分析（依赖偏差结果，但可以并行与建议生成）
        compatibility_analysis = await self._analyze_compatibility(
            self_a, self_b, bias_a, bias_b
        )

        # Step 4: Her 生成专业建议
        advice = await self._generate_professional_advice(
            intent_match, bias_a, bias_b, compatibility_analysis, compatibility_score
        )

        logger.info(f"[Her] 匹配建议完成: type={advice.advice_type}")
        return advice

    def _check_intent_match(
        self,
        desire_a: DesireProfile,
        desire_b: DesireProfile,
        self_a: SelfProfile,
        self_b: SelfProfile,
    ) -> str:
        """检查双向意向匹配"""
        # A 想要 B 这种类型？
        a_wants_b = self._check_type_match(desire_a.surface_preference, self_b)

        # B 想要 A 这种类型？
        b_wants_a = self._check_type_match(desire_b.surface_preference, self_a)

        if a_wants_b and b_wants_a:
            return "bidirectional_match"
        elif a_wants_b or b_wants_a:
            return "unidirectional_match"
        else:
            return "no_intent_match"

    def _check_type_match(self, preference: str, target_profile: SelfProfile) -> bool:
        """检查类型是否匹配偏好（简单规则）"""
        # 这是一个简化版，实际应该由 LLM 判断
        if not preference:
            return True  # 无偏好则默认匹配

        # 检查关键词
        pref_lower = preference.lower()

        # 性别检查
        if "男" in pref_lower and target_profile.gender != "male":
            return False
        if "女" in pref_lower and target_profile.gender != "female":
            return False

        # 性格关键词检查
        if "内向" in pref_lower and "内向" not in target_profile.actual_personality:
            return False
        if "外向" in pref_lower and "外向" not in target_profile.actual_personality:
            return False

        return True

    async def _analyze_compatibility(
        self,
        self_a: SelfProfile,
        self_b: SelfProfile,
        bias_a: CognitiveBiasAnalysis,
        bias_b: CognitiveBiasAnalysis,
    ) -> Dict[str, Any]:
        """Her 分析双向适配度"""
        prompt = self._build_compatibility_prompt(self_a, self_b, bias_a, bias_b)

        try:
            llm_response = await self._call_llm_async(prompt)
            return self._parse_compatibility_response(llm_response)
        except Exception as e:
            logger.error(f"[Her] 适配度分析失败: {e}")
            return {}

    def _build_compatibility_prompt(
        self,
        self_a: SelfProfile,
        self_b: SelfProfile,
        bias_a: CognitiveBiasAnalysis,
        bias_b: CognitiveBiasAnalysis,
    ) -> str:
        """构建适配度分析 Prompt"""

        return f'''你是一位拥有20年经验的专业婚恋顾问 Her。

请分析两个用户的适配度。

【用户A画像】
{json.dumps(self_a.to_dict(), ensure_ascii=False, indent=2)}

【用户A认知偏差】
{json.dumps(bias_a.to_dict(), ensure_ascii=False, indent=2) if bias_a.has_bias else "无明显偏差"}

【用户B画像】
{json.dumps(self_b.to_dict(), ensure_ascii=False, indent=2)}

【用户B认知偏差】
{json.dumps(bias_b.to_dict(), ensure_ascii=False, indent=2) if bias_b.has_bias else "无明显偏差"}

【分析维度】
1. 性格互补性：两人性格是否互补或冲突？
2. 依恋类型匹配：依恋类型是否匹配？
3. 权力动态：权力倾向是否平衡？
4. 情感需求匹配：情感需求是否能互相满足？
5. 沟通风格兼容：沟通方式是否兼容？
6. 价值观一致性：核心价值观是否一致？

【输出格式】
返回 JSON 格式：
{{
    "overall_compatibility": 0.0-1.0,
    "personality_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "attachment_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "power_dynamic_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "emotional_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "communication_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "value_match": {{
        "score": 0.0-1.0,
        "analysis": "分析说明"
    }},
    "strengths": ["关系优势"],
    "challenges": ["潜在挑战"],
    "critical_issues": ["关键问题（如果有）"]
}}

只返回 JSON，不要其他文字。'''

    def _parse_compatibility_response(self, response: str) -> Dict[str, Any]:
        """解析适配度分析响应"""
        try:
            response = response.strip()
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            return json.loads(response.strip())
        except:
            return {}

    async def _generate_professional_advice(
        self,
        intent_match: str,
        bias_a: CognitiveBiasAnalysis,
        bias_b: CognitiveBiasAnalysis,
        compatibility_analysis: Dict[str, Any],
        compatibility_score: float,
    ) -> MatchAdvice:
        """Her 生成专业建议"""

        # 根据情况类型生成建议
        prompt = self._build_advice_prompt(
            intent_match, bias_a, bias_b, compatibility_analysis, compatibility_score
        )

        try:
            llm_response = await self._call_llm_async(prompt)
            return self._parse_advice_response(llm_response, compatibility_score)
        except Exception as e:
            logger.error(f"[Her] 建议生成失败: {e}")
            # 返回默认建议
            return MatchAdvice(
                advice_type="recommend_with_caution",
                advice_content="建议进一步沟通了解彼此",
                compatibility_score=compatibility_score,
            )

    def _build_advice_prompt(
        self,
        intent_match: str,
        bias_a: CognitiveBiasAnalysis,
        bias_b: CognitiveBiasAnalysis,
        compatibility_analysis: Dict[str, Any],
        compatibility_score: float,
    ) -> str:
        """构建建议生成 Prompt"""

        situation_description = {
            "bidirectional_match": "双方都有意向，表面匹配",
            "unidirectional_match": "单方有意向，意向不对称",
            "no_intent_match": "双方意向不匹配",
        }

        return f'''你是一位拥有20年经验的专业婚恋顾问 Her。

请根据以下信息，给出专业匹配建议。

【意向匹配状态】
{situation_description.get(intent_match, intent_match)}

【认知偏差分析】
用户A偏差：{json.dumps(bias_a.to_dict(), ensure_ascii=False) if bias_a.has_bias else "无明显偏差"}
用户B偏差：{json.dumps(bias_b.to_dict(), ensure_ascii=False) if bias_b.has_bias else "无明显偏差"}

【适配度分析】
{json.dumps(compatibility_analysis, ensure_ascii=False, indent=2)}

【基础匹配分数】
{compatibility_score:.2f}

【任务】
请给出专业建议：

1. 确定建议类型：
   - strongly_recommend: 强烈推荐（双向匹配+双向适合）
   - recommend_with_caution: 谨慎推荐（表面匹配但有隐患）
   - not_recommended: 不推荐（有明显冲突）
   - suggest_adjustment: 建议调整期待（实际适合但表面不匹配）
   - potential_but_needs_work: 有潜力但需要努力

2. 给出建议内容：简洁、真诚、专业

3. 列出给双方的具体建议

4. 指出潜在问题

【输出格式】
返回 JSON 格式：
{{
    "advice_type": "建议类型",
    "advice_content": "建议内容（100字以内）",
    "reasoning": "推理过程",
    "suggestions_for_user": ["给用户的具体建议"],
    "potential_issues": ["潜在问题"]
}}

只返回 JSON，不要其他文字。'''

    def _parse_advice_response(
        self,
        response: str,
        compatibility_score: float
    ) -> MatchAdvice:
        """解析建议响应"""
        try:
            response = response.strip()
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]

            data = json.loads(response.strip())

            return MatchAdvice(
                advice_type=data.get("advice_type", "recommend_with_caution"),
                advice_content=data.get("advice_content", ""),
                reasoning=data.get("reasoning", ""),
                suggestions_for_user=data.get("suggestions_for_user", []),
                potential_issues=data.get("potential_issues", []),
                compatibility_score=compatibility_score,
            )
        except:
            return MatchAdvice(
                advice_type="recommend_with_caution",
                advice_content="建议进一步了解彼此",
                compatibility_score=compatibility_score,
            )

    async def _call_llm_async(self, prompt: str) -> str:
        """异步调用 LLM"""
        llm_service = get_llm_semantic_service()
        return await llm_service._call_llm(prompt)


# ============= ProactiveSuggestionGenerator - 主动建议生成器 =============

class ProactiveSuggestionGenerator:
    """
    主动建议生成器

    在用户搜索时给出专业意见，而非被动返回结果
    """

    def __init__(self):
        self._llm_service = get_llm_semantic_service()

    async def generate_proactive_suggestion(
        self,
        user_profile: Tuple[SelfProfile, DesireProfile],
        bias_analysis: CognitiveBiasAnalysis,
        matches: List[Dict[str, Any]],
    ) -> ProactiveSuggestion:
        """
        生成主动建议

        建议类型：
        1. 认知偏差提醒："你想要的和你适合的可能不一致"
        2. 搜索范围建议："匹配池较小，建议放宽条件"
        3. 行为模式提醒："你说喜欢内向的，但最近看了户外活动的人"
        4. 匹配质量建议："当前匹配质量较高/较低"
        """
        logger.info(f"[Her] 开始生成主动建议")

        suggestions = []

        self_profile, desire_profile = user_profile

        # 1. 认知偏差提醒（高优先级）
        if bias_analysis.has_bias:
            suggestions.append({
                "type": "cognitive_bias_reminder",
                "importance": "high",
                "message": f"Her 发现：{bias_analysis.bias_description}",
                "suggestion": bias_analysis.adjustment_suggestion,
            })

        # 2. 搜索范围建议
        if matches and len(matches) < 3:
            suggestions.append({
                "type": "search_range_suggestion",
                "importance": "medium",
                "message": f"当前条件下匹配池较小，只有{len(matches)}人",
                "suggestion": "建议放宽年龄或地点范围，会有更多选择",
            })

        # 3. 行为模式提醒
        if desire_profile.preference_gap:
            suggestions.append({
                "type": "behavior_pattern_reminder",
                "importance": "medium",
                "message": f"你说想要{desire_profile.surface_preference}，但最近的行为显示你更倾向{desire_profile.actual_preference}",
                "suggestion": "要不要试试这类人？可能会有惊喜",
            })

        # 4. 匹配质量建议
        if matches:
            avg_score = sum(m.get("score", 0) for m in matches) / len(matches)
            if avg_score < 0.6:
                suggestions.append({
                    "type": "match_quality_reminder",
                    "importance": "low",
                    "message": "当前匹配对象的平均匹配度较低",
                    "suggestion": "建议稍后再来，或者调整一下你的期待",
                })
            elif avg_score > 0.8:
                suggestions.append({
                    "type": "match_quality_reminder",
                    "importance": "low",
                    "message": "当前匹配质量很高！",
                    "suggestion": "这些人很适合你，建议优先考虑",
                })

        return ProactiveSuggestion(
            suggestions=suggestions,
            has_critical_suggestion=bias_analysis.has_bias,
        )


# ============= HerAdvisorService - 主服务 =============

class HerAdvisorService:
    """
    Her 顾问服务 - 主服务

    整合所有组件，提供完整的 Her 顾问能力
    """

    def __init__(self):
        self._bias_detector = CognitiveBiasDetector()
        self._match_advisor = MatchAdvisor()
        self._proactive_generator = ProactiveSuggestionGenerator()
        self._llm_service = get_llm_semantic_service()

    async def analyze_user_bias(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
    ) -> CognitiveBiasAnalysis:
        """
        分析用户认知偏差

        Args:
            user_id: 用户ID
            self_profile: 自身画像
            desire_profile: 意愿画像

        Returns:
            认知偏差分析结果
        """
        logger.info(f"[HerAdvisor] 开始分析用户 {user_id} 的认知偏差")

        bias_analysis = await self._bias_detector.detect_cognitive_bias(
            self_profile, desire_profile
        )

        # 持久化分析结果
        await self._save_bias_analysis(user_id, bias_analysis, self_profile)

        return bias_analysis

    async def generate_match_advice(
        self,
        user_a_id: str,
        user_a_profile: Tuple[SelfProfile, DesireProfile],
        user_b_id: str,
        user_b_profile: Tuple[SelfProfile, DesireProfile],
        compatibility_score: float,
    ) -> MatchAdvice:
        """
        生成匹配建议

        Args:
            user_a_id: 用户A ID
            user_a_profile: 用户A画像
            user_b_id: 用户B ID
            user_b_profile: 用户B画像
            compatibility_score: 基础匹配分数

        Returns:
            匹配建议
        """
        logger.info(f"[HerAdvisor] 开始为 {user_a_id} 和 {user_b_id} 生成匹配建议")

        advice = await self._match_advisor.generate_match_advice(
            user_a_profile, user_b_profile, compatibility_score
        )

        # 持久化建议
        await self._save_match_advice(user_a_id, user_b_id, advice)

        return advice

    async def generate_proactive_suggestions(
        self,
        user_id: str,
        user_profile: Tuple[SelfProfile, DesireProfile],
        bias_analysis: CognitiveBiasAnalysis,
        matches: List[Dict[str, Any]],
    ) -> ProactiveSuggestion:
        """
        生成主动建议

        Args:
            user_id: 用户ID
            user_profile: 用户画像
            bias_analysis: 认知偏差分析
            matches: 匹配结果列表

        Returns:
            主动建议
        """
        logger.info(f"[HerAdvisor] 开始为用户 {user_id} 生成主动建议")

        return await self._proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

    async def _save_bias_analysis(
        self,
        user_id: str,
        bias_analysis: CognitiveBiasAnalysis,
        profile_snapshot: SelfProfile,
    ) -> None:
        """保存认知偏差分析结果"""
        # 这里可以持久化到数据库
        # 暂时只记录日志
        logger.info(f"[HerAdvisor] 用户 {user_id} 认知偏差分析: has_bias={bias_analysis.has_bias}")

    async def _save_match_advice(
        self,
        user_a_id: str,
        user_b_id: str,
        advice: MatchAdvice,
    ) -> None:
        """保存匹配建议"""
        logger.info(f"[HerAdvisor] {user_a_id}-{user_b_id} 匹配建议: type={advice.advice_type}")


# ============= 全局服务实例 =============

_her_advisor_service: Optional[HerAdvisorService] = None


def get_her_advisor_service() -> HerAdvisorService:
    """获取 Her 顾问服务单例"""
    global _her_advisor_service
    if _her_advisor_service is None:
        _her_advisor_service = HerAdvisorService()
        logger.info("HerAdvisorService initialized")
    return _her_advisor_service