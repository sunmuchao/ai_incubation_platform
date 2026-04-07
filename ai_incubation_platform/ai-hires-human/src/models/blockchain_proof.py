"""
区块链存证数据模型。
用于记录关键业务数据的哈希上链，确保数据不可篡改和可追溯。
"""
from datetime import datetime
from typing import Optional, Dict

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class BlockchainProofDB(Base):
    """区块链存证表。"""
    __tablename__ = "blockchain_proofs"

    # 存证 ID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proof_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)

    # 业务类型：task_created, task_submitted, task_accepted, task_rejected,
    #           payment_completed, dispute_resolved, escrow_released
    business_type: Mapped[str] = mapped_column(String(50), index=True)

    # 业务 ID（任务 ID、支付 ID、争议 ID 等）
    business_id: Mapped[str] = mapped_column(String(255), index=True)

    # 数据哈希（SHA256）
    data_hash: Mapped[str] = mapped_column(String(64), index=True)

    # 原始数据摘要（用于验证，不存储完整数据）
    data_summary: Mapped[Dict] = mapped_column(JSON, default=dict)

    # 区块链信息
    blockchain_network: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ethereum, polygon, bsc, etc.
    transaction_hash: Mapped[Optional[str]] = mapped_column(String(66), unique=True)  # 链上交易哈希
    block_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 区块高度
    contract_address: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)  # 智能合约地址

    # 存证状态
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, confirmed, failed

    #  gas 费用
    gas_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Gas 费用（ETH/MATIC 等）
    gas_fee_cny: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Gas 费用（CNY 计价）

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 审计字段
    created_by: Mapped[str] = mapped_column(String(255), default="system")  # 创建者（用户 ID 或 system）
    verification_count: Mapped[int] = mapped_column(Integer, default=0)  # 验证次数
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_business_type_status', 'business_type', 'status'),
        Index('idx_transaction_hash', 'transaction_hash'),
        Index('idx_created_at', 'created_at'),
    )


class BlockchainConfigDB(Base):
    """区块链配置表。"""
    __tablename__ = "blockchain_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    config_name: Mapped[str] = mapped_column(String(100), unique=True)  # 配置名称

    # 区块链网络配置
    network: Mapped[str] = mapped_column(String(50))  # ethereum, polygon, bsc
    rpc_url: Mapped[str] = mapped_column(String(500))  # RPC 节点地址
    explorer_url: Mapped[str] = mapped_column(String(500))  # 区块浏览器地址

    # 智能合约配置
    contract_address: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)  # 存证合约地址
    contract_abi: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # 合约 ABI

    # 账户配置
    wallet_address: Mapped[Optional[str]] = mapped_column(String(42), nullable=True)  # 钱包地址
    wallet_private_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 加密的私钥

    # Gas 配置
    gas_limit: Mapped[int] = mapped_column(Integer, default=21000)  # Gas 限制
    max_gas_price_gwei: Mapped[float] = mapped_column(Float, default=50.0)  # 最大 Gas 价格（Gwei）

    # 存证配置
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否启用
    auto_proof_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否自动存证
    batch_proof_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否批量存证

    # 业务类型配置（哪些业务类型需要存证）
    enabled_business_types: Mapped[Dict] = mapped_column(JSON, default=list)  # ["task_submitted", "payment_completed"]

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class BlockchainVerificationLogDB(Base):
    """区块链验证日志表。"""
    __tablename__ = "blockchain_verification_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proof_id: Mapped[str] = mapped_column(String(36), index=True)

    # 验证结果
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)  # 验证是否通过
    verification_result: Mapped[Dict] = mapped_column(JSON, default=dict)  # 验证结果详情

    # 验证方式：hash_compare, on_chain_verify, full_verify
    verification_method: Mapped[str] = mapped_column(String(50), default="hash_compare")

    # 验证时间
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    # 验证者
    verified_by: Mapped[str] = mapped_column(String(255), default="system")

    # 备注
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

