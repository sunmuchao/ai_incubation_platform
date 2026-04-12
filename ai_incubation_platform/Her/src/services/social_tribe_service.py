"""
SocialTribe 圈子融合服务层

包含：
1. 部落匹配服务
2. 数字小家服务
3. 见家长模拟服务
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB
from models.social_tribe_models import (
    LifestyleTribeDB,
    UserTribeMembershipDB,
    TribeCompatibilityDB,
    CoupleDigitalHomeDB,
    CoupleGoalDB,
    CoupleCheckinDB,
    VirtualRoleDB,
    FamilyMeetingSimulationDB
)
from utils.logger import logger


class TribeMatchingService:
    """部落匹配服务"""

    # 生活方式标签兼容性矩阵
    TAG_COMPATIBILITY = {
        "outdoor": {"compatible": ["fitness", "traveler"], "conflicting": ["homebody", "gamer"]},
        "homebody": {"compatible": ["reader", "gamer"], "conflicting": ["outdoor", "party"]},
        "fitness": {"compatible": ["outdoor", "health"], "conflicting": ["party"]},
        "foodie": {"compatible": ["cooking", "traveler"], "conflicting": []},
        "traveler": {"compatible": ["outdoor", "photography"], "conflicting": ["homebody"]},
    }

    def calculate_tribe_compatibility(
        self,
        user_a_id: str,
        user_b_id: str,
        db_session
    ) -> Dict[str, Any]:
        """计算两人的部落兼容性"""
        # 获取两人的部落成员关系
        user_a_tribes = db_session.query(UserTribeMembershipDB).filter(
            UserTribeMembershipDB.user_id == user_a_id
        ).all()

        user_b_tribes = db_session.query(UserTribeMembershipDB).filter(
            UserTribeMembershipDB.user_id == user_b_id
        ).all()

        # 提取部落 ID
        user_a_tribe_ids = set(t.tribe_id for t in user_a_tribes)
        user_b_tribe_ids = set(t.tribe_id for t in user_b_tribes)

        # 共同部落
        common_tribes = list(user_a_tribe_ids & user_b_tribe_ids)

        # 获取标签
        user_a_tags = self._get_user_lifestyle_tags(user_a_tribes, db_session)
        user_b_tags = self._get_user_lifestyle_tags(user_b_tribes, db_session)

        # 计算兼容性
        compatible_tags = []
        conflicting_tags = []

        for tag_a in user_a_tags:
            compat_info = self.TAG_COMPATIBILITY.get(tag_a, {})
            for tag_b in user_b_tags:
                if tag_b in compat_info.get("compatible", []):
                    compatible_tags.append((tag_a, tag_b))
                elif tag_b in compat_info.get("conflicting", []):
                    conflicting_tags.append((tag_a, tag_b))

        # 计算兼容性评分
        base_score = len(common_tribes) * 0.3
        compat_bonus = len(compatible_tags) * 0.1
        conflict_penalty = len(conflicting_tags) * 0.15

        compatibility_score = max(0, min(1, base_score + compat_bonus - conflict_penalty))

        # 生成融合建议
        fusion_suggestions = self._generate_fusion_suggestions(
            user_a_tags, user_b_tags, compatible_tags
        )

        return {
            "common_tribes": common_tribes,
            "compatible_tags": compatible_tags,
            "conflicting_tags": conflicting_tags,
            "compatibility_score": compatibility_score,
            "fusion_suggestions": fusion_suggestions
        }

    def _get_user_lifestyle_tags(
        self,
        memberships: List[UserTribeMembershipDB],
        db_session
    ) -> List[str]:
        """获取用户的生活方式标签"""
        tags = []
        for membership in memberships:
            tribe = db_session.query(LifestyleTribeDB).filter(
                LifestyleTribeDB.id == membership.tribe_id
            ).first()
            if tribe and tribe.lifestyle_tags:
                tags.extend(tribe.lifestyle_tags)
        return list(set(tags))

    def _generate_fusion_suggestions(
        self,
        tags_a: List[str],
        tags_b: List[str],
        compatible: List[tuple]
    ) -> List[Dict]:
        """生成圈子融合建议"""
        suggestions = []

        if compatible:
            suggestions.append({
                "type": "shared_activity",
                "description": f"你们在{compatible[0][0]}和{compatible[0][1]}方面有共同兴趣，可以一起参加相关活动"
            })

        # 找出独特的标签
        unique_to_a = set(tags_a) - set(tags_b)
        unique_to_b = set(tags_b) - set(tags_a)

        if unique_to_a:
            suggestions.append({
                "type": "explore",
                "description": f"你可以了解 TA 的{list(unique_to_a)[:2]}兴趣"
            })

        if unique_to_b:
            suggestions.append({
                "type": "share",
                "description": f"TA 可以了解你的{list(unique_to_b)[:2]}兴趣"
            })

        return suggestions


class DigitalHomeService:
    """数字小家服务"""

    def create_digital_home(
        self,
        user_a_id: str,
        user_b_id: str,
        home_name: str,
        theme: Optional[str] = None,
        db_session=None
    ) -> CoupleDigitalHomeDB:
        """创建数字小家"""
        home_id = f"home_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        home = CoupleDigitalHomeDB(
            id=home_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            home_name=home_name,
            theme=theme or "温馨",
            shared_space_config={
                "photo_wall": True,
                "calendar": True,
                "todo_list": True,
                "memory_box": True
            }
        )

        if db_session:
            db_session.add(home)
            db_session.commit()
            db_session.refresh(home)

        return home

    def create_couple_goal(
        self,
        home_id: str,
        user_a_id: str,
        user_b_id: str,
        goal_title: str,
        goal_type: str,
        target_value: float,
        target_date: datetime,
        db_session=None
    ) -> CoupleGoalDB:
        """创建共同目标"""
        goal_id = f"goal_{home_id}_{datetime.utcnow().timestamp()}"
        goal = CoupleGoalDB(
            id=goal_id,
            home_id=home_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            goal_title=goal_title,
            goal_type=goal_type,
            target_value=target_value,
            target_date=target_date,
            status="active"
        )

        if db_session:
            db_session.add(goal)
            db_session.commit()
            db_session.refresh(goal)

        return goal

    def checkin_goal(
        self,
        goal_id: str,
        user_id: str,
        checkin_value: float = 1,
        proof_photo_urls: Optional[List[str]] = None,
        db_session=None
    ) -> CoupleCheckinDB:
        """打卡目标"""
        # 获取目标
        goal = db_session.query(CoupleGoalDB).filter(
            CoupleGoalDB.id == goal_id
        ).first()

        if not goal:
            raise ValueError("目标不存在")

        # 创建打卡记录
        checkin_id = f"checkin_{goal_id}_{datetime.utcnow().timestamp()}"
        checkin = CoupleCheckinDB(
            id=checkin_id,
            goal_id=goal_id,
            user_id=user_id,
            checkin_value=checkin_value,
            proof_photo_urls=proof_photo_urls or []
        )

        db_session.add(checkin)

        # 更新目标进度
        goal.current_value += checkin_value
        if goal.current_value >= goal.target_value:
            goal.status = "completed"
            goal.completed_at = datetime.utcnow()

        db_session.commit()
        db_session.refresh(checkin)

        return checkin


class FamilyMeetingSimulationService:
    """见家长模拟服务"""

    def create_virtual_role(
        self,
        user_id: str,
        role_name: str,
        role_type: str,
        personality: str,
        db_session=None
    ) -> VirtualRoleDB:
        """创建虚拟角色"""
        role_id = f"role_{user_id}_{datetime.utcnow().timestamp()}"
        role = VirtualRoleDB(
            id=role_id,
            user_id=user_id,
            role_name=role_name,
            role_type=role_type,
            personality=personality,
            typical_questions=self._generate_typical_questions(role_type, personality)
        )

        if db_session:
            db_session.add(role)
            db_session.commit()
            db_session.refresh(role)

        return role

    def _generate_typical_questions(
        self,
        role_type: str,
        personality: str
    ) -> List[str]:
        """生成典型问题"""
        questions = {
            "parent": {
                "严厉": ["你是做什么工作的？", "有房吗？", "打算什么时候结婚？"],
                "温和": ["孩子最近怎么样？", "你们怎么认识的？", "平时喜欢做什么？"],
                "开明": ["年轻人有自己的想法很好", "有什么计划吗？", "需要我们支持什么？"]
            },
            "sibling": {
                "友好": ["你们去哪玩的？", "他/她对你怎么样？", "什么时候请我吃饭？"]
            }
        }

        return questions.get(role_type, {}).get(personality, ["你好啊！", "最近怎么样？"])

    def start_simulation(
        self,
        user_id: str,
        role_id: str,
        scenario: str,
        db_session=None
    ) -> FamilyMeetingSimulationDB:
        """开始见家长模拟"""
        sim_id = f"sim_{user_id}_{datetime.utcnow().timestamp()}"
        sim = FamilyMeetingSimulationDB(
            id=sim_id,
            user_id=user_id,
            role_id=role_id,
            scenario=scenario,
            conversation_history=[],
            status="ongoing"
        )

        if db_session:
            db_session.add(sim)
            db_session.commit()
            db_session.refresh(sim)

        return sim

    def add_simulation_message(
        self,
        simulation_id: str,
        role: str,
        content: str,
        db_session
    ) -> bool:
        """添加模拟对话消息"""
        sim = db_session.query(FamilyMeetingSimulationDB).filter(
            FamilyMeetingSimulationDB.id == simulation_id
        ).first()

        if not sim:
            return False

        if sim.conversation_history is None:
            sim.conversation_history = []

        sim.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

        db_session.commit()
        return True

    def complete_simulation(
        self,
        simulation_id: str,
        performance_scores: Dict[str, int],
        db_session
    ) -> FamilyMeetingSimulationDB:
        """完成模拟"""
        sim = db_session.query(FamilyMeetingSimulationDB).filter(
            FamilyMeetingSimulationDB.id == simulation_id
        ).first()

        if not sim:
            raise ValueError("模拟不存在")

        sim.is_completed = True
        sim.completed_at = datetime.utcnow()
        sim.performance_scores = performance_scores

        # 生成 AI 反馈
        sim.ai_feedback = self._generate_ai_feedback(performance_scores)
        sim.improvement_suggestions = self._generate_improvement_suggestions(performance_scores)

        db_session.commit()
        db_session.refresh(sim)

        return sim

    def _generate_ai_feedback(self, scores: Dict[str, int]) -> str:
        """生成 AI 反馈"""
        avg_score = sum(scores.values()) / max(1, len(scores))

        if avg_score >= 8:
            return "表现出色！你展现了良好的沟通技巧和礼貌素养。"
        elif avg_score >= 6:
            return "表现不错，但还有一些可以改进的地方。"
        else:
            return "建议多加练习，注意沟通方式和礼仪。"

    def _generate_improvement_suggestions(self, scores: Dict[str, int]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if scores.get("communication", 5) < 6:
            suggestions.append("练习更清晰的表达")
        if scores.get("respect", 5) < 6:
            suggestions.append("注意倾听长辈讲话")
        if scores.get("confidence", 5) < 6:
            suggestions.append("保持自信但谦虚的态度")

        return suggestions


# 创建全局服务实例
tribe_matching_service = TribeMatchingService()
digital_home_service = DigitalHomeService()
family_meeting_simulation_service = FamilyMeetingSimulationService()
