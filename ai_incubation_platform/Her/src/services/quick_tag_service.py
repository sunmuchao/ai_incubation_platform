"""
动态快捷标签服务 - AI 驱动

根据用户状态动态生成最相关的快捷标签，
而非硬编码规则。

感知维度：
- 基础状态：注册天数、资料完整度、认证状态
- 社交状态：未读消息、匹配数、活跃对话数
- 行为模式：最近活跃时间、滑动行为、功能使用
- 关系进展：关系阶段、最近约会、里程碑
- 时间上下文：当前时段、周几、节假日
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from utils.db_session_manager import db_session_readonly
from db.models import (
    UserDB, ChatConversationDB, MatchHistoryDB,
    SwipeActionDB, RelationshipProgressDB, BehaviorEventDB
)
from utils.logger import logger
from llm.client import call_llm


class QuickTagService:
    """
    动态快捷标签服务

    AI 分析用户当前状态，返回最相关的快捷标签。
    """

    def get_quick_tags(self, user_id: str) -> List[Dict]:
        """
        获取动态快捷标签

        Args:
            user_id: 用户 ID

        Returns:
            快捷标签列表，如：
            [
                {"label": "今日推荐", "trigger": "看看今天有什么推荐"},
                {"label": "谁在等我", "trigger": "有谁给我发消息了吗"}
            ]
        """
        try:
            # 1. 收集用户状态
            user_state = self._get_user_state(user_id)

            # 2. AI 生成标签
            tags = self._generate_tags_with_ai(user_state)

            if tags:
                return tags

            # 3. 降级：极简默认
            return self._get_fallback_tags(user_state)

        except Exception as e:
            logger.error(f"QuickTagService error: {e}")
            return [{"label": "今日推荐", "trigger": "看看今天有什么推荐"}]

    def _get_user_state(self, user_id: str) -> Dict:
        """收集用户状态数据（多维感知）"""
        state = {
            "user_id": user_id,
            # === 基础状态 ===
            "is_new_user": False,
            "days_since_register": 0,
            "profile_completeness": 0,  # 资料完整度 0-100
            "is_verified": False,
            "is_member": False,
            # === 社交状态 ===
            "unread_count": 0,
            "match_count": 0,
            "active_chat_count": 0,
            "pending_match_count": 0,  # 待处理的匹配
            # === 行为模式 ===
            "last_active_hours_ago": 999,
            "recent_swipe_like_ratio": 0.5,  # 最近滑动点赞比例
            "most_used_feature": None,
            "login_frequency": "unknown",  # daily/weekly/occasional
            # === 关系进展 ===
            "relationship_stage": "single",  # single/dating/relationship
            "days_since_last_date": 999,
            "has_milestone": False,
            # === 时间上下文 ===
            "time_of_day": "unknown",  # morning/afternoon/evening/night
            "is_weekend": False,
            # === 情感状态 ===
            "recent_emotion_trend": "neutral",  # positive/neutral/negative
        }

        try:
            with db_session_readonly() as db:
                # ========== 基础状态 ==========
                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                if not user:
                    return state

                # 注册天数
                if user.created_at:
                    days = (datetime.now() - user.created_at).days
                    state["days_since_register"] = days
                    state["is_new_user"] = days < 3

                # 资料完整度
                completeness = self._calculate_profile_completeness(user)
                state["profile_completeness"] = completeness

                # 认证状态
                state["is_verified"] = getattr(user, "verified", False) or False

                # 会员状态
                state["is_member"] = getattr(user, "is_member", False) or False

                # ========== 社交状态 ==========
                # 未读消息和活跃对话
                conversations = db.query(ChatConversationDB).filter(
                    (ChatConversationDB.user_id_1 == user_id) |
                    (ChatConversationDB.user_id_2 == user_id)
                ).all()

                state["unread_count"] = sum(c.unread_count or 0 for c in conversations)
                state["active_chat_count"] = len([
                    c for c in conversations
                    if c.last_message_at and
                    (datetime.now() - c.last_message_at).days < 7
                ])

                # 匹配数
                matches = db.query(MatchHistoryDB).filter(
                    (MatchHistoryDB.user_id_1 == user_id) |
                    (MatchHistoryDB.user_id_2 == user_id),
                    MatchHistoryDB.status == "matched"
                ).count()
                state["match_count"] = matches

                # 待处理匹配（对方喜欢但自己未处理）
                pending = db.query(SwipeActionDB).filter(
                    SwipeActionDB.target_user_id == user_id,
                    SwipeActionDB.action == "like",
                ).count()
                state["pending_match_count"] = min(pending, 10)

                # ========== 行为模式 ==========
                # 最近活跃时间
                if user.updated_at:
                    hours = (datetime.now() - user.updated_at).total_seconds() / 3600
                    state["last_active_hours_ago"] = round(hours, 1)

                # 最近滑动行为
                recent_swipes = db.query(SwipeActionDB).filter(
                    SwipeActionDB.user_id == user_id,
                    SwipeActionDB.created_at >= datetime.now() - timedelta(days=7)
                ).all()

                if recent_swipes:
                    likes = sum(1 for s in recent_swipes if s.action == "like")
                    state["recent_swipe_like_ratio"] = likes / len(recent_swipes)

                # 登录频率（基于最近 30 天行为）
                login_events = db.query(BehaviorEventDB).filter(
                    BehaviorEventDB.user_id == user_id,
                    BehaviorEventDB.event_type == "login",
                    BehaviorEventDB.created_at >= datetime.now() - timedelta(days=30)
                ).count()

                if login_events >= 20:
                    state["login_frequency"] = "daily"
                elif login_events >= 8:
                    state["login_frequency"] = "weekly"
                else:
                    state["login_frequency"] = "occasional"

                # ========== 关系进展 ==========
                # 关系阶段
                progress = db.query(RelationshipProgressDB).filter(
                    (RelationshipProgressDB.user_id_1 == user_id) |
                    (RelationshipProgressDB.user_id_2 == user_id)
                ).order_by(RelationshipProgressDB.created_at.desc()).first()

                if progress:
                    state["relationship_stage"] = getattr(progress, "stage", "single") or "single"
                    state["has_milestone"] = True

                # 最近约会
                last_date = db.query(BehaviorEventDB).filter(
                    BehaviorEventDB.user_id == user_id,
                    BehaviorEventDB.event_type == "date_completed",
                ).order_by(BehaviorEventDB.created_at.desc()).first()

                if last_date and last_date.created_at:
                    days = (datetime.now() - last_date.created_at).days
                    state["days_since_last_date"] = days

                # ========== 时间上下文 ==========
                hour = datetime.now().hour
                if 6 <= hour < 12:
                    state["time_of_day"] = "morning"
                elif 12 <= hour < 18:
                    state["time_of_day"] = "afternoon"
                elif 18 <= hour < 22:
                    state["time_of_day"] = "evening"
                else:
                    state["time_of_day"] = "night"

                state["is_weekend"] = datetime.now().weekday() >= 5

        except Exception as e:
            logger.error(f"Error getting user state: {e}")

        return state

    def _calculate_profile_completeness(self, user: UserDB) -> int:
        """计算资料完整度 0-100"""
        score = 0
        weights = {
            "name": 15,
            "age": 10,
            "gender": 10,
            "location": 10,
            "bio": 15,
            "interests": 15,
            "photos": 15,
            "goal": 10,
        }

        if user.name:
            score += weights["name"]
        if user.age:
            score += weights["age"]
        if user.gender:
            score += weights["gender"]
        if user.location:
            score += weights["location"]
        if user.bio and len(user.bio) > 10:
            score += weights["bio"]
        if user.interests and len(user.interests) >= 3:
            score += weights["interests"]
        if user.photos and len(user.photos) >= 2:
            score += weights["photos"]
        if user.goal:
            score += weights["goal"]

        return min(score, 100)

    def _generate_tags_with_ai(self, user_state: Dict) -> Optional[List[Dict]]:
        """
        使用 AI 生成快捷标签

        让 AI 分析用户状态，判断最可能的下一步需求。
        """
        prompt = f"""分析用户状态，推荐 1-3 个最相关的快捷标签。

