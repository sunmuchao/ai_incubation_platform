"""
P6 - 数据源扩展模块

新增数据源：
1. 政策数据 - 政府政策、补贴政策、产业政策
2. 供应链数据 - 供应商、客户关系、上下游产业链
3. 数据源健康监控增强
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import hashlib
import json
import os
import numpy as np

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """政策类型"""
    INDUSTRY_SUPPORT = "industry_support"  # 产业扶持政策
    TAX_INCENTIVE = "tax_incentive"  # 税收优惠
    SUBSIDY = "subsidy"  # 补贴政策
    REGULATORY_CHANGE = "regulatory_change"  # 监管政策变化
    INNOVATION_SUPPORT = "innovation_support"  # 创新支持政策
    TALENT_POLICY = "talent_policy"  # 人才政策
    FINANCING_SUPPORT = "financing_support"  # 融资支持
    REGIONAL_DEVELOPMENT = "regional_development"  # 区域发展政策


class PolicyLevel(Enum):
    """政策级别"""
    NATIONAL = "national"  # 国家级
    PROVINCIAL = "provincial"  # 省级
    MUNICIPAL = "municipal"  # 市级
    DISTRICT = "district"  # 区级


class SupplyChainRole(Enum):
    """供应链角色"""
    SUPPLIER = "supplier"  # 供应商
    MANUFACTURER = "manufacturer"  # 制造商
    DISTRIBUTOR = "distributor"  # 分销商
    RETAILER = "retailer"  # 零售商
    CUSTOMER = "customer"  # 客户
    LOGISTICS = "logistics"  # 物流服务商


class PolicyData:
    """政策数据模型"""

    def __init__(
        self,
        title: str,
        policy_type: PolicyType,
        level: PolicyLevel,
        region: str,
        industry: str,
        summary: str,
        content: str,
        publish_date: datetime,
        effective_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        issuing_body: str = "",
        document_number: str = "",
        source_url: str = "",
        tags: Optional[List[str]] = None
    ):
        self.id = self._generate_id(title, publish_date)
        self.title = title
        self.policy_type = policy_type
        self.level = level
        self.region = region
        self.industry = industry
        self.summary = summary
        self.content = content
        self.publish_date = publish_date
        self.effective_date = effective_date or publish_date
        self.expiry_date = expiry_date
        self.issuing_body = issuing_body
        self.document_number = document_number
        self.source_url = source_url
        self.tags = tags or []
        self.created_at = datetime.now()

    def _generate_id(self, title: str, date: datetime) -> str:
        """生成唯一 ID"""
        content = f"{title}_{date.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "policy_type": self.policy_type.value,
            "level": self.level.value,
            "region": self.region,
            "industry": self.industry,
            "summary": self.summary,
            "publish_date": self.publish_date.isoformat(),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "issuing_body": self.issuing_body,
            "document_number": self.document_number,
            "source_url": self.source_url,
            "tags": self.tags,
        }


class SupplyChainNode:
    """供应链节点模型"""

    def __init__(
        self,
        company_id: str,
        company_name: str,
        role: SupplyChainRole,
        industry: str,
        region: str,
        products: Optional[List[str]] = None,
        capacity: Optional[str] = None,
        certification: Optional[List[str]] = None,
        risk_level: str = "low",
        cooperation_history: Optional[List[Dict]] = None
    ):
        self.company_id = company_id
        self.company_name = company_name
        self.role = role
        self.industry = industry
        self.region = region
        self.products = products or []
        self.capacity = capacity
        self.certification = certification or []
        self.risk_level = risk_level
        self.cooperation_history = cooperation_history or []
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "role": self.role.value,
            "industry": self.industry,
            "region": self.region,
            "products": self.products,
            "capacity": self.capacity,
            "certification": self.certification,
            "risk_level": self.risk_level,
        }


class SupplyChainRelationship:
    """供应链关系模型"""

    def __init__(
        self,
        source_company: str,
        target_company: str,
        relationship_type: str,
        strength: float = 0.5,
        transaction_volume: Optional[float] = None,
        contract_period: Optional[Tuple[datetime, datetime]] = None,
        is_exclusive: bool = False,
        notes: str = ""
    ):
        self.id = f"{source_company}_{target_company}_{relationship_type}"
        self.source_company = source_company
        self.target_company = target_company
        self.relationship_type = relationship_type
        self.strength = strength  # 关系强度 0-1
        self.transaction_volume = transaction_volume  # 交易额
        self.contract_period = contract_period  # 合同期限
        self.is_exclusive = is_exclusive  # 是否独家
        self.notes = notes
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_company": self.source_company,
            "target_company": self.target_company,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "transaction_volume": self.transaction_volume,
            "contract_start": self.contract_period[0].isoformat() if self.contract_period else None,
            "contract_end": self.contract_period[1].isoformat() if self.contract_period else None,
            "is_exclusive": self.is_exclusive,
        }


class PolicyCrawler:
    """政策数据采集器"""

    # 模拟政策数据
    MOCK_POLICIES = [
        {
            "title": "关于促进人工智能产业发展的若干政策",
            "type": PolicyType.INDUSTRY_SUPPORT,
            "level": PolicyLevel.NATIONAL,
            "region": "中国",
            "industry": "人工智能",
            "summary": "支持人工智能核心技术研发，推动产业应用落地",
            "publish_date": datetime(2026, 3, 15),
            "issuing_body": "工业和信息化部",
        },
        {
            "title": "高新技术企业税收优惠政策",
            "type": PolicyType.TAX_INCENTIVE,
            "level": PolicyLevel.NATIONAL,
            "region": "中国",
            "industry": "高新技术",
            "summary": "高新技术企业享受 15% 企业所得税优惠税率",
            "publish_date": datetime(2026, 2, 1),
            "issuing_body": "国家税务总局",
        },
        {
            "title": "深圳市科技创新补贴政策",
            "type": PolicyType.SUBSIDY,
            "level": PolicyLevel.MUNICIPAL,
            "region": "深圳市",
            "industry": "科技",
            "summary": "对科技企业研发投入给予最高 500 万元补贴",
            "publish_date": datetime(2026, 3, 1),
            "issuing_body": "深圳市科技创新委员会",
        },
        {
            "title": "上海市人才引进优惠政策",
            "type": PolicyType.TALENT_POLICY,
            "level": PolicyLevel.MUNICIPAL,
            "region": "上海市",
            "industry": "通用",
            "summary": "为高端人才提供落户、住房、子女教育等支持",
            "publish_date": datetime(2026, 1, 15),
            "issuing_body": "上海市人力资源和社会保障局",
        },
        {
            "title": "中小企业融资支持政策",
            "type": PolicyType.FINANCING_SUPPORT,
            "level": PolicyLevel.NATIONAL,
            "region": "中国",
            "industry": "中小企业",
            "summary": "设立中小企业发展基金，提供贷款贴息支持",
            "publish_date": datetime(2026, 2, 20),
            "issuing_body": "中国人民银行",
        },
    ]

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key
        self.api_url = api_url
        self.cache = {}
        self.last_update = {}

    def fetch_policies(
        self,
        industry: Optional[str] = None,
        policy_type: Optional[PolicyType] = None,
        level: Optional[PolicyLevel] = None,
        region: Optional[str] = None,
        limit: int = 50
    ) -> List[PolicyData]:
        """
        获取政策数据

        Args:
            industry: 行业筛选
            policy_type: 政策类型筛选
            level: 政策级别筛选
            region: 地区筛选
            limit: 返回数量限制

        Returns:
            政策数据列表
        """
        cache_key = f"{industry}_{policy_type}_{level}_{region}_{limit}"

        # 检查缓存
        if cache_key in self.cache:
            cache_time = self.last_update.get(cache_key, datetime.now())
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info(f"使用缓存的政策数据：{cache_key}")
                return self.cache[cache_key]

        # 如果没有配置真实 API，使用模拟数据
        if not self.api_key:
            logger.info("使用模拟政策数据")
            policies = self._generate_mock_policies(
                industry=industry,
                policy_type=policy_type,
                level=level,
                region=region,
                limit=limit
            )
        else:
            # TODO: 实现真实 API 调用
            # 实际应调用政府开放数据 API
            policies = self._generate_mock_policies(
                industry=industry,
                policy_type=policy_type,
                level=level,
                region=region,
                limit=limit
            )

        # 更新缓存
        self.cache[cache_key] = policies
        self.last_update[cache_key] = datetime.now()

        return policies

    def _generate_mock_policies(
        self,
        industry: Optional[str],
        policy_type: Optional[PolicyType],
        level: Optional[PolicyLevel],
        region: Optional[str],
        limit: int
    ) -> List[PolicyData]:
        """生成模拟政策数据"""
        policies = []

        for mock in self.MOCK_POLICIES[:limit]:
            # 应用筛选
            if industry and mock.get("industry") != industry:
                continue
            if policy_type and mock.get("type") != policy_type:
                continue
            if region and mock.get("region") != region:
                continue

            policy = PolicyData(
                title=mock["title"],
                policy_type=mock["type"],
                level=mock["level"],
                region=mock["region"],
                industry=mock["industry"],
                summary=mock["summary"],
                content=f"{mock['summary']}。这是政策详细内容...",
                publish_date=mock["publish_date"],
                effective_date=mock["publish_date"] + timedelta(days=30),
                issuing_body=mock.get("issuing_body", ""),
                source_url=f"https://example.gov.cn/policy/{hash(mock['title']) % 10000}",
                tags=[mock["type"].value, mock["industry"], mock["level"].value]
            )
            policies.append(policy)

        return policies

    def search_policies(
        self,
        keywords: List[str],
        limit: int = 20
    ) -> List[PolicyData]:
        """
        搜索政策

        Args:
            keywords: 搜索关键词列表
            limit: 返回数量限制

        Returns:
            匹配的政策列表
        """
        cache_key = f"search_{'_'.join(keywords)}_{limit}"

        if cache_key in self.cache:
            cache_time = self.last_update.get(cache_key, datetime.now())
            if datetime.now() - cache_time < timedelta(hours=1):
                return self.cache[cache_key]

        # 简单关键词匹配
        all_policies = self.fetch_policies(limit=100)
        matched = []

        for policy in all_policies:
            score = 0
            text = f"{policy.title} {policy.summary} {' '.join(policy.tags)}".lower()

            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1

            if score > 0:
                matched.append((score, policy))

        # 按匹配度排序
        matched.sort(key=lambda x: x[0], reverse=True)
        result = [p for _, p in matched[:limit]]

        self.cache[cache_key] = result
        self.last_update[cache_key] = datetime.now()

        return result


class SupplyChainCrawler:
    """供应链数据采集器"""

    # 模拟供应链数据
    MOCK_COMPANIES = [
        {"name": "华为技术有限公司", "industry": "通信设备", "role": SupplyChainRole.MANUFACTURER},
        {"name": "富士康科技集团", "industry": "电子制造", "role": SupplyChainRole.MANUFACTURER},
        {"name": "台积电", "industry": "半导体", "role": SupplyChainRole.SUPPLIER},
        {"name": "高通公司", "industry": "芯片设计", "role": SupplyChainRole.SUPPLIER},
        {"name": "京东", "industry": "电商", "role": SupplyChainRole.DISTRIBUTOR},
        {"name": "顺丰速运", "industry": "物流", "role": SupplyChainRole.LOGISTICS},
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.nodes: Dict[str, SupplyChainNode] = {}
        self.relationships: Dict[str, SupplyChainRelationship] = {}

    def add_node(self, node: SupplyChainNode):
        """添加供应链节点"""
        self.nodes[node.company_id] = node

    def add_relationship(self, relationship: SupplyChainRelationship):
        """添加供应链关系"""
        self.relationships[relationship.id] = relationship

    def get_supply_chain(
        self,
        company_name: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        获取公司供应链图谱

        Args:
            company_name: 公司名称
            depth: 搜索深度

        Returns:
            供应链图谱数据
        """
        # 查找中心节点
        center_node = None
        for node in self.nodes.values():
            if node.company_name == company_name:
                center_node = node
                break

        if not center_node:
            # 创建默认节点
            center_node = SupplyChainNode(
                company_id=f"company_{hash(company_name) % 10000}",
                company_name=company_name,
                role=SupplyChainRole.MANUFACTURER,
                industry="通用",
                region="中国"
            )
            self.nodes[center_node.company_id] = center_node

        # 查找相关关系
        related_nodes = []
        related_relationships = []

        for rel in self.relationships.values():
            if rel.source_company == company_name or rel.target_company == company_name:
                related_relationships.append(rel.to_dict())

                # 获取另一端节点
                other_company = rel.target_company if rel.source_company == company_name else rel.source_company
                for node in self.nodes.values():
                    if node.company_name == other_company:
                        related_nodes.append(node.to_dict())
                        break

        # 如果没有关系，生成模拟数据
        if not related_relationships:
            related_nodes, related_relationships = self._generate_mock_supply_chain(
                company_name, depth
            )

        return {
            "center": center_node.to_dict(),
            "nodes": related_nodes,
            "relationships": related_relationships,
            "depth": depth,
        }

    def _generate_mock_supply_chain(
        self,
        company_name: str,
        depth: int
    ) -> Tuple[List[Dict], List[Dict]]:
        """生成模拟供应链数据"""
        nodes = []
        relationships = []

        # 基于公司类型生成不同的供应链
        if "华为" in company_name:
            # 华为供应链
            suppliers = [
                ("台积电", SupplyChainRole.SUPPLIER, "芯片代工"),
                ("高通", SupplyChainRole.SUPPLIER, "芯片供应"),
                ("京东方", SupplyChainRole.SUPPLIER, "屏幕供应"),
            ]
            distributors = [
                ("京东", SupplyChainRole.DISTRIBUTOR, "线上销售"),
                ("苏宁", SupplyChainRole.DISTRIBUTOR, "线下零售"),
            ]
        elif "小米" in company_name:
            suppliers = [
                ("富士康", SupplyChainRole.MANUFACTURER, "代工生产"),
                ("高通", SupplyChainRole.SUPPLIER, "芯片供应"),
            ]
            distributors = [
                ("小米之家", SupplyChainRole.RETAILER, "直营店"),
                ("天猫", SupplyChainRole.DISTRIBUTOR, "电商平台"),
            ]
        else:
            # 通用供应链
            suppliers = [
                ("供应商 A", SupplyChainRole.SUPPLIER, "原材料"),
                ("供应商 B", SupplyChainRole.SUPPLIER, "零部件"),
            ]
            distributors = [
                ("分销商 A", SupplyChainRole.DISTRIBUTOR, "区域分销"),
            ]

        # 添加供应商节点
        for name, role, relation in suppliers:
            node = SupplyChainNode(
                company_id=f"company_{hash(name) % 10000}",
                company_name=name,
                role=role,
                industry="制造业",
                region="中国"
            )
            nodes.append(node.to_dict())
            relationships.append(
                SupplyChainRelationship(
                    source_company=name,
                    target_company=company_name,
                    relationship_type="supply",
                    strength=0.8,
                    notes=relation
                ).to_dict()
            )

        # 添加分销商节点
        for name, role, relation in distributors:
            node = SupplyChainNode(
                company_id=f"company_{hash(name) % 10000}",
                company_name=name,
                role=role,
                industry="零售/分销",
                region="中国"
            )
            nodes.append(node.to_dict())
            relationships.append(
                SupplyChainRelationship(
                    source_company=company_name,
                    target_company=name,
                    relationship_type="distribution",
                    strength=0.7,
                    notes=relation
                ).to_dict()
            )

        return nodes, relationships

    def find_alternative_suppliers(
        self,
        current_supplier: str,
        product: str,
        region: Optional[str] = None
    ) -> List[SupplyChainNode]:
        """
        寻找替代供应商

        Args:
            current_supplier: 当前供应商
            product: 产品/服务
            region: 地区限制

        Returns:
            替代供应商列表
        """
        # 简单实现：返回同类型的其他供应商
        alternatives = []

        for node in self.nodes.values():
            if node.company_name != current_supplier and node.role == SupplyChainRole.SUPPLIER:
                if product.lower() in " ".join(node.products).lower():
                    if region is None or node.region == region:
                        alternatives.append(node)

        # 如果没有找到，返回模拟供应商
        if not alternatives:
            alternatives = [
                SupplyChainNode(
                    company_id=f"alt_{hash(product) % 10000}",
                    company_name=f"替代供应商_{hash(product) % 100}",
                    role=SupplyChainRole.SUPPLIER,
                    industry="制造业",
                    region=region or "中国",
                    products=[product]
                )
            ]

        return alternatives


