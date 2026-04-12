"""
数字潜意识分析 Skill

Identity 功能：分析用户数字潜意识，包括依恋风格、潜意识特质、行为模式等
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class SubconsciousAnalyzerSkill:
    """
    数字潜意识分析 Skill

    核心能力:
    - 依恋风格分析
    - 潜意识特质识别
    - 行为模式解读
    - 深层性格画像
    - 匹配建议生成

    自主触发条件:
    - 用户完成心理测试后
    - 关系进入深度阶段
    - 用户主动探索自我
    """

    name = "subconscious_analyzer"
    version = "1.0.0"
    description = """
    数字潜意识分析专家

    能力:
    - 依恋风格分析 (安全型/焦虑型/回避型/混乱型)
    - 潜意识特质识别 (12 维度)
    - 行为模式深度解读
    - 深层性格画像生成
    - 基于潜意识的匹配建议
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["basic", "deep", "comprehensive"],
                    "description": "分析深度"
                },
                "focus_area": {
                    "type": "string",
                    "enum": ["attachment", "traits", "patterns", "all"],
                    "description": "聚焦分析领域"
                },
                "with_suggestions": {
                    "type": "boolean",
                    "description": "是否包含建议"
                }
            },
            "required": ["user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "attachment_style": {"type": "object"},
                "subconscious_traits": {"type": "array"},
                "behavior_patterns": {"type": "array"},
                "personality_profile": {"type": "object"},
                "suggestions": {"type": "array"}
            }
        }

    async def execute(
        self,
        user_id: str,
        analysis_depth: str = "basic",
        focus_area: str = "all",
        with_suggestions: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行潜意识分析

        Args:
            user_id: 用户 ID
            analysis_depth: 分析深度
            focus_area: 聚焦领域
            with_suggestions: 是否包含建议

        Returns:
            分析结果
        """
        logger.info(f"SubconsciousAnalyzer: Analyzing user={user_id}, depth={analysis_depth}")

        try:
            # 获取潜意识档案
            profile = self._get_subconscious_profile(user_id)

            # 获取依恋风格
            attachment = self._analyze_attachment_style(user_id, profile)

            # 获取潜意识特质
            traits = self._analyze_subconscious_traits(user_id, profile)

            # 获取行为模式
            patterns = self._analyze_behavior_patterns(user_id)

            # 根据分析深度构建响应
            if analysis_depth == "basic":
                return self._build_basic_response(attachment, traits)
            elif analysis_depth == "deep":
                return self._build_deep_response(attachment, traits, patterns)
            else:  # comprehensive
                suggestions = self._generate_suggestions(attachment, traits, patterns) if with_suggestions else []
                return self._build_comprehensive_response(
                    attachment, traits, patterns, suggestions
                )

        except Exception as e:
            logger.error(f"SubconsciousAnalyzer execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "潜意识分析失败，请稍后再试"
            }

    def _get_subconscious_profile(self, user_id: str) -> Optional[Dict]:
        """获取潜意识档案"""
        from utils.db_session_manager import db_session
        from models.perception_models import DigitalSubconsciousProfileDB

        with db_session() as db:
            profile = db.query(DigitalSubconsciousProfileDB).filter(
                DigitalSubconsciousProfileDB.user_id == user_id
            ).first()

            if profile:
                return {
                    "id": profile.id,
                    "user_id": profile.user_id,
                    "attachment_style": profile.attachment_style,
                    "attachment_score": profile.attachment_score,
                    "subconscious_traits": profile.subconscious_traits,
                    "confidence_scores": profile.confidence_scores,
                    "last_updated": profile.updated_at.isoformat() if profile.updated_at else None,
                }
            return None

    def _analyze_attachment_style(
        self,
        user_id: str,
        profile: Optional[Dict]
    ) -> Dict:
        """分析依恋风格"""
        from services.perception_layer_service import perception_layer_service

        if profile and profile.get("attachment_style"):
            style = profile["attachment_style"]
            score = profile.get("attachment_score", 0.5)
        else:
            # 动态分析
            result = perception_layer_service.analyze_attachment_style(user_id)
            style = result.get("attachment_style", "unknown")
            score = result.get("confidence", 0.5)

        # 获取依恋风格描述
        style_descriptions = {
            "secure": {
                "name": "安全型",
                "description": "能够建立健康、稳定的亲密关系",
                "strengths": ["信任他人", "情感表达自然", "独立且亲密"],
                "growth_areas": ["继续保持开放的沟通"],
            },
            "anxious": {
                "name": "焦虑型",
                "description": "渴望亲密但担心被抛弃",
                "strengths": ["情感丰富", "重视关系", "敏感体贴"],
                "growth_areas": ["建立自我价值感", "学习自我安抚"],
            },
            "avoidant": {
                "name": "回避型",
                "description": "倾向独立，避免过度亲密",
                "strengths": ["独立自主", "理性冷静", "个人边界清晰"],
                "growth_areas": ["学习表达情感", "适度依赖他人"],
            },
            "disorganized": {
                "name": "混乱型",
                "description": "对亲密关系既渴望又恐惧",
                "strengths": ["自我觉察潜力大", "情感深刻"],
                "growth_areas": ["建立安全感", "寻求专业支持"],
            },
        }

        info = style_descriptions.get(style, style_descriptions["secure"])

        return {
            "style": style,
            "name": info["name"],
            "description": info["description"],
            "confidence": score,
            "strengths": info["strengths"],
            "growth_areas": info["growth_areas"],
        }

    def _analyze_subconscious_traits(
        self,
        user_id: str,
        profile: Optional[Dict]
    ) -> List[Dict]:
        """分析潜意识特质"""
        traits = []

        if profile and profile.get("subconscious_traits"):
            for trait_name, score in profile["subconscious_traits"].items():
                traits.append({
                    "name": self._get_trait_name(trait_name),
                    "key": trait_name,
                    "score": score,
                    "level": self._get_trait_level(score),
                    "description": self._get_trait_description(trait_name, score),
                })
        else:
            # 使用默认特质
            default_traits = ["openness", "authenticity", "vulnerability", "intimacy_comfort"]
            for trait in default_traits:
                traits.append({
                    "name": self._get_trait_name(trait),
                    "key": trait,
                    "score": 0.5,
                    "level": "medium",
                    "description": "暂无足够数据进行深度分析",
                })

        # 按分数排序
        traits.sort(key=lambda x: x["score"], reverse=True)
        return traits[:8]  # 返回前 8 个特质

    def _analyze_behavior_patterns(self, user_id: str) -> List[Dict]:
        """分析行为模式"""
        from utils.db_session_manager import db_session
        from models.l4_learning_models import BehaviorLearningPattern

        with db_session() as db:
            patterns = db.query(BehaviorLearningPattern).filter(
                BehaviorLearningPattern.user_id == user_id,
                BehaviorLearningPattern.is_validated == True,
            ).limit(5).all()

            result = []
            for p in patterns:
                result.append({
                    "type": p.pattern_type,
                    "name": self._get_pattern_name(p.pattern_type),
                    "data": p.pattern_data,
                    "strength": p.pattern_strength,
                    "description": self._get_pattern_description(p.pattern_type, p.pattern_data),
                })

            return result

    def _generate_suggestions(
        self,
        attachment: Dict,
        traits: List[Dict],
        patterns: List[Dict]
    ) -> List[Dict]:
        """生成成长建议"""
        suggestions = []

        # 基于依恋风格的建议
        for area in attachment.get("growth_areas", []):
            suggestions.append({
                "category": "attachment",
                "priority": "high",
                "message": f"依恋风格成长：{area}",
                "action": "attachment_growth",
            })

        # 基于低分特质的建议
        low_traits = [t for t in traits if t["score"] < 0.4]
        for trait in low_traits:
            suggestions.append({
                "category": "trait",
                "priority": "medium",
                "message": f"培养{trait['name']}：尝试相关练习",
                "action": "trait_development",
                "trait": trait["key"],
            })

        # 基于行为模式的建议
        for pattern in patterns:
            if pattern["strength"] > 0.7:
                suggestions.append({
                    "category": "pattern",
                    "priority": "low",
                    "message": f"保持良好模式：{pattern['name']}",
                    "action": "pattern_reinforce",
                })

        return suggestions[:5]

    def _build_basic_response(
        self,
        attachment: Dict,
        traits: List[Dict]
    ) -> Dict[str, Any]:
        """构建基础响应"""
        ai_message = f"您的依恋风格是{attachment['name']}。"
        if traits:
            top_trait = traits[0]
            ai_message += f"最突出的特质是{top_trait['name']}。"

        return {
            "success": True,
            "data": {
                "attachment_style": attachment,
                "top_traits": traits[:3],
            },
            "ai_message": ai_message,
        }

    def _build_deep_response(
        self,
        attachment: Dict,
        traits: List[Dict],
        patterns: List[Dict]
    ) -> Dict[str, Any]:
        """构建深度响应"""
        ai_message = self._generate_ai_message(attachment, traits, patterns)

        return {
            "success": True,
            "data": {
                "attachment_style": attachment,
                "subconscious_traits": traits,
                "behavior_patterns": patterns,
            },
            "ai_message": ai_message,
        }

    def _build_comprehensive_response(
        self,
        attachment: Dict,
        traits: List[Dict],
        patterns: List[Dict],
        suggestions: List[Dict]
    ) -> Dict[str, Any]:
        """构建全面响应"""
        ai_message = self._generate_ai_message(attachment, traits, patterns)
        if suggestions:
            ai_message += f"\n\n为您生成{len(suggestions)}条成长建议~"

        return {
            "success": True,
            "data": {
                "attachment_style": attachment,
                "subconscious_traits": traits,
                "behavior_patterns": patterns,
                "suggestions": suggestions,
            },
            "ai_message": ai_message,
        }

    def _generate_ai_message(
        self,
        attachment: Dict,
        traits: List[Dict],
        patterns: List[Dict]
    ) -> str:
        """生成 AI 消息"""
        lines = ["潜意识分析结果：", ""]

        # 依恋风格
        lines.append(f"🧠 依恋风格：{attachment['name']}")
        lines.append(f"   {attachment['description']}")
        lines.append("")

        # 核心特质
        if traits:
            lines.append("✨ 核心特质：")
            for t in traits[:3]:
                lines.append(f"   • {t['name']} ({t['level']})")
            lines.append("")

        # 行为模式
        if patterns:
            lines.append("🔄 行为模式：")
            for p in patterns[:2]:
                lines.append(f"   • {p['name']}")

        return "\n".join(lines)

    # ========== 辅助函数 ==========

    def _get_trait_name(self, key: str) -> str:
        """获取特质名称"""
        names = {
            "openness": "开放性",
            "authenticity": "真实性",
            "vulnerability": "脆弱接纳",
            "intimacy_comfort": "亲密舒适度",
            "emotional_awareness": "情感觉察",
            "trust_tendency": "信任倾向",
            "independence": "独立性",
            "empathy": "共情能力",
        }
        return names.get(key, key)

    def _get_trait_level(self, score: float) -> str:
        """获取特质等级"""
        if score >= 0.8:
            return "很高"
        elif score >= 0.6:
            return "较高"
        elif score >= 0.4:
            return "中等"
        elif score >= 0.2:
            return "较低"
        else:
            return "很低"

    def _get_trait_description(self, key: str, score: float) -> str:
        """获取特质描述"""
        descriptions = {
            "openness": "对新体验和新想法的开放程度",
            "authenticity": "展现真实自我的能力",
            "vulnerability": "接纳和表达脆弱的能力",
            "intimacy_comfort": "在亲密关系中的舒适度",
        }
        base = descriptions.get(key, "该特质的描述")
        level = self._get_trait_level(score)
        return f"{base}。当前水平：{level}"

    def _get_pattern_name(self, pattern_type: str) -> str:
        """获取模式名称"""
        names = {
            "online_time": "活跃时间模式",
            "response_style": "回复风格模式",
            "matching_preference": "匹配偏好模式",
            "communication_habit": "沟通习惯模式",
            "dating_preference": "约会偏好模式",
        }
        return names.get(pattern_type, pattern_type)

    def _get_pattern_description(self, pattern_type: str, data: Dict) -> str:
        """获取模式描述"""
        return f"基于{len(data)}个维度的行为数据分析"


# 全局单例获取函数
_skill_instance: Optional[SubconsciousAnalyzerSkill] = None


def get_subconscious_analyzer_skill() -> SubconsciousAnalyzerSkill:
    """获取数字潜意识分析 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = SubconsciousAnalyzerSkill()
    return _skill_instance
