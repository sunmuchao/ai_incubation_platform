"""
区块链存证 API。
提供存证创建、验证、查询等功能。
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from services.blockchain_proof_service import get_blockchain_proof_service, BlockchainProofService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain 存证"])


# ============== Dependency ==============

async def get_db() -> AsyncSession:
    """获取数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session


# ============== Schemas ==============

class ProofCreateRequest(BaseModel):
    """创建存证请求。"""
    business_type: str = Field(..., description="业务类型")
    business_id: str = Field(..., description="业务 ID")
    data: Dict[str, Any] = Field(..., description="要存证的数据")


class ProofCreateResponse(BaseModel):
    """创建存证响应。"""
    proof_id: str
    business_type: str
    business_id: str
    data_hash: str
    status: str
    created_at: datetime


class ProofVerifyRequest(BaseModel):
    """验证存证请求。"""
    proof_id: str = Field(..., description="存证 ID")
    original_data: Optional[Dict[str, Any]] = Field(None, description="原始数据（可选，用于哈希比对）")


class ProofVerifyResponse(BaseModel):
    """验证存证响应。"""
    valid: bool
    proof_id: str
    business_type: str
    business_id: str
    data_hash: str
    blockchain_network: Optional[str]
    transaction_hash: Optional[str]
    block_number: Optional[int]
    confirmed_at: Optional[datetime]
    explorer_url: Optional[str]
    error: Optional[str] = None


class ProofDetailResponse(BaseModel):
    """存证详情响应。"""
    proof_id: str
    business_type: str
    business_id: str
    data_hash: str
    data_summary: Dict[str, Any]
    blockchain_network: Optional[str]
    transaction_hash: Optional[str]
    block_number: Optional[int]
    contract_address: Optional[str]
    status: str
    gas_fee: Optional[float]
    gas_fee_cny: Optional[float]
    created_at: datetime
    confirmed_at: Optional[datetime]
    verification_count: int
    last_verified_at: Optional[datetime]
    explorer_url: Optional[str]


class ProofStatisticsResponse(BaseModel):
    """存证统计响应。"""
    total_count: int
    today_count: int
    status_stats: Dict[str, int]
    type_stats: Dict[str, int]


class BatchProofRequest(BaseModel):
    """批量存证请求。"""
    proofs: List[Dict[str, Any]] = Field(..., description="存证数据列表")


# ============== APIs ==============

@router.post("/proofs", response_model=ProofCreateResponse, summary="创建区块链存证")
async def create_proof(
    request: ProofCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Header("system", alias="X-User-ID")
):
    """
    创建区块链存证。

    将关键业务数据的哈希写入区块链，确保数据不可篡改。
    """
    service = get_blockchain_proof_service(db)

    # 创建存证
    proof = await service.create_proof(
        business_type=request.business_type,
        business_id=request.business_id,
        data=request.data,
        created_by=user_id,
    )

    # 异步提交到区块链（不阻塞响应）
    await service.submit_to_blockchain(proof)

    return ProofCreateResponse(
        proof_id=proof.proof_id,
        business_type=proof.business_type,
        business_id=proof.business_id,
        data_hash=proof.data_hash,
        status=proof.status,
        created_at=proof.created_at,
    )


