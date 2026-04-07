"""
图谱构建器
从文本中自动抽取实体和关系，构建知识图谱
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import re
import logging
from models.graph import (
    KnowledgeGraph, GraphEntity, GraphRelation,
    EntityType, RelationType, knowledge_graph
)
from nlp.text_analyzer import text_analyzer
from nlp.event_detector import event_detector, EventType, BusinessEvent

logger = logging.getLogger(__name__)


class GraphBuilder:
    """图谱构建器"""

    def __init__(self):
        self.text_analyzer = text_analyzer
        self.event_detector = event_detector
        self.graph = knowledge_graph

        # 实体提取规则
        self.entity_rules = {
            EntityType.COMPANY: {
                "patterns": [
                    re.compile(r'([^\s，。；：]+)(股份 | 有限责任 | 集团 | 公司 | 企业)'),
                    re.compile(r'([^\s，。；：]+)(科技 | 网络 | 智能 | 数据 | 系统)'),
                ],
                "keywords": ["公司", "企业", "集团", "股份", "有限"]
            },
            EntityType.PERSON: {
                "patterns": [
                    re.compile(r'([^\s，。；：]+)(先生 | 女士 | 博士 | 教授 |CEO| 董事长 | 总经理 | 总裁 | 创始人)'),
                ],
                "keywords": ["先生", "女士", "博士", "CEO", "董事长", "总经理", "总裁", "创始人"]
            },
            EntityType.PRODUCT: {
                "patterns": [
                    re.compile(r'([^\s，。；：]+)(产品 | 系统 | 平台 | 解决方案 | 服务 | App| 软件)'),
                ],
                "keywords": ["产品", "系统", "平台", "解决方案", "App"]
            },
            EntityType.INVESTOR: {
                "patterns": [
                    re.compile(r'([^\s，。；：]+)(资本 | 创投 | 投资 | 基金 | 合伙)'),
                ],
                "keywords": ["资本", "创投", "投资", "基金", "VC", "PE"]
            }
        }

        # 关系抽取规则
        self.relation_rules = {
            RelationType.INVESTED_IN: {
                "patterns": [
                    re.compile(r'(\S+)\s*(领投 | 跟投 | 投资 | 入股)\s*(\S+)'),
                    re.compile(r'(\S+)\s*获得\s*(\S+)\s*投资'),
                ],
                "events": [EventType.FUNDING, EventType.INVESTMENT]
            },
            RelationType.ACQUIRED: {
                "patterns": [
                    re.compile(r'(\S+)\s*(收购 | 并购 | 控股)\s*(\S+)'),
                    re.compile(r'(\S+)\s*被\s*(\S+)\s*收购'),
                ],
                "events": [EventType.ACQUISITION]
            },
            RelationType.FOUNDED_BY: {
                "patterns": [
                    re.compile(r'(\S+)\s*创始人\s*(\S+)'),
                    re.compile(r'(\S+)\s*由\s*(\S+)\s*创立'),
                ],
                "events": []
            },
            RelationType.CEO_OF: {
                "patterns": [
                    re.compile(r'(\S+)\s*(CEO| 董事长 | 总裁 | 总经理)\s*(\S+)'),
                ],
                "events": [EventType.EXECUTIVE_CHANGE]
            },
            RelationType.PARTNERSHIP_WITH: {
                "patterns": [
                    re.compile(r'(\S+)\s*与\s*(\S+)\s*(战略合作 | 达成合作 | 签署协议)'),
                    re.compile(r'(\S+)\s*联合\s*(\S+)'),
                ],
                "events": [EventType.PARTNERSHIP]
            },
            RelationType.COMPETES_WITH: {
                "patterns": [
                    re.compile(r'(\S+)\s*与\s*(\S+)\s*竞争'),
                    re.compile(r'(\S+)\s*是\s*(\S+)\s*的竞争对手'),
                ],
                "events": []
            },
            RelationType.OWNS_PRODUCT: {
                "patterns": [
                    re.compile(r'(\S+)\s*(发布 | 推出 | 发布)\s*(\S+)\s*(产品 | 系统 | 平台)'),
                ],
                "events": [EventType.PRODUCT_LAUNCH]
            }
        }

    def build_from_text(self, text: str, source: str = "", source_url: str = "") -> Tuple[List[GraphEntity], List[GraphRelation]]:
        """从单个文本构建图谱"""
        entities = []
        relations = []

        # 1. 提取实体
        for entity_type, rules in self.entity_rules.items():
            extracted = self._extract_entities_by_type(text, entity_type, rules)
            entities.extend(extracted)

        # 2. 提取关系
        for relation_type, rules in self.relation_rules.items():
            extracted = self._extract_relations_by_type(text, relation_type, rules, entities)
            relations.extend(extracted)

        # 3. 从事件中提取
        events = self.event_detector.detect_events(text, {"source": source, "source_url": source_url})
        event_entities, event_relations = self._extract_from_events(events)
        entities.extend(event_entities)
        relations.extend(event_relations)

        # 4. 添加到图谱
        for entity in entities:
            # 检查是否已存在
            existing = self.graph.get_entity_by_name(entity.name)
            if not existing:
                self.graph.add_entity(entity)

        for relation in relations:
            self.graph.add_relation(relation)

        return entities, relations

    def build_from_articles(self, articles: List[Dict]) -> Dict:
        """从文章列表构建图谱"""
        total_entities = 0
        total_relations = 0
        entity_sources = {}

        for article in articles:
            text = article.get("content", "") or article.get("summary", "")
            if not text:
                continue

            source = article.get("source", "") or article.get("publisher", "")
            url = article.get("url", "")

            entities, relations = self.build_from_text(text, source, url)
            total_entities += len(entities)
            total_relations += len(relations)

            # 统计来源
            for entity in entities:
                if source not in entity_sources:
                    entity_sources[source] = 0
                entity_sources[source] += 1

        return {
            "total_entities": total_entities,
            "total_relations": total_relations,
            "entity_sources": entity_sources,
            "graph_statistics": self.graph.to_dict()["statistics"]
        }

    def _extract_entities_by_type(
        self,
        text: str,
        entity_type: EntityType,
        rules: Dict
    ) -> List[GraphEntity]:
        """按类型提取实体"""
        entities = []
        seen_names = set()

        for pattern in rules["patterns"]:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0] + match[1]
                else:
                    name = match

                # 过滤太短或太长的名称
                if len(name) < 2 or len(name) > 50:
                    continue

                # 去重
                if name in seen_names:
                    continue
                seen_names.add(name)

                entity = GraphEntity(
                    entity_type=entity_type.value,
                    name=name,
                    description=f"从文本中提取的{entity_type.value}实体",
                    source="text_extraction",
                    confidence=0.7
                )
                entities.append(entity)

        return entities

    def _extract_relations_by_type(
        self,
        text: str,
        relation_type: RelationType,
        rules: Dict,
        known_entities: List[GraphEntity]
    ) -> List[GraphRelation]:
        """按类型提取关系"""
        relations = []

        for pattern in rules["patterns"]:
            matches = pattern.findall(text)
            for match in matches:
                if not isinstance(match, tuple) or len(match) < 2:
                    continue

                entity1_name = match[0]
                entity2_name = match[1]

                # 尝试匹配已知实体
                entity1 = self._find_or_create_entity(entity1_name, known_entities)
                entity2 = self._find_or_create_entity(entity2_name, known_entities)

                if entity1 and entity2:
                    relation = GraphRelation(
                        from_entity_id=entity1.id,
                        to_entity_id=entity2.id,
                        relation_type=relation_type.value,
                        source="text_extraction",
                        confidence=0.7
                    )
                    relations.append(relation)

        return relations

    def _find_or_create_entity(
        self,
        name: str,
        known_entities: List[GraphEntity]
    ) -> Optional[GraphEntity]:
        """查找或创建实体"""
        # 先在已知实体中查找
        for entity in known_entities:
            if entity.name == name or name in entity.aliases:
                return entity

        # 在图谱中查找
        existing = self.graph.get_entity_by_name(name)
        if existing:
            return existing

        # 创建新实体（默认为公司）
        entity = GraphEntity(
            entity_type=EntityType.COMPANY.value,
            name=name,
            description="从关系中提取的实体",
            source="relation_extraction",
            confidence=0.6
        )
        self.graph.add_entity(entity)
        return entity

    def _extract_from_events(
        self,
        events: List[BusinessEvent]
    ) -> Tuple[List[GraphEntity], List[GraphRelation]]:
        """从事件中提取实体和关系"""
        entities = []
        relations = []

        for event in events:
            # 为公司创建实体
            for company_name in event.companies:
                existing = self.graph.get_entity_by_name(company_name)
                if not existing:
                    entity = GraphEntity(
                        entity_type=EntityType.COMPANY.value,
                        name=company_name,
                        description=f"从事件{event.event_type}中提取",
                        source=event.source,
                        properties={
                            "last_event_type": event.event_type,
                            "last_event_date": event.publish_date.isoformat() if event.publish_date else None
                        }
                    )
                    entities.append(entity)

            # 根据事件类型创建关系
            if event.event_type == EventType.FUNDING and event.companies:
                # 假设有投资方（从 extra 中提取）
                investor_name = event.extra.get("investor", "未知投资方")
                investor = GraphEntity(
                    entity_type=EntityType.INVESTOR.value,
                    name=investor_name,
                    source=event.source
                )
                entities.append(investor)

                relation = GraphRelation(
                    from_entity_id=investor.id,
                    to_entity_id=self._get_entity_id(event.companies[0], entities),
                    relation_type=RelationType.INVESTED_IN.value,
                    properties={
                        "amount": event.amount,
                        "currency": event.currency,
                        "event_date": event.publish_date.isoformat() if event.publish_date else None
                    },
                    source=event.source,
                    confidence=event.confidence
                )
                relations.append(relation)

            elif event.event_type == EventType.ACQUISITION and len(event.companies) >= 2:
                relation = GraphRelation(
                    from_entity_id=self._get_entity_id(event.companies[0], entities),
                    to_entity_id=self._get_entity_id(event.companies[1], entities),
                    relation_type=RelationType.ACQUIRED.value,
                    properties={
                        "amount": event.amount,
                        "event_date": event.publish_date.isoformat() if event.publish_date else None
                    },
                    source=event.source,
                    confidence=event.confidence
                )
                relations.append(relation)

            elif event.event_type == EventType.PARTNERSHIP and len(event.companies) >= 2:
                relation = GraphRelation(
                    from_entity_id=self._get_entity_id(event.companies[0], entities),
                    to_entity_id=self._get_entity_id(event.companies[1], entities),
                    relation_type=RelationType.PARTNERSHIP_WITH.value,
                    properties={
                        "event_date": event.publish_date.isoformat() if event.publish_date else None
                    },
                    source=event.source,
                    confidence=event.confidence
                )
                relations.append(relation)

        return entities, relations

    def _get_entity_id(self, name: str, entities: List[GraphEntity]) -> str:
        """获取实体 ID"""
        # 先在临时实体列表中查找
        for entity in entities:
            if entity.name == name:
                return entity.id

        # 在图谱中查找
        existing = self.graph.get_entity_by_name(name)
        if existing:
            return existing.id

        # 创建新实体
        new_entity = GraphEntity(
            entity_type=EntityType.COMPANY.value,
            name=name,
            source="event_extraction"
        )
        self.graph.add_entity(new_entity)
        return new_entity.id

    def get_graph_summary(self) -> Dict:
        """获取图谱摘要"""
        return self.graph.to_dict()

    def query_companies_by_industry(self, industry: str) -> List[Dict]:
        """按行业查询公司"""
        results = []
        for entity in self.graph.find_entities(tags=[industry]):
            if EntityType(entity.entity_type) == EntityType.COMPANY:
                results.append(entity.to_dict())
        return results

    def get_company_competitors(self, company_name: str) -> List[Dict]:
        """获取公司竞争对手"""
        return self.graph.get_competitors(company_name)

    def get_company_profile(self, company_name: str) -> Dict:
        """获取公司档案"""
        return self.graph.get_company_profile(company_name)


# 全局单例
graph_builder = GraphBuilder()
