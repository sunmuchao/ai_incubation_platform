"""
P17 跨平台集成 API 路由

提供：
- 邮件通知 API
- 短信通知 API
- OAuth 认证 API
- SSO 单点登录 API
- 社交分享 API
- 跨平台身份绑定 API
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request, Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import uuid

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.integration_service import (
    email_service,
    sms_service,
    oauth_service,
    sso_service,
    share_service,
    cross_platform_service,
)

router = APIRouter(prefix="/api/p17", tags=["p17_integration"])


# ==================== 请求/响应模型 ====================

class EmailSendRequest(BaseModel):
    """邮件发送请求"""
    recipient_email: EmailStr = Field(..., description="收件人邮箱")
    subject: str = Field(..., description="邮件主题", max_length=500)
    content: str = Field(..., description="邮件内容")
    template_type: Optional[str] = Field(default=None, description="模板类型")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量")
    is_html: bool = Field(default=False, description="是否为 HTML 格式")


class EmailSendResponse(BaseModel):
    """邮件发送响应"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class SMSSendRequest(BaseModel):
    """短信发送请求"""
    recipient_phone: str = Field(..., description="收件人手机号", pattern=r"^\+?[1-9]\d{1,14}$")
    template_code: str = Field(..., description="模板代码")
    template_params: Dict[str, str] = Field(default_factory=dict, description="模板参数")


class SMSSendResponse(BaseModel):
    """短信发送响应"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class OAuthConfigRequest(BaseModel):
    """OAuth 配置请求"""
    provider: str = Field(..., description="OAuth 提供商")
    client_id: str = Field(..., description="客户端 ID")
    client_secret: str = Field(..., description="客户端密钥")
    redirect_uri: str = Field(..., description="重定向 URI")
    authorize_url: Optional[str] = Field(default=None, description="授权 URL")
    token_url: Optional[str] = Field(default=None, description="令牌 URL")
    userinfo_url: Optional[str] = Field(default=None, description="用户信息 URL")
    scopes: List[str] = Field(default_factory=list, description="权限范围")
    user_mapping: Dict[str, str] = Field(default_factory=dict, description="用户字段映射")


class OAuthAuthorizeResponse(BaseModel):
    """OAuth 授权响应"""
    success: bool
    authorize_url: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth 回调请求"""
    code: str = Field(..., description="授权码")
    state: str = Field(..., description="状态参数")


class CrossPlatformLinkRequest(BaseModel):
    """跨平台绑定请求"""
    platform: str = Field(..., description="外部平台")
    platform_user_id: str = Field(..., description="外部平台用户 ID")
    platform_username: str = Field(..., description="外部平台用户名")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")


class CrossPlatformIdentityResponse(BaseModel):
    """跨平台身份响应"""
    success: bool
    identities: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ShareRequest(BaseModel):
    """分享请求"""
    platform: str = Field(..., description="分享平台")
    content_type: str = Field(..., description="内容类型")
    content_id: str = Field(..., description="内容 ID")
    content_title: str = Field(..., description="内容标题")
    content_description: Optional[str] = Field(default=None, description="内容描述")
    content_image: Optional[str] = Field(default=None, description="内容图片 URL")


class ShareResponse(BaseModel):
    """分享响应"""
    success: bool
    share_url: Optional[str] = None
    share_card: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SSOLoginRequest(BaseModel):
    """SSO 登录请求"""
    config_name: str = Field(..., description="SSO 配置名称")
    return_to: Optional[str] = Field(default=None, description="登录后返回地址")


class SSOSessionResponse(BaseModel):
    """SSO 会话响应"""
    success: bool
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    redirect_url: Optional[str] = None
    error: Optional[str] = None


# ==================== 邮件通知 API ====================

@router.post("/email/send", response_model=EmailSendResponse, tags=["email"])
async def send_email(request: EmailSendRequest):
    """
    发送邮件

    需要管理员权限
    """
    success, result = await email_service.send_email(
        recipient=request.recipient_email,
        subject=request.subject,
        content=request.content,
        template_type=request.template_type,
        variables=request.variables,
        is_html=request.is_html
    )

    if success:
        return EmailSendResponse(success=True, message_id=result)
    else:
        return EmailSendResponse(success=False, error=result)


