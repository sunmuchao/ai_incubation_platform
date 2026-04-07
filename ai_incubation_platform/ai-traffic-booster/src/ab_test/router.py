"""
A/B测试 API 路由
"""
from fastapi import APIRouter, Path, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from schemas.ab_test import (
    ABTestCreateRequest,
    ABTestResponse,
    ABTestResultResponse,
    ABTestListResponse,
    ABTestStatus,
)
from schemas.common import Response
from core.response import success
from .service import ab_test_service
from .templates.factory import report_factory
from core.exceptions import (
    BadRequestException,
    ABTestNotFoundException,
    ABTestStatusInvalidException,
    ABTestStatisticsFailedException,
)
from io import BytesIO

router = APIRouter(prefix="/ab-test", tags=["A/B测试"])


@router.get("/list", response_model=Response[ABTestListResponse])
async def get_test_list():
    """
    获取A/B测试列表
    - 所有测试的基本信息
    - 按状态统计：运行中、已完成、草稿
    """
    result = ab_test_service.get_test_list()
    return success(data=result)


@router.post("/create", response_model=Response[ABTestResponse])
async def create_test(request: ABTestCreateRequest):
    """
    创建新的A/B测试
    - 支持多变量测试
    - 自定义流量分配
    - 设置测试目标和指标
    - 配置置信水平和最小样本量
    """
    try:
        test = ab_test_service.create_test(request)
        return success(data=test, message="A/B测试创建成功")
    except ValueError as e:
        raise BadRequestException(str(e))


@router.get("/{test_id}", response_model=Response[ABTestResponse])
async def get_test_detail(
    test_id: str = Path(..., description="测试ID")
):
    """获取测试详情"""
    test = ab_test_service.get_test_detail(test_id)
    if not test:
        raise ABTestNotFoundException("测试不存在")
    return success(data=test)


@router.get("/{test_id}/result", response_model=Response[ABTestResultResponse])
async def get_test_result(
    test_id: str = Path(..., description="测试ID")
):
    """
    获取测试结果
    - 各变体的详细指标：访客数、转化数、转化率、提升率
    - 统计显著性计算
    - 自动识别获胜变体
    - 测试结论和建议
    """
    test = ab_test_service.get_test_detail(test_id)
    if not test:
        raise ABTestNotFoundException("测试不存在")
    if test.status not in [ABTestStatus.RUNNING, ABTestStatus.COMPLETED]:
        raise ABTestStatusInvalidException("测试尚未开始运行或状态不允许获取结果")

    result = ab_test_service.get_test_result(test_id)
    if not result:
        raise ABTestStatisticsFailedException("A/B测试统计失败或结果生成异常")
    return success(data=result)


@router.post("/{test_id}/start", response_model=Response[ABTestResponse])
async def start_test(
    test_id: str = Path(..., description="测试ID")
):
    """启动测试"""
    test = ab_test_service.get_test_detail(test_id)
    if not test:
        raise ABTestNotFoundException("测试不存在")
    if test.status != ABTestStatus.DRAFT:
        raise ABTestStatusInvalidException("测试状态不允许启动")

    started = ab_test_service.start_test(test_id)
    if not started:
        raise ABTestStatusInvalidException("测试启动失败或状态已变更")
    test = started
    return success(data=test, message="测试已启动")


@router.post("/{test_id}/stop", response_model=Response[ABTestResponse])
async def stop_test(
    test_id: str = Path(..., description="测试ID")
):
    """停止测试"""
    test = ab_test_service.get_test_detail(test_id)
    if not test:
        raise ABTestNotFoundException("测试不存在")
    if test.status != ABTestStatus.RUNNING:
        raise ABTestStatusInvalidException("测试状态不允许停止（需处于运行中）")

    stopped = ab_test_service.stop_test(test_id)
    if not stopped:
        raise ABTestStatusInvalidException("测试停止失败或状态已变更")
    test = stopped
    return success(data=test, message="测试已停止")


@router.get("/{test_id}/report", summary="导出测试报告")
async def export_test_report(
    test_id: str = Path(..., description="测试ID"),
    format: str = Query(default="json", description="报告格式: json, markdown, html, csv"),
    wrap: bool = Query(default=False, description="是否返回统一JSON包装（wrap=true 时即使html/csv也返回JSON）"),
):
    """
    导出A/B测试报告
    支持多种格式：
    - json: JSON格式结构化数据
    - markdown: Markdown格式文档
    - html: 美观的HTML页面报告
    - csv: CSV格式数据表
    """
    test = ab_test_service.get_test_detail(test_id)
    if not test:
        raise ABTestNotFoundException("测试不存在")

    result = ab_test_service.get_test_result(test_id)
    if not result:
        raise ABTestStatusInvalidException("测试尚无结果数据或状态不允许导出报告")

    try:
        report = report_factory.create_report(test, result, format=format)

        format_lower = format.lower()
        if format_lower == "json":
            return success(data=report)
        elif format_lower == "markdown":
            return success(data={"content": report})
        elif format_lower == "html":
            if wrap:
                return success(data={"format": format_lower, "content": report})
            return HTMLResponse(content=report)
        elif format_lower == "csv":
            if wrap:
                return success(data={"format": format_lower, "content": report})
            # 创建CSV文件响应
            buffer = BytesIO()
            buffer.write(report.encode('utf-8-sig'))
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=ab_test_{test_id}_report.csv"}
            )
        else:
            raise BadRequestException(f"不支持的报告格式: {format}")

    except Exception as e:
        raise BadRequestException(f"生成报告失败: {str(e)}")
