"""
视频片段服务

参考 Tinder 的视频片段功能：
- 用户可以录制短视频自我介绍
- 视频片段作为匹配资料的一部分
- 增加真实感和吸引力
- AI 分析视频内容，辅助匹配
"""
import uuid
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.logger import logger
from services.base_service import BaseService


class VideoClipService(BaseService):
    """视频片段服务"""

    # 视频配置
    MAX_VIDEO_DURATION = 30  # 最大时长（秒）
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 最大文件大小（50MB）
    ALLOWED_FORMATS = ["mp4", "mov", "webm", "avi"]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def upload_video(
        self,
        user_id: str,
        video_file_path: str,
        video_duration: float,
        video_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传视频片段

        Args:
            user_id: 用户 ID
            video_file_path: 视频文件路径
            video_duration: 视频时长（秒）
            video_description: 视频描述（可选）

        Returns:
            视频记录信息
        """
        # 检查时长限制
        if video_duration > self.MAX_VIDEO_DURATION:
            return {
                "success": False,
                "message": f"视频时长超过限制（最大 {self.MAX_VIDEO_DURATION} 秒）"
            }

        # 检查文件大小
        if os.path.exists(video_file_path):
            file_size = os.path.getsize(video_file_path)
            if file_size > self.MAX_VIDEO_SIZE:
                return {
                    "success": False,
                    "message": f"视频文件过大（最大 {self.MAX_VIDEO_SIZE / 1024 / 1024}MB）"
                }

        # 生成视频 ID
        video_id = str(uuid.uuid4())

        # AI 分析视频内容
        video_analysis = await self._analyze_video_content(video_file_path)

        # 保存到数据库
        from models.video_clip import VideoClipDB

        video_record = VideoClipDB(
            id=video_id,
            user_id=user_id,
            video_url=video_file_path,  # 实际应用中应上传到云存储
            video_duration=video_duration,
            video_description=video_description or video_analysis.get("summary", ""),
            video_thumbnail=video_analysis.get("thumbnail_url"),
            video_analysis=video_analysis,
            is_primary=False,
            created_at=datetime.now()
        )
        self.db.add(video_record)
        self.db.commit()

        logger.info(f"Video clip uploaded: {video_id} by user {user_id}")

        return {
            "success": True,
            "video_id": video_id,
            "user_id": user_id,
            "video_url": video_file_path,
            "video_duration": video_duration,
            "video_description": video_description,
            "video_analysis": video_analysis,
            "created_at": datetime.now().isoformat()
        }

    async def _analyze_video_content(self, video_file_path: str) -> Dict[str, Any]:
        """
        AI 分析视频内容

        分析视频中的内容、场景、情感等
        """
        # 视频分析暂用模拟数据（集成视频分析 AI 后可提取真实场景/情感）
        # 这里返回模拟结果
        return {
            "summary": "用户自我介绍视频",
            "scenes": ["室内", "站立"],
            "emotions": ["自信", "友善"],
            "keywords": ["自我介绍", "爱好"],
            "thumbnail_url": None,  # 视频缩略图
            "confidence": 0.8
        }

    def get_user_videos(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户的视频片段列表

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            视频列表
        """
        from models.video_clip import VideoClipDB

        videos = self.db.query(VideoClipDB).filter(
            VideoClipDB.user_id == user_id,
            VideoClipDB.is_deleted == False
        ).order_by(desc(VideoClipDB.created_at)).limit(limit).all()

        return [
            {
                "video_id": v.id,
                "user_id": v.user_id,
                "video_url": v.video_url,
                "video_thumbnail": v.video_thumbnail,
                "video_duration": v.video_duration,
                "video_description": v.video_description,
                "is_primary": v.is_primary,
                "view_count": v.view_count,
                "created_at": v.created_at.isoformat()
            }
            for v in videos
        ]

    def set_primary_video(self, user_id: str, video_id: str) -> bool:
        """
        设置主要视频（作为资料展示）

        Args:
            user_id: 用户 ID
            video_id: 视频 ID

        Returns:
            是否成功
        """
        from models.video_clip import VideoClipDB

        # 先取消所有其他视频的主要状态
        self.db.query(VideoClipDB).filter(
            VideoClipDB.user_id == user_id
        ).update({"is_primary": False})

        # 设置目标视频为主要
        target_video = self.db.query(VideoClipDB).filter(
            VideoClipDB.id == video_id,
            VideoClipDB.user_id == user_id
        ).first()

        if target_video:
            target_video.is_primary = True
            self.db.commit()
            logger.info(f"Primary video set: {video_id} for user {user_id}")
            return True

        return False

    def delete_video(self, user_id: str, video_id: str) -> bool:
        """
        删除视频

        Args:
            user_id: 用户 ID
            video_id: 视频 ID

        Returns:
            是否成功
        """
        from models.video_clip import VideoClipDB

        video = self.db.query(VideoClipDB).filter(
            VideoClipDB.id == video_id,
            VideoClipDB.user_id == user_id
        ).first()

        if video:
            video.is_deleted = True
            self.db.commit()

            # 物理文件删除暂未实现（软删除已足够，后续可集成对象存储删除）

            logger.info(f"Video deleted: {video_id}")
            return True

        return False

    def get_primary_video(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的主要视频

        Args:
            user_id: 用户 ID

        Returns:
            主要视频信息
        """
        from models.video_clip import VideoClipDB

        video = self.db.query(VideoClipDB).filter(
            VideoClipDB.user_id == user_id,
            VideoClipDB.is_primary == True,
            VideoClipDB.is_deleted == False
        ).first()

        if video:
            return {
                "video_id": video.id,
                "user_id": video.user_id,
                "video_url": video.video_url,
                "video_thumbnail": video.video_thumbnail,
                "video_duration": video.video_duration,
                "video_description": video.video_description,
                "view_count": video.view_count,
                "created_at": video.created_at.isoformat()
            }

        return None

    def increment_view_count(self, video_id: str) -> int:
        """
        增加视频观看次数

        Args:
            video_id: 视频 ID

        Returns:
            当前观看次数
        """
        from models.video_clip import VideoClipDB

        video = self.db.query(VideoClipDB).filter(
            VideoClipDB.id == video_id
        ).first()

        if video:
            video.view_count += 1
            self.db.commit()
            return video.view_count

        return 0

    async def generate_video_intro_suggestions(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        AI 生成视频介绍建议

        帮助用户录制更好的自我介绍视频

        Args:
            user_profile: 用户资料

        Returns:
            介绍建议列表
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        prompt = f"""请为用户生成短视频自我介绍的建议：

用户资料：
- 年龄：{user_profile.get('age')}
- 兴趣：{user_profile.get('interests', [])}
- 简介：{user_profile.get('bio', '')}
- 交友目的：{user_profile.get('goal', '')}

请提供 3-5 个不同风格的介绍建议：
1. 自然风格 - 最真实的自我介绍
2. 轻松风格 - 幽默有趣的表达
3. 深度风格 - 更有内涵的介绍
4. 简洁风格 - 短小精悍的介绍

每个建议请给出：
- 介绍内容大纲（不超过 30 秒）
- 拍摄建议（场景、姿势）
- 预期效果

回复格式：
[
  {
    "style": "natural",
    "outline": "介绍内容大纲",
    "filming_tips": "拍摄建议",
    "expected_effect": "预期效果"
  },
  ...
]"""

        try:
            result = await llm_service.generate(prompt)
            import json
            suggestions = json.loads(result)
            return suggestions
        except Exception as e:
            logger.error(f"Failed to generate video intro suggestions: {e}")
            return [
                {
                    "style": "natural",
                    "outline": "大家好，我是...喜欢...期待...",
                    "filming_tips": "选择安静的环境，保持微笑",
                    "expected_effect": "真实自然，容易引起共鸣"
                }
            ]


# 服务工厂函数
def get_video_clip_service(db: Session) -> VideoClipService:
    """获取视频片段服务实例"""
    return VideoClipService(db)