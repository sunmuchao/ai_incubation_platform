"""
P5 文件存储 API

提供文件上传、下载、删除、列表等接口
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config.database import get_db
from services.file_storage_service import FileStorageService
from models.file_models import FileTypeCategory

router = APIRouter(prefix="/api/files", tags=["Files"])


def get_file_service(db: Session) -> FileStorageService:
    """获取文件存储服务实例"""
    return FileStorageService(db)


@router.post("/upload", summary="上传文件", response_model=dict)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件"),
    category: FileTypeCategory = Form(..., description="文件分类"),
    related_order_id: Optional[str] = Form(None, description="关联订单 ID"),
    related_dispute_id: Optional[str] = Form(None, description="关联争议 ID"),
    is_public: bool = Form(False, description="是否公开"),
    db: Session = Depends(get_db),
    user_id: str = Form(..., description="用户 ID"),
    tenant_id: str = Form(..., description="租户 ID")
):
    """
    上传文件

    - **category**: 文件分类 (deliverable/evidence/avatar/document/image/video/audio/code/other)
    - **related_order_id**: 关联订单 ID (可选)
    - **related_dispute_id**: 关联争议 ID (可选)
    - **is_public**: 是否公开访问
    - **user_id**: 用户 ID
    - **tenant_id**: 租户 ID
    """
    file_service = get_file_service(db)
    file_record = await file_service.upload_file(
        file=file,
        category=category,
        uploader_id=user_id,
        tenant_id=tenant_id,
        related_order_id=related_order_id,
        related_dispute_id=related_dispute_id,
        is_public=is_public
    )
    return {
        "message": "文件上传成功",
        "file": file_record.to_dict()
    }


@router.get("/{file_id}", summary="获取文件信息", response_model=dict)
async def get_file_info(
    file_id: str,
    db: Session = Depends(get_db)
):
    """获取文件详细信息"""
    file_service = get_file_service(db)
    file_record = file_service.get_file_info(file_id)
    return {"file": file_record.to_dict()}


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    下载文件

    返回文件二进制内容
    """
    try:
        file_service = get_file_service(db)
        file_path, original_filename, file_type = file_service.download_file(file_id, "anonymous")
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type=file_type
        )
    except HTTPException:
        raise


@router.delete("/{file_id}", summary="删除文件", response_model=dict)
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    user_id: str = Query(..., description="用户 ID")
):
    """删除文件 (软删除)"""
    file_service = get_file_service(db)
    result = file_service.delete_file(file_id, user_id)
    return result


@router.get("", summary="列出文件", response_model=dict)
async def list_files(
    category: Optional[FileTypeCategory] = Query(None, description="文件分类"),
    related_order_id: Optional[str] = Query(None, description="关联订单 ID"),
    related_dispute_id: Optional[str] = Query(None, description="关联争议 ID"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
    tenant_id: str = Query(..., description="租户 ID")
):
    """
    列出文件列表

    支持按分类、关联订单、关联争议过滤
    """
    file_service = get_file_service(db)
    files = file_service.list_files(
        tenant_id=tenant_id,
        category=category,
        related_order_id=related_order_id,
        related_dispute_id=related_dispute_id,
        limit=limit,
        offset=offset
    )

    return {
        "files": [f.to_dict() for f in files],
        "total": len(files),
        "limit": limit,
        "offset": offset
    }


@router.get("/usage", summary="获取存储空间使用情况", response_model=dict)
async def get_storage_usage(
    db: Session = Depends(get_db),
    tenant_id: str = Query(..., description="租户 ID")
):
    """获取租户存储空间使用情况统计"""
    file_service = get_file_service(db)
    usage = file_service.get_tenant_storage_usage(tenant_id)
    return {"usage": usage}


@router.post("/upload-multiple", summary="批量上传文件", response_model=dict)
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="要上传的文件列表"),
    category: FileTypeCategory = Form(..., description="文件分类"),
    related_order_id: Optional[str] = Form(None, description="关联订单 ID"),
    related_dispute_id: Optional[str] = Form(None, description="关联争议 ID"),
    is_public: bool = Form(False, description="是否公开"),
    db: Session = Depends(get_db),
    user_id: str = Form(..., description="用户 ID"),
    tenant_id: str = Form(..., description="租户 ID")
):
    """
    批量上传文件

    最多同时上传 10 个文件
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="最多同时上传 10 个文件"
        )

    file_service = get_file_service(db)
    uploaded_files = []
    failed_files = []

    for file in files:
        try:
            file_record = await file_service.upload_file(
                file=file,
                category=category,
                uploader_id=user_id,
                tenant_id=tenant_id,
                related_order_id=related_order_id,
                related_dispute_id=related_dispute_id,
                is_public=is_public
            )
            uploaded_files.append(file_record.to_dict())
        except HTTPException as e:
            failed_files.append({
                "filename": file.filename,
                "error": e.detail
            })

    return {
        "message": f"成功上传 {len(uploaded_files)} 个文件，失败 {len(failed_files)} 个",
        "uploaded_files": uploaded_files,
        "failed_files": failed_files
    }
