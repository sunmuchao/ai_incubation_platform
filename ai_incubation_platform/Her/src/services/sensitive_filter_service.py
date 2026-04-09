"""
敏感信息过滤服务

P0 功能：在 AI 预沟通阶段，自动过滤敏感信息，保护用户隐私

关系阶段过滤策略：
- initial (初识): 完全屏蔽联系方式、地址、真实姓名等
- chatting (聊天中): 可透露兴趣、价值观，仍屏蔽联系方式
- contact_exchange (已交换联系方式): 可透露部分个人信息
- meeting_confirmed (已确认见面): 完全开放，可交换详细信息
"""
import re
from typing import Dict, List, Optional, Any
from utils.logger import logger


class SensitiveFilterService:
    """敏感信息过滤服务"""

    # 敏感信息正则模式
    SENSITIVE_PATTERNS = {
        "phone": {
            "pattern": r"1[3-9]\d{9}",
            "replacement": "[手机号已隐藏]",
            "description": "手机号码"
        },
        "wechat": {
            "pattern": r"(wxid_|微信号：|wechat：|wechat ID：)[a-zA-Z0-9_-]+",
            "replacement": "[微信号已隐藏]",
            "description": "微信号"
        },
        "qq": {
            "pattern": r"qq[:：]?\s*\d{5,10}",
            "replacement": "[QQ 号已隐藏]",
            "description": "QQ 号"
        },
        "email": {
            "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "replacement": "[邮箱已隐藏]",
            "description": "电子邮箱"
        },
        "address": {
            # 匹配包含省市区县的路径或地址
            "pattern": r"([北京上海天津重庆][市区县]|.*?[省][市区县].*?|[市区县].*?[路街道巷小区楼栋号单元室].*?|.*?[路街道巷小区].*?[楼栋号单元室].*?)",
            "replacement": "[地址已隐藏]",
            "description": "详细地址"
        },
        "id_card": {
            "pattern": r"\d{17}[\dXx]|\d{15}",
            "replacement": "[身份证号已隐藏]",
            "description": "身份证号"
        },
        "bank_card": {
            "pattern": r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
            "replacement": "[银行卡号已隐藏]",
            "description": "银行卡号"
        },
        "real_name": {
            # 常见姓氏 + 1-2 个字的名字
            "pattern": r"([张王李赵刘陈杨黄吴周徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金邱陆郝江毛常万钱严覃武邵戴涂靳乔贺苗耿岳冀牛童敖向段祁耿岳荆邱柴苑樊凌霍岳窦祁卜关荆)|([张王李赵刘陈杨黄吴周徐孙][一二三四五六七八九十百千万])",
            "replacement": "[姓名已隐藏]",
            "description": "真实姓名",
            "enabled": False  # 默认禁用，避免误判
        },
        "company": {
            "pattern": r"(\w+?)(公司 | 集团 | 企业 | 厂 | 店 | 局 | 所 | 院 | 校 | 单位)",
            "replacement": "[工作单位已隐藏]",
            "description": "工作单位",
            "enabled": False  # 默认禁用
        }
    }

    # 关系阶段定义
    RELATIONSHIP_STAGES = {
        "initial": 0,           # 初识阶段
        "chatting": 1,          # 聊天中
        "contact_exchange": 2,  # 已交换联系方式
        "meeting_confirmed": 3, # 已确认见面
    }

    # 各阶段允许透露的信息类型
    STAGE_ALLOWED_INFO = {
        "initial": ["interests", "values", "hobbies", "personality"],
        "chatting": ["interests", "values", "hobbies", "personality", "general_location"],
        "contact_exchange": ["interests", "values", "hobbies", "personality", "general_location", "company_type"],
        "meeting_confirmed": ["all"],  # 完全开放
    }

    def __init__(self):
        # 预编译正则
        self._compiled_patterns = {}
        for key, config in self.SENSITIVE_PATTERNS.items():
            if config.get("enabled", True):  # 只编译启用的模式
                self._compiled_patterns[key] = re.compile(
                    config["pattern"],
                    re.IGNORECASE
                )

    def filter_message(
        self,
        content: str,
        relationship_stage: str = "initial"
    ) -> str:
        """
        过滤消息中的敏感信息

        Args:
            content: 原始消息内容
            relationship_stage: 关系阶段

        Returns:
            过滤后的消息
        """
        if not content:
            return ""

        # 如果已确认见面，不 filtering
        if relationship_stage == "meeting_confirmed":
            return content

        # 应用过滤
        filtered_content = content
        for key, pattern in self._compiled_patterns.items():
            filtered_content = pattern.sub(
                self.SENSITIVE_PATTERNS[key]["replacement"],
                filtered_content
            )

        if filtered_content != content:
            logger.info(f"SensitiveFilter: Filtered content from '{content[:50]}...' to '{filtered_content[:50]}...'")

        return filtered_content

    def filter_response(
        self,
        response_data: Dict[str, Any],
        relationship_stage: str = "initial"
    ) -> Dict[str, Any]:
        """
        过滤 API 响应中的敏感信息

        Args:
            response_data: 原始响应数据
            relationship_stage: 关系阶段

        Returns:
            过滤后的响应数据
        """
        if not response_data:
            return response_data

        filtered_data = self._recursive_filter(response_data, relationship_stage)
        filtered_data["_filtered_fields"] = self._get_filtered_fields(response_data, filtered_data)

        return filtered_data

    def _recursive_filter(
        self,
        obj: Any,
        relationship_stage: str,
        path: str = ""
    ) -> Any:
        """递归过滤对象中的敏感字段"""
        if isinstance(obj, str):
            return self.filter_message(obj, relationship_stage)
        elif isinstance(obj, dict):
            return {
                key: self._recursive_filter(value, relationship_stage, f"{path}.{key}")
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._recursive_filter(item, relationship_stage, f"{path}[]")
                for item in obj
            ]
        else:
            return obj

    def _get_filtered_fields(self, original: dict, filtered: dict) -> List[str]:
        """获取被过滤的字段列表"""
        filtered_fields = []

        def compare(orig, filt, path=""):
            if isinstance(orig, str) and isinstance(filt, str):
                if orig != filt:
                    filtered_fields.append(path)
            elif isinstance(orig, dict) and isinstance(filt, dict):
                for key in orig:
                    compare(orig[key], filt.get(key), f"{path}.{key}")
            elif isinstance(orig, list) and isinstance(filt, list):
                for i, (o, f) in enumerate(zip(orig, filt)):
                    compare(o, f, f"{path}[{i}]")

        compare(original, filtered)
        return filtered_fields

    def should_allow_field(
        self,
        field_name: str,
        relationship_stage: str
    ) -> bool:
        """
        判断是否应该允许显示某个字段

        Args:
            field_name: 字段名称
            relationship_stage: 关系阶段

        Returns:
            是否允许显示
        """
        allowed = self.STAGE_ALLOWED_INFO.get(relationship_stage, [])

        if "all" in allowed:
            return True

        # 敏感字段列表
        sensitive_fields = {
            "phone": False,
            "wechat": False,
            "qq": False,
            "email": False,
            "address": False,
            "id_card": False,
            "bank_card": False,
        }

        # 检查字段是否敏感
        for sensitive_field in sensitive_fields:
            if sensitive_field in field_name.lower():
                return False

        return True

    def mask_partial(
        self,
        content: str,
        mask_ratio: float = 0.5
    ) -> str:
        """
        部分掩码（用于 contact_exchange 阶段）

        Args:
            content: 原始内容
            mask_ratio: 掩码比例 (0-1)

        Returns:
            部分掩码后的内容
        """
        if len(content) <= 4:
            return "*" * len(content)

        mask_length = int(len(content) * mask_ratio)
        start = len(content) - mask_length

        return content[:start] + "*" * mask_length


# 全局单例
sensitive_filter_service = SensitiveFilterService()
