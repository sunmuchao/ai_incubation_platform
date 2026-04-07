"""
TalentAgent - 人才智能体

基于 DeerFlow 2.0 的自主人才管理智能体

核心职责:
- 自主分析员工能力画像
- 自主匹配人才与机会 (转岗/晋升/项目)
- 自主规划职业发展路径
- 自主追踪绩效并提供建议
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .deerflow_client import DeerFlowClient

logger = logging.getLogger(__name__)


class TalentAgent:
    """
    人才智能体

    作为 AI Native 的核心决策引擎，TalentAgent 负责:
    1. 主动分析员工能力画像
    2. 主动匹配转岗/晋升机会
    3. 主动生成职业发展规划
    4. 主动追踪绩效并提供改进建议

    使用 DeerFlow 2.0 框架进行工作流编排和工具调用
    """

    def __init__(self, deerflow_client: Optional[DeerFlowClient] = None):
        """
        初始化 TalentAgent

        Args:
            deerflow_client: DeerFlow 客户端，用于工作流执行
        """
        self.df_client = deerflow_client or DeerFlowClient()
        self._tools_registered = False
        self._workflows_registered = False
        self._trace_id_counter = 0

    def _generate_trace_id(self) -> str:
        """生成唯一的追踪 ID"""
        self._trace_id_counter += 1
        return f"talent-agent-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._trace_id_counter:04d}"

    async def initialize(self):
        """初始化智能体 - 注册工具和工作流"""
        if not self._tools_registered:
            await self._register_tools()
            self._tools_registered = True

        if not self._workflows_registered:
            await self._register_workflows()
            self._workflows_registered = True

        logger.info("TalentAgent 初始化完成")

    async def _register_tools(self):
        """注册人才管理工具"""
        try:
            from tools.talent_tools import TOOLS_REGISTRY as TALENT_TOOLS
            from tools.career_tools import TOOLS_REGISTRY as CAREER_TOOLS
        except ImportError:
            from ..tools.talent_tools import TOOLS_REGISTRY as TALENT_TOOLS
            from ..tools.career_tools import TOOLS_REGISTRY as CAREER_TOOLS

        all_tools = {**TALENT_TOOLS, **CAREER_TOOLS}

        for tool_name, tool_info in all_tools.items():
            self.df_client.register_tool(
                name=tool_info["name"],
                description=tool_info["description"],
                input_schema=tool_info["input_schema"],
                handler=tool_info["handler"]
            )

        logger.info(f"TalentAgent: 已注册 {len(all_tools)} 个工具")

    async def _register_workflows(self):
        """注册核心工作流"""
        try:
            from workflows.talent_workflows import (
                AutoTalentMatchWorkflow,
                AutoPerformanceReviewWorkflow
            )
            from workflows.career_workflows import (
                AutoCareerPlanningWorkflow,
                AutoSkillGapAnalysisWorkflow
            )
        except ImportError:
            from ..workflows.talent_workflows import (
                AutoTalentMatchWorkflow,
                AutoPerformanceReviewWorkflow
            )
            from ..workflows.career_workflows import (
                AutoCareerPlanningWorkflow,
                AutoSkillGapAnalysisWorkflow
            )

        self.df_client.register_workflow("auto_talent_match", AutoTalentMatchWorkflow)
        self.df_client.register_workflow("auto_performance_review", AutoPerformanceReviewWorkflow)
        self.df_client.register_workflow("auto_career_planning", AutoCareerPlanningWorkflow)
        self.df_client.register_workflow("auto_skill_gap_analysis", AutoSkillGapAnalysisWorkflow)

        logger.info("TalentAgent: 已注册 4 个工作流")

    # ==================== 核心 AI 能力 ====================

    async def analyze_employee_profile(self, employee_id: str, include_projects: bool = True) -> Dict[str, Any]:
        """
        分析员工能力画像

        Args:
            employee_id: 员工 ID
            include_projects: 是否包含项目历史

        Returns:
            Dict: 员工画像分析结果
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始分析员工画像：{employee_id}")

        try:
            result = await self.df_client.call_tool(
                "analyze_employee_profile",
                employee_id=employee_id,
                include_projects=include_projects
            )
            logger.info(f"[{trace_id}] 员工画像分析完成")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 员工画像分析失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    async def match_opportunities(
        self,
        employee_id: str,
        opportunity_type: str = "all",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        匹配人才与机会

        Args:
            employee_id: 员工 ID
            opportunity_type: 机会类型 (transfer/promotion/project/all)
            limit: 最大返回数量

        Returns:
            Dict: 匹配的机会列表
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始匹配机会：{employee_id}, 类型={opportunity_type}")

        try:
            # 使用工作流进行完整匹配
            if opportunity_type == "all" or opportunity_type == "transfer":
                result = await self.df_client.run_workflow(
                    "auto_talent_match",
                    employee_id=employee_id,
                    opportunity_type=opportunity_type,
                    limit=limit,
                    trace_id=trace_id
                )
            else:
                result = await self.df_client.call_tool(
                    "match_opportunities",
                    employee_id=employee_id,
                    opportunity_type=opportunity_type,
                    limit=limit
                )

            logger.info(f"[{trace_id}] 机会匹配完成，找到 {len(result.get('opportunities', []))} 个机会")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 机会匹配失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    async def plan_career(
        self,
        employee_id: str,
        target_role: Optional[str] = None,
        timeframe_months: int = 12
    ) -> Dict[str, Any]:
        """
        生成职业发展规划

        Args:
            employee_id: 员工 ID
            target_role: 目标职位（可选，不传则 AI 自动推荐）
            timeframe_months: 规划时间范围（月）

        Returns:
            Dict: 职业发展规划
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始生成职业规划：{employee_id}, 目标={target_role}")

        try:
            result = await self.df_client.run_workflow(
                "auto_career_planning",
                employee_id=employee_id,
                target_role=target_role,
                timeframe_months=timeframe_months,
                trace_id=trace_id
            )
            logger.info(f"[{trace_id}] 职业规划生成完成")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 职业规划生成失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    async def track_performance(
        self,
        employee_id: str,
        period: str = "quarterly"
    ) -> Dict[str, Any]:
        """
        追踪绩效并提供改进建议

        Args:
            employee_id: 员工 ID
            period: 评估周期 (weekly/monthly/quarterly)

        Returns:
            Dict: 绩效评估结果和改进建议
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始绩效评估：{employee_id}, 周期={period}")

        try:
            result = await self.df_client.run_workflow(
                "auto_performance_review",
                employee_id=employee_id,
                period=period,
                trace_id=trace_id
            )
            logger.info(f"[{trace_id}] 绩效评估完成")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 绩效评估失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    async def analyze_skill_gap(
        self,
        employee_id: str,
        target_role_id: str
    ) -> Dict[str, Any]:
        """
        分析技能差距

        Args:
            employee_id: 员工 ID
            target_role_id: 目标职位 ID

        Returns:
            Dict: 技能差距分析结果
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始技能差距分析：{employee_id} -> {target_role_id}")

        try:
            result = await self.df_client.run_workflow(
                "auto_skill_gap_analysis",
                employee_id=employee_id,
                target_role_id=target_role_id,
                trace_id=trace_id
            )
            logger.info(f"[{trace_id}] 技能差距分析完成")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 技能差距分析失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    # ==================== 主动推送能力 ====================

    async def proactive_opportunity_scan(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        主动扫描并推送机会

        定期运行，为所有活跃员工匹配机会

        Args:
            batch_size: 每批处理的员工数量

        Returns:
            Dict: 扫描结果统计
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始主动机会扫描")

        try:
            from ..services.career_development_service import CareerDevelopmentService
            career_service = CareerDevelopmentService()

            # 获取所有活跃员工
            # 这里简化处理，实际应从数据库获取
            stats = {
                "scanned": 0,
                "matched": 0,
                "notified": 0
            }

            logger.info(f"[{trace_id}] 主动扫描完成：{stats}")
            return {"status": "success", "stats": stats, "trace_id": trace_id}
        except Exception as e:
            logger.error(f"[{trace_id}] 主动扫描失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    async def generate_talent_insights(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成人才洞察报告

        Args:
            department_id: 部门 ID（可选，不传则分析全公司）

        Returns:
            Dict: 人才洞察报告
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 开始生成人才洞察报告")

        try:
            # 调用人才分析工具
            result = await self.df_client.call_tool(
                "analyze_team_composition",
                department_id=department_id
            )
            logger.info(f"[{trace_id}] 人才洞察报告生成完成")
            return result
        except Exception as e:
            logger.error(f"[{trace_id}] 人才洞察报告生成失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    # ==================== 审计日志 ====================

    async def log_action(
        self,
        action: str,
        employee_id: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        status: str = "success"
    ):
        """
        记录审计日志

        Args:
            action: 操作类型
            employee_id: 员工 ID
            request: 请求数据
            response: 响应数据
            status: 操作状态
        """
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] 审计日志：{action} for {employee_id}")

        # 实际实现应写入数据库的 audit_logs 表
        # 这里仅记录日志
        logger.info(f"AUDIT: action={action}, employee={employee_id}, status={status}")


# 全局智能体实例
_talent_agent: Optional[TalentAgent] = None


def get_talent_agent() -> TalentAgent:
    """获取全局 TalentAgent 实例"""
    global _talent_agent
    if _talent_agent is None:
        _talent_agent = TalentAgent()
    return _talent_agent


async def initialize_talent_agent():
    """初始化全局 TalentAgent"""
    agent = get_talent_agent()
    await agent.initialize()
    return agent
