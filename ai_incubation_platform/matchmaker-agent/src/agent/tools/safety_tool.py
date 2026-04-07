"""
安全与信任工具 - 参考 Bumble 的安全机制

提供用户安全保护功能：
- 用户举报系统
- 用户封禁管理
- 安全评分计算
- 敏感内容检测
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import re
from utils.logger import logger
from db.database import get_db
from db.repositories import UserRepository


class ReportReason(str, Enum):
    """举报原因"""
    FAKE_PROFILE = "fake_profile"  # 虚假资料
    HARASSMENT = "harassment"  # 骚扰行为
    INAPPROPRIATE_CONTENT = "inappropriate_content"  # 不当内容
    SPAM = "spam"  # 垃圾信息
    UNDERAGE = "underage"  # 未成年
    SCAM = "scam"  # 诈骗
    OTHER = "other"  # 其他


class BanStatus(str, Enum):
    """封禁状态"""
    ACTIVE = "active"  # 正常
    WARNED = "warned"  # 已警告
    TEMP_BANNED = "temp_banned"  # 临时封禁
    PERMANENT_BANNED = "permanent_banned"  # 永久封禁


@dataclass
class Report:
    """举报记录"""
    id: str
    reporter_id: str
    reported_user_id: str
    reason: str
    description: str
    status: str  # pending, reviewed, resolved
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_action: Optional[str] = None


@dataclass
class SafetyScore:
    """安全评分"""
    overall_score: float  # 总体安全评分 0-1
    profile_completeness: float  # 资料完整度
    behavior_score: float  # 行为评分
    verification_status: float  # 认证状态
    risk_factors: List[str]  # 风险因素


class SafetyService:
    """
    安全服务 - 参考 Bumble 的安全机制

    功能：
    - 用户举报处理
    - 安全评分计算
    - 敏感内容检测
    - 自动警告/封禁
    """

    # 敏感词库 (示例)
    SENSITIVE_WORDS = [
        "转账", "汇款", "投资", "理财", "博彩",
        "微信", "QQ", "电话", "地址",
        "色情", "裸聊", "视频聊天"
    ]

    # 自动封禁阈值
    AUTO_BAN_THRESHOLD = 5  # 被举报 5 次自动临时封禁
    AUTO_WARN_THRESHOLD = 3  # 被举报 3 次自动警告

    # 风险行为权重
    RISK_WEIGHTS = {
        "fake_profile": 0.3,
        "harassment": 0.4,
        "inappropriate_content": 0.25,
        "spam": 0.15,
        "underage": 0.5,
        "scam": 0.5,
        "other": 0.1
    }

    @staticmethod
    def detect_sensitive_content(text: str) -> List[str]:
        """
        检测敏感内容

        Args:
            text: 待检测文本

        Returns:
            检测到的敏感词列表
        """
        found = []
        text_lower = text.lower()
        for word in SafetyService.SENSITIVE_WORDS:
            if word.lower() in text_lower:
                found.append(word)
        return found

    @staticmethod
    def calculate_safety_score(
        user_data: dict,
        report_count: int = 0,
        verified: bool = False
    ) -> SafetyScore:
        """
        计算用户安全评分

        Args:
            user_data: 用户数据
            report_count: 被举报次数
            verified: 是否已认证

        Returns:
            安全评分
        """
        # 资料完整度 (30%)
        completeness_factors = [
            user_data.get("bio"),
            user_data.get("interests"),
            user_data.get("avatar_url"),
            user_data.get("values"),
        ]
        profile_completeness = sum(1 for f in completeness_factors if f) / len(completeness_factors)

        # 行为评分 (40%) - 基于举报
        behavior_score = max(0, 1 - report_count * 0.2)

        # 认证状态 (30%)
        verification_status = 1.0 if verified else 0.3

        # 总体评分
        overall_score = (
            profile_completeness * 0.3 +
            behavior_score * 0.4 +
            verification_status * 0.3
        )

        # 风险因素
        risk_factors = []
        if report_count >= SafetyService.AUTO_WARN_THRESHOLD:
            risk_factors.append("多次被举报")
        if not user_data.get("bio"):
            risk_factors.append("资料不完整")
        if not verified:
            risk_factors.append("未通过认证")

        return SafetyScore(
            overall_score=round(overall_score, 3),
            profile_completeness=round(profile_completeness, 3),
            behavior_score=round(behavior_score, 3),
            verification_status=round(verification_status, 3),
            risk_factors=risk_factors
        )

    @staticmethod
    def should_auto_action(report_count: int) -> tuple:
        """
        判断是否需要自动处理

        Args:
            report_count: 被举报次数

        Returns:
            (是否需要警告，是否需要封禁)
        """
        should_warn = report_count >= SafetyService.AUTO_WARN_THRESHOLD
        should_ban = report_count >= SafetyService.AUTO_BAN_THRESHOLD
        return should_warn, should_ban


class SafetyTool:
    """
    安全工具 - Agent 工具封装

    功能：
    - 用户举报
    - 安全评分查询
    - 敏感内容检测
    - 封禁管理
    """

    name = "safety_tool"
    description = "用户安全与信任工具 (参考 Bumble 安全机制)"
    tags = ["safety", "report", "ban", "trust"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["report_user", "get_safety_score", "detect_content", "get_user_status"]
                },
                "reporter_id": {
                    "type": "string",
                    "description": "举报人用户 ID"
                },
                "reported_user_id": {
                    "type": "string",
                    "description": "被举报用户 ID"
                },
                "reason": {
                    "type": "string",
                    "description": "举报原因",
                    "enum": ["fake_profile", "harassment", "inappropriate_content", "spam", "underage", "scam", "other"]
                },
                "description": {
                    "type": "string",
                    "description": "举报详细描述"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID (用于查询安全评分)"
                },
                "content": {
                    "type": "string",
                    "description": "待检测内容"
                }
            },
            "required": ["action"]
        }

    @staticmethod
    def handle(action: str, **kwargs) -> dict:
        """处理安全相关请求"""
        logger.info(f"SafetyTool: Executing action={action}")

        try:
            if action == "report_user":
                return SafetyTool._handle_report(kwargs)
            elif action == "get_safety_score":
                return SafetyTool._handle_safety_score(kwargs)
            elif action == "detect_content":
                return SafetyTool._handle_content_detection(kwargs)
            elif action == "get_user_status":
                return SafetyTool._handle_user_status(kwargs)
            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"SafetyTool: Failed to execute action {action}: {e}")
            return {"error": str(e)}

    @staticmethod
    def _handle_report(params: dict) -> dict:
        """处理举报请求"""
        reporter_id = params.get("reporter_id")
        reported_user_id = params.get("reported_user_id")
        reason = params.get("reason")
        description = params.get("description", "")

        if not reporter_id or not reported_user_id or not reason:
            return {"error": "Missing required parameters"}

        # 验证被举报用户是否存在
        db = next(get_db())
        user_repo = UserRepository(db)
        reported_user = user_repo.get_by_id(reported_user_id)
        if not reported_user:
            return {"error": "Reported user not found"}

        # 检测举报描述中的敏感内容
        sensitive_words = SafetyService.detect_sensitive_content(description)

        # 创建举报记录 (简化版，实际应存储到数据库)
        report_id = f"rpt_{reporter_id}_{reported_user_id}_{datetime.now().timestamp()}"
        report = {
            "id": report_id,
            "reporter_id": reporter_id,
            "reported_user_id": reported_user_id,
            "reason": reason,
            "description": description,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "sensitive_words_detected": sensitive_words
        }

        # 获取用户被举报次数
        report_count = SafetyTool._get_report_count(reported_user_id)

        # 判断是否需要自动处理
        should_warn, should_ban = SafetyService.should_auto_action(report_count + 1)

        auto_action = None
        if should_ban:
            auto_action = "temp_banned"
        elif should_warn:
            auto_action = "warned"

        logger.info(f"SafetyTool: Report created for user {reported_user_id}, auto_action={auto_action}")

        return {
            "report": report,
            "report_count": report_count + 1,
            "auto_action": auto_action,
            "message": f"举报已提交，我们将尽快处理" + (f"，用户已被{auto_action}" if auto_action else "")
        }

    @staticmethod
    def _handle_safety_score(params: dict) -> dict:
        """处理安全评分查询"""
        user_id = params.get("user_id")
        if not user_id:
            return {"error": "user_id is required"}

        db = next(get_db())
        user_repo = UserRepository(db)
        db_user = user_repo.get_by_id(user_id)
        if not db_user:
            return {"error": "User not found"}

        from api.users import _from_db
        user = _from_db(db_user)

        # 获取举报次数
        report_count = SafetyTool._get_report_count(user_id)

        # 计算安全评分
        safety_score = SafetyService.calculate_safety_score(
            {
                "bio": user.bio,
                "interests": user.interests,
                "avatar_url": user.avatar,
                "values": user.values,
            },
            report_count,
            verified=False  # 简化处理
        )

        return {
            "user_id": user_id,
            "safety_score": asdict(safety_score),
            "report_count": report_count
        }

    @staticmethod
    def _handle_content_detection(params: dict) -> dict:
        """处理内容检测"""
        content = params.get("content")
        if not content:
            return {"error": "content is required"}

        sensitive_words = SafetyService.detect_sensitive_content(content)
        is_safe = len(sensitive_words) == 0

        return {
            "is_safe": is_safe,
            "sensitive_words": sensitive_words,
            "word_count": len(sensitive_words),
            "content_length": len(content)
        }

    @staticmethod
    def _handle_user_status(params: dict) -> dict:
        """处理用户状态查询"""
        user_id = params.get("user_id")
        if not user_id:
            return {"error": "user_id is required"}

        db = next(get_db())
        user_repo = UserRepository(db)
        db_user = user_repo.get_by_id(user_id)
        if not db_user:
            return {"error": "User not found"}

        report_count = SafetyTool._get_report_count(user_id)
        should_warn, should_ban = SafetyService.should_auto_action(report_count)

        status = "active"
        if should_ban:
            status = "temp_banned"
        elif should_warn:
            status = "warned"

        return {
            "user_id": user_id,
            "status": status,
            "report_count": report_count,
            "is_active": db_user.is_active
        }

    @staticmethod
    def _get_report_count(user_id: str) -> int:
        """获取用户被举报次数 (简化实现)"""
        # 实际应从数据库读取
        # 这里使用内存缓存模拟
        if not hasattr(SafetyTool, "_report_counts"):
            SafetyTool._report_counts = {}
        return SafetyTool._report_counts.get(user_id, 0)


# 注意：这是一个简化实现，实际生产环境需要：
# 1. 举报记录持久化到数据库
# 2. 封禁状态管理
# 3. 审核流程
# 4. 申诉机制
