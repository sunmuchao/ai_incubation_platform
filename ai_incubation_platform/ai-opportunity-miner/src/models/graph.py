"""
关系图谱模型
定义公司、人、产品等实体及其关系的图结构
参考 CB Insights 的知识图谱能力
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from enum import Enum
import uuid


class EntityType(str, Enum):
    """实体类型"""
    COMPANY = "company"  # 公司
    PERSON = "person"  # 人物
    PRODUCT = "product"  # 产品
    INVESTOR = "investor"  # 投资机构/人
    INDUSTRY = "industry"  # 行业
    TECHNOLOGY = "technology"  # 技术
    EVENT = "event"  # 事件


class RelationType(str, Enum):
    """关系类型"""
    # 投资关系
    INVESTED_IN = "invested_in"  # 投资于
    FUNDED_BY = "funded_by"  # 被投资
    ACQUIRED = "acquired"  # 收购
    ACQUIRED_BY = "acquired_by"  # 被收购

    # 人事关系
    FOUNDED_BY = "founded_by"  # 创始人
    EMPLOYS = "employs"  # 雇佣
    WORKS_AT = "works_at"  # 任职于
    CEO_OF = "ceo_of"  # CEO

    # 竞争关系
    COMPETES_WITH = "competes_with"  # 竞争对手

    # 合作关系
    PARTNERSHIP_WITH = "partnership_with"  # 合作伙伴
    SUPPLIES_TO = "supplies_to"  # 供应给
    CUSTOMER_OF = "customer_of"  # 客户

    # 产品/技术关系
    OWNS_PRODUCT = "owns_product"  # 拥有产品
    DEVELOPS_TECHNOLOGY = "develops_technology"  # 开发技术
    USES_TECHNOLOGY = "uses_technology"  # 使用技术

    # 行业关系
    BELONGS_TO_INDUSTRY = "belongs_to_industry"  # 属于行业
    FOCUSES_ON = "focuses_on"  # 专注于


class GraphEntity(BaseModel):
    """图谱实体"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: EntityType
    name: str
    description: str = ""

    # 属性（动态扩展）
    properties: Dict[str, Any] = Field(default_factory=dict)

    # 元数据
    source: str = ""
    source_url: str = ""
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 索引字段（用于快速查询）
    aliases: List[str] = Field(default_factory=list)  # 别名
    tags: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    def add_property(self, key: str, value: Any):
        """添加属性"""
        self.properties[key] = value
        self.updated_at = datetime.now()

    def add_alias(self, alias: str):
        """添加别名"""
        if alias not in self.aliases:
            self.aliases.append(alias)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "source": self.source,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "aliases": self.aliases,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class GraphRelation(BaseModel):
    """图谱关系"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 关系两端
    from_entity_id: str
    to_entity_id: str
    relation_type: RelationType

    # 关系属性
    properties: Dict[str, Any] = Field(default_factory=dict)

    # 关系强度/置信度
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    weight: float = Field(1.0, ge=0.0, le=1.0)

    # 时间信息（如投资日期、合作开始时间等）
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 来源
    source: str = ""
    source_url: str = ""

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "confidence": self.confidence,
            "weight": self.weight,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat()
        }


class KnowledgeGraph:
    """知识图谱（内存实现，可替换为 Neo4j 等图数据库）"""

    def __init__(self):
        self.entities: Dict[str, GraphEntity] = {}
        self.relations: List[GraphRelation] = []

        # 索引
        self.name_to_id: Dict[str, str] = {}  # 名称->ID
        self.aliases_to_id: Dict[str, str] = {}  # 别名->ID
        self.entity_type_index: Dict[EntityType, Set[str]] = {}  # 类型->ID 集合

    def add_entity(self, entity: GraphEntity) -> str:
        """添加实体"""
        self.entities[entity.id] = entity

        # 建立索引
        self.name_to_id[entity.name.lower()] = entity.id
        for alias in entity.aliases:
            self.aliases_to_id[alias.lower()] = entity.id

        # 类型索引
        entity_type = EntityType(entity.entity_type)
        if entity_type not in self.entity_type_index:
            self.entity_type_index[entity_type] = set()
        self.entity_type_index[entity_type].add(entity.id)

        return entity.id

    def add_relation(self, relation: GraphRelation):
        """添加关系"""
        self.relations.append(relation)

    def get_entity_by_id(self, entity_id: str) -> Optional[GraphEntity]:
        """通过 ID 获取实体"""
        return self.entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Optional[GraphEntity]:
        """通过名称获取实体"""
        entity_id = self.name_to_id.get(name.lower()) or self.aliases_to_id.get(name.lower())
        if entity_id:
            return self.entities.get(entity_id)
        return None

    def find_entities(self, entity_type: Optional[EntityType] = None, tags: Optional[List[str]] = None) -> List[GraphEntity]:
        """查找实体"""
        results = []

        for entity_id, entity in self.entities.items():
            # 类型过滤
            if entity_type and EntityType(entity.entity_type) != entity_type:
                continue

            # 标签过滤
            if tags and not any(tag in entity.tags for tag in tags):
                continue

            results.append(entity)

        return results

    def get_relations(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Dict]:
        """获取实体的关系（包含关联实体信息）"""
        results = []

        for relation in self.relations:
            if relation.from_entity_id != entity_id and relation.to_entity_id != entity_id:
                continue

            if relation_type and RelationType(relation.relation_type) != relation_type:
                continue

            # 获取关联实体
            other_id = relation.to_entity_id if relation.from_entity_id == entity_id else relation.from_entity_id
            other_entity = self.get_entity_by_id(other_id)

            results.append({
                "relation": relation.to_dict(),
                "related_entity": other_entity.to_dict() if other_entity else None
            })

        return results

    def find_path(self, from_entity_id: str, to_entity_id: str, max_depth: int = 3) -> List[List[str]]:
        """查找两个实体之间的路径（BFS）"""
        if from_entity_id not in self.entities or to_entity_id not in self.entities:
            return []

        # BFS
        queue = [(from_entity_id, [from_entity_id])]
        visited = {from_entity_id}
        paths = []

        while queue and len(paths) < 5:  # 最多返回 5 条路径
            current_id, path = queue.pop(0)

            if current_id == to_entity_id:
                paths.append(path)
                continue

            if len(path) > max_depth:
                continue

            # 查找相邻节点
            for relation in self.relations:
                neighbor_id = None
                if relation.from_entity_id == current_id:
                    neighbor_id = relation.to_entity_id
                elif relation.to_entity_id == current_id:
                    neighbor_id = relation.from_entity_id

                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return paths

    def get_company_profile(self, company_name: str) -> Dict:
        """获取公司档案（类似 CB Insights 的公司页面）"""
        company = self.get_entity_by_name(company_name)
        if not company:
            return {}

        # 获取所有关系
        relations = self.get_relations(company.id)

        # 分类关系
        investors = []
        investments = []
        competitors = []
        partners = []
        products = []
        executives = []

        for item in relations:
            relation = item["relation"]
            entity = item["related_entity"]
            if not entity:
                continue

            rel_type = relation["relation_type"]

            if rel_type == RelationType.INVESTED_IN.value:
                investors.append(entity)
            elif rel_type == RelationType.FUNDED_BY.value:
                investments.append(entity)
            elif rel_type == RelationType.COMPETES_WITH.value:
                competitors.append(entity)
            elif rel_type == RelationType.PARTNERSHIP_WITH.value:
                partners.append(entity)
            elif rel_type == RelationType.OWNS_PRODUCT.value:
                products.append(entity)
            elif rel_type in [RelationType.FOUNDED_BY.value, RelationType.CEO_OF.value, RelationType.EMPLOYS.value]:
                executives.append(entity)

        return {
            "company": company.to_dict(),
            "investors": investors,
            "investments": investments,
            "competitors": competitors,
            "partners": partners,
            "products": products,
            "executives": executives,
            "statistics": {
                "total_relations": len(relations),
                "investor_count": len(investors),
                "investment_count": len(investments),
                "competitor_count": len(competitors),
                "partner_count": len(partners),
            }
        }

    def get_competitors(self, company_name: str, depth: int = 2) -> List[Dict]:
        """获取竞争对手（直接和间接）"""
        company = self.get_entity_by_name(company_name)
        if not company:
            return []

        competitors = []
        seen = set()

        # 直接竞争对手
        for item in self.get_relations(company.id, RelationType.COMPETES_WITH):
            entity = item["related_entity"]
            if entity and entity["id"] not in seen:
                seen.add(entity["id"])
                competitors.append(entity)

        # 间接竞争对手（竞争对手的竞争对手）
        if depth > 1:
            for competitor in competitors[:]:
                for item in self.get_relations(competitor["id"], RelationType.COMPETES_WITH):
                    entity = item["related_entity"]
                    if entity and entity["id"] not in seen and entity["id"] != company.id:
                        seen.add(entity["id"])
                        competitors.append(entity)

        return competitors

    def get_investment_chain(self, company_name: str) -> List[Dict]:
        """获取投资链（投资方和被投资公司）"""
        company = self.get_entity_by_name(company_name)
        if not company:
            return []

        chain = {
            "company": company.to_dict(),
            "investors": [],
            "portfolio_companies": []
        }

        # 投资方
        for item in self.get_relations(company.id, RelationType.FUNDED_BY):
            entity = item["related_entity"]
            if entity:
                chain["investors"].append(entity)

        # 被投资公司（如果这是一个投资机构）
        for item in self.get_relations(company.id, RelationType.INVESTED_IN):
            entity = item["related_entity"]
            if entity:
                chain["portfolio_companies"].append(entity)

        return chain

    def to_dict(self) -> Dict:
        """导出图谱数据"""
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations],
            "statistics": {
                "entity_count": len(self.entities),
                "relation_count": len(self.relations),
                "by_type": {
                    et.value: len(ids) for et, ids in self.entity_type_index.items()
                }
            }
        }


# 全局图谱实例
knowledge_graph = KnowledgeGraph()
