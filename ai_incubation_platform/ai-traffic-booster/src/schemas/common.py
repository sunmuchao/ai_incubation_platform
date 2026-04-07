"""
通用 schema 定义
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field
from enum import IntEnum

T = TypeVar('T')


class ErrorCode(IntEnum):
    """统一错误码定义"""
    SUCCESS = 0
    # 通用错误 1000-1999
    BAD_REQUEST = 1000
    UNAUTHORIZED = 1001
    FORBIDDEN = 1002
    NOT_FOUND = 1003
    METHOD_NOT_ALLOWED = 1004
    VALIDATION_ERROR = 1005
    INTERNAL_ERROR = 1006
    SERVICE_UNAVAILABLE = 1007

    # SEO 模块错误 2000-2999
    SEO_ANALYSIS_FAILED = 2000
    SEO_CONTENT_EMPTY = 2001
    SEO_KEYWORDS_EMPTY = 2002

    # 内容模块错误 3000-3999
    CONTENT_GENERATION_FAILED = 3000
    CONTENT_TOO_SHORT = 3001
    CONTENT_TOO_LONG = 3002

    # 分析模块错误 4000-4999
    ANALYTICS_DATA_NOT_FOUND = 4000
    ANALYTICS_QUERY_FAILED = 4001

    # A/B测试模块错误 5000-5999
    AB_TEST_NOT_FOUND = 5000
    AB_TEST_STATUS_INVALID = 5001
    AB_TEST_STATISTICS_FAILED = 5002
    AB_TEST_TRAFFIC_ALLOCATION_INVALID = 5003
    AB_TEST_CONTROL_VARIANT_INVALID = 5004

    # 竞争情报模块错误 6000-6999
    COMPETITOR_NOT_FOUND = 6000
    COMPETITOR_ANALYSIS_FAILED = 6001
    COMPETITOR_DATA_INVALID = 6002


class Response(BaseModel, Generic[T]):
    """通用响应格式"""
    code: ErrorCode = Field(default=ErrorCode.SUCCESS, description="响应码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    request_id: Optional[str] = Field(default=None, description="请求ID")

    class Config:
        json_encoders = {
            ErrorCode: lambda x: x.value
        }


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")


class PaginationResult(BaseModel, Generic[T]):
    """分页结果"""
    items: List[T] = Field(description="数据列表")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
