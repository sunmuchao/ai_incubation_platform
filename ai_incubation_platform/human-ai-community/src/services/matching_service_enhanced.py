"""
Matching Service Enhanced - 增强成员匹配服务

基于 AI 的成员匹配推荐服务，支持：
1. 兴趣图谱分析
2. 多维度匹配算法
3. 主动推荐
4. 匹配反馈学习

这是 AI Native 架构的核心服务，AI 主动发现匹配机会并推送建议。
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from models.member import CommunityMember, MemberType, Post

logger = logging.getLogger(__name__)


class MatchReason(str, Enum):
    """匹配理由类型"""
    COMMON_INTERESTS = "common_interests"
    COMPLEMENTARY_SKILLS = "complementary_skills"
    SIMILAR_ACTIVITY = "similar_activity"
    COLLABORATION_POTENTIAL = "collaboration_potential"
    MUTUAL_CONNECTIONS = "mutual_connections"


@dataclass
class MemberProfile:
    """成员画像"""
    member_id: str
    name: str
    interests: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    activity_level: str = "medium"  # low/medium/high
    post_count: int = 0
    comment_count: int = 0
    reputation_score: float = 1.0
    preferred_collaboration_types: List[str] = field(default_factory=list)
    last_active_at: Optional[datetime] = None


@dataclass
class MatchResult:
    """匹配结果"""
    matched_member_id: str
    matched_member_name: str
    match_score: float  # 0-1
    reasons: List[MatchReason] = field(default_factory=list)
    common_interests: List[str] = field(default_factory=list)
    complementary_skills: List[str] = field(default_factory=list)
    collaboration_suggestion: str = ""
    confidence: float = 0.0


class MatchingServiceEnhanced:
    """
    增强成员匹配服务

    使用 AI 主动分析成员兴趣和行为模式，
    发现潜在的匹配机会并推送推荐。
    """

    def __init__(self, community_service=None):
        self.community_service = community_service
        self._member_profiles: Dict[str, MemberProfile] = {}
        self._match_history: Dict[str, List[MatchResult]] = {}
        self._pending_recommendations: Dict[str, List[MatchResult]] = {}

        # 匹配权重配置
        self.weights = {
            "interests": 0.4,
            "skills": 0.2,
            "activity": 0.15,
            "reputation": 0.15,
            "recency": 0.1,
        }

    def build_member_profile(self, member: CommunityMember) -> MemberProfile:
        """
        构建成员画像

        分析成员的兴趣、技能、活跃度等特征。
        """
        # 占位实现（实际应分析发帖、评论、点赞等行为）
        profile = MemberProfile(
            member_id=member.id,
            name=member.name,
            interests=self._extract_interests(member),
            skills=self._extract_skills(member),
            activity_level=self._calculate_activity_level(member),
            post_count=member.post_count,
            reputation_score=1.0,
            last_active_at=member.join_date,
        )
        self._member_profiles[member.id] = profile
        return profile

    def _extract_interests(self, member: CommunityMember) -> List[str]:
        """从成员行为提取兴趣标签"""
        # 占位实现（实际应分析发帖内容、标签、互动等）
        interest_keywords = {
            "人工智能": ["AI", "机器学习", "深度学习", "NLP"],
            "编程": ["Python", "Java", "JavaScript", "代码"],
            "数据科学": ["数据分析", "可视化", "统计"],
            "产品": ["产品设计", "用户体验", "需求"],
        }

        # 从 ai_persona 提取（如果是 AI 成员）
        if member.ai_persona:
            interests = []
            for category, keywords in interest_keywords.items():
                if any(kw in member.ai_persona for kw in keywords):
                    interests.append(category)
            return interests

        # 默认兴趣
        return ["社区", "交流"]

    def _extract_skills(self, member: CommunityMember) -> List[str]:
        """从成员行为提取技能标签"""
        # 占位实现
        if member.ai_model:
            return [f"AI 模型：{member.ai_model}"]
        return []

    def _calculate_activity_level(self, member: CommunityMember) -> str:
        """计算活跃度等级"""
        if member.post_count >= 10:
            return "high"
        elif member.post_count >= 3:
            return "medium"
        else:
            return "low"

    async def find_matching_members(
        self,
        member_id: str,
        limit: int = 10,
        criteria: Optional[Dict[str, Any]] = None,
    ) -> List[MatchResult]:
        """
        查找匹配成员

        基于兴趣、技能、活跃度等多维度计算匹配度。
        """
        if member_id not in self._member_profiles:
            if self.community_service:
                member = self.community_service.get_member(member_id)
                if member:
                    self.build_member_profile(member)
                else:
                    return []
            else:
                return []

        source_profile = self._member_profiles[member_id]
        matches = []

        # 遍历所有成员计算匹配度
        for target_id, target_profile in self._member_profiles.items():
            if target_id == member_id:
                continue

            match_result = self._calculate_match(
                source_profile,
                target_profile,
            )
            if match_result.match_score >= 0.3:  # 最低匹配阈值
                matches.append(match_result)

        # 排序并返回
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:limit]

    def _calculate_match(
        self,
        source: MemberProfile,
        target: MemberProfile,
    ) -> MatchResult:
        """计算两个成员之间的匹配度"""
        reasons = []
        common_interests = []
        complementary_skills = []

        # 兴趣匹配
        interest_score = self._calculate_interest_similarity(source, target)
        if interest_score > 0.3:
            reasons.append(MatchReason.COMMON_INTERESTS)
            common_interests = list(set(source.interests) & set(target.interests))

        # 技能互补
        skill_complementarity = self._calculate_skill_complementarity(source, target)
        if skill_complementarity > 0.3:
            reasons.append(MatchReason.COMPLEMENTARY_SKILLS)
            complementary_skills = self._find_complementary_skills(source, target)

        # 活跃度相似
        if source.activity_level == target.activity_level:
            reasons.append(MatchReason.SIMILAR_ACTIVITY)

        # 综合匹配分数
        match_score = (
            interest_score * self.weights["interests"] +
            skill_complementarity * self.weights["skills"] +
            (1.0 if source.activity_level == target.activity_level else 0.5) * self.weights["activity"] +
            min(source.reputation_score, target.reputation_score) / 5.0 * self.weights["reputation"]
        )

        # 生成协作建议
        collaboration_suggestion = self._generate_collaboration_suggestion(
            source, target, common_interests, complementary_skills
        )
        if collaboration_suggestion:
            reasons.append(MatchReason.COLLABORATION_POTENTIAL)

        return MatchResult(
            matched_member_id=target.member_id,
            matched_member_name=target.name,
            match_score=round(match_score, 3),
            reasons=reasons,
            common_interests=common_interests,
            complementary_skills=complementary_skills,
            collaboration_suggestion=collaboration_suggestion,
            confidence=0.8,  # 占位置信度
        )

    def _calculate_interest_similarity(
        self,
        source: MemberProfile,
        target: MemberProfile,
    ) -> float:
        """计算兴趣相似度（Jaccard 相似度）"""
        if not source.interests or not target.interests:
            return 0.0

        intersection = len(set(source.interests) & set(target.interests))
        union = len(set(source.interests) | set(target.interests))

        return intersection / union if union > 0 else 0.0

    def _calculate_skill_complementarity(
        self,
        source: MemberProfile,
        target: MemberProfile,
    ) -> float:
        """计算技能互补性"""
        if not source.skills or not target.skills:
            return 0.5  # 无技能信息时返回默认值

        # 技能不同但有重叠领域时互补性高
        source_skills = set(source.skills)
        target_skills = set(target.skills)

        intersection = len(source_skills & target_skills)
        symmetric_diff = len(source_skills ^ target_skills)

        if intersection == 0:
            return 0.3  # 无共同技能，互补性低

        return min(1.0, symmetric_diff / (intersection + symmetric_diff))

    def _find_complementary_skills(
        self,
        source: MemberProfile,
        target: MemberProfile,
    ) -> List[str]:
        """找出互补技能"""
        source_skills = set(source.skills)
        target_skills = set(target.skills)

        # 对方有而自己没有的技能
        complementary = list(target_skills - source_skills)
        return complementary[:5]  # 限制数量

    def _generate_collaboration_suggestion(
        self,
        source: MemberProfile,
        target: MemberProfile,
        common_interests: List[str],
        complementary_skills: List[str],
    ) -> str:
        """生成协作建议"""
        if common_interests:
            interests_str = "、".join(common_interests[:3])
            return f"你们都对 {interests_str} 感兴趣，可以一起讨论或合作项目"

        if complementary_skills:
            return f"你们的技能互补，可以考虑协作完成相关项目"

        return ""

    async def get_active_recommendations(
        self,
        member_id: str,
        limit: int = 5,
    ) -> List[MatchResult]:
        """
        获取主动推荐

        AI 主动分析并推送匹配推荐，而不是等待用户查询。
        """
        # 检查是否有待推送的推荐
        if member_id in self._pending_recommendations:
            recommendations = self._pending_recommendations[member_id]
            del self._pending_recommendations[member_id]
            return recommendations[:limit]

        # 实时计算推荐
        matches = await self.find_matching_members(member_id, limit=limit)
        return matches

    async def proactively_push_recommendations(
        self,
        member_id: str,
    ) -> List[MatchResult]:
        """
        主动推送推荐

        AI 定期分析社区成员，发现新的匹配机会并推送。
        """
        matches = await self.find_matching_members(member_id, limit=3)

        # 过滤掉已经推荐过的
        history = self._match_history.get(member_id, [])
        previously_recommended = {m.matched_member_id for m in history}
        new_matches = [m for m in matches if m.matched_member_id not in previously_recommended]

        if new_matches:
            # 添加到待推送队列
            if member_id not in self._pending_recommendations:
                self._pending_recommendations[member_id] = []
            self._pending_recommendations[member_id].extend(new_matches)

            # 记录历史
            if member_id not in self._match_history:
                self._match_history[member_id] = []
            self._match_history[member_id].extend(new_matches)

        return new_matches

    def record_match_feedback(
        self,
        member_id: str,
        matched_member_id: str,
        liked: bool,
        feedback: Optional[str] = None,
    ):
        """
        记录匹配反馈

        用于优化推荐算法。
        """
        # 占位实现（实际应用于模型训练）
        logger.info(
            f"Match feedback: {member_id} -> {matched_member_id}, liked={liked}, feedback={feedback}"
        )

    def analyze_community_interests(self) -> Dict[str, Any]:
        """
        分析社区整体兴趣分布

        用于发现社区热点和趋势。
        """
        interest_counts = {}
        for profile in self._member_profiles.values():
            for interest in profile.interests:
                interest_counts[interest] = interest_counts.get(interest, 0) + 1

        # 排序
        sorted_interests = sorted(
            interest_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "total_members": len(self._member_profiles),
            "top_interests": [
                {"interest": name, "count": count}
                for name, count in sorted_interests[:10]
            ],
            "interest_distribution": interest_counts,
        }


# 全局服务实例
_matching_service_enhanced: Optional[MatchingServiceEnhanced] = None


def get_matching_service_enhanced(community_service=None) -> MatchingServiceEnhanced:
    """获取匹配服务单例"""
    global _matching_service_enhanced
    if _matching_service_enhanced is None:
        _matching_service_enhanced = MatchingServiceEnhanced(community_service)
    return _matching_service_enhanced
