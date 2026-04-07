"""
行为追溯链服务

实现 AI 行为的完整追溯、决策过程记录、追溯链查询等功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
import logging
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBBehaviorTrace, DBAgentReputation
from models.p6_entities import BehaviorTraceStatus, TraceChain

logger = logging.getLogger(__name__)


class BehaviorTraceService:
    """行为追溯链服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trace(
        self,
        agent_id: str,
        agent_name: str,
        action_type: str,
        input_data: Dict[str, Any],
        output_result: Dict[str, Any],
        action_description: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        operator_id: Optional[str] = None,
        parent_trace_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> DBBehaviorTrace:
        """
        创建行为追溯记录

        Args:
            agent_id: Agent 标识
            agent_name: Agent 名称
            action_type: 行为类型
            input_data: 输入数据
            output_result: 输出结果
            action_description: 行为描述
            resource_type: 资源类型
            resource_id: 资源 ID
            model_provider: 模型提供方
            model_name: 模型名称
            model_version: 模型版本
            operator_id: 运营者 ID
            parent_trace_id: 父追溯 ID
            trace_id: 追溯链 ID（可选，自动生成）

        Returns:
            创建的追溯记录
        """
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        db_trace = DBBehaviorTrace(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            agent_id=agent_id,
            agent_name=agent_name,
            model_provider=model_provider,
            model_name=model_name,
            model_version=model_version,
            operator_id=operator_id,
            action_type=action_type,
            action_description=action_description,
            resource_type=resource_type,
            resource_id=resource_id,
            input_data=input_data,
            output_result=output_result,
            started_at=datetime.now(),
            status=BehaviorTraceStatus.IN_PROGRESS.value
        )

        self.db.add(db_trace)
        await self.db.commit()
        await self.db.refresh(db_trace)

        logger.debug(f"创建行为追溯记录：{db_trace.id} ({action_type})")
        return db_trace

    async def complete_trace(
        self,
        trace_id: str,
        output_result: Optional[Dict[str, Any]] = None,
        decision_process: Optional[Dict[str, Any]] = None,
        rules_applied: Optional[List[str]] = None,
        confidence_score: Optional[float] = None,
        risk_assessment: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> DBBehaviorTrace:
        """
        完成行为追溯记录

        Args:
            trace_id: 追溯记录 ID
            output_result: 输出结果
            decision_process: 决策过程详情
            rules_applied: 应用的规则列表
            confidence_score: 置信度分数
            risk_assessment: 风险评估结果
            error_message: 错误信息
            duration_ms: 耗时（毫秒）

        Returns:
            更新后的追溯记录
        """
        # 获取追溯记录
        result = await self.db.execute(
            select(DBBehaviorTrace).where(DBBehaviorTrace.id == trace_id)
        )
        trace = result.scalar_one_or_none()

        if not trace:
            raise ValueError(f"追溯记录 {trace_id} 不存在")

        # 更新字段
        if output_result is not None:
            trace.output_result = output_result

        if decision_process is not None:
            trace.decision_process = decision_process

        if rules_applied is not None:
            trace.rules_applied = rules_applied

        if confidence_score is not None:
            trace.confidence_score = confidence_score

        if risk_assessment is not None:
            trace.risk_assessment = risk_assessment

        trace.completed_at = datetime.now()
        trace.duration_ms = duration_ms

        if error_message:
            trace.status = BehaviorTraceStatus.FAILED.value
            trace.error_message = error_message
        else:
            trace.status = BehaviorTraceStatus.COMPLETED.value

        await self.db.commit()
        await self.db.refresh(trace)

        logger.info(f"完成行为追溯记录：{trace_id}, 状态：{trace.status}")
        return trace

    async def add_feedback(
        self,
        trace_id: str,
        feedback: Dict[str, Any]
    ) -> DBBehaviorTrace:
        """
        添加用户反馈

        Args:
            trace_id: 追溯记录 ID
            feedback: 反馈数据

        Returns:
            更新后的追溯记录
        """
        result = await self.db.execute(
            select(DBBehaviorTrace).where(DBBehaviorTrace.id == trace_id)
        )
        trace = result.scalar_one_or_none()

        if not trace:
            raise ValueError(f"追溯记录 {trace_id} 不存在")

        # 合并反馈
        if trace.user_feedback is None:
            trace.user_feedback = {}

        if "ratings" not in trace.user_feedback:
            trace.user_feedback["ratings"] = []

        trace.user_feedback["ratings"].append(feedback)
        trace.user_feedback["last_updated"] = datetime.now().isoformat()

        await self.db.commit()
        await self.db.refresh(trace)

        return trace

    async def add_review_result(
        self,
        trace_id: str,
        review_result: Dict[str, Any]
    ) -> DBBehaviorTrace:
        """
        添加复核结果

        Args:
            trace_id: 追溯记录 ID
            review_result: 复核结果数据

        Returns:
            更新后的追溯记录
        """
        result = await self.db.execute(
            select(DBBehaviorTrace).where(DBBehaviorTrace.id == trace_id)
        )
        trace = result.scalar_one_or_none()

        if not trace:
            raise ValueError(f"追溯记录 {trace_id} 不存在")

        trace.review_result = review_result

        await self.db.commit()
        await self.db.refresh(trace)

        return trace

    async def get_trace(self, trace_id: str) -> Optional[DBBehaviorTrace]:
        """获取追溯记录"""
        result = await self.db.execute(
            select(DBBehaviorTrace).where(DBBehaviorTrace.id == trace_id)
        )
        return result.scalar_one_or_none()

    async def get_trace_by_trace_id(self, trace_id: str) -> Optional[DBBehaviorTrace]:
        """根据 trace_id 获取追溯记录"""
        result = await self.db.execute(
            select(DBBehaviorTrace).where(DBBehaviorTrace.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def get_trace_chain(self, root_trace_id: str) -> Optional[TraceChain]:
        """
        获取追溯链（包含所有子追溯）

        Args:
            root_trace_id: 根追溯 ID

        Returns:
            追溯链对象
        """
        # 获取根追溯
        root = await self.get_trace(root_trace_id)
        if not root:
            return None

        # 获取所有子追溯
        result = await self.db.execute(
            select(DBBehaviorTrace)
            .where(DBBehaviorTrace.parent_trace_id == root_trace_id)
            .order_by(DBBehaviorTrace.started_at)
        )
        children = result.scalars().all()

        # 递归获取孙子追溯
        all_descendants = []
        for child in children:
            descendant_chain = await self._get_all_descendants(child.id)
            all_descendants.extend(descendant_chain)

        # 计算总耗时
        total_duration = sum(
            (t.duration_ms or 0) for t in [root] + children + all_descendants
        )

        # 构建决策路径
        decision_path = [root.action_type] + [c.action_type for c in children]

        return TraceChain(
            chain_id=root.trace_id,
            root_trace=self._db_trace_to_entity(root),
            child_traces=[self._db_trace_to_entity(c) for c in children],
            total_duration_ms=total_duration,
            decision_path=decision_path
        )

    async def _get_all_descendants(self, parent_id: str) -> List[DBBehaviorTrace]:
        """递归获取所有后代追溯"""
        result = await self.db.execute(
            select(DBBehaviorTrace)
            .where(DBBehaviorTrace.parent_trace_id == parent_id)
        )
        children = result.scalars().all()

        descendants = list(children)
        for child in children:
            descendants.extend(await self._get_all_descendants(child.id))

        return descendants

    def _db_trace_to_entity(self, db_trace: DBBehaviorTrace) -> 'BehaviorTrace':
        """将 DB 模型转换为实体模型"""
        from models.p6_entities import BehaviorTrace as EntityBehaviorTrace

        return EntityBehaviorTrace(
            id=db_trace.id,
            trace_id=db_trace.trace_id,
            parent_trace_id=db_trace.parent_trace_id,
            agent_id=db_trace.agent_id,
            agent_name=db_trace.agent_name,
            model_provider=db_trace.model_provider,
            model_name=db_trace.model_name,
            model_version=db_trace.model_version,
            operator_id=db_trace.operator_id,
            action_type=db_trace.action_type,
            action_description=db_trace.action_description,
            resource_type=db_trace.resource_type,
            resource_id=db_trace.resource_id,
            input_data=db_trace.input_data,
            decision_process=db_trace.decision_process,
            output_result=db_trace.output_result,
            rules_applied=db_trace.rules_applied or [],
            confidence_score=db_trace.confidence_score,
            risk_assessment=db_trace.risk_assessment,
            started_at=db_trace.started_at,
            completed_at=db_trace.completed_at,
            duration_ms=db_trace.duration_ms,
            status=BehaviorTraceStatus(db_trace.status),
            error_message=db_trace.error_message,
            user_feedback=db_trace.user_feedback,
            review_result=db_trace.review_result,
            ip_address=db_trace.ip_address,
            metadata=db_trace.trace_metadata or {}
        )

    async def list_traces(
        self,
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[BehaviorTraceStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DBBehaviorTrace]:
        """
        查询追溯记录列表

        Args:
            agent_id: Agent ID 过滤
            action_type: 行为类型过滤
            resource_type: 资源类型过滤
            resource_id: 资源 ID 过滤
            status: 状态过滤
            start_time: 开始时间过滤
            end_time: 结束时间过滤
            limit: 返回数量
            offset: 偏移量

        Returns:
            追溯记录列表
        """
        query = select(DBBehaviorTrace)

        # 应用过滤条件
        conditions = []
        if agent_id:
            conditions.append(DBBehaviorTrace.agent_id == agent_id)
        if action_type:
            conditions.append(DBBehaviorTrace.action_type == action_type)
        if resource_type:
            conditions.append(DBBehaviorTrace.resource_type == resource_type)
        if resource_id:
            conditions.append(DBBehaviorTrace.resource_id == resource_id)
        if status:
            conditions.append(DBBehaviorTrace.status == status.value)
        if start_time:
            conditions.append(DBBehaviorTrace.started_at >= start_time)
        if end_time:
            conditions.append(DBBehaviorTrace.started_at <= end_time)

        if conditions:
            query = query.where(and_(*conditions))

        # 排序和分页
        query = query.order_by(desc(DBBehaviorTrace.started_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_statistics(
        self,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取行为追溯统计信息

        Args:
            agent_id: Agent ID 过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息字典
        """
        # 构建基础查询条件
        conditions = []
        if agent_id:
            conditions.append(DBBehaviorTrace.agent_id == agent_id)
        if start_time:
            conditions.append(DBBehaviorTrace.started_at >= start_time)
        if end_time:
            conditions.append(DBBehaviorTrace.started_at <= end_time)

        # 总追溯数
        query = select(func.count(DBBehaviorTrace.id))
        if conditions:
            query = query.where(and_(*conditions))
        result = await self.db.execute(query)
        total_traces = result.scalar() or 0

        # 各状态数量
        status_query = select(
            DBBehaviorTrace.status,
            func.count(DBBehaviorTrace.id)
        )
        if conditions:
            status_query = status_query.where(and_(*conditions))
        status_query = status_query.group_by(DBBehaviorTrace.status)
        result = await self.db.execute(status_query)
        status_counts = dict(result.all())

        # 平均响应时间
        duration_query = select(func.avg(DBBehaviorTrace.duration_ms))
        if conditions:
            duration_query = duration_query.where(and_(*conditions))
        result = await self.db.execute(duration_query)
        avg_duration = result.scalar() or 0

        # 平均置信度
        confidence_query = select(func.avg(DBBehaviorTrace.confidence_score))
        if conditions:
            confidence_query = confidence_query.where(and_(*conditions))
        result = await self.db.execute(confidence_query)
        avg_confidence = result.scalar() or 0

        # 行为类型分布
        type_query = select(
            DBBehaviorTrace.action_type,
            func.count(DBBehaviorTrace.id)
        )
        if conditions:
            type_query = type_query.where(and_(*conditions))
        type_query = type_query.group_by(DBBehaviorTrace.action_type)
        result = await self.db.execute(type_query)
        type_counts = dict(result.all())

        return {
            "total_traces": total_traces,
            "status_counts": status_counts,
            "avg_duration_ms": round(avg_duration, 2),
            "avg_confidence_score": round(avg_confidence, 3) if avg_confidence else None,
            "action_type_counts": type_counts
        }

    async def get_trace_transparency_report(
        self,
        trace_id: str
    ) -> Dict[str, Any]:
        """
        生成追溯记录透明度报告

        Args:
            trace_id: 追溯记录 ID

        Returns:
            透明度报告字典
        """
        trace = await self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"追溯记录 {trace_id} 不存在")

        # 评估透明度
        transparency_factors = {
            "has_decision_process": bool(trace.decision_process),
            "has_rules_applied": bool(trace.rules_applied),
            "has_confidence_score": trace.confidence_score is not None,
            "has_risk_assessment": bool(trace.risk_assessment),
            "has_model_info": bool(trace.model_name or trace.model_provider),
            "has_operator_info": bool(trace.operator_id),
            "has_timing_info": trace.duration_ms is not None,
        }

        transparency_score = sum(transparency_factors.values()) / len(transparency_factors)

        return {
            "trace_id": trace.trace_id,
            "agent_id": trace.agent_id,
            "agent_name": trace.agent_name,
            "action_type": trace.action_type,
            "transparency_score": round(transparency_score, 3),
            "transparency_factors": transparency_factors,
            "decision_process": trace.decision_process,
            "rules_applied": trace.rules_applied,
            "confidence_score": trace.confidence_score,
            "risk_assessment": trace.risk_assessment,
            "model_info": {
                "provider": trace.model_provider,
                "name": trace.model_name,
                "version": trace.model_version
            },
            "operator_id": trace.operator_id,
            "timing": {
                "started_at": trace.started_at.isoformat() if trace.started_at else None,
                "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
                "duration_ms": trace.duration_ms
            }
        }

    async def get_visualization_data(
        self,
        root_trace_id: str
    ) -> Dict[str, Any]:
        """
        获取行为追溯链可视化数据

        Args:
            root_trace_id: 根追溯 ID

        Returns:
            可视化数据字典，包含节点和边信息
        """
        chain = await self.get_trace_chain(root_trace_id)
        if not chain:
            raise ValueError(f"追溯链 {root_trace_id} 不存在")

        # 构建节点数据
        nodes = []
        edges = []

        # 添加根节点
        root = chain.root_trace
        nodes.append({
            "id": root.trace_id,
            "label": f"{root.agent_name}\n{root.action_type}",
            "type": "root",
            "agent_id": root.agent_id,
            "agent_name": root.agent_name,
            "action_type": root.action_type,
            "status": root.status.value,
            "confidence_score": root.confidence_score,
            "duration_ms": root.duration_ms,
            "started_at": root.started_at.isoformat() if root.started_at else None,
            "completed_at": root.completed_at.isoformat() if root.completed_at else None
        })

        # 添加子节点和边
        for child in chain.child_traces:
            nodes.append({
                "id": child.trace_id,
                "label": f"{child.agent_name}\n{child.action_type}",
                "type": "child",
                "agent_id": child.agent_id,
                "agent_name": child.agent_name,
                "action_type": child.action_type,
                "status": child.status.value,
                "confidence_score": child.confidence_score,
                "duration_ms": child.duration_ms,
                "started_at": child.started_at.isoformat() if child.started_at else None,
                "completed_at": child.completed_at.isoformat() if child.completed_at else None
            })

            # 添加边
            edges.append({
                "source": root.trace_id,
                "target": child.trace_id,
                "label": "trigger",
                "type": "sequential"
            })

        # 计算决策路径深度
        max_depth = self._calculate_tree_depth(chain.child_traces)

        return {
            "chain_id": chain.chain_id,
            "total_duration_ms": chain.total_duration_ms,
            "decision_path": chain.decision_path,
            "depth": max_depth + 1,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "visualization": {
                "nodes": nodes,
                "edges": edges
            },
            "summary": {
                "root_action": root.action_type,
                "root_agent": root.agent_name,
                "child_actions": [c.action_type for c in chain.child_traces],
                "total_agents": len(set([root.agent_id] + [c.agent_id for c in chain.child_traces]))
            }
        }

    def _calculate_tree_depth(self, children: List) -> int:
        """计算树形结构的深度"""
        if not children:
            return 0

        max_child_depth = 0
        for child in children:
            # 递归计算子节点的深度
            child_depth = 1
            if hasattr(child, 'child_traces') and child.child_traces:
                child_depth += self._calculate_tree_depth(child.child_traces)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    async def get_agent_trace_timeline(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取 AI Agent 行为追溯时间线数据

        Args:
            agent_id: Agent ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            时间线数据字典
        """
        traces = await self.list_traces(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        timeline_events = []
        for trace in traces:
            event = {
                "trace_id": trace.trace_id,
                "timestamp": trace.started_at.isoformat() if trace.started_at else None,
                "action_type": trace.action_type,
                "status": trace.status.value,
                "duration_ms": trace.duration_ms,
                "confidence_score": trace.confidence_score,
                "resource_type": trace.resource_type,
                "resource_id": trace.resource_id
            }
            timeline_events.append(event)

        # 按时间排序
        timeline_events.sort(key=lambda x: x["timestamp"] or "")

        # 计算统计信息
        total_duration = sum(t["duration_ms"] or 0 for t in timeline_events)
        avg_confidence = sum(t["confidence_score"] or 0 for t in timeline_events) / len(timeline_events) if timeline_events else 0

        return {
            "agent_id": agent_id,
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "total_events": len(timeline_events),
            "total_duration_ms": total_duration,
            "avg_confidence_score": round(avg_confidence, 3),
            "timeline": timeline_events
        }

    async def get_trace_graph_stats(
        self,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取行为追溯图谱统计信息

        Args:
            agent_id: Agent ID 过滤
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            图谱统计信息字典
        """
        # 获取追溯列表
        traces = await self.list_traces(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )

        # 统计行为类型分布
        action_type_dist = {}
        # 统计 Agent 分布
        agent_dist = {}
        # 统计状态分布
        status_dist = {}
        # 统计资源类型分布
        resource_type_dist = {}

        for trace in traces:
            # 行为类型
            action_type = trace.action_type
            action_type_dist[action_type] = action_type_dist.get(action_type, 0) + 1

            # Agent
            agent_id_key = trace.agent_id
            agent_dist[agent_id_key] = agent_dist.get(agent_id_key, 0) + 1

            # 状态
            status = trace.status.value
            status_dist[status] = status_dist.get(status, 0) + 1

            # 资源类型
            if trace.resource_type:
                resource_type_dist[trace.resource_type] = resource_type_dist.get(trace.resource_type, 0) + 1

        # 计算平均置信度
        confidence_scores = [t.confidence_score for t in traces if t.confidence_score is not None]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # 计算平均耗时
        durations = [t.duration_ms for t in traces if t.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_traces": len(traces),
            "action_type_distribution": action_type_dist,
            "agent_distribution": agent_dist,
            "status_distribution": status_dist,
            "resource_type_distribution": resource_type_dist,
            "avg_confidence_score": round(avg_confidence, 3),
            "avg_duration_ms": round(avg_duration, 2),
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }


# 全局服务实例
_behavior_trace_service: Optional[BehaviorTraceService] = None


def get_behavior_trace_service(db: AsyncSession) -> BehaviorTraceService:
    """获取行为追溯链服务实例"""
    global _behavior_trace_service
    if _behavior_trace_service is None or _behavior_trace_service.db is not db:
        _behavior_trace_service = BehaviorTraceService(db)
    return _behavior_trace_service
