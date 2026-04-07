"""
AI 任务分解服务。

核心功能：
1. 智能任务分解 - 基于 AI 将复杂任务拆分为可执行的子任务
2. 依赖关系管理 - 管理子任务之间的依赖关系
3. 关键路径计算 - 计算完成所有子任务的最长路径
4. 结果聚合 - 聚合子任务结果生成最终交付物
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from models.task_decomposition import (
    DecompositionRequest,
    DecompositionResponse,
    DecompositionStrategy,
    SubTask,
    SubTaskStatus,
    TaskDecomposition,
)

logger = logging.getLogger(__name__)


class AITaskDecompositionService:
    """
    AI 任务分解服务。

    提供以下能力：
    1. 基于规则的任务分解（适用于常见任务模式）
    2. 基于依赖关系的任务编排
    3. 关键路径分析
    4. 结果聚合
    """

    # 常见任务分解模板
    TASK_TEMPLATES = {
        "survey": {
            "pattern": r"(调研 | 调查 | 问卷 | 采集).*(数据 | 信息 | 样本)",
            "sub_tasks": [
                {"title": "设计调研问卷/表格", "duration": 60},
                {"title": "确定调研对象和样本", "duration": 30},
                {"title": "执行调研/数据采集", "duration": 120},
                {"title": "整理和验证数据", "duration": 60},
                {"title": "生成调研报告", "duration": 45},
            ],
        },
        "photo_verification": {
            "pattern": r"(拍照 | 摄影 | 图片).*(验证 | 记录 | 采集)",
            "sub_tasks": [
                {"title": "确认拍摄地点和要求", "duration": 15},
                {"title": "前往拍摄地点", "duration": 60},
                {"title": "执行拍摄", "duration": 30},
                {"title": "上传和标注图片", "duration": 20},
                {"title": "质量自检", "duration": 15},
            ],
        },
        "document_review": {
            "pattern": r"(审核 | 审查 | 核对).*(文档 | 文件 | 资料)",
            "sub_tasks": [
                {"title": "阅读文档内容", "duration": 45},
                {"title": "核对关键信息", "duration": 30},
                {"title": "标记问题和建议", "duration": 30},
                {"title": "生成审核报告", "duration": 30},
            ],
        },
        "data_entry": {
            "pattern": r"(录入 | 输入 | 整理).*(数据 | 信息)",
            "sub_tasks": [
                {"title": "准备数据源", "duration": 15},
                {"title": "录入数据批次 1", "duration": 45},
                {"title": "录入数据批次 2", "duration": 45},
                {"title": "数据校验和纠错", "duration": 30},
                {"title": "最终确认", "duration": 15},
            ],
        },
        "translation": {
            "pattern": r"(翻译 | 译成).*(内容 | 文档 | 文本)",
            "sub_tasks": [
                {"title": "理解原文内容和上下文", "duration": 30},
                {"title": "初步翻译", "duration": 60},
                {"title": "校对和优化译文", "duration": 30},
                {"title": "专业术语核对", "duration": 20},
                {"title": "最终审校", "duration": 15},
            ],
        },
    }

    def __init__(self):
        # 内存存储（生产环境应使用数据库）
        self._decompositions: Dict[str, TaskDecomposition] = {}
        self._sub_tasks: Dict[str, SubTask] = {}
        self._task_to_decomposition: Dict[str, str] = {}  # task_id -> decomposition_id

    def analyze_task(self, task_title: str, task_description: str) -> Dict[str, Any]:
        """
        分析任务特征，识别适合的任务分解模式。

        Returns:
            {
                "matched_template": str,  # 匹配的模板名称
                "confidence": float,  # 匹配置信度
                "suggested_strategy": DecompositionStrategy,
                "estimated_complexity": str,  # low, medium, high
            }
        """
        combined_text = f"{task_title} {task_description}".lower()

        best_match = None
        best_confidence = 0.0

        for template_name, template_data in self.TASK_TEMPLATES.items():
            pattern = template_data["pattern"]
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                # 计算置信度（基于匹配位置和关键词数量）
                confidence = 0.5 + 0.1 * len(match.groups()) if match.groups() else 0.7
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = template_name

        # 如果没有匹配到模板，基于任务特征推断
        if not best_match:
            # 检查任务描述长度和复杂度
            if len(task_description) > 500:
                best_match = "complex_general"
                best_confidence = 0.5
            else:
                best_match = "simple_general"
                best_confidence = 0.6

        # 推断建议的分解策略
        suggested_strategy = self._infer_strategy(combined_text, best_match)

        # 评估复杂度
        complexity = self._assess_complexity(task_description, best_match)

        return {
            "matched_template": best_match,
            "confidence": best_confidence,
            "suggested_strategy": suggested_strategy,
            "estimated_complexity": complexity,
        }

    def _infer_strategy(self, text: str, template: Optional[str]) -> DecompositionStrategy:
        """根据任务特征推断合适的分解策略。"""
        # 检查是否有顺序依赖的关键词
        sequential_keywords = ["然后", "接着", "之后", "然后", "步骤", "顺序"]
        if any(kw in text for kw in sequential_keywords):
            return DecompositionStrategy.SEQUENTIAL

        # 检查是否有并行可能的关键词
        parallel_keywords = ["同时", "并行", "各自", "分别", "独立"]
        if any(kw in text for kw in parallel_keywords):
            return DecompositionStrategy.PARALLEL

        # 基于模板推断
        if template:
            if template in ["survey", "photo_verification", "document_review"]:
                return DecompositionStrategy.SEQUENTIAL
            elif template in ["data_entry"]:
                return DecompositionStrategy.PARALLEL

        # 默认使用顺序分解
        return DecompositionStrategy.SEQUENTIAL

    def _assess_complexity(self, description: str, template: Optional[str]) -> str:
        """评估任务复杂度。"""
        # 基于描述长度
        length_score = len(description) / 100  # 每 100 字为 1 分

        # 基于特殊要求数量
        requirement_count = description.count("需要") + description.count("必须")
        constraint_count = description.count("限制") + description.count("条件")

        total_score = length_score + requirement_count * 0.5 + constraint_count * 0.3

        if total_score > 5:
            return "high"
        elif total_score > 2:
            return "medium"
        else:
            return "low"

    def decompose_task(
        self,
        request: DecompositionRequest,
        task_title: str,
        task_description: str,
        acceptance_criteria: List[str],
    ) -> DecompositionResponse:
        """
        执行任务分解。

        Args:
            request: 分解请求
            task_title: 任务标题
            task_description: 任务描述
            acceptance_criteria: 验收标准列表

        Returns:
            分解响应，包含生成的子任务列表
        """
        try:
            # 1. 分析任务特征
            analysis = self.analyze_task(task_title, task_description)
            logger.info(
                "Task analysis: task=%s, template=%s, confidence=%.2f",
                request.task_id,
                analysis["matched_template"],
                analysis["confidence"],
            )

            # 2. 生成子任务
            sub_tasks = self._generate_sub_tasks(
                request=request,
                task_title=task_title,
                task_description=task_description,
                acceptance_criteria=acceptance_criteria,
                template=analysis["matched_template"],
            )

            if not sub_tasks:
                return DecompositionResponse(
                    success=False,
                    message="无法生成有效的子任务，请检查任务描述是否清晰",
                )

            # 3. 创建分解记录
            decomposition = TaskDecomposition(
                root_task_id=request.task_id,
                strategy=request.strategy,
                strategy_config=request.strategy_config,
                sub_task_ids=[st.id for st in sub_tasks],
                total_sub_tasks=len(sub_tasks),
                ai_model_used="rule_based_v1",
                decomposition_confidence=analysis["confidence"],
            )

            # 4. 存储分解结果
            self._decompositions[decomposition.id] = decomposition
            self._task_to_decomposition[request.task_id] = decomposition.id
            for sub_task in sub_tasks:
                self._sub_tasks[sub_task.id] = sub_task

            # 5. 计算关键路径
            critical_path = self._calculate_critical_path(sub_tasks)

            # 6. 计算总预估时间
            total_duration = sum(st.estimated_duration_minutes for st in sub_tasks)

            logger.info(
                "Task decomposition completed: decomposition_id=%s, sub_tasks=%d, total_duration=%dmin",
                decomposition.id,
                len(sub_tasks),
                total_duration,
            )

            return DecompositionResponse(
                success=True,
                decomposition_id=decomposition.id,
                sub_tasks=sub_tasks,
                message=f"成功分解为 {len(sub_tasks)} 个子任务",
                estimated_total_duration_minutes=total_duration,
                critical_path=critical_path,
            )

        except Exception as e:
            logger.exception("Task decomposition failed: %s", e)
            return DecompositionResponse(
                success=False,
                message=f"分解失败：{str(e)}",
            )

    def _generate_sub_tasks(
        self,
        request: DecompositionRequest,
        task_title: str,
        task_description: str,
        acceptance_criteria: List[str],
        template: Optional[str],
    ) -> List[SubTask]:
        """生成子任务列表。"""
        sub_tasks = []

        # 尝试使用模板生成
        if template and template in self.TASK_TEMPLATES:
            template_data = self.TASK_TEMPLATES[template]
            template_tasks = template_data["sub_tasks"]

            for i, template_task in enumerate(template_tasks):
                if len(sub_tasks) >= request.max_sub_tasks:
                    break

                sub_task = SubTask(
                    parent_task_id=request.task_id,
                    root_task_id=request.task_id,
                    title=template_task["title"],
                    description=f"{task_title} - {template_task['title']}",
                    requirements=[],
                    acceptance_criteria=acceptance_criteria[:2] if acceptance_criteria else [],
                    depends_on=[sub_tasks[i - 1].id] if i > 0 and request.strategy == DecompositionStrategy.SEQUENTIAL else [],
                    estimated_duration_minutes=template_task["duration"],
                    priority=request.max_sub_tasks - i,
                )
                sub_tasks.append(sub_task)

        # 如果没有模板或超过限制，使用通用分解
        if not sub_tasks:
            sub_tasks = self._generate_generic_sub_tasks(request, task_title, task_description, acceptance_criteria)

        return sub_tasks

    def _generate_generic_sub_tasks(
        self,
        request: DecompositionRequest,
        task_title: str,
        task_description: str,
        acceptance_criteria: List[str],
    ) -> List[SubTask]:
        """通用的任务分解逻辑（基于规则和启发式）。"""
        sub_tasks = []

        # 基于验收标准拆分
        if acceptance_criteria:
            for i, criterion in enumerate(acceptance_criteria[: request.max_sub_tasks]):
                sub_task = SubTask(
                    parent_task_id=request.task_id,
                    root_task_id=request.task_id,
                    title=f"完成验收项 {i + 1}",
                    description=f"验收标准：{criterion}",
                    requirements=[criterion],
                    acceptance_criteria=[criterion],
                    depends_on=[sub_tasks[i - 1].id] if i > 0 and request.strategy == DecompositionStrategy.SEQUENTIAL else [],
                    estimated_duration_minutes=30,
                    priority=len(acceptance_criteria) - i,
                )
                sub_tasks.append(sub_task)

        # 如果验收标准太少，基于句子拆分
        if len(sub_tasks) < 2:
            sentences = re.split(r"[。！？.!?]", task_description)
            sentences = [s.strip() for s in sentences if s.strip()]

            chunk_size = max(1, len(sentences) // min(request.max_sub_tasks, 3))
            for i in range(0, len(sentences), chunk_size):
                if len(sub_tasks) >= request.max_sub_tasks:
                    break

                chunk = sentences[i : i + chunk_size]
                sub_task = SubTask(
                    parent_task_id=request.task_id,
                    root_task_id=request.task_id,
                    title=f"子任务 {len(sub_tasks) + 1}",
                    description=". ".join(chunk),
                    requirements=[],
                    acceptance_criteria=[],
                    depends_on=[sub_tasks[i - 1].id] if i > 0 and request.strategy == DecompositionStrategy.SEQUENTIAL else [],
                    estimated_duration_minutes=30 * len(chunk),
                    priority=request.max_sub_tasks - len(sub_tasks),
                )
                sub_tasks.append(sub_task)

        # 确保至少有一个子任务
        if not sub_tasks:
            sub_tasks.append(
                SubTask(
                    parent_task_id=request.task_id,
                    root_task_id=request.task_id,
                    title=task_title,
                    description=task_description,
                    requirements=[],
                    acceptance_criteria=acceptance_criteria,
                    estimated_duration_minutes=60,
                    priority=1,
                )
            )

        return sub_tasks

    def _calculate_critical_path(self, sub_tasks: List[SubTask]) -> List[str]:
        """
        计算关键路径（最长依赖链）。

        使用拓扑排序和动态规划计算从起始任务到结束任务的最长路径。
        """
        if not sub_tasks:
            return []

        # 构建依赖图
        task_map = {st.id: st for st in sub_tasks}
        dependents = {st.id: [] for st in sub_tasks}

        for st in sub_tasks:
            for dep_id in st.depends_on:
                if dep_id in dependents:
                    dependents[dep_id].append(st.id)

        # 找到没有依赖的任务（起始任务）
        starts = [st.id for st in sub_tasks if not st.depends_on]
        if not starts:
            return [sub_tasks[0].id] if sub_tasks else []

        # 动态规划计算最长路径
        longest_path = {st_id: [st_id] for st_id in starts}
        longest_duration = {st_id: task_map[st_id].estimated_duration_minutes for st_id in starts}

        # 拓扑排序处理
        in_degree = {st.id: len(st.depends_on) for st in sub_tasks}
        queue = list(starts)

        while queue:
            current = queue.pop(0)
            current_duration = longest_duration.get(current, 0)
            current_path = longest_path.get(current, [current])

            for next_id in dependents.get(current, []):
                in_degree[next_id] -= 1
                next_task = task_map[next_id]

                new_duration = current_duration + next_task.estimated_duration_minutes
                if new_duration > longest_duration.get(next_id, 0):
                    longest_duration[next_id] = new_duration
                    longest_path[next_id] = current_path + [next_id]

                if in_degree[next_id] == 0:
                    queue.append(next_id)

        if not longest_duration:
            return []

        end_node = max(longest_duration, key=longest_duration.get)
        return longest_path.get(end_node, [end_node])

    def get_decomposition(self, decomposition_id: str) -> Optional[TaskDecomposition]:
        """获取分解记录。"""
        return self._decompositions.get(decomposition_id)

    def get_sub_task(self, sub_task_id: str) -> Optional[SubTask]:
        """获取子任务。"""
        return self._sub_tasks.get(sub_task_id)

    def get_decomposition_by_task_id(self, task_id: str) -> Optional[TaskDecomposition]:
        """通过任务 ID 获取分解记录。"""
        decomposition_id = self._task_to_decomposition.get(task_id)
        if decomposition_id:
            return self._decompositions.get(decomposition_id)
        return None

    def get_sub_tasks_by_parent_id(self, parent_task_id: str) -> List[SubTask]:
        """获取父任务下的所有子任务。"""
        return [st for st in self._sub_tasks.values() if st.parent_task_id == parent_task_id]

    def accept_sub_task(self, sub_task_id: str, worker_id: str) -> bool:
        """工人接单子任务。"""
        sub_task = self._sub_tasks.get(sub_task_id)
        if not sub_task or sub_task.status != SubTaskStatus.PENDING:
            return False

        sub_task.status = SubTaskStatus.IN_PROGRESS
        sub_task.worker_id = worker_id
        sub_task.started_at = datetime.now()
        sub_task.updated_at = datetime.now()
        return True

    def submit_sub_task(self, sub_task_id: str, worker_id: str, content: str, attachments: List[str]) -> bool:
        """提交子任务交付物。"""
        sub_task = self._sub_tasks.get(sub_task_id)
        if not sub_task or sub_task.worker_id != worker_id:
            return False

        sub_task.delivery_content = content
        sub_task.delivery_attachments = attachments
        sub_task.status = SubTaskStatus.REVIEW
        sub_task.submitted_at = datetime.now()
        sub_task.updated_at = datetime.now()

        self._update_dependent_tasks(sub_task_id)
        return True

    def complete_sub_task(self, sub_task_id: str, approved: bool) -> bool:
        """验收子任务。"""
        sub_task = self._sub_tasks.get(sub_task_id)
        if not sub_task or sub_task.status not in [SubTaskStatus.REVIEW, SubTaskStatus.IN_PROGRESS]:
            return False

        if approved:
            sub_task.status = SubTaskStatus.COMPLETED
            sub_task.completed_at = datetime.now()

            decomposition = self._get_decomposition_by_sub_task(sub_task_id)
            if decomposition:
                decomposition.completed_count += 1
                if decomposition.completed_count >= decomposition.total_sub_tasks:
                    decomposition.status = "completed"
                    decomposition.completed_at = datetime.now()
        else:
            sub_task.status = SubTaskStatus.IN_PROGRESS

        sub_task.updated_at = datetime.now()
        return True

    def _update_dependent_tasks(self, completed_sub_task_id: str) -> None:
        """更新依赖任务的状态（检查是否可以从 waiting_dependency 转为 pending）。"""
        for sub_task in self._sub_tasks.values():
            if sub_task.status == SubTaskStatus.WAITING_DEPENDENCY:
                if completed_sub_task_id in sub_task.depends_on:
                    # 检查是否所有依赖都已完成
                    all_deps_completed = all(
                        self._sub_tasks.get(dep_id, SubTask()).status == SubTaskStatus.COMPLETED
                        for dep_id in sub_task.depends_on
                    )
                    if all_deps_completed:
                        sub_task.status = SubTaskStatus.PENDING

    def _get_decomposition_by_sub_task(self, sub_task_id: str) -> Optional[TaskDecomposition]:
        """通过子任务 ID 查找分解记录。"""
        for decomp in self._decompositions.values():
            if sub_task_id in decomp.sub_task_ids:
                return decomp
        return None

    def aggregate_results(self, decomposition_id: str) -> Optional[str]:
        """聚合子任务结果生成最终交付物。"""
        decomposition = self._decompositions.get(decomposition_id)
        if not decomposition:
            return None

        # 收集所有已完成的子任务结果
        completed_results = []
        for sub_task_id in decomposition.sub_task_ids:
            sub_task = self._sub_tasks.get(sub_task_id)
            if sub_task and sub_task.status == SubTaskStatus.COMPLETED and sub_task.delivery_content:
                completed_results.append({
                    "task_id": sub_task_id,
                    "title": sub_task.title,
                    "content": sub_task.delivery_content,
                    "attachments": sub_task.delivery_attachments,
                })

        if not completed_results:
            return None

        # 简单聚合：按顺序拼接结果
        aggregated = "=== 任务分解结果汇总 ===\n\n"
        for i, result in enumerate(completed_results, 1):
            aggregated += f"## {i}. {result['title']}\n"
            aggregated += f"{result['content']}\n\n"

        decomposition.aggregated_result = aggregated
        decomposition.aggregated_attachments = [
            att for result in completed_results for att in result.get("attachments", [])
        ]

        return aggregated


# 全局单例
task_decomposition_service = AITaskDecompositionService()