【用户状态】
基础：
- 注册天数：{user_state.get("days_since_register", 0)} 天
- 是否新用户：{"是" if user_state.get("is_new_user") else "否"}
- 资料完整度：{user_state.get("profile_completeness", 0)}%
- 已认证：{"是" if user_state.get("is_verified") else "否"}
- 会员：{"是" if user_state.get("is_member") else "否"}

社交：
- 未读消息：{user_state.get("unread_count", 0)} 条
- 匹配对象：{user_state.get("match_count", 0)} 个
- 活跃对话：{user_state.get("active_chat_count", 0)} 个
- 待处理匹配：{user_state.get("pending_match_count", 0)} 个

行为：
- 最后活跃：{user_state.get("last_active_hours_ago", 999):.1f} 小时前
- 登录频率：{user_state.get("login_frequency", "unknown")}
- 滑动点赞率：{user_state.get("recent_swipe_like_ratio", 0.5) * 100:.0f}%

关系：
- 关系阶段：{user_state.get("relationship_stage", "single")}
- 距上次约会：{user_state.get("days_since_last_date", 999)} 天

时间：
- 时段：{user_state.get("time_of_day", "unknown")}
- 周末：{"是" if user_state.get("is_weekend") else "否"}

【任务】
根据用户状态，推荐 1-3 个最可能的下一步操作。
每个标签包含：label（显示文字，4字以内）和 trigger（触发语）。

