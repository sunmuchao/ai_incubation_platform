"""
微信登录 API

提供微信扫码登录相关接口：
- 获取登录二维码
- 检查登录状态（轮询）
- 处理微信回调
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from services.wechat_login_service import wechat_login_service
from utils.logger import logger

router = APIRouter(prefix="/api/wechat", tags=["WeChat Login"])


class QRCodeResponse(BaseModel):
    """二维码响应"""
    qrcode_url: str
    state: str
    expires_in: int


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    status: str  # pending/scanned/confirmed/expired/invalid
    user_id: Optional[str] = None
    token: Optional[str] = None
    message: Optional[str] = None


class CallbackResponse(BaseModel):
    """回调响应"""
    success: bool
    user_id: Optional[str] = None
    token: Optional[str] = None
    message: Optional[str] = None


@router.get("/qrcode", response_model=QRCodeResponse)
async def get_qrcode():
    """
    获取微信扫码登录二维码

    返回二维码 URL 和状态标识，前端展示二维码并轮询检查状态。
    """
    try:
        result = wechat_login_service.get_qrcode_url()
        return QRCodeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate WeChat QR code: {e}")
        raise HTTPException(status_code=500, detail="生成二维码失败")


@router.get("/status", response_model=LoginStatusResponse)
async def check_status(state: str = Query(..., description="登录状态标识")):
    """
    检查扫码登录状态

    前端轮询此接口，检测用户是否已扫码确认。
    建议轮询间隔：1-2 秒，最长轮询 5 分钟。
    """
    result = wechat_login_service.check_login_status(state)
    return LoginStatusResponse(**result)


@router.get("/callback")
async def wechat_callback(
    code: str = Query(..., description="微信授权码"),
    state: str = Query(..., description="登录状态标识"),
):
    """
    处理微信登录回调

    用户扫码确认后，微信会回调此接口。
    此接口获取用户信息并完成登录。
    """
    logger.info(f"WeChat callback received: code={code[:10]}..., state={state}")

    result = wechat_login_service.handle_callback(code, state)

    if result.get("success"):
        # 登录成功，返回 HTML 页面通知前端
        # 前端通过轮询检测到登录成功
        return {
            "success": True,
            "message": "登录成功，正在跳转...",
            "user_id": result.get("user_id"),
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "登录失败"),
        }


@router.get("/config")
async def check_config():
    """
    检查微信登录配置状态

    用于前端判断是否显示微信登录按钮。
    """
    return {
        "enabled": wechat_login_service.is_configured(),
    }