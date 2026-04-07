"""
合规校验工具

用于校验用户输入和输出内容的合规性，确保符合平台规范。
"""
from typing import Dict, List, Optional, Any
import re
from utils.logger import logger


class ComplianceTool:
    """
    合规校验工具

    功能：
    - 敏感信息检测
    - 不当内容拦截
    - 输入验证
    """

    name = "compliance_check"
    description = "校验内容合规性，检测敏感信息和不当内容"
    tags = ["compliance", "security", "validation"]

    # 敏感信息正则
    SENSITIVE_PATTERNS = {
        "phone": re.compile(r"1[3-9]\d{9}"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "wechat": re.compile(r"微信 | 威信|VX|vx|wx"),
        "qq": re.compile(r"QQ|[Qq][Qq]:?\s*\d{5,}"),
        "id_card": re.compile(r"\d{17}[\dXx]|\d{15}"),
        "bank_card": re.compile(r"\d{16,19}"),
    }

    # 不当内容关键词（示例，实际应使用更完善的敏感词库）
    INAPPROPRIATE_KEYWORDS = [
        # 违法内容
        "赌博", "毒品", "枪支",
        # 色情内容
        "色情", "裸聊", "约炮",
        # 诈骗内容
        "刷单", "传销", "理财返利",
        # 广告营销
        "加微信", "扫码", "点击链接",
    ]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "待校验的内容"
                },
                "check_type": {
                    "type": "string",
                    "description": "校验类型",
                    "enum": ["all", "sensitive_only", "content_only"],
                    "default": "all"
                },
                "strict_mode": {
                    "type": "boolean",
                    "description": "是否启用严格模式",
                    "default": False
                }
            },
            "required": ["content"]
        }

    @staticmethod
    def handle(
        content: str,
        check_type: str = "all",
        strict_mode: bool = False
    ) -> dict:
        """
        处理合规校验请求

        Args:
            content: 待校验的内容
            check_type: 校验类型
            strict_mode: 严格模式（更严格的匹配规则）

        Returns:
            校验结果
        """
        logger.info(f"ComplianceTool: Checking content (type={check_type}, strict={strict_mode})")

        result = {
            "passed": True,
            "issues": [],
            "sensitive_info": [],
            "inappropriate_content": []
        }

        # 敏感信息检测
        if check_type in ["all", "sensitive_only"]:
            sensitive_issues = ComplianceTool._check_sensitive_info(content, strict_mode)
            result["sensitive_info"] = sensitive_issues
            if sensitive_issues:
                result["passed"] = False
                result["issues"].extend(sensitive_issues)

        # 不当内容检测
        if check_type in ["all", "content_only"]:
            content_issues = ComplianceTool._check_inappropriate_content(content, strict_mode)
            result["inappropriate_content"] = content_issues
            if content_issues:
                result["passed"] = False
                result["issues"].extend(content_issues)

        logger.info(f"ComplianceTool: Check completed, passed={result['passed']}")
        return result

    @classmethod
    def _check_sensitive_info(cls, content: str, strict_mode: bool) -> List[str]:
        """检测敏感信息"""
        issues = []

        for info_type, pattern in cls.SENSITIVE_PATTERNS.items():
            matches = pattern.findall(content)
            if matches:
                issues.append(f"检测到敏感信息：{info_type}")

        # 严格模式下检测变体表达
        if strict_mode:
            variant_patterns = [
                re.compile(r"联\s*系\s*方?\s*式"),
                re.compile(r"私\s*聊"),
                re.compile(r"微\s*信?\s*号?"),
            ]
            for pattern in variant_patterns:
                if pattern.search(content):
                    issues.append("检测到敏感信息：联系方式变体")
                    break

        return issues

    @classmethod
    def _check_inappropriate_content(cls, content: str, strict_mode: bool) -> List[str]:
        """检测不当内容"""
        issues = []

        content_lower = content.lower()

        for keyword in cls.INAPPROPRIATE_KEYWORDS:
            if keyword.lower() in content_lower:
                issues.append(f"检测到不当内容：{keyword}")

        # 严格模式下检测拼音变体
        if strict_mode:
            # 这里可以添加拼音变体检测逻辑
            pass

        return issues

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        脱敏内容

        Args:
            content: 原始内容

        Returns:
            脱敏后的内容
        """
        result = content

        # 脱敏手机号
        result = re.sub(r"1[3-9]\d{9}", "1***1234", result)

        # 脱敏邮箱
        result = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "***@***.***",
            result
        )

        # 脱敏 QQ 号
        result = re.sub(r"[Qq][Qq]:?\s*\d{5,}", "QQ: *****", result)

        return result

    @staticmethod
    def get_compliance_rules() -> dict:
        """获取合规规则说明"""
        return {
            "sensitive_info_rules": [
                "禁止直接交换联系方式（手机号、微信、QQ 等）",
                "禁止泄露身份证号、银行卡号等个人敏感信息"
            ],
            "content_rules": [
                "禁止发布违法内容",
                "禁止发布色情低俗内容",
                "禁止发布诈骗信息",
                "禁止发布广告营销内容"
            ],
            "violation_consequences": [
                "内容将被拦截",
                "多次违规可能导致账号受限"
            ]
        }
