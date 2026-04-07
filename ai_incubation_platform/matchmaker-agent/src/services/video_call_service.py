"""
P6 视频通话服务

基于 WebRTC 的实时音视频通话功能。
支持信令交换、通话记录、通话质量管理。

技术架构:
- 使用 WebRTC 进行 P2P 音视频传输
- WebSocket 用于信令交换
- 可选 TURN/STUN 服务器用于 NAT 穿透
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid

from db.models import VideoCallDB, UserDB


# WebRTC 配置
DEFAULT_ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
    # 生产环境应配置自己的 TURN 服务器
    # {"urls": "turn:your-turn-server.com:3478", "username": "user", "credential": "pass"},
]


class VideoCallService:
    """视频通话服务"""

    def __init__(self, db: Session):
        self.db = db
        self.active_calls = {}  # 内存存储活跃通话 {room_id: call_info}

    def create_call(self, caller_id: str, receiver_id: str) -> Dict[str, Any]:
        """
        创建视频通话

        Returns:
            {
                "call_id": str,
                "room_id": str,
                "status": "pending",
                "ice_servers": [...],
            }
        """
        # 验证用户
        caller = self.db.query(UserDB).filter(UserDB.id == caller_id).first()
        receiver = self.db.query(UserDB).filter(UserDB.id == receiver_id).first()

        if not caller or not receiver:
            raise ValueError("用户不存在")

        # 生成唯一房间 ID
        room_id = f"call_{uuid.uuid4().hex[:12]}"

        # 创建通话记录
        call = VideoCallDB(
            id=str(uuid.uuid4()),
            caller_id=caller_id,
            receiver_id=receiver_id,
            room_id=room_id,
            status="pending",
        )

        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)

        # 存储到活跃通话
        self.active_calls[room_id] = {
            "call_id": call.id,
            "caller_id": caller_id,
            "receiver_id": receiver_id,
            "status": "pending",
            "started_at": None,
        }

        return {
            "call_id": call.id,
            "room_id": room_id,
            "status": "pending",
            "ice_servers": DEFAULT_ICE_SERVERS,
            "created_at": call.created_at.isoformat(),
        }

    def accept_call(self, call_id: str, receiver_id: str) -> Dict[str, Any]:
        """接受视频通话"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        if call.receiver_id != receiver_id:
            raise ValueError("无权接受此通话")

        if call.status != "pending":
            raise ValueError(f"通话状态不允许接受：{call.status}")

        call.status = "accepted"
        call.started_at = datetime.utcnow()

        self.db.commit()

        # 更新活跃通话状态
        if call.room_id in self.active_calls:
            self.active_calls[call.room_id]["status"] = "accepted"
            self.active_calls[call.room_id]["started_at"] = call.started_at.isoformat()

        return {
            "call_id": call.id,
            "room_id": call.room_id,
            "status": "accepted",
            "ice_servers": DEFAULT_ICE_SERVERS,
        }

    def reject_call(self, call_id: str, receiver_id: str) -> bool:
        """拒绝视频通话"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        if call.receiver_id != receiver_id:
            raise ValueError("无权拒绝此通话")

        call.status = "rejected"
        self.db.commit()

        # 从活跃通话移除
        if call.room_id in self.active_calls:
            del self.active_calls[call.room_id]

        return True

    def end_call(self, call_id: str, user_id: str,
                 duration_seconds: Optional[int] = None,
                 quality_score: Optional[float] = None) -> bool:
        """结束视频通话"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        if call.caller_id != user_id and call.receiver_id != user_id:
            raise ValueError("无权结束此通话")

        call.status = "ended"
        call.ended_at = datetime.utcnow()

        if duration_seconds is not None:
            call.duration_seconds = duration_seconds
        elif call.started_at:
            call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())

        if quality_score is not None:
            call.quality_score = quality_score

        self.db.commit()

        # 从活跃通话移除
        if call.room_id in self.active_calls:
            del self.active_calls[call.room_id]

        return True

    def update_sdp_offer(self, call_id: str, sdp_offer: str, user_id: str) -> bool:
        """更新 SDP Offer"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        if call.caller_id != user_id:
            raise ValueError("只有主叫方可以设置 SDP Offer")

        call.sdp_offer = sdp_offer
        self.db.commit()

        return True

    def update_sdp_answer(self, call_id: str, sdp_answer: str, user_id: str) -> bool:
        """更新 SDP Answer"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        if call.receiver_id != user_id:
            raise ValueError("只有被叫方可以设置 SDP Answer")

        call.sdp_answer = sdp_answer
        self.db.commit()

        return True

    def add_ice_candidate(self, call_id: str, candidate: Dict[str, Any],
                          user_id: str) -> bool:
        """添加 ICE Candidate"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        # 解析现有的 ICE candidates
        ice_candidates = json.loads(call.ice_candidates) if call.ice_candidates else []

        # 添加新的 candidate
        ice_candidates.append({
            "candidate": candidate,
            "from_user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        call.ice_candidates = json.dumps(ice_candidates)
        self.db.commit()

        return True

    def get_ice_candidates(self, call_id: str, for_user_id: str) -> List[Dict[str, Any]]:
        """获取 ICE Candidates (排除自己的)"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            raise ValueError("通话不存在")

        ice_candidates = json.loads(call.ice_candidates) if call.ice_candidates else []

        # 返回对方的 candidates
        return [
            c for c in ice_candidates
            if c.get("from_user_id") != for_user_id
        ]

    def get_call_info(self, call_id: str) -> Optional[Dict[str, Any]]:
        """获取通话信息"""
        call = self.db.query(VideoCallDB).filter(VideoCallDB.id == call_id).first()

        if not call:
            return None

        return {
            "call_id": call.id,
            "room_id": call.room_id,
            "caller_id": call.caller_id,
            "receiver_id": call.receiver_id,
            "status": call.status,
            "duration_seconds": call.duration_seconds,
            "quality_score": call.quality_score,
            "connection_type": call.connection_type,
            "created_at": call.created_at.isoformat(),
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        }

    def get_user_call_history(self, user_id: str,
                              limit: int = 20,
                              offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户通话历史"""
        calls = self.db.query(VideoCallDB).filter(
            (VideoCallDB.caller_id == user_id) | (VideoCallDB.receiver_id == user_id)
        ).order_by(VideoCallDB.created_at.desc()).limit(limit).offset(offset).all()

        return [
            {
                "call_id": call.id,
                "room_id": call.room_id,
                "caller_id": call.caller_id,
                "receiver_id": call.receiver_id,
                "status": call.status,
                "duration_seconds": call.duration_seconds,
                "quality_score": call.quality_score,
                "created_at": call.created_at.isoformat(),
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                # 添加对方用户信息
                "other_user_id": call.receiver_id if call.caller_id == user_id else call.caller_id,
            }
            for call in calls
        ]

    def get_active_calls(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户活跃的通话"""
        active = []

        for room_id, call_info in self.active_calls.items():
            if call_info["caller_id"] == user_id or call_info["receiver_id"] == user_id:
                active.append({
                    "call_id": call_info["call_id"],
                    "room_id": room_id,
                    "caller_id": call_info["caller_id"],
                    "receiver_id": call_info["receiver_id"],
                    "status": call_info["status"],
                })

        return active

    def get_call_stats(self, user_id: str) -> Dict[str, Any]:
        """获取通话统计"""
        total_calls = self.db.query(VideoCallDB).filter(
            (VideoCallDB.caller_id == user_id) | (VideoCallDB.receiver_id == user_id)
        ).count()

        completed_calls = self.db.query(VideoCallDB).filter(
            (VideoCallDB.caller_id == user_id) | (VideoCallDB.receiver_id == user_id),
            VideoCallDB.status == "ended",
            VideoCallDB.duration_seconds > 0
        ).count()

        total_duration = self.db.query(func.sum(VideoCallDB.duration_seconds)).filter(
            (VideoCallDB.caller_id == user_id) | (VideoCallDB.receiver_id == user_id),
            VideoCallDB.status == "ended"
        ).scalar() or 0

        avg_quality = self.db.query(func.avg(VideoCallDB.quality_score)).filter(
            (VideoCallDB.caller_id == user_id) | (VideoCallDB.receiver_id == user_id),
            VideoCallDB.quality_score.isnot(None)
        ).scalar() or 0

        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "total_duration_minutes": int(total_duration / 60),
            "average_quality_score": round(avg_quality, 2) if avg_quality else 0,
            "completion_rate": round(completed_calls / total_calls * 100, 2) if total_calls > 0 else 0,
        }

    def cleanup_stale_calls(self, max_age_hours: int = 24) -> int:
        """清理过期的通话记录"""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        stale_calls = self.db.query(VideoCallDB).filter(
            VideoCallDB.status == "pending",
            VideoCallDB.created_at < cutoff
        ).all()

        count = 0
        for call in stale_calls:
            call.status = "missed"
            count += 1

        self.db.commit()

        return count