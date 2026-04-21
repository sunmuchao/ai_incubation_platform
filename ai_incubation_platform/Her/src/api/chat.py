"""
实时聊天 API

P4 新增:
- WebSocket 消息
- 聊天界面
- 消息历史记录
"""
import uuid
import random
from typing import List, Optional, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timedelta
import re

from db.database import get_db
from auth.jwt import get_current_user, get_current_user_optional
from db.models import UserDB, ChatConversationDB
from db.models import UserProfileUpdateDB
from services.chat_service import ChatService
from config import settings
from utils.logger import logger, get_trace_id
from utils.db_session_manager import db_session
from agent.user_simulation_agent import get_agent_for_user
import asyncio


router = APIRouter(prefix="/api/chat", tags=["实时聊天"])

# ============= 无感画像更新（0-token 规则提取） =============

PROFILE_AUTO_UPDATE_SOURCE = "chat_auto_rule"
PROFILE_AUTO_ROLLBACK_SOURCE = "chat_auto_rollback"
def _get_auto_profile_runtime_config() -> Dict[str, Any]:
    return {
        "cooldown_hours": max(1, int(getattr(settings, "chat_auto_update_cooldown_hours", 24))),
        "confirm_window_days": max(1, int(getattr(settings, "chat_auto_update_confirm_window_days", 30))),
        "min_text_len_for_llm": max(8, int(getattr(settings, "chat_auto_update_min_text_len_for_llm", 18))),
        "llm_max_tokens": max(60, int(getattr(settings, "chat_auto_update_llm_max_tokens", 120))),
        "pending_ttl_days": max(1, int(getattr(settings, "chat_auto_update_pending_ttl_days", 30))),
        "threshold": {
            "location": max(0.8, float(getattr(settings, "chat_auto_update_location_threshold", 1.4))),
            "occupation": max(0.8, float(getattr(settings, "chat_auto_update_occupation_threshold", 1.4))),
        },
    }

INTEREST_KEYWORDS = {
    "动漫": "动漫",
    "二次元": "动漫",
    "音乐": "音乐",
    "听歌": "音乐",
    "演唱会": "音乐",
    "电影": "电影",
    "追剧": "追剧",
    "游戏": "游戏",
    "旅行": "旅行",
    "旅游": "旅行",
    "跑步": "跑步",
    "健身": "健身",
    "美食": "美食",
    "探店": "探店",
    "摄影": "摄影",
    "阅读": "阅读",
    "看书": "阅读",
    "编程": "编程",
}

OCCUPATION_PATTERNS = [
    (r"(软件开发|开发工程师|程序员|后端开发|前端开发)", "软件开发"),
    (r"(产品经理)", "产品经理"),
    (r"(测试工程师|软件测试)", "测试工程师"),
    (r"(设计师|UI设计)", "设计师"),
    (r"(运营)", "运营"),
]

CITY_PATTERNS = ["无锡", "北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安"]


def _extract_profile_signals_from_text(text: str) -> Dict[str, Any]:
    """
    从聊天文本提取可用于画像更新的结构化信号（规则版，无 token 消耗）。
    """
    msg = (text or "").strip()
    if len(msg) < 8:
        return {}
    # 仅在“自我陈述”场景触发，降低误判
    if not any(token in msg for token in ["我", "自己", "平时", "本人", "从事", "喜欢"]):
        return {}

    out: Dict[str, Any] = {}

    # 地点提取：优先城市词典
    for city in CITY_PATTERNS:
        if city in msg:
            out["location"] = city
            break

    # 职业提取
    for pattern, normalized in OCCUPATION_PATTERNS:
        if re.search(pattern, msg):
            out["occupation"] = normalized
            break

    # 兴趣提取（多值）
    interests: List[str] = []
    for kw, normalized in INTEREST_KEYWORDS.items():
        if kw in msg and normalized not in interests:
            interests.append(normalized)
    if interests:
        out["interests"] = interests[:6]

    return out


def _parse_profile_signals_from_llm_text(llm_text: str) -> Dict[str, Any]:
    """
    解析小模型返回的 JSON 信号，返回已清洗字段。
    """
    if not llm_text:
        return {}
    try:
        payload = json.loads(llm_text)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}

    result: Dict[str, Any] = {}
    location = payload.get("location")
    occupation = payload.get("occupation")
    interests = payload.get("interests")

    if isinstance(location, str) and location.strip():
        result["location"] = location.strip()[:40]
    if isinstance(occupation, str) and occupation.strip():
        result["occupation"] = occupation.strip()[:40]
    if isinstance(interests, list):
        items: List[str] = []
        for it in interests:
            if isinstance(it, str) and it.strip():
                cleaned = it.strip()[:20]
                if cleaned not in items:
                    items.append(cleaned)
        if items:
            result["interests"] = items[:6]
    return result


def _extract_profile_signals_with_small_llm(text: str) -> Dict[str, Any]:
    """
    小模型兜底抽取（仅规则抽不到时触发，严格控 token）。
    """
    runtime_cfg = _get_auto_profile_runtime_config()
    msg = (text or "").strip()
    if len(msg) < runtime_cfg["min_text_len_for_llm"]:
        return {}
    if not any(token in msg for token in ["我", "自己", "平时", "本人", "从事", "喜欢"]):
        return {}

    try:
        from llm.client import call_llm
        system_prompt = (
            "你是信息抽取器。只抽取用户自我介绍里的画像字段。"
            "输出严格 JSON: {\"location\":\"\",\"occupation\":\"\",\"interests\":[]}"
            "若不确定填空字符串或空数组。禁止输出其他内容。"
        )
        llm_text = call_llm(
            prompt=msg,
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=runtime_cfg["llm_max_tokens"],
            timeout=30,
        )
        return _parse_profile_signals_from_llm_text(llm_text)
    except Exception as e:
        logger.warning(f"[chat_auto_profile] small-llm extract failed: {e}")
        return {}


