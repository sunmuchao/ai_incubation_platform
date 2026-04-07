"""
自主匹配工作流

基于 DeerFlow 2.0 的工作流编排，实现 AI 自主匹配、关系分析、破冰助手等功能。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import logger
import json

# 导入工具
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
        profile_result = ProfileTool.handle(user_id=user_id)

        if "error" in profile_result:
            return {"is_active": False, "error": profile_result["error"]}

        profile = profile_result.get("profile", {})

        # 检查用户是否活跃
        is_active = profile.get("is_active", True)

        # 检查用户是否有匹配意向
        # TODO: 从用户偏好表读取

        return {
            "is_active": is_active,
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

            # 添加兼容性洞察
            compat_analysis = match.get("compatibility_analysis", {})
            if compat_analysis:
                match["common_interests"] = compat_analysis.get("dimension_analysis", {}).get("interests", {}).get("details", {}).get("common_interests", [])
                match["potential_conflicts"] = compat_analysis.get("potential_conflicts", [])
                match["recommendation"] = compat_analysis.get("recommendation", "")

            result.append(match)

        return result

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
        # TODO: 集成推送通知系统
        user_ids = report.get("user_ids", [])

        push_result = {
            "pushed_to": user_ids,
            "push_count": len(user_ids),
            "status": "simulated"  # TODO: 实际推送
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
        # TODO: 集成推送通知系统
        push_result = {
            "recommendations_count": len(recommendations),
            "status": "simulated"
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


# 便捷执行函数
async def run_workflow(name: str, **kwargs) -> dict:
    """
    运行指定工作流

    Args:
        name: 工作流名称
        **kwargs: 工作流参数

    Returns:
        工作流执行结果
    """
    workflows = register_autonomous_workflows()

    if name not in workflows:
        return {"error": f"Workflow not found: {name}"}

    workflow_class = workflows[name]
    workflow_instance = workflow_class()

    # 所有工作流都使用 execute 方法
    if hasattr(workflow_instance, 'execute'):
        return workflow_instance.execute(**kwargs)
    else:
        return {"error": f"Workflow {name} does not have execute method"}