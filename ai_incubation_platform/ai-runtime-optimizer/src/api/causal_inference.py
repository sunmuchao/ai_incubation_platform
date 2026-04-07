"""
因果推断根因分析 API v2.2
基于 Pearl 因果推断理论和贝叶斯网络的根因定位系统

功能：
1. 因果图构建和查询
2. 贝叶斯因果推断
3. 根因分析
4. 因果效应量化
5. 反事实推理
6. 因果链可视化
"""
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from core.causal_inference import (
    get_causal_inference_engine,
    CausalInferenceEngine,
    create_sample_causal_graph
)
from core.service_map import service_map

router = APIRouter(prefix="/api/root-cause/v2.2", tags=["root-cause-v2.2"])


# ==================== 请求/响应模型 ====================

class CausalGraphBuildRequest(BaseModel):
    """因果图构建请求"""
    service_map_data: Optional[Dict[str, Any]] = Field(
        None,
        description="服务映射数据，如果不传则从 service_map 获取"
    )


class CausalGraphResponse(BaseModel):
    """因果图响应"""
    graph: Dict[str, Any]
    is_dag: bool
    num_nodes: int
    num_edges: int


class RootCauseAnalysisRequest(BaseModel):
    """根因分析请求"""
    evidence: Optional[Dict[str, Any]] = Field(
        None,
        description="观察到的证据（异常服务列表、指标数据等）"
    )
    lookback_minutes: int = Field(
        default=30,
        description="回溯时间（分钟）",
        ge=5,
        le=120
    )
    include_counterfactual: bool = Field(
        default=True,
        description="是否包含反事实分析"
    )
    include_visualization: bool = Field(
        default=True,
        description="是否包含可视化数据"
    )


class ConfidenceFactorResponse(BaseModel):
    """置信度因子响应"""
    statistical: float = Field(description="统计置信度（贝叶斯后验概率）")
    causal: float = Field(description="因果置信度（因果效应强度）")
    temporal: float = Field(description="时间置信度（时间先后顺序）")
    structural: float = Field(description="结构置信度（拓扑位置）")
    consistency: float = Field(description="一致性置信度（多源证据一致）")


class RootCauseHypothesisResponse(BaseModel):
    """根因假设响应"""
    hypothesis_id: str
    candidate_service: str
    root_cause_type: str
    prior_probability: float
    posterior_probability: float
    likelihood: float
    total_effect: float
    direct_effect: float
    indirect_effect: float
    confidence_score: float
    confidence_factors: Dict[str, float]
    evidence: List[Dict[str, Any]]
    counterfactual: Optional[Dict[str, Any]]


class RootCauseAnalysisResponse(BaseModel):
    """根因分析响应"""
    analysis_id: str
    timestamp: str
    summary: str
    root_causes: List[RootCauseHypothesisResponse]
    confidence_level: str
    recommendations: List[str]
    visualization: Optional[Dict[str, Any]]
    causal_graph: Optional[Dict[str, Any]]


class CausalEffectRequest(BaseModel):
    """因果效应计算请求"""
    cause_node: str = Field(..., description="原因节点 ID")
    effect_node: str = Field(..., description="结果节点 ID")
    intervention_value: str = Field(
        default="failed",
        description="干预值（failed, degraded, normal）"
    )


class CausalEffectResponse(BaseModel):
    """因果效应响应"""
    cause_node: str
    effect_node: str
    total_effect: float
    direct_effect: float
    indirect_effect: float
    interpretation: str


class CounterfactualRequest(BaseModel):
    """反事实推理请求"""
    hypothesis_id: str = Field(..., description="根因假设 ID")
    intervention: str = Field(
        default="normal",
        description="反事实干预（假设节点状态）"
    )


class CounterfactualResponse(BaseModel):
    """反事实推理响应"""
    intervention: str
    counterfactual_outcomes: Dict[str, Any]
    total_anomaly_reduction: float
    services_would_be_normal: int
    total_affected_services: int


class CausalPathQueryRequest(BaseModel):
    """因果路径查询请求"""
    source_node: str = Field(..., description="源节点 ID")
    target_node: str = Field(..., description="目标节点 ID")
    max_depth: int = Field(default=5, ge=1, le=10)


class CausalPathResponse(BaseModel):
    """因果路径响应"""
    paths: List[Dict[str, Any]]
    total_paths: int


