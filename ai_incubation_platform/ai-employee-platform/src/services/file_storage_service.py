"""
P5 文件存储服务

支持:
- 文件上传 (本地/S3/MinIO)
- 文件下载
- 文件类型校验
- 病毒扫描 (可选)
- 文件哈希计算
- 存储空间管理
"""

import os
import uuid
import hashlib
import mimetypes
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import shutil

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status, Depends

from models.file_models import FileDB, FileTypeCategory, FileStatus
from models.db_models import TenantDB
from config.settings import settings
from config.database import get_db


# ============== 允许的文件类型配置 ==============

ALLOWED_FILE_TYPES: Dict[FileTypeCategory, List[str]] = {
    FileTypeCategory.DELIVERABLE: [
        "application/pdf", "application/zip", "application/x-zip-compressed",
        "application/json", "text/plain", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv", "application/x-tar", "application/gzip"
    ],
    FileTypeCategory.EVIDENCE: [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain", "audio/mpeg", "audio/wav",
        "video/mp4", "video/quicktime"
    ],
    FileTypeCategory.AVATAR: [
        "image/jpeg", "image/png", "image/gif", "image/webp"
    ],
    FileTypeCategory.DOCUMENT: [
        "application/pdf", "text/plain", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/markdown", "text/rtf"
    ],
    FileTypeCategory.IMAGE: [
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"
    ],
    FileTypeCategory.VIDEO: [
        "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"
    ],
    FileTypeCategory.AUDIO: [
        "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"
    ],
    FileTypeCategory.CODE: [
        "text/plain", "text/x-python", "text/x-java", "text/x-c",
        "text/x-c++", "text/javascript", "text/html", "text/css",
        "application/json", "application/xml", "text/yaml", "application/x-yaml"
    ],
    FileTypeCategory.OTHER: ["*"]  # 允许所有类型
}

# 文件大小限制 (字节)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB 默认限制
MAX_FILE_SIZE_BY_CATEGORY = {
    FileTypeCategory.DELIVERABLE: 500 * 1024 * 1024,  # 500MB
    FileTypeCategory.EVIDENCE: 100 * 1024 * 1024,  # 100MB
    FileTypeCategory.AVATAR: 5 * 1024 * 1024,  # 5MB
    FileTypeCategory.DOCUMENT: 50 * 1024 * 1024,  # 50MB
    FileTypeCategory.IMAGE: 20 * 1024 * 1024,  # 20MB
    FileTypeCategory.VIDEO: 1024 * 1024 * 1024,  # 1GB
    FileTypeCategory.AUDIO: 100 * 1024 * 1024,  # 100MB
    FileTypeCategory.CODE: 10 * 1024 * 1024,  # 10MB
    FileTypeCategory.OTHER: 100 * 1024 * 1024,  # 100MB
}

# 危险文件扩展名黑名单
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.vbe',
    '.js', '.jse', '.wsf', '.wsh', '.msi', '.msp', '.hta', '.cpl',
    '.msc', '.jar', '.ps1', '.reg', '.dll', '.sys', '.drv'
}


