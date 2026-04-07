"""
数据血缘与影响分析模块

实现完整的数据血缘追踪、影响分析功能，并提供与代码理解服务的数据字典协作接口。

核心功能：
1. SQL 解析与血缘提取：从 SQL 中提取表级和列级血缘关系
2. 血缘图存储与查询：使用邻接表存储血缘关系图
3. 影响分析：分析表/列变更的影响范围
4. 数据字典：与代码理解服务协作提供统一的元数据管理
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import re
import json
import httpx

from utils.logger import logger
from services.lineage_persistence_service import lineage_persistence_service


@dataclass
class LineageNode:
    """血缘节点"""
    id: str
    name: str
    type: str  # table, column, view, api, etc.
    datasource: str
    schema_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "datasource": self.datasource,
            "schema_name": self.schema_name,
            "metadata": self.metadata
        }


@dataclass
class LineageEdge:
    """血缘边"""
    id: str
    source_id: str
    target_id: str
    edge_type: str  # read, write, transform, depends_on, etc.
    operation: str  # SELECT, INSERT, UPDATE, DELETE, JOIN, etc.
    timestamp: datetime
    query_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "query_hash": self.query_hash,
            "metadata": self.metadata
        }


@dataclass
class ImpactAnalysisResult:
    """影响分析结果"""
    target_node: LineageNode
    affected_nodes: List[LineageNode]
    affected_edges: List[LineageEdge]
    risk_level: str  # low, medium, high
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_node": self.target_node.to_dict(),
            "affected_nodes": [n.to_dict() for n in self.affected_nodes],
            "affected_edges": [e.to_dict() for e in self.affected_edges],
            "risk_level": self.risk_level,
            "summary": self.summary,
            "details": self.details
        }


@dataclass
class ColumnLineage:
    """列级血缘信息"""
    target_column: str
    target_table: str
    source_columns: List[Tuple[str, str]]  # List of (column, table)
    transformation: str  # 转换逻辑描述

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_column": self.target_column,
            "target_table": self.target_table,
            "source_columns": [{"column": c, "table": t} for c, t in self.source_columns],
            "transformation": self.transformation
        }


class SQLLineageExtractor:
    """SQL 血缘提取器"""

    # SQL 语句类型
    OPERATION_SELECT = "SELECT"
    OPERATION_INSERT = "INSERT"
    OPERATION_UPDATE = "UPDATE"
    OPERATION_DELETE = "DELETE"
    OPERATION_CREATE = "CREATE"
    OPERATION_DROP = "DROP"
    OPERATION_ALTER = "ALTER"

    def __init__(self):
        # 正则表达式用于解析 SQL
        self.table_pattern = re.compile(
            r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?[`"\']?(\w+)[`"\']?(?:\.[`"\']?(\w+)[`"\']?)?',
            re.IGNORECASE
        )
        self.column_pattern = re.compile(
            r'\bSELECT\s+(.+?)\s+FROM',
            re.IGNORECASE | re.DOTALL
        )
        self.alias_pattern = re.compile(
            r'(\w+)\s+(?:AS\s+)?(\w+)',
            re.IGNORECASE
        )

    def extract_operation_type(self, sql: str) -> str:
        """提取 SQL 操作类型"""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            return self.OPERATION_SELECT
        elif sql_upper.startswith("INSERT"):
            return self.OPERATION_INSERT
        elif sql_upper.startswith("UPDATE"):
            return self.OPERATION_UPDATE
        elif sql_upper.startswith("DELETE"):
            return self.OPERATION_DELETE
        elif sql_upper.startswith("CREATE"):
            return self.OPERATION_CREATE
        elif sql_upper.startswith("DROP"):
            return self.OPERATION_DROP
        elif sql_upper.startswith("ALTER"):
            return self.OPERATION_ALTER
        return "UNKNOWN"

    def extract_tables(self, sql: str) -> Dict[str, List[str]]:
        """
        从 SQL 中提取表名，按角色分类
        返回：{"source_tables": [...], "target_tables": [...]}
        """
        source_tables = set()
        target_tables = set()

        sql_upper = sql.upper()

        # 目标表（INSERT INTO, UPDATE, CREATE TABLE）
        insert_match = re.search(r'INSERT\s+INTO\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?[`"\']?(\w+)[`"\']?', sql, re.IGNORECASE)
        if insert_match:
            target_tables.add(insert_match.group(1))

        update_match = re.search(r'UPDATE\s+(?:ONLY\s+)?[`"\']?(\w+)[`"\']?', sql, re.IGNORECASE)
        if update_match:
            target_tables.add(update_match.group(1))

        create_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?', sql, re.IGNORECASE)
        if create_match:
            target_tables.add(create_match.group(1))

        # 源表（FROM, JOIN）
        from_matches = re.findall(r'\bFROM\s+(?:ONLY\s+)?[`"\']?(\w+)[`"\']?', sql, re.IGNORECASE)
        source_tables.update(from_matches)

        join_matches = re.findall(r'\bJOIN\s+(?:ONLY\s+)?[`"\']?(\w+)[`"\']?', sql, re.IGNORECASE)
        source_tables.update(join_matches)

        # 子查询处理（递归提取）
        subquery_pattern = re.compile(r'\(\s*(SELECT\s+.+?)\)', re.IGNORECASE | re.DOTALL)
        for subquery in subquery_pattern.findall(sql):
            sub_result = self.extract_tables(subquery)
            source_tables.update(sub_result["source_tables"])
            target_tables.update(sub_result["target_tables"])

        return {
            "source_tables": list(source_tables),
            "target_tables": list(target_tables)
        }

    def extract_column_lineage(self, sql: str) -> List[ColumnLineage]:
        """
        提取列级血缘关系
        解析 SELECT 子句中的列及其来源
        """
        column_lineages = []

        # 提取 SELECT 部分
        select_match = self.column_pattern.search(sql)
        if not select_match:
            return column_lineages

        select_clause = select_match.group(1)

        # 提取表别名映射
        alias_map = {}
        table_matches = self.table_pattern.findall(sql)
        for match in table_matches:
            if len(match) == 2 and match[1]:  # schema.table 格式
                alias_map[match[1]] = f"{match[0]}.{match[1]}"
            elif len(match) == 1:
                alias_map[match[0]] = match[0]

        # 解析列
        columns = self._parse_select_columns(select_clause)
        for col_info in columns:
            lineage = ColumnLineage(
                target_column=col_info["target"],
                target_table="",  # 需要从上下文中获取
                source_columns=col_info["sources"],
                transformation=col_info["transformation"]
            )
            column_lineages.append(lineage)

        return column_lineages

    def _parse_select_columns(self, select_clause: str) -> List[Dict[str, Any]]:
        """解析 SELECT 子句中的列"""
        result = []

        # 处理 * 情况
        if select_clause.strip() == "*":
            return [{"target": "*", "sources": [], "transformation": "all_columns"}]

        # 简单分割逗号（不考虑嵌套函数）
        columns = self._split_columns(select_clause)

        for col in columns:
            col = col.strip()
            if not col or col == "*":
                continue

            # 检测聚合函数
            transformation = "direct"
            if any(func in col.upper() for func in ["COUNT", "SUM", "AVG", "MAX", "MIN", "COALESCE", "CASE"]):
                transformation = "aggregation"

            # 提取列名和别名
            alias_match = self.alias_pattern.search(col)
            if alias_match and " AS " in col.upper():
                parts = col.upper().split(" AS ")
                target = parts[1].strip().strip('"\'`') if len(parts) > 1 else parts[0].strip()
                source_expr = parts[0].strip()
            else:
                target = col.split(".")[-1].strip().strip('"\'`')
                source_expr = col

            # 提取源列
            sources = []
            col_refs = re.findall(r'(\w+)\.(\w+)|(?<!\.)\b(\w+)\b(?! *\()', source_expr, re.IGNORECASE)
            for ref in col_refs:
                if ref[0] and ref[1]:  # table.column 格式
                    sources.append((ref[1], ref[0]))
                elif ref[2] and ref[2].upper() not in ("AS", "FROM", "WHERE", "AND", "OR", "ON"):
                    sources.append((ref[2], ""))

            result.append({
                "target": target,
                "sources": sources,
                "transformation": transformation
            })

        return result

    def _split_columns(self, clause: str) -> List[str]:
        """分割列，考虑括号嵌套"""
        columns = []
        current = ""
        depth = 0

        for char in clause:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                columns.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            columns.append(current.strip())

        return columns


class DataDictionaryClient:
    """数据字典客户端 - 与代码理解服务协作"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or "http://localhost:8000"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_cache_key(self, datasource: str, table_name: Optional[str] = None) -> str:
        """生成缓存键"""
        return f"{datasource}:{table_name or '*'}"

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache_ttl:
            return False
        return datetime.now() < self._cache_ttl[key]

    async def fetch_data_dictionary(
        self,
        project_name: str,
        table_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从代码理解服务获取数据字典

        参数:
            project_name: 项目名称（代码理解服务中的索引项目）
            table_pattern: 表名模式（可选，支持通配符）

        返回:
            数据字典信息
        """
        cache_key = self._get_cache_key(project_name, table_pattern)

        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.debug(f"Data dictionary cache hit: {cache_key}")
            return self._cache[cache_key]

        try:
            client = await self.get_client()
            # 调用代码理解服务的 global-map 接口获取项目结构
            response = await client.get(
                "/api/understanding/global-map",
                params={"project_name": project_name}
            )
            response.raise_for_status()
            project_data = response.json()

            # 解析项目结构，提取数据相关的元数据
            dictionary = self._parse_project_dictionary(project_data, table_pattern)

            # 缓存结果（5 分钟 TTL）
            self._cache[cache_key] = dictionary
            self._cache_ttl[cache_key] = datetime.now() + datetime.timedelta(minutes=5)

            logger.info(f"Fetched data dictionary for project: {project_name}")
            return dictionary

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch data dictionary from code understanding service: {e}")
            return self._get_fallback_dictionary(project_name, table_pattern)
        except Exception as e:
            logger.error(f"Error fetching data dictionary: {e}")
            return self._get_fallback_dictionary(project_name, table_pattern)

    def _parse_project_dictionary(
        self,
        project_data: Dict[str, Any],
        table_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """从代码理解服务返回的项目数据中解析数据字典"""
        dictionary = {
            "project_name": project_data.get("project", ""),
            "repo_path": project_data.get("repo", ""),
            "tables": [],
            "apis": [],
            "data_models": [],
            "last_synced": datetime.utcnow().isoformat()
        }

        # 提取目录结构中的 model/schema 相关文件
        structure = project_data.get("structure", {})
        if structure:
            # 查找模型定义文件
            for path, info in structure.get("files", {}).items():
                lower_path = path.lower()
                if any(keyword in lower_path for keyword in ["model", "schema", "table", "entity"]):
                    dictionary["data_models"].append({
                        "path": path,
                        "type": info.get("type", "unknown"),
                        "symbols": info.get("symbols", [])
                    })

            # 查找 API 定义
            for path, info in structure.get("files", {}).items():
                if "api" in path.lower() or "route" in path.lower():
                    dictionary["apis"].append({
                        "path": path,
                        "methods": info.get("methods", []),
                        "symbols": info.get("symbols", [])
                    })

        # 提取全局符号
        symbols = project_data.get("symbols", [])
        for symbol in symbols:
            symbol_name = symbol.get("name", "")
            symbol_type = symbol.get("type", "")

            # 识别数据相关的符号
            if any(kw in symbol_name.lower() for kw in ["table", "model", "schema", "entity"]):
                dictionary["tables"].append({
                    "name": symbol_name,
                    "type": symbol_type,
                    "file_path": symbol.get("file_path", ""),
                    "fields": symbol.get("fields", [])
                })

        return dictionary

    def _get_fallback_dictionary(
        self,
        project_name: str,
        table_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """返回降级字典（当代码理解服务不可用时）"""
        return {
            "project_name": project_name,
            "tables": [],
            "apis": [],
            "data_models": [],
            "last_synced": datetime.utcnow().isoformat(),
            "fallback": True,
            "message": "代码理解服务不可用，返回空字典"
        }

    async def search_dictionary(
        self,
        keyword: str,
        project_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索数据字典

        参数:
            keyword: 搜索关键词
            project_name: 项目名称（可选）

        返回:
            匹配的元数据列表
        """
        try:
            client = await self.get_client()
            # 使用代码理解服务的 ask 接口进行搜索
            response = await client.post(
                "/api/understanding/ask",
                json={
                    "question": f"查找与'{keyword}'相关的数据表、模型或 API 定义",
                    "scope_paths": None
                }
            )
            response.raise_for_status()
            result = response.json()

            # 解析回答，提取相关信息
            return self._parse_search_results(result, keyword)

        except Exception as e:
            logger.warning(f"Dictionary search failed: {e}")
            return []

    def _parse_search_results(
        self,
        result: Dict[str, Any],
        keyword: str
    ) -> List[Dict[str, Any]]:
        """解析搜索结果"""
        results = []

        # 从回答中提取引用
        citations = result.get("citations", [])
        for citation in citations:
            results.append({
                "file_path": citation.get("file_path", ""),
                "line_range": f"{citation.get('start_line', 0)}-{citation.get('end_line', 0)}",
                "content": citation.get("content", "")[:500],
                "similarity": citation.get("similarity", 0)
            })

        return results


class DataLineageManager:
    """数据血缘管理器 - 支持内存 + 持久化存储"""

    def __init__(self, code_understanding_base_url: Optional[str] = None, enable_persistence: bool = True):
        self._node_store: Dict[str, LineageNode] = {}
        self._edge_store: Dict[str, LineageEdge] = {}
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)  # 正向依赖
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # 反向依赖
        self._query_history: List[Dict[str, Any]] = []
        self._data_dictionaries: Dict[str, Dict[str, Any]] = {}

        # SQL 提取器
        self._sql_extractor = SQLLineageExtractor()

        # 数据字典客户端
        self._dictionary_client = DataDictionaryClient(code_understanding_base_url)

        # 持久化服务
        self._enable_persistence = enable_persistence
        self._persistence_service = lineage_persistence_service if enable_persistence else None

        logger.info(f"Data lineage manager initialized with persistence={enable_persistence}")

    def _generate_node_id(self, datasource: str, name: str, node_type: str) -> str:
        """生成节点唯一 ID"""
        return f"{datasource}:{node_type}:{name}"

    def _generate_edge_id(self, source_id: str, target_id: str, operation: str) -> str:
        """生成边唯一 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"edge:{source_id}:{target_id}:{operation}:{timestamp}"

    def _hash_query(self, query: str) -> str:
        """生成查询哈希"""
        import hashlib
        # 规范化 SQL（去除空白、统一大小写）
        normalized = " ".join(query.split()).upper()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def record_query_impact(
        self,
        datasource: str,
        query: str,
        operation_type: str,
        affected_tables: List[str],
        user: str = None,
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录查询操作的血缘影响

        完整实现：
        1. 解析 SQL 提取表级和列级血缘
        2. 创建节点和边
        3. 更新邻接表
        4. 记录查询历史
        5. 持久化到数据库（如果启用）
        """
        # 提取 SQL 中的表关系
        tables_info = self._sql_extractor.extract_tables(query)
        source_tables = tables_info.get("source_tables", [])
        target_tables = tables_info.get("target_tables", [])

        # 如果没有显式的目标表，将查询影响的表视为目标
        if not target_tables and affected_tables:
            target_tables = affected_tables

        created_nodes = []
        created_edges = []

        # 创建/获取节点
        all_tables = set(source_tables + target_tables)
        for table in all_tables:
            node_id = self._generate_node_id(datasource, table, "table")
            if node_id not in self._node_store:
                node = LineageNode(
                    id=node_id,
                    name=table,
                    type="table",
                    datasource=datasource,
                    schema_name=schema_name,
                    metadata={
                        "created_at": datetime.utcnow().isoformat(),
                        "created_by": "query_analysis"
                    }
                )
                self._node_store[node_id] = node
                created_nodes.append(node_id)

        # 创建边
        timestamp = datetime.now()
        query_hash = self._hash_query(query)

        for source_table in source_tables:
            for target_table in target_tables:
                source_id = self._generate_node_id(datasource, source_table, "table")
                target_id = self._generate_node_id(datasource, target_table, "table")

                edge_id = self._generate_edge_id(source_id, target_id, operation_type)

                edge = LineageEdge(
                    id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    edge_type="transform" if operation_type == "SELECT" else "write",
                    operation=operation_type,
                    timestamp=timestamp,
                    query_hash=query_hash,
                    metadata={
                        "user": user,
                        "query_sample": query[:200] if len(query) > 200 else query
                    }
                )

                self._edge_store[edge_id] = edge
                self._adjacency_list[source_id].add(target_id)
                self._reverse_adjacency[target_id].add(source_id)
                created_edges.append(edge_id)

        # 记录查询历史
        self._query_history.append({
            "timestamp": timestamp.isoformat(),
            "datasource": datasource,
            "operation_type": operation_type,
            "source_tables": source_tables,
            "target_tables": target_tables,
            "user": user,
            "query_hash": query_hash
        })

        # 持久化到数据库
        if self._enable_persistence and self._persistence_service:
            self._persist_lineage_to_db(
                datasource=datasource,
                query=query,
                operation_type=operation_type,
                source_tables=source_tables,
                target_tables=target_tables,
                user=user,
                created_nodes=created_nodes,
                created_edges=created_edges,
                query_hash=query_hash
            )

        logger.info(
            "Lineage recorded",
            extra={
                "datasource": datasource,
                "source_tables": source_tables,
                "target_tables": target_tables,
                "user": user
            }
        )

        return {
            "nodes_created": created_nodes,
            "edges_created": created_edges,
            "query_hash": query_hash
        }

    async def _persist_lineage_to_db(
        self,
        datasource: str,
        query: str,
        operation_type: str,
        source_tables: List[str],
        target_tables: List[str],
        user: str,
        created_nodes: List[str],
        created_edges: List[str],
        query_hash: str
    ):
        """将血缘数据持久化到数据库"""
        try:
            # 创建节点
            for table in set(source_tables + target_tables):
                node_id = self._generate_node_id(datasource, table, "table")
                node = self._node_store.get(node_id)
                if node:
                    await self._persistence_service.create_node(
                        node_id=node_id,
                        name=node.name,
                        node_type=node.type,
                        datasource=datasource,
                        schema_name=node.schema_name,
                        metadata=node.metadata,
                        created_by="query_analysis"
                    )

            # 创建边
            for source_table in source_tables:
                for target_table in target_tables:
                    source_id = self._generate_node_id(datasource, source_table, "table")
                    target_id = self._generate_node_id(datasource, target_table, "table")

                    await self._persistence_service.create_edge(
                        source_id=source_id,
                        target_id=target_id,
                        edge_type="transform" if operation_type == "SELECT" else "write",
                        operation=operation_type,
                        query_hash=query_hash,
                        metadata={"user": user},
                        created_by=user
                    )

            # 记录查询历史
            await self._persistence_service.record_query_history(
                datasource=datasource,
                query_sql=query,
                query_hash=query_hash,
                operation_type=operation_type,
                source_tables=source_tables,
                target_tables=target_tables,
                user_id=user,
                nodes_created=len(created_nodes),
                edges_created=len(created_edges)
            )

            logger.info("Lineage persisted to database")

        except Exception as e:
            logger.error(f"Failed to persist lineage to database: {e}")

    def get_table_lineage(
        self,
        datasource: str,
        table_name: str,
        include_upstream: bool = True,
        include_downstream: bool = True,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        获取表的血缘关系（上游和下游）

        参数:
            datasource: 数据源名称
            table_name: 表名
            include_upstream: 是否包含上游（依赖的表）
            include_downstream: 是否包含下游（依赖此表的表）
            max_depth: 最大追踪深度
        """
        node_id = self._generate_node_id(datasource, table_name, "table")

        if node_id not in self._node_store:
            logger.warning(f"Table node not found: {node_id}")
            return {
                "table": f"{datasource}.{table_name}",
                "upstream": [],
                "downstream": [],
                "node_found": False,
                "message": f"表 {table_name} 尚未被血缘追踪，请先执行相关查询"
            }

        result = {
            "table": f"{datasource}.{table_name}",
            "node_id": node_id,
            "upstream": [],
            "downstream": [],
            "upstream_count": 0,
            "downstream_count": 0,
            "last_updated": datetime.utcnow().isoformat()
        }

        # 获取上游（此表依赖的表）
        if include_upstream:
            upstream_ids = self._traverse_graph(
                node_id,
                self._reverse_adjacency,
                max_depth
            )
            upstream_nodes = [
                self._node_store[nid].to_dict()
                for nid in upstream_ids
                if nid in self._node_store
            ]
            result["upstream"] = upstream_nodes
            result["upstream_count"] = len(upstream_nodes)

        # 获取下游（依赖此表的表）
        if include_downstream:
            downstream_ids = self._traverse_graph(
                node_id,
                self._adjacency_list,
                max_depth
            )
            downstream_nodes = [
                self._node_store[nid].to_dict()
                for nid in downstream_ids
                if nid in self._node_store
            ]
            result["downstream"] = downstream_nodes
            result["downstream_count"] = len(downstream_nodes)

        # 获取相关的边
        related_edges = []
        for edge in self._edge_store.values():
            if edge.source_id == node_id or edge.target_id == node_id:
                related_edges.append(edge.to_dict())
        result["related_edges"] = related_edges
        result["edge_count"] = len(related_edges)

        return result

    def _traverse_graph(
        self,
        start_id: str,
        adjacency: Dict[str, Set[str]],
        max_depth: int
    ) -> Set[str]:
        """BFS 遍历图"""
        visited = set()
        queue = [(start_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            for neighbor_id in adjacency.get(current_id, set()):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, depth + 1))

        # 移除起始节点
        visited.discard(start_id)
        return visited

    def analyze_impact(
        self,
        datasource: str,
        table_name: str,
        proposed_changes: Optional[Dict[str, Any]] = None
    ) -> ImpactAnalysisResult:
        """
        分析表变更的影响范围

        参数:
            datasource: 数据源名称
            table_name: 表名
            proposed_changes: 拟议的变更，如：
                {
                    "change_type": "schema_change|data_change|drop_table",
                    "details": {...}
                }
        """
        node_id = self._generate_node_id(datasource, table_name, "table")

        if node_id not in self._node_store:
            return ImpactAnalysisResult(
                target_node=LineageNode(
                    id=node_id,
                    name=table_name,
                    type="table",
                    datasource=datasource
                ),
                affected_nodes=[],
                affected_edges=[],
                risk_level="unknown",
                summary=f"表 {table_name} 不存在于血缘图中，无法分析影响范围"
            )

        # 获取所有下游节点（受影响的节点）
        downstream_ids = self._traverse_graph(
            node_id,
            self._adjacency_list,
            max_depth=10
        )

        affected_nodes = [
            self._node_store[nid]
            for nid in downstream_ids
            if nid in self._node_store
        ]

        # 获取受影响的边
        affected_edges = [
            edge
            for edge in self._edge_store.values()
            if edge.source_id in downstream_ids or edge.target_id == node_id
        ]

        # 评估风险等级
        risk_level = self._evaluate_risk(
            target_node=self._node_store[node_id],
            affected_nodes=affected_nodes,
            affected_edges=affected_edges,
            proposed_changes=proposed_changes
        )

        # 生成摘要
        summary = self._generate_impact_summary(
            table_name=table_name,
            risk_level=risk_level,
            affected_nodes_count=len(affected_nodes),
            affected_edges_count=len(affected_edges),
            proposed_changes=proposed_changes
        )

        target_node = self._node_store[node_id]

        return ImpactAnalysisResult(
            target_node=target_node,
            affected_nodes=affected_nodes,
            affected_edges=affected_edges,
            risk_level=risk_level,
            summary=summary,
            details={
                "datasource": datasource,
                "table": table_name,
                "proposed_changes": proposed_changes,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        )

    def _evaluate_risk(
        self,
        target_node: LineageNode,
        affected_nodes: List[LineageNode],
        affected_edges: List[LineageEdge],
        proposed_changes: Optional[Dict[str, Any]] = None
    ) -> str:
        """评估变更风险等级"""
        if not proposed_changes:
            return "low"

        change_type = proposed_changes.get("change_type", "")

        # DROP TABLE 是最高风险
        if change_type == "drop_table":
            return "high"

        # 架构变更根据影响范围评估
        if change_type == "schema_change":
            if len(affected_nodes) > 5:
                return "high"
            elif len(affected_nodes) > 2:
                return "medium"
            return "low"

        # 数据变更通常是低风险
        if change_type == "data_change":
            return "low"

        return "medium"

    def _generate_impact_summary(
        self,
        table_name: str,
        risk_level: str,
        affected_nodes_count: int,
        affected_edges_count: int,
        proposed_changes: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成影响分析摘要"""
        change_desc = "未知变更"
        if proposed_changes:
            change_type = proposed_changes.get("change_type", "")
            change_desc = {
                "drop_table": "删除表",
                "schema_change": "架构变更（列修改/删除）",
                "data_change": "数据变更",
                "add_column": "添加列"
            }.get(change_type, change_type)

        return (
            f"表 {table_name} 拟进行{change_desc}。"
            f"风险评估：{risk_level}。"
            f"将影响 {affected_nodes_count} 个下游节点，"
            f"涉及 {affected_edges_count} 条血缘关系。"
            f"建议在变更前与下游系统负责人确认。"
        )

    def register_data_dictionary(
        self,
        datasource: str,
        schema: Dict[str, Any],
        source: str = "manual"
    ) -> None:
        """
        注册数据字典信息

        参数:
            datasource: 数据源名称
            schema: Schema 信息，如：
                {
                    "tables": {
                        "users": {
                            "columns": ["id", "name", "email"],
                            "description": "用户表"
                        }
                    }
                }
            source: 来源（manual, auto_discovered, code_understanding）
        """
        self._data_dictionaries[datasource] = {
            "schema": schema,
            "source": source,
            "registered_at": datetime.utcnow().isoformat()
        }

        # 为 schema 中的表创建节点
        tables = schema.get("tables", {})
        for table_name, table_info in tables.items():
            node_id = self._generate_node_id(datasource, table_name, "table")
            if node_id not in self._node_store:
                self._node_store[node_id] = LineageNode(
                    id=node_id,
                    name=table_name,
                    type="table",
                    datasource=datasource,
                    metadata={
                        "columns": table_info.get("columns", []),
                        "description": table_info.get("description", ""),
                        "source": source
                    }
                )

        logger.info(
            "Data dictionary registered",
            extra={"datasource": datasource, "tables_count": len(tables)}
        )

    async def sync_data_dictionary_from_code_understanding(
        self,
        datasource: str,
        project_name: str,
        table_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从代码理解服务同步数据字典

        参数:
            datasource: 数据源名称
            project_name: 代码理解服务中的项目名称
            table_pattern: 表名模式（可选）

        返回:
            同步结果
        """
        dictionary = await self._dictionary_client.fetch_data_dictionary(
            project_name,
            table_pattern
        )

        # 注册到本地
        self._data_dictionaries[datasource] = {
            "schema": dictionary,
            "source": "code_understanding",
            "project_name": project_name,
            "synced_at": datetime.utcnow().isoformat()
        }

        # 为发现的数据模型创建节点
        nodes_created = 0
        for model in dictionary.get("data_models", []):
            for symbol in model.get("symbols", []):
                node_id = self._generate_node_id(datasource, symbol, "data_model")
                if node_id not in self._node_store:
                    self._node_store[node_id] = LineageNode(
                        id=node_id,
                        name=symbol,
                        type="data_model",
                        datasource=datasource,
                        metadata={"path": model.get("path", "")}
                    )
                    nodes_created += 1

        return {
            "success": True,
            "datasource": datasource,
            "project_name": project_name,
            "nodes_created": nodes_created,
            "tables_found": len(dictionary.get("tables", [])),
            "models_found": len(dictionary.get("data_models", []))
        }

    def get_data_dictionary(
        self,
        datasource: str,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从数据字典获取元数据

        参数:
            datasource: 数据源名称
            table_name: 表名（可选，不传则返回全部）
        """
        if datasource not in self._data_dictionaries:
            return {
                "datasource": datasource,
                "table": table_name,
                "fields": [],
                "description": f"数据源 {datasource} 尚未注册数据字典",
                "last_synced": None,
                "message": "请先调用 register_data_dictionary 或 sync_data_dictionary_from_code_understanding"
            }

        dict_data = self._data_dictionaries[datasource]
        schema = dict_data.get("schema", {})

        if table_name:
            # 返回特定表的信息
            tables = schema.get("tables", {})
            if table_name in tables:
                table_info = tables[table_name]
                return {
                    "datasource": datasource,
                    "table": table_name,
                    "fields": table_info.get("columns", []),
                    "description": table_info.get("description", ""),
                    "metadata": {k: v for k, v in table_info.items() if k not in ["columns", "description"]},
                    "source": dict_data.get("source", "unknown"),
                    "last_synced": dict_data.get("synced_at", dict_data.get("registered_at"))
                }
            else:
                return {
                    "datasource": datasource,
                    "table": table_name,
                    "fields": [],
                    "description": f"表 {table_name} 未在数据字典中找到",
                    "available_tables": list(tables.keys()),
                    "last_synced": dict_data.get("synced_at", dict_data.get("registered_at"))
                }
        else:
            # 返回整个数据源的数据字典
            return {
                "datasource": datasource,
                "tables": list(schema.get("tables", {}).keys()),
                "table_count": len(schema.get("tables", {})),
                "schema_summary": schema,
                "source": dict_data.get("source", "unknown"),
                "last_synced": dict_data.get("synced_at", dict_data.get("registered_at"))
            }

    async def search_data_dictionary(
        self,
        keyword: str,
        datasource: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索数据字典

        参数:
            keyword: 搜索关键词
            datasource: 数据源名称（可选，不传则搜索所有）
        """
        results = []

        # 本地搜索
        sources_to_search = [datasource] if datasource else list(self._data_dictionaries.keys())

        for source in sources_to_search:
            dict_data = self._data_dictionaries.get(source, {})
            schema = dict_data.get("schema", {})

            # 搜索表名和字段名
            for table_name, table_info in schema.get("tables", {}).items():
                if keyword.lower() in table_name.lower():
                    results.append({
                        "type": "table",
                        "datasource": source,
                        "name": table_name,
                        "description": table_info.get("description", ""),
                        "columns": table_info.get("columns", []),
                        "match_type": "table_name"
                    })

                # 搜索字段
                for column in table_info.get("columns", []):
                    if keyword.lower() in column.lower():
                        results.append({
                            "type": "column",
                            "datasource": source,
                            "table": table_name,
                            "name": column,
                            "match_type": "column_name"
                        })

        # 尝试从代码理解服务搜索
        if not datasource:
            remote_results = await self._dictionary_client.search_dictionary(keyword)
            results.extend(remote_results)

        return results

    def get_lineage_statistics(self) -> Dict[str, Any]:
        """获取血缘统计信息"""
        stats = {
            "total_nodes": len(self._node_store),
            "total_edges": len(self._edge_store),
            "total_queries_tracked": len(self._query_history),
            "datasources": len(self._data_dictionaries),
            "node_types": self._count_node_types(),
            "query_history_sample": self._query_history[-5:] if self._query_history else [],
            "persistence_enabled": self._enable_persistence
        }
        return stats

    async def get_lineage_statistics_from_db(self) -> Dict[str, Any]:
        """从数据库获取血缘统计信息"""
        if not self._persistence_service:
            return {"success": False, "message": "Persistence not enabled"}

        return await self._persistence_service.get_statistics()

    def _count_node_types(self) -> Dict[str, int]:
        """统计各类型节点数量"""
        type_counts = defaultdict(int)
        for node in self._node_store.values():
            type_counts[node.type] += 1
        return dict(type_counts)

    async def cleanup(self):
        """清理资源"""
        await self._dictionary_client.close()

    async def create_snapshot(self, snapshot_name: str, description: str = None, created_by: str = None) -> Dict[str, Any]:
        """创建血缘快照"""
        if not self._persistence_service:
            return {"success": False, "message": "Persistence not enabled"}

        return await self._persistence_service.create_snapshot(
            snapshot_name=snapshot_name,
            description=description,
            created_by=created_by
        )

    async def load_lineage_from_db(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """从数据库加载血缘数据到内存"""
        if not self._persistence_service:
            return {"success": False, "message": "Persistence not enabled"}

        try:
            # 加载节点
            nodes_result = await self._persistence_service.list_nodes(
                datasource=datasource,
                limit=10000
            )

            if nodes_result.get("success"):
                for node_data in nodes_result.get("nodes", []):
                    node = LineageNode(
                        id=node_data["id"],
                        name=node_data["name"],
                        type=node_data["type"],
                        datasource=node_data["datasource"],
                        schema_name=node_data.get("schema_name"),
                        metadata=node_data.get("metadata", {})
                    )
                    self._node_store[node.id] = node

                logger.info(f"Loaded {len(nodes_result.get('nodes', []))} nodes from database")

            return {"success": True, "loaded": True}

        except Exception as e:
            logger.error(f"Failed to load lineage from database: {e}")
            return {"success": False, "message": str(e)}


# 全局实例
lineage_manager = DataLineageManager()
