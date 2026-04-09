"""
阿里云短信服务客户端

用于发送验证码、通知短信等
"""
from typing import Dict, Any, Optional
from utils.logger import logger


class AliyunSmsClient:
    """阿里云短信客户端"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        sign_name: str,
        template_code: str
    ):
        """
        初始化阿里云短信客户端

        Args:
            access_key_id: AccessKey ID
            access_key_secret: AccessKey Secret
            sign_name: 短信签名
            template_code: 模板 CODE
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.sign_name = sign_name
        self.template_code = template_code

        # 延迟导入，避免依赖问题
        self._client = None

    def _get_client(self):
        """获取阿里云客户端"""
        if self._client is None:
            try:
                from aliyunsdkcore.client import AcsClient
                from aliyunsdkcore.request import CommonRequest

                self._client = AcsClient(
                    self.access_key_id,
                    self.access_key_secret,
                    "cn-hangzhou"  # 默认使用杭州节点
                )
            except ImportError:
                logger.warning("Aliyun SDK not installed, running in mock mode")
                return None

        return self._client

    def send_verification_code(
        self,
        phone: str,
        code: str
    ) -> Dict[str, Any]:
        """
        发送验证码短信

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            {"success": bool, "error": Optional[str]}
        """
        client = self._get_client()

        if client is None:
            # Mock 模式
            logger.info(f"[MOCK SMS] Verification code {code} sent to {phone}")
            return {"success": True, "mock": True}

        try:
            from aliyunsdkcore.request import CommonRequest

            request = CommonRequest()
            request.set_method('POST')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')

            request.add_param('PhoneNumbers', phone)
            request.add_param('SignName', self.sign_name)
            request.add_param('TemplateCode', self.template_code)
            request.add_param('TemplateParam', f'{{"code":"{code}"}}')

            response = client.do_action_with_exception(request)

            logger.info(f"SMS sent to {phone}: {response}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            return {"success": False, "error": str(e)}

    def send_notification(
        self,
        phone: str,
        content: str,
        template_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送通知短信

        Args:
            phone: 手机号
            content: 短信内容
            template_code: 模板 CODE（可选，默认使用初始化时的模板）

        Returns:
            {"success": bool, "error": Optional[str]}
        """
        client = self._get_client()

        if client is None:
            logger.info(f"[MOCK SMS] Notification sent to {phone}: {content}")
            return {"success": True, "mock": True}

        try:
            from aliyunsdkcore.request import CommonRequest

            request = CommonRequest()
            request.set_method('POST')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')

            request.add_param('PhoneNumbers', phone)
            request.add_param('SignName', self.sign_name)
            request.add_param(
                'TemplateCode',
                template_code or self.template_code
            )
            request.add_param('TemplateParam', f'{{"content":"{content}"}}')

            response = client.do_action_with_exception(request)

            logger.info(f"SMS notification sent to {phone}: {response}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to send SMS notification to {phone}: {e}")
            return {"success": False, "error": str(e)}


# 全局客户端实例
_sms_client: Optional[AliyunSmsClient] = None


def get_sms_client() -> Optional[AliyunSmsClient]:
    """获取短信客户端实例"""
    global _sms_client

    if _sms_client is None:
        from config import settings

        # 检查配置
        access_key_id = getattr(settings, 'aliyun_sms_access_key_id', None)
        access_key_secret = getattr(settings, 'aliyun_sms_access_key_secret', None)
        sign_name = getattr(settings, 'aliyun_sms_sign_name', None)
        template_code = getattr(settings, 'aliyun_sms_template_code', None)

        if all([access_key_id, access_key_secret, sign_name, template_code]):
            _sms_client = AliyunSmsClient(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                sign_name=sign_name,
                template_code=template_code
            )
            logger.info("Aliyun SMS client initialized")
        else:
            logger.warning("Aliyun SMS credentials not configured")
            return None

    return _sms_client