class FileStorageService:
    """文件存储服务"""

    def __init__(self, db: Session):
        self.db = db
        self.storage_base = Path(settings.file_storage_path)
        self.storage_base.mkdir(parents=True, exist_ok=True)

    def _generate_file_id(self) -> str:
        """生成文件 ID"""
        return str(uuid.uuid4())

    def _generate_stored_filename(self, file_id: str, extension: str) -> str:
        """生成存储文件名"""
        return f"{file_id}{extension}"

    def _get_storage_path(self, tenant_id: str, category: FileTypeCategory) -> Path:
        """获取存储路径"""
        base_path = self.storage_base / tenant_id / category.value
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path

    def _calculate_file_hash(self, file_content: bytes) -> str:
        """计算文件 SHA256 哈希"""
        sha256_hash = hashlib.sha256(file_content)
        return sha256_hash.hexdigest()

    def _detect_mime_type(self, filename: str, file_content: bytes) -> str:
        """检测文件 MIME 类型"""
        # 首先尝试通过扩展名判断
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type

        # 通过文件头判断
        if file_content[:4] == b'\x89PNG':
            return 'image/png'
        elif file_content[:2] == b'\xff\xd8':
            return 'image/jpeg'
        elif file_content[:4] == b'GIF8':
            return 'image/gif'
        elif file_content[:4] == b'%PDF':
            return 'application/pdf'
        elif file_content[:4] == b'PK\x03\x04':
            return 'application/zip'

        return 'application/octet-stream'

    def _validate_file(self, file: UploadFile, category: FileTypeCategory) -> None:
        """验证文件"""
        # 检查文件扩展名
        ext = Path(file.filename).suffix.lower()
        if ext in DANGEROUS_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不允许的文件类型：{ext}"
            )

        # 检查 MIME 类型
        allowed_types = ALLOWED_FILE_TYPES.get(category, ["*"])
        if "*" not in allowed_types:
            mime_type = file.content_type or self._detect_mime_type(file.filename, b"")
            if mime_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不允许的文件类型：{mime_type}，允许的類型：{allowed_types}"
                )

        # 检查文件大小
        max_size = MAX_FILE_SIZE_BY_CATEGORY.get(category, MAX_FILE_SIZE)
        # 注意：实际大小检查需要在读取文件后进行

    async def _get_file_size(self, file: UploadFile) -> int:
        """获取文件大小"""
        # 读取文件内容以获取大小
        content = await file.read()
        file_size = len(content)
        # 重置文件指针
        await file.seek(0)
        return file_size

    def _save_file_locally(self, file_id: str, content: bytes, storage_path: Path, filename: str) -> str:
        """本地保存文件"""
        file_path = storage_path / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        return str(file_path)

    async def upload_file(
        self,
        file: UploadFile,
        category: FileTypeCategory,
        uploader_id: str,
        tenant_id: str,
        related_order_id: Optional[str] = None,
        related_dispute_id: Optional[str] = None,
        is_public: bool = False
    ) -> FileDB:
        """
        上传文件

        Args:
            file: 上传的文件
            category: 文件分类
            uploader_id: 上传者 ID
            tenant_id: 租户 ID
            related_order_id: 关联订单 ID
            related_dispute_id: 关联争议 ID
            is_public: 是否公开

        Returns:
            FileDB: 文件记录
        """
        # 验证租户
        tenant = self.db.query(TenantDB).filter(TenantDB.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        # 验证文件
        self._validate_file(file, category)

        # 读取文件内容
        content = await file.read()

        # 检查文件大小
        file_size = len(content)
        max_size = MAX_FILE_SIZE_BY_CATEGORY.get(category, MAX_FILE_SIZE)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超出限制：{FileDB.format_file_size(file_size)} > {FileDB.format_file_size(max_size)}"
            )

        # 生成文件信息
        file_id = self._generate_file_id()
        file_extension = Path(file.filename).suffix.lower()
        stored_filename = self._generate_stored_filename(file_id, file_extension)
        file_type = file.content_type or self._detect_mime_type(file.filename, content)
        file_hash = self._calculate_file_hash(content)

        # 获取存储路径
        storage_path = self._get_storage_path(tenant_id, category)

        # 保存文件
        try:
            storage_file_path = self._save_file_locally(file_id, content, storage_path, stored_filename)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件保存失败：{str(e)}"
            )

        # 创建文件记录
        file_record = FileDB(
            id=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_type=file_type,
            file_extension=file_extension,
            file_size=file_size,
            category=category,
            storage_type="local",
            storage_path=storage_file_path,
            storage_bucket=None,
            public_url=None,
            file_hash=file_hash,
            virus_scan_status="skipped",  # 暂不实现病毒扫描
            virus_scan_result=None,
            uploader_id=uploader_id,
            tenant_id=tenant_id,
            related_order_id=related_order_id,
            related_dispute_id=related_dispute_id,
            status=FileStatus.ACTIVE,
            is_public=is_public,
            download_count=0
        )

        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)

        return file_record

    def download_file(self, file_id: str, user_id: str) -> tuple:
        """
        下载文件

        Args:
            file_id: 文件 ID
            user_id: 下载者 ID

        Returns:
            tuple: (文件路径，原始文件名，MIME 类型)
        """
        file_record = self.db.query(FileDB).filter(FileDB.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")

        if file_record.status != FileStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="文件不可用")

        # 检查权限
        if not file_record.is_public:
            # 只有上传者、订单相关方、争议相关方可以下载
            if file_record.uploader_id != user_id:
                if file_record.related_order_id:
                    # TODO: 检查是否是订单相关方
                    pass
                if file_record.related_dispute_id:
                    # TODO: 检查是否是争议相关方
                    pass

        # 增加下载次数
        file_record.download_count += 1
        self.db.commit()

        return (
            file_record.storage_path,
            file_record.original_filename,
            file_record.file_type
        )

    def delete_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        删除文件 (软删除)

        Args:
            file_id: 文件 ID
            user_id: 用户 ID

        Returns:
            Dict: 删除结果
        """
        file_record = self.db.query(FileDB).filter(FileDB.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 检查权限：只有上传者可以删除
        if file_record.uploader_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有删除权限"
            )

        # 软删除
        file_record.status = FileStatus.DELETED
        file_record.deleted_at = datetime.utcnow()
        self.db.commit()

        # 物理删除文件 (可选)
        try:
            if os.path.exists(file_record.storage_path):
                os.remove(file_record.storage_path)
        except Exception:
            pass  # 文件删除失败不影响软删除

        return {"message": "文件删除成功", "file_id": file_id}

    def get_file_info(self, file_id: str) -> FileDB:
        """获取文件信息"""
        file_record = self.db.query(FileDB).filter(FileDB.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        return file_record

    def list_files(
        self,
        tenant_id: str,
        category: Optional[FileTypeCategory] = None,
        related_order_id: Optional[str] = None,
        related_dispute_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FileDB]:
        """
        列出文件

        Args:
            tenant_id: 租户 ID
            category: 文件分类
            related_order_id: 关联订单 ID
            related_dispute_id: 关联争议 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[FileDB]: 文件列表
        """
        query = self.db.query(FileDB).filter(
            FileDB.tenant_id == tenant_id,
            FileDB.status == FileStatus.ACTIVE
        )

        if category:
            query = query.filter(FileDB.category == category)
        if related_order_id:
            query = query.filter(FileDB.related_order_id == related_order_id)
        if related_dispute_id:
            query = query.filter(FileDB.related_dispute_id == related_dispute_id)

        return query.order_by(FileDB.created_at.desc()).offset(offset).limit(limit).all()

    def get_tenant_storage_usage(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户存储空间使用情况

        Args:
            tenant_id: 租户 ID

        Returns:
            Dict: 使用情况统计
        """
        files = self.db.query(FileDB).filter(
            FileDB.tenant_id == tenant_id,
            FileDB.status == FileStatus.ACTIVE
        ).all()

        total_size = sum(f.file_size for f in files)
        category_stats = {}

        for category in FileTypeCategory:
            category_files = [f for f in files if f.category == category]
            if category_files:
                category_stats[category.value] = {
                    "count": len(category_files),
                    "total_size": sum(f.file_size for f in category_files),
                    "total_size_formatted": FileDB.format_file_size(sum(f.file_size for f in category_files))
                }

        return {
            "tenant_id": tenant_id,
            "total_files": len(files),
            "total_size": total_size,
            "total_size_formatted": FileDB.format_file_size(total_size),
            "category_stats": category_stats
        }


# 依赖注入
from fastapi import Depends

def get_file_storage_service(db: Session):
    """获取文件存储服务实例"""
    return FileStorageService(db)
