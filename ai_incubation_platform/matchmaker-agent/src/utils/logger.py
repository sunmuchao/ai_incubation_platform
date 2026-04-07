"""
日志工具模块
支持结构化日志和敏感字段自动脱敏
"""
import logging
import json
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from config import settings
import re


class SensitiveDataFilter(logging.Filter):
    """敏感数据脱敏过滤器"""

    def __init__(self):
        super().__init__()
        self.sensitive_fields = settings.sensitive_fields
        self.sensitive_fields_lower = [str(f).lower() for f in self.sensitive_fields]
        # 敏感字段正则匹配（不区分大小写）
        self.sensitive_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(field) for field in self.sensitive_fields) + r')\b',
            re.IGNORECASE
        )
        # 邮箱正则
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        # 手机号正则（中国大陆）
        self.phone_pattern = re.compile(r'\b1[3-9]\d{9}\b')

        # JWT-like（三段式）/ Bearer token
        jwt_segment = r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
        self.jwt_pattern = re.compile(rf"\b{jwt_segment}\b")
        self.bearer_pattern = re.compile(rf"(?i)\bBearer\s+({jwt_segment})\b")

        # key=value / JSON key="xxx" 形式的敏感值脱敏（只替换值，不整句吞掉）
        kv_keys = r"(password|password_hash|token|secret|jwt|access_token|refresh_token|api_key|apikey|id_card|bank_card|location)"
        self.key_value_pattern = re.compile(rf"(?i)\b{kv_keys}\b\s*[:=]\s*([^\s,;]+)")
        self.json_key_value_pattern = re.compile(
            rf"(?i)\"{kv_keys}\"\s*:\s*\"([^\"]*)\""
        )

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，脱敏敏感信息"""
        # 处理消息
        if hasattr(record, 'msg'):
            record.msg = self._desensitize(record.msg)

        # 处理参数
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._desensitize(v) for k, v in record.args.items()}
            else:
                record.args = tuple(self._desensitize(arg) for arg in record.args)

        # 处理异常信息
        if hasattr(record, 'exc_info') and record.exc_info:
            record.exc_info = self._desensitize_exc_info(record.exc_info)

        return True

    def _desensitize(self, value: Any) -> Any:
        """对值进行脱敏处理"""
        if value is None:
            return value

        if isinstance(value, str):
            # 脱敏邮箱
            value = self.email_pattern.sub(self._mask_email, value)
            # 脱敏手机号
            value = self.phone_pattern.sub(self._mask_phone, value)
            # 脱敏 Bearer token
            value = self.bearer_pattern.sub("Bearer [SENSITIVE_TOKEN]", value)
            # 脱敏 JWT-like 字符串（包含在 Bearer 之外的日志/异常里也能覆盖）
            value = self.jwt_pattern.sub("[SENSITIVE_JWT]", value)
            # 脱敏 JSON key="value"
            value = self.json_key_value_pattern.sub(
                lambda m: f"\"{m.group(1)}\":\"[SENSITIVE]\"",
                value,
            )
            # 脱敏 key=value
            value = self.key_value_pattern.sub(
                lambda m: f"{m.group(1)}=[SENSITIVE]",
                value,
            )
            return value

        if isinstance(value, dict):
            def _is_sensitive_key(key: Any) -> bool:
                k_lower = str(key).lower()

                # 1) 精确匹配（password / token / email 等）
                if k_lower in self.sensitive_fields_lower:
                    return True

                # 2) 复合字段名匹配（user_password / password_hash / bank_card_number 等）
                #    避免对过于通用的 `key` 进行无条件子串匹配，降低误脱敏风险
                if any(f != "key" and f.lower() in k_lower for f in self.sensitive_fields):
                    return True

                # 3) 对 *_key / api_key / apikey 这类更明确的密钥命名做补充规则
                return k_lower.endswith("_key") or "api_key" in k_lower or k_lower == "apikey" or "apikey" in k_lower

            return {k: "[SENSITIVE]" if _is_sensitive_key(k) else self._desensitize(v) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            return type(value)(self._desensitize(item) for item in value)

        return value

    def _desensitize_exc_info(self, exc_info: tuple) -> tuple:
        """脱敏异常信息"""
        exc_type, exc_value, exc_traceback = exc_info
        if exc_value:
            exc_value.args = tuple(self._desensitize(arg) for arg in exc_value.args)
        return (exc_type, exc_value, exc_traceback)

    @staticmethod
    def _mask_email(match: re.Match) -> str:
        """掩码邮箱：a***@example.com"""
        email = match.group()
        username, domain = email.split('@', 1)
        if len(username) <= 1:
            return f"{username}***@{domain}"
        return f"{username[0]}***@{domain}"

    @staticmethod
    def _mask_phone(match: re.Match) -> str:
        """掩码手机号：138****1234"""
        phone = match.group()
        return f"{phone[:3]}****{phone[7:]}"


def setup_logger() -> logging.Logger:
    """配置并返回日志记录器"""
    logger = logging.getLogger("matchmaker-agent")
    logger.setLevel(settings.log_level.upper())

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 添加敏感数据过滤器
    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    # 创建处理器
    handler = logging.StreamHandler()
    handler.addFilter(sensitive_filter)

    # 设置格式
    if settings.log_format.lower() == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# 全局日志实例
logger = setup_logger()
