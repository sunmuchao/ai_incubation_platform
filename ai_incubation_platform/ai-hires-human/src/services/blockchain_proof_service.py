"""
区块链存证服务。
提供数据哈希计算、区块链写入、验证等功能。
"""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.blockchain_proof import BlockchainProofDB, BlockchainConfigDB, BlockchainVerificationLogDB

logger = logging.getLogger(__name__)


class BlockchainProofService:
    """区块链存证服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_cache: Optional[BlockchainConfigDB] = None

    async def _get_active_config(self) -> Optional[BlockchainConfigDB]:
        """获取激活的区块链配置。"""
        if self.config_cache and self.config_cache.is_active:
            return self.config_cache

        result = await self.db.execute(
            select(BlockchainConfigDB).where(BlockchainConfigDB.is_active == True)
        )
        config = result.scalar_one_or_none()
        if config:
            self.config_cache = config
        return config

    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        计算数据的 SHA256 哈希。

        Args:
            data: 要哈希的数据字典

        Returns:
            64 字符的十六进制哈希字符串
        """
        # 标准化 JSON 格式（排序键，确保一致性）
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def extract_data_summary(self, data: Dict[str, Any], business_type: str) -> Dict[str, Any]:
        """
        提取数据摘要（用于存证，不包含敏感信息）。

        Args:
            data: 原始数据
            business_type: 业务类型

        Returns:
            数据摘要字典
        """
        summary = {
            "business_type": business_type,
            "timestamp": data.get("created_at", data.get("submitted_at", datetime.now().isoformat())),
        }

        # 根据业务类型提取关键字段
        if business_type == "task_created":
            summary.update({
                "task_id": data.get("id", data.get("task_id")),
                "ai_employer_id": data.get("ai_employer_id"),
                "title": data.get("title"),
                "reward_amount": data.get("reward_amount"),
                "interaction_type": data.get("interaction_type"),
            })
        elif business_type == "task_submitted":
            summary.update({
                "task_id": data.get("id", data.get("task_id")),
                "worker_id": data.get("worker_id"),
                "submitted_at": data.get("submitted_at"),
                "delivery_content_preview": self._safe_preview(data.get("delivery_content")),
            })
        elif business_type in ("task_accepted", "task_rejected"):
            summary.update({
                "task_id": data.get("id", data.get("task_id")),
                "worker_id": data.get("worker_id"),
                "ai_employer_id": data.get("ai_employer_id"),
                "status": data.get("status"),
            })
        elif business_type == "payment_completed":
            summary.update({
                "transaction_id": data.get("id", data.get("transaction_id")),
                "task_id": data.get("task_id"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "payee_id": data.get("payee_id"),
            })
        elif business_type == "escrow_released":
            summary.update({
                "escrow_id": data.get("id", data.get("escrow_id")),
                "task_id": data.get("task_id"),
                "amount": data.get("principal_amount"),
                "worker_id": data.get("worker_id"),
            })
        elif business_type == "dispute_resolved":
            summary.update({
                "task_id": data.get("id", data.get("task_id")),
                "resolution": data.get("dispute_resolution"),
                "resolved_at": data.get("resolved_at"),
            })

        return summary

    def _safe_preview(self, content: Optional[str], max_length: int = 100) -> Optional[str]:
        """安全的内容预览（截断并脱敏）。"""
        if not content:
            return None
        content = str(content)
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    async def create_proof(
        self,
        business_type: str,
        business_id: str,
        data: Dict[str, Any],
        created_by: str = "system"
    ) -> BlockchainProofDB:
        """
        创建区块链存证。

        Args:
            business_type: 业务类型
            business_id: 业务 ID
            data: 要存证的原始数据
            created_by: 创建者

        Returns:
            存证记录
        """
        proof_id = str(uuid.uuid4())
        data_hash = self.calculate_data_hash(data)
        data_summary = self.extract_data_summary(data, business_type)

        proof = BlockchainProofDB(
            id=proof_id,
            proof_id=proof_id,
            business_type=business_type,
            business_id=business_id,
            data_hash=data_hash,
            data_summary=data_summary,
            status="pending",
            created_by=created_by,
        )

        self.db.add(proof)
        await self.db.commit()
        await self.db.refresh(proof)

        logger.info(f"创建区块链存证：proof_id={proof_id}, business_type={business_type}, business_id={business_id}")

        return proof

    async def submit_to_blockchain(self, proof: BlockchainProofDB) -> bool:
        """
        将存证提交到区块链。

        注意：这是模拟实现，实际生产环境需要：
        1. 集成 web3.py 库
        2. 连接真实的区块链节点
        3. 调用智能合约写入数据

        Args:
            proof: 存证记录

        Returns:
            是否成功提交
        """
        config = await self._get_active_config()
        if not config:
            logger.warning("没有激活的区块链配置，跳过上链")
            # 模拟成功（开发/测试模式）
            proof.status = "confirmed"
            proof.transaction_hash = "0x" + hashlib.sha256(proof.id.encode()).hexdigest()
            proof.block_number = 1000000 + hash(proof.id) % 100000
            proof.confirmed_at = datetime.now()
            await self.db.commit()
            return True

        try:
            # TODO: 实际生产环境实现 web3 调用
            # from web3 import Web3
            # w3 = Web3(Web3.HTTPProvider(config.rpc_url))
            # contract = w3.eth.contract(address=config.contract_address, abi=config.contract_abi)
            # tx_hash = await contract.functions.storeProof(
            #     proof.data_hash,
            #     proof.business_type,
            #     proof.business_id
            # ).transact({'from': config.wallet_address})

            # 模拟交易哈希
            simulated_tx_hash = "0x" + hashlib.sha256(
                f"{proof.id}{datetime.now().isoformat()}".encode()
            ).hexdigest()

            proof.transaction_hash = simulated_tx_hash
            proof.blockchain_network = config.network
            proof.block_number = 1000000 + hash(proof.id) % 100000
            proof.contract_address = config.contract_address
            proof.status = "confirmed"
            proof.confirmed_at = datetime.now()
            proof.gas_fee = 0.001  # 模拟 gas 费用
            proof.gas_fee_cny = 0.02  # 模拟 CNY 计价

            await self.db.commit()

            logger.info(f"存证上链成功：proof_id={proof.id}, tx_hash={simulated_tx_hash}")
            return True

        except Exception as e:
            logger.error(f"存证上链失败：proof_id={proof.id}, error={str(e)}")
            proof.status = "failed"
            await self.db.commit()
            return False

    async def verify_proof(self, proof_id: str, original_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        验证存证。

        Args:
            proof_id: 存证 ID
            original_data: 可选的原始数据，用于比对哈希

        Returns:
            验证结果
        """
        result = await self.db.execute(
            select(BlockchainProofDB).where(BlockchainProofDB.proof_id == proof_id)
        )
        proof = result.scalar_one_or_none()

        if not proof:
            return {
                "valid": False,
                "error": "存证不存在",
                "proof_id": proof_id
            }

        verification_result = {
            "valid": True,
            "proof_id": proof_id,
            "business_type": proof.business_type,
            "business_id": proof.business_id,
            "data_hash": proof.data_hash,
            "blockchain_network": proof.blockchain_network,
            "transaction_hash": proof.transaction_hash,
            "block_number": proof.block_number,
            "confirmed_at": proof.confirmed_at.isoformat() if proof.confirmed_at else None,
        }

        # 如果提供了原始数据，验证哈希是否匹配
        if original_data:
            computed_hash = self.calculate_data_hash(original_data)
            if computed_hash != proof.data_hash:
                verification_result["valid"] = False
                verification_result["error"] = "数据哈希不匹配，数据可能已被篡改"
            else:
                verification_result["hash_verified"] = True

        # 模拟链上验证（实际生产环境需要调用区块链 RPC）
        if proof.transaction_hash:
            verification_result["on_chain_verified"] = True
            verification_result["explorer_url"] = f"https://explorer.example.com/tx/{proof.transaction_hash}"

        # 更新验证日志
        await self._log_verification(proof_id, verification_result["valid"], verification_result)

        # 更新验证计数
        proof.verification_count += 1
        proof.last_verified_at = datetime.now()
        await self.db.commit()

        return verification_result

    async def _log_verification(
        self,
        proof_id: str,
        is_valid: bool,
        result: Dict[str, Any],
        method: str = "hash_compare"
    ):
        """记录验证日志。"""
        log = BlockchainVerificationLogDB(
            id=str(uuid.uuid4()),
            proof_id=proof_id,
            is_valid=is_valid,
            verification_result=result,
            verification_method=method,
        )
        self.db.add(log)
        await self.db.commit()

    async def batch_create_proofs(
        self,
        proofs_data: List[Dict[str, Any]],
        created_by: str = "system"
    ) -> List[BlockchainProofDB]:
        """
        批量创建存证。

        Args:
            proofs_data: 存证数据列表，每项包含 business_type, business_id, data
            created_by: 创建者

        Returns:
            存证记录列表
        """
        proofs = []
        for item in proofs_data:
            proof = await self.create_proof(
                business_type=item["business_type"],
                business_id=item["business_id"],
                data=item["data"],
                created_by=created_by,
            )
            proofs.append(proof)

        logger.info(f"批量创建 {len(proofs)} 个存证")
        return proofs

    async def get_proof_by_business_id(
        self,
        business_type: str,
        business_id: str
    ) -> Optional[BlockchainProofDB]:
        """根据业务 ID 获取存证。"""
        result = await self.db.execute(
            select(BlockchainProofDB).where(
                BlockchainProofDB.business_type == business_type,
                BlockchainProofDB.business_id == business_id
            )
        )
        return result.scalar_one_or_none()

    async def get_proofs_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[BlockchainProofDB]:
        """获取用户的存证列表。"""
        # 这里简化实现，实际应该根据业务 ID 关联查询
        result = await self.db.execute(
            select(BlockchainProofDB)
            .where(BlockchainProofDB.created_by == user_id)
            .order_by(BlockchainProofDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_statistics(self) -> Dict[str, Any]:
        """获取存证统计信息。"""
        from sqlalchemy import func

        # 总存证数
        total_result = await self.db.execute(select(func.count(BlockchainProofDB.id)))
        total_count = total_result.scalar() or 0

        # 按状态统计
        status_result = await self.db.execute(
            select(BlockchainProofDB.status, func.count(BlockchainProofDB.id))
            .group_by(BlockchainProofDB.status)
        )
        status_stats = {row[0]: row[1] for row in status_result.all()}

        # 按业务类型统计
        type_result = await self.db.execute(
            select(BlockchainProofDB.business_type, func.count(BlockchainProofDB.id))
            .group_by(BlockchainProofDB.business_type)
        )
        type_stats = {row[0]: row[1] for row in type_result.all()}

        # 今日新增
        today = datetime.now().date()
        today_result = await self.db.execute(
            select(func.count(BlockchainProofDB.id)).where(
                func.date(BlockchainProofDB.created_at) == today
            )
        )
        today_count = today_result.scalar() or 0

        return {
            "total_count": total_count,
            "status_stats": status_stats,
            "type_stats": type_stats,
            "today_count": today_count,
        }


# 全局服务实例（用于依赖注入）
blockchain_proof_service_instance: Optional[BlockchainProofService] = None


def get_blockchain_proof_service(db: AsyncSession) -> BlockchainProofService:
    """获取区块链存证服务实例。"""
    return BlockchainProofService(db)