def _merge_interests(existing_raw: Optional[str], new_items: List[str]) -> str:
    existing: List[str] = []
    if existing_raw:
        try:
            parsed = json.loads(existing_raw)
            if isinstance(parsed, list):
                existing = [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            existing = [x.strip() for x in str(existing_raw).split(",") if x.strip()]
    merged = list(dict.fromkeys(existing + new_items))
    return json.dumps(merged[:12], ensure_ascii=False)


def _record_profile_update(
    db: Session,
    user_id: str,
    update_type: str,
    old_value: Any,
    new_value: Any,
    confidence: float,
    applied: bool,
) -> None:
    db.add(UserProfileUpdateDB(
        id=str(uuid.uuid4()),
        user_id=user_id,
        update_type=update_type,
        old_value="" if old_value is None else str(old_value),
        new_value="" if new_value is None else str(new_value),
        source=PROFILE_AUTO_UPDATE_SOURCE,
        confidence=confidence,
        applied=applied,
    ))


def _cleanup_expired_pending_updates(db: Session, user_id: str, update_type: str, expire_before: datetime) -> None:
    db.query(UserProfileUpdateDB).filter(
        UserProfileUpdateDB.user_id == user_id,
        UserProfileUpdateDB.update_type == update_type,
        UserProfileUpdateDB.source == PROFILE_AUTO_UPDATE_SOURCE,
        UserProfileUpdateDB.applied.is_(False),
        UserProfileUpdateDB.created_at < expire_before,
    ).delete(synchronize_session=False)


def _get_pending_evidence_score(
    db: Session,
    user_id: str,
    update_type: str,
    new_value: str,
    window_start: datetime,
) -> float:
    rows = db.query(UserProfileUpdateDB.confidence).filter(
        UserProfileUpdateDB.user_id == user_id,
        UserProfileUpdateDB.update_type == update_type,
        UserProfileUpdateDB.new_value == new_value,
        UserProfileUpdateDB.source == PROFILE_AUTO_UPDATE_SOURCE,
        UserProfileUpdateDB.applied.is_(False),
        UserProfileUpdateDB.created_at >= window_start,
    ).all()
    return float(sum((r[0] or 0.0) for r in rows))


def _safe_parse_json_object(raw: Any) -> Dict[str, Any]:
    """安全解析 JSON 对象字符串，失败时返回空对象。"""
    if not raw or not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _sync_vector_dimensions_for_auto_updates(
    user: UserDB,
    applied_fields: Dict[str, Any],
) -> None:
    """
    同步无感更新到 vector_dimensions，保证基础字段与画像维度一致。
    """
    self_profile_data = _safe_parse_json_object(getattr(user, "self_profile_json", None))
    desire_profile_data = _safe_parse_json_object(getattr(user, "desire_profile_json", None))

    self_vector = self_profile_data.setdefault("vector_dimensions", {})
    desire_vector = desire_profile_data.setdefault("vector_dimensions", {})

    demographics = self_vector.setdefault("demographics", {})
    lifestyle = self_vector.setdefault("lifestyle", {})
    interest_pref = desire_vector.setdefault("interests", {})

    if "location" in applied_fields:
        demographics["location"] = applied_fields["location"]
    if "occupation" in applied_fields:
        demographics["occupation"] = applied_fields["occupation"]
    if "interests" in applied_fields and isinstance(applied_fields["interests"], list):
        interest_pref["declared_interests"] = applied_fields["interests"][:12]
        interest_pref["clicked_types"] = interest_pref.get("clicked_types", [])
        lifestyle["hobby_labels"] = applied_fields["interests"][:8]

    user.self_profile_json = json.dumps(self_profile_data, ensure_ascii=False)
    user.desire_profile_json = json.dumps(desire_profile_data, ensure_ascii=False)


def _safe_auto_update_profile_from_chat(db: Session, user_id: str, text: str) -> Dict[str, Any]:
    """
    无感画像更新（规则版）：
    - 低风险字段（interests）可直接合并；
    - 中风险字段（location/occupation）冲突时需要“重复一次”才覆盖；
    - 全程记录 UserProfileUpdateDB，便于审计与回滚。
    """
    runtime_cfg = _get_auto_profile_runtime_config()
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        return {"applied": 0, "pending": 0}

    extractor = "rule"
    signals = _extract_profile_signals_from_text(text)
    if not signals:
        extractor = "small_llm"
        signals = _extract_profile_signals_with_small_llm(text)
    if not signals:
        return {"applied": 0, "pending": 0}

    applied_count = 0
    pending_count = 0
    applied_fields: Dict[str, Any] = {}
    cooldown_cutoff = datetime.utcnow() - timedelta(hours=runtime_cfg["cooldown_hours"])
    confirm_cutoff = datetime.utcnow() - timedelta(days=runtime_cfg["confirm_window_days"])
    pending_expire_before = datetime.utcnow() - timedelta(days=runtime_cfg["pending_ttl_days"])

    # interests：低风险，直接并集更新（有冷却）
    if isinstance(signals.get("interests"), list) and signals["interests"]:
        latest_interest_update = db.query(UserProfileUpdateDB).filter(
            UserProfileUpdateDB.user_id == user_id,
            UserProfileUpdateDB.update_type == "chat_auto_interests",
            UserProfileUpdateDB.source == PROFILE_AUTO_UPDATE_SOURCE,
            UserProfileUpdateDB.applied.is_(True),
            UserProfileUpdateDB.created_at >= cooldown_cutoff,
        ).first()
        if not latest_interest_update:
            old_raw = user.interests or "[]"
            merged_raw = _merge_interests(old_raw, signals["interests"])
            if merged_raw != old_raw:
                user.interests = merged_raw
                applied_count += 1
                applied_fields["interests"] = json.loads(merged_raw)
                _record_profile_update(
                    db, user_id, "chat_auto_interests",
                    old_raw, merged_raw, 0.92, True
                )

    # location / occupation：中风险，冲突需二次确认
    for field in ("location", "occupation"):
        if not signals.get(field):
            continue
        new_val = str(signals[field]).strip()
        old_val = (getattr(user, field, "") or "").strip()
        update_type = f"chat_auto_{field}"

        if old_val == new_val:
            continue

        # 当前为空：直接填充
        if not old_val:
            setattr(user, field, new_val)
            applied_count += 1
            applied_fields[field] = new_val
            _record_profile_update(db, user_id, update_type, old_val, new_val, 0.9, True)
            continue

        # 冲突场景：证据分数累计达到阈值才覆盖（可配置）
        _cleanup_expired_pending_updates(db, user_id, update_type, pending_expire_before)
        existing_score = _get_pending_evidence_score(db, user_id, update_type, new_val, confirm_cutoff)
        current_score = 0.72 if extractor == "rule" else 0.62
        threshold = float(runtime_cfg["threshold"].get(field, 1.4))
        total_score = existing_score + current_score

        if total_score >= threshold:
            setattr(user, field, new_val)
            applied_count += 1
            applied_fields[field] = new_val
            _record_profile_update(db, user_id, update_type, old_val, new_val, min(0.95, total_score / 2), True)
        else:
            pending_count += 1
            _record_profile_update(db, user_id, update_type, old_val, new_val, current_score, False)

    if applied_count > 0 or pending_count > 0:
        if applied_fields:
            _sync_vector_dimensions_for_auto_updates(user, applied_fields)
        user.profile_updated_at = datetime.utcnow()
        db.commit()

    return {"applied": applied_count, "pending": pending_count}


def _rollback_latest_auto_profile_update(db: Session, user_id: str, field: str) -> Dict[str, Any]:
    allowed_fields = {"location", "occupation", "interests"}
    if field not in allowed_fields:
        raise ValueError(f"field must be one of: {sorted(allowed_fields)}")

    update_type = f"chat_auto_{field}"
    latest = db.query(UserProfileUpdateDB).filter(
        UserProfileUpdateDB.user_id == user_id,
        UserProfileUpdateDB.update_type == update_type,
        UserProfileUpdateDB.source == PROFILE_AUTO_UPDATE_SOURCE,
        UserProfileUpdateDB.applied.is_(True),
    ).order_by(UserProfileUpdateDB.created_at.desc()).first()
    if not latest:
        return {"rolled_back": False, "reason": "no_applied_update"}

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        return {"rolled_back": False, "reason": "user_not_found"}

    before_val = getattr(user, field, "") or ""
    restored_val = latest.old_value or ""
    setattr(user, field, restored_val)
    user.profile_updated_at = datetime.utcnow()

    db.add(UserProfileUpdateDB(
        id=str(uuid.uuid4()),
        user_id=user_id,
        update_type=f"chat_auto_rollback_{field}",
        old_value=str(before_val),
        new_value=str(restored_val),
        source=PROFILE_AUTO_ROLLBACK_SOURCE,
        confidence=1.0,
        applied=True,
    ))
    db.commit()
    return {"rolled_back": True, "field": field, "restored_value": restored_val}


# ============= Pydantic 模型 =============

class MessageSendRequest(BaseModel):
    """发送消息请求

    安全验证规则：
    - receiver_id: 必填，UUID 格式验证
    - content: 必填，长度 1-10000 字符，禁止纯空格
    - message_type: 必须是有效类型 (text/image/emoji/voice)
    """
    receiver_id: str = Field(..., min_length=36, max_length=36, description="接收者 ID（UUID格式）")
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    message_type: str = Field(default="text", description="消息类型：text/image/emoji/voice")
    message_metadata: Optional[dict] = Field(default=None, description="元数据")

    @field_validator('receiver_id')
    @classmethod
    def validate_receiver_id(cls, v: str) -> str:
        """验证 receiver_id 为 UUID 格式"""
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, v.lower()):
            raise ValueError('receiver_id must be a valid UUID format')
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证消息内容：禁止纯空格"""
        if v is None or v.strip() == '':
            raise ValueError('content cannot be empty or whitespace only')
        return v

    @field_validator('message_type')
    @classmethod
    def validate_message_type(cls, v: str) -> str:
        """验证消息类型"""
        valid_types = ['text', 'image', 'emoji', 'voice']
        if v not in valid_types:
            raise ValueError(f'message_type must be one of: {valid_types}')
        return v


class MessageResponse(BaseModel):
    """消息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: str
    status: str
    is_read: bool
    created_at: str
    metadata: Optional[dict] = None


