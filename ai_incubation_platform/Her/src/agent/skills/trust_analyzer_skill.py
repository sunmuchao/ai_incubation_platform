"""
信任度分析 Skill

P0 功能：综合分析用户信任度，包括信任分、信任勋章、验证状态等
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class TrustAnalyzerSkill:
    """
    信任度分析 Skill

    核心能力:
    - 综合信任分计算
    - 信任勋章分析
    - 验证状态评估
    - 信任等级判定
    - 提升建议生成

    自主触发条件:
    - 用户查看个人资料时
    - 匹配推荐排序时
    - 关系阶段升级前
    """

    name = "trust_analyzer"
    version = "1.0.0"
    description = """
    信任度分析专家

    能力:
    - 综合信任分计算 (0-100)
    - 信任勋章墙分析
    - 验证状态全面评估
    - 信任等级判定 (青铜/白银/黄金/铂金/钻石)
    - 个性化信任提升建议
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
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID (可选，用于查看他人信任度)"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["full", "score_only", "badges_only", "suggestions"],
                    "description": "分析类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "viewing_profile": {"type": "boolean"},
                        "matching_sort": {"type": "boolean"},
                        "pre_date_check": {"type": "boolean"}
                    }
                }
            },
            "required": ["user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "trust_score": {"type": "number"},
                "trust_level": {"type": "string"},
                "badges": {"type": "array"},
                "verifications": {"type": "array"},
                "suggestions": {"type": "array"}
            }
        }

    async def execute(
        self,
        user_id: str,
        target_user_id: Optional[str] = None,
        analysis_type: str = "full",
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行信任度分析

        Args:
            user_id: 请求用户 ID
            target_user_id: 目标用户 ID (可选)
            analysis_type: 分析类型
            context: 上下文信息

        Returns:
            分析结果
        """
        logger.info(f"TrustAnalyzer: Analyzing trust for user={user_id}, target={target_user_id}")

        try:
            # 确定分析目标
            analysis_target = target_user_id or user_id

            # 获取信任分
            trust_score_info = self._get_trust_score(analysis_target)

            # 获取信任勋章
            badges = self._get_trust_badges(analysis_target)

            # 获取验证状态
            verifications = self._get_verifications(analysis_target)

            # 根据分析类型返回结果
            if analysis_type == "score_only":
                return self._build_score_response(trust_score_info)
            elif analysis_type == "badges_only":
                return self._build_badges_response(badges)
            elif analysis_type == "suggestions":
                suggestions = self._generate_suggestions(trust_score_info, badges, verifications)
                return self._build_suggestions_response(suggestions)
            else:  # full
                suggestions = self._generate_suggestions(trust_score_info, badges, verifications)
                return self._build_full_response(
                    trust_score_info, badges, verifications, suggestions, context
                )

        except Exception as e:
            logger.error(f"TrustAnalyzer execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "信任度分析失败，请稍后再试"
            }

    def _get_trust_score(self, user_id: str) -> Dict:
        """获取信任分信息"""
        # 调用信任分服务
        from services.behavior_credit_service import behavior_credit_service

        credit_report = behavior_credit_service.get_user_credit_report(user_id)

        return {
            "score": credit_report.get("credit_score", 0),
            "level": self._score_to_level(credit_report.get("credit_score", 0)),
            "level_name": self._get_level_name(credit_report.get("credit_score", 0)),
            "factors": credit_report.get("factors", []),
        }

    def _get_trust_badges(self, user_id: str) -> List[Dict]:
        """获取信任勋章"""
        from db.database import SessionLocal
        from models.p0_identity_models import TrustBadgeDB

        db = SessionLocal()
        badges = db.query(TrustBadgeDB).filter(
            TrustBadgeDB.user_id == user_id,
            TrustBadgeDB.is_active == True
        ).all()

        return [
            {
                "id": b.id,
                "badge_type": b.badge_type,
                "badge_name": b.badge_name,
                "badge_icon": b.badge_icon,
                "earned_at": b.earned_at.isoformat() if b.earned_at else None,
                "score_weight": b.score_weight,
            }
            for b in badges
        ]

    def _get_verifications(self, user_id: str) -> List[Dict]:
        """获取验证状态"""
        from db.database import SessionLocal
        from models.p0_identity_models import (
            EducationCredentialDB,
            OccupationCredentialDB,
            IncomeCredentialDB,
            PropertyCredentialDB,
        )
        from db.models import IdentityVerificationDB

        db = SessionLocal()
        verifications = []

        # 基础实名认证
        basic = db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id
        ).first()
        if basic:
            verifications.append({
                "type": "identity",
                "name": "实名认证",
                "icon": "🆔",
                "status": basic.verification_status,
                "verified_at": basic.verified_at.isoformat() if basic.verified_at else None,
            })

        # 学历认证
        edu = db.query(EducationCredentialDB).filter(
            EducationCredentialDB.user_id == user_id
        ).first()
        if edu:
            verifications.append({
                "type": "education",
                "name": "学历认证",
                "icon": "🎓",
                "status": edu.verification_status,
                "school_name": edu.school_name,
                "degree_type": edu.degree_type,
                "verified_at": edu.verified_at.isoformat() if edu.verified_at else None,
            })

        # 职业认证
        occ = db.query(OccupationCredentialDB).filter(
            OccupationCredentialDB.user_id == user_id
        ).first()
        if occ:
            verifications.append({
                "type": "occupation",
                "name": "职业认证",
                "icon": "💼",
                "status": occ.verification_status,
                "company_name": occ.company_name,
                "verified_at": occ.verified_at.isoformat() if occ.verified_at else None,
            })

        return verifications

    def _score_to_level(self, score: int) -> str:
        """分数转等级"""
        if score >= 90:
            return "diamond"
        elif score >= 80:
            return "platinum"
        elif score >= 60:
            return "gold"
        elif score >= 40:
            return "silver"
        else:
            return "bronze"

    def _get_level_name(self, score: int) -> str:
        """获取等级名称"""
        level_names = {
            "diamond": "钻石",
            "platinum": "铂金",
            "gold": "黄金",
            "silver": "白银",
            "bronze": "青铜",
        }
        return level_names.get(self._score_to_level(score), "未知")

    def _generate_suggestions(
        self,
        score_info: Dict,
        badges: List[Dict],
        verifications: List[Dict]
    ) -> List[Dict]:
        """生成信任提升建议"""
        suggestions = []

        # 基于信任分的建议
        if score_info["score"] < 40:
            suggestions.append({
                "priority": "high",
                "type": "complete_profile",
                "message": "完善个人资料，提升基础信任分",
                "action": "complete_profile",
                "score_impact": "+10",
            })

        # 基于验证状态的建议
        verified_types = {v["type"] for v in verifications if v["status"] == "verified"}

        if "identity" not in verified_types:
            suggestions.append({
                "priority": "high",
                "type": "verify_identity",
                "message": "完成实名认证，获得🆔信任勋章",
                "action": "verify_identity",
                "score_impact": "+20",
            })

        if "education" not in verified_types:
            suggestions.append({
                "priority": "medium",
                "type": "verify_education",
                "message": "完成学历认证，获得🎓信任勋章",
                "action": "verify_education",
                "score_impact": "+20",
            })

        if "occupation" not in verified_types:
            suggestions.append({
                "priority": "medium",
                "type": "verify_occupation",
                "message": "完成职业认证，获得💼信任勋章",
                "action": "verify_occupation",
                "score_impact": "+15",
            })

        # 基于勋章数量的建议
        if len(badges) < 3:
            suggestions.append({
                "priority": "low",
                "type": "collect_badges",
                "message": "收集更多信任勋章，提升综合信任度",
                "action": "collect_badges",
                "score_impact": "variable",
            })

        return suggestions[:5]  # 最多返回 5 条建议

    def _build_full_response(
        self,
        score_info: Dict,
        badges: List[Dict],
        verifications: List[Dict],
        suggestions: List[Dict],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """构建完整响应"""
        is_self = context.get("viewing_profile") if context else True

        ai_message = self._generate_ai_message(score_info, badges, verifications, is_self)

        return {
            "success": True,
            "data": {
                "trust_score": score_info["score"],
                "trust_level": score_info["level"],
                "trust_level_name": score_info["level_name"],
                "badges": badges,
                "badge_count": len(badges),
                "verifications": verifications,
                "suggestions": suggestions,
            },
            "ai_message": ai_message,
        }

    def _build_score_response(self, score_info: Dict) -> Dict[str, Any]:
        """构建仅分数响应"""
        return {
            "success": True,
            "data": {
                "trust_score": score_info["score"],
                "trust_level": score_info["level"],
                "trust_level_name": score_info["level_name"],
            },
            "ai_message": f"当前信任分为{score_info['score']}，等级为{score_info['level_name']}",
        }

    def _build_badges_response(self, badges: List[Dict]) -> Dict[str, Any]:
        """构建仅勋章响应"""
        return {
            "success": True,
            "data": {
                "badges": badges,
                "badge_count": len(badges),
            },
            "ai_message": f"共获得{len(badges)}枚信任勋章",
        }

    def _build_suggestions_response(self, suggestions: List[Dict]) -> Dict[str, Any]:
        """构建仅建议响应"""
        return {
            "success": True,
            "data": {
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
            },
            "ai_message": f"有{len(suggestions)}条信任提升建议",
        }

    def _generate_ai_message(
        self,
        score_info: Dict,
        badges: List[Dict],
        verifications: List[Dict],
        is_self: bool = True
    ) -> str:
        """生成 AI 消息"""
        level_name = score_info["level_name"]
        score = score_info["score"]

        if is_self:
            prefix = "您的信任度分析结果："
        else:
            prefix = "对方的信任度分析结果："

        # 根据分数生成不同语气
        if score >= 80:
            tone = f"非常优秀！您已达到{level_name}等级，继续保持~"
        elif score >= 60:
            tone = f"不错！当前为{level_name}等级，还有提升空间~"
        elif score >= 40:
            tone = f"当前为{level_name}等级，建议完成更多认证提升信任度"
        else:
            tone = f"当前为{level_name}等级，请尽快完善资料和认证"

        badge_msg = f"已获得{len(badges)}枚信任勋章" if badges else "尚未获得信任勋章"

        return f"{prefix}\n\n{tone}\n{badge_msg}"


# 全局单例获取函数
_skill_instance: Optional[TrustAnalyzerSkill] = None


def get_trust_analyzer_skill() -> TrustAnalyzerSkill:
    """获取信任度分析 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = TrustAnalyzerSkill()
    return _skill_instance