@router.post("/proofs/verify", response_model=ProofVerifyResponse, summary="验证存证")
async def verify_proof(
    request: ProofVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    验证存证。

    验证数据哈希是否匹配，并检查链上存证状态。
    """
    service = get_blockchain_proof_service(db)

    result = await service.verify_proof(
        proof_id=request.proof_id,
        original_data=request.original_data,
    )

    if "error" in result and result.get("error") == "存证不存在":
        raise HTTPException(status_code=404, detail=result["error"])

    return ProofVerifyResponse(
        valid=result["valid"],
        proof_id=result["proof_id"],
        business_type=result["business_type"],
        business_id=result["business_id"],
        data_hash=result["data_hash"],
        blockchain_network=result.get("blockchain_network"),
        transaction_hash=result.get("transaction_hash"),
        block_number=result.get("block_number"),
        confirmed_at=datetime.fromisoformat(result["confirmed_at"]) if result.get("confirmed_at") else None,
        explorer_url=result.get("explorer_url"),
        error=result.get("error"),
    )


@router.get("/proofs/{proof_id}", response_model=ProofDetailResponse, summary="获取存证详情")
async def get_proof(
    proof_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取存证详情。

    返回存证的完整信息，包括链上交易哈希和验证次数。
    """
    from sqlalchemy import select
    from models.blockchain_proof import BlockchainProofDB

    result = await db.execute(
        select(BlockchainProofDB).where(BlockchainProofDB.proof_id == proof_id)
    )
    proof = result.scalar_one_or_none()

    if not proof:
        raise HTTPException(status_code=404, detail="存证不存在")

    # 构建区块浏览器 URL
    explorer_url = None
    if proof.transaction_hash and proof.blockchain_network:
        if proof.blockchain_network == "ethereum":
            explorer_url = f"https://etherscan.io/tx/{proof.transaction_hash}"
        elif proof.blockchain_network == "polygon":
            explorer_url = f"https://polygonscan.com/tx/{proof.transaction_hash}"
        elif proof.blockchain_network == "bsc":
            explorer_url = f"https://bscscan.com/tx/{proof.transaction_hash}"
        else:
            explorer_url = f"https://explorer.example.com/tx/{proof.transaction_hash}"

    return ProofDetailResponse(
        proof_id=proof.proof_id,
        business_type=proof.business_type,
        business_id=proof.business_id,
        data_hash=proof.data_hash,
        data_summary=proof.data_summary,
        blockchain_network=proof.blockchain_network,
        transaction_hash=proof.transaction_hash,
        block_number=proof.block_number,
        contract_address=proof.contract_address,
        status=proof.status,
        gas_fee=proof.gas_fee,
        gas_fee_cny=proof.gas_fee_cny,
        created_at=proof.created_at,
        confirmed_at=proof.confirmed_at,
        verification_count=proof.verification_count,
        last_verified_at=proof.last_verified_at,
        explorer_url=explorer_url,
    )


@router.get("/proofs", response_model=List[ProofDetailResponse], summary="查询存证列表")
async def list_proofs(
    business_type: Optional[str] = Query(None, description="业务类型筛选"),
    business_id: Optional[str] = Query(None, description="业务 ID 筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """
    查询存证列表。

    支持按业务类型、业务 ID、状态等条件筛选。
    """
    from sqlalchemy import select
    from models.blockchain_proof import BlockchainProofDB

    query = select(BlockchainProofDB)

    if business_type:
        query = query.where(BlockchainProofDB.business_type == business_type)
    if business_id:
        query = query.where(BlockchainProofDB.business_id == business_id)
    if status:
        query = query.where(BlockchainProofDB.status == status)

    query = query.order_by(BlockchainProofDB.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    proofs = result.scalars().all()

    return [
        ProofDetailResponse(
            proof_id=proof.proof_id,
            business_type=proof.business_type,
            business_id=proof.business_id,
            data_hash=proof.data_hash,
            data_summary=proof.data_summary,
            blockchain_network=proof.blockchain_network,
            transaction_hash=proof.transaction_hash,
            block_number=proof.block_number,
            contract_address=proof.contract_address,
            status=proof.status,
            gas_fee=proof.gas_fee,
            gas_fee_cny=proof.gas_fee_cny,
            created_at=proof.created_at,
            confirmed_at=proof.confirmed_at,
            verification_count=proof.verification_count,
            last_verified_at=proof.last_verified_at,
            explorer_url=f"https://explorer.example.com/tx/{proof.transaction_hash}" if proof.transaction_hash else None,
        )
        for proof in proofs
    ]


@router.get("/proofs/business/{business_type}/{business_id}", response_model=ProofDetailResponse, summary="根据业务 ID 获取存证")
async def get_proof_by_business(
    business_type: str,
    business_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    根据业务 ID 获取存证。

    例如：/api/blockchain/proofs/business/task_submitted/task-123
    """
    service = get_blockchain_proof_service(db)

    proof = await service.get_proof_by_business_id(
        business_type=business_type,
        business_id=business_id,
    )

    if not proof:
        raise HTTPException(status_code=404, detail="存证不存在")

    explorer_url = None
    if proof.transaction_hash:
        explorer_url = f"https://explorer.example.com/tx/{proof.transaction_hash}"

    return ProofDetailResponse(
        proof_id=proof.proof_id,
        business_type=proof.business_type,
        business_id=proof.business_id,
        data_hash=proof.data_hash,
        data_summary=proof.data_summary,
        blockchain_network=proof.blockchain_network,
        transaction_hash=proof.transaction_hash,
        block_number=proof.block_number,
        contract_address=proof.contract_address,
        status=proof.status,
        gas_fee=proof.gas_fee,
        gas_fee_cny=proof.gas_fee_cny,
        created_at=proof.created_at,
        confirmed_at=proof.confirmed_at,
        verification_count=proof.verification_count,
        last_verified_at=proof.last_verified_at,
        explorer_url=explorer_url,
    )


@router.post("/proofs/batch", response_model=List[ProofCreateResponse], summary="批量创建存证")
async def batch_create_proofs(
    request: BatchProofRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Header("system", alias="X-User-ID")
):
    """
    批量创建存证。

    适用于批量任务提交、批量支付等场景。
    """
    service = get_blockchain_proof_service(db)

    proofs = await service.batch_create_proofs(
        proofs_data=request.proofs,
        created_by=user_id,
    )

    # 批量上链
    for proof in proofs:
        await service.submit_to_blockchain(proof)

    return [
        ProofCreateResponse(
            proof_id=proof.proof_id,
            business_type=proof.business_type,
            business_id=proof.business_id,
            data_hash=proof.data_hash,
            status=proof.status,
            created_at=proof.created_at,
        )
        for proof in proofs
    ]


@router.get("/statistics", response_model=ProofStatisticsResponse, summary="获取存证统计")
async def get_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    获取存证统计信息。

    包括总存证数、今日新增、按状态和业务类型的分布。
    """
    service = get_blockchain_proof_service(db)

    stats = await service.get_statistics()

    return ProofStatisticsResponse(**stats)


@router.post("/config", summary="创建/更新区块链配置")
async def create_config(
    config_data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    创建或更新区块链配置。

    配置包括：
    - 区块链网络（ethereum, polygon, bsc）
    - RPC 节点地址
    - 智能合约地址
    - 钱包地址
    - Gas 配置
    """
    from models.blockchain_proof import BlockchainConfigDB
    import uuid

    # 检查是否已有配置
    from sqlalchemy import select
    result = await db.execute(select(BlockchainConfigDB))
    existing_config = result.scalar_one_or_none()

    if existing_config:
        # 更新现有配置
        for key, value in config_data.items():
            if hasattr(existing_config, key):
                setattr(existing_config, key, value)
        await db.commit()
        await db.refresh(existing_config)
        config = existing_config
    else:
        # 创建新配置
        config = BlockchainConfigDB(
            id=str(uuid.uuid4()),
            **{k: v for k, v in config_data.items() if hasattr(BlockchainConfigDB, k)},
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return {
        "message": "配置已保存",
        "config_id": config.id,
        "network": config.network,
        "is_active": config.is_active,
    }


@router.get("/config", summary="获取区块链配置")
async def get_config(db: AsyncSession = Depends(get_db)):
    """
    获取当前激活的区块链配置。
    """
    from sqlalchemy import select
    from models.blockchain_proof import BlockchainConfigDB

    result = await db.execute(
        select(BlockchainConfigDB).where(BlockchainConfigDB.is_active == True)
    )
    config = result.scalar_one_or_none()

    if not config:
        return {
            "is_configured": False,
            "message": "区块链存证功能尚未配置"
        }

    return {
        "is_configured": True,
        "network": config.network,
        "rpc_url": config.rpc_url,
        "explorer_url": config.explorer_url,
        "contract_address": config.contract_address,
        "wallet_address": config.wallet_address,
        "is_active": config.is_active,
        "auto_proof_enabled": config.auto_proof_enabled,
        "enabled_business_types": config.enabled_business_types,
    }


# ============== 自动存证 Hook 接口 ==============

@router.post("/auto-proof/trigger", summary="触发自动存证")
async def trigger_auto_proof(
    business_type: str = Query(..., description="业务类型"),
    business_id: str = Query(..., description="业务 ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    触发自动存证。

    此接口用于在其他业务流程完成后，触发区块链存证。
    例如：任务提交成功后，调用此接口自动存证。
    """
    from sqlalchemy import select
    from models.blockchain_proof import BlockchainProofDB

    # 检查是否已存在存证
    service = get_blockchain_proof_service(db)
    existing = await service.get_proof_by_business_id(
        business_type=business_type,
        business_id=business_id,
    )

    if existing:
        return {
            "message": "存证已存在",
            "proof_id": existing.proof_id,
            "status": existing.status,
        }

    # 注意：实际业务中，这里需要从对应的业务表获取完整数据
    # 由于是通用接口，这里只做演示
    proof = await service.create_proof(
        business_type=business_type,
        business_id=business_id,
        data={"business_type": business_type, "business_id": business_id},
        created_by="auto",
    )

    await service.submit_to_blockchain(proof)

    return {
        "message": "存证已创建",
        "proof_id": proof.proof_id,
        "status": proof.status,
    }
