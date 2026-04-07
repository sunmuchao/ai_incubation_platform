"""
P7 安全风控 AI 服务

基于 AI 的内容安全检测：
- 骚扰内容识别
- 诈骗风险检测
- 不当内容过滤
- 用户风险评估
- 自动告警与处置

架构原则：
- 多层检测：规则引擎 + AI 模型 + 用户反馈
- 渐进处置：警告 -> 限制 -> 封禁
- 可解释性：每个风险判断都有明确原因
- 隐私保护：仅分析必要数据，支持删除
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import re
import json
from collections import defaultdict

from db.models import (
    UserDB, ConversationDB, BehaviorEventDB,
    MatchHistoryDB, ChatMessageDB
)
from utils.logger import logger


# ============= 风险类型定义 =============

class RiskType:
    """风险类型常量"""
    HARASSMENT = "harassment"  # 骚扰
    SCAM = "scam"  # 诈骗
    INAPPROPRIATE_CONTENT = "inappropriate_content"  # 不当内容
    SPAM = "spam"  # 垃圾信息
    FAKE_PROFILE = "fake_profile"  # 虚假资料
    ABNORMAL_BEHAVIOR = "abnormal_behavior"  # 异常行为


# ============= 风险关键词库 =============

# 骚扰相关关键词
HARASSMENT_KEYWORDS = [
    # 性骚扰
    "约吗", "开房", "睡觉", "做爱", "操", "插", "逼", "屄",
    # 言语骚扰
    "贱人", "婊子", "妓女", "出台", "卖淫", "嫖娼",
    # 威胁性语言
    "弄死你", "杀你", "打你", "找到你", "跟踪你",
    # 过度纠缠
    "求求你", "别不理我", "为什么不回我", "必须", "一定", "马上"
]

# 诈骗相关关键词
SCAM_KEYWORDS = [
    # 金钱相关
    "转账", "汇款", "借钱", "贷款", "投资", "理财", "赚钱", "兼职",
    "刷单", "返利", "中奖", "红包", "路费", "手续费", "保证金",
    # 联系方式诱导
    "加微信", "加 QQ", "line", "whatsapp", "私下联系",
    # 虚假身份
    "军官", "维和部队", "联合国", "外交官", "富二代", "老板",
    # 紧急情况
    "急用钱", "生病了", "出事了", "被困", "钱包丢了"
]

# 不当内容关键词
INAPPROPRIATE_KEYWORDS = [
    # 色情
    "色情", "淫秽", "裸体", "做爱", "性交", "口交", "手淫",
    # 暴力
    "暴力", "杀人", "砍人", "枪击", "爆炸", "自杀",
    # 赌博
    "赌博", "赌球", "百家乐", "轮盘", "老虎机", "六合彩",
    # 毒品
    "毒品", "冰毒", "海洛因", "大麻", "摇头丸", "K 粉"
]

# 垃圾信息特征
SPAM_PATTERNS = [
    r'http[s]?://[^\s]+',  # URL 链接
    r'\d{5,}',  # 连续数字（可能是账号）
    r'[A-Za-z]{10,}',  # 长英文（可能是推广）
    r'【.*】',  # 方括号内容（可能是广告）
    r'加 [Vv][Xx]?[:：;\s]*[a-zA-Z0-9_-]+',  # 加微信
]


# ============= 风险等级 =============

class RiskLevel:
    """风险等级"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


