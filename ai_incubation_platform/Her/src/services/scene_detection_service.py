"""
场景触发服务

AI Native 核心能力：
根据用户当前场景，适时推送功能入口，而非等待用户主动寻找。

设计原则：
1. AI 主动感知用户场景
2. 在合适时机推送功能入口
3. 不打扰用户，自然融入对话流
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import json

from utils.logger import logger


@dataclass
class SceneContext:
    """场景上下文"""
    user_id: str
    scene_type: str
    trigger_data: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PushAction:
    """推送动作"""
    feature: str  # 功能标识
    priority: str  # high, medium, low
    delay_seconds: int  # 延迟推送秒数
    condition: Optional[Callable] = None  # 额外条件检查


class SceneDetectionService:
    """
    场景检测服务

    识别用户当前场景，决定是否推送功能入口
    """

    # 场景触发规则定义
    SCENE_RULES = {
        # ========== 新用户场景 ==========
        'new_user_registered': {
            'description': '新用户注册完成',
            'trigger': 'user_registered',
            'delay': 5,  # 延迟 5 秒推送
            'push': [
                {'feature': 'photos', 'priority': 'high', 'message': '上传照片让大家认识你'},
            ]
        },
        'profile_incomplete': {
            'description': '资料不完整',
            'trigger': 'profile_check',
            'condition': lambda ctx: ctx.get('profile_completion', 0) < 50,
            'push': [
                {'feature': 'photos', 'priority': 'medium', 'message': '完善资料提升匹配率'},
            ]
        },

        # ========== 匹配场景 ==========
        'first_match': {
            'description': '首次匹配成功',
            'trigger': 'match_created',
            'condition': lambda ctx: ctx.get('match_count', 0) == 1,
            'push': [
                {'feature': 'verify', 'priority': 'medium', 'message': '完成认证增加信任度'},
            ]
        },
        'new_match': {
            'description': '新的匹配',
            'trigger': 'match_created',
            'delay': 0,
            'push': [
                {'feature': 'chat', 'priority': 'high', 'message': '开始和 TA 聊天吧'},
            ]
        },
        'high_compatibility_match': {
            'description': '高匹配度',
            'trigger': 'match_created',
            'condition': lambda ctx: ctx.get('compatibility_score', 0) >= 80,
            'push': [
                {'feature': 'gifts', 'priority': 'low', 'message': '高匹配度，可以考虑送个小礼物'},
            ]
        },

        # ========== 聊天场景 ==========
        'chat_milestone_7days': {
            'description': '聊天满 7 天',
            'trigger': 'chat_duration',
            'condition': lambda ctx: ctx.get('days', 0) == 7,
            'push': [
                {'feature': 'milestones', 'priority': 'high', 'message': '记录你们的第一个里程碑'},
            ]
        },
        'chat_milestone_30days': {
            'description': '聊天满 30 天',
            'trigger': 'chat_duration',
            'condition': lambda ctx: ctx.get('days', 0) == 30,
            'push': [
                {'feature': 'analysis', 'priority': 'high', 'message': '看看你们的关系进展'},
                {'feature': 'membership', 'priority': 'medium', 'message': '解锁更多关系功能'},
            ]
        },
        'silence_detected': {
            'description': '沉默检测',
            'trigger': 'silence_duration',
            'condition': lambda ctx: ctx.get('seconds', 0) > 300,  # 5 分钟
            'push': [
                {'feature': 'chat_assistant', 'priority': 'high', 'message': '需要话题建议吗？'},
            ]
        },

        # ========== 约会场景 ==========
        'dating_intent': {
            'description': '约会意图',
            'trigger': 'intent_detected',
            'condition': lambda ctx: ctx.get('intent') in ['dating', 'date', 'meet'],
            'push': [
                {'feature': 'verify', 'priority': 'high', 'message': '首次约会建议先完成认证'},
                {'feature': 'date_planning', 'priority': 'high', 'message': '我来帮你规划约会'},
            ]
        },
        'gift_occasion': {
            'description': '礼物场景',
            'trigger': 'occasion_detected',
            'condition': lambda ctx: ctx.get('occasion') in ['birthday', 'anniversary', 'holiday'],
            'push': [
                {'feature': 'gifts', 'priority': 'high', 'message': '为特别的日子选份礼物吧'},
            ]
        },

        # ========== 关系场景 ==========
        'conflict_detected': {
            'description': '冲突检测',
            'trigger': 'emotion_analysis',
            'condition': lambda ctx: ctx.get('conflict_level', 0) > 0.6,
            'push': [
                {'feature': 'love_language', 'priority': 'high', 'message': '让我帮你理解 TA 的真实想法'},
            ]
        },
        'relationship_health_low': {
            'description': '关系健康度低',
            'trigger': 'health_check',
            'condition': lambda ctx: ctx.get('health_score', 100) < 50,
            'push': [
                {'feature': 'analysis', 'priority': 'high', 'message': '看看如何改善你们的关系'},
                {'feature': 'coaching', 'priority': 'medium', 'message': '获取关系建议'},
            ]
        },

        # ========== 安全场景 ==========
        'safety_concern': {
            'description': '安全关注',
            'trigger': 'safety_check',
            'condition': lambda ctx: ctx.get('risk_level') == 'high',
            'push': [
                {'feature': 'safety', 'priority': 'high', 'message': '保护好自己，添加紧急联系人'},
            ]
        },
    }

    def __init__(self):
        self._user_scene_history: Dict[str, List[SceneContext]] = {}

    def detect_scene(
        self,
        user_id: str,
        trigger: str,
        context: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        检测场景并返回推送建议

        Args:
            user_id: 用户 ID
            trigger: 触发事件
            context: 上下文数据

        Returns:
            推送建议列表，或 None
        """
        matching_rules = []

        for rule_name, rule in self.SCENE_RULES.items():
            # 检查触发条件
            if rule.get('trigger') != trigger:
                continue

            # 检查额外条件
            condition = rule.get('condition')
            if condition and not condition(context):
                continue

            # 检查是否最近已推送过（避免重复）
            if self._recently_pushed(user_id, rule_name, hours=24):
                logger.debug(f"Scene {rule_name} recently pushed for user {user_id}, skipping")
                continue

            matching_rules.append((rule_name, rule))

        if not matching_rules:
            return None

        # 处理匹配的规则
        results = []
        for rule_name, rule in matching_rules:
            push_actions = rule.get('push', [])
            delay = rule.get('delay', 0)

            for action in push_actions:
                results.append({
                    'scene': rule_name,
                    'feature': action['feature'],
                    'priority': action.get('priority', 'medium'),
                    'message': action.get('message', ''),
                    'delay_seconds': delay,
                })

            # 记录场景历史
            self._record_scene(user_id, rule_name, context)

        if results:
            logger.info(f"Scene detected for user {user_id}: {len(results)} push actions")

        return results

    def _recently_pushed(self, user_id: str, scene_name: str, hours: int = 24) -> bool:
        """检查最近是否已推送过"""
        history = self._user_scene_history.get(user_id, [])
        if not history:
            return False

        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)

        for scene in history:
            if scene.scene_type == scene_name and scene.timestamp > cutoff:
                return True

        return False

    def _record_scene(self, user_id: str, scene_name: str, context: Dict[str, Any]):
        """记录场景历史"""
        if user_id not in self._user_scene_history:
            self._user_scene_history[user_id] = []

        scene = SceneContext(
            user_id=user_id,
            scene_type=scene_name,
            trigger_data=context,
        )

        self._user_scene_history[user_id].append(scene)

        # 限制历史记录数量
        if len(self._user_scene_history[user_id]) > 100:
            self._user_scene_history[user_id] = self._user_scene_history[user_id][-50:]

    def get_user_scene_history(self, user_id: str) -> List[SceneContext]:
        """获取用户场景历史"""
        return self._user_scene_history.get(user_id, [])

    def clear_user_history(self, user_id: str):
        """清除用户场景历史"""
        if user_id in self._user_scene_history:
            del self._user_scene_history[user_id]