class DataSourceHealthMonitor:
    """数据源健康监控器"""

    def __init__(self):
        self.health_records: Dict[str, Dict] = {}
        self.alert_thresholds = {
            "error_rate": 0.1,  # 错误率超过 10% 告警
            "latency_p99": 5.0,  # P99 延迟超过 5 秒告警
            "success_rate": 0.9,  # 成功率低于 90% 告警
        }

    def record_call(
        self,
        data_source: str,
        success: bool,
        latency: float,
        error_message: Optional[str] = None
    ):
        """记录数据源调用"""
        if data_source not in self.health_records:
            self.health_records[data_source] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "latencies": [],
                "errors": [],
                "last_success": None,
                "last_failure": None,
            }

        record = self.health_records[data_source]
        record["total_calls"] += 1

        if success:
            record["successful_calls"] += 1
            record["last_success"] = datetime.now()
        else:
            record["failed_calls"] += 1
            record["last_failure"] = datetime.now()
            if error_message:
                record["errors"].append({
                    "time": datetime.now().isoformat(),
                    "message": error_message
                })

        # 记录延迟（保留最近 100 次）
        record["latencies"].append(latency)
        if len(record["latencies"]) > 100:
            record["latencies"] = record["latencies"][-100:]

    def get_health_status(self, data_source: str) -> Dict[str, Any]:
        """获取数据源健康状态"""
        if data_source not in self.health_records:
            return {
                "status": "unknown",
                "message": "无调用记录"
            }

        record = self.health_records[data_source]
        total = record["total_calls"]

        if total == 0:
            return {
                "status": "unknown",
                "message": "无调用记录"
            }

        # 计算指标
        success_rate = record["successful_calls"] / total
        error_rate = record["failed_calls"] / total

        latencies = record["latencies"]
        avg_latency = np.mean(latencies) if latencies else 0
        p99_latency = np.percentile(latencies, 99) if latencies else 0

        # 判断状态
        if error_rate > self.alert_thresholds["error_rate"]:
            status = "unhealthy"
        elif success_rate < self.alert_thresholds["success_rate"]:
            status = "degraded"
        elif p99_latency > self.alert_thresholds["latency_p99"]:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_calls": total,
            "success_rate": round(success_rate, 4),
            "error_rate": round(error_rate, 4),
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "p99_latency_ms": round(p99_latency * 1000, 2),
            "last_success": record["last_success"].isoformat() if record["last_success"] else None,
            "last_failure": record["last_failure"].isoformat() if record["last_failure"] else None,
            "recent_errors": record["errors"][-5:]  # 最近 5 次错误
        }

    def get_all_health_status(self) -> Dict[str, Dict]:
        """获取所有数据源健康状态"""
        return {
            ds: self.get_health_status(ds)
            for ds in self.health_records
        }

    def check_alerts(self) -> List[Dict]:
        """检查是否需要告警"""
        alerts = []

        for data_source, status in self.get_all_health_status().items():
            if status["status"] in ["unhealthy", "degraded"]:
                alerts.append({
                    "data_source": data_source,
                    "status": status["status"],
                    "time": datetime.now().isoformat(),
                    "details": status
                })

        return alerts


# 全局单例
policy_crawler = PolicyCrawler()
supply_chain_crawler = SupplyChainCrawler()
health_monitor = DataSourceHealthMonitor()
