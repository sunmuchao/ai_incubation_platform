"""
P5 文件存储服务 - 数据模型

文件存储系统支持:
- 文件上传/下载
- 文件类型校验
- 文件分类 (交付物、证据、头像、文档等)
- 本地存储或 S3/MinIO 存储
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .db_models import Base


class FileTypeCategory(str, enum.Enum):
    """文件分类"""
    DELIVERABLE = "deliverable"  # 交付物
    EVIDENCE = "evidence"  # 争议证据
    AVATAR = "avatar"  # 头像
    DOCUMENT = "document"  # 文档
    IMAGE = "image"  # 图片
    VIDEO = "video"  # 视频
    AUDIO = "audio"  # 音频
    CODE = "code"  # 代码文件
    OTHER = "other"  # 其他


class FileStatus(str, enum.Enum):
    """文件状态"""
    PENDING = "pending"  # 上传中
    ACTIVE = "active"  # 有效
    DELETED = "deleted"  # 已删除 (软删除)
    QUARANTINED = "quarantined"  # 隔离中 (安全扫描)


class FileDB(Base):
    """文件数据库模型"""
    __tablename__ = "files"

    id = Column(String(64), primary_key=True)  # 文件 ID (UUID)

    # 文件基本信息
    original_filename = Column(String(255), nullable=False)  # 原始文件名
    stored_filename = Column(String(255), nullable=False)  # 存储文件名 (UUID + 扩展名)
    file_type = Column(String(100), nullable=False)  # MIME 类型
    file_extension = Column(String(20), nullable=False)  # 文件扩展名
    file_size = Column(BigInteger, nullable=False)  # 文件大小 (字节)
    category = Column(SQLEnum(FileTypeCategory), default=FileTypeCategory.OTHER)  # 文件分类

    # 文件存储信息
    storage_type = Column(String(20), nullable=False, default="local")  # 存储类型：local/s3/minio
    storage_path = Column(String(512), nullable=False)  # 存储路径
    storage_bucket = Column(String(255), nullable=True)  # 存储桶名称 (S3/MinIO)
    public_url = Column(String(1024), nullable=True)  # 公开访问 URL

    # 文件校验信息
    file_hash = Column(String(64), nullable=True)  # 文件哈希 (SHA256)
    virus_scan_status = Column(String(20), default="pending")  # 病毒扫描状态
    virus_scan_result = Column(Text, nullable=True)  # 病毒扫描结果

    # 关联信息
    uploader_id = Column(String(64), ForeignKey("users.id"), nullable=False)  # 上传者 ID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)  # 租户 ID
    related_order_id = Column(String(64), ForeignKey("orders.id"), nullable=True)  # 关联订单 ID
    related_dispute_id = Column(String(64), ForeignKey("disputes.id"), nullable=True)  # 关联争议 ID

    # 文件状态
    status = Column(SQLEnum(FileStatus), default=FileStatus.PENDING)  # 文件状态
    is_public = Column(Boolean, default=False)  # 是否公开
    download_count = Column(Integer, default=0)  # 下载次数

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    deleted_at = Column(DateTime, nullable=True)  # 删除时间

    # 关联关系
    uploader = relationship("UserDB", back_populates="files")
    tenant = relationship("TenantDB", back_populates="files")
    order = relationship("OrderDB", back_populates="files")
    # dispute 关联在 add_file_relationships 中动态添加，避免循环依赖
    dispute = None  # 由 add_file_relationships() 动态添加

    def to_dict(self):
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_size_formatted": self.format_file_size(self.file_size),
            "file_extension": self.file_extension,
            "category": self.category.value,
            "storage_type": self.storage_type,
            "storage_path": self.storage_path,
            "public_url": self.public_url,
            "file_hash": self.file_hash,
            "status": self.status.value,
            "is_public": self.is_public,
            "download_count": self.download_count,
            "uploader_id": self.uploader_id,
            "related_order_id": self.related_order_id,
            "related_dispute_id": self.related_dispute_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# 添加到 db_models 的关联关系
def add_file_relationships():
    """添加文件关联关系到现有模型"""
    from .db_models import UserDB, TenantDB, OrderDB
    from .p4_models import DisputeDB

    # UserDB 关联
    if not hasattr(UserDB, 'files'):
        UserDB.files = relationship("FileDB", back_populates="uploader", lazy="dynamic")

    # TenantDB 关联
    if not hasattr(TenantDB, 'files'):
        TenantDB.files = relationship("FileDB", back_populates="tenant", lazy="dynamic")

    # OrderDB 关联
    if not hasattr(OrderDB, 'files'):
        OrderDB.files = relationship("FileDB", back_populates="order", lazy="dynamic")

    # DisputeDB 关联 - 动态添加 files 关系
    if not hasattr(DisputeDB, 'files'):
        DisputeDB.files = relationship("FileDB", back_populates="dispute", lazy="dynamic")

    # FileDB 关联 - 动态添加 dispute 关系
    if not hasattr(FileDB, 'dispute') or getattr(FileDB, 'dispute') is None:
        FileDB.dispute = relationship("DisputeDB", back_populates="files")
