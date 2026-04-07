"""
知识图谱数据模型

定义图谱中的节点和边类型，支持多层级代码表示
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import hashlib


class NodeType(str, Enum):
    """节点类型"""
    PROJECT = "project"      # 项目
    PACKAGE = "package"      # 包/目录
    MODULE = "module"        # 文件/模块
    CLASS = "class"          # 类
    FUNCTION = "function"    # 函数/方法
    VARIABLE = "variable"    # 变量/常量
    INTERFACE = "interface"  # 接口/协议
    ENUM = "enum"           # 枚举


class EdgeType(str, Enum):
    """边类型"""
    # 结构关系
    CONTAINS = "contains"        # 包含（包包含模块，模块包含类/函数）
    BELONGS_TO = "belongs_to"    # 属于（函数属于类，类属于模块）

    # 依赖关系
    IMPORTS = "imports"          # 导入
    DEPENDS_ON = "depends_on"    # 依赖

    # 面向对象关系
    EXTENDS = "extends"          # 继承
    IMPLEMENTS = "implements"    # 实现

    # 调用关系
    CALLS = "calls"              # 调用
    ACCESSES = "accesses"        # 访问（变量/属性）

    # 引用关系
    REFERENCES = "references"    # 引用（泛用）
    DEFINES = "defines"          # 定义
    USED_BY = "used_by"          # 被使用


@dataclass
class KGNode:
    """
    知识图谱节点

    属性:
        id: 节点唯一标识符（基于 file_path 和 symbol_name 生成）
        node_type: 节点类型
        name: 节点名称
        file_path: 所属文件路径
        symbol_name: 符号名称（类名、函数名等）
        start_line: 起始行号
        end_line: 结束行号
        language: 编程语言
        content: 代码内容片段
        metadata: 额外元数据
        signature_hash: 签名哈希（用于增量检测）
    """
    node_type: NodeType
    name: str
    file_path: str
    symbol_name: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: str = "unknown"
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    signature_hash: Optional[str] = None

    def __post_init__(self):
        """初始化后计算 ID 和签名哈希"""
        if not self.id:
            self.id = self._generate_id()
        if not self.signature_hash:
            self.signature_hash = self._compute_signature_hash()

    @property
    def id(self) -> str:
        """生成节点唯一 ID"""
        return self._generate_id()

    def _generate_id(self) -> str:
        """基于文件路径和符号名称生成唯一 ID"""
        key_parts = [self.file_path]
        if self.symbol_name:
            key_parts.append(self.symbol_name)
        elif self.name:
            key_parts.append(self.name)
        key = "::".join(key_parts)
        return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]

    def _compute_signature_hash(self) -> str:
        """计算签名哈希（用于检测变更）"""
        content = f"{self.name}:{self.symbol_name}:{self.start_line}:{self.end_line}:{self.language}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    @property
    def display_name(self) -> str:
        """获取显示名称"""
        if self.symbol_name:
            return self.symbol_name
        return self.name or self.file_path.split('/')[-1]

    @property
    def location(self) -> str:
        """获取位置字符串"""
        location = self.file_path
        if self.start_line:
            location += f":{self.start_line}"
        if self.end_line and self.end_line != self.start_line:
            location += f"-{self.end_line}"
        return location

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "content": self.content[:500] if self.content and len(self.content) > 500 else self.content,
            "metadata": self.metadata,
            "signature_hash": self.signature_hash,
            "display_name": self.display_name,
            "location": self.location
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KGNode":
        """从字典创建节点"""
        node = cls(
            node_type=NodeType(data.get("node_type", "module")),
            name=data.get("name", ""),
            file_path=data.get("file_path", ""),
            symbol_name=data.get("symbol_name"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            language=data.get("language", "unknown"),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            signature_hash=data.get("signature_hash")
        )
        return node


@dataclass
class KGEdge:
    """
    知识图谱边

    属性:
        id: 边唯一标识符
        source: 源节点 ID
        target: 目标节点 ID
        edge_type: 边类型
        metadata: 额外元数据
        weight: 权重（用于路径分析）
    """
    source: str
    target: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()

    @property
    def id(self) -> str:
        """生成边唯一 ID"""
        return self._generate_id()

    def _generate_id(self) -> str:
        """基于源节点和目标节点生成唯一 ID"""
        key = f"{self.source}->{self.target}:{self.edge_type.value}"
        return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "metadata": self.metadata,
            "weight": self.weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KGEdge":
        """从字典创建边"""
        edge = cls(
            source=data.get("source", ""),
            target=data.get("target", ""),
            edge_type=EdgeType(data.get("edge_type", "references")),
            metadata=data.get("metadata", {}),
            weight=data.get("weight", 1.0)
        )
        return edge


@dataclass
class GraphStats:
    """图谱统计信息"""
    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_type: Dict[str, int] = field(default_factory=dict)
    edges_by_type: Dict[str, int] = field(default_factory=dict)
    max_in_degree: int = 0
    max_out_degree: int = 0
    avg_in_degree: float = 0.0
    avg_out_degree: float = 0.0
    cycle_count: int = 0
    connected_components: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "nodes_by_type": self.nodes_by_type,
            "edges_by_type": self.edges_by_type,
            "max_in_degree": self.max_in_degree,
            "max_out_degree": self.max_out_degree,
            "avg_in_degree": self.avg_in_degree,
            "avg_out_degree": self.avg_out_degree,
            "cycle_count": self.cycle_count,
            "connected_components": self.connected_components
        }