class ConversationResponse(BaseModel):
    """会话响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id_1: str
    user_id_2: str
    status: str
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    partner_avatar_url: Optional[str] = None
    unread_count: int = 0
    created_at: str


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    partner_id: Optional[str] = Field(default=None, description="对方用户 ID（新格式）")
    user_id_1: Optional[str] = Field(default=None, description="用户 ID 1（兼容旧格式）")
    user_id_2: Optional[str] = Field(default=None, description="用户 ID 2（兼容旧格式）")

    def resolve_partner_id(self, current_user_id: str) -> Optional[str]:
        """
        统一解析目标对话用户：
        - 新格式：直接使用 partner_id
        - 旧格式：根据 user_id_1 / user_id_2 和当前用户推导对方 ID
        """
        if self.partner_id:
            return self.partner_id

        if self.user_id_1 and self.user_id_2:
            if current_user_id == self.user_id_1:
                return self.user_id_2
            if current_user_id == self.user_id_2:
                return self.user_id_1

        return None


class AutoProfileRollbackRequest(BaseModel):
    """无感画像自动更新回滚请求"""
    field: str = Field(..., description="可选字段: location/occupation/interests")

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        valid = {"location", "occupation", "interests"}
        vv = (v or "").strip()
        if vv not in valid:
            raise ValueError(f"field must be one of: {sorted(valid)}")
        return vv


# ============= WebSocket 连接管理 =============

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> WebSocket 连接
        self.active_connections: dict[str, WebSocket] = {}
        # user_id -> set of 连接 (支持多设备)
        self.user_connections: dict[str, set] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开 WebSocket 连接"""
        # 仅在当前记录的活动连接就是该 websocket 时才移除，避免多连接场景误删
        if user_id in self.active_connections and self.active_connections[user_id] is websocket:
            del self.active_connections[user_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """向特定用户发送消息"""
        logger.info(f"🔗 [WS:SEND] Attempting to send message to user={user_id}, online_users={list(self.user_connections.keys())}")
        if user_id in self.user_connections:
            # 复制快照迭代，避免发送失败时删除连接导致 "Set changed size during iteration"
            connections_snapshot = list(self.user_connections[user_id])
            for websocket in connections_snapshot:
                try:
                    logger.info(f"🔗 [WS:SEND] Sending to user={user_id}: {message.get('type', 'unknown')}")
                    await websocket.send_json(message)
                    logger.info(f"🔗 [WS:SEND] Successfully sent to user={user_id}")
                except Exception as e:
                    # 连接已断开，记录日志并移除断开的连接
                    logger.warning(f"🔗 [WS:SEND] WebSocket send failed for user {user_id}: {e}")
                    try:
                        await websocket.close()
                    except Exception:
                        pass
                    # 统一走 disconnect，确保 active_connections / user_connections 一致
                    self.disconnect(websocket, user_id)
        else:
            logger.warning(f"🔗 [WS:SEND] User {user_id} not in online connections")

    async def broadcast(self, message: dict):
        """广播消息 (给所有在线用户)"""
        disconnected = []
        for websocket in self.active_connections.values():
            try:
                await websocket.send_json(message)
            except Exception as e:
                # 连接已断开，记录并稍后清理
                logger.debug(f"Broadcast failed: {e}")
                disconnected.append(websocket)

        # 清理断开的连接
        for ws in disconnected:
            for user_id, connections in list(self.user_connections.items()):
                if ws in connections:
                    connections.remove(ws)


# 创建连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(default=None)
):
    """
    WebSocket 聊天连接

    客户端连接示例:
    ws://localhost:8001/api/chat/ws/{user_id}?token={jwt_token}

    认证说明:
    - 生产环境：必须提供有效的 JWT token
    - 开发环境：允许匿名用户连接
    """
    # 验证 JWT token（如果提供）
    # 注：当前简化处理，生产环境应严格验证
    # token = query_params.get("token")
    # if token:
    #     user_id_from_token = decode_access_token(token)
    #     if user_id_from_token != user_id:
    #         await websocket.close(code=4001, reason="Token mismatch")
    #         return

    logger.info(f"🔗 [WS:CONNECT] WebSocket connection requested for user={user_id}")
    await manager.connect(websocket, user_id)
    logger.info(f"🔗 [WS:CONNECT] WebSocket accepted for user={user_id}, active_connections={list(manager.active_connections.keys())}")

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 消息类型处理
            message_type = data.get("type", "message")

            if message_type == "message":
                # 聊天消息
                await handle_chat_message(websocket, data, user_id)
            elif message_type == "read_receipt":
                # 已读回执
                await handle_read_receipt(websocket, data, user_id)
            elif message_type == "typing":
                # 正在输入
                await handle_typing_indicator(websocket, data, user_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        # 通知对方用户已离线
        await manager.send_personal_message(
            {"type": "user_offline", "user_id": user_id},
            user_id
        )


async def handle_chat_message(websocket: WebSocket, data: dict, sender_id: str):
    """处理聊天消息"""
    receiver_id = data.get("receiver_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    metadata = data.get("metadata")

    if not receiver_id or not content:
        await websocket.send_json({
            "type": "error",
            "message": "缺少必要参数"
        })
        return

    # 这里可以将消息存储到数据库
    # 实际应在完整的依赖注入环境中处理
    # 为简化，这里只做消息转发

    # 转发给接收者
    await manager.send_personal_message({
        "type": "new_message",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "message_type": message_type,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat()
    }, receiver_id)

    # 确认发送给发送者
    await websocket.send_json({
        "type": "message_sent",
        "receiver_id": receiver_id,
        "status": "sent"
    })


async def handle_read_receipt(websocket: WebSocket, data: dict, user_id: str):
    """处理已读回执"""
    sender_id = data.get("sender_id")
    message_id = data.get("message_id")

    if sender_id:
        await manager.send_personal_message({
            "type": "read_receipt",
            "message_id": message_id,
            "user_id": user_id
        }, sender_id)


async def handle_typing_indicator(websocket: WebSocket, data: dict, user_id: str):
    """处理正在输入指示"""
    target_user_id = data.get("target_user_id")

    if target_user_id:
        await manager.send_personal_message({
            "type": "typing",
            "user_id": user_id
        }, target_user_id)


# ============= REST API 端点 =============

@router.post("/send", summary="发送消息")
async def send_message(
    request: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    发送消息

    - **receiver_id**: 接收者 ID
    - **content**: 消息内容
    - **message_type**: 消息类型 (text/image/emoji/voice)
    - **metadata**: 元数据
    """
    # 生成/获取 trace_id
    trace_id = get_trace_id()
    logger.info(f"📡 [CHAT:SEND] START trace_id={trace_id}")

    # 开发环境匿名用户处理
    user_id = current_user.get("user_id", "user-anonymous-dev")
    is_anonymous = current_user.get("is_anonymous", True)

    logger.info(f"📡 [CHAT:SEND] user={user_id}, receiver={request.receiver_id}, anonymous={is_anonymous}, trace_id={trace_id}")

    service = ChatService(db)

    try:
        message = service.send_message(
            sender_id=user_id,
            receiver_id=request.receiver_id,
            content=request.content,
            message_type=request.message_type,
            message_metadata=request.message_metadata
        )
        logger.info(f"📡 [CHAT:SEND] DB saved message_id={message.id}, conversation_id={message.conversation_id}")

        # 如果接收者在线，通过 WebSocket 推送
        if request.receiver_id in manager.user_connections:
            await manager.send_personal_message({
                "type": "new_message",
                "id": message.id,
                "sender_id": user_id,
                "content": message.content,
                "message_type": message.message_type,
                "timestamp": message.created_at.isoformat()
            }, request.receiver_id)
            logger.info(f"📡 [CHAT:SEND] Pushed to WebSocket for receiver {request.receiver_id}")

        # 开发环境：触发模拟 Agent 回复
        if settings.environment == "development":
            logger.info(f"📡 [CHAT:SEND] DevMode: Scheduling agent reply for receiver {request.receiver_id}")
            # 后台异步触发模拟回复（必须使用独立 DB 会话：请求结束后 Depends(get_db) 会关闭原 session）
            asyncio.create_task(
                simulate_agent_reply(
                    conversation_id=message.conversation_id,
                    message_content=request.content,
                    sender_id=user_id,
                    receiver_id=request.receiver_id
                )
            )

        logger.info(f"📡 [CHAT:SEND] SUCCESS trace_id={trace_id}, message_id={message.id}")

        # AI Native: 触发消息发送事件，更新活跃状态
        try:
            from agent.autonomous.event_listener import emit_event
            emit_event(
                event_type="message_sent",
                event_data={
                    "sender_id": user_id,
                    "receiver_id": request.receiver_id,
                    "match_id": message.conversation_id,
                    "message_id": message.id,
                },
                event_source=user_id
            )
            logger.info(f"📡 [CHAT:SEND] Event 'message_sent' emitted for conversation {message.conversation_id}")
        except Exception as e:
            logger.warning(f"Failed to emit message_sent event: {e}")

        # 无感画像更新（规则版，0 token 成本；失败不影响主链路）
        try:
            profile_update_result = _safe_auto_update_profile_from_chat(db, user_id, request.content)
            if profile_update_result.get("applied", 0) or profile_update_result.get("pending", 0):
                logger.info(
                    f"📡 [CHAT:SEND] Profile auto-update result user={user_id} "
                    f"applied={profile_update_result.get('applied', 0)} "
                    f"pending={profile_update_result.get('pending', 0)}"
                )
        except Exception as profile_err:
            logger.warning(f"📡 [CHAT:SEND] Profile auto-update skipped: {profile_err}")

        # 手动构建响应（避免 Pydantic 验证问题）
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "message_type": message.message_type,
            "content": message.content,
            "status": message.status,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat(),
            "metadata": message.message_metadata
        }

    except Exception as e:
        logger.error(f"📡 [CHAT:SEND] FAILED trace_id={trace_id} error={str(e)}", exc_info=True)
        raise


@router.post("/profile/auto-update/rollback", summary="回滚无感画像自动更新")
async def rollback_auto_profile_update(
    request: AutoProfileRollbackRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional),
):
    """
    回滚当前用户最近一次自动画像更新。
    """
    user_id = current_user.get("user_id", "user-anonymous-dev")
    try:
        result = _rollback_latest_auto_profile_update(db, user_id, request.field)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        logger.error(f"[chat_auto_profile] rollback failed user={user_id}, err={e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="rollback failed")


async def simulate_agent_reply(
    conversation_id: str,
    message_content: str,
    sender_id: str,
    receiver_id: str
):
    """
    模拟 Agent 回复（后台任务）

    Args:
        conversation_id: 会话 ID
        message_content: 收到的消息内容
        sender_id: 发送者 ID
        receiver_id: 接收者 ID（模拟用户）
    """
    # 获取 trace_id 用于链路追踪
    trace_id = get_trace_id()
    logger.info(f"🤖 [AGENT:REPLY] START trace_id={trace_id} conv={conversation_id}")

    try:
        # 检查是否是给自己发消息
        if sender_id == receiver_id:
            logger.info(f"🤖 [AGENT:REPLY] Skipping - sender and receiver are the same user ({sender_id})")
            return

        logger.info(f"🤖 [AGENT:REPLY] Task started - conv={conversation_id}, sender={sender_id}, receiver={receiver_id}")

        # 独立会话：禁止复用 HTTP 请求的 db（请求结束即 close，后台任务会踩已关闭 Session）
        with db_session() as db:
            # 从数据库读取接收者的真实画像，创建模拟 Agent
            from agent.user_simulation_agent import create_agent_from_db
            agent = create_agent_from_db(db, receiver_id)
            logger.info(f"🤖 [AGENT:REPLY] create_agent_from_db result: {agent is not None}")

            # 如果数据库中找不到用户，使用默认 Agent
            if agent is None:
                logger.warning(f"🤖 [AGENT:REPLY] User {receiver_id} not found in DB, using default agent")
                from agent.user_simulation_agent import get_agent_for_user
                agent = get_agent_for_user(receiver_id)
                logger.info(f"🤖 [AGENT:REPLY] Using default agent for user {receiver_id}")

            logger.info(f"🤖 [AGENT:REPLY] Agent created successfully, name={agent.name}, reply_probability={agent.reply_config['reply_probability']}")

            # 模拟收到消息后的反应
            reply_info = agent.simulate_receive_message(
                conversation_id=conversation_id,
                message_content=message_content,
                sender_id=sender_id,
                sender_name="用户"
            )

            logger.info(f"🤖 [AGENT:REPLY] simulate_receive_message result: {reply_info is not None}")

            if reply_info:
                logger.info(f"🤖 [AGENT:REPLY] Will reply after {reply_info['delay_seconds']}s with content: {reply_info['content'][:30]}...")
                # 等待延迟时间（保持会话在 with 内，避免释放后再用）
                await asyncio.sleep(reply_info["delay_seconds"])

                # 创建回复消息
                service = ChatService(db)
                reply_message = service.send_message(
                    sender_id=receiver_id,
                    receiver_id=sender_id,
                    content=reply_info["content"],
                    message_type=reply_info.get("message_type", "text")
                )
                logger.info(f"🤖 [AGENT:REPLY] Message sent to DB, id={reply_message.id}")

                # 如果发送者在线，推送回复
                if sender_id in manager.user_connections:
                    await manager.send_personal_message({
                        "type": "new_message",
                        "id": reply_message.id,
                        "sender_id": receiver_id,
                        "content": reply_message.content,
                        "message_type": reply_message.message_type,
                        "timestamp": reply_message.created_at.isoformat()
                    }, sender_id)
                    logger.info(f"🤖 [AGENT:REPLY] Pushed to WebSocket for sender {sender_id}")
                else:
                    logger.info(f"🤖 [AGENT:REPLY] Sender {sender_id} not in online connections, message saved to DB only")

                logger.info(f"🤖 [AGENT:REPLY] Sent reply to {sender_id}: {reply_info['content'][:30]}...")
            else:
                logger.info(f"🤖 [AGENT:REPLY] Decided not to reply to {sender_id}")

        logger.info(f"🤖 [AGENT:REPLY] SUCCESS trace_id={trace_id}")

    except Exception as e:
        logger.error(f"🤖 [AGENT:REPLY] FAILED trace_id={trace_id} error={str(e)}", exc_info=True)


@router.get("/conversations", response_model=List[ConversationResponse], summary="获取会话列表")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """获取当前用户的聊天会话列表"""
    # 开发环境匿名用户处理
    user_id = current_user.get("user_id", "user-anonymous-dev")
    is_anonymous = current_user.get("is_anonymous", True)

    service = ChatService(db)
    conversations = service.get_user_conversations(user_id)

    # 预加载会话对端用户信息，避免前端再自行猜测名字
    partner_ids = set()
    for conv in conversations:
        partner_id = conv.user_id_2 if conv.user_id_1 == user_id else conv.user_id_1
        if partner_id:
            partner_ids.add(partner_id)

    partner_map: Dict[str, Dict[str, Optional[str]]] = {}
    if partner_ids:
        partners = db.query(UserDB).filter(UserDB.id.in_(list(partner_ids))).all()
        for p in partners:
            raw_name = (p.name or p.username or "").strip()
            is_uuid_like = bool(re.match(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", raw_name.lower())) if raw_name else False
            safe_name = raw_name if raw_name and raw_name != "user-anonymous-dev" and not is_uuid_like else "TA"
            partner_map[p.id] = {
                "name": safe_name,
                "avatar_url": p.avatar_url
            }

    # 转换为响应格式
    result = []
    for conv in conversations:
        # 计算当前用户的未读数
        if conv.user_id_1 == user_id:
            unread = conv.unread_count_user1
        else:
            unread = conv.unread_count_user2

        partner_id = conv.user_id_2 if conv.user_id_1 == user_id else conv.user_id_1
        partner_info = partner_map.get(partner_id, {})
        partner_name = partner_info.get("name") or "TA"
        partner_avatar_url = partner_info.get("avatar_url")

        result.append({
            "id": conv.id,
            "user_id_1": conv.user_id_1,
            "user_id_2": conv.user_id_2,
            "status": conv.status,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "last_message_preview": conv.last_message_preview,
            "partner_id": partner_id,
            "partner_name": partner_name,
            "partner_avatar_url": partner_avatar_url,
            "unread_count": unread,
            "created_at": conv.created_at.isoformat()
        })

    return result


@router.get("/history/{other_user_id}", summary="获取聊天历史")
async def get_chat_history(
    other_user_id: str,
    limit: int = Query(default=50, description="返回消息数量"),
    offset: int = Query(default=0, description="偏移量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """获取与指定用户的聊天历史记录"""
    user_id = current_user.get("user_id", "user-anonymous-dev")

    service = ChatService(db)
    messages = service.get_conversation_messages(
        user_id_1=user_id,
        user_id_2=other_user_id,
        limit=limit,
        offset=offset
    )

    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "message_type": msg.message_type,
            "content": msg.content,
            "status": msg.status,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.message_metadata if msg.message_metadata else None
        }
        for msg in messages
    ]


@router.post("/read/message/{message_id}", summary="标记消息已读")
async def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """标记指定消息为已读"""
    service = ChatService(db)
    success = service.mark_message_read(message_id, current_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标记失败")

    return {"message": "已标记为已读"}


@router.post("/read/conversation", summary="标记会话已读")
async def mark_conversation_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
    ):
    """标记整个会话为已读"""
    service = ChatService(db)
    partner_id = request.resolve_partner_id(current_user_id)
    if not partner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="请求参数缺失：请提供 partner_id，或提供 user_id_1 与 user_id_2 且包含当前用户"
        )

    success = service.mark_conversation_read(current_user_id, partner_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标记失败")

    return {"message": "会话已标记为已读"}


@router.post("/recall/{message_id}", summary="撤回消息")
async def recall_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """撤回已发送的消息（2 分钟内）"""
    service = ChatService(db)
    success = service.recall_message(message_id, current_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="撤回失败")

    return {"message": "消息已撤回"}


@router.delete("/message/{message_id}", summary="删除消息")
async def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """删除消息"""
    service = ChatService(db)
    success = service.delete_message(message_id, current_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="删除失败")

    return {"message": "消息已删除"}


@router.post("/archive/{other_user_id}", summary="归档会话")
async def archive_conversation(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """归档聊天会话"""
    service = ChatService(db)
    success = service.archive_conversation(current_user_id, other_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="归档失败")

    return {"message": "会话已归档"}


@router.post("/block/{other_user_id}", summary="屏蔽用户")
async def block_user(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """屏蔽指定用户"""
    service = ChatService(db)
    success = service.block_user(current_user_id, other_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="屏蔽失败")

    return {"message": "用户已屏蔽"}


@router.get("/unread/count", summary="获取未读消息数")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """获取当前用户的未读消息总数"""
    service = ChatService(db)
    count = service.get_unread_count(current_user_id)
    return {"unread_count": count}


@router.get("/search", summary="搜索消息")
async def search_messages(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=20, description="返回数量"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """搜索包含关键词的消息"""
    service = ChatService(db)
    messages = service.search_messages(current_user_id, keyword, limit)

    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]


@router.post("/simulate-reply", summary="模拟回复 (开发环境)")
async def simulate_reply(
    conversation_id: str = Query(..., description="会话 ID"),
    user_message: str = Query(..., description="用户消息"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    模拟对方回复（开发环境使用）

    AI 根据用户消息生成模拟回复，用于演示。
    """
    user_id = current_user.get("user_id", "user-anonymous-dev")
    logger.info(f"SimulateReply: conv={conversation_id}, msg={user_message[:30]}..., user={user_id}")

    try:
        # 简单的关键词回复逻辑
        user_message_lower = user_message.lower()

        if any(word in user_message_lower for word in ["你好", "hi", "hello", "嗨", "哈喽"]):
            replies = [
                "嗨！很高兴见到你~ 👋",
                "你好呀！今天过得怎么样？",
                "哈喽！看到你的消息很开心~"
            ]
        elif any(word in user_message_lower for word in ["喜欢", "爱好", "兴趣"]):
            replies = [
                "真的吗？我也挺感兴趣的！有机会可以一起呀~",
                "听起来很有趣！你一般什么时候去做这个？",
                "哇，这个我也喜欢！我们可以分享下经验~"
            ]
        elif any(word in user_message_lower for word in ["旅行", "旅游", "去过"]):
            replies = [
                "好棒！我也想去那里！有什么推荐的地方吗？",
                "旅行真的能开阔眼界呢~ 你去过最难忘的地方是哪里？",
                "听你这么说我也心动了！下次可以一起去呀~"
            ]
        elif any(word in user_message_lower for word in ["吃", "美食", "饭"]):
            replies = [
                "说到吃的我就来精神了！你喜欢吃什么口味的？",
                "我知道几家不错的店，有空可以一起去尝尝~",
                "美食真的能让人开心呢！你最爱的菜是什么？"
            ]
        elif any(word in user_message_lower for word in ["工作", "忙", "累"]):
            replies = [
                "辛苦啦！要注意休息哦~",
                "工作再忙也要照顾好自己，按时吃饭~",
                "抱抱~ 下班后好好放松一下吧"
            ]
        elif "?" in user_message or "吗" in user_message:
            replies = [
                "这个问题问得好！我觉得...",
                "嗯...让我想想，应该是不错的~",
                "我也在想这个问题呢，你觉得呢？"
            ]
        else:
            # 通用回复
            replies = [
                "嗯嗯，我理解你的感受~",
                "真的吗？那太好了！",
                "和你聊天真开心~ 想多了解你一些呢",
                "你说得对！我也这么觉得~",
                "好有趣！继续说下去我想听~"
            ]

        # 随机选择一个回复
        reply_content = random.choice(replies)

        # 获取会话信息
        chat_service = ChatService(db)
        conversation = db.query(ChatConversationDB).filter(
            ChatConversationDB.id == conversation_id
        ).first()

        if not conversation:
            # 创建新会话
            partner_id = conversation_id.split('_')[-1] if '_' in conversation_id else user_id
            conversation = chat_service.get_or_create_conversation(user_id, partner_id)

        # 确定对方用户 ID
        partner_id = conversation.user_id_2 if conversation.user_id_1 == user_id else conversation.user_id_1

        # 创建模拟回复消息
        message = chat_service.send_message(
            sender_id=partner_id,
            receiver_id=user_id,
            content=reply_content,
            message_type=ChatService.TYPE_TEXT
        )

        logger.info(f"Simulated reply: {reply_content}")

        return {
            "success": True,
            "message_id": message.id,
            "content": reply_content,
            "created_at": message.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"SimulateReply failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 悬浮球快速对话 API（合并自 quick_chat）==============

class QuickChatRequest(BaseModel):
    """快速对话请求"""
    question: str
    partnerId: str
    partnerName: str = "TA"
    recentMessages: List[Dict] = []


class QuickChatResponse(BaseModel):
    """快速对话响应"""
    answer: str
    suggestions: List[str] = []
    analysis: Dict = {}


class SuggestReplyRequest(BaseModel):
    """回复建议请求"""
    partnerId: str
    lastMessage: Dict
    recentMessages: List[Dict] = []
    relationshipStage: str = "初识"


class SuggestionItem(BaseModel):
    """回复建议项"""
    style: str
    content: str


class SuggestReplyResponse(BaseModel):
    """回复建议响应"""
    suggestions: List[SuggestionItem]


class FeedbackRequest(BaseModel):
    """反馈记录请求"""
    partnerId: str
    suggestionId: str
    feedbackType: str  # adopted/ignored/modified
    suggestionContent: str
    suggestionStyle: str
    userActualReply: Optional[str] = None


@router.get("/tags", summary="获取智能快捷标签")
async def get_quick_tags(
    current_user: dict = Depends(get_current_user_optional),
):
    """
    获取智能快捷标签

    根据用户画像、状态和场景，智能生成个性化的快捷对话标签
    让标签真正理解用户的意图和需求
    """
    # 从 dict 中提取 user_id
    current_user_id = current_user.get("user_id") if current_user else None

    # 如果没有用户，返回基础标签
    if not current_user_id:
        return {"tags": [
            {"label": "介绍一下", "trigger": "介绍一下你自己"},
            {"label": "开始匹配", "trigger": "帮我找对象"},
        ]}

    try:
        # 获取用户画像和状态
        user_profile = await _get_user_profile_for_tags(current_user_id)
        user_state = await _get_user_state_for_tags(current_user_id)

        # 基于用户状态生成标签（简化逻辑，不依赖 LLM）
        tags = _generate_tags_from_state(user_profile, user_state)

        logger.info(f"[QuickTags] Generated {len(tags)} tags for user {current_user_id}")
        return {"tags": tags}

    except Exception as e:
        logger.error(f"[QuickTags] Failed: {e}")
        return {"tags": _get_fallback_tags()}


def _generate_tags_from_state(profile: Dict, state: Dict) -> List[Dict]:
    """基于用户状态生成标签（简化版，不依赖 LLM）"""
    tags = []

    # 根据匹配状态
    if state.get("has_active_match"):
        tags.append({"label": "继续聊天", "trigger": "看看今天的聊天"})
        tags.append({"label": "关系分析", "trigger": "分析我和TA的关系"})
    else:
        tags.append({"label": "今日推荐", "trigger": "看看今天有什么推荐"})
        tags.append({"label": "找对象", "trigger": "帮我找对象"})

    # 根据资料完成度
    if state.get("profile_completion", 0) < 50:
        tags.append({"label": "完善资料", "trigger": "帮我完善资料"})

    # 根据关系目标
    goal = profile.get("relationship_goal", "")
    if goal == "serious" or goal == "marriage":
        tags.append({"label": "认真恋爱", "trigger": "我想找认真恋爱的对象"})
    elif goal == "dating":
        tags.append({"label": "轻松交友", "trigger": "我想轻松交友"})

    # 确保至少有 2 个标签
    if len(tags) < 2:
        tags.extend(_get_fallback_tags()[:2])

    return tags[:5]  # 最多 5 个标签



async def _get_user_profile_for_tags(user_id: str) -> Dict:
    """获取用户画像（用于生成标签）"""
    try:
        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                self_profile_data = _safe_parse_json_object(getattr(user, "self_profile_json", None))
                desire_profile_data = _safe_parse_json_object(getattr(user, "desire_profile_json", None))
                return {
                    "relationship_goal": user.relationship_goal or "未设置",
                    "personality": user.personality or "未设置",
                    "interests": user.interests or "未设置",
                    "age": user.age,
                    "location": user.location,
                    "vector_dimensions": {
                        "self": self_profile_data.get("vector_dimensions", {}),
                        "desire": desire_profile_data.get("vector_dimensions", {}),
                    },
                }
    except Exception as e:
        logger.warning(f"[QuickTags] Failed to get profile: {e}")
    return {}


async def _get_user_state_for_tags(user_id: str) -> Dict:
    """获取用户状态（用于生成标签）"""
    try:
        with db_session() as db:
            # 检查匹配状态
            from db.models import MatchHistoryDB, ChatConversationDB

            has_active_match = db.query(MatchHistoryDB).filter(
                (MatchHistoryDB.user_id_1 == user_id) | (MatchHistoryDB.user_id_2 == user_id),
                MatchHistoryDB.status == 'accepted'
            ).count() > 0

            # 检查消息状态
            conversations = db.query(ChatConversationDB).filter(
                (ChatConversationDB.user_id_1 == user_id) | (ChatConversationDB.user_id_2 == user_id)
            ).all()

            has_unread_messages = any(
                conv.unread_count_user1 > 0 if conv.user_id_1 == user_id else conv.unread_count_user2 > 0
                for conv in conversations
            ) if conversations else False

            # 计算资料完成度
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            profile_fields = ['relationship_goal', 'personality', 'interests', 'bio', 'avatar_url']
            filled_fields = sum(1 for f in profile_fields if getattr(user, f, None))
            profile_completion = int(filled_fields / len(profile_fields) * 100)

            return {
                "has_active_match": has_active_match,
                "has_unread_messages": has_unread_messages,
                "activity_level": "active" if has_active_match else "new" if profile_completion < 50 else "normal",
                "recent_behavior": "有匹配" if has_active_match else "有资料" if profile_completion > 50 else "刚注册",
                "profile_completion": profile_completion,
            }
    except Exception as e:
        logger.warning(f"[QuickTags] Failed to get state: {e}")
    return {}


def _get_fallback_tags() -> List[Dict]:
    """降级标签"""
    return [
        {"label": "今日推荐", "trigger": "看看今天有什么推荐"},
        {"label": "找对象", "trigger": "帮我找对象"},
    ]


@router.post("/quick-ask", response_model=QuickChatResponse, summary="悬浮球快速对话")
async def quick_chat(
    request: QuickChatRequest,
    current_user_id: str = Depends(get_current_user),
):
    """
    悬浮球快速对话

    用户可以向 Her 提问关于匹配对象的问题，例如:
    - "她为什么不回我消息？"
    - "我该怎么回复她？"
    - "她对我有意思吗？"

    Her 会分析聊天上下文给出建议
    """
    try:
        from services.quick_chat_service import QuickChatService
        service = QuickChatService()
        result = service.get_ai_advice(
            current_user_id=current_user_id,
            partner_id=request.partnerId,
            question=request.question,
            recent_messages=request.recentMessages,
        )

        return QuickChatResponse(
            answer=result.get("answer", ""),
            suggestions=result.get("suggestions", []),
            analysis=result.get("analysis", {}),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI 思考失败：{str(e)}")


@router.post("/suggest-reply", response_model=SuggestReplyResponse, summary="生成回复建议")
async def suggest_reply(
    request: SuggestReplyRequest,
    current_user_id: str = Depends(get_current_user),
):
    """
    生成回复建议

    当用户收到消息但不知道如何回复时，可以调用此接口
    AI 会生成 3 种不同风格的回复建议
    """
    try:
        from services.quick_chat_service import QuickChatService
        service = QuickChatService()
        result = service.suggest_reply(
            current_user_id=current_user_id,
            partner_id=request.partnerId,
            last_message=request.lastMessage,
            recent_messages=request.recentMessages,
            relationship_stage=request.relationshipStage,
        )

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail="生成建议失败")

        suggestions = [
            SuggestionItem(**s) for s in result.get("suggestions", [])
        ]

        return SuggestReplyResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成建议失败：{str(e)}")


@router.post("/suggestion-feedback", summary="记录建议反馈")
async def record_feedback(
    request: FeedbackRequest,
    current_user_id: str = Depends(get_current_user),
):
    """
    记录用户对 AI 建议的反馈

    用于追踪 AI 建议的采纳情况和效果，持续优化 AI 策略
    """
    try:
        from services.quick_chat_service import QuickChatService
        service = QuickChatService()
        feedback_id = service.record_suggestion_feedback(
            current_user_id=current_user_id,
            partner_id=request.partnerId,
            suggestion_id=request.suggestionId,
            feedback_type=request.feedbackType,
            suggestion_content=request.suggestionContent,
            suggestion_style=request.suggestionStyle,
            user_actual_reply=request.userActualReply,
        )

        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录反馈失败：{str(e)}")


@router.get("/quick-tags", summary="获取动态快捷标签")
async def get_quick_tags(
    current_user_id: str = Depends(get_current_user),
):
    """
    获取动态快捷标签

    AI 根据用户状态动态生成最相关的 1-3 个快捷标签。
    """
    try:
        from services.quick_tag_service import get_quick_tag_service
        service = get_quick_tag_service()
        tags = service.get_quick_tags(current_user_id)

        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签失败：{str(e)}")


# ============= 对话分析 API（合并自 conversations）==============

@router.post("/analyze-message", summary="分析单条消息")
async def analyze_message(
    message: str,
    sender_id: str,
    receiver_id: str
):
    """
    分析单条消息

    Args:
        message: 消息内容
        sender_id: 发送者 ID
        receiver_id: 接收者 ID
    """
    from services.conversation_analysis_service import conversation_analyzer
    result = conversation_analyzer.analyze_message(
        message=message,
        sender_id=sender_id,
        receiver_id=receiver_id
    )

    return {"analysis": result}


@router.post("/save-with-analysis", summary="保存对话记录（带分析）")
async def save_conversation_with_analysis(
    sender_id: str,
    receiver_id: str,
    message: str,
    message_type: str = "text"
):
    """
    保存对话记录（带分析）

    Args:
        sender_id: 发送者 ID
        receiver_id: 接收者 ID
        message: 消息内容
        message_type: 消息类型
    """
    from services.conversation_analysis_service import conversation_analyzer
    conversation_id = conversation_analyzer.save_conversation(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message=message,
        message_type=message_type
    )

    return {
        "conversation_id": conversation_id,
        "status": "saved"
    }


@router.get("/topic-profile/{user_id}", summary="获取用户话题画像")
async def get_topic_profile(
    user_id: str,
    days: int = 30
):
    """
    获取用户的话题画像

    Args:
        user_id: 用户 ID
        days: 分析天数
    """
    from services.conversation_analysis_service import conversation_analyzer
    profile = conversation_analyzer.get_user_topic_profile(user_id, days=days)

    return {
        "user_id": user_id,
        "period_days": days,
        "topic_profile": profile
    }


@router.get("/profile-suggestions/{user_id}", summary="获取画像更新建议")
async def get_profile_update_suggestions(
    user_id: str,
    days: int = 30
):
    """
    获取画像更新建议（基于对话分析）

    Args:
        user_id: 用户 ID
        days: 分析天数
    """
    from services.conversation_analysis_service import conversation_analyzer
    suggestions = conversation_analyzer.generate_profile_update_suggestions(
        user_id=user_id,
        days=days
    )

    return {
        "user_id": user_id,
        "suggestions": suggestions
    }
