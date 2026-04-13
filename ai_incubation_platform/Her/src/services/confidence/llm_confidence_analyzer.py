"""
LLM 深度验证服务

功能：
- 文本一致性分析（bio与聊天风格对比）
- 年龄语言推断（从聊天风格推断年龄段）
- 价值观深度推断（从行为和聊天推断价值观）
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import re

from utils.logger import logger
from db.models import UserDB, ChatMessageDB, BehaviorEventDB


# ============================================
# LLM 客户端接口（简化版，实际需对接真实LLM）
# ============================================

class MockLLMClient:
    """
    模拟LLM客户端（开发阶段使用）

    实际部署时替换为真实的LLM API调用
    """

    async def analyze_text(self, prompt: str) -> Dict[str, Any]:
        """
        模拟LLM分析

        实际实现需要：
        - 对接 OpenAI/Anthropic/本地模型
        - 处理 API 响应
        - 错误处理和重试
        """
        # 简化实现：基于关键词匹配模拟分析结果
        return {"mock": True, "note": "实际部署需对接真实LLM"}

    async def chat(self, prompt: str) -> str:
        """模拟聊天响应"""
        return "这是模拟响应，实际部署需对接真实LLM API"


# 全局LLM客户端（可替换为真实实现）
llm_client = MockLLMClient()


# ============================================
# 文本一致性分析器
# ============================================

class TextConsistencyAnalyzer:
    """分析用户描述文本与实际行为的一致性"""

    # 关键词权重映射
    PERSONALITY_KEYWORDS = {
        "introvert": {
            "positive": ["内向", "安静", "独处", "宅", "不爱说话", "害羞", "低调", "沉稳"],
            "negative": ["外向", "活泼", "开朗", "健谈", "热情", "社交达人"],
        },
        "outgoing": {
            "positive": ["外向", "活泼", "开朗", "健谈", "热情", "阳光", "爱交朋友", "社交"],
            "negative": ["内向", "安静", "独处", "宅", "害羞", "低调"],
        },
        "serious": {
            "positive": ["认真", "负责", "稳重", "踏实", "靠谱", "严谨", "成熟"],
            "negative": ["随意", "玩闹", "不靠谱", "幼稚", "轻浮"],
        },
        "playful": {
            "positive": ["幽默", "有趣", "搞笑", "玩闹", "轻松", "随性", "活泼"],
            "negative": ["严肃", "认真", "沉闷", "无趣", "古板"],
        },
    }

    # 价值观关键词映射
    VALUE_KEYWORDS = {
        "family_oriented": ["家庭", "家人", "孩子", "父母", "孝顺", "传统", "亲情"],
        "career_oriented": ["事业", "工作", "奋斗", "上进", "职业", "成功", "拼搏"],
        "relationship_oriented": ["爱情", "伴侣", "婚姻", "感情", "浪漫", "真心"],
        "freedom_oriented": ["自由", "独立", "旅行", "探索", "无拘束", "随性"],
    }

    async def analyze_bio_chat_consistency(
        self,
        user: UserDB,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        分析个人简介与聊天风格的一致性

        Returns:
            {
                "bio_chat_consistency": 0-1,
                "claimed_personality": "...",
                "inferred_personality": "...",
                "red_flags": [...],
                "suggestions": [...]
            }
        """
        # 获取用户个人简介
        bio = user.bio or ""

        # 获取聊天样本
        messages = db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user.id,
            ChatMessageDB.message_type == "text",
            ChatMessageDB.created_at >= datetime.now() - timedelta(days=days)
        ).order_by(ChatMessageDB.created_at.desc()).limit(50).all()

        if len(messages) < 5:
            return {
                "bio_chat_consistency": 0.5,
                "note": "聊天样本不足",
                "sample_size": len(messages),
            }

        # 合并聊天文本
        chat_text = " ".join([m.content for m in messages if m.content])
        chat_text_lower = chat_text.lower()

        # 从简介推断声称的性格倾向
        claimed_personality = self._infer_personality_from_text(bio)

        # 从聊天推断实际性格倾向
        inferred_personality = self._infer_personality_from_text(chat_text)

        # 计算一致性
        consistency = self._calculate_personality_match(claimed_personality, inferred_personality)

        # 检查红旗警告
        red_flags = self._detect_red_flags(bio, chat_text)

        return {
            "bio_chat_consistency": consistency,
            "claimed_personality": claimed_personality,
            "inferred_personality": inferred_personality,
            "bio_text": bio[:100] + "..." if len(bio) > 100 else bio,
            "chat_sample": chat_text[:200] + "..." if len(chat_text) > 200 else chat_text,
            "red_flags": red_flags,
            "suggestions": [] if consistency > 0.6 else ["建议完善个人简介以反映真实性格"],
            "sample_size": len(messages),
        }

    def _infer_personality_from_text(self, text: str) -> Dict[str, float]:
        """从文本推断性格倾向"""
        text_lower = text.lower()
        scores = {}

        for personality_type, keywords in self.PERSONALITY_KEYWORDS.items():
            score = 0
            for keyword in keywords["positive"]:
                if keyword in text_lower:
                    score += 1
            for keyword in keywords["negative"]:
                if keyword in text_lower:
                    score -= 0.5
            scores[personality_type] = max(0, score)

        # 归一化
        total = sum(scores.values()) if sum(scores.values()) > 0 else 1
        return {k: v/total for k, v in scores.items()}

    def _calculate_personality_match(
        self,
        claimed: Dict[str, float],
        inferred: Dict[str, float]
    ) -> float:
        """计算性格匹配度"""
        if not claimed or not inferred:
            return 0.5

        # 比较主要性格倾向
        claimed_main = max(claimed, key=claimed.get) if claimed else None
        inferred_main = max(inferred, key=inferred.get) if inferred else None

        # 相反性格对
        opposite_pairs = [("introvert", "outgoing"), ("serious", "playful")]

        for pair in opposite_pairs:
            if claimed_main in pair and inferred_main in pair:
                if claimed_main == inferred_main:
                    return 0.8  # 一致
                else:
                    return 0.3  # 矛盾

        return 0.6  # 默认中等一致性

    def _detect_red_flags(self, bio: str, chat: str) -> List[str]:
        """检测红旗警告"""
        red_flags = []

        # 检查简介说"内向"但聊天很活跃
        if "内向" in bio.lower() or "安静" in bio.lower():
            # 检查聊天活跃度
            chat_lines = chat.split("\n") if chat else []
            if len(chat_lines) > 20:  # 聊天内容很多
                red_flags.append("简介说内向但聊天内容丰富活跃")

        # 检查简介说"幽默"但聊天严肃
        if "幽默" in bio.lower() or "有趣" in bio.lower():
            # 检查聊天是否有表情或轻松内容
            emoji_count = sum(1 for c in chat if ord(c) > 127 and ord(c) < 128000)
            if emoji_count < 3:  # 表情很少
                red_flags.append("简介说幽默但聊天风格严肃")

        return red_flags