class SafetyAIService:
    """
    安全风控 AI 服务

    负责：
    1. 内容安全检测
    2. 用户风险评估
    3. 自动处置建议
    4. 风险告警
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self._build_patterns()

    def _build_patterns(self):
        """编译正则表达式模式"""
        self.harassment_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in HARASSMENT_KEYWORDS),
            re.IGNORECASE
        )
        self.scam_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in SCAM_KEYWORDS),
            re.IGNORECASE
        )
        self.inappropriate_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in INAPPROPRIATE_KEYWORDS),
            re.IGNORECASE
        )
        self.spam_patterns = [re.compile(p) for p in SPAM_PATTERNS]

    # ==================== 内容安全检测 ====================

    def check_content_safety(
        self,
        content: str,
        sender_id: str,
        context_messages: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        检查内容安全性

        Args:
            content: 待检查内容
            sender_id: 发送者 ID
            context_messages: 上下文消息列表（用于检测持续性骚扰）

        Returns:
            检查结果字典，包含：
            - is_safe: 是否安全
            - risk_level: 风险等级
            - risk_types: 风险类型列表
            - risk_score: 风险分数 0-100
            - details: 详细分析结果
            - action_suggestion: 建议处置动作
        """
        result = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW,
            "risk_types": [],
            "risk_score": 0,
            "details": {},
            "action_suggestion": "none"
        }

        # 1. 关键词检测
        keyword_results = self._keyword_detection(content)
        result["details"]["keyword_detection"] = keyword_results

        # 2. 模式检测
        pattern_results = self._pattern_detection(content)
        result["details"]["pattern_detection"] = pattern_results

        # 3. 上下文分析（检测持续性骚扰）
        if context_messages:
            context_result = self._context_analysis(context_messages, sender_id)
            result["details"]["context_analysis"] = context_result
            result["risk_score"] += context_result.get("risk_score", 0)

        # 4. 发送者历史风险评估
        sender_risk = self._get_sender_risk_profile(sender_id)
        result["details"]["sender_risk"] = sender_risk

        # 5. 综合风险评分
        total_score = self._calculate_risk_score(
            keyword_results,
            pattern_results,
            sender_risk
        )
        result["risk_score"] = min(100, total_score)

        # 6. 确定风险等级和类型
        result["risk_level"] = self._get_risk_level(result["risk_score"])
        result["risk_types"] = self._get_risk_types(keyword_results, pattern_results)
        result["is_safe"] = result["risk_level"] == RiskLevel.LOW

        # 7. 生成处置建议
        result["action_suggestion"] = self._get_action_suggestion(
            result["risk_level"],
            sender_risk
        )

        # 8. 记录风险内容（如果需要）
        if result["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._log_risk_content(
                sender_id=sender_id,
                content=content,
                risk_level=result["risk_level"],
                risk_types=result["risk_types"]
            )

        return result

    def _keyword_detection(self, content: str) -> Dict[str, Any]:
        """关键词检测"""
        results = {}

        # 骚扰关键词
        harassment_matches = self.harassment_pattern.findall(content)
        results[RiskType.HARASSMENT] = {
            "detected": len(harassment_matches) > 0,
            "matches": list(set(harassment_matches)),
            "count": len(harassment_matches)
        }

        # 诈骗关键词
        scam_matches = self.scam_pattern.findall(content)
        results[RiskType.SCAM] = {
            "detected": len(scam_matches) > 0,
            "matches": list(set(scam_matches)),
            "count": len(scam_matches)
        }

        # 不当内容关键词
        inappropriate_matches = self.inappropriate_pattern.findall(content)
        results[RiskType.INAPPROPRIATE_CONTENT] = {
            "detected": len(inappropriate_matches) > 0,
            "matches": list(set(inappropriate_matches)),
            "count": len(inappropriate_matches)
        }

        return results

    def _pattern_detection(self, content: str) -> Dict[str, Any]:
        """模式检测"""
        spam_matches = []
        for pattern in self.spam_patterns:
            matches = pattern.findall(content)
            if matches:
                spam_matches.extend(matches)

        return {
            RiskType.SPAM: {
                "detected": len(spam_matches) > 0,
                "matches": list(set(spam_matches)),
                "count": len(spam_matches)
            }
        }

    def _context_analysis(
        self,
        messages: List[Dict],
        sender_id: str
    ) -> Dict[str, Any]:
        """
        上下文分析 - 检测持续性骚扰模式

        分析指标：
        - 短时间内的消息频率
        - 负面内容比例
        - 重复内容比例
        """
        if len(messages) < 3:
            return {"risk_score": 0, "pattern": "normal"}

        # 检查消息频率
        recent_count = sum(1 for m in messages if m.get("sender_id") == sender_id)
        frequency_risk = recent_count > len(messages) * 0.7  # 超过 70% 是同一人发送

        # 检查负面内容比例
        negative_count = 0
        for msg in messages:
            content = msg.get("content", "")
            if self.harassment_pattern.search(content):
                negative_count += 1

        negative_ratio = negative_count / len(messages)

        # 计算风险分数
        risk_score = 0
        if frequency_risk:
            risk_score += 20
        if negative_ratio > 0.5:
            risk_score += 30
        elif negative_ratio > 0.3:
            risk_score += 15

        pattern = "normal"
        if frequency_risk and negative_ratio > 0.3:
            pattern = "persistent_harassment"
        elif frequency_risk:
            pattern = "spamming"

        return {
            "risk_score": risk_score,
            "pattern": pattern,
            "message_count": len(messages),
            "sender_message_count": recent_count,
            "negative_ratio": round(negative_ratio, 2)
        }

    def _get_sender_risk_profile(self, user_id: str) -> Dict[str, Any]:
        """获取发送者风险画像"""
        # 查询用户历史违规记录
        risk_events = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.event_type.in_(["safety_warning", "content_blocked", "account_restricted"])
        ).count()

        # 查询用户被举报次数
        # TODO: 实现举报系统后添加

        # 计算基础风险分
        base_risk = min(50, risk_events * 10)

        risk_level = RiskLevel.LOW
        if base_risk >= 40:
            risk_level = RiskLevel.HIGH
        elif base_risk >= 20:
            risk_level = RiskLevel.MEDIUM

        return {
            "user_id": user_id,
            "violation_count": risk_events,
            "base_risk_score": base_risk,
            "risk_level": risk_level
        }

    def _calculate_risk_score(
        self,
        keyword_results: Dict,
        pattern_results: Dict,
        sender_risk: Dict
    ) -> int:
        """计算综合风险分数"""
        score = sender_risk.get("base_risk_score", 0)

        # 关键词检测加分
        for risk_type, result in keyword_results.items():
            if result["detected"]:
                if risk_type == RiskType.HARASSMENT:
                    score += result["count"] * 15
                elif risk_type == RiskType.SCAM:
                    score += result["count"] * 20
                elif risk_type == RiskType.INAPPROPRIATE_CONTENT:
                    score += result["count"] * 25

        # 模式检测加分
        for risk_type, result in pattern_results.items():
            if result["detected"]:
                score += result["count"] * 10

        return min(100, score)

    def _get_risk_level(self, score: int) -> str:
        """根据分数确定风险等级"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _get_risk_types(
        self,
        keyword_results: Dict,
        pattern_results: Dict
    ) -> List[str]:
        """获取检测到的风险类型"""
        risk_types = []

        for result_dict in [keyword_results, pattern_results]:
            for risk_type, result in result_dict.items():
                if result.get("detected"):
                    risk_types.append(risk_type)

        return risk_types

    def _get_action_suggestion(
        self,
        risk_level: str,
        sender_risk: Dict
    ) -> str:
        """生成处置建议"""
        violation_count = sender_risk.get("violation_count", 0)

        if risk_level == RiskLevel.CRITICAL:
            return "block_user_and_report"
        elif risk_level == RiskLevel.HIGH:
            if violation_count >= 3:
                return "temporary_ban"
            else:
                return "strong_warning"
        elif risk_level == RiskLevel.MEDIUM:
            return "warning"
        else:
            return "none"

    def _log_risk_content(
        self,
        sender_id: str,
        content: str,
        risk_level: str,
        risk_types: List[str]
    ):
        """记录风险内容"""
        try:
            event = BehaviorEventDB(
                id=str(__import__('uuid').uuid4()),
                user_id=sender_id,
                event_type="safety_violation",
                event_data={
                    "content_preview": content[:100],
                    "risk_level": risk_level,
                    "risk_types": risk_types,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.db.add(event)
            self.db.commit()
            logger.warning(f"Safety violation logged: user={sender_id}, risk={risk_level}, types={risk_types}")
        except Exception as e:
            logger.error(f"Error logging risk content: {e}")
            self.db.rollback()

    # ==================== 用户风险评估 ====================

    def assess_user_risk(self, user_id: str) -> Dict[str, Any]:
        """
        评估用户整体风险

        考虑因素：
        - 历史违规记录
        - 被举报次数
        - 行为模式异常
        - 资料真实性
        """
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        # 1. 历史违规
        violations = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.event_type.in_(["safety_violation", "safety_warning", "content_blocked"])
        ).all()

        # 2. 异常行为检测
        abnormal_behaviors = self._detect_abnormal_behaviors(user_id)

        # 3. 资料真实性检查
        profile_authenticity = self._check_profile_authenticity(user)

        # 计算综合风险分
        risk_score = self._calculate_user_risk_score(
            violation_count=len(violations),
            abnormal_behaviors=abnormal_behaviors,
            profile_authenticity=profile_authenticity
        )

        return {
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "violation_count": len(violations),
            "abnormal_behaviors": abnormal_behaviors,
            "profile_authenticity": profile_authenticity,
            "recommendations": self._get_user_risk_recommendations(risk_score, abnormal_behaviors)
        }

    def _detect_abnormal_behaviors(self, user_id: str) -> Dict[str, Any]:
        """检测异常行为"""
        # 检查滑动行为异常（短时间内大量滑动）
        recent_swipes = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.event_type.in_(["swipe_like", "swipe_pass"]),
            BehaviorEventDB.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()

        # 检查发消息异常（短时间内给多人发消息）
        recent_messages = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user_id,
            ChatMessageDB.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()

        unique_receivers = len(set(m.receiver_id for m in recent_messages))

        return {
            "swipe_count_1h": recent_swipes,
            "abnormal_swipe": recent_swipes > 50,
            "message_receivers_1h": unique_receivers,
            "abnormal_messaging": unique_receivers > 20
        }

    def _check_profile_authenticity(self, user: UserDB) -> Dict[str, Any]:
        """检查资料真实性"""
        authenticity_score = 100
        issues = []

        # 检查必填字段
        if not user.avatar_url:
            authenticity_score -= 20
            issues.append("no_avatar")

        if not user.bio or len(user.bio) < 20:
            authenticity_score -= 15
            issues.append("incomplete_bio")

        # TODO: 检查照片验证状态
        # TODO: 检查实名认证状态

        return {
            "score": max(0, authenticity_score),
            "issues": issues,
            "is_suspicious": authenticity_score < 60
        }

    def _calculate_user_risk_score(
        self,
        violation_count: int,
        abnormal_behaviors: Dict,
        profile_authenticity: Dict
    ) -> int:
        """计算用户风险分数"""
        score = 0

        # 违规历史
        score += min(50, violation_count * 15)

        # 异常行为
        if abnormal_behaviors.get("abnormal_swipe"):
            score += 15
        if abnormal_behaviors.get("abnormal_messaging"):
            score += 20

        # 资料真实性
        if profile_authenticity.get("is_suspicious"):
            score += 25

        return min(100, score)

    def _get_user_risk_recommendations(
        self,
        risk_score: int,
        abnormal_behaviors: Dict
    ) -> List[str]:
        """获取用户风险处理建议"""
        recommendations = []

        if risk_score >= 80:
            recommendations.append("建议立即封禁账号")
        elif risk_score >= 60:
            recommendations.append("建议临时限制账号功能")
        elif risk_score >= 40:
            recommendations.append("建议发送警告通知")

        if abnormal_behaviors.get("abnormal_swipe"):
            recommendations.append("限制每小时滑动次数")
        if abnormal_behaviors.get("abnormal_messaging"):
            recommendations.append("限制每小时发消息人数")

        return recommendations

    # ==================== 统计与报告 ====================

    def get_safety_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取安全统计"""
        since = datetime.utcnow() - timedelta(days=days)

        # 违规事件统计
        violations = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.event_type == "safety_violation",
            BehaviorEventDB.created_at >= since
        ).all()

        # 按类型统计
        type_counts = defaultdict(int)
        for event in violations:
            risk_types = event.event_data.get("risk_types", []) if event.event_data else []
            for rt in risk_types:
                type_counts[rt] += 1

        return {
            "total_violations": len(violations),
            "violations_by_type": dict(type_counts),
            "period_days": days,
            "daily_average": round(len(violations) / days, 2)
        }


# 全局服务实例获取函数
def get_safety_service(db: Session) -> SafetyAIService:
    """获取安全服务实例"""
    return SafetyAIService(db)
