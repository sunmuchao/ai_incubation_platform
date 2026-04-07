"""
P9 多平台/小程序集成 - API 路由

提供多平台集成的 HTTP API 接口：
- 平台认证：登录/绑定/解绑
- 平台账号管理
- 平台订单管理
- 平台通知推送
- 平台配置管理
- 同步日志查询
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from config.database import get_db
from services.p9_platform_service import (
    PlatformAuthService,
    PlatformOrderService,
    PlatformNotificationService,
    PlatformConfigService,
    PlatformSyncLogService,
    PlatformIntegrationService,
)
from models.p9_models import (
    PlatformType,
    PlatformLoginRequest,
    PlatformLoginResponse,
    PlatformBindRequest,
    PlatformBindResponse,
    PlatformAccountResponse,
    PlatformOrderCreate,
    PlatformOrderUpdate,
    PlatformOrderResponse,
    PlatformOrderSyncRequest,
    PlatformOrderSyncResponse,
    PlatformNotificationSendRequest,
    PlatformNotificationResponse,
    PlatformConfigCreate,
    PlatformConfigUpdate,
    PlatformConfigResponse,
    PlatformSyncLogCreate,
    PlatformSyncLogResponse,
    PlatformSyncLogQuery,
    PlatformApiResponse,
    PlatformStats,
    OrderStatus,
    PaymentStatus,
    SyncStatus,
    SyncDirection,
    SyncAction,
)

# 创建路由
router = APIRouter(prefix="/api/platform", tags=["P9 多平台/小程序集成"])


# ============= 平台认证 API =============

@router.post("/auth/{platform}/login", response_model=PlatformLoginResponse, summary="平台用户登录")
async def platform_login(
    request: PlatformLoginRequest,
    platform: str,
    db: Session = Depends(get_db)
):
    """
    平台用户登录

    使用平台登录 code 换取用户信息并创建/关联系统账号。

    **请求参数**:
    - platform: 平台类型 (wechat/alipay)
    - code: 登录 code (微信 js_code / 支付宝 auth_code)
    - encrypted_data: 加密数据 (可选，用于解密用户信息)
    - iv: 加密向量 (可选)

    **返回**:
    - user_id: 系统用户 ID
    - platform_account_id: 平台账号 ID
    - is_new_user: 是否新用户
    - access_token: 系统访问令牌
    """
    # 验证 platform 参数一致性
    if request.platform.value != platform:
        raise HTTPException(status_code=400, detail="平台参数不一致")

    auth_service = PlatformAuthService(db)
    try:
        response = auth_service.login(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/{platform}/bind", response_model=PlatformBindResponse, summary="绑定平台账号")
async def bind_platform_account(
    request: PlatformBindRequest,
    platform: str,
    db: Session = Depends(get_db)
):
    """
    绑定平台账号到系统用户

    将平台账号绑定到已有的系统用户账号。

    **请求参数**:
    - platform: 平台类型
    - code: 登录 code
    - user_id: 系统用户 ID

    **返回**:
    - success: 是否成功
    - platform_account_id: 平台账号 ID
    - message: 提示信息
    """
    if request.platform.value != platform:
        raise HTTPException(status_code=400, detail="平台参数不一致")

    auth_service = PlatformAuthService(db)
    try:
        response = auth_service.bind(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/{platform}/unbind", response_model=PlatformApiResponse, summary="解绑平台账号")
async def unbind_platform_account(
    platform: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    解绑平台账号

    **请求参数**:
    - platform: 平台类型
    - user_id: 用户 ID

    **返回**:
    - success: 是否成功
    - message: 提示信息
    """
    auth_service = PlatformAuthService(db)
    try:
        success = auth_service.unbind(user_id, platform)
        if success:
            return PlatformApiResponse(
                success=True,
                message="解绑成功",
                platform=platform
            )
        else:
            return PlatformApiResponse(
                success=False,
                message="未找到绑定的平台账号",
                platform=platform
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts", response_model=List[PlatformAccountResponse], summary="获取用户平台账号")
async def get_user_accounts(
    user_id: str = Query(..., description="用户 ID"),
    platform: Optional[str] = Query(None, description="平台类型"),
    db: Session = Depends(get_db)
):
    """
    获取用户绑定的平台账号

    **请求参数**:
    - user_id: 用户 ID
    - platform: 平台类型 (可选)

    **返回**:
    平台账号列表
    """
    auth_service = PlatformAuthService(db)
    accounts = auth_service.get_account(user_id, platform)
    return [PlatformAccountResponse.model_validate(account) for account in accounts]


# ============= 平台订单 API =============

@router.post("/orders", response_model=PlatformOrderResponse, summary="创建平台订单映射")
async def create_platform_order(
    order: PlatformOrderCreate,
    db: Session = Depends(get_db)
):
    """
    创建平台订单映射

    当用户在平台下单后，创建平台订单与系统订单的映射关系。

    **请求参数**:
    - global_order_id: 系统订单 ID
    - platform: 平台类型
    - platform_order_id: 平台订单 ID
    - platform_order_no: 平台订单号 (可选)
    - transaction_id: 支付流水号 (可选)
    - payment_amount: 支付金额 (可选)
    - platform_metadata: 平台订单原始数据 (可选)
    """
    order_service = PlatformOrderService(db)
    try:
        platform_order = order_service.create_order_mapping(order)
        return PlatformOrderResponse.model_validate(platform_order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{platform_order_id}", response_model=PlatformOrderResponse, summary="获取平台订单详情")
async def get_platform_order(
    platform_order_id: str,
    db: Session = Depends(get_db)
):
    """
    获取平台订单详情

    **路径参数**:
    - platform_order_id: 平台订单 ID
    """
    order_service = PlatformOrderService(db)
    platform_order = order_service.get_order(platform_order_id)

    if not platform_order:
        raise HTTPException(status_code=404, detail="平台订单不存在")

    return PlatformOrderResponse.model_validate(platform_order)


@router.get("/orders", response_model=List[PlatformOrderResponse], summary="获取用户订单")
async def get_user_orders(
    user_id: str = Query(..., description="用户 ID"),
    platform: Optional[str] = Query(None, description="平台类型"),
    db: Session = Depends(get_db)
):
    """
    获取用户订单 (跨平台)

    **请求参数**:
    - user_id: 用户 ID
    - platform: 平台类型 (可选)
    """
    order_service = PlatformOrderService(db)
    orders = order_service.get_orders_by_user(user_id, platform)
    return [PlatformOrderResponse.model_validate(order) for order in orders]


@router.put("/orders/{platform_order_id}/status", response_model=PlatformOrderResponse, summary="更新平台订单状态")
async def update_platform_order_status(
    platform_order_id: str,
    update: PlatformOrderUpdate,
    db: Session = Depends(get_db)
):
    """
    更新平台订单状态

    **路径参数**:
    - platform_order_id: 平台订单 ID

    **请求参数**:
    - order_status: 订单状态
    - payment_status: 支付状态
    - payment_time: 支付时间
    - refund_amount: 退款金额
    - refund_time: 退款时间
    - refund_reason: 退款原因
    - sync_status: 同步状态
    """
    order_service = PlatformOrderService(db)
    try:
        platform_order = order_service.update_order_status(platform_order_id, update)
        return PlatformOrderResponse.model_validate(platform_order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/sync", response_model=PlatformOrderSyncResponse, summary="同步订单到平台")
async def sync_order_to_platform(
    request: PlatformOrderSyncRequest,
    db: Session = Depends(get_db)
):
    """
    同步订单状态到平台

    **请求参数**:
    - global_order_id: 系统订单 ID
    - platform: 平台类型
    - order_status: 订单状态 (可选)
    - notify_user: 是否通知用户
    """
    order_service = PlatformOrderService(db)
    try:
        success, message = order_service.sync_to_platform(
            global_order_id=request.global_order_id,
            platform=request.platform.value,
            order_status=request.order_status,
            notify_user=request.notify_user
        )

        # 获取平台订单 ID
        platform_orders = order_service.get_orders_by_global_id(request.global_order_id)
        platform_order_id = platform_orders[0].platform_order_id if platform_orders else ""

        return PlatformOrderSyncResponse(
            success=success,
            platform_order_id=platform_order_id,
            sync_result="success" if success else "failed",
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============= 平台通知 API =============

@router.post("/notifications/send", response_model=PlatformNotificationResponse, summary="发送平台通知")
async def send_platform_notification(
    request: PlatformNotificationSendRequest,
    db: Session = Depends(get_db)
):
    """
    发送平台通知

    **请求参数**:
    - user_id: 用户 ID
    - platform: 平台类型
    - template_id: 模板 ID
    - template_name: 模板名称
    - content: 通知内容数据
    - page_path: 跳转页面路径
    - title: 通知标题
    """
    notification_service = PlatformNotificationService(db)
    try:
        response = notification_service.send(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/notifications", response_model=List[PlatformNotificationResponse], summary="获取用户通知")
async def get_user_notifications(
    user_id: str = Query(..., description="用户 ID"),
    platform: Optional[str] = Query(None, description="平台类型"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取用户通知列表

    **请求参数**:
    - user_id: 用户 ID
    - platform: 平台类型 (可选)
    - limit: 返回数量限制 (默认 20)
    """
    notification_service = PlatformNotificationService(db)
    notifications = notification_service.get_notifications(user_id, platform, limit)
    return [PlatformNotificationResponse.model_validate(n) for n in notifications]


@router.post("/notifications/{notification_id}/read", response_model=PlatformApiResponse, summary="标记通知为已读")
async def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db)
):
    """
    标记通知为已读

    **路径参数**:
    - notification_id: 通知 ID
    """
    notification_service = PlatformNotificationService(db)
    success = notification_service.mark_as_read(notification_id)

    return PlatformApiResponse(
        success=success,
        message="操作成功" if success else "通知不存在"
    )


@router.get("/notifications/templates", response_model=PlatformApiResponse, summary="获取通知模板列表")
async def get_notification_templates(
    platform: Optional[str] = Query(None, description="平台类型"),
    db: Session = Depends(get_db)
):
    """
    获取通知模板列表

    **请求参数**:
    - platform: 平台类型 (可选，不传则返回所有平台)
    """
    templates = PlatformNotificationService.TEMPLATES

    if platform:
        templates = {platform: templates.get(platform, {})}

    return PlatformApiResponse(
        success=True,
        message="获取成功",
        data={"templates": templates}
    )


# ============= 平台配置 API =============

@router.post("/configs", response_model=PlatformConfigResponse, summary="创建平台配置")
async def create_platform_config(
    config: PlatformConfigCreate,
    db: Session = Depends(get_db)
):
    """
    创建平台配置

    **请求参数**:
    - platform: 平台类型
    - platform_name: 平台名称
    - app_id: 平台 AppID
    - app_secret: 平台 AppSecret
    - encoding_aes_key: 消息加密密钥
    - mch_id: 商户 ID
    - mch_key: 商户密钥
    - cert_path: 证书路径
    - key_path: 私钥路径
    - api_version: API 版本
    - api_base_url: API 基础 URL
    - webhook_url: 回调 URL
    - webhook_token: 回调验证 token
    - is_enabled: 是否启用
    - config_json: 额外配置
    - remarks: 备注
    """
    config_service = PlatformConfigService(db)
    try:
        entity = config_service.create(config)
        return PlatformConfigResponse.model_validate(entity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/configs/{platform}", response_model=PlatformConfigResponse, summary="获取平台配置")
async def get_platform_config(
    platform: str,
    db: Session = Depends(get_db)
):
    """
    获取平台配置

    **路径参数**:
    - platform: 平台类型
    """
    config_service = PlatformConfigService(db)
    config = config_service.get(platform)

    if not config:
        raise HTTPException(status_code=404, detail=f"平台 {platform} 配置不存在")

    return PlatformConfigResponse.model_validate(config)


@router.get("/configs", response_model=List[PlatformConfigResponse], summary="获取所有平台配置")
async def get_all_platform_configs(
    enabled_only: bool = Query(False, description="是否仅返回启用的配置"),
    db: Session = Depends(get_db)
):
    """
    获取所有平台配置

    **请求参数**:
    - enabled_only: 是否仅返回启用的配置
    """
    config_service = PlatformConfigService(db)
    configs = config_service.get_all(enabled_only)
    return [PlatformConfigResponse.model_validate(config) for config in configs]


@router.put("/configs/{platform}", response_model=PlatformConfigResponse, summary="更新平台配置")
async def update_platform_config(
    platform: str,
    update: PlatformConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新平台配置

    **路径参数**:
    - platform: 平台类型

    **请求参数**:
    - 各配置字段 (可选)
    """
    config_service = PlatformConfigService(db)
    config = config_service.update(platform, update)

    if not config:
        raise HTTPException(status_code=404, detail=f"平台 {platform} 配置不存在")

    return PlatformConfigResponse.model_validate(config)


@router.delete("/configs/{platform}", response_model=PlatformApiResponse, summary="删除平台配置")
async def delete_platform_config(
    platform: str,
    db: Session = Depends(get_db)
):
    """
    删除平台配置

    **路径参数**:
    - platform: 平台类型
    """
    config_service = PlatformConfigService(db)
    success = config_service.delete(platform)

    return PlatformApiResponse(
        success=success,
        message="删除成功" if success else "配置不存在"
    )


# ============= 同步日志 API =============

@router.post("/sync-logs", response_model=PlatformSyncLogResponse, summary="创建同步日志")
async def create_sync_log(
    log: PlatformSyncLogCreate,
    db: Session = Depends(get_db)
):
    """
    创建平台同步日志

    **请求参数**:
    - sync_type: 同步类型 (order/account/notification)
    - platform: 平台类型
    - sync_direction: 同步方向 (inbound/outbound)
    - sync_action: 同步动作 (create/update/delete/query)
    - platform_resource_id: 平台资源 ID
    - internal_resource_id: 内部资源 ID
    - request_data: 请求数据
    - response_data: 响应数据
    - error_message: 错误信息
    - duration_ms: 同步耗时
    - operator_id: 操作人 ID
    - operator_type: 操作类型
    """
    sync_log_service = PlatformSyncLogService(db)
    try:
        entity = sync_log_service.create(log)
        return PlatformSyncLogResponse.model_validate(entity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sync-logs", response_model=PlatformApiResponse, summary="查询同步日志")
async def query_sync_logs(
    sync_type: Optional[str] = Query(None, description="同步类型"),
    platform: Optional[str] = Query(None, description="平台类型"),
    sync_status: Optional[str] = Query(None, description="同步状态"),
    internal_resource_id: Optional[str] = Query(None, description="内部资源 ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    查询同步日志

    **请求参数**:
    - sync_type: 同步类型
    - platform: 平台类型
    - sync_status: 同步状态
    - internal_resource_id: 内部资源 ID
    - start_time: 开始时间
    - end_time: 结束时间
    - page: 页码
    - page_size: 每页数量
    """
    sync_log_service = PlatformSyncLogService(db)

    logs, total = sync_log_service.query(
        sync_type=sync_type,
        platform=platform,
        sync_status=sync_status,
        internal_resource_id=internal_resource_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )

    return PlatformApiResponse(
        success=True,
        message="查询成功",
        data={
            "logs": [PlatformSyncLogResponse.model_validate(log) for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/sync-logs/stats", response_model=PlatformApiResponse, summary="获取同步统计")
async def get_sync_logs_stats(
    platform: Optional[str] = Query(None, description="平台类型"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    """
    获取同步日志统计

    **请求参数**:
    - platform: 平台类型
    - start_time: 开始时间
    - end_time: 结束时间
    """
    sync_log_service = PlatformSyncLogService(db)
    stats = sync_log_service.get_stats(platform, start_time, end_time)

    return PlatformApiResponse(
        success=True,
        message="获取成功",
        data=stats
    )


# ============= 平台统计 API =============

@router.get("/stats", response_model=PlatformApiResponse, summary="获取平台统计信息")
async def get_platform_stats(
    db: Session = Depends(get_db)
):
    """
    获取所有平台统计信息

    返回各平台的账号数、订单数、通知数等统计信息。
    """
    integration_service = PlatformIntegrationService(db)
    stats = integration_service.get_platform_stats()

    return PlatformApiResponse(
        success=True,
        message="获取成功",
        data={"platform_stats": stats}
    )