# ============================================
# 年龄语言推断器
# ============================================

class AgeLanguageInferrer:
    """从聊天风格推断用户年龄段"""

    # 年龄段语言特征
    AGE_LANGUAGE_PATTERNS = {
        "young": {  # 18-25岁
            "slang": ["yyds", "绝绝子", "笑死", "破防", "宝藏", "神仙", "真的会谢", "家人们",
                      "无语", "吐槽", "磕", "入坑", "出坑", "绝了", "太爱了", "冲"],
            "topics": ["毕业", "找工作", "考研", "大学", "宿舍", "室友", "校园", "实习", "offer"],
            "emoji_rate": 0.25,  # 高表情使用率
            "age_range": (18, 25),
        },
        "young_adult": {  # 25-35岁
            "slang": ["内卷", "躺平", "996", "加班", "跳槽", "晋升", "理财", "买房", "房贷",
                      "职场", "项目", "deadline", "kpi"],
            "topics": ["工作", "同事", "领导", "项目", "客户", "房贷", "结婚", "相亲", "婚礼"],
            "emoji_rate": 0.12,
            "age_range": (25, 35),
        },
        "middle": {  # 35-45岁
            "slang": ["孩子", "学区房", "补习", "教育", "家长", "接送", "辅导"],
            "topics": ["孩子", "家庭", "学校", "父母", "健康", "体检", "养生", "中年", "压力"],
            "emoji_rate": 0.06,
            "age_range": (35, 45),
        },
        "senior": {  # 45-60岁
            "slang": ["退休", "养老金", "社保", "医保"],
            "topics": ["退休", "旅游", "子女", "健康", "老友", "回忆", "养生", "保健品", "孙辈"],
            "emoji_rate": 0.03,
            "age_range": (45, 60),
        },
    }

    def infer_age_bracket(
        self,
        user: UserDB,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        从聊天内容推断年龄段

        Returns:
            {
                "inferred_bracket": "young"/"young_adult"/"middle"/"senior",
                "inferred_range": (min_age, max_age),
                "confidence": 0-1,
                "evidence": [...],
                "claimed_age": N,
                "match": True/False
            }
        """
        # 获取聊天记录
        messages = db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user.id,
            ChatMessageDB.message_type == "text",
            ChatMessageDB.created_at >= datetime.now() - timedelta(days=days)
        ).order_by(ChatMessageDB.created_at.desc()).limit(100).all()

        if len(messages) < 10:
            return {
                "inferred_bracket": "unknown",
                "confidence": 0,
                "note": "聊天样本不足",
            }

        # 合并聊天文本
        chat_text = " ".join([m.content for m in messages if m.content])
        chat_text_lower = chat_text.lower()

        # 分析各年龄段特征得分
        bracket_scores = {}
        evidence_by_bracket = {}

        for bracket, patterns in self.AGE_LANGUAGE_PATTERNS.items():
            score = 0
            evidence = []

            # 检查网络用语/俚语
            for slang in patterns["slang"]:
                if slang in chat_text_lower:
                    score += 2
                    evidence.append(f"使用俚语 '{slang}'")

            # 检查话题
            for topic in patterns["topics"]:
                if topic in chat_text_lower:
                    score += 1
                    evidence.append(f"提及话题 '{topic}'")

            # 检查表情使用率（粗略估算）
            emoji_count = sum(1 for c in chat_text if ord(c) > 127 and ord(c) < 128000)
            text_length = len(chat_text)
            actual_emoji_rate = emoji_count / text_length if text_length > 0 else 0
            expected_rate = patterns["emoji_rate"]

            # 表情使用率接近预期 → 加分
            if abs(actual_emoji_rate - expected_rate) < 0.1:
                score += 1
                evidence.append(f"表情使用率 {actual_emoji_rate:.2%} 符合年龄段特征")

            bracket_scores[bracket] = score
            evidence_by_bracket[bracket] = evidence

        # 找出得分最高的年龄段
        if not bracket_scores or max(bracket_scores.values()) == 0:
            return {
                "inferred_bracket": "unknown",
                "confidence": 0,
                "note": "聊天内容无明显年龄特征",
            }

        inferred_bracket = max(bracket_scores, key=bracket_scores.get)
        inferred_range = self.AGE_LANGUAGE_PATTERNS[inferred_bracket]["age_range"]

        # 计算置信度（基于得分差距）
        max_score = bracket_scores[inferred_bracket]
        second_score = sorted(bracket_scores.values())[-2] if len(bracket_scores) > 1 else 0
        confidence = min(0.9, max_score / (max_score + second_score + 1))

        # 对比声称年龄
        claimed_age = user.age
        min_age, max_age = inferred_range

        # 允许误差
        tolerance = 5
        match = claimed_age >= min_age - tolerance and claimed_age <= max_age + tolerance

        return {
            "inferred_bracket": inferred_bracket,
            "inferred_range": inferred_range,
            "confidence": confidence,
            "evidence": evidence_by_bracket[inferred_bracket],
            "claimed_age": claimed_age,
            "match": match,
            "bracket_scores": bracket_scores,
        }


# ============================================
# 价值观深度推断器
# ============================================

class ValueInferrer:
    """从行为和聊天推断用户深层价值观"""

    # 价值观维度
    VALUE_DIMENSIONS = {
        "family": {
            "keywords": ["家庭", "家人", "孩子", "父母", "孝顺", "亲情", "传统"],
            "browse_targets": ["looking_for_family_oriented"],
            "weight": 0.2,
        },
        "career": {
            "keywords": ["事业", "工作", "奋斗", "上进", "成功", "拼搏", "职业发展"],
            "browse_targets": ["looking_for_successful", "high_income"],
            "weight": 0.15,
        },
        "relationship": {
            "keywords": ["爱情", "伴侣", "婚姻", "感情", "真心", "浪漫", "陪伴"],
            "browse_targets": ["looking_for_love", "relationship_focused"],
            "weight": 0.25,
        },
        "freedom": {
            "keywords": ["自由", "独立", "旅行", "探索", "无拘束", "随性", "冒险"],
            "browse_targets": ["looking_for_independent"],
            "weight": 0.15,
        },
        "stability": {
            "keywords": ["稳定", "安稳", "踏实", "平静", "安逸", "舒适"],
            "browse_targets": ["looking_for_stable"],
            "weight": 0.15,
        },
        "growth": {
            "keywords": ["成长", "进步", "学习", "提升", "改变", "突破"],
            "browse_targets": ["looking_for_growth_oriented"],
            "weight": 0.1,
        },
    }

    async def infer_values(
        self,
        user: UserDB,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        推断用户深层价值观

        Returns:
            {
                "values": {"family": 0.7, "career": 0.5, ...},
                "overall_consistency": 0-1,
                "browse_pattern_analysis": {...},
                "chat_pattern_analysis": {...}
            }
        """
        # 1. 从聊天内容分析价值观关键词
        chat_values = self._analyze_values_from_chat(user, db, days)

        # 2. 从浏览行为分析价值观倾向
        browse_values = self._analyze_values_from_browse(user, db, days)

        # 3. 从用户画像推断价值观
        profile_values = self._analyze_values_from_profile(user)

        # 4. 综合推断
        final_values = {}
        for dim in self.VALUE_DIMENSIONS:
            weights = self.VALUE_DIMENSIONS[dim]["weight"]
            chat_score = chat_values.get(dim, 0.5)
            browse_score = browse_values.get(dim, 0.5)
            profile_score = profile_values.get(dim, 0.5)

            # 加权平均（聊天权重最高）
            final_values[dim] = (chat_score * 0.4 + browse_score * 0.3 + profile_score * 0.3)

        # 5. 计算与声称价值观的一致性
        claimed_values = self._get_claimed_values(user)
        consistency = self._calculate_value_consistency(final_values, claimed_values)

        return {
            "values": final_values,
            "claimed_values": claimed_values,
            "overall_consistency": consistency,
            "chat_pattern_analysis": chat_values,
            "browse_pattern_analysis": browse_values,
            "profile_analysis": profile_values,
            "dominant_values": sorted(final_values, key=final_values.get, reverse=True)[:3],
        }

    def _analyze_values_from_chat(self, user: UserDB, db: Session, days: int) -> Dict[str, float]:
        """从聊天内容分析价值观"""
        messages = db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user.id,
            ChatMessageDB.created_at >= datetime.now() - timedelta(days=days)
        ).limit(50).all()

        chat_text = " ".join([m.content for m in messages if m.content]).lower()

        scores = {}
        for dim, config in self.VALUE_DIMENSIONS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in chat_text:
                    score += 1
            # 归一化到 0-1
            scores[dim] = min(1, score / 3)

        return scores

    def _analyze_values_from_browse(self, user: UserDB, db: Session, days: int) -> Dict[str, float]:
        """从浏览行为分析价值观倾向"""
        # 获取用户浏览的用户类型统计
        browse_events = db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user.id,
            BehaviorEventDB.event_type == "profile_view",
            BehaviorEventDB.created_at >= datetime.now() - timedelta(days=days)
        ).limit(50).all()

        # 分析被浏览用户的特征
        # 简化实现：假设浏览了"高收入"用户 → 倾向"career"价值观
        # 浏览了"家庭导向"用户 → 倾向"family"价值观

        # 这里简化返回默认值，实际需要分析被浏览用户画像
        return {"family": 0.5, "career": 0.5, "relationship": 0.6, "freedom": 0.4, "stability": 0.5, "growth": 0.5}

    def _analyze_values_from_profile(self, user: UserDB) -> Dict[str, float]:
        """从用户画像推断价值观"""
        # 分析用户填写的信息
        scores = {}

        # 从 bio 分析
        bio = (user.bio or "").lower()
        for dim, config in self.VALUE_DIMENSIONS.items():
            for keyword in config["keywords"]:
                if keyword in bio:
                    scores[dim] = scores.get(dim, 0.5) + 0.2

        # 从兴趣分析
        try:
            interests = json.loads(user.interests or "[]")
        except:
            interests = []

        # 兴趣映射到价值观
        interest_value_map = {
            "旅行": "freedom",
            "阅读": "growth",
            "运动": "growth",
            "投资": "career",
            "家庭": "family",
            "孩子": "family",
        }

        for interest in interests:
            dim = interest_value_map.get(interest)
            if dim:
                scores[dim] = scores.get(dim, 0.5) + 0.15

        # 确保所有维度都有值
        for dim in self.VALUE_DIMENSIONS:
            scores[dim] = scores.get(dim, 0.5)

        return scores

    def _get_claimed_values(self, user: UserDB) -> Dict[str, float]:
        """获取用户声称的价值观"""
        # 从用户填写的价值观字段获取
        try:
            values = json.loads(user.values or "{}")
        except:
            values = {}

        # 如果没有填写，返回空
        return values

    def _calculate_value_consistency(
        self,
        inferred: Dict[str, float],
        claimed: Dict[str, float]
    ) -> float:
        """计算推断价值观与声称价值观的一致性"""
        if not claimed:
            return 0.5  # 未声称，默认中等一致性

        # 对比主要价值观倾向
        inferred_main = sorted(inferred, key=inferred.get, reverse=True)[:3]
        claimed_main = sorted(claimed, key=claimed.get, reverse=True)[:3] if claimed else []

        # 计算交集
        common = set(inferred_main) & set(claimed_main)
        consistency = len(common) / 3 if inferred_main else 0.5

        return consistency