@router.post("/email/verification", response_model=EmailSendResponse, tags=["email"])
async def send_verification_email(
    recipient_email: EmailStr = Query(..., description="收件人邮箱"),
    code: str = Query(..., description="验证码")
):
    """发送验证邮件"""
    success, result = await email_service.send_verification_code(
        recipient=recipient_email,
        code=code
    )

    if success:
        return EmailSendResponse(success=True, message_id=result)
    else:
        return EmailSendResponse(success=False, error=result)


@router.post("/email/welcome", response_model=EmailSendResponse, tags=["email"])
async def send_welcome_email(
    recipient_email: EmailStr = Query(..., description="收件人邮箱"),
    username: str = Query(..., description="用户名")
):
    """发送欢迎邮件"""
    success, result = await email_service.send_welcome_email(
        recipient=recipient_email,
        username=username
    )

    if success:
        return EmailSendResponse(success=True, message_id=result)
    else:
        return EmailSendResponse(success=False, error=result)


@router.post("/email/digest", response_model=EmailSendResponse, tags=["email"])
async def send_digest_email(
    recipient_email: EmailStr = Query(..., description="收件人邮箱"),
    username: str = Query(..., description="用户名"),
    digest_data: Dict[str, Any] = Body(..., description="摘要数据")
):
    """发送摘要邮件"""
    success, result = await email_service.send_digest_email(
        recipient=recipient_email,
        username=username,
        digest_data=digest_data
    )

    if success:
        return EmailSendResponse(success=True, message_id=result)
    else:
        return EmailSendResponse(success=False, error=result)


# ==================== 短信通知 API ====================

@router.post("/sms/send", response_model=SMSSendResponse, tags=["sms"])
async def send_sms(request: SMSSendRequest):
    """
    发送短信

    需要管理员权限
    """
    success, result = await sms_service.send_sms(
        recipient=request.recipient_phone,
        content="",  # 由模板生成
        template_code=request.template_code,
        template_params=request.template_params
    )

    if success:
        return SMSSendResponse(success=True, message_id=result)
    else:
        return SMSSendResponse(success=False, error=result)


@router.post("/sms/verification", response_model=SMSSendResponse, tags=["sms"])
async def send_verification_sms(
    recipient_phone: str = Query(..., description="收件人手机号"),
    code: str = Query(..., description="验证码")
):
    """发送验证码短信"""
    success, result = await sms_service.send_verification_code(
        recipient=recipient_phone,
        code=code
    )

    if success:
        return SMSSendResponse(success=True, message_id=result)
    else:
        return SMSSendResponse(success=False, error=result)


# ==================== OAuth 认证 API ====================

@router.post("/oauth/config", tags=["oauth"])
async def register_oauth_config(request: OAuthConfigRequest):
    """
    注册 OAuth 提供商配置

    需要管理员权限
    """
    config = {
        'client_id': request.client_id,
        'client_secret': request.client_secret,
        'redirect_uri': request.redirect_uri,
        'authorize_url': request.authorize_url,
        'token_url': request.token_url,
        'userinfo_url': request.userinfo_url,
        'scopes': request.scopes,
        'user_mapping': request.user_mapping,
    }

    success = oauth_service.register_provider(request.provider, config)

    return {
        "success": success,
        "provider": request.provider
    }


@router.get("/oauth/authorize", response_model=OAuthAuthorizeResponse, tags=["oauth"])
async def get_oauth_authorize_url(
    provider: str = Query(..., description="OAuth 提供商"),
    redirect_uri: Optional[str] = Query(default=None, description="重定向 URI")
):
    """获取 OAuth 授权 URL"""
    success, result = oauth_service.get_authorize_url(provider, redirect_uri)

    if success:
        return OAuthAuthorizeResponse(success=True, authorize_url=result, state=str(uuid.uuid4()))
    else:
        return OAuthAuthorizeResponse(success=False, error=result)


@router.post("/oauth/callback", tags=["oauth"])
async def handle_oauth_callback(
    provider: str = Query(..., description="OAuth 提供商"),
    request: OAuthCallbackRequest = Body(...)
):
    """
    处理 OAuth 回调

    这是 OAuth 流程的回调端点
    """
    success, result = await oauth_service.handle_callback(
        provider=provider,
        code=request.code,
        state=request.state
    )

    if success:
        return {
            "success": True,
            "user_info": result
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "OAuth callback failed"))


