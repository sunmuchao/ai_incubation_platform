"""
对话分析服务 - P3

从用户对话中提取有价值的偏好信号：
- 话题偏好（经常讨论的话题）
- 沟通风格（正式/随意、主动/被动）
- 意愿信号（继续发展的兴趣程度）
- 敏感内容检测（安全风险）

注意：对话分析需遵循隐私保护原则
- 仅分析用户明确同意的对话
- 优先保留摘要和特征，不长期存储原文
- 提供撤回和删除机制
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import re
from collections import defaultdict
from db.database import SessionLocal
from db.models import ConversationDB, UserProfileUpdateDB, UserDB
from utils.logger import logger


# 预定义话题分类
TOPIC_CATEGORIES = {
    "旅行": ["旅行", "旅游", "度假", "景点", "酒店", "机票", "签证", "背包客", "自驾游"],
    "美食": ["美食", "餐厅", "做饭", "食谱", "甜点", "咖啡", "茶", "酒吧", "小吃"],
    "娱乐": ["电影", "电视剧", "综艺", "动漫", "音乐", "演唱会", "明星", "演员"],
    "运动": ["运动", "健身", "跑步", "游泳", "瑜伽", "篮球", "足球", "网球", "滑雪"],
    "学习": ["学习", "读书", "课程", "考试", "培训", "技能", "语言", "证书"],
    "工作": ["工作", "职业", "创业", "公司", "项目", "会议", "加班", "同事"],
    "家庭": ["家庭", "父母", "孩子", "婚姻", "恋爱", "结婚", "生子"],
    "兴趣": ["兴趣", "爱好", "收藏", "手办", "园艺", "摄影", "绘画", "乐器"],
    "科技": ["科技", "数码", "手机", "电脑", "AI", "编程", "互联网", "游戏"],
    "生活": ["生活", "日常", "购物", "装修", "宠物", "健康", "养生", "心理"]
}

# 沟通风格关键词
COMMUNICATION_STYLES = {
    "formal": ["您", "请问", "感谢", "抱歉", "麻烦", "敬请"],
    "casual": ["哈哈", "嘿嘿", "嗯嗯", "好的", "OK", "没问题"],
    "enthusiastic": ["太棒了", "超级", "非常", "特别", "喜欢", "爱"],
    "reserved": ["还行", "可以", "不错", "嗯", "哦", "好"]
}

# 意愿信号关键词
INTENT_SIGNALS = {
    "positive": ["想见", "见面", "一起", "下次", "有空", "交换微信", "电话", "约会"],
    "negative": ["不太合适", "算了吧", "再看看", "暂时不想", "没感觉", "不合适"],
    "neutral": ["先聊聊", "了解一下", "慢慢来", "看缘分"]
}


class ConversationAnalysisService:
    """对话分析服务"""

    def __init__(self):
        self._topic_patterns = self._build_topic_patterns()
        self._style_patterns = self._build_style_patterns()

    def _build_topic_patterns(self) -> Dict[str, re.Pattern]:
        """构建话题匹配正则"""
        patterns = {}
        for category, keywords in TOPIC_CATEGORIES.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            patterns[category] = re.compile(pattern, re.IGNORECASE)
        return patterns

    def _build_style_patterns(self) -> Dict[str, re.Pattern]:
        """构建沟通风格匹配正则"""
        patterns = {}
        for style, keywords in COMMUNICATION_STYLES.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            patterns[style] = re.compile(pattern, re.IGNORECASE)
        return patterns

    def analyze_message(
        self,
        message: str,
        sender_id: str,
        receiver_id: str,
        is_sensitive_check: bool = True
    ) -> Dict[str, Any]:
        """
        分析单条消息

        Args:
            message: 消息内容
            sender_id: 发送者 ID
            receiver_id: 接收者 ID
            is_sensitive_check: 是否进行敏感内容检测

        Returns:
            分析结果字典
        """
        result = {
            "topics": self._extract_topics(message),
            "communication_style": self._detect_communication_style(message),
            "intent_signal": self._detect_intent_signal(message),
            "sentiment_score": self._estimate_sentiment(message),
            "is_sensitive": False,
            "safety_flags": []
        }

        # 敏感内容检测
        if is_sensitive_check:
            sensitive_result = self._check_sensitive_content(message)
            result["is_sensitive"] = sensitive_result["is_sensitive"]
            result["safety_flags"] = sensitive_result["flags"]

        return result

    def _extract_topics(self, text: str) -> List[str]:
        """提取话题标签"""
        topics = []
        for category, pattern in self._topic_patterns.items():
            if pattern.search(text):
                topics.append(category)
        return topics

    def _detect_communication_style(self, text: str) -> Optional[str]:
        """检测沟通风格"""
        style_scores = {}
        for style, pattern in self._style_patterns.items():
            matches = pattern.findall(text)
            style_scores[style] = len(matches)

        if max(style_scores.values()) > 0:
            return max(style_scores.items(), key=lambda x: x[1])[0]
        return None

    def _detect_intent_signal(self, text: str) -> Optional[str]:
        """检测意愿信号"""
        for signal_type, keywords in INTENT_SIGNALS.items():
            for keyword in keywords:
                if keyword in text:
                    return signal_type
        return None

    def _estimate_sentiment(self, text: str) -> float:
        """
        估算情感得分（简化版）
        返回 -1.0（负面）到 1.0（正面）
        """
        positive_words = ["好", "喜欢", "开心", "棒", "满意", "爱", "期待", "谢谢"]
        negative_words = ["不好", "讨厌", "生气", "差", "失望", "恨", "无奈", "抱歉"]

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        total = pos_count + neg_count
        if total == 0:
            return 0.0  # 中性

        return (pos_count - neg_count) / total

    def _check_sensitive_content(self, text: str) -> Dict[str, Any]:
        """
        检测敏感内容

        返回：
            {"is_sensitive": bool, "flags": List[str]}
        """
        flags = []

        # 联系方式检测（简化）
        phone_pattern = r'1[3-9]\d{9}'
        wechat_pattern = r'(微信|wechat|VX|薇信)[：:;\s]*[a-zA-Z0-9_-]+'

        if re.search(phone_pattern, text):
            flags.append("phone_number")
        if re.search(wechat_pattern, text, re.IGNORECASE):
            flags.append("contact_request")

        # 敏感词检测（简化示例）
        sensitive_keywords = ["转账", "汇款", "投资", "理财", "赚钱", "兼职"]
        for keyword in sensitive_keywords:
            if keyword in text:
                flags.append("potential_scam")
                break

        # 不当内容检测
        inappropriate_keywords = ["色情", "赌博", "毒品", "暴力"]
        for keyword in inappropriate_keywords:
            if keyword in text:
                flags.append("inappropriate_content")
                break

        return {
            "is_sensitive": len(flags) > 0,
            "flags": flags
        }

    def save_conversation(
        self,
        sender_id: str,
        receiver_id: str,
        message: str,
        message_type: str = "text",
        analysis_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存对话记录（带分析结果）

        Args:
            sender_id: 发送者 ID
            receiver_id: 接收者 ID
            message: 消息内容
            message_type: 消息类型
            analysis_result: 分析结果

        Returns:
            记录 ID
        """
        conversation_id = str(__import__('uuid').uuid4())

        # 如果没有提供分析结果，则进行分析
        if analysis_result is None:
            analysis_result = self.analyze_message(message, sender_id, receiver_id)

        db = SessionLocal()
        try:
            conv_record = ConversationDB(
                id=conversation_id,
                user_id_1=sender_id,
                user_id_2=receiver_id,
                message_content=message[:500],  # 限制长度
                message_type=message_type,
                sender_id=sender_id,
                topic_tags=json.dumps(analysis_result.get("topics", [])),
                sentiment_score=analysis_result.get("sentiment_score"),
                is_sensitive=analysis_result.get("is_sensitive", False),
                safety_flags=json.dumps(analysis_result.get("safety_flags", []))
            )
            db.add(conv_record)
            db.commit()
            db.refresh(conv_record)

            logger.debug(f"Saved conversation: {conversation_id}")
            return conversation_id
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving conversation: {e}")
            raise
        finally:
            db.close()

    def get_conversation_history(
        self,
        user_id_1: str,
        user_id_2: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取两人之间的对话历史

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            limit: 返回数量限制

        Returns:
            对话记录列表
        """
        db = SessionLocal()
        try:
            conversations = db.query(ConversationDB).filter(
                ((ConversationDB.user_id_1 == user_id_1) & (ConversationDB.user_id_2 == user_id_2)) |
                ((ConversationDB.user_id_1 == user_id_2) & (ConversationDB.user_id_2 == user_id_1))
            ).order_by(ConversationDB.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": c.id,
                    "sender_id": c.sender_id,
                    "message": c.message_content,
                    "type": c.message_type,
                    "topics": json.loads(c.topic_tags) if c.topic_tags else [],
                    "sentiment_score": c.sentiment_score,
                    "is_sensitive": c.is_sensitive,
                    "created_at": c.created_at.isoformat()
                }
                for c in conversations
            ]
        finally:
            db.close()

    def get_user_topic_profile(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户的话题画像

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            话题画像字典
        """
        db = SessionLocal()
        try:
            from datetime import timedelta
            since = datetime.now() - timedelta(days=days)

            # 查询用户发送的消息
            conversations = db.query(ConversationDB).filter(
                ConversationDB.sender_id == user_id,
                ConversationDB.created_at >= since
            ).all()

            if not conversations:
                return {"topics": {}, "style_distribution": {}, "avg_sentiment": 0}

            # 统计话题频率
            topic_counts = defaultdict(int)
            style_counts = defaultdict(int)
            sentiment_sum = 0
            sentiment_count = 0

            for conv in conversations:
                topics = json.loads(conv.topic_tags) if conv.topic_tags else []
                for topic in topics:
                    topic_counts[topic] += 1

                if conv.sentiment_score is not None:
                    sentiment_sum += conv.sentiment_score
                    sentiment_count += 1

            # 按频率排序
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

            return {
                "topics": dict(sorted_topics[:10]),  # 前 10 个话题
                "total_messages": len(conversations),
                "avg_sentiment": round(sentiment_sum / sentiment_count, 2) if sentiment_count > 0 else 0,
                "analysis_period_days": days
            }
        finally:
            db.close()

    def generate_profile_update_suggestions(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        基于对话分析生成画像更新建议

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            画像更新建议列表
        """
        topic_profile = self.get_user_topic_profile(user_id, days)

        if not topic_profile.get("topics"):
            return []

        suggestions = []

        # 提取高频话题作为兴趣建议
        top_topics = [t for t, count in list(topic_profile["topics"].items())[:5] if count >= 3]

        if top_topics:
            suggestions.append({
                "update_type": "interest_from_conversation",
                "suggested_interests": top_topics,
                "confidence": min(0.9, len(top_topics) / 10),
                "source": "conversation_analysis"
            })

        # 情感倾向分析
        if topic_profile.get("avg_sentiment", 0) > 0.5:
            suggestions.append({
                "update_type": "personality_trait",
                "trait": "positive_communicator",
                "confidence": topic_profile["avg_sentiment"],
                "source": "conversation_analysis"
            })
        elif topic_profile.get("avg_sentiment", 0) < -0.3:
            suggestions.append({
                "update_type": "personality_trait",
                "trait": "reserved_communicator",
                "confidence": abs(topic_profile["avg_sentiment"]),
                "source": "conversation_analysis"
            })

        return suggestions


# 全局服务实例
conversation_analyzer = ConversationAnalysisService()
