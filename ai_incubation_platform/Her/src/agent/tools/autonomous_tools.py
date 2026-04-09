"""
自主匹配工具集

提供深度兼容性分析、破冰话题推荐、关系追踪等 AI Native 工具。
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from db.database import get_db
from db.repositories import UserRepository
from utils.logger import logger
import json


class CompatibilityAnalysisTool:
    """
    深度兼容性分析工具

    功能：
    - 多维度兼容性分析（性格/价值观/生活方式）
    - 潜在冲突点识别
    - 匹配度置信度评估
    """

    name = "compatibility_analysis"
    description = "深度分析两个用户之间的兼容性，包括性格、价值观和生活方式"
    tags = ["compatibility", "analysis", "matching"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id_1": {
                    "type": "string",
                    "description": "第一个用户 ID"
                },
                "user_id_2": {
                    "type": "string",
                    "description": "第二个用户 ID"
                },
                "dimensions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["personality", "values", "lifestyle", "interests", "goals"]
                    },
                    "description": "分析维度列表",
                    "default": ["personality", "values", "lifestyle"]
                }
            },
            "required": ["user_id_1", "user_id_2"]
        }

    @staticmethod
    def handle(
        user_id_1: str,
        user_id_2: str,
        dimensions: Optional[List[str]] = None
    ) -> dict:
        """
        执行深度兼容性分析

        Args:
            user_id_1: 第一个用户 ID
            user_id_2: 第二个用户 ID
            dimensions: 分析维度列表

        Returns:
            兼容性分析报告
        """
        logger.info(f"CompatibilityAnalysisTool: Analyzing {user_id_1} <-> {user_id_2}")

        if dimensions is None:
            dimensions = ["personality", "values", "lifestyle", "interests"]

        try:
            db = next(get_db())
            user_repo = UserRepository(db)

            db_user1 = user_repo.get_by_id(user_id_1)
            db_user2 = user_repo.get_by_id(user_id_2)

            if not db_user1 or not db_user2:
                return {"error": "User not found"}

            from api.users import _from_db
            user1 = _from_db(db_user1)
            user2 = _from_db(db_user2)

            # 多维度分析
            analysis_results = {}
            overall_score = 0.0
            dimension_count = 0

            for dimension in dimensions:
                if dimension == "interests":
                    score, details = CompatibilityAnalysisTool._analyze_interests(user1, user2)
                elif dimension == "personality":
                    score, details = CompatibilityAnalysisTool._analyze_personality(user1, user2)
                elif dimension == "values":
                    score, details = CompatibilityAnalysisTool._analyze_values(user1, user2)
                elif dimension == "lifestyle":
                    score, details = CompatibilityAnalysisTool._analyze_lifestyle(user1, user2)
                elif dimension == "goals":
                    score, details = CompatibilityAnalysisTool._analyze_goals(user1, user2)
                else:
                    continue

                analysis_results[dimension] = {
                    "score": round(score, 2),
                    "details": details
                }
                overall_score += score
                dimension_count += 1

            # 计算总体兼容性
            if dimension_count > 0:
                overall_score /= dimension_count

            # 识别潜在冲突点
            conflicts = CompatibilityAnalysisTool._identify_conflicts(user1, user2, analysis_results)

            # 生成置信度评分
            confidence = CompatibilityAnalysisTool._calculate_confidence(analysis_results)

            logger.info(f"CompatibilityAnalysisTool: Overall score={overall_score:.2f}, confidence={confidence:.2f}")

            return {
                "user_id_1": user_id_1,
                "user_id_2": user_id_2,
                "overall_score": round(overall_score, 2),
                "confidence": round(confidence, 2),
                "dimension_analysis": analysis_results,
                "potential_conflicts": conflicts,
                "recommendation": CompatibilityAnalysisTool._generate_recommendation(overall_score, conflicts),
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"CompatibilityAnalysisTool: Analysis failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def _analyze_interests(user1, user2) -> tuple:
        """分析兴趣匹配度"""
        interests1 = set(user1.interests) if user1.interests else set()
        interests2 = set(user2.interests) if user2.interests else set()

        if not interests1 or not interests2:
            return 0.5, {"message": "兴趣数据不足"}

        common = interests1 & interests2
        union = interests1 | interests2

        jaccard = len(common) / len(union) if union else 0

        # 考虑兴趣多样性
        diversity_bonus = min(len(common) * 0.05, 0.2)  # 最多加 0.2

        score = min(jaccard + diversity_bonus, 1.0)

        details = {
            "common_interests": list(common),
            "user1_unique": list(interests1 - interests2),
            "user2_unique": list(interests2 - interests1),
            "jaccard_index": round(jaccard, 2),
            "common_count": len(common)
        }

        return score, details

    @staticmethod
    def _analyze_personality(user1, user2) -> tuple:
        """分析性格匹配度"""
        # 注意：当前数据库中没有存储性格数据 (personality_traits)
        # 使用基于兴趣和行为的推断方式

        # 基于兴趣和行为模式推断
        db = next(get_db())

        # 分析兴趣匹配作为性格代理
        interests1 = set(user1.interests) if user1.interests else set()
        interests2 = set(user2.interests) if user2.interests else set()

        if not interests1 or not interests2:
            # 没有兴趣数据，返回默认值
            return 0.5, {"message": "性格数据不足，使用默认匹配", "has_personality_data": False}

        common = interests1 & interests2
        union = interests1 | interests2

        jaccard = len(common) / len(union) if union else 0

        # 考虑兴趣多样性
        diversity_bonus = min(len(common) * 0.05, 0.2)

        score = min(jaccard + diversity_bonus, 1.0)

        details = {
            "common_interests": list(common),
            "interest_overlap_score": round(jaccard, 2),
            "inferred_from_interests": True,
            "has_personality_data": False
        }

        return score, details

    @staticmethod
    def _infer_personality_from_behavior(user1, user2) -> tuple:
        """从行为推断性格匹配度"""
        # 基于兴趣和行为模式推断
        db = next(get_db())

        # 分析活动参与模式
        from db.models import BehaviorEventDB
        from sqlalchemy import func

        behavior_patterns = db.query(
            BehaviorEventDB.event_type, func.count().label('count')
        ).filter(
            BehaviorEventDB.user_id.in_([user1.id, user2.id])
        ).group_by(
            BehaviorEventDB.event_type
        ).all()

        if not behavior_patterns:
            return 0.5, {"message": "行为数据不足", "has_personality_data": False}

        # 简单推断：活跃用户更外向
        details = {
            "inferred_from_behavior": True,
            "has_personality_data": False
        }

        return 0.6, details

    @staticmethod
    def _analyze_values(user1, user2) -> tuple:
        """分析价值观匹配度"""
        values1 = set(json.loads(user1.values)) if user1.values else set()
        values2 = set(json.loads(user2.values)) if user2.values else set()

        if not values1 or not values2:
            return 0.5, {"message": "价值观数据不足"}

        common_values = values1 & values2
        all_values = values1 | values2

        score = len(common_values) / len(all_values) if all_values else 0

        details = {
            "common_values": list(common_values),
            "total_values_compared": len(all_values)
        }

        return score, details

    @staticmethod
    def _analyze_lifestyle(user1, user2) -> tuple:
        """分析生活方式匹配度"""
        score = 0.5
        details = {}

        # 位置距离
        from agent.tools.geo_tool import GeoService
        distance = GeoService.calculate_distance(user1.location, user2.location)
        if distance is not None:
            if distance < 5:
                details["distance_bonus"] = 0.2
                score += 0.2
            elif distance < 20:
                details["distance_bonus"] = 0.1
                score += 0.1

        # 年龄差距
        age_diff = abs(user1.age - user2.age)
        if age_diff <= 3:
            details["age_compatibility"] = "excellent"
            score += 0.15
        elif age_diff <= 5:
            details["age_compatibility"] = "good"
            score += 0.1
        elif age_diff <= 10:
            details["age_compatibility"] = "acceptable"
            score += 0.05
        else:
            details["age_compatibility"] = "large_gap"

        details["age_difference"] = age_diff
        details["distance_km"] = round(distance, 1) if distance else None

        return min(score, 1.0), details

    @staticmethod
    def _analyze_goals(user1, user2) -> tuple:
        """分析目标匹配度"""
        # 从用户目标字段分析
        goal1 = getattr(user1, 'goal', None) if hasattr(user1, 'goal') else None
        goal2 = getattr(user2, 'goal', None) if hasattr(user2, 'goal') else None

        if not goal1 or not goal2:
            return 0.5, {"message": "目标数据不足"}

        goal_alignment = {
            ("serious", "serious"): 1.0,
            ("casual", "casual"): 1.0,
            ("serious", "casual"): 0.3,
            ("casual", "serious"): 0.3,
        }

        score = goal_alignment.get((goal1, goal2), 0.5)

        details = {
            "user1_goal": goal1,
            "user2_goal": goal2,
            "aligned": goal1 == goal2
        }

        return score, details

    @staticmethod
    def _identify_conflicts(user1, user2, analysis: dict) -> List[dict]:
        """识别潜在冲突点"""
        conflicts = []

        # 检查生活方式冲突
        if "lifestyle" in analysis:
            lifestyle = analysis["lifestyle"]
            if lifestyle.get("details", {}).get("age_compatibility") == "large_gap":
                conflicts.append({
                    "type": "age_gap",
                    "severity": "medium",
                    "description": "年龄差距较大，可能存在代沟"
                })

        # 检查目标冲突
        if "goals" in analysis:
            goals = analysis["goals"]
            if not goals.get("details", {}).get("aligned", True):
                conflicts.append({
                    "type": "goal_mismatch",
                    "severity": "high",
                    "description": "双方关系目标不一致"
                })

        # 检查兴趣冲突
        if "interests" in analysis:
            interests = analysis["interests"]
            if interests.get("details", {}).get("common_count", 0) == 0:
                conflicts.append({
                    "type": "no_common_interests",
                    "severity": "low",
                    "description": "没有共同兴趣，可能需要更多探索"
                })

        return conflicts

    @staticmethod
    def _calculate_confidence(analysis: dict) -> float:
        """计算分析结果的置信度"""
        confidence = 0.5  # 基础置信度

        # 维度越多，置信度越高
        dimension_count = len(analysis)
        confidence += min(dimension_count * 0.1, 0.3)

        # 检查数据完整性
        has_data_issues = False
        for dim_name, dim_result in analysis.items():
            if dim_result.get("score", 0) == 0.5 and "数据不足" in str(dim_result.get("details", {})):
                has_data_issues = True
                break

        if has_data_issues:
            confidence -= 0.2

        return max(min(confidence, 1.0), 0.0)

    @staticmethod
    def _generate_recommendation(overall_score: float, conflicts: List[dict]) -> str:
        """生成匹配建议"""
        if overall_score >= 0.8:
            base_rec = "强烈推荐匹配"
        elif overall_score >= 0.6:
            base_rec = "推荐匹配"
        elif overall_score >= 0.4:
            base_rec = "可尝试接触"
        else:
            base_rec = "匹配度较低"

        if conflicts:
            high_severity = [c for c in conflicts if c.get("severity") == "high"]
            if high_severity:
                base_rec += f"（注意：{len(high_severity)}个高风险冲突）"

        return base_rec


class TopicSuggestionTool:
    """
    破冰话题推荐工具

    基于匹配双方的特征和互动历史，智能推荐对话话题。
    """

    name = "topic_suggestion"
    description = "基于匹配双方特征推荐破冰话题和对话建议"
    tags = ["icebreaker", "topics", "conversation"]

    # 扩展话题库
    TOPIC_CATEGORIES = {
        "first_chat": [
            "最近有什么让你特别兴奋的事情吗？",
            "如果用三个词形容自己，你会选哪三个？",
            "你理想中的周末是怎样的？",
            "有什么电影/剧集最近让你印象深刻？",
        ],
        "follow_up": [
            "上次你说的那个事情后来怎么样了？",
            "最近有尝试我之前推荐的那个吗？",
            "这周有什么特别的计划吗？",
        ],
        "date_plan": [
            "你更喜欢户外活动还是室内活动？",
            "有没有一直想去的餐厅？",
            "周末有空的话，要不要一起...?",
        ],
        "deep_connection": [
            "你人生中最重要的转折点是什么？",
            "有什么事情是你特别坚持的？",
            "你对未来的期待是什么？",
        ]
    }

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "string",
                    "description": "匹配记录 ID"
                },
                "context": {
                    "type": "string",
                    "description": "话题场景",
                    "enum": ["first_chat", "follow_up", "date_plan", "deep_connection"],
                    "default": "first_chat"
                },
                "count": {
                    "type": "integer",
                    "description": "推荐话题数量",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["match_id"]
        }

    @staticmethod
    def handle(
        match_id: str,
        context: str = "first_chat",
        count: int = 5
    ) -> dict:
        """
        生成话题建议

        Args:
            match_id: 匹配记录 ID
            context: 话题场景
            count: 推荐数量

        Returns:
            话题建议列表
        """
        logger.info(f"TopicSuggestionTool: Generating topics for {match_id}, context={context}")

        try:
            db = next(get_db())

            # 获取匹配记录
            from db.models import MatchHistoryDB
            match_record = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()

            if not match_record:
                return {"error": "Match not found"}

            user_id_1 = match_record.user_id_1
            user_id_2 = match_record.user_id_2
            common_interests_str = match_record.common_interests
            relationship_stage = match_record.relationship_stage

            # 获取用户信息
            user_repo = UserRepository(db)
            db_user1 = user_repo.get_by_id(user_id_1)
            db_user2 = user_repo.get_by_id(user_id_2)

            if not db_user1 or not db_user2:
                return {"error": "User not found"}

            from api.users import _from_db
            user1 = _from_db(db_user1)
            user2 = _from_db(db_user2)

            # 解析共同兴趣
            common_interests = json.loads(common_interests_str) if common_interests_str else []

            # 获取基础话题
            base_topics = TopicSuggestionTool.TOPIC_CATEGORIES.get(context, [])

            # 生成个性化话题
            personalized_topics = []

            # 1. 基于共同兴趣的话题
            for interest in common_interests[:3]:
                topic = TopicSuggestionTool._generate_interest_topic(interest, context)
                if topic:
                    personalized_topics.append({
                        "topic": topic,
                        "type": "interest_based",
                        "context": f"基于共同兴趣：{interest}",
                        "confidence": 0.9
                    })

            # 2. 基于用户画像的话题
            profile_topics = TopicSuggestionTool._generate_profile_topics(user1, user2, context)
            personalized_topics.extend(profile_topics)

            # 3. 通用话题补充
            while len(personalized_topics) < count and base_topics:
                topic = base_topics[len(personalized_topics) % len(base_topics)]
                personalized_topics.append({
                    "topic": topic,
                    "type": "general",
                    "context": f"{TopicSuggestionTool._get_context_name(context)}场景",
                    "confidence": 0.6
                })

            # 生成对话策略建议
            tips = TopicSuggestionTool._generate_conversation_tips(
                user1, user2, common_interests, context
            )

            logger.info(f"TopicSuggestionTool: Generated {len(personalized_topics)} topics")

            return {
                "match_id": match_id,
                "context": context,
                "topics": personalized_topics[:count],
                "conversation_tips": tips,
                "common_interests": common_interests,
                "relationship_stage": relationship_stage
            }

        except Exception as e:
            logger.error(f"TopicSuggestionTool: Failed to generate topics: {e}")
            return {"error": str(e)}

    @staticmethod
    def _generate_interest_topic(interest: str, context: str) -> str:
        """基于兴趣生成话题"""
        templates = {
            "旅行": f"看到你也喜欢旅行，最近有去哪里玩吗？",
            "美食": f"你也是美食爱好者啊，有什么推荐的好吃的地方吗？",
            "音乐": f"最近有听什么好听的歌吗？求推荐！",
            "电影": f"最近有看什么好电影吗？我正愁剧荒呢",
            "健身": f"你平时喜欢在哪里健身？有什么推荐的课程吗？",
            "阅读": f"最近有读什么好书吗？我正在找新书看",
        }

        return templates.get(interest, f"看到你也喜欢{interest}，有什么心得可以分享吗？")

    @staticmethod
    def _generate_profile_topics(user1, user2, context: str) -> List[dict]:
        """基于用户画像生成话题"""
        topics = []

        # 基于 bio 生成话题
        if user1.bio and user2.bio:
            topics.append({
                "topic": "感觉你们的个人简介都很有意思，能聊聊背后的故事吗？",
                "type": "profile_based",
                "context": "基于个人简介",
                "confidence": 0.7
            })

        # 基于位置生成话题
        if user1.location and user2.location:
            if user1.location == user2.location:
                topics.append({
                    "topic": f"你们都在{user1.location}，有什么本地人推荐的好去处吗？",
                    "type": "location_based",
                    "context": "基于共同位置",
                    "confidence": 0.8
                })

        return topics

    @staticmethod
    def _get_context_name(context: str) -> str:
        """获取场景中文名"""
        names = {
            "first_chat": "初次聊天",
            "follow_up": "后续跟进",
            "date_plan": "约会计划",
            "deep_connection": "深度交流"
        }
        return names.get(context, "通用")

    @staticmethod
    def _generate_conversation_tips(user1, user2, common_interests: List[str], context: str) -> List[str]:
        """生成对话建议"""
        tips = []

        if common_interests:
            tips.append(f"可以从共同的兴趣 '{common_interests[0]}' 开始聊起")

        if context == "first_chat":
            tips.extend([
                "保持真诚和好奇心，不要急于表现自己",
                "问开放式问题，鼓励对方分享更多",
                "注意对方的回应节奏，不要连续发问"
            ])
        elif context == "follow_up":
            tips.extend([
                "回顾上次对话的关键点，显示你在认真倾听",
                "分享自己的近况，保持互动平衡",
                "如果对方回复慢，不要过度追问"
            ])
        elif context == "date_plan":
            tips.extend([
                "提出具体的时间和地点建议",
                "考虑对方的兴趣和偏好",
                "准备好备选方案"
            ])

        return tips


class RelationshipTrackingTool:
    """
    关系追踪工具

    追踪关系进展，分析互动质量，识别关系阶段。
    """

    name = "relationship_tracking"
    description = "追踪匹配关系进展，分析互动质量和关系健康度"
    tags = ["relationship", "tracking", "health"]

    # 关系阶段定义
    RELATIONSHIP_STAGES = {
        "matched": {"order": 1, "name": "匹配成功"},
        "chatting": {"order": 2, "name": "聊天中"},
        "exchanged_contacts": {"order": 3, "name": "交换联系方式"},
        "first_date": {"order": 4, "name": "首次约会"},
        "dating": {"order": 5, "name": "交往中"},
        "in_relationship": {"order": 6, "name": "确定关系"},
    }

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "string",
                    "description": "匹配记录 ID"
                },
                "period": {
                    "type": "string",
                    "description": "分析周期",
                    "enum": ["weekly", "monthly"],
                    "default": "weekly"
                }
            },
            "required": ["match_id"]
        }

    @staticmethod
    def handle(
        match_id: str,
        period: str = "weekly"
    ) -> dict:
        """
        追踪关系进展

        Args:
            match_id: 匹配记录 ID
            period: 分析周期

        Returns:
            关系进展报告
        """
        logger.info(f"RelationshipTrackingTool: Tracking {match_id}, period={period}")

        try:
            db = next(get_db())

            # 获取匹配记录
            from db.models import MatchHistoryDB
            match_record = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()

            if not match_record:
                return {"error": "Match not found"}

            user_id_1 = match_record.user_id_1
            user_id_2 = match_record.user_id_2
            current_stage = match_record.relationship_stage
            created_at = match_record.created_at

            # 收集互动数据
            interactions = RelationshipTrackingTool._collect_interactions(
                db, user_id_1, user_id_2, period
            )

            # 分析互动质量
            quality_analysis = RelationshipTrackingTool._analyze_interaction_quality(interactions)

            # 识别当前关系阶段
            identified_stage = RelationshipTrackingTool._identify_stage(
                current_stage, interactions, quality_analysis
            )

            # 发现潜在问题
            issues = RelationshipTrackingTool._detect_issues(interactions, quality_analysis)

            # 生成改进建议
            advice = RelationshipTrackingTool._generate_advice(identified_stage, issues)

            # 计算关系健康度
            health_score = RelationshipTrackingTool._calculate_health_score(
                quality_analysis, issues
            )

            logger.info(f"RelationshipTrackingTool: Health score={health_score:.2f}, stage={identified_stage}")

            return {
                "match_id": match_id,
                "user_ids": [user_id_1, user_id_2],
                "period": period,
                "current_stage": identified_stage,
                "health_score": round(health_score, 2),
                "interaction_summary": {
                    "total_messages": interactions.get("message_count", 0),
                    "avg_response_time_hours": interactions.get("avg_response_time_hours", None),
                    "active_days": interactions.get("active_days", 0)
                },
                "quality_analysis": quality_analysis,
                "potential_issues": issues,
                "recommendations": advice,
                "tracked_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"RelationshipTrackingTool: Tracking failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def _collect_interactions(db, user_id_1: str, user_id_2: str, period: str) -> dict:
        """收集互动数据"""
        from db.models import ChatMessageDB
        from sqlalchemy import func, distinct, or_

        # 计算时间范围
        days = 7 if period == "weekly" else 30
        since = datetime.now() - timedelta(days=days)

        # 获取消息数量
        message_count = db.query(ChatMessageDB).filter(
            or_(
                (ChatMessageDB.sender_id == user_id_1) & (ChatMessageDB.receiver_id == user_id_2),
                (ChatMessageDB.sender_id == user_id_2) & (ChatMessageDB.receiver_id == user_id_1)
            ),
            ChatMessageDB.created_at >= since
        ).count()

        # 获取活跃天数
        active_days = db.query(func.count(func.distinct(func.date(ChatMessageDB.created_at)))).filter(
            or_(
                (ChatMessageDB.sender_id == user_id_1) & (ChatMessageDB.receiver_id == user_id_2),
                (ChatMessageDB.sender_id == user_id_2) & (ChatMessageDB.receiver_id == user_id_1)
            ),
            ChatMessageDB.created_at >= since
        ).scalar()

        # 获取平均响应时间（简化版本）
        avg_response_time = None

        return {
            "message_count": message_count,
            "active_days": active_days,
            "avg_response_time_hours": avg_response_time,
            "period_days": days
        }

    @staticmethod
    def _analyze_interaction_quality(interactions: dict) -> dict:
        """分析互动质量"""
        quality = {
            "frequency": "low",
            "consistency": "unknown",
            "engagement": "unknown"
        }

        message_count = interactions.get("message_count", 0)
        active_days = interactions.get("active_days", 0)
        period_days = interactions.get("period_days", 7)

        # 频率评估
        if message_count > 50:
            quality["frequency"] = "high"
        elif message_count > 20:
            quality["frequency"] = "medium"
        elif message_count > 5:
            quality["frequency"] = "low"
        else:
            quality["frequency"] = "very_low"

        # 一致性评估
        if active_days > 0:
            activity_ratio = active_days / period_days
            if activity_ratio > 0.7:
                quality["consistency"] = "high"
            elif activity_ratio > 0.4:
                quality["consistency"] = "medium"
            else:
                quality["consistency"] = "low"

        # 参与度评估（简化）
        if quality["frequency"] in ["high", "medium"] and quality["consistency"] in ["high", "medium"]:
            quality["engagement"] = "high"
        elif quality["frequency"] == "very_low":
            quality["engagement"] = "low"
        else:
            quality["engagement"] = "medium"

        return quality

    @staticmethod
    def _identify_stage(current_stage: str, interactions: dict, quality: dict) -> str:
        """识别当前关系阶段"""
        stage_order = RelationshipTrackingTool.RELATIONSHIP_STAGES.get(
            current_stage, {"order": 1}
        )["order"]

        message_count = interactions.get("message_count", 0)
        active_days = interactions.get("active_days", 0)

        # 基于互动数据判断是否应该升级阶段
        if stage_order <= 2:  # matched 或 chatting
            if message_count > 100 and active_days >= 7:
                return "chatting"
            elif message_count > 50:
                return "chatting"

        return current_stage

    @staticmethod
    def _detect_issues(interactions: dict, quality: dict) -> List[dict]:
        """发现潜在问题"""
        issues = []

        # 检查互动频率
        if quality.get("frequency") == "very_low":
            issues.append({
                "type": "low_interaction",
                "severity": "high",
                "description": "互动频率过低，关系可能停滞"
            })

        # 检查一致性
        if quality.get("consistency") == "low":
            issues.append({
                "type": "inconsistent_communication",
                "severity": "medium",
                "description": "沟通不规律，可能缺乏兴趣"
            })

        # 检查消息数量但活跃天数少
        message_count = interactions.get("message_count", 0)
        active_days = interactions.get("active_days", 0)
        if message_count > 20 and active_days <= 2:
            issues.append({
                "type": "burst_then_silent",
                "severity": "medium",
                "description": "集中聊天后长时间沉默"
            })

        return issues

    @staticmethod
    def _generate_advice(stage: str, issues: List[dict]) -> List[str]:
        """生成改进建议"""
        advice = []

        # 基于阶段的建议
        if stage == "matched":
            advice.append("尽快发起第一次对话，不要超过 24 小时")
        elif stage == "chatting":
            advice.append("保持稳定的沟通频率，尝试深入了解对方")
        elif stage == "first_date":
            advice.append("安排一个轻松的活动，不要给双方太大压力")

        # 基于问题的建议
        for issue in issues:
            if issue["type"] == "low_interaction":
                advice.append("主动分享日常生活，创造话题机会")
            elif issue["type"] == "inconsistent_communication":
                advice.append("建立规律的沟通习惯，如每天晚安")

        return advice

    @staticmethod
    def _calculate_health_score(quality: dict, issues: List[dict]) -> float:
        """计算关系健康度"""
        score = 0.5  # 基础分

        # 质量加分
        frequency_scores = {"high": 0.3, "medium": 0.2, "low": 0.1, "very_low": -0.1}
        consistency_scores = {"high": 0.2, "medium": 0.1, "low": -0.1}

        score += frequency_scores.get(quality.get("frequency", "low"), 0)
        score += consistency_scores.get(quality.get("consistency", "low"), 0)

        # 问题减分
        for issue in issues:
            severity = issue.get("severity", "medium")
            if severity == "high":
                score -= 0.2
            elif severity == "medium":
                score -= 0.1

        return max(min(score, 1.0), 0.0)


# 工具注册函数
def register_autonomous_tools(registry) -> None:
    """
    注册所有自主匹配工具到工具注册表

    Args:
        registry: ToolRegistry 实例
    """
    # 注册兼容性分析工具
    registry.register(
        name="compatibility_analysis",
        handler=CompatibilityAnalysisTool.handle,
        description="深度分析两个用户之间的兼容性，包括性格、价值观和生活方式",
        input_schema=CompatibilityAnalysisTool.get_input_schema(),
        tags=["compatibility", "analysis", "matching"]
    )

    # 注册话题推荐工具
    registry.register(
        name="topic_suggestion",
        handler=TopicSuggestionTool.handle,
        description="基于匹配双方特征推荐破冰话题和对话建议",
        input_schema=TopicSuggestionTool.get_input_schema(),
        tags=["icebreaker", "topics", "conversation"]
    )

    # 注册关系追踪工具
    registry.register(
        name="relationship_tracking",
        handler=RelationshipTrackingTool.handle,
        description="追踪匹配关系进展，分析互动质量和关系健康度",
        input_schema=RelationshipTrackingTool.get_input_schema(),
        tags=["relationship", "tracking", "health"]
    )

    logger.info("Autonomous tools registered successfully")