【推荐策略】
1. 新用户+资料不全 → 引导完善资料
2. 有未读消息 → 引导查看消息
3. 有待处理匹配 → 引导查看谁喜欢我
4. 活跃用户+无匹配 → 引导今日推荐
5. 有匹配+晚上 → 可能想聊天
6. 有约会+周末 → 约会建议
7. 关系稳定 → 关系经营建议

【输出格式】
请严格输出 JSON 格式：
{{
  "tags": [
    {{"label": "今日推荐", "trigger": "看看今天有什么推荐"}},
    {{"label": "谁在等我", "trigger": "有谁给我发消息了吗"}}
  ],
  "reason": "简要说明推荐理由"
}}

只返回 JSON，不要其他文字。"""

        try:
            response = call_llm(
                prompt=prompt,
                system_prompt="你是一个用户行为分析专家，帮助判断用户最可能的需求。",
                temperature=0.3,
                max_tokens=300,
            )

            # 解析响应
            result = self._parse_response(response)
            return result

        except Exception as e:
            logger.debug(f"AI tag generation failed: {e}")
            return None

    def _parse_response(self, response: str) -> Optional[List[Dict]]:
        """解析 AI 响应"""
        try:
            # 清理响应
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            tags = data.get("tags", [])

            # 验证格式
            valid_tags = []
            for tag in tags:
                if "label" in tag and "trigger" in tag:
                    valid_tags.append({
                        "label": str(tag["label"])[:6],  # 限制长度
                        "trigger": str(tag["trigger"])
                    })

            return valid_tags if valid_tags else None

        except json.JSONDecodeError:
            return None

    def _get_fallback_tags(self, user_state: Dict) -> List[Dict]:
        """
        降级方案：基于状态的简单判断

        只在 AI 不可用时使用
        """
        tags = []

        # 有未读消息
        if user_state.get("unread_count", 0) > 0:
            tags.append({"label": "谁在等我", "trigger": "有谁给我发消息了吗"})

        # 待处理匹配
        if user_state.get("pending_match_count", 0) > 0:
            tags.append({"label": "谁喜欢我", "trigger": "看看谁喜欢我"})

        # 默认推荐
        tags.append({"label": "今日推荐", "trigger": "看看今天有什么推荐"})

        return tags[:2]  # 最多 2 个


# 全局实例
_quick_tag_service: Optional[QuickTagService] = None


def get_quick_tag_service() -> QuickTagService:
    """获取快捷标签服务实例"""
    global _quick_tag_service
    if _quick_tag_service is None:
        _quick_tag_service = QuickTagService()
    return _quick_tag_service