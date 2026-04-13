"""
快速入门服务 - 传统红娘第一步

核心理念：
- 30秒完成基础信息收集
- 最小信息立即匹配
- 红娘风格开场白

设计参考：docs/PROGRESSIVE_SMART_MATCHING_SYSTEM.md
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import random
import json
import uuid

from sqlalchemy.orm import Session
from services.base_service import BaseService
from db.models import (
    QuickStartRecordDB,
    UserDB,
    UserSocialMetricsDB,
    UserFeedbackLearningDB,
    MatchHistoryDB,
)
from utils.logger import logger
from utils.db_session_manager import db_session

# 导入向量调整服务
from services.vector_adjustment_service import (
    get_vector_adjustment_service,
    VectorAdjustmentService,
)


# ==================== 数据结构定义 ====================

@dataclass
class QuickStartInput:
    """快速入门输入（4个硬条件 + 3个可选字段）"""
    age: int
    gender: str  # male, female, other
    location: str
    relationship_goal: str  # serious, marriage, dating, casual
    # 可选字段（提高匹配精度）
    education: Optional[str] = None  # high_school, college, bachelor, bachelor_student, master, master_student, phd, phd_student
    occupation: Optional[str] = None  # student, tech, finance, education, medical, government, business, freelancer, other
    income: Optional[str] = None  # no_income, under_10, 10-20, 20-30, 30-50, over_50, private


@dataclass
class SocialProof:
    """社会认同背书"""
    like_rate: float = 0.5
    elements: List[str] = field(default_factory=list)
    trust_badges: List[str] = field(default_factory=list)
    confidence_level: str = "medium"  # high, medium, low


@dataclass
class InitialMatchCandidate:
    """初始推荐候选人"""
    user_id: str
    name: str
    age: int
    location: str
    avatar_url: Optional[str] = None
    compatibility_preview: str = ""
    social_proof: SocialProof = field(default_factory=SocialProof)

    # 匹配详情
    match_type: str = "cold_start"  # cold_start, location_priority, popular
    score: float = 0.5


@dataclass
class QuickStartResult:
    """快速入门结果"""
    user_id: str
    user_vector_basic: List[float]  # 基础向量（仅人口统计学）
    initial_matches: List[InitialMatchCandidate]
    ai_message: str
    next_step: str = "show_matches"
    quick_start_completed: bool = False


# ==================== 关系目标选项 ====================

RELATIONSHIP_GOAL_OPTIONS = [
    {"value": "serious", "label": "认真恋爱", "icon": "💕", "description": "寻找认真交往的伴侣"},
    {"value": "marriage", "label": "奔着结婚", "icon": "💍", "description": "以结婚为目标"},
    {"value": "dating", "label": "轻松交友", "icon": "☕", "description": "轻松约会、交友"},
    {"value": "casual", "label": "随便聊聊", "icon": "💭", "description": "先聊聊看看"},
]

# 不喜欢原因选项（红娘追问）
DISLIKE_REASON_OPTIONS = [
    {"value": "age_not_match", "label": "年龄不太合适", "icon": "📅"},
    {"value": "location_far", "label": "距离太远了", "icon": "📍"},
    {"value": "not_my_type", "label": "不是我喜欢的类型", "icon": "💔"},
    {"value": "photo_concern", "label": "照片让我犹豫", "icon": "📸"},
    {"value": "bio_issue", "label": "简介不太吸引我", "icon": "📝"},
    {"value": "already_chatting", "label": "已经和别人在聊了", "icon": "💬"},
    {"value": "other", "label": "其他原因", "icon": "💭"},
]


# ==================== 快速入门服务 ====================

class QuickStartService(BaseService[QuickStartRecordDB]):
    """
    快速入门服务 - 传统红娘第一步

    核心能力：
    - 30秒完成基础信息收集
    - 基于最小信息的冷启动匹配
    - 生成红娘风格开场白
    - 为每个候选人生成社会认同背书

    自主触发条件：
    - 新用户注册后
    - 用户主动发起快速入门
    """

    def __init__(self, db: Session = None):
        super().__init__(db, QuickStartRecordDB)

    async def quick_register(
        self,
        user_id: str,
        input_data: QuickStartInput
    ) -> QuickStartResult:
        """
        30秒快速入门

        Args:
            user_id: 用户ID（如果已有账户）
            input_data: 快速入门输入

        Returns:
            QuickStartResult:
                - user_vector_basic: 基础向量（仅人口统计学）
                - initial_matches: 3-5个初始推荐
                - ai_message: 红娘风格开场白
        """
        self.log_info(f"QuickStartService: Starting quick register for user={user_id}")

        # 1. 如果没有用户ID，创建临时用户；否则更新用户信息
        if not user_id:
            user_id = await self._create_temporary_user(input_data)
        else:
            # 更新现有用户的基本信息
            await self._update_user_profile(user_id, input_data)

        # 2. 创建基础用户向量（仅填充人口统计学维度 v0-v9）
        user_vector = self._create_basic_vector(input_data)

        # 3. 使用冷启动匹配策略
        initial_matches = await self._cold_start_match(
            user_id=user_id,
            input_data=input_data,
            user_vector=user_vector,
            limit=5
        )

        # 4. 为每个候选人生成社会认同背书
        for match in initial_matches:
            match.social_proof = await self._get_social_proof(match.user_id)

        # 5. 生成红娘风格开场白
        ai_message = self._generate_matchmaker_intro(
            matches_count=len(initial_matches),
            location=input_data.location
        )

        # 6. 持久化快速入门记录
        await self._save_quick_start_record(
            user_id=user_id,
            input_data=input_data,
            initial_matches=initial_matches
        )

        return QuickStartResult(
            user_id=user_id,
            user_vector_basic=user_vector.tolist(),
            initial_matches=initial_matches,
            ai_message=ai_message,
            next_step="show_matches"
        )

    def _create_basic_vector(self, input_data: QuickStartInput) -> Any:
        """创建基础用户向量（仅填充人口统计学维度 v0-v9）"""
        import numpy as np

        vector = np.zeros(144)

        # v0: 年龄归一化
        vector[0] = input_data.age / 100

        # v1-v2: 年龄偏好（默认同龄上下5岁）
        vector[1] = (input_data.age - 5) / 100  # 下限
        vector[2] = (input_data.age + 5) / 100  # 上限

        # v3: 性别编码
        vector[3] = self._encode_gender(input_data.gender)

        # v4: 性取向（默认异性）
        vector[4] = 0.0

        # v5: 性别偏好（默认异性）
        opposite_gender = "female" if input_data.gender == "male" else "male"
        vector[5] = self._encode_gender(opposite_gender)

        # v6-v9: 地理编码
        vector[6:10] = self._encode_location(input_data.location)

        return vector

    def _encode_gender(self, gender: str) -> float:
        """性别编码"""
        mapping = {"male": 0.0, "female": 1.0, "other": 0.5}
        return mapping.get(gender.lower(), 0.5)

    def _encode_location(self, location: str) -> Any:
        """地理编码（返回 v6-v9）"""
        import numpy as np

        # v6: 城市层级（一线=1.0, 二线=0.7, 三线=0.5）
        city_level = self._get_city_level(location)

        # v7: 是否接受异地（默认可以）
        accept_remote = 0.5

        # v8-v9: 经纬度（默认值）
        longitude = 0.5
        latitude = 0.5

        return np.array([city_level, accept_remote, longitude, latitude])

    def _get_city_level(self, location: str) -> float:
        """获取城市层级"""
        first_tier = ["北京", "上海", "广州", "深圳", "一线城市"]
        second_tier = ["杭州", "南京", "武汉", "成都", "重庆", "西安", "苏州", "天津"]

        if any(city in location for city in first_tier):
            return 1.0
        elif any(city in location for city in second_tier):
            return 0.7
        else:
            return 0.5

    async def _cold_start_match(
        self,
        user_id: str,
        input_data: QuickStartInput,
        user_vector: Any,
        limit: int = 5
    ) -> List[InitialMatchCandidate]:
        """
        冷启动匹配策略

        策略组合：
        1. 地理优先匹配（同城/同省）
        2. 关系目标兼容性
        3. 年龄适配
        4. 热门候选补充
        """
        matches = []

        # 1. 查询候选池
        candidates = await self._query_candidate_pool(
            input_data=input_data,
            exclude_user_id=user_id,
            limit=limit * 3
        )

        # 2. 计算匹配分数
        scored_candidates = []
        for candidate in candidates:
            score, match_type, preview = self._calculate_cold_start_score(
                input_data=input_data,
                candidate=candidate,
                user_vector=user_vector
            )
            scored_candidates.append({
                "candidate": candidate,
                "score": score,
                "match_type": match_type,
                "preview": preview
            })

        # 3. 按分数排序
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # 4. 取前 limit 个
        for item in scored_candidates[:limit]:
            candidate = item["candidate"]
            matches.append(InitialMatchCandidate(
                user_id=candidate["id"],
                name=candidate.get("name", "TA"),
                age=candidate.get("age", 0),
                location=candidate.get("location", ""),
                avatar_url=candidate.get("avatar_url"),
                compatibility_preview=item["preview"],
                match_type=item["match_type"],
                score=item["score"]
            ))

        return matches

    async def _query_candidate_pool(
        self,
        input_data: QuickStartInput,
        exclude_user_id: str,
        limit: int
    ) -> List[Dict]:
        """查询候选池"""

        with db_session() as db:
            # 构建查询条件
            query = db.query(UserDB).filter(
                UserDB.id != exclude_user_id,
                UserDB.is_active == True,
                UserDB.is_permanently_banned == False
            )

            # 关系目标兼容性
            if input_data.relationship_goal == "marriage":
                # 奔着结婚 → 优先找也是奔着结婚的
                query = query.filter(
                    UserDB.relationship_goal.in_(["marriage", "serious"])
                )
            elif input_data.relationship_goal == "serious":
                query = query.filter(
                    UserDB.relationship_goal.in_(["serious", "marriage", "dating"])
                )

            # 年龄适配（上下5岁）
            age_min = input_data.age - 5
            age_max = input_data.age + 5
            query = query.filter(
                UserDB.age >= max(18, age_min),
                UserDB.age <= min(60, age_max)
            )

            # 按创建时间排序（优先活跃用户）
            query = query.order_by(UserDB.created_at.desc())

            users = query.limit(limit).all()

            return [
                {
                    "id": u.id,
                    "name": u.name,
                    "age": u.age,
                    "gender": u.gender,
                    "location": u.location,
                    "avatar_url": u.avatar_url,
                    "relationship_goal": u.relationship_goal,
                }
                for u in users
            ]

    def _calculate_cold_start_score(
        self,
        input_data: QuickStartInput,
        candidate: Dict,
        user_vector: Any
    ) -> tuple:
        """计算冷启动匹配分数"""

        score = 0.5
        match_type = "cold_start"
        preview_parts = []

        # 1. 地理匹配（权重最高）
        if input_data.location == candidate.get("location"):
            score += 0.3
            match_type = "location_priority"
            preview_parts.append("同城")
        elif self._same_province(input_data.location, candidate.get("location", "")):
            score += 0.15
            preview_parts.append("同省")

        # 2. 关系目标匹配
        goal_match = self._check_goal_compatibility(
            input_data.relationship_goal,
            candidate.get("relationship_goal")
        )
        if goal_match:
            score += 0.2
            preview_parts.append("目标一致")

        # 3. 年龄适配
        age_diff = abs(input_data.age - candidate.get("age", 30))
        if age_diff <= 2:
            score += 0.1
            preview_parts.append("年龄合适")

        preview = ", ".join(preview_parts) if preview_parts else "初步匹配"

        return score, match_type, preview

    def _same_province(self, location1: str, location2: str) -> bool:
        """判断是否同省"""
        # 简化实现：取城市名前缀
        province_keywords = {
            "北京": "北京", "上海": "上海", "广州": "广东", "深圳": "广东",
            "杭州": "浙江", "南京": "江苏", "武汉": "湖北", "成都": "四川",
        }

        prov1 = province_keywords.get(location1.split("市")[0], "")
        prov2 = province_keywords.get(location2.split("市")[0], "")

        return prov1 and prov2 and prov1 == prov2

    def _check_goal_compatibility(self, goal1: str, goal2: str) -> bool:
        """检查关系目标兼容性"""
        compatible_groups = [
            {"serious", "marriage"},
            {"dating", "casual"}
        ]

        for group in compatible_groups:
            if goal1 in group and goal2 in group:
                return True

        return goal1 == goal2

    async def _get_social_proof(self, user_id: str) -> SocialProof:
        """获取社会认同背书"""

        with db_session() as db:
            # 尝试获取已有的社会认同指标
            metrics = db.query(UserSocialMetricsDB).filter(
                UserSocialMetricsDB.user_id == user_id
            ).first()

            # 获取信任徽章
            trust_badges = self._get_trust_badges(db, user_id)

            if metrics:
                elements = []

                # 好评率背书
                if metrics.like_rate > 0.7:
                    elements.append(f"好评率{int(metrics.like_rate * 100)}%")

                # 聊天活跃度背书
                if metrics.chat_response_rate > 0.8:
                    elements.append("回复很积极")

                # 成功案例背书
                if metrics.success_match_count > 0:
                    elements.append(f"{metrics.success_match_count}对成功匹配")

                # 添加徽章背书
                if trust_badges:
                    badge_names = [b.get("display_name", "") for b in trust_badges[:2]]
                    elements.extend(badge_names)

                confidence = "high" if metrics.like_rate > 0.8 else "medium"

                return SocialProof(
                    like_rate=metrics.like_rate,
                    elements=elements,
                    trust_badges=trust_badges,
                    confidence_level=confidence
                )

            # 没有数据，检查是否有徽章
            if trust_badges:
                return SocialProof(
                    like_rate=0.5,
                    elements=[b.get("display_name", "已认证") for b in trust_badges[:2]],
                    trust_badges=trust_badges,
                    confidence_level="medium"
                )

            # 没有数据，返回默认值
            return SocialProof(
                like_rate=0.5,
                elements=["新人推荐"],
                trust_badges=[],
                confidence_level="low"
            )

    def _get_trust_badges(self, db: Session, user_id: str) -> List[Dict]:
        """获取用户信任徽章"""
        from db.models import VerificationBadgeDB

        badges = db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.status == "active"
        ).order_by(VerificationBadgeDB.display_order).limit(5).all()

        return [
            {
                "badge_type": b.badge_type,
                "display_name": b.description or self._get_badge_display_name(b.badge_type),
                "icon": b.icon_url or self._get_badge_icon(b.badge_type),
            }
            for b in badges
        ]

    def _get_badge_display_name(self, badge_type: str) -> str:
        """获取徽章显示名称"""
        badge_names = {
            "identity_verified": "实名认证",
            "face_verified": "人脸认证",
            "education_verified": "学历认证",
            "career_verified": "职业认证",
            "premium_member": "会员用户",
            "active_user": "活跃用户",
        }
        return badge_names.get(badge_type, "已认证")

    def _get_badge_icon(self, badge_type: str) -> str:
        """获取徽章图标"""
        badge_icons = {
            "identity_verified": "✅",
            "face_verified": "⭐",
            "education_verified": "🎓",
            "career_verified": "💼",
            "premium_member": "👑",
            "active_user": "🔥",
        }
        return badge_icons.get(badge_type, "✓")

    def _generate_matchmaker_intro(
        self,
        matches_count: int,
        location: str
    ) -> str:
        """生成红娘风格开场白"""
        templates = [
            f"好的，我这有{matches_count}个觉得合适的，你先看看~",
            f"根据你在{location}，我找了几位可能合适的，看看有没有眼缘？",
            f"来，先给你推几位，不喜欢的话告诉我原因，我再帮你找~",
            f"这几位我觉得挺适合你的，你看看有没有感兴趣的？",
        ]
        return random.choice(templates)

    async def _update_user_profile(self, user_id: str, input_data: QuickStartInput) -> None:
        """更新现有用户的基本信息"""
        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                # 核心字段
                user.age = input_data.age
                user.gender = input_data.gender
                user.location = input_data.location
                user.relationship_goal = input_data.relationship_goal
                # 可选字段（提高匹配精度）
                if input_data.education:
                    user.education = input_data.education
                if input_data.occupation:
                    user.occupation = input_data.occupation
                if input_data.income:
                    user.income = input_data.income
                db.commit()
                logger.info(f"[QuickStart] Updated user profile for user={user_id}")

    async def _create_temporary_user(self, input_data: QuickStartInput) -> str:
        """创建临时用户"""
        user_id = f"quick_start_{uuid.uuid4().hex[:8]}"

        with db_session() as db:
            user = UserDB(
                id=user_id,
                name="新用户",
                email=f"{user_id}@temp.her.app",
                password_hash="temp",
                age=input_data.age,
                gender=input_data.gender,
                location=input_data.location,
                relationship_goal=input_data.relationship_goal,
                is_active=True
            )
            db.add(user)
            db.commit()

        return user_id

    async def _save_quick_start_record(
        self,
        user_id: str,
        input_data: QuickStartInput,
        initial_matches: List[InitialMatchCandidate]
    ) -> None:
        """保存快速入门记录（更新或创建）"""

        with db_session() as db:
            # 先检查是否已存在记录
            existing_record = db.query(QuickStartRecordDB).filter(
                QuickStartRecordDB.user_id == user_id
            ).first()

            if existing_record:
                # 更新现有记录
                existing_record.age = input_data.age
                existing_record.gender = input_data.gender
                existing_record.location = input_data.location
                existing_record.relationship_goal = input_data.relationship_goal
                existing_record.initial_match_ids = json.dumps([m.user_id for m in initial_matches])
                existing_record.initial_match_count = len(initial_matches)
                existing_record.updated_at = datetime.now()
                logger.info(f"[QuickStart] Updated existing record for user={user_id}")
            else:
                # 创建新记录
                record = QuickStartRecordDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    age=input_data.age,
                    gender=input_data.gender,
                    location=input_data.location,
                    relationship_goal=input_data.relationship_goal,
                    initial_match_ids=json.dumps([m.user_id for m in initial_matches]),
                    initial_match_count=len(initial_matches)
                )
                db.add(record)
                logger.info(f"[QuickStart] Created new record for user={user_id}")
            db.commit()

    async def update_view_stats(
        self,
        user_id: str,
        viewed_count: int,
        liked_count: int,
        disliked_count: int,
        skipped_count: int
    ) -> None:
        """更新浏览统计"""

        with db_session() as db:
            record = db.query(QuickStartRecordDB).filter(
                QuickStartRecordDB.user_id == user_id
            ).first()

            if record:
                record.viewed_count = viewed_count
                record.liked_count = liked_count
                record.disliked_count = disliked_count
                record.skipped_count = skipped_count

                # 如果喜欢了至少一个，标记为完成
                if liked_count > 0:
                    record.completed_quick_start = True
                    record.first_like_at = datetime.now()

                db.commit()


# ==================== 反馈学习服务 ====================

class FeedbackLearningService(BaseService[UserFeedbackLearningDB]):
    """
    反馈学习服务 - 传统红娘第三步

    核心能力：
    - 处理用户反馈（喜欢/不喜欢/跳过）
    - 不喜欢时追问原因
    - 学习偏好并更新向量
    - 立即生成调整后的新推荐
    """

    def __init__(self, db: Session = None):
        super().__init__(db, UserFeedbackLearningDB)

    async def process_feedback(
        self,
        user_id: str,
        match_id: str,
        feedback_type: str,
        dislike_reason: str = None,
        dislike_detail: str = None
    ) -> Dict:
        """
        处理用户反馈

        Args:
            user_id: 用户ID
            match_id: 被反馈的匹配对象ID
            feedback_type: like, dislike, skip
            dislike_reason: 不喜欢的原因（仅dislike时）
            dislike_detail: 详细说明（可选）

        Returns:
            处理结果，包含：
            - learned_preference: 学习到的偏好
            - ai_response: 红娘风格回应
            - next_matches: 调整后的新推荐（仅dislike时）
        """
        self.log_info(f"FeedbackLearningService: Processing {feedback_type} for user={user_id}, match={match_id}")

        # 1. 持久化反馈记录
        await self._save_feedback_record(
            user_id=user_id,
            match_id=match_id,
            feedback_type=feedback_type,
            dislike_reason=dislike_reason,
            dislike_detail=dislike_detail
        )

        # 2. 根据反馈类型处理
        if feedback_type == "like":
            return await self._process_like_feedback(user_id, match_id)
        elif feedback_type == "dislike":
            return await self._process_dislike_feedback(
                user_id=user_id,
                match_id=match_id,
                reason=dislike_reason,
                detail=dislike_detail
            )
        else:  # skip
            return await self._process_skip_feedback(user_id, match_id)

    async def _process_like_feedback(self, user_id: str, match_id: str) -> Dict:
        """处理喜欢反馈"""

        # 从喜欢的对象提取正向偏好
        liked_profile = await self._get_user_profile(match_id)

        learned_preference = {
            "dimension": "positive_preference",
            "liked_age": liked_profile.get("age"),
            "liked_location": liked_profile.get("location"),
            "confidence": 0.7
        }

        # 调用向量调整服务，更新用户向量
        vector_service = get_vector_adjustment_service()
        learning_result = await vector_service.apply_feedback_adjustment(
            user_id=user_id,
            feedback_type="like",
            reason=None,
            target_profile=liked_profile
        )

        ai_response = "好的，我记下了，下次给你找更多这类~"

        return {
            "success": True,
            "learned_preference": learned_preference,
            "ai_response": ai_response,
            "next_matches": [],  # 喜欢时不立即推新推荐
            "can_start_chat": True,
            "vector_completeness": learning_result.completeness_after,
            "learned_dimensions": learning_result.learned_dimensions,
        }

    async def _process_dislike_feedback(
        self,
        user_id: str,
        match_id: str,
        reason: str,
        detail: str = None
    ) -> Dict:
        """处理不喜欢反馈"""

        # 1. 从原因推断偏好
        inferred_preference = self._infer_preference_from_reason(reason)

        # 2. 获取被拒绝对象画像
        disliked_profile = await self._get_user_profile(match_id)

        # 3. 调用向量调整服务，更新用户向量
        vector_service = get_vector_adjustment_service()
        learning_result = await vector_service.apply_feedback_adjustment(
            user_id=user_id,
            feedback_type="dislike",
            reason=reason,
            target_profile=disliked_profile
        )

        # 4. 生成红娘风格回应
        ai_response = self._generate_matchmaker_followup(reason)

        # 5. 立即生成新的推荐（仅dislike时）
        next_matches = await self._generate_adjusted_matches(
            user_id=user_id,
            exclude_ids=[match_id],
            limit=3
        )

        return {
            "success": True,
            "learned_preference": inferred_preference,
            "ai_response": ai_response,
            "next_matches": next_matches,
            "can_start_chat": False,
            "vector_completeness": learning_result.completeness_after,
            "learned_dimensions": learning_result.learned_dimensions,
        }

    async def _process_skip_feedback(self, user_id: str, match_id: str) -> Dict:
        """处理跳过反馈"""

        return {
            "success": True,
            "learned_preference": {"dimension": "skip", "confidence": 0.3},
            "ai_response": "好的，看看下一个~",
            "next_matches": [],
            "can_start_chat": False
        }

    def _infer_preference_from_reason(self, reason: str) -> Dict:
        """从不喜欢原因推断偏好"""

        mapping = {
            "age_not_match": {
                "dimension": "age_preference",
                "adjustment": "adjust_age_range",
                "confidence": 0.8
            },
            "location_far": {
                "dimension": "location_preference",
                "adjustment": "tighten_location",
                "confidence": 0.9
            },
            "not_my_type": {
                "dimension": "personality_preference",
                "adjustment": "infer_personality",
                "confidence": 0.5
            },
            "photo_concern": {
                "dimension": "visual_preference",
                "adjustment": "infer_visual",
                "confidence": 0.6
            },
            "bio_issue": {
                "dimension": "content_preference",
                "adjustment": "infer_content",
                "confidence": 0.5
            },
        }

        return mapping.get(reason, {
            "dimension": "general",
            "confidence": 0.3
        })

    def _generate_matchmaker_followup(self, reason: str) -> str:
        """生成红娘风格追问回应"""

        templates = {
            "age_not_match": [
                "好的，看来你更喜欢年轻一点的，下次给你找~",
                "明白了，年龄这块我记下了，帮你调整一下~",
                "懂了，下次给你推更符合你年龄偏好的~",
            ],
            "location_far": [
                "那下次给你找同城的，近距离更方便~",
                "了解，距离确实重要，我帮你筛同城的~",
                "好的，我记下了，下次优先推同城~",
            ],
            "not_my_type": [
                "每个人眼缘不一样，你觉得什么样的更吸引你？",
                "能说说你比较喜欢什么类型的吗？下次帮你精准找~",
                "好的，下次给你推不同类型的试试~",
            ],
            "photo_concern": [
                "照片确实很重要，下次帮你找照片更清晰自然的~",
                "明白，下次给你推照片更真实的~",
            ],
            "bio_issue": [
                "简介这块我记下了，下次给你找更有内容的~",
            ],
            "other": [
                "好的，我记下了，下次调整~",
            ],
        }

        return random.choice(templates.get(reason, ["好的，我记下了，下次调整~"]))

    async def _get_user_profile(self, user_id: str) -> Dict:
        """获取用户画像"""

        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()

            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "age": user.age,
                    "gender": user.gender,
                    "location": user.location,
                    "relationship_goal": user.relationship_goal,
                }

            return {}

    async def _save_feedback_record(
        self,
        user_id: str,
        match_id: str,
        feedback_type: str,
        dislike_reason: str = None,
        dislike_detail: str = None
    ) -> None:
        """保存反馈记录"""

        with db_session() as db:
            record = UserFeedbackLearningDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                feedback_type=feedback_type,
                target_match_id=match_id,
                dislike_reason=dislike_reason,
                dislike_detail=dislike_detail,
                created_at=datetime.now()
            )
            db.add(record)
            db.commit()

    async def _generate_adjusted_matches(
        self,
        user_id: str,
        exclude_ids: List[str],
        limit: int
    ) -> List[Dict]:
        """生成调整后的新推荐"""

        # 简化实现：直接调用 QuickStartService
        quick_start_service = QuickStartService()

        # 获取用户基础信息
        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()

            if user:
                input_data = QuickStartInput(
                    age=user.age,
                    gender=user.gender,
                    location=user.location,
                    relationship_goal=user.relationship_goal or "dating"
                )

                matches = await quick_start_service._cold_start_match(
                    user_id=user_id,
                    input_data=input_data,
                    user_vector=quick_start_service._create_basic_vector(input_data),
                    limit=limit
                )

                # 过滤排除的ID
                filtered = [m for m in matches if m.user_id not in exclude_ids]

                return [
                    {
                        "user_id": m.user_id,
                        "name": m.name,
                        "age": m.age,
                        "location": m.location,
                        "avatar_url": m.avatar_url,
                        "compatibility_preview": m.compatibility_preview,
                    }
                    for m in filtered
                ]

        return []

    def get_dislike_reason_options(self) -> List[Dict]:
        """获取不喜欢原因选项"""
        return DISLIKE_REASON_OPTIONS


# ==================== 社会认同服务 ====================

class SocialProofService(BaseService[UserSocialMetricsDB]):
    """
    社会认同服务 - 传统红娘第六步

    核心能力：
    - 计算用户社会认同指标
    - 生成口碑背书推荐理由
    - 更新信任徽章展示
    """

    def __init__(self, db: Session = None):
        super().__init__(db, UserSocialMetricsDB)

    async def calculate_social_metrics(self, user_id: str) -> Dict:
        """计算用户社会认同指标"""

        with db_session() as db:
            # 获取反馈统计
            likes = db.query(UserFeedbackLearningDB).filter(
                UserFeedbackLearningDB.target_match_id == user_id,
                UserFeedbackLearningDB.feedback_type == "like"
            ).count()

            dislikes = db.query(UserFeedbackLearningDB).filter(
                UserFeedbackLearningDB.target_match_id == user_id,
                UserFeedbackLearningDB.feedback_type == "dislike"
            ).count()

            skips = db.query(UserFeedbackLearningDB).filter(
                UserFeedbackLearningDB.target_match_id == user_id,
                UserFeedbackLearningDB.feedback_type == "skip"
            ).count()

            total = likes + dislikes + skips
            like_rate = likes / total if total > 0 else 0.5

            # 更新或创建社会认同指标
            metrics = db.query(UserSocialMetricsDB).filter(
                UserSocialMetricsDB.user_id == user_id
            ).first()

            if metrics:
                metrics.like_count = likes
                metrics.dislike_count = dislikes
                metrics.pass_count = skips
                metrics.like_rate = like_rate
                metrics.last_calculated_at = datetime.now()
            else:
                metrics = UserSocialMetricsDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    like_count=likes,
                    dislike_count=dislikes,
                    pass_count=skips,
                    like_rate=like_rate,
                    last_calculated_at=datetime.now()
                )
                db.add(metrics)

            db.commit()

            return {
                "like_rate": like_rate,
                "like_count": likes,
                "total_feedback": total,
            }

    async def generate_social_proof_reasoning(
        self,
        user_id: str
    ) -> Dict:
        """生成社会认同推荐理由"""

        metrics = await self.calculate_social_metrics(user_id)

        elements = []

        if metrics["like_rate"] > 0.7:
            elements.append(f"好评率{int(metrics['like_rate'] * 100)}%，很多人夸TA")

        if metrics["like_count"] > 5:
            elements.append(f"已有{metrics['like_count']}人喜欢TA")

        return {
            "social_proof_elements": elements,
            "like_rate": metrics["like_rate"],
            "confidence_level": "high" if metrics["like_rate"] > 0.8 else "medium"
        }


# ==================== 全局单例 ====================

_quick_start_service: Optional[QuickStartService] = None
_feedback_learning_service: Optional[FeedbackLearningService] = None
_social_proof_service: Optional[SocialProofService] = None


def get_quick_start_service() -> QuickStartService:
    """获取快速入门服务实例"""
    global _quick_start_service
    if _quick_start_service is None:
        _quick_start_service = QuickStartService()
    return _quick_start_service


def get_feedback_learning_service() -> FeedbackLearningService:
    """获取反馈学习服务实例"""
    global _feedback_learning_service
    if _feedback_learning_service is None:
        _feedback_learning_service = FeedbackLearningService()
    return _feedback_learning_service


def get_social_proof_service() -> SocialProofService:
    """获取社会认同服务实例"""
    global _social_proof_service
    if _social_proof_service is None:
        _social_proof_service = SocialProofService()
    return _social_proof_service