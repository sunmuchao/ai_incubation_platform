"""
团队匹配服务 - v1.16 新增核心功能。

核心功能：
1. 批量任务与团队自动匹配
2. 团队自动组建（基于技能互补）
3. 多角色协同匹配
4. 项目分解与团队分配
5. 团队绩效评估
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TeamMatchStatus(Enum):
    """团队匹配状态。"""
    PENDING = "pending"
    MATCHING = "matching"
    MATCHED = "matched"
    TEAM_FORMED = "team_formed"
    FAILED = "failed"


class MemberRole(Enum):
    """团队成员角色类型。"""
    LEADER = "leader"  # 团队负责人
    DEVELOPER = "developer"  # 开发者
    DESIGNER = "designer"  # 设计师
    ANALYST = "analyst"  # 分析师
    REVIEWER = "reviewer"  # 审核员
    SPECIALIST = "specialist"  # 专家/特殊技能


@dataclass
class WorkerProfile:
    """工人画像（用于匹配）。"""
    worker_id: str
    skills: Dict[str, float] = field(default_factory=dict)  # skill_name -> proficiency (0-1)
    availability: float = 1.0  # 可用性 (0-1)
    reputation_score: float = 0.5  # 信誉评分 (0-1)
    completed_tasks: int = 0
    success_rate: float = 0.0
    preferred_roles: List[str] = field(default_factory=list)
    hourly_rate: float = 0.0
    max_workload: int = 5  # 最大同时任务数
    current_workload: int = 0

    def get_available_capacity(self) -> int:
        """获取可用工作容量。"""
        return max(0, self.max_workload - self.current_workload)

    def get_composite_score(self) -> float:
        """计算综合评分（用于排序）。"""
        return (
            self.reputation_score * 0.3 +
            self.success_rate * 0.3 +
            self.availability * 0.2 +
            min(1.0, self.completed_tasks / 100) * 0.2
        )


@dataclass
class TaskRequirement:
    """任务需求。"""
    task_id: str
    required_skills: Dict[str, float]  # skill_name -> min_proficiency
    preferred_role: Optional[str] = None
    estimated_effort: int = 1  # 预估工作量单位
    priority: int = 1  # 优先级 (1-5, 5 最高)
    deadline: Optional[datetime] = None


@dataclass
class MatchResult:
    """匹配结果。"""
    task_id: str
    matched_workers: List[str]  # worker_id 列表
    match_scores: Dict[str, float]  # worker_id -> match_score
    match_reason: str
    confidence: float  # 匹配置信度 (0-1)


@dataclass
class TeamComposition:
    """团队组成。"""
    team_id: str
    project_id: str
    members: Dict[str, str]  # worker_id -> role
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    total_reputation: float = 0.0
    skill_coverage: Dict[str, float] = field(default_factory=dict)


@dataclass
class TeamPerformance:
    """团队绩效。"""
    team_id: str
    completed_projects: int = 0
    success_rate: float = 0.0
    average_delivery_time: float = 0.0  # 平均交付时间（小时）
    client_satisfaction: float = 0.0
    member_satisfaction: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class TeamMatchingService:
    """
    团队匹配服务。

    提供以下核心能力：
    1. 基于技能的任务 - 工人匹配
    2. 批量任务智能分配
    3. 团队自动组建（技能互补）
    4. 多角色协同匹配
    5. 团队绩效评估
    """

    def __init__(self):
        # 内存存储（生产环境应使用数据库）
        self._worker_profiles: Dict[str, WorkerProfile] = {}
        self._task_requirements: Dict[str, TaskRequirement] = {}
        self._match_results: Dict[str, MatchResult] = {}
        self._team_compositions: Dict[str, TeamComposition] = {}
        self._team_performances: Dict[str, TeamPerformance] = {}
        self._match_history: List[Dict[str, Any]] = []

    # ==================== 工人画像管理 ====================

    def register_worker(
        self,
        worker_id: str,
        skills: Dict[str, float],
        preferred_roles: Optional[List[str]] = None,
        hourly_rate: float = 0.0,
        max_workload: int = 5,
    ) -> WorkerProfile:
        """注册/更新工人画像。"""
        profile = WorkerProfile(
            worker_id=worker_id,
            skills=skills,
            preferred_roles=preferred_roles or [],
            hourly_rate=hourly_rate,
            max_workload=max_workload,
        )
        self._worker_profiles[worker_id] = profile
        logger.info(f"Worker profile registered: {worker_id}, skills: {list(skills.keys())}")
        return profile

    def update_worker_stats(
        self,
        worker_id: str,
        completed_tasks: Optional[int] = None,
        success_rate: Optional[float] = None,
        reputation_score: Optional[float] = None,
    ) -> Optional[WorkerProfile]:
        """更新工人统计数据。"""
        profile = self._worker_profiles.get(worker_id)
        if not profile:
            return None

        if completed_tasks is not None:
            profile.completed_tasks = completed_tasks
        if success_rate is not None:
            profile.success_rate = max(0, min(1, success_rate))
        if reputation_score is not None:
            profile.reputation_score = max(0, min(1, reputation_score))

        return profile

    def update_workload(self, worker_id: str, delta: int) -> bool:
        """更新工人工作负载。"""
        profile = self._worker_profiles.get(worker_id)
        if not profile:
            return False

        profile.current_workload = max(0, profile.current_workload + delta)
        profile.availability = max(0, 1.0 - (profile.current_workload / profile.max_workload))
        return True

    def get_worker_profile(self, worker_id: str) -> Optional[WorkerProfile]:
        """获取工人画像。"""
        return self._worker_profiles.get(worker_id)

    def list_available_workers(
        self,
        min_availability: float = 0.5,
        limit: int = 100,
    ) -> List[WorkerProfile]:
        """获取可用工人列表。"""
        available = [
            p for p in self._worker_profiles.values()
            if p.availability >= min_availability and p.get_available_capacity() > 0
        ]
        # 按综合评分排序
        available.sort(key=lambda p: p.get_composite_score(), reverse=True)
        return available[:limit]

    # ==================== 任务需求管理 ====================

    def define_task_requirement(
        self,
        task_id: str,
        required_skills: Dict[str, float],
        preferred_role: Optional[str] = None,
        estimated_effort: int = 1,
        priority: int = 1,
        deadline: Optional[datetime] = None,
    ) -> TaskRequirement:
        """定义任务需求。"""
        requirement = TaskRequirement(
            task_id=task_id,
            required_skills=required_skills,
            preferred_role=preferred_role,
            estimated_effort=estimated_effort,
            priority=priority,
            deadline=deadline,
        )
        self._task_requirements[task_id] = requirement
        return requirement

    def get_task_requirement(self, task_id: str) -> Optional[TaskRequirement]:
        """获取任务需求。"""
        return self._task_requirements.get(task_id)

    # ==================== 核心匹配算法 ====================

    def match_worker_to_task(
        self,
        task_id: str,
        candidate_workers: Optional[List[str]] = None,
    ) -> Optional[MatchResult]:
        """
        为任务匹配最合适的工人。

        匹配逻辑：
        1. 技能匹配度（必需技能 >= 要求阈值）
        2. 角色偏好匹配
        3. 可用性检查
        4. 综合评分排序
        """
        requirement = self._task_requirements.get(task_id)
        if not requirement:
            return None

        # 获取候选工人
        if candidate_workers:
            candidates = [
                self._worker_profiles.get(wid)
                for wid in candidate_workers
            ]
            candidates = [p for p in candidates if p is not None]
        else:
            candidates = list(self._worker_profiles.values())

        # 过滤和评分
        scored_candidates = []
        for profile in candidates:
            # 检查可用性
            if profile.get_available_capacity() < requirement.estimated_effort:
                continue

            # 检查技能匹配
            skill_match, skill_score = self._calculate_skill_match(profile, requirement.required_skills)
            if not skill_match:
                continue

            # 角色偏好加分
            role_bonus = 0.1 if requirement.preferred_role in profile.preferred_roles else 0.0

            # 计算最终匹配分
            match_score = (
                skill_score * 0.5 +
                profile.get_composite_score() * 0.4 +
                role_bonus * 0.1
            )

            scored_candidates.append((profile, match_score))

        if not scored_candidates:
            return MatchResult(
                task_id=task_id,
                matched_workers=[],
                match_scores={},
                match_reason="No qualified workers available",
                confidence=0.0,
            )

        # 按匹配分排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # 选择最佳匹配
        best_profile, best_score = scored_candidates[0]

        result = MatchResult(
            task_id=task_id,
            matched_workers=[best_profile.worker_id],
            match_scores={best_profile.worker_id: best_score},
            match_reason=f"Best skill match ({best_score:.2f}) with {len(requirement.required_skills)} required skills",
            confidence=min(1.0, best_score),
        )

        self._match_results[task_id] = result
        self._record_match_history(task_id, [best_profile.worker_id], "single_task_match")

        return result

    def match_team_to_project(
        self,
        project_id: str,
        task_requirements: List[TaskRequirement],
        max_team_size: int = 10,
    ) -> Optional[TeamComposition]:
        """
        为项目匹配团队（多角色协同匹配）。

        匹配逻辑：
        1. 分析项目所需的全部技能和角色
        2. 寻找技能互补的工人组合
        3. 确保团队整体能力覆盖所有需求
        4. 优化团队规模和效率
        """
        if not task_requirements:
            return None

        # 汇总项目所需技能
        project_skills: Dict[str, float] = {}
        role_requirements: Dict[str, List[TaskRequirement]] = {}

        for req in task_requirements:
            for skill, min_level in req.required_skills.items():
                project_skills[skill] = max(project_skills.get(skill, 0), min_level)

            role = req.preferred_role or "specialist"
            if role not in role_requirements:
                role_requirements[role] = []
            role_requirements[role].append(req)

        # 团队组建策略
        team_members: Dict[str, str] = {}  # worker_id -> role
        team_skills: Dict[str, float] = {}
        used_worker_ids: Set[str] = set()

        # 按角色逐一匹配
        for role, role_tasks in role_requirements.items():
            # 合并该角色的技能需求
            role_skills: Dict[str, float] = {}
            for task in role_tasks:
                for skill, min_level in task.required_skills.items():
                    role_skills[skill] = max(role_skills.get(skill, 0), min_level)

            # 寻找该角色的最佳候选人
            candidate = self._find_best_candidate(
                required_skills=role_skills,
                excluded_workers=used_worker_ids,
                preferred_role=role,
            )

            if candidate:
                team_members[candidate.worker_id] = role
                used_worker_ids.add(candidate.worker_id)

                # 累积团队技能
                for skill, level in candidate.skills.items():
                    team_skills[skill] = max(team_skills.get(skill, 0), level)

            if len(team_members) >= max_team_size:
                break

        if not team_members:
            return None

        # 创建团队组成
        team_id = str(uuid.uuid4())
        total_reputation = sum(
            self._worker_profiles[wid].reputation_score
            for wid in team_members.keys()
            if wid in self._worker_profiles
        )

        # 计算技能覆盖率
        skill_coverage: Dict[str, float] = {}
        for skill, required_level in project_skills.items():
            actual_level = team_skills.get(skill, 0)
            skill_coverage[skill] = min(1.0, actual_level / required_level) if required_level > 0 else 1.0

        team = TeamComposition(
            team_id=team_id,
            project_id=project_id,
            members=team_members,
            total_reputation=total_reputation,
            skill_coverage=skill_coverage,
        )

        self._team_compositions[team_id] = team

        # 初始化团队绩效
        self._team_performances[team_id] = TeamPerformance(team_id=team_id)

        logger.info(f"Team formed: {team_id}, members: {len(team_members)}, skill_coverage: {skill_coverage}")

        return team

    def batch_match_tasks(
        self,
        task_ids: List[str],
        match_strategy: str = "greedy",  # greedy, optimal, round_robin
    ) -> Dict[str, MatchResult]:
        """
        批量匹配任务。

        策略：
        - greedy: 贪心算法，每个任务选择当前最佳
        - optimal: 全局最优，考虑任务间竞争
        - round_robin: 轮询分配，保证负载均衡
        """
        results = {}

        if match_strategy == "greedy":
            # 按优先级排序
            sorted_tasks = sorted(
                task_ids,
                key=lambda tid: self._task_requirements.get(tid, TaskRequirement(tid, {})).priority,
                reverse=True,
            )

            for task_id in sorted_tasks:
                result = self.match_worker_to_task(task_id)
                if result and result.matched_workers:
                    # 更新工人负载
                    for wid in result.matched_workers:
                        self.update_workload(wid, 1)
                    results[task_id] = result

        elif match_strategy == "round_robin":
            # 获取所有可用工人
            available = self.list_available_workers()
            if not available:
                return results

            worker_index = 0
            for task_id in task_ids:
                requirement = self._task_requirements.get(task_id)
                if not requirement:
                    continue

                # 轮询选择工人
                selected = available[worker_index % len(available)]

                # 验证技能匹配
                skill_match, skill_score = self._calculate_skill_match(
                    selected, requirement.required_skills
                )

                if skill_match:
                    result = MatchResult(
                        task_id=task_id,
                        matched_workers=[selected.worker_id],
                        match_scores={selected.worker_id: skill_score},
                        match_reason=f"Round-robin assignment with skill score {skill_score:.2f}",
                        confidence=skill_score,
                    )
                    results[task_id] = result
                    self.update_workload(selected.worker_id, 1)

                worker_index += 1

        elif match_strategy == "optimal":
            # 简化的全局优化：先匹配高优先级任务，考虑工人负载平衡
            sorted_tasks = sorted(
                task_ids,
                key=lambda tid: (
                    self._task_requirements.get(tid, TaskRequirement(tid, {})).priority,
                    -self._task_requirements.get(tid, TaskRequirement(tid, {})).estimated_effort,
                ),
                reverse=True,
            )

            for task_id in sorted_tasks:
                result = self.match_worker_to_task(task_id)
                if result and result.matched_workers:
                    results[task_id] = result
                    for wid in result.matched_workers:
                        self.update_workload(wid, 1)

        # 记录批量匹配历史
        if results:
            self._record_match_history(
                ",".join(task_ids),
                [wid for r in results.values() for wid in r.matched_workers],
                f"batch_match_{match_strategy}",
            )

        return results

    # ==================== 团队绩效管理 ====================

    def record_team_performance(
        self,
        team_id: str,
        success: bool,
        delivery_time_hours: float,
        client_rating: float,
        member_ratings: Optional[List[float]] = None,
    ) -> Optional[TeamPerformance]:
        """记录团队绩效。"""
        perf = self._team_performances.get(team_id)
        if not perf:
            return None

        # 更新统计
        perf.completed_projects += 1

        # 移动平均更新
        n = perf.completed_projects
        perf.success_rate = ((n - 1) * perf.success_rate + (1 if success else 0)) / n
        perf.average_delivery_time = (
            ((n - 1) * perf.average_delivery_time + delivery_time_hours) / n
        )
        perf.client_satisfaction = (
            ((n - 1) * perf.client_satisfaction + client_rating) / n
        )

        if member_ratings:
            avg_member = sum(member_ratings) / len(member_ratings)
            perf.member_satisfaction = (
                ((n - 1) * perf.member_satisfaction + avg_member) / n
            )

        perf.last_updated = datetime.now()

        logger.info(f"Team performance updated: {team_id}, success_rate: {perf.success_rate:.2f}")

        return perf

    def get_team_performance(self, team_id: str) -> Optional[TeamPerformance]:
        """获取团队绩效。"""
        return self._team_performances.get(team_id)

    def get_team_composition(self, team_id: str) -> Optional[TeamComposition]:
        """获取团队组成。"""
        return self._team_compositions.get(team_id)

    # ==================== 内部辅助方法 ====================

    def _calculate_skill_match(
        self,
        profile: WorkerProfile,
        required_skills: Dict[str, float],
    ) -> Tuple[bool, float]:
        """
        计算技能匹配度。

        Returns:
            (是否匹配，匹配分数 0-1)
        """
        if not required_skills:
            return True, 1.0

        matched_skills = 0
        total_score = 0.0

        for skill, min_level in required_skills.items():
            actual_level = profile.skills.get(skill, 0)
            if actual_level >= min_level:
                matched_skills += 1
                total_score += actual_level
            else:
                # 技能不满足直接返回
                return False, 0.0

        if matched_skills == 0:
            return True, 0.5  # 没有技能要求时给中等分数

        avg_score = total_score / len(required_skills)
        return True, avg_score

    def _find_best_candidate(
        self,
        required_skills: Dict[str, float],
        excluded_workers: Set[str],
        preferred_role: Optional[str] = None,
    ) -> Optional[WorkerProfile]:
        """寻找最佳候选人。"""
        candidates = []

        for profile in self._worker_profiles.values():
            if profile.worker_id in excluded_workers:
                continue

            if profile.get_available_capacity() <= 0:
                continue

            # 检查技能匹配
            skill_match, skill_score = self._calculate_skill_match(profile, required_skills)
            if not skill_match:
                continue

            # 角色偏好加分
            role_bonus = 0.1 if preferred_role and preferred_role in profile.preferred_roles else 0.0

            # 综合评分
            score = skill_score * 0.6 + profile.get_composite_score() * 0.3 + role_bonus * 0.1
            candidates.append((profile, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _record_match_history(
        self,
        task_or_project_id: str,
        matched_workers: List[str],
        match_type: str,
    ):
        """记录匹配历史。"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_or_project_id": task_or_project_id,
            "matched_workers": matched_workers,
            "match_type": match_type,
        }
        self._match_history.append(record)

        # 保留最近 1000 条记录
        if len(self._match_history) > 1000:
            self._match_history = self._match_history[-1000:]

    def get_match_history(
        self,
        limit: int = 100,
        match_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取匹配历史。"""
        history = self._match_history
        if match_type:
            history = [h for h in history if h.get("match_type") == match_type]
        return history[-limit:]


# 全局单例
team_matching_service = TeamMatchingService()
