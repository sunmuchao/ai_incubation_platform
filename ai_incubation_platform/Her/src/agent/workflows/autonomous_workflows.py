"""
自主匹配工作流

基于 DeerFlow 2.0 的工作流编排，实现 AI 自主匹配、关系分析、破冰助手等功能。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import logger
import json

# 导入原有工具
from agent.tools.autonomous_tools import (
    CompatibilityAnalysisTool,
    TopicSuggestionTool,
    RelationshipTrackingTool
)
from agent.tools.profile_tool import ProfileTool
from agent.tools.match_tool import MatchTool
from agent.tools.reasoning_tool import ReasoningTool
from agent.tools.logging_tool import LoggingTool
from agent.tools.icebreaker_tool import IcebreakerTool

# 导入 Skill 工具（新增）
from agent.tools.skill_tool import (
    EmotionAnalysisTool,
    SafetyGuardianTool,
    SilenceBreakerTool,
    EmotionMediatorTool,
    LoveLanguageTranslatorTool,
    RelationshipProphetTool,
    DateCoachTool,
    DateAssistantTool,
    RelationshipCuratorTool,
    RiskControlTool,
    ShareGrowthTool,
    PerformanceCoachTool,
    ActivityDirectorTool,
    VideoDateCoachTool,
    ConversationMatchmakerTool
)


class NotificationService:
    """
    推送通知服务（模拟实现）

    注：当前为模拟实现，生产环境应对接：
    - 极光推送（JPush）：移动端推送
    - 微信模板消息：微信服务号通知
    - 短信服务：阿里云短信/腾讯云短信
    """

    @staticmethod
    async def push_to_user(user_id: str, title: str, content: str, notification_type: str = "info") -> dict:
        """
        推送通知给用户

        Args:
            user_id: 用户 ID
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型 (info/match/date/reminder)

        Returns:
            推送结果
        """
        logger.info(f"NotificationService: Pushing to user={user_id}, type={notification_type}")
        logger.info(f"  Title: {title}")
        logger.info(f"  Content: {content}")

        # 注：当前仅记录日志，实际推送待对接外部服务
        return {
            "success": True,
            "user_id": user_id,
            "notification_type": notification_type,
            "status": "logged",  # 生产环境应为 "delivered"
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    async def push_to_users(user_ids: List[str], title: str, content: str, notification_type: str = "info") -> dict:
        """批量推送给多个用户"""
        results = []
        for user_id in user_ids:
            result = await NotificationService.push_to_user(user_id, title, content, notification_type)
            results.append(result)

        return {
            "success": True,
            "pushed_count": len(results),
            "results": results
        }


class AutoMatchRecommendWorkflow:
    """
    自主匹配推荐工作流

    流程：
    1. 分析用户状态（单身/活跃）
    2. 扫描候选池
    3. 深度兼容性分析
    4. 匹配度排序
    5. 生成推荐理由
    6. 推送匹配结果
    7. 追踪反馈
    """

    name = "auto_match_recommend"
    description = "AI 自主分析用户画像并推送高质量匹配推荐"

    def __init__(self):
        self.tools = {
            "profile": ProfileTool,
            "match": MatchTool,
            "compatibility": CompatibilityAnalysisTool,
            "reasoning": ReasoningTool,
            "logging": LoggingTool
        }

    def execute(
        self,
        user_id: str,
        limit: int = 5,
        min_score: float = 0.6,
        include_deep_analysis: bool = True
    ) -> dict:
        """
        执行自主匹配推荐工作流

        Args:
            user_id: 用户 ID
            limit: 推荐数量上限
            min_score: 最低匹配度阈值
            include_deep_analysis: 是否包含深度兼容性分析

        Returns:
            匹配推荐结果
        """
        logger.info(f"AutoMatchRecommendWorkflow: Starting for user {user_id}")

        result = {
            "workflow": "auto_match_recommend",
            "user_id": user_id,
            "steps": {},
            "recommendations": [],
            "errors": []
        }

        try:
            # Step 1: 分析用户状态
            logger.info("Step 1: Analyzing user status")
            status_result = self._analyze_user_status(user_id)
            result["steps"]["analyze_status"] = status_result

            if not status_result.get("is_active"):
                result["errors"].append("User is not active for matching")
                return result

            # 开发环境匿名用户：降低匹配分数阈值
            is_anonymous = status_result.get("is_anonymous", False)
            if is_anonymous:
                logger.info("AutoMatchRecommendWorkflow: Anonymous user detected, using relaxed min_score=0.4")
                min_score = 0.4

            # Step 2: 扫描候选池
            logger.info("Step 2: Scanning candidate pool")
            candidates_result = self._scan_candidates(user_id, limit * 3)  # 获取更多候选
            result["steps"]["scan_candidates"] = {
                "candidate_count": len(candidates_result.get("candidates", []))
            }

            if not candidates_result.get("candidates"):
                result["errors"].append("No candidates found")
                return result

            # Step 3: 深度兼容性分析
            if include_deep_analysis:
                logger.info("Step 3: Performing deep compatibility analysis")
                analyzed_candidates = self._deep_compatibility_analysis(
                    user_id,
                    candidates_result["candidates"]
                )
                result["steps"]["compatibility_analysis"] = {
                    "analyzed_count": len(analyzed_candidates)
                }
            else:
                analyzed_candidates = candidates_result["candidates"]

            # Step 4: 匹配度排序
            logger.info("Step 4: Ranking matches")
            ranked_matches = self._rank_matches(analyzed_candidates, min_score)
            result["steps"]["ranking"] = {
                "ranked_count": len(ranked_matches),
                "passed_threshold": len([m for m in ranked_matches if m.get("score", 0) >= min_score])
            }

            # Step 5: 生成推荐理由
            logger.info("Step 5: Generating reasoning")
            matches_with_reasoning = self._generate_reasoning(user_id, ranked_matches[:limit])
            result["steps"]["reasoning_generation"] = {
                "processed_count": len(matches_with_reasoning)
            }

            # Step 6: 记录匹配历史
            logger.info("Step 6: Recording match history")
            logged_count = self._log_matches(user_id, matches_with_reasoning[:3])  # 只记录前 3 个
            result["steps"]["log_record"] = {"logged_count": logged_count}

            # 构建最终结果
            result["recommendations"] = matches_with_reasoning
            result["total"] = len(matches_with_reasoning)
            result["generated_at"] = datetime.now().isoformat()

            logger.info(f"AutoMatchRecommendWorkflow: Completed, found {len(result['recommendations'])} recommendations")

        except Exception as e:
            logger.error(f"AutoMatchRecommendWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result

    def _analyze_user_status(self, user_id: str) -> dict:
        """Step 1: 分析用户状态"""
        # 开发环境的匿名用户，允许匹配
        if user_id == "user-anonymous-dev":
            return {
                "is_active": True,
                "is_anonymous": True,
                "profile_summary": {
                    "age": 25,
                    "gender": "unknown",
                    "location": "unknown",
                    "interests_count": 0
                }
            }

        profile_result = ProfileTool.handle(user_id=user_id)

        if "error" in profile_result:
            # 用户不存在于数据库，按匿名用户处理（开发环境）
            logger.info(f"_analyze_user_status: User {user_id} not found, treating as anonymous user")
            return {
                "is_active": True,
                "is_anonymous": True,
                "profile_summary": {
                    "age": 25,
                    "gender": "unknown",
                    "location": "unknown",
                    "interests_count": 0
                }
            }

        profile = profile_result.get("profile", {})

        # 检查用户是否活跃
        is_active = profile.get("is_active", True)

        # 检查用户是否有匹配意向
        # 注：当前从用户资料中读取匹配意向字段，生产环境应从用户偏好表读取
        # 偏好表应包含：matching_enabled, matching_preferences, deal_breakers 等字段
        has_matching_intent = profile.get("looking_for_relationship", True)  # 简化处理

        return {
            "is_active": is_active and has_matching_intent,
            "profile_summary": {
                "age": profile.get("age"),
                "gender": profile.get("gender"),
                "location": profile.get("location"),
                "interests_count": len(profile.get("interests", []))
            }
        }

    def _scan_candidates(self, user_id: str, limit: int) -> dict:
        """Step 2: 扫描候选池"""
        match_result = MatchTool.handle(user_id=user_id, limit=limit)

        if "error" in match_result:
            return {"candidates": []}

        return {"candidates": match_result.get("matches", [])}

    def _deep_compatibility_analysis(self, user_id: str, candidates: List[dict]) -> List[dict]:
        """Step 3: 深度兼容性分析"""
        analyzed = []

        # 开发环境匿名用户：跳过深度兼容性分析（因为用户不在数据库中）
        if user_id == "user-anonymous-dev":
            logger.info("AutoMatchRecommendWorkflow: Skipping deep analysis for anonymous user")
            # 为每个候选人添加简化的兼容性分析
            for candidate in candidates:
                candidate["compatibility_analysis"] = {
                    "overall_score": candidate.get("score", 0.65),
                    "confidence": 0.5,
                    "dimension_analysis": {
                        "interests": {"score": 0.5, "description": "开发环境简化评估"},
                        "values": {"score": 0.5, "description": "开发环境简化评估"},
                        "age": {"score": 0.8, "description": "年龄匹配度良好"},
                        "location": {"score": 0.3, "description": "地区匹配度一般"}
                    },
                    "potential_conflicts": [],
                    "recommendation": "开发环境简化分析"
                }
                candidate["confidence"] = 0.5
                analyzed.append(candidate)
            return analyzed

        for candidate in candidates:
            candidate_user_id = candidate.get("user_id")
            if not candidate_user_id:
                continue

            # 调用兼容性分析工具
            compat_result = CompatibilityAnalysisTool.handle(
                user_id_1=user_id,
                user_id_2=candidate_user_id,
                dimensions=["interests", "personality", "lifestyle", "goals"]
            )

            if "error" not in compat_result:
                candidate["compatibility_analysis"] = compat_result
                # 使用深度分析分数覆盖原始分数
                candidate["score"] = compat_result.get("overall_score", candidate.get("score", 0.5))
                candidate["confidence"] = compat_result.get("confidence", 0.5)
                analyzed.append(candidate)
            else:
                # 分析失败，保留原始数据
                candidate["confidence"] = 0.5
                analyzed.append(candidate)

        return analyzed

    def _rank_matches(self, candidates: List[dict], min_score: float) -> List[dict]:
        """Step 4: 匹配度排序"""
        # 过滤低于阈值的候选
        filtered = [
            c for c in candidates
            if c.get("score", 0) >= min_score
        ]

        # 按分数降序排序
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)

        return filtered

    def _generate_reasoning(self, user_id: str, matches: List[dict]) -> List[dict]:
        """Step 5: 生成推荐理由"""
        result = []

        for match in matches:
            target_user_id = match.get("user_id")
            if not target_user_id:
                continue

            # 生成匹配解释
            reasoning_result = ReasoningTool.handle(
                user_id=user_id,
                target_user_id=target_user_id,
                score=match.get("score"),
                breakdown=match.get("compatibility_analysis", {}).get("dimension_analysis", {})
            )

            if "error" not in reasoning_result:
                match["reasoning"] = reasoning_result.get("reasoning", "")
                match["match_dimensions"] = reasoning_result.get("match_dimensions", {})
                # 添加 score_breakdown 以便前端展示
                match["score_breakdown"] = reasoning_result.get("match_dimensions", {})
            else:
                # ReasoningTool 失败（如匿名用户），生成简化版推荐理由
                logger.info(f"_generate_reasoning: Using fallback reasoning for {user_id} -> {target_user_id}")
                match["reasoning"] = self._generate_fallback_reasoning(match)
                match["match_dimensions"] = match.get("compatibility_analysis", {}).get("dimension_analysis", {})
                match["score_breakdown"] = match.get("compatibility_analysis", {}).get("dimension_analysis", {})

            # 添加兼容性洞察
            compat_analysis = match.get("compatibility_analysis", {})
            if compat_analysis:
                match["common_interests"] = compat_analysis.get("dimension_analysis", {}).get("interests", {}).get("details", {}).get("common_interests", [])
                match["potential_conflicts"] = compat_analysis.get("potential_conflicts", [])
                match["recommendation"] = compat_analysis.get("recommendation", "")

            result.append(match)

        return result

    def _generate_fallback_reasoning(self, match: dict) -> str:
        """为匿名用户生成简化的推荐理由"""
        user = match.get("user", {})
        score = match.get("score", 0)
        name = user.get("name", "TA")
        interests = user.get("interests", [])
        bio = user.get("bio", "")

        reasoning_parts = [f"{name}是一位值得了解的异性。"]

        # 从兴趣生成理由
        if interests:
            reasoning_parts.append(f"TA 的兴趣爱好包括{interests[0]}等，也许你们有共同话题。")

        # 从简介生成理由
        if bio and len(bio) > 10:
            reasoning_parts.append(f"从简介看，{bio[:30]}... 看起来是个有趣的人。")

        # 从分数生成评价
        if score >= 0.7:
            reasoning_parts.append("你们在多个维度上有不错的匹配度。")
        else:
            reasoning_parts.append("虽然匹配度不是特别高，但缘分往往来自意外的惊喜。")

        return " ".join(reasoning_parts)

    def _log_matches(self, user_id: str, matches: List[dict]) -> int:
        """Step 6: 记录匹配历史"""
        logged_count = 0

        for match in matches:
            target_user_id = match.get("user_id")
            if not target_user_id:
                continue

            log_result = LoggingTool.handle(
                user_id=user_id,
                action="autonomous_match_recommend",
                target_user_id=target_user_id,
                score=match.get("score", 0)
            )

            if "error" not in log_result:
                logged_count += 1

        return logged_count


class RelationshipHealthCheckWorkflow:
    """
    关系健康度分析工作流

    流程：
    1. 收集互动数据
    2. 分析互动质量
    3. 识别关系阶段
    4. 发现潜在问题
    5. 生成改进建议
    6. 推送健康报告
    """

    name = "relationship_health_check"
    description = "AI 自主分析关系健康度并推送改进建议"

    def __init__(self):
        self.tracking_tool = RelationshipTrackingTool

    def execute(
        self,
        match_id: str,
        period: str = "weekly",
        auto_push: bool = True
    ) -> dict:
        """
        执行关系健康度分析工作流

        Args:
            match_id: 匹配记录 ID
            period: 分析周期 (weekly/monthly)
            auto_push: 是否自动推送报告

        Returns:
            关系健康报告
        """
        logger.info(f"RelationshipHealthCheckWorkflow: Analyzing {match_id}, period={period}")

        result = {
            "workflow": "relationship_health_check",
            "match_id": match_id,
            "steps": {},
            "health_report": None,
            "errors": []
        }

        try:
            # Step 1-5: 使用关系追踪工具完成分析
            logger.info("Step 1-5: Running relationship tracking analysis")
            tracking_result = RelationshipTrackingTool.handle(
                match_id=match_id,
                period=period
            )

            if "error" in tracking_result:
                result["errors"].append(tracking_result["error"])
                return result

            result["health_report"] = tracking_result
            result["steps"]["analysis"] = {
                "stage": tracking_result.get("current_stage"),
                "health_score": tracking_result.get("health_score"),
                "issues_count": len(tracking_result.get("potential_issues", [])),
                "recommendations_count": len(tracking_result.get("recommendations", []))
            }

            # Step 6: 推送健康报告
            if auto_push:
                logger.info("Step 6: Pushing health report to users")
                push_result = self._push_health_report(match_id, tracking_result)
                result["steps"]["push_report"] = push_result

            result["completed_at"] = datetime.now().isoformat()

            logger.info(f"RelationshipHealthCheckWorkflow: Completed, health_score={tracking_result.get('health_score', 0)}")

        except Exception as e:
            logger.error(f"RelationshipHealthCheckWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result

    def _push_health_report(self, match_id: str, report: dict) -> dict:
        """Step 6: 推送健康报告给双方用户"""
        user_ids = report.get("user_ids", [])
        health_score = report.get("health_score", 0)

        # 生成推送消息
        if health_score >= 80:
            title = "关系健康报告"
            content = f"你们的關係健康度评分为{health_score}分，状态优秀！点击查看详细分析~"
        elif health_score >= 60:
            title = "关系健康提醒"
            content = f"你们的關係健康度评分为{health_score}分，有一些可以改进的地方~"
        else:
            title = "关系健康预警"
            content = f"你们的關係健康度评分为{health_score}分，建议及时沟通交流~"

        # 使用通知服务推送
        # 注：当前 NotificationService 为模拟实现，生产环境应对接极光推送/微信模板消息
        push_result = {
            "pushed_to": user_ids,
            "push_count": len(user_ids),
            "status": "simulated",  # 生产环境应为 "delivered"
            "notification_service": "NotificationService (mock)"
        }

        logger.info(f"RelationshipHealthCheckWorkflow: Report would be pushed to {user_ids}")

        return push_result


class AutoIcebreakerWorkflow:
    """
    自主破冰助手工作流

    触发条件：
    - 新匹配成功
    - 对话停滞超过 3 天
    - 即将首次约会

    流程：
    1. 检测破冰时机
    2. 分析双方兴趣
    3. 生成话题建议
    4. 个性化推荐
    5. 追踪效果
    """

    name = "auto_icebreaker"
    description = "AI 自主检测破冰时机并推送个性化话题建议"

    def __init__(self):
        self.topic_tool = TopicSuggestionTool
        self.icebreaker_tool = IcebreakerTool

    def execute(
        self,
        match_id: str,
        trigger_type: str = "new_match",
        auto_push: bool = True
    ) -> dict:
        """
        执行破冰助手工作流

        Args:
            match_id: 匹配记录 ID
            trigger_type: 触发类型 (new_match/stale_conversation/upcoming_date)
            auto_push: 是否自动推送建议

        Returns:
            破冰建议结果
        """
        logger.info(f"AutoIcebreakerWorkflow: Analyzing {match_id}, trigger={trigger_type}")

        result = {
            "workflow": "auto_icebreaker",
            "match_id": match_id,
            "trigger_type": trigger_type,
            "steps": {},
            "recommendations": [],
            "errors": []
        }

        try:
            # Step 1: 检测破冰时机
            logger.info("Step 1: Detecting icebreaker timing")
            timing_result = self._detect_timing(match_id, trigger_type)
            result["steps"]["timing_detection"] = timing_result

            if not timing_result.get("should_act"):
                logger.info(f"AutoIcebreakerWorkflow: No action needed for {match_id}")
                result["status"] = "no_action_needed"
                return result

            # Step 2: 分析双方兴趣
            logger.info("Step 2: Analyzing interests")
            interest_analysis = self._analyze_interests(match_id)
            result["steps"]["interest_analysis"] = {
                "common_interests_count": len(interest_analysis.get("common_interests", [])),
                "has_interests": len(interest_analysis.get("common_interests", [])) > 0
            }

            # Step 3: 生成话题建议
            logger.info("Step 3: Generating topic suggestions")
            context = self._determine_context(trigger_type, interest_analysis)
            topics_result = self.topic_tool.handle(
                match_id=match_id,
                context=context,
                count=5
            )

            if "error" in topics_result:
                result["errors"].append(topics_result["error"])
                return result

            result["recommendations"] = topics_result.get("topics", [])
            result["conversation_tips"] = topics_result.get("conversation_tips", [])
            result["steps"]["topic_generation"] = {
                "context": context,
                "topics_count": len(result["recommendations"])
            }

            # Step 4: 个性化推荐
            logger.info("Step 4: Personalizing recommendations")
            personalized = self._personalize_recommendations(
                result["recommendations"],
                interest_analysis
            )
            result["recommendations"] = personalized

            # Step 5: 推送建议
            if auto_push:
                logger.info("Step 5: Pushing recommendations")
                push_result = self._push_recommendations(match_id, personalized)
                result["steps"]["push_recommendations"] = push_result

            result["status"] = "completed"
            result["completed_at"] = datetime.now().isoformat()

            logger.info(f"AutoIcebreakerWorkflow: Completed, generated {len(result['recommendations'])} recommendations")

        except Exception as e:
            logger.error(f"AutoIcebreakerWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result

    def _detect_timing(self, match_id: str, trigger_type: str) -> dict:
        """Step 1: 检测破冰时机"""
        db = None  # 需要从外部传入或创建

        timing_result = {
            "should_act": True,
            "trigger_type": trigger_type,
            "confidence": 0.8
        }

        # 根据不同触发类型判断
        if trigger_type == "new_match":
            # 新匹配，总是需要破冰
            timing_result["reason"] = "新匹配成功，需要破冰"
            timing_result["urgency"] = "high"

        elif trigger_type == "stale_conversation":
            # 对话停滞，需要重新激活
            timing_result["reason"] = "对话停滞，需要重新激活"
            timing_result["urgency"] = "medium"

        elif trigger_type == "upcoming_date":
            # 即将约会，需要话题准备
            timing_result["reason"] = "即将约会，需要话题准备"
            timing_result["urgency"] = "medium"

        return timing_result

    def _analyze_interests(self, match_id: str) -> dict:
        """Step 2: 分析双方兴趣"""
        try:
            from db.database import get_db
            from db.repositories import UserRepository

            db = next(get_db())
            cursor = db.cursor()

            # 获取匹配信息
            cursor.execute("""
                SELECT user_id_1, user_id_2, common_interests
                FROM match_history
                WHERE id = ?
            """, (match_id,))

            row = cursor.fetchone()
            if not row:
                return {"common_interests": [], "error": "Match not found"}

            user_id_1, user_id_2, common_interests_str = row

            # 解析共同兴趣
            common_interests = json.loads(common_interests_str) if common_interests_str else []

            # 获取用户详情
            user_repo = UserRepository(db)
            db_user1 = user_repo.get_by_id(user_id_1)
            db_user2 = user_repo.get_by_id(user_id_2)

            from api.users import _from_db

            result = {
                "common_interests": common_interests,
                "user1_interests": json.loads(db_user1.interests) if db_user1 and db_user1.interests else [],
                "user2_interests": json.loads(db_user2.interests) if db_user2 and db_user2.interests else []
            }

            return result

        except Exception as e:
            logger.error(f"AutoIcebreakerWorkflow: Interest analysis failed: {e}")
            return {"common_interests": [], "error": str(e)}

    def _determine_context(self, trigger_type: str, interest_analysis: dict) -> str:
        """确定话题场景"""
        context_mapping = {
            "new_match": "first_chat",
            "stale_conversation": "follow_up",
            "upcoming_date": "date_plan"
        }
        return context_mapping.get(trigger_type, "first_chat")

    def _personalize_recommendations(self, topics: List[dict], interest_analysis: dict) -> List[dict]:
        """Step 4: 个性化推荐"""
        # 提升基于兴趣的话题优先级
        for topic in topics:
            if topic.get("type") == "interest_based":
                topic["priority"] = "high"
            elif topic.get("type") == "profile_based":
                topic["priority"] = "medium"
            else:
                topic["priority"] = "low"

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        topics.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

        return topics

    def _push_recommendations(self, match_id: str, recommendations: List[dict]) -> dict:
        """Step 5: 推送建议"""
        # 注：当前使用模拟通知服务，生产环境应对接极光推送/微信模板消息
        push_result = {
            "recommendations_count": len(recommendations),
            "status": "simulated",
            "notification_service": "NotificationService (mock)"
        }

        logger.info(f"AutoIcebreakerWorkflow: Would push {len(recommendations)} recommendations")

        return push_result


# 工作流注册函数
def register_autonomous_workflows() -> dict:
    """
    注册所有自主工作流

    Returns:
        工作流字典
    """
    workflows = {
        "auto_match_recommend": AutoMatchRecommendWorkflow,
        "relationship_health_check": RelationshipHealthCheckWorkflow,
        "auto_icebreaker": AutoIcebreakerWorkflow
    }

    logger.info(f"Registered {len(workflows)} autonomous workflows")

    return workflows


# ============= Skill 驱动的工作流（新增） =============

class SkillDrivenWorkflow:
    """
    Skill 驱动的工作流

    使用 AI Native Skill 作为核心能力，实现更智能的自主行为。
    """

    name = "skill_driven_workflow"
    description = "使用 AI Native Skill 驱动的自主工作流"

    def __init__(self):
        self.skill_tools = {
            "emotion_analysis": EmotionAnalysisTool,
            "safety_guardian": SafetyGuardianTool,
            "silence_breaker": SilenceBreakerTool,
            "emotion_mediator": EmotionMediatorTool,
            "relationship_prophet": RelationshipProphetTool,
            "date_coach": DateCoachTool,
            "date_assistant": DateAssistantTool,
            "relationship_curator": RelationshipCuratorTool,
            "activity_director": ActivityDirectorTool,
            "video_date_coach": VideoDateCoachTool,
            "conversation_matchmaker": ConversationMatchmakerTool,
        }

    def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> dict:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            params: Skill 参数

        Returns:
            Skill 执行结果
        """
        if skill_name not in self.skill_tools:
            return {"error": f"Skill not found: {skill_name}"}

        tool = self.skill_tools[skill_name]
        logger.info(f"SkillDrivenWorkflow: Executing skill={skill_name}")

        try:
            result = tool.execute(**params)
            return result
        except Exception as e:
            logger.error(f"SkillDrivenWorkflow: Execution failed: {e}")
            return {"error": str(e)}

    def daily_recommendation_workflow(self, user_id: str) -> dict:
        """
        每日推荐工作流

        使用 ConversationMatchmakerSkill 进行自主推荐
        """
        logger.info(f"DailyRecommendationWorkflow: Running for user={user_id}")

        result = {
            "workflow": "daily_recommendation",
            "user_id": user_id,
            "steps": {},
            "recommendations": [],
            "errors": []
        }

        try:
            # 使用对话式匹配工具
            match_result = ConversationMatchmakerTool.execute(
                user_id=user_id,
                service_type="daily_recommend",
                context={}
            )

            if "error" in match_result:
                result["errors"].append(match_result["error"])
                return result

            result["recommendations"] = match_result.get("matchmaker_result", {}).get("matches", [])
            result["steps"]["conversation_matching"] = {
                "matches_count": len(result["recommendations"])
            }

            logger.info(f"DailyRecommendationWorkflow: Found {len(result['recommendations'])} recommendations")

        except Exception as e:
            logger.error(f"DailyRecommendationWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result

    def relationship_check_workflow(self, user_a_id: str, user_b_id: str) -> dict:
        """
        关系检查工作台流

        使用 PerformanceCoachSkill 进行关系健康度分析
        """
        logger.info(f"RelationshipCheckWorkflow: Running for users={user_a_id},{user_b_id}")

        result = {
            "workflow": "relationship_check",
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "steps": {},
            "health_report": None,
            "errors": []
        }

        try:
            # 使用绩效教练工具进行关系分析
            coach_result = PerformanceCoachTool.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="relationship_assessment",
                context={}
            )

            if "error" in coach_result:
                result["errors"].append(coach_result["error"])
                return result

            result["health_report"] = coach_result.get("coach_result", {}).get("assessment", {})
            result["steps"]["relationship_assessment"] = {
                "health_score": result["health_report"].get("overall_health_score", 0)
            }

            logger.info(f"RelationshipCheckWorkflow: Health score={result['health_report'].get('overall_health_score', 0)}")

        except Exception as e:
            logger.error(f"RelationshipCheckWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result

    def activity_planning_workflow(self, user_id: str, occasion: str = "casual") -> dict:
        """
        活动策划工作台流

        使用 ActivityDirectorSkill 进行活动推荐
        """
        logger.info(f"ActivityPlanningWorkflow: Running for user={user_id}, occasion={occasion}")

        result = {
            "workflow": "activity_planning",
            "user_id": user_id,
            "occasion": occasion,
            "steps": {},
            "recommendations": [],
            "errors": []
        }

        try:
            # 使用活动导演工具
            director_result = ActivityDirectorTool.execute(
                user_id=user_id,
                service_type="activity_planning",
                context={"occasion": occasion}
            )

            if "error" in director_result:
                result["errors"].append(director_result["error"])
                return result

            result["recommendations"] = director_result.get("director_result", {}).get("recommendations", [])
            result["activity_plan"] = director_result.get("director_result", {}).get("activity_plan", {})
            result["steps"]["activity_planning"] = {
                "plan_count": len(result["recommendations"])
            }

            logger.info(f"ActivityPlanningWorkflow: Generated {len(result['recommendations'])} recommendations")

        except Exception as e:
            logger.error(f"ActivityPlanningWorkflow: Failed: {e}")
            result["errors"].append(str(e))

        return result


# 更新工作流注册函数以包含 Skill 驱动的工作流
def register_all_workflows() -> dict:
    """
    注册所有工作流（包括 Skill 驱动的）

    Returns:
        工作流字典
    """
    workflows = {
        "auto_match_recommend": AutoMatchRecommendWorkflow,
        "relationship_health_check": RelationshipHealthCheckWorkflow,
        "auto_icebreaker": AutoIcebreakerWorkflow,
        "skill_driven": SkillDrivenWorkflow
    }

    logger.info(f"Registered {len(workflows)} workflows (including {len(workflows) - 3} Skill-driven)")

    return workflows


# 更新 run_workflow 函数以支持新工作流
async def run_workflow(name: str, **kwargs) -> dict:
    """
    运行指定工作流

    Args:
        name: 工作流名称
        **kwargs: 工作流参数

    Returns:
        工作流执行结果
    """
    workflows = register_all_workflows()

    if name not in workflows:
        return {"error": f"Workflow not found: {name}"}

    workflow_class = workflows[name]
    workflow_instance = workflow_class()

    # 所有工作流都使用 execute 方法
    if hasattr(workflow_instance, 'execute'):
        return workflow_instance.execute(**kwargs)
    else:
        return {"error": f"Workflow {name} does not have execute method"}