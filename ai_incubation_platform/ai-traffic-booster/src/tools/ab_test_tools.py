"""
A/B 测试工具集 - 封装 A/B 测试能力为 DeerFlow 可调用工具
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ab_test.service import ab_test_service
from schemas.ab_test import (
    ABTestCreateRequest,
    ABTestVariant,
    ABTestGoal
)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None


class ABTestTools:
    """
    A/B 测试工具集

    提供测试创建、管理、结果分析等能力，
    可作为 DeerFlow 2.0 的工具节点被调用。
    """

    def __init__(self):
        self._service = ab_test_service

    def list_tests(self) -> ToolResult:
        """
        获取 A/B 测试列表

        Returns:
            ToolResult: 包含测试列表
        """
        try:
            result = self._service.get_test_list()

            return ToolResult(
                success=True,
                data={
                    "tests": [{"id": t.id, "name": t.name, "status": t.status.value, "page_url": t.page_url}
                              for t in result.tests],
                    "total": result.total,
                    "running": result.running,
                    "completed": result.completed,
                    "draft": result.draft
                },
                message=f"获取测试列表成功，共 {result.total} 个测试"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_test_detail(self, test_id: str) -> ToolResult:
        """
        获取测试详情

        Args:
            test_id: 测试 ID

        Returns:
            ToolResult: 包含测试详情
        """
        try:
            result = self._service.get_test_detail(test_id)

            if not result:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"测试 {test_id} 不存在"
                )

            return ToolResult(
                success=True,
                data={
                    "id": result.id,
                    "name": result.name,
                    "description": result.description,
                    "page_url": result.page_url,
                    "status": result.status.value,
                    "variants": [{"id": v.id, "name": v.name, "is_control": v.is_control,
                                  "traffic_percentage": v.traffic_percentage}
                                 for v in result.variants],
                    "goals": [{"name": g.name, "metric": g.metric} for g in result.goals],
                    "created_at": result.created_at.isoformat() if result.created_at else None
                },
                message=f"获取测试详情成功：{result.name}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def create_test(
        self,
        name: str,
        description: str,
        page_url: str,
        variants: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
        confidence_level: float = 0.95,
        minimum_sample_size: int = 1000
    ) -> ToolResult:
        """
        创建 A/B 测试

        Args:
            name: 测试名称
            description: 测试描述
            page_url: 测试页面 URL
            variants: 测试变体列表，每个变体包含：
                      - name: 变体名称
                      - description: 变体描述
                      - traffic_percentage: 流量分配百分比 (0-1)
                      - content: 变体内容配置
                      - is_control: 是否为对照组
            goals: 测试目标列表，每个目标包含：
                   - name: 目标名称
                   - metric: 指标名称
                   - target_value: 目标值
                   - operator: 操作方向 (increase/decrease)
            confidence_level: 置信水平 (默认 0.95)
            minimum_sample_size: 最小样本量 (默认 1000)

        Returns:
            ToolResult: 包含创建的测试信息
        """
        try:
            if not name or not name.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    error="测试名称不能为空"
                )

            if len(variants) < 2:
                return ToolResult(
                    success=False,
                    data=None,
                    error="至少需要 2 个变体"
                )

            # 转换变体
            variant_objects = []
            for v in variants:
                variant_objects.append(ABTestVariant(
                    id=v.get("id", f"var-{len(variant_objects)+1}"),
                    name=v["name"],
                    description=v.get("description"),
                    traffic_percentage=v["traffic_percentage"],
                    content=v.get("content", {}),
                    is_control=v.get("is_control", False)
                ))

            # 转换目标
            goal_objects = []
            for g in goals:
                goal_objects.append(ABTestGoal(
                    name=g["name"],
                    metric=g["metric"],
                    target_value=g["target_value"],
                    operator=g.get("operator", "increase")
                ))

            request = ABTestCreateRequest(
                name=name,
                description=description,
                page_url=page_url,
                variants=variant_objects,
                goals=goal_objects,
                confidence_level=confidence_level,
                minimum_sample_size=minimum_sample_size
            )

            result = self._service.create_test(request)

            return ToolResult(
                success=True,
                data={
                    "id": result.id,
                    "name": result.name,
                    "status": result.status.value,
                    "variants_count": len(result.variants)
                },
                message=f"测试创建成功，ID: {result.id}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def start_test(self, test_id: str) -> ToolResult:
        """
        启动测试

        Args:
            test_id: 测试 ID

        Returns:
            ToolResult: 执行结果
        """
        try:
            result = self._service.start_test(test_id)

            if not result:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"测试 {test_id} 不存在或状态不允许启动"
                )

            return ToolResult(
                success=True,
                data={"id": result.id, "status": result.status.value},
                message=f"测试 {result.name} 已启动"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def stop_test(self, test_id: str) -> ToolResult:
        """
        停止测试

        Args:
            test_id: 测试 ID

        Returns:
            ToolResult: 执行结果
        """
        try:
            result = self._service.stop_test(test_id)

            if not result:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"测试 {test_id} 不存在或状态不允许停止"
                )

            return ToolResult(
                success=True,
                data={"id": result.id, "status": result.status.value},
                message=f"测试 {result.name} 已停止"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_test_result(self, test_id: str) -> ToolResult:
        """
        获取测试结果

        Args:
            test_id: 测试 ID

        Returns:
            ToolResult: 包含测试结果和结论
        """
        try:
            result = self._service.get_test_result(test_id)

            if not result:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"测试 {test_id} 不存在或没有结果"
                )

            return ToolResult(
                success=True,
                data={
                    "test_id": result.test_id,
                    "test_name": result.test_name,
                    "status": result.status.value,
                    "current_sample_size": result.current_sample_size,
                    "remaining_sample_size": result.remaining_sample_size,
                    "has_winner": result.has_winner,
                    "can_terminate": result.can_terminate,
                    "metrics": [{"variant_name": m.variant_name, "conversion_rate": round(m.conversion_rate, 4),
                                 "improvement": round(m.improvement, 4), "is_winner": m.is_winner}
                                for m in result.metrics],
                    "conclusion": result.conclusion,
                    "recommendations": result.recommendations[:3]  # 只返回前 3 条建议
                },
                message=f"获取测试结果成功：{result.conclusion}" if result.conclusion else "获取测试结果成功"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
