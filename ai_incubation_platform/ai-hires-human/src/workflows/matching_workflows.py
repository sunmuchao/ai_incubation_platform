"""
匹配工作流 - 智能匹配和分配工人

支持两种模式：
1. DeerFlow 模式：当 DeerFlow 服务可用时，使用 @workflow 和 @step 装饰器
2. 本地降级模式：当 DeerFlow 不可用时，使用本地 execute 方法
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# 尝试导入 DeerFlow，如果不可用则使用本地模式
try:
    from deerflow import workflow, step
    DEERFLOW_AVAILABLE = True
except ImportError:
    DEERFLOW_AVAILABLE = False
    # 定义本地装饰器占位符
    def workflow(name=None):
        def decorator(cls):
            return cls
        return decorator

    def step(func):
        return func


class SmartMatchingWorkflow:
    """
    智能匹配工作流

    流程：
    1. 分析任务需求
    2. 搜索候选工人
    3. 计算匹配分数
    4. 排序和筛选
    5. 返回匹配结果
    """

    def __init__(self):
        self._context: Dict[str, Any] = {}

    async def analyze_task(self, input_data: Dict) -> Dict:
        """Step 1: 分析任务需求"""
        task_id = input_data.get("task_id")

        if not task_id:
            raise ValueError("task_id is required")

        from tools.task_tools import get_task
        task_result = await get_task(task_id)

        if not task_result.get("found"):
            raise ValueError(f"Task {task_id} not found")

        task_info = task_result.get("task", {})

        # 提取关键需求
        requirements = {
            "task_id": task_id,
            "required_skills": task_info.get("required_skills", {}),
            "location_hint": task_info.get("location_hint"),
            "priority": task_info.get("priority"),
            "reward_amount": task_info.get("reward_amount"),
        }

        self._context["task_requirements"] = requirements

        return requirements

    async def search_candidates(self, step1_result: Dict) -> Dict:
        """Step 2: 搜索候选工人"""
        requirements = step1_result

        # 构建搜索条件
        skills = ",".join(requirements.get("required_skills", {}).keys())
        location = requirements.get("location_hint")

        from tools.worker_tools import search_workers
        search_result = await search_workers(
            skills=skills if skills else None,
            location=location,
            min_level=0,
            min_rating=0.0,
            limit=50  # 获取更多候选
        )

        candidates = search_result.get("workers", [])

        logger.info(f"Found {len(candidates)} candidate workers")

        self._context["candidates"] = candidates

        return {
            "task_id": requirements.get("task_id"),
            "candidates": candidates,
            "total_found": len(candidates)
        }

    async def calculate_scores(self, step2_result: Dict) -> Dict:
        """Step 3: 计算匹配分数"""
        task_id = step2_result.get("task_id")
        candidates = step2_result.get("candidates", [])
        requirements = self._context.get("task_requirements", {})

        scored_candidates = []

        required_skills = set(requirements.get("required_skills", {}).keys())
        task_location = (requirements.get("location_hint") or "").lower()

        for candidate in candidates:
            # 技能匹配分数
            candidate_skills = set((candidate.get("skills") or {}).keys())
            skill_overlap = len(required_skills & candidate_skills)
            skill_score = skill_overlap / len(required_skills) if required_skills else 0.5

            # 地点匹配分数
            location_score = 0.5
            if task_location:
                candidate_location = (candidate.get("location") or "").lower()
                if task_location in candidate_location:
                    location_score = 1.0
                elif candidate_location:
                    location_score = 0.3
            else:
                location_score = 0.7  # 无地点要求时给较高分数

            # 评分分数
            rating = candidate.get("rating", 0)
            rating_score = rating / 5.0 if rating else 0.5

            # 经验分数（基于完成任务数）
            completed_tasks = candidate.get("completed_tasks", 0)
            experience_score = min(completed_tasks / 50.0, 1.0)

            # 等级分数
            level = candidate.get("level", 1)
            level_score = min(level / 10.0, 1.0)

            # 综合分数（加权平均）
            overall_score = (
                skill_score * 0.35 +
                location_score * 0.15 +
                rating_score * 0.25 +
                experience_score * 0.15 +
                level_score * 0.10
            )

            scored_candidates.append({
                "worker_id": candidate.get("id"),
                "worker_name": candidate.get("name"),
                "overall_score": round(overall_score, 3),
                "skill_score": round(skill_score, 3),
                "location_score": round(location_score, 3),
                "rating_score": round(rating_score, 3),
                "experience_score": round(experience_score, 3),
                "level_score": round(level_score, 3),
                "details": {
                    "skills": candidate.get("skills"),
                    "rating": rating,
                    "level": level,
                    "completed_tasks": completed_tasks,
                    "location": candidate.get("location"),
                }
            })

        # 按综合分数排序
        scored_candidates.sort(key=lambda x: x["overall_score"], reverse=True)

        self._context["scored_candidates"] = scored_candidates

        return {
            "task_id": task_id,
            "scored_candidates": scored_candidates,
            "total_scored": len(scored_candidates)
        }

    async def filter_and_rank(self, step3_result: Dict) -> Dict:
        """Step 4: 筛选和排序"""
        scored_candidates = step3_result.get("scored_candidates", [])
        limit = self._context.get("match_limit", 10)

        # 应用筛选规则
        filtered = []
        for candidate in scored_candidates:
            # 过滤低分候选
            if candidate["overall_score"] < 0.3:
                continue

            # 过滤技能完全不匹配的
            if candidate["skill_score"] < 0.2:
                continue

            filtered.append(candidate)

        # 取前 N 名
        top_matches = filtered[:limit]

        # 添加排名
        for i, match in enumerate(top_matches):
            match["rank"] = i + 1
            match["confidence"] = match["overall_score"]  # 置信度等于综合分数

        return {
            "task_id": step3_result.get("task_id"),
            "matches": top_matches,
            "total_candidates": step3_result.get("total_scored"),
            "filtered_count": len(filtered)
        }

    async def generate_recommendations(self, step4_result: Dict) -> Dict:
        """Step 5: 生成推荐建议"""
        matches = step4_result.get("matches", [])

        if not matches:
            return {
                "task_id": step4_result.get("task_id"),
                "matches": [],
                "recommendation": "未找到匹配的工人，建议调整任务要求或提高报酬"
            }

        # 生成推荐建议
        best_match = matches[0]
        recommendations = []

        # 基于最佳匹配的分数构成给出建议
        if best_match["skill_score"] < 0.8:
            recommendations.append(
                "技能匹配度不高，建议明确所需技能或扩大技能范围"
            )

        if best_match["location_score"] < 0.5 and self._context.get("task_requirements", {}).get("location_hint"):
            recommendations.append(
                "地点匹配度较低，建议考虑远程执行或调整地点要求"
            )

        if best_match["rating_score"] < 0.6:
            recommendations.append(
                "候选工人评分普遍不高，建议提高报酬吸引更多优质工人"
            )

        if not recommendations:
            recommendations.append("匹配结果良好，可以继续进行自动分配")

        # 自动分配建议
        auto_assign_recommendation = best_match["overall_score"] >= 0.8

        return {
            "task_id": step4_result.get("task_id"),
            "matches": matches,
            "recommendation": recommendations[0],
            "detailed_recommendations": recommendations,
            "auto_assign_recommended": auto_assign_recommendation,
            "best_match": {
                "worker_id": best_match["worker_id"],
                "worker_name": best_match["worker_name"],
                "confidence": best_match["confidence"]
            }
        }

    async def execute(self, **input_data) -> Dict[str, Any]:
        """执行工作流（本地模式）"""
        try:
            # 设置自定义参数
            self._context["match_limit"] = input_data.get("limit", 10)

            result1 = await self.analyze_task(input_data)
            result2 = await self.search_candidates(result1)
            result3 = await self.calculate_scores(result2)
            result4 = await self.filter_and_rank(result3)
            final_result = await self.generate_recommendations(result4)

            return final_result
        except Exception as e:
            logger.error(f"Matching workflow execution failed: {e}")
            return {
                "matches": [],
                "error": str(e)
            }


# 批量匹配工作流
class BatchMatchingWorkflow:
    """
    批量任务匹配工作流

    用于同时为多个任务匹配工人
    """

    def __init__(self):
        self._context: Dict[str, Any] = {}

    async def validate_tasks(self, input_data: Dict) -> Dict:
        """Step 1: 验证任务列表"""
        task_ids = input_data.get("task_ids", [])

        if not task_ids:
            raise ValueError("task_ids is required")

        valid_tasks = []
        invalid_tasks = []

        from tools.task_tools import get_task

        for task_id in task_ids:
            result = await get_task(task_id)
            if result.get("found"):
                valid_tasks.append(task_id)
            else:
                invalid_tasks.append(task_id)

        return {
            "valid_tasks": valid_tasks,
            "invalid_tasks": invalid_tasks
        }

    async def match_all_tasks(self, step1_result: Dict) -> Dict:
        """Step 2: 为所有有效任务匹配工人"""
        valid_tasks = step1_result.get("valid_tasks", [])

        all_matches = {}

        for task_id in valid_tasks:
            # 重用智能匹配工作流
            matching_workflow = SmartMatchingWorkflow()
            match_result = await matching_workflow.execute(task_id=task_id, limit=5)
            all_matches[task_id] = match_result

        return {
            "matches_by_task": all_matches,
            "total_tasks": len(valid_tasks)
        }

    async def summarize_results(self, step2_result: Dict) -> Dict:
        """Step 3: 汇总结果"""
        matches_by_task = step2_result.get("matches_by_task", {})

        summary = {
            "total_tasks": len(matches_by_task),
            "tasks_with_matches": 0,
            "tasks_without_matches": 0,
            "total_candidates": 0,
        }

        for task_id, match_result in matches_by_task.items():
            matches = match_result.get("matches", [])
            if matches:
                summary["tasks_with_matches"] += 1
                summary["total_candidates"] += len(matches)
            else:
                summary["tasks_without_matches"] += 1

        return {
            "summary": summary,
            "matches_by_task": matches_by_task
        }

    async def execute(self, **input_data) -> Dict[str, Any]:
        """执行工作流（本地模式）"""
        try:
            result1 = await self.validate_tasks(input_data)
            result2 = await self.match_all_tasks(result1)
            final_result = await self.summarize_results(result2)

            return final_result
        except Exception as e:
            logger.error(f"Batch matching workflow execution failed: {e}")
            return {
                "error": str(e)
            }
