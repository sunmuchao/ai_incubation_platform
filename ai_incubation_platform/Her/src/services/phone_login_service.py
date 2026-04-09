"""
手机号登录服务

功能:
- 发送短信验证码
- 验证短信验证码
- 手机号登录/注册
- 手机号绑定/解绑
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import random
import re
from sqlalchemy.orm import Session

from db.models import UserDB
from db.repositories import UserRepository
from utils.logger import logger


class PhoneLoginService:
    """手机号登录服务"""

    # 验证码有效期（分钟）
    CODE_EXPIRY_MINUTES = 10

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _generate_verification_code(self) -> str:
        """生成 6 位验证码"""
        return ''.join(random.choices('0123456789', k=6))

    def _validate_phone_format(self, phone: str) -> bool:
        """验证手机号格式（中国大陆）"""
        # 简单验证：1 开头，11 位数字
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))

    def send_verification_code(self, phone: str) -> Dict[str, Any]:
        """
        发送验证码到手机号

        Args:
            phone: 手机号

        Returns:
            {"success": bool, "message": str, "user_exists": bool}
        """
        # 验证手机号格式
        if not self._validate_phone_format(phone):
            return {"success": False, "message": "手机号格式不正确"}

        # 检查手机号是否已注册
        user = self.user_repo.get_by_phone(phone)

        if user:
            # 已注册用户：发送验证码到该手机号
            code = self._generate_verification_code()
            expires_at = datetime.now() + timedelta(minutes=self.CODE_EXPIRY_MINUTES)

            self.user_repo.update_phone_verification_code(user.id, code, expires_at)

            # 发送短信
            sms_result = self._send_sms(phone, code)

            if sms_result["success"]:
                logger.info(f"Verification code sent to existing user: {phone}")
                return {
                    "success": True,
                    "message": "验证码已发送",
                    "user_exists": True
                }
            else:
                return {"success": False, "message": f"短信发送失败：{sms_result['error']}"}

        else:
            # 未注册用户：创建新用户并发送验证码
            import uuid
            user_id = str(uuid.uuid4())
            code = self._generate_verification_code()
            expires_at = datetime.now() + timedelta(minutes=self.CODE_EXPIRY_MINUTES)

            # 创建新用户
            user_data = {
                "id": user_id,
                "name": f"用户{phone[-4:]}",  # 默认用户名
                "email": f"{user_id}@temp.local",  # 临时邮箱
                "password_hash": "",  # 手机号登录不需要密码
                "age": 18,  # 默认年龄
                "gender": "unknown",
                "location": "未知",
                "phone": phone,
                "phone_verified": False
            }

            new_user = self.user_repo.create(user_data)
            self.user_repo.update_phone_verification_code(new_user.id, code, expires_at)

            # 发送短信
            sms_result = self._send_sms(phone, code)

            if sms_result["success"]:
                logger.info(f"Verification code sent to new user: {phone}, user_id={user_id}")
                return {
                    "success": True,
                    "message": "验证码已发送",
                    "user_exists": False,
                    "user_id": user_id
                }
            else:
                return {"success": False, "message": f"短信发送失败：{sms_result['error']}"}

    def _send_sms(self, phone: str, code: str) -> Dict[str, Any]:
        """
        发送短信验证码

        使用阿里云短信服务（或配置的其他服务商）
        """
        from config import settings

        # 检查是否启用了短信服务
        if not getattr(settings, 'sms_enabled', False):
            # 降级方案：记录日志，返回成功（用于开发/测试）
            logger.warning(f"SMS service not enabled, mock code {code} for {phone}")
            return {"success": True, "mock_code": code}

        # 使用阿里云短信服务
        try:
            from integration.aliyun_sms_client import get_sms_client
            sms_client = get_sms_client()

            result = sms_client.send_verification_code(phone, code)

            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result.get("error", "未知错误")}

        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            return {"success": False, "error": str(e)}

    def verify_code_and_login(
        self,
        phone: str,
        verification_code: str
    ) -> Dict[str, Any]:
        """
        验证验证码并登录

        Args:
            phone: 手机号
            verification_code: 验证码

        Returns:
            {"success": bool, "user": Optional[UserDB], "message": str}
        """
        user = self.user_repo.get_by_phone(phone)

        if not user:
            return {"success": False, "message": "用户不存在"}

        # 验证验证码
        if self.user_repo.verify_phone(user.id, verification_code):
            logger.info(f"Phone verified successfully: {phone}, user_id={user.id}")
            return {
                "success": True,
                "message": "验证成功",
                "user": user
            }
        else:
            logger.warning(f"Verification failed for phone: {phone}")
            return {"success": False, "message": "验证码错误或已过期"}

    def bind_phone(
        self,
        user_id: str,
        phone: str,
        verification_code: str
    ) -> Dict[str, Any]:
        """
        为已有用户绑定手机号

        Args:
            user_id: 用户 ID
            phone: 手机号
            verification_code: 验证码

        Returns:
            {"success": bool, "message": str}
        """
        user = self.user_repo.get_by_id(user_id)

        if not user:
            return {"success": False, "message": "用户不存在"}

        # 检查手机号是否已被其他用户使用
        existing_user = self.user_repo.get_by_phone(phone)
        if existing_user and existing_user.id != user_id:
            return {"success": False, "message": "该手机号已被其他用户使用"}

        # 验证验证码
        if not self._validate_phone_format(phone):
            return {"success": False, "message": "手机号格式不正确"}

        # 直接验证（假设验证码已通过其他方式发送）
        if user.phone_verification_code == verification_code:
            user.phone = phone
            user.phone_verified = True
            user.phone_verification_code = None
            user.phone_verification_expires_at = None
            self.db.commit()

            logger.info(f"Phone bound successfully: user_id={user_id}, phone={phone}")
            return {"success": True, "message": "手机号绑定成功"}
        else:
            return {"success": False, "message": "验证码错误"}

    def unbind_phone(self, user_id: str) -> Dict[str, Any]:
        """
        解绑手机号

        Args:
            user_id: 用户 ID

        Returns:
            {"success": bool, "message": str}
        """
        user = self.user_repo.get_by_id(user_id)

        if not user:
            return {"success": False, "message": "用户不存在"}

        if not user.phone:
            return {"success": False, "message": "未绑定手机号"}

        # 如果有邮箱，可以解绑；否则需要保留至少一个登录方式
        if not user.email:
            return {
                "success": False,
                "message": "需要保留至少一个登录方式（邮箱或手机号）"
            }

        user.phone = None
        user.phone_verified = False
        self.db.commit()

        logger.info(f"Phone unbound: user_id={user_id}")
        return {"success": True, "message": "手机号已解绑"}


# 工厂函数
def get_phone_login_service(db: Session) -> PhoneLoginService:
    """获取手机号登录服务实例"""
    return PhoneLoginService(db)