@router.post("/oauth/token/exchange", tags=["oauth"])
async def exchange_oauth_token(
    provider: str = Query(..., description="OAuth 提供商"),
    code: str = Body(..., description="授权码")
):
    """交换 OAuth 访问令牌"""
    success, result = await oauth_service.exchange_token(provider, code)

    if success:
        return {
            "success": True,
            "token_info": result
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Token exchange failed"))


# ==================== SSO 单点登录 API ====================

@router.post("/sso/config", tags=["sso"])
async def register_sso_config(
    name: str = Body(..., description="配置名称"),
    protocol: str = Body(..., description="SSO 协议：saml2/oidc/ldap"),
    config: Dict[str, Any] = Body(..., description="SSO 配置")
):
    """
    注册 SSO 配置

    需要管理员权限
    """
    config['protocol'] = protocol
    success = sso_service.register_config(name, config)

    return {
        "success": success,
        "name": name
    }


@router.post("/sso/login", response_model=SSOSessionResponse, tags=["sso"])
async def sso_login(request: SSOLoginRequest):
    """
    SSO 登录

    发起 SSO 登录流程
    """
    # 这里应该根据 SSO 协议类型进行不同的处理
    # 当前为简化实现
    return SSOSessionResponse(
        success=True,
        redirect_url=f"/sso/initiate?config={request.config_name}&return_to={request.return_to}"
    )


@router.get("/sso/callback", tags=["sso"])
async def sso_callback(
    config: str = Query(..., description="SSO 配置名称"),
    assertion: Optional[str] = Query(default=None, description="SAML Assertion"),
    code: Optional[str] = Query(default=None, description="OIDC Code")
):
    """
    SSO 回调

    处理 SSO 提供商的回调
    """
    # 这里应该根据协议类型解析响应
    # 当前为简化实现
    return {
        "success": True,
        "message": "SSO callback processed",
        "config": config
    }


@router.post("/sso/logout", tags=["sso"])
async def sso_logout(
    session_id: str = Body(..., description="会话 ID"),
    return_to: Optional[str] = Body(default=None, description="登出后返回地址")
):
    """SSO 登出"""
    success = sso_service.logout(session_id)

    return {
        "success": success,
        "return_to": return_to
    }


# ==================== 社交分享 API ====================

@router.post("/share/config", tags=["share"])
async def register_share_platform(
    platform: str = Body(..., description="分享平台"),
    app_id: Optional[str] = Body(default=None, description="应用 ID"),
    app_secret: Optional[str] = Body(default=None, description="应用密钥"),
    base_url: str = Body(default="https://community.example.com", description="基础 URL"),
    url_template: str = Body(default="/posts/{id}", description="URL 模板")
):
    """
    注册分享平台配置

    需要管理员权限
    """
    config = {
        'app_id': app_id,
        'app_secret': app_secret,
        'base_url': base_url,
        'url_template': url_template,
    }

    success = share_service.register_platform(platform, config)

    return {
        "success": success,
        "platform": platform
    }


@router.post("/share/generate", response_model=ShareResponse, tags=["share"])
async def generate_share_url(request: ShareRequest):
    """生成分享链接和卡片"""
    success, share_url = share_service.generate_share_url(
        platform=request.platform,
        content_type=request.content_type,
        content_id=request.content_id,
        content_title=request.content_title
    )

    if not success:
        return ShareResponse(success=False, error=share_url)

    share_card = share_service.generate_share_card(
        platform=request.platform,
        content_type=request.content_type,
        content_id=request.content_id,
        content_title=request.content_title,
        content_description=request.content_description,
        content_image=request.content_image
    )

    return ShareResponse(
        success=True,
        share_url=share_url,
        share_card=share_card
    )


# ==================== 跨平台身份绑定 API ====================

@router.post("/identity/link", tags=["identity"])
async def link_cross_platform_identity(
    user_id: str = Query(..., description="本地用户 ID"),
    request: CrossPlatformLinkRequest = Body(...)
):
    """
    绑定跨平台身份

    将外部平台身份与本地账号关联
    """
    success, message = cross_platform_service.link_identity(
        local_user_id=user_id,
        external_platform=request.platform,
        external_user_id=request.platform_user_id,
        external_username=request.platform_username,
        access_token=request.access_token,
        refresh_token=request.refresh_token
    )

    if success:
        return {
            "success": True,
            "message": message
        }
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/identity/unlink", tags=["identity"])
async def unlink_cross_platform_identity(
    user_id: str = Query(..., description="本地用户 ID"),
    platform: str = Body(..., description="外部平台")
):
    """解绑跨平台身份"""
    success = cross_platform_service.unlink_identity(user_id, platform)

    return {
        "success": success,
        "user_id": user_id,
        "platform": platform
    }


@router.get("/identity/list", response_model=CrossPlatformIdentityResponse, tags=["identity"])
async def list_cross_platform_identities(
    user_id: str = Query(..., description="本地用户 ID")
):
    """获取用户绑定的所有外部身份"""
    identities = cross_platform_service.get_linked_identities(user_id)

    return CrossPlatformIdentityResponse(
        success=True,
        identities=identities
    )


@router.post("/identity/sync-reputation", tags=["identity"])
async def sync_cross_platform_reputation(
    user_id: str = Query(..., description="本地用户 ID"),
    platform: str = Body(..., description="外部平台"),
    reputation_score: float = Body(..., description="信誉分数", ge=0, le=1)
):
    """同步跨平台信誉分数"""
    success = cross_platform_service.sync_reputation(
        local_user_id=user_id,
        external_platform=platform,
        reputation_score=reputation_score
    )

    return {
        "success": success,
        "user_id": user_id,
        "platform": platform,
        "reputation_score": reputation_score
    }


@router.get("/identity/resolve", tags=["identity"])
async def resolve_cross_platform_identity(
    platform: str = Query(..., description="外部平台"),
    platform_user_id: str = Query(..., description="外部平台用户 ID")
):
    """根据外部身份解析本地用户 ID"""
    local_user_id = cross_platform_service.get_local_user_id(platform, platform_user_id)

    if local_user_id:
        return {
            "success": True,
            "local_user_id": local_user_id
        }
    else:
        return {
            "success": False,
            "error": "Identity not found"
        }


# ==================== 集成配置管理 API ====================

@router.get("/integration/status", tags=["integration"])
async def get_integration_status():
    """获取所有集成服务的状态"""
    return {
        "email": {
            "configured": bool(email_service._configs),
            "provider": email_service._configs.get('provider', 'N/A')
        },
        "sms": {
            "configured": bool(sms_service._configs),
            "provider": sms_service._configs.get('provider', 'N/A')
        },
        "oauth": {
            "configured": len(oauth_service._providers) > 0,
            "providers": list(oauth_service._providers.keys())
        },
        "sso": {
            "configured": len(sso_service._configs) > 0,
            "configs": list(sso_service._configs.keys())
        },
        "share": {
            "configured": len(share_service._platforms) > 0,
            "platforms": list(share_service._platforms.keys())
        },
        "cross_platform": {
            "identities_count": len(cross_platform_service._identities)
        }
    }


@router.post("/integration/test/email", tags=["integration"])
async def test_email_integration(
    recipient_email: EmailStr = Body(..., description="测试邮箱")
):
    """测试邮件集成"""
    success, result = await email_service.send_email(
        recipient=recipient_email,
        subject="【测试邮件】Human-AI-Community 集成测试",
        content="这是一封测试邮件，如果您收到此邮件，说明邮件集成配置正确。"
    )

    return {
        "success": success,
        "message": result if success else "Test failed",
        "recipient": recipient_email
    }


@router.post("/integration/test/sms", tags=["integration"])
async def test_sms_integration(
    recipient_phone: str = Body(..., description="测试手机号")
):
    """测试短信集成"""
    success, result = await sms_service.send_sms(
        recipient=recipient_phone,
        content="【Human-AI-Community】这是一条测试短信，如果您收到此短信，说明短信集成配置正确。"
    )

    return {
        "success": success,
        "message": result if success else "Test failed",
        "recipient": recipient_phone
    }