# 单例实例
_scene_service: Optional[SceneDetectionService] = None


def get_scene_service() -> SceneDetectionService:
    """获取场景检测服务单例"""
    global _scene_service
    if _scene_service is None:
        _scene_service = SceneDetectionService()
    return _scene_service


# ========== FastAPI 路由 ==========

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from db.database import get_db
from auth.jwt import get_current_user

router = APIRouter(prefix="/api/scene", tags=["场景检测"])


@router.post("/detect")
async def detect_scene_endpoint(
    trigger: str = Body(..., embed=True),
    context: Dict[str, Any] = Body(default={}, embed=True),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检测场景并返回推送建议

    前端调用示例：
    - 用户注册完成时：trigger='user_registered', context={}
    - 匹配成功时：trigger='match_created', context={'match_count': 1, 'compatibility_score': 85}
    - 聊天时长变化：trigger='chat_duration', context={'days': 7}
    """
    user_id = current_user.get("user_id")
    service = get_scene_service()

    results = service.detect_scene(user_id, trigger, context)

    return {
        "success": True,
        "user_id": user_id,
        "trigger": trigger,
        "push_actions": results or []
    }


@router.get("/history/{user_id}")
async def get_scene_history(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户场景历史"""
    service = get_scene_service()
    history = service.get_user_scene_history(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "history": [
            {
                "scene_type": h.scene_type,
                "trigger_data": h.trigger_data,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None
            }
            for h in history[-20:]  # 最近 20 条
        ]
    }


@router.get("/rules")
async def get_scene_rules():
    """获取所有场景规则（用于调试）"""
    return {
        "success": True,
        "rules": [
            {
                "name": name,
                "description": rule.get('description', ''),
                "trigger": rule.get('trigger'),
            }
            for name, rule in SceneDetectionService.SCENE_RULES.items()
        ]
    }