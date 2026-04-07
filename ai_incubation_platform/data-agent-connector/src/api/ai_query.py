"""
AI 查询 API 路由 - NL2SQL AI 驱动和 Schema 自动演进
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.nl2sql_ai_service import nl2sql_ai_service, NL2SQLAIService
from services.nl2sql_ai_service_enhanced import nl2sql_ai_service_enhanced, NL2SQLAIServiceEnhanced
from services.schema_evolution_service import schema_evolution_service, SchemaEvolutionService
from core.connection_manager import connection_manager
from .deps import verify_api_key, get_user_role
from utils.logger import logger
from config.settings import settings

router = APIRouter(prefix="/api/ai", tags=["ai-query"], dependencies=[Depends(verify_api_key)])


class AIQueryRequest(BaseModel):
    """AI 查询请求"""
    connector_name: str
    natural_language: str
    use_llm: Optional[bool] = True


class AIQueryResponse(BaseModel):
    """AI 查询响应"""
    success: bool
    sql: str
    intent: Dict[str, Any]
    confidence: float
    validation: Dict[str, Any]
    suggestions: List[str]
    data: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None
    execution_time_ms: Optional[float] = None


class SchemaCompareRequest(BaseModel):
    """Schema 比较请求"""
    connector_name: str
    from_version: int
    to_version: Optional[int] = None


class MigrationScriptRequest(BaseModel):
    """迁移脚本请求"""
    connector_name: str
    from_version: int
    to_version: Optional[int] = None
    dialect: str = "postgresql"


@router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    request: AIQueryRequest,
    role: str = Depends(get_user_role)
):
    """
    AI 驱动的自然语言查询

    使用 LLM 将自然语言转换为 SQL，并提供：
    - 查询意图识别
    - SQL 验证和安全检查
    - 查询优化建议
    - 结果解释生成
    """
    try:
        # 获取连接器 Schema
        connector = await connection_manager.get_connector(request.connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {request.connector_name} 不存在"
            )

        # 获取 Schema
        schema = nl2sql_ai_service._llm_provider._format_schema if hasattr(nl2sql_ai_service._llm_provider, '_format_schema') else {}
        schema = await connector.get_schema()

        # 使用 AI 服务转换 SQL
        result = await nl2sql_ai_service.convert_to_sql(
            natural_language=request.natural_language,
            schema=schema,
            use_llm=request.use_llm if request.use_llm is not None else settings.ai.nl2sql_use_llm
        )

        # 检查 SQL 是否有效
        if not result["validation"]["is_valid"]:
            return AIQueryResponse(
                success=False,
                sql="",
                intent=result["intent"],
                confidence=result["confidence"],
                validation=result["validation"],
                suggestions=result["suggestions"]
            )

        # 执行 SQL
        from core.query_engine import query_engine
        exec_result = await query_engine.execute_query(
            connector_name=request.connector_name,
            query=result["sql"],
            role=role
        )

        # 生成结果解释（如果启用）
        explanation = None
        if settings.ai.enable_result_explanation and exec_result.success:
            try:
                explanation = await nl2sql_ai_service.explain_result(
                    natural_language=request.natural_language,
                    sql=result["sql"],
                    result=exec_result.data or [],
                    schema=schema
                )
            except Exception as e:
                logger.warning("Result explanation generation failed", extra={"error": str(e)})

        return AIQueryResponse(
            success=exec_result.success,
            sql=result["sql"],
            intent=result["intent"],
            confidence=result["confidence"],
            validation=result["validation"],
            suggestions=result["suggestions"],
            data=exec_result.data if exec_result.success else None,
            explanation=explanation,
            execution_time_ms=exec_result.execution_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI query failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"AI 查询失败：{str(e)}")


@router.post("/intent")
async def recognize_intent(
    connector_name: str,
    natural_language: str
):
    """识别查询意图"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )

        schema = await connector.get_schema()
        intent = await nl2sql_ai_service.llm_provider.recognize_intent(natural_language, schema)

        return {
            "success": True,
            "intent": intent.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Intent recognition failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"意图识别失败：{str(e)}")


@router.post("/explain")
async def explain_result(
    connector_name: str,
    natural_language: str,
    sql: str,
    result: List[Dict[str, Any]]
):
    """解释查询结果"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )

        schema = await connector.get_schema()
        explanation = await nl2sql_ai_service.explain_result(natural_language, sql, result, schema)

        return {
            "success": True,
            "explanation": explanation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Result explanation failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"结果解释失败：{str(e)}")


@router.post("/optimize")
async def suggest_optimization(
    connector_name: str,
    sql: str,
    execution_stats: Optional[Dict[str, Any]] = None
):
    """生成查询优化建议"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )

        schema = await connector.get_schema()
        suggestions = await nl2sql_ai_service.llm_provider.suggest_optimization(sql, schema, execution_stats)

        return {
            "success": True,
            "suggestions": suggestions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Optimization suggestion failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"优化建议生成失败：{str(e)}")


@router.get("/history")
async def get_query_history(
    limit: int = Query(100, ge=1, le=1000)
):
    """获取 AI 查询历史"""
    history = nl2sql_ai_service.get_query_history(limit)
    return {
        "success": True,
        "history": history,
        "count": len(history)
    }


@router.delete("/history")
async def clear_query_history():
    """清空 AI 查询历史"""
    nl2sql_ai_service.clear_history()
    return {
        "success": True,
        "message": "查询历史已清空"
    }


# Schema 自动演进 API


@router.post("/schema/register")
async def register_schema_version(
    connector_name: str,
    description: Optional[str] = None
):
    """注册新的 Schema 版本"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )

        # 获取最新 Schema
        new_schema = await connector.get_schema()

        # 注册版本
        version = await schema_evolution_service.register_schema(
            connector_name=connector_name,
            schema=new_schema,
            description=description or "自动注册的 Schema 版本"
        )

        return {
            "success": True,
            "version": version.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Schema registration failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Schema 注册失败：{str(e)}")


@router.get("/schema/history/{connector_name}")
async def get_schema_history(connector_name: str):
    """获取 Schema 版本历史"""
    history = schema_evolution_service.get_version_history(connector_name)
    return {
        "success": True,
        "history": history,
        "count": len(history)
    }


@router.get("/schema/current/{connector_name}")
async def get_current_schema(connector_name: str):
    """获取当前 Schema"""
    schema = schema_evolution_service.get_current_schema(connector_name)
    if not schema:
        # 尝试从连接器获取
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )
        schema = await connector.get_schema()

    return {
        "success": True,
        "schema": schema
    }


@router.get("/schema/version/{connector_name}/{version}")
async def get_schema_version(
    connector_name: str,
    version: int
):
    """获取指定版本的 Schema"""
    schema = schema_evolution_service.get_version(connector_name, version)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"版本 {version} 不存在"
        )

    return {
        "success": True,
        "schema": schema
    }


@router.post("/schema/compare")
async def compare_schema_versions(request: SchemaCompareRequest):
    """比较两个 Schema 版本"""
    result = schema_evolution_service.compare_versions(
        connector_name=request.connector_name,
        version1=request.from_version,
        version2=request.to_version or schema_evolution_service._current_version.get(request.connector_name, 0)
    )

    return {
        "success": True,
        "comparison": result
    }


@router.post("/schema/migration")
async def generate_migration_script(request: MigrationScriptRequest):
    """生成 Schema 迁移脚本"""
    script = schema_evolution_service.generate_migration_script(
        connector_name=request.connector_name,
        from_version=request.from_version,
        to_version=request.to_version or schema_evolution_service._current_version.get(request.connector_name, 0),
        dialect=request.dialect
    )

    return {
        "success": True,
        "migration_script": script
    }


@router.get("/schema/detect/{connector_name}")
async def detect_schema_changes(connector_name: str):
    """检测 Schema 变更"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(
                status_code=404,
                detail=f"数据源 {connector_name} 不存在"
            )

        # 获取当前缓存的 Schema
        old_schema = schema_evolution_service.get_current_schema(connector_name)
        if not old_schema:
            # 没有缓存，注册初始版本
            new_schema = await connector.get_schema()
            version = await schema_evolution_service.register_schema(connector_name, new_schema)
            return {
                "success": True,
                "message": "初始 Schema 已注册",
                "version": version.to_dict()
            }

        # 获取最新 Schema
        new_schema = await connector.get_schema()

        # 检测变更
        changes = await schema_evolution_service.detect_changes(connector_name, old_schema, new_schema)

        if not changes:
            return {
                "success": True,
                "message": "未检测到 Schema 变更",
                "changes": []
            }

        # 注册新版本
        version = await schema_evolution_service.register_schema(connector_name, new_schema)

        # 如果启用自动应用，尝试应用非破坏性变更
        applied_changes = []
        pending_changes = []
        if settings.ai.schema_auto_apply:
            for change in changes:
                result = await schema_evolution_service.auto_apply_schema_change(
                    connector_name, change, auto_approve=True
                )
                if result["status"] == "applied":
                    applied_changes.append({**change.to_dict(), "sql": result.get("sql")})
                else:
                    pending_changes.append(change.to_dict())
        else:
            pending_changes = [c.to_dict() for c in changes]

        return {
            "success": True,
            "version": version.to_dict(),
            "changes": [c.to_dict() for c in changes],
            "applied_changes": applied_changes,
            "pending_changes": pending_changes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Schema change detection failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Schema 变更检测失败：{str(e)}")


# ============== v1.3 增强版 NL2SQL API ==============

class EnhancedAIQueryResponse(BaseModel):
    """增强版 AI 查询响应"""
    success: bool
    sql: str
    intent: Dict[str, Any]
    confidence: float
    validation: Dict[str, Any]
    suggestions: List[str]
    data: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None
    execution_time_ms: Optional[float] = None
    clarification: Optional[Dict[str, Any]] = None
    few_shot_examples: Optional[List[Dict[str, Any]]] = None


class AIQueryRequestV2(BaseModel):
    """AI 查询请求 v2（支持增强功能）"""
    connector_name: str
    natural_language: str
    use_llm: Optional[bool] = True
    use_enhanced: Optional[bool] = True  # 是否使用增强版 NL2SQL
    enable_self_correction: Optional[bool] = True


@router.post("/query/v2", response_model=EnhancedAIQueryResponse)
async def ai_query_v2(
    request: AIQueryRequestV2,
    role: str = Depends(get_user_role)
):
    """
    AI 驱动的自然语言查询 v2（增强版）

    新增功能:
    - Few-Shot 示例学习
    - Schema 关系增强
    - 查询澄清机制
    - SQL 自校正
    """
    try:
        connector = await connection_manager.get_connector(request.connector_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"数据源 {request.connector_name} 不存在")

        schema = await connector.get_schema()

        # 使用增强版 AI 服务
        if request.use_enhanced:
            result = await nl2sql_ai_service_enhanced.convert_to_sql(
                natural_language=request.natural_language,
                schema=schema,
                use_llm=request.use_llm,
                enable_self_correction=request.enable_self_correction
            )
        else:
            # 使用基础服务
            result = await nl2sql_ai_service.convert_to_sql(
                natural_language=request.natural_language,
                schema=schema,
                use_llm=request.use_llm
            )

        if not result["validation"]["is_valid"]:
            return EnhancedAIQueryResponse(
                success=False,
                sql="",
                intent=result.get("intent", {}),
                confidence=result.get("confidence", 0.0),
                validation=result.get("validation", {}),
                suggestions=result.get("suggestions", []),
                clarification=result.get("clarification")
            )

        # 执行 SQL
        from core.query_engine import query_engine
        exec_result = await query_engine.execute_query(
            connector_name=request.connector_name,
            query=result["sql"],
            role=role
        )

        explanation = None
        if settings.ai.enable_result_explanation and exec_result.success:
            try:
                explanation = await nl2sql_ai_service.explain_result(
                    natural_language=request.natural_language,
                    sql=result["sql"],
                    result=exec_result.data or [],
                    schema=schema
                )
            except Exception as e:
                logger.warning("Result explanation generation failed", extra={"error": str(e)})

        # 获取 Few-Shot 示例
        few_shot_examples = []
        if request.use_enhanced:
            try:
                library = nl2sql_ai_service_enhanced.get_example_library()
                examples = library.get_similar_examples(
                    request.natural_language,
                    limit=3
                )
                few_shot_examples = [ex.to_dict() for ex in examples]
            except Exception as e:
                logger.warning("Failed to get few shot examples", extra={"error": str(e)})

        return EnhancedAIQueryResponse(
            success=exec_result.success,
            sql=result["sql"],
            intent=result.get("intent", {}),
            confidence=result.get("confidence", 0.0),
            validation=result.get("validation", {}),
            suggestions=result.get("suggestions", []),
            data=exec_result.data if exec_result.success else None,
            explanation=explanation,
            execution_time_ms=exec_result.execution_time_ms,
            clarification=result.get("clarification"),
            few_shot_examples=few_shot_examples
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI query v2 failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"AI 查询失败：{str(e)}")


@router.post("/examples/add")
async def add_query_example(
    natural_language: str,
    sql: str,
    intent_type: str = "simple_select",
    tables: List[str] = None
):
    """添加查询示例到 Few-Shot 库"""
    if tables is None:
        tables = []

    try:
        example_id = nl2sql_ai_service_enhanced.add_query_example(
            natural_language=natural_language,
            sql=sql,
            intent_type=intent_type,
            tables=tables
        )
        return {
            "success": True,
            "example_id": example_id,
            "message": "示例已添加"
        }
    except Exception as e:
        logger.error("Failed to add example", extra={"error": str(e)})
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/examples")
async def get_query_examples(
    natural_language: Optional[str] = None,
    limit: int = 10
):
    """获取查询示例"""
    try:
        library = nl2sql_ai_service_enhanced.get_example_library()

        if natural_language:
            examples = library.get_similar_examples(natural_language, limit=limit)
        else:
            examples = library.all_examples[:limit]

        return {
            "success": True,
            "examples": [ex.to_dict() for ex in examples],
            "count": len(examples)
        }
    except Exception as e:
        logger.error("Failed to get examples", extra={"error": str(e)})
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/evaluate")
async def evaluate_nl2sql_accuracy(
    use_llm: bool = True,
    enable_self_correction: bool = True
):
    """
    评估 NL2SQL 准确率

    返回评估报告和详细分析
    """
    try:
        from services.nl2sql_evaluator import get_evaluator

        # 使用测试 Schema
        test_schema = {
            "tables": {
                "users": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "age", "type": "INTEGER"},
                    {"name": "email", "type": "VARCHAR(100)"},
                    {"name": "city", "type": "VARCHAR(50)"},
                    {"name": "department", "type": "VARCHAR(50)"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "orders": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "user_id", "type": "INTEGER"},
                    {"name": "total_amount", "type": "DECIMAL(10,2)"},
                    {"name": "status", "type": "VARCHAR(20)"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "products": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "price", "type": "DECIMAL(10,2)"},
                    {"name": "category_id", "type": "INTEGER"},
                ],
                "order_items": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "order_id", "type": "INTEGER"},
                    {"name": "product_id", "type": "INTEGER"},
                    {"name": "quantity", "type": "INTEGER"},
                    {"name": "price", "type": "DECIMAL(10,2)"},
                ],
                "employees": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR(100)"},
                    {"name": "salary", "type": "DECIMAL(10,2)"},
                    {"name": "department", "type": "VARCHAR(50)"},
                ]
            }
        }

        evaluator = get_evaluator(nl2sql_ai_service_enhanced)
        report = await evaluator.run_evaluation(
            test_schema,
            use_llm=use_llm,
            enable_self_correction=enable_self_correction
        )

        return {
            "success": True,
            "report": {
                "total_tests": report.total_tests,
                "correct_count": report.correct_count,
                "accuracy": report.accuracy,
                "avg_confidence": report.avg_confidence,
                "avg_latency_ms": report.avg_latency_ms,
                "accuracy_by_difficulty": report.accuracy_by_difficulty,
                "accuracy_by_category": report.accuracy_by_category,
                "error_breakdown": report.error_breakdown,
                "timestamp": report.timestamp
            },
            "failed_tests": [
                {
                    "test_id": t.test_id,
                    "natural_language": t.natural_language,
                    "expected_sql": t.expected_sql,
                    "actual_sql": t.actual_sql,
                    "mismatch_reason": t.mismatch_reason
                }
                for t in report.failed_tests
            ]
        }
    except Exception as e:
        logger.error("Evaluation failed", extra={"error": str(e)})
        return {
            "success": False,
            "message": str(e)
        }
