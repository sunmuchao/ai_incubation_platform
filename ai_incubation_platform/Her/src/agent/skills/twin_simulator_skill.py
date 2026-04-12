"""
数字分身模拟 Skill

Values 功能：使用数字分身进行模拟对话，生成兼容性报告和复盘分析
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class TwinSimulatorSkill:
    """
    数字分身模拟 Skill

    核心能力:
    - 数字分身配置管理
    - 模拟对话执行
    - 兼容性评分计算
    - 复盘报告生成
    - 约会建议输出

    自主触发条件:
    - 新匹配产生且双方已配置分身
    - 关系进入深度阶段前
    - 用户主动请求模拟
    """

    name = "twin_simulator"
    version = "1.0.0"
    description = """
    数字分身模拟专家

    能力:
    - 基于用户配置的数字分身创建
    - 10 轮模拟对话执行
    - 多维度兼容性评分
    - 精彩对话片段提取
    - 个性化约会建议生成
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_a_id": {
                    "type": "string",
                    "description": "用户 A ID"
                },
                "user_b_id": {
                    "type": "string",
                    "description": "用户 B ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["start", "run", "report", "status"],
                    "description": "操作类型"
                },
                "simulation_id": {
                    "type": "integer",
                    "description": "模拟 ID (用于 run/report/status)"
                },
                "total_rounds": {
                    "type": "integer",
                    "description": "模拟轮数",
                    "default": 10
                }
            },
            "required": ["user_a_id", "user_b_id", "action"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "simulation_id": {"type": "integer"},
                "status": {"type": "string"},
                "compatibility_score": {"type": "number"},
                "conversation_highlights": {"type": "array"},
                "report": {"type": "object"}
            }
        }

    async def execute(
        self,
        user_a_id: str,
        user_b_id: str,
        action: str = "start",
        simulation_id: Optional[int] = None,
        total_rounds: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行数字分身模拟

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            action: 操作类型
            simulation_id: 模拟 ID
            total_rounds: 模拟轮数

        Returns:
            执行结果
        """
        logger.info(f"TwinSimulator: {action} for {user_a_id} vs {user_b_id}")

        try:
            if action == "start":
                return await self._start_simulation(user_a_id, user_b_id, total_rounds)
            elif action == "run":
                return await self._run_simulation(simulation_id)
            elif action == "report":
                return self._generate_report(simulation_id, user_a_id)
            elif action == "status":
                return self._get_status(simulation_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "ai_message": "未知的操作类型",
                }

        except Exception as e:
            logger.error(f"TwinSimulator execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "数字分身模拟失败，请稍后再试"
            }

    async def _start_simulation(
        self,
        user_a_id: str,
        user_b_id: str,
        total_rounds: int
    ) -> Dict[str, Any]:
        """启动模拟"""
        from services.digital_twin_service import digital_twin_service

        # 检查分身配置
        twin_a = digital_twin_service.get_twin_profile(user_a_id)
        twin_b = digital_twin_service.get_twin_profile(user_b_id)

        if not twin_a:
            return {
                "success": False,
                "error": "用户 A 未配置数字分身",
                "ai_message": "您需要先配置数字分身才能进行模拟~",
            }

        if not twin_b:
            return {
                "success": False,
                "error": "用户 B 未配置数字分身",
                "ai_message": "对方尚未配置数字分身~",
            }

        # 启动模拟
        success, message, simulation = digital_twin_service.start_simulation(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            total_rounds=total_rounds,
        )

        if not success:
            return {
                "success": False,
                "error": message,
                "ai_message": message,
            }

        return {
            "success": True,
            "data": {
                "simulation_id": simulation.id,
                "status": simulation.status,
                "total_rounds": total_rounds,
                "user_a": twin_a.display_name,
                "user_b": twin_b.display_name,
            },
            "ai_message": f"数字分身模拟已启动，将进行{total_rounds}轮对话~",
        }

    async def _run_simulation(
        self,
        simulation_id: int
    ) -> Dict[str, Any]:
        """运行模拟"""
        from services.digital_twin_service import digital_twin_service

        # 异步运行模拟
        async def progress_callback(round_num: int, response: Dict):
            logger.info(f"Simulation round {round_num} completed")

        success, message = await digital_twin_service.run_simulation(
            simulation_id=simulation_id,
            callback=progress_callback,
        )

        if not success:
            return {
                "success": False,
                "error": message,
                "ai_message": message,
            }

        # 获取模拟结果
        db = digital_twin_service._get_db()
        from models.digital_twin_models import DigitalTwinSimulation
        simulation = db.query(DigitalTwinSimulation).filter(
            DigitalTwinSimulation.id == simulation_id
        ).first()

        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "status": "completed",
                "compatibility_score": simulation.compatibility_score,
                "chemistry_score": simulation.chemistry_score,
                "communication_match": simulation.communication_match,
                "values_alignment": simulation.values_alignment,
                "highlights": simulation.highlights,
                "potential_conflicts": simulation.potential_conflicts,
            },
            "ai_message": f"模拟完成！兼容性评分{simulation.compatibility_score:.0f}分",
        }

    def _generate_report(
        self,
        simulation_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """生成报告"""
        from services.digital_twin_service import digital_twin_service

        # 生成报告
        success, message, report = digital_twin_service.generate_report(
            simulation_id=simulation_id,
            user_id=user_id,
        )

        if not success:
            return {
                "success": False,
                "error": message,
                "ai_message": message,
            }

        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "report_id": report.id,
                "report_title": report.report_title,
                "report_summary": report.report_summary,
                "overall_compatibility": report.overall_compatibility,
                "dimension_scores": report.dimension_scores,
                "strengths": report.strengths,
                "growth_areas": report.growth_areas,
                "date_suggestions": report.date_suggestions,
                "conversation_snippets": report.conversation_snippets,
            },
            "ai_message": f"复盘报告已生成：{report.report_summary}",
        }

    def _get_status(
        self,
        simulation_id: int
    ) -> Dict[str, Any]:
        """获取状态"""
        from utils.db_session_manager import db_session
        from models.digital_twin_models import DigitalTwinSimulation

        with db_session() as db:
            simulation = db.query(DigitalTwinSimulation).filter(
                DigitalTwinSimulation.id == simulation_id
            ).first()

            if not simulation:
                return {
                    "success": False,
                    "error": "模拟未找到",
                    "ai_message": "模拟不存在~",
                }

            return {
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "status": simulation.status,
                    "total_rounds": simulation.total_rounds,
                    "completed_rounds": simulation.completed_rounds,
                    "progress": round(
                        simulation.completed_rounds / simulation.total_rounds * 100
                    )
                    if simulation.total_rounds > 0
                    else 0,
                    "started_at": simulation.started_at.isoformat()
                    if simulation.started_at
                    else None,
                    "completed_at": simulation.completed_at.isoformat()
                    if simulation.completed_at
                    else None,
                },
                "ai_message": f"模拟进度：{simulation.completed_rounds}/{simulation.total_rounds}",
            }


# 全局单例获取函数
_skill_instance: Optional[TwinSimulatorSkill] = None


def get_twin_simulator_skill() -> TwinSimulatorSkill:
    """获取数字分身模拟 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = TwinSimulatorSkill()
    return _skill_instance