class DSeparationRequest(BaseModel):
    """d-分离查询请求"""
    node_x: str = Field(..., description="节点 X")
    node_y: str = Field(..., description="节点 Y")
    condition_set: List[str] = Field(default=[], description="条件集 Z")


class DSeparationResponse(BaseModel):
    """d-分离响应"""
    is_d_separated: bool
    explanation: str


# ==================== 核心 API ====================

@router.post("/build-graph", response_model=CausalGraphResponse)
async def build_causal_graph(request: CausalGraphBuildRequest):
    """
    构建因果图

    从服务映射数据构建因果结构（DAG）
    """
    try:
        engine = get_causal_inference_engine()

        # 获取服务映射数据
        if request.service_map_data:
            service_map_data = request.service_map_data
        else:
            service_map_data = service_map.get_service_map_data()
            # 转换为因果图需要的格式
            service_map_data = {
                "services": [
                    {
                        "id": node["id"],
                        "name": node["name"],
                        "type": node["type"],
                        "health_status": node["health_status"],
                        "metrics": node["metrics"]
                    }
                    for node in service_map_data.get("nodes", [])
                ],
                "edges": [
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "dependency_type": edge["dependency_type"],
                        "metrics": edge["metrics"]
                    }
                    for edge in service_map_data.get("edges", [])
                ]
            }

        # 构建因果图
        engine.build_graph_from_service_map(service_map_data)

        # 返回图信息
        graph_data = engine.graph.to_dict()

        return CausalGraphResponse(
            graph=graph_data,
            is_dag=graph_data["is_dag"],
            num_nodes=graph_data["num_nodes"],
            num_edges=graph_data["num_edges"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build causal graph: {str(e)}")


@router.post("/analyze", response_model=RootCauseAnalysisResponse)
async def analyze_root_cause(request: RootCauseAnalysisRequest):
    """
    执行因果推断根因分析

    基于贝叶斯网络和因果推断理论进行根因定位
    """
    try:
        engine = get_causal_inference_engine()

        # 检查因果图是否已构建
        if not engine.graph._nodes:
            # 自动构建因果图
            service_map_data = service_map.get_service_map_data()
            service_map_data = {
                "services": [
                    {
                        "id": node["id"],
                        "name": node["name"],
                        "type": node["type"],
                        "health_status": node["health_status"],
                        "metrics": node["metrics"]
                    }
                    for node in service_map_data.get("nodes", [])
                ],
                "edges": [
                    {
                        "source": edge["source"],
                        "target": edge["target"],
                        "dependency_type": edge["dependency_type"],
                        "metrics": edge["metrics"]
                    }
                    for edge in service_map_data.get("edges", [])
                ]
            }
            engine.build_graph_from_service_map(service_map_data)

        # 执行分析
        result = engine.analyze(
            evidence=request.evidence,
            lookback_minutes=request.lookback_minutes
        )

        # 处理响应
        root_causes = []
        for rc in result.get("root_causes", []):
            root_causes.append(RootCauseHypothesisResponse(
                hypothesis_id=rc["hypothesis_id"],
                candidate_service=rc["candidate_service"],
                root_cause_type=rc["root_cause_type"],
                prior_probability=rc["prior_probability"],
                posterior_probability=rc["posterior_probability"],
                likelihood=rc["likelihood"],
                total_effect=rc["total_effect"],
                direct_effect=rc["direct_effect"],
                indirect_effect=rc["indirect_effect"],
                confidence_score=rc["confidence_score"],
                confidence_factors=rc["confidence_factors"],
                evidence=rc["evidence"],
                counterfactual=rc.get("counterfactual") if request.include_counterfactual else None
            ))

        visualization = None
        if request.include_visualization and "visualization" in result:
            visualization = result["visualization"]

        causal_graph = None
        if "causal_graph" in result:
            causal_graph = result["causal_graph"]

        return RootCauseAnalysisResponse(
            analysis_id=result["analysis_id"],
            timestamp=result["timestamp"],
            summary=result["summary"],
            root_causes=root_causes,
            confidence_level=result.get("confidence_level", "unknown"),
            recommendations=result.get("recommendations", []),
            visualization=visualization,
            causal_graph=causal_graph
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Root cause analysis failed: {str(e)}")


@router.post("/causal-effect", response_model=CausalEffectResponse)
async def compute_causal_effect(request: CausalEffectRequest):
    """
    计算因果效应

    使用 do-演算计算干预效应 P(Y | do(X))
    """
    try:
        engine = get_causal_inference_engine()

        if not engine.bayesian_inference:
            raise HTTPException(
                status_code=400,
                detail="Causal graph not built. Please call /build-graph first."
            )

        # 计算因果效应
        total, direct, indirect = engine.bayesian_inference.compute_causal_effect(
            request.cause_node,
            request.effect_node,
            request.intervention_value
        )

        # 生成解释
        if total > 0.7:
            interpretation = f"强因果关系：{request.cause_node} 对 {request.effect_node} 有显著影响"
        elif total > 0.4:
            interpretation = f"中等因果关系：{request.cause_node} 对 {request.effect_node} 有一定影响"
        elif total > 0.1:
            interpretation = f"弱因果关系：{request.cause_node} 对 {request.effect_node} 影响较小"
        else:
            interpretation = f"无明显因果关系：{request.cause_node} 对 {request.effect_node} 影响微乎其微"

        return CausalEffectResponse(
            cause_node=request.cause_node,
            effect_node=request.effect_node,
            total_effect=total,
            direct_effect=direct,
            indirect_effect=indirect,
            interpretation=interpretation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Causal effect computation failed: {str(e)}")


@router.post("/counterfactual", response_model=CounterfactualResponse)
async def compute_counterfactual(request: CounterfactualRequest):
    """
    执行反事实推理

    回答"如果 X 没有发生，Y 会怎样？"的问题
    """
    try:
        engine = get_causal_inference_engine()

        if not engine.bayesian_inference:
            raise HTTPException(
                status_code=400,
                detail="Causal graph not built. Please call /build-graph first."
            )

        # 获取最近的根因假设
        history = engine.get_analysis_history(limit=10)

        if not history:
            raise HTTPException(
                status_code=404,
                detail="No recent root cause analysis found. Please run analysis first."
            )

        # 查找指定的假设
        target_hypothesis = None
        for analysis in history:
            for hypothesis in analysis.get("all_hypotheses", []):
                if hypothesis.get("hypothesis_id") == request.hypothesis_id:
                    target_hypothesis = hypothesis
                    break
            if target_hypothesis:
                break

        if not target_hypothesis:
            raise HTTPException(
                status_code=404,
                detail=f"Hypothesis {request.hypothesis_id} not found"
            )

        # 计算反事实
        from core.causal_inference import RootCauseHypothesis
        hypothesis = RootCauseHypothesis(
            hypothesis_id=target_hypothesis["hypothesis_id"],
            candidate_service=target_hypothesis["candidate_service"],
            root_cause_type=target_hypothesis["root_cause_type"],
            prior_probability=target_hypothesis["prior_probability"],
            posterior_probability=target_hypothesis["posterior_probability"],
            likelihood=target_hypothesis["likelihood"],
            total_effect=target_hypothesis["total_effect"],
            direct_effect=target_hypothesis["direct_effect"],
            indirect_effect=target_hypothesis["indirect_effect"],
            confidence_score=target_hypothesis["confidence_score"],
            confidence_factors=target_hypothesis["confidence_factors"],
            evidence=target_hypothesis["evidence"]
        )

        counterfactual = engine.bayesian_inference.compute_counterfactual(
            hypothesis,
            {"metrics": {}}
        )

        return CounterfactualResponse(
            intervention=counterfactual["intervention"],
            counterfactual_outcomes=counterfactual["counterfactual_outcomes"],
            total_anomaly_reduction=counterfactual["total_anomaly_reduction"],
            services_would_be_normal=counterfactual["services_would_be_normal"],
            total_affected_services=counterfactual["total_affected_services"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counterfactual reasoning failed: {str(e)}")


@router.post("/paths", response_model=CausalPathResponse)
async def query_causal_paths(request: CausalPathQueryRequest):
    """
    查询因果路径

    获取从源节点到目标节点的所有因果路径
    """
    try:
        engine = get_causal_inference_engine()

        if not engine.graph._nodes:
            raise HTTPException(
                status_code=400,
                detail="Causal graph not built. Please call /build-graph first."
            )

        # 查询路径
        paths = engine.graph.get_all_paths(
            request.source_node,
            request.target_node,
            max_depth=request.max_depth
        )

        # 格式化路径
        formatted_paths = []
        for path in paths:
            # 计算路径的因果效应
            total_effect = 1.0
            for i in range(len(path) - 1):
                edge = engine.graph.get_edge(path[i], path[i+1])
                if edge:
                    total_effect *= edge.causal_strength

            formatted_paths.append({
                "path": path,
                "length": len(path),
                "total_causal_effect": total_effect,
                "nodes": [
                    {
                        "id": node_id,
                        "name": engine.graph.get_node(node_id).name if engine.graph.get_node(node_id) else node_id
                    }
                    for node_id in path
                ]
            })

        return CausalPathResponse(
            paths=formatted_paths,
            total_paths=len(formatted_paths)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Path query failed: {str(e)}")


@router.post("/d-separation", response_model=DSeparationResponse)
async def query_d_separation(request: DSeparationRequest):
    """
    查询 d-分离

    判断在给定条件集 Z 下，X 和 Y 是否条件独立
    """
    try:
        engine = get_causal_inference_engine()

        if not engine.graph._nodes:
            raise HTTPException(
                status_code=400,
                detail="Causal graph not built. Please call /build-graph first."
            )

        # 判断 d-分离
        from core.causal_inference import CausalMarkovCondition
        is_separated = CausalMarkovCondition.d_separation(
            engine.graph,
            request.node_x,
            request.node_y,
            set(request.condition_set)
        )

        # 生成解释
        if is_separated:
            if request.condition_set:
                explanation = (
                    f"在给定 {request.condition_set} 的条件下，"
                    f"{request.node_x} 和 {request.node_y} 是 d-分离的（条件独立）。"
                    f"这意味着控制 {request.condition_set} 后，{request.node_x} 和 {request.node_y} 之间没有信息流动。"
                )
            else:
                explanation = (
                    f"{request.node_x} 和 {request.node_y} 是 d-分离的（边缘独立）。"
                    f"这意味着两者之间没有直接的因果路径。"
                )
        else:
            if request.condition_set:
                explanation = (
                    f"在给定 {request.condition_set} 的条件下，"
                    f"{request.node_x} 和 {request.node_y} 不是 d-分离的（存在依赖关系）。"
                    f"这可能意味着存在未阻断的因果路径或共同原因。"
                )
            else:
                explanation = (
                    f"{request.node_x} 和 {request.node_y} 不是 d-分离的（存在依赖关系）。"
                    f"这意味着两者之间可能存在因果路径或共同原因。"
                )

        return DSeparationResponse(
            is_d_separated=is_separated,
            explanation=explanation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D-separation query failed: {str(e)}")


@router.get("/graph")
async def get_causal_graph():
    """获取当前因果图"""
    try:
        engine = get_causal_inference_engine()

        if not engine.graph._nodes:
            return {
                "graph": None,
                "message": "Causal graph not built yet. Please call /build-graph first."
            }

        return engine.graph.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get causal graph: {str(e)}")


@router.get("/hypotheses")
async def get_root_cause_hypotheses(limit: int = 10):
    """获取最近的根因假设"""
    try:
        engine = get_causal_inference_engine()
        history = engine.get_analysis_history(limit=limit)

        all_hypotheses = []
        for analysis in history:
            for hypothesis in analysis.get("all_hypotheses", []):
                all_hypotheses.append(hypothesis)

        # 按置信度排序
        all_hypotheses.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

        return {
            "hypotheses": all_hypotheses[:limit],
            "total_count": len(all_hypotheses)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hypotheses: {str(e)}")


@router.get("/history")
async def get_analysis_history(limit: int = 10):
    """获取根因分析历史"""
    try:
        engine = get_causal_inference_engine()
        history = engine.get_analysis_history(limit=limit)
        return {
            "history": history,
            "total_count": len(history)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis history: {str(e)}")


@router.post("/reset")
async def reset_causal_graph():
    """重置因果图"""
    try:
        global _causal_inference_engine
        from core.causal_inference import _causal_inference_engine
        _causal_inference_engine = None

        return {
            "status": "success",
            "message": "Causal graph has been reset"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset causal graph: {str(e)}")


@router.post("/sample")
async def create_sample_graph():
    """创建示例因果图（用于测试和演示）"""
    try:
        from core.causal_inference import create_sample_causal_graph

        graph = create_sample_causal_graph()

        return {
            "status": "success",
            "message": "Sample causal graph created",
            "graph": graph.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sample graph: {str(e)}")
