"""
冲突兼容性分析 Skill

Values 功能：分析双方冲突处理风格的兼容性，预测潜在冲突并生成建议
"""
from typing import Dict, Any, Optional, List
from agent.skills.base import BaseSkill
from utils.logger import logger


class ConflictCompatibilityAnalyzerSkill:
    """
    冲突兼容性分析 Skill

    核心能力:
    - 冲突风格评估
    - 双方兼容性分析
    - 冲突模式预测
    - 调解建议生成
    - 关系风险评估

    自主触发条件:
    - 新匹配产生时
    - 关系进入深度阶段
    - 检测到潜在冲突
    """

    name = "conflict_compatibility_analyzer"
    version = "1.0.0"
    description = """
    冲突兼容性分析专家

    能力:
    - 冲突处理风格评估 (5 种风格)
    - 双方兼容性矩阵分析 (25 种组合)
    - 潜在冲突模式预测
    - 个性化冲突调解建议
    - 关系风险评估与预警
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_a_id": {
                    "type": "string",
                    "description": "用户 A ID"
                },
                "user_b_id": {
                    "type": "string",
                    "description": "用户 B ID"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["compatibility", "prediction", "suggestions", "full"],
                    "description": "分析类型"
                },
                "include_history": {
                    "type": "boolean",
                    "description": "是否包含历史冲突分析"
                }
            },
            "required": ["user_a_id", "user_b_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_a_style": {"type": "object"},
                "user_b_style": {"type": "object"},
                "compatibility_score": {"type": "number"},
                "compatibility_level": {"type": "string"},
                "potential_conflicts": {"type": "array"},
                "suggestions": {"type": "array"}
            }
        }

    async def execute(
        self,
        user_a_id: str,
        user_b_id: str,
        analysis_type: str = "full",
        include_history: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行冲突兼容性分析

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            analysis_type: 分析类型
            include_history: 是否包含历史

        Returns:
            分析结果
        """
        logger.info(f"ConflictCompatibilityAnalyzer: Analyzing {user_a_id} vs {user_b_id}")

        try:
            # 获取双方冲突风格
            user_a_style = self._get_conflict_style(user_a_id)
            user_b_style = self._get_conflict_style(user_b_id)

            # 计算兼容性
            compatibility = self._calculate_compatibility(user_a_style, user_b_style)

            # 预测潜在冲突
            potential_conflicts = self._predict_conflicts(user_a_style, user_b_style)

            # 生成建议
            suggestions = self._generate_suggestions(
                user_a_style, user_b_style, compatibility, potential_conflicts
            )

            # 根据分析类型返回
            if analysis_type == "compatibility":
                return self._build_compatibility_response(compatibility)
            elif analysis_type == "prediction":
                return self._build_prediction_response(potential_conflicts)
            elif analysis_type == "suggestions":
                return self._build_suggestions_response(suggestions)
            else:  # full
                return self._build_full_response(
                    user_a_style, user_b_style, compatibility,
                    potential_conflicts, suggestions, include_history
                )

        except Exception as e:
            logger.error(f"ConflictCompatibilityAnalyzer execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "冲突兼容性分析失败，请稍后再试"
            }

    def _get_conflict_style(self, user_id: str) -> Dict:
        """获取用户冲突风格"""
        from utils.db_session_manager import db_session
        from models.conflict_models import ConflictStyleDB

        with db_session() as db:
            style = db.query(ConflictStyleDB).filter(
                ConflictStyleDB.user_id == user_id
            ).order_by(ConflictStyleDB.created_at.desc()).first()

            if style:
                return {
                    "primary_style": style.primary_style,
                    "secondary_style": style.secondary_style,
                    "style_scores": style.style_scores,
                    "assessment_date": style.assessed_at.isoformat() if style.assessed_at else None,
                }
            else:
                # 返回默认风格
                return {
                    "primary_style": "unknown",
                    "secondary_style": None,
                    "style_scores": {},
                    "assessment_date": None,
                }

    def _calculate_compatibility(
        self,
        user_a_style: Dict,
        user_b_style: Dict
    ) -> Dict:
        """计算兼容性"""
        style_a = user_a_style.get("primary_style", "unknown")
        style_b = user_b_style.get("primary_style", "unknown")

        # 兼容性矩阵
        COMPATIBILITY_MATRIX = {
            ("avoiding", "avoiding"): 0.4,
            ("avoiding", "competing"): 0.3,
            ("avoiding", "accommodating"): 0.6,
            ("avoiding", "compromising"): 0.5,
            ("avoiding", "collaborating"): 0.7,
            ("competing", "avoiding"): 0.3,
            ("competing", "competing"): 0.2,
            ("competing", "accommodating"): 0.6,
            ("competing", "compromising"): 0.4,
            ("competing", "collaborating"): 0.3,
            ("accommodating", "avoiding"): 0.6,
            ("accommodating", "competing"): 0.6,
            ("accommodating", "accommodating"): 0.7,
            ("accommodating", "compromising"): 0.6,
            ("accommodating", "collaborating"): 0.8,
            ("compromising", "avoiding"): 0.5,
            ("compromising", "competing"): 0.4,
            ("compromising", "accommodating"): 0.6,
            ("compromising", "compromising"): 0.7,
            ("compromising", "collaborating"): 0.7,
            ("collaborating", "avoiding"): 0.7,
            ("collaborating", "competing"): 0.3,
            ("collaborating", "accommodating"): 0.8,
            ("collaborating", "compromising"): 0.7,
            ("collaborating", "collaborating"): 0.9,
        }

        # 获取兼容性分数
        base_score = COMPATIBILITY_MATRIX.get((style_a, style_b), 0.5)

        # 考虑次要风格的影响
        secondary_a = user_a_style.get("secondary_style")
        secondary_b = user_b_style.get("secondary_style")
        if secondary_a and secondary_b:
            secondary_score = COMPATIBILITY_MATRIX.get((secondary_a, secondary_b), 0.5)
            final_score = (base_score * 0.7) + (secondary_score * 0.3)
        else:
            final_score = base_score

        return {
            "score": round(final_score, 2),
            "level": self._get_compatibility_level(final_score),
            "style_pair": f"{style_a} + {style_b}",
            "description": self._get_compatibility_description(style_a, style_b, final_score),
        }

    def _predict_conflicts(
        self,
        user_a_style: Dict,
        user_b_style: Dict
    ) -> List[Dict]:
        """预测潜在冲突"""
        style_a = user_a_style.get("primary_style", "unknown")
        style_b = user_b_style.get("primary_style", "unknown")

        conflicts = []

        # 基于风格组合的冲突预测
        if style_a == "competing" and style_b == "competing":
            conflicts.append({
                "type": "power_struggle",
                "description": "双方都倾向于主导，容易发生权力争夺",
                "trigger_scenarios": ["做决定时", "意见不合时", "规划未来时"],
                "severity": "high",
            })

        if style_a == "avoiding" and style_b == "avoiding":
            conflicts.append({
                "type": "communication_gap",
                "description": "双方都回避冲突，问题可能累积",
                "trigger_scenarios": ["敏感话题", "关系问题", "不满情绪"],
                "severity": "medium",
            })

        if (style_a == "competing" and style_b == "avoiding") or \
           (style_a == "avoiding" and style_b == "competing"):
            conflicts.append({
                "type": "pursuer_distancer",
                "description": "一方追逐一方逃避的模式",
                "trigger_scenarios": ["需要沟通时", "解决问题时"],
                "severity": "high",
            })

        if style_a == "accommodating" and style_b == "competing":
            conflicts.append({
                "type": "imbalance",
                "description": "一方过度迁就可能导致关系失衡",
                "trigger_scenarios": ["长期决策", "资源分配"],
                "severity": "medium",
            })

        # 通用冲突
        conflicts.append({
            "type": "communication_style_mismatch",
            "description": "沟通风格差异可能导致误解",
            "trigger_scenarios": ["日常交流", "情感表达"],
            "severity": "low",
        })

        return conflicts

    def _generate_suggestions(
        self,
        user_a_style: Dict,
        user_b_style: Dict,
        compatibility: Dict,
        potential_conflicts: List[Dict]
    ) -> List[Dict]:
        """生成建议"""
        suggestions = []

        # 基于兼容性分数的建议
        score = compatibility["score"]
        if score < 0.4:
            suggestions.append({
                "category": "awareness",
                "priority": "high",
                "message": "你们的冲突处理风格差异较大，需要更多理解和包容",
                "action": "style_awareness",
            })
        elif score < 0.6:
            suggestions.append({
                "category": "communication",
                "priority": "medium",
                "message": "建议学习对方的冲突处理方式，找到平衡点",
                "action": "learn_style",
            })
        else:
            suggestions.append({
                "category": "strength",
                "priority": "low",
                "message": "你们的冲突处理方式较为兼容，继续保持良好沟通",
                "action": "maintain",
            })

        # 基于冲突类型的建议
        for conflict in potential_conflicts[:2]:
            suggestions.append({
                "category": "conflict_prevention",
                "priority": "medium",
                "message": f"预防{conflict['type']}：{conflict['description']}",
                "tips": self._get_prevention_tips(conflict["type"]),
            })

        # 风格特定建议
        style_a = user_a_style.get("primary_style")
        style_b = user_b_style.get("primary_style")

        if style_a == "avoiding":
            suggestions.append({
                "category": "personal_growth",
                "priority": "medium",
                "message": "尝试更直接地表达自己的需求和感受",
                "action": "express_more",
            })

        if style_b == "competing":
            suggestions.append({
                "category": "personal_growth",
                "priority": "medium",
                "message": "学习倾听和妥协，考虑对方的感受",
                "action": "listen_more",
            })

        return suggestions[:5]

    def _build_full_response(
        self,
        user_a_style: Dict,
        user_b_style: Dict,
        compatibility: Dict,
        potential_conflicts: List[Dict],
        suggestions: List[Dict],
        include_history: bool
    ) -> Dict[str, Any]:
        """构建完整响应"""
        ai_message = self._generate_ai_message(
            user_a_style, user_b_style, compatibility, potential_conflicts
        )
        if suggestions:
            ai_message += f"\n\n{len(suggestions)}条建议供参考~"

        data = {
            "user_a_style": user_a_style,
            "user_b_style": user_b_style,
            "compatibility_score": compatibility["score"],
            "compatibility_level": compatibility["level"],
            "compatibility_description": compatibility["description"],
            "potential_conflicts": potential_conflicts,
            "suggestions": suggestions,
        }

        if include_history:
            data["conflict_history"] = self._get_conflict_history(
                user_a_style, user_b_style
            )

        return {
            "success": True,
            "data": data,
            "ai_message": ai_message,
        }

    def _build_compatibility_response(self, compatibility: Dict) -> Dict[str, Any]:
        """构建兼容性响应"""
        return {
            "success": True,
            "data": {
                "compatibility_score": compatibility["score"],
                "compatibility_level": compatibility["level"],
                "description": compatibility["description"],
            },
            "ai_message": f"冲突兼容性评分为{compatibility['score'] * 100:.0f}分，等级为{compatibility['level']}",
        }

    def _build_prediction_response(self, potential_conflicts: List[Dict]) -> Dict[str, Any]:
        """构建预测响应"""
        return {
            "success": True,
            "data": {
                "potential_conflicts": potential_conflicts,
                "conflict_count": len(potential_conflicts),
            },
            "ai_message": f"预测{len(potential_conflicts)}个潜在冲突点",
        }

    def _build_suggestions_response(self, suggestions: List[Dict]) -> Dict[str, Any]:
        """构建建议响应"""
        return {
            "success": True,
            "data": {
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
            },
            "ai_message": f"生成{len(suggestions)}条冲突处理建议",
        }

    def _generate_ai_message(
        self,
        user_a_style: Dict,
        user_b_style: Dict,
        compatibility: Dict,
        potential_conflicts: List[Dict]
    ) -> str:
        """生成 AI 消息"""
        style_a = user_a_style.get("primary_style", "未知")
        style_b = user_b_style.get("primary_style", "未知")

        lines = [
            "冲突兼容性分析结果：",
            "",
            f"👤 用户 A 的主要风格：{self._get_style_name(style_a)}",
            f"👤 用户 B 的主要风格：{self._get_style_name(style_b)}",
            "",
            f"兼容性评分：{compatibility['score'] * 100:.0f}分 ({compatibility['level']})",
            f"分析：{compatibility['description']}",
        ]

        if potential_conflicts:
            lines.append("")
            lines.append(f"预测{len(potential_conflicts)}个潜在冲突点:")
            for c in potential_conflicts[:2]:
                lines.append(f"   • {c['description']}")

        return "\n".join(lines)

    # ========== 辅助函数 ==========

    def _get_style_name(self, style: str) -> str:
        """获取风格名称"""
        names = {
            "avoiding": "回避型",
            "competing": "对抗型",
            "accommodating": "迁就型",
            "compromising": "妥协型",
            "collaborating": "协作型",
            "unknown": "未评估",
        }
        return names.get(style, style)

    def _get_compatibility_level(self, score: float) -> str:
        """获取兼容性等级"""
        if score >= 0.8:
            return "优秀"
        elif score >= 0.6:
            return "良好"
        elif score >= 0.4:
            return "一般"
        else:
            return "需关注"

    def _get_compatibility_description(
        self,
        style_a: str,
        style_b: str,
        score: float
    ) -> str:
        """获取兼容性描述"""
        descriptions = {
            ("collaborating", "collaborating"): "理想的协作组合，双方都愿意通过沟通解决问题",
            ("collaborating", "compromising"): "良好的互补，一方主导协作，一方愿意妥协",
            ("competing", "accommodating"): "需要注意平衡，避免一方过度迁就",
            ("avoiding", "avoiding"): "需要注意沟通，避免问题累积",
            ("competing", "competing"): "容易产生冲突，需要学习互相尊重",
        }
        return descriptions.get((style_a, style_b), f"兼容性得分{score * 100:.0f}分")

    def _get_conflict_history(
        self,
        user_a_style: Dict,
        user_b_style: Dict
    ) -> Dict:
        """获取冲突历史（简化实现）"""
        return {
            "total_conflicts": 0,
            "resolved_count": 0,
            "patterns": [],
        }

    def _get_prevention_tips(self, conflict_type: str) -> List[str]:
        """获取预防建议"""
        tips = {
            "power_struggle": [
                "学习轮流做决定",
                "寻找双赢方案",
                "尊重对方的意见",
            ],
            "communication_gap": [
                "定期进行沟通",
                "创造安全的表达环境",
                "不要回避敏感话题",
            ],
            "pursuer_distancer": [
                "追逐方给逃避方一些空间",
                "逃避方尝试表达自己的感受",
                "找到双方都舒适的沟通节奏",
            ],
            "imbalance": [
                "迁就方学习表达自己的需求",
                "主导方多考虑对方感受",
                "建立平等的决策机制",
            ],
            "communication_style_mismatch": [
                "了解对方的沟通风格",
                "调整自己的表达方式",
                "多确认对方的理解",
            ],
        }
        return tips.get(conflict_type, ["保持开放沟通"])


# 全局单例获取函数
_skill_instance: Optional[ConflictCompatibilityAnalyzerSkill] = None


def get_conflict_compatibility_analyzer_skill() -> ConflictCompatibilityAnalyzerSkill:
    """获取冲突兼容性分析 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = ConflictCompatibilityAnalyzerSkill()
    return _skill_instance