# ============================================
# 综合LLM分析服务
# ============================================

class LLMConfidenceAnalyzer:
    """综合LLM置信度分析服务"""

    def __init__(self):
        self.text_analyzer = TextConsistencyAnalyzer()
        self.age_inferrer = AgeLanguageInferrer()
        self.value_inferrer = ValueInferrer()

    async def analyze_user_confidence_deep(
        self,
        user: UserDB,
        db: Session
    ) -> Dict[str, Any]:
        """
        执行完整的LLM深度分析

        Returns:
            {
                "text_consistency": {...},
                "age_inference": {...},
                "value_inference": {...},
                "overall_llm_confidence": 0-1,
                "red_flags": [...],
                "recommendations": [...]
            }
        """
        results = {}
        red_flags = []

        # 1. 文本一致性分析
        try:
            text_result = await self.text_analyzer.analyze_bio_chat_consistency(user, db)
            results["text_consistency"] = text_result
            if text_result.get("bio_chat_consistency") < 0.4:
                red_flags.extend(text_result.get("red_flags", []))
        except Exception as e:
            logger.warning(f"文本一致性分析失败: {e}")
            results["text_consistency"] = {"error": str(e)}

        # 2. 年龄语言推断
        try:
            age_result = self.age_inferrer.infer_age_bracket(user, db)
            results["age_inference"] = age_result
            if not age_result.get("match"):
                red_flags.append(f"聊天风格推断年龄段与声称年龄不一致")
        except Exception as e:
            logger.warning(f"年龄推断失败: {e}")
            results["age_inference"] = {"error": str(e)}

        # 3. 价值观推断
        try:
            value_result = await self.value_inferrer.infer_values(user, db)
            results["value_inference"] = value_result
            if value_result.get("overall_consistency") < 0.5:
                red_flags.append("价值观描述与实际行为不一致")
        except Exception as e:
            logger.warning(f"价值观推断失败: {e}")
            results["value_inference"] = {"error": str(e)}

        # 4. 计算综合LLM置信度
        scores = []
        if results.get("text_consistency", {}).get("bio_chat_consistency"):
            scores.append(results["text_consistency"]["bio_chat_consistency"])
        if results.get("value_inference", {}).get("overall_consistency"):
            scores.append(results["value_inference"]["overall_consistency"])

        overall_llm_confidence = sum(scores) / len(scores) if scores else 0.6

        # 5. 生成建议
        recommendations = []
        if results.get("text_consistency", {}).get("bio_chat_consistency") < 0.6:
            recommendations.append("建议完善个人简介，使其更真实反映您的性格")
        if results.get("age_inference", {}).get("match") == False:
            recommendations.append("年龄信息可能与您的实际状态不符，建议核实")
        if results.get("value_inference", {}).get("overall_consistency") < 0.5:
            recommendations.append("价值观描述可以更准确地反映您的实际追求")

        return {
            "text_consistency": results.get("text_consistency", {}),
            "age_inference": results.get("age_inference", {}),
            "value_inference": results.get("value_inference", {}),
            "overall_llm_confidence": overall_llm_confidence,
            "red_flags": red_flags,
            "recommendations": recommendations,
        }


# ============================================
# 导出
# ============================================

# 全局服务实例
text_analyzer = TextConsistencyAnalyzer()
age_inferrer = AgeLanguageInferrer()
value_inferrer = ValueInferrer()
llm_confidence_analyzer = LLMConfidenceAnalyzer()