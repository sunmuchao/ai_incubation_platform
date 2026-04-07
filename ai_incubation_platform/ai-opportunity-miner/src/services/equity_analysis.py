"""
股权穿透分析服务
支持递归持股计算、最终受益人识别、控制权分析
"""
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import logging
from datetime import datetime

from models.investment import (
    ShareholderNode, ShareholderType, EquityOwnership
)

logger = logging.getLogger(__name__)


class EquityAnalysisService:
    """股权穿透分析服务"""

    def __init__(self):
        # 内存存储股东关系
        # key: company_id, value: list of shareholder info
        self._shareholders: Dict[str, List[Dict]] = defaultdict(list)
        # 缓存股权穿透结果
        self._cache: Dict[str, EquityOwnership] = {}
        # 初始化模拟数据
        self._init_mock_data()

    def _init_mock_data(self):
        """初始化模拟股东数据"""
        # 构建一个复杂的股权穿透示例
        mock_data = {
            # 目标公司：阿里巴巴集团
            "ENT-阿里巴巴集团": [
                {"name": "软银集团", "type": "corporate", "ratio": 25.5, "company_id": "ENT-软银集团"},
                {"name": "马云", "type": "individual", "ratio": 6.3, "identity_masked": "马*"},
                {"name": "蔡崇信", "type": "individual", "ratio": 1.7, "identity_masked": "蔡*"},
                {"name": "阿里巴巴合伙人", "type": "other", "ratio": 7.0},
                {"name": "公众股东", "type": "other", "ratio": 59.5},
            ],
            # 软银集团（股东向上穿透）
            "ENT-软银集团": [
                {"name": "孙正义", "type": "individual", "ratio": 27.4, "identity_masked": "孙*"},
                {"name": "公众股东", "type": "other", "ratio": 72.6},
            ],
            # 腾讯控股
            "ENT-腾讯控股": [
                {"name": "MIH TC Holdings", "type": "corporate", "ratio": 28.9, "company_id": "ENT-Naspers"},
                {"name": "马化腾", "type": "individual", "ratio": 8.2, "identity_masked": "马*"},
                {"name": "刘炽平", "type": "individual", "ratio": 0.5, "identity_masked": "刘*"},
                {"name": "腾讯合伙人", "type": "other", "ratio": 5.4},
                {"name": "公众股东", "type": "other", "ratio": 57.0},
            ],
            # Naspers（腾讯股东向上穿透）
            "ENT-Naspers": [
                {"name": "公众股东", "type": "other", "ratio": 100.0},
            ],
            # 京东集团
            "ENT-京东集团": [
                {"name": "刘强东", "type": "individual", "ratio": 15.4, "identity_masked": "刘*", "voting_ratio": 78.0},
                {"name": "腾讯投资", "type": "corporate", "ratio": 17.4, "company_id": "ENT-腾讯控股"},
                {"name": "沃尔玛", "type": "corporate", "ratio": 10.1, "company_id": "ENT-沃尔玛"},
                {"name": "公众股东", "type": "other", "ratio": 57.1},
            ],
            # 美团点评
            "ENT-美团点评": [
                {"name": "王兴", "type": "individual", "ratio": 9.6, "identity_masked": "王*", "voting_ratio": 55.0},
                {"name": "腾讯投资", "type": "corporate", "ratio": 17.0, "company_id": "ENT-腾讯控股"},
                {"name": "红杉资本", "type": "investment_firm", "ratio": 8.5},
                {"name": "公众股东", "type": "other", "ratio": 64.9},
            ],
            # 字节跳动
            "ENT-字节跳动": [
                {"name": "张一鸣", "type": "individual", "ratio": 78.0, "identity_masked": "张*", "voting_ratio": 98.0},
                {"name": "梁汝波", "type": "individual", "ratio": 3.0, "identity_masked": "梁*"},
                {"name": "员工持股平台", "type": "other", "ratio": 19.0},
            ],
            # 拼多多
            "ENT-拼多多": [
                {"name": "黄峥", "type": "individual", "ratio": 28.0, "identity_masked": "黄*", "voting_ratio": 85.0},
                {"name": "腾讯投资", "type": "corporate", "ratio": 8.2, "company_id": "ENT-腾讯控股"},
                {"name": "红杉资本", "type": "investment_firm", "ratio": 7.0},
                {"name": "公众股东", "type": "other", "ratio": 56.8},
            ],
            # 小红书
            "ENT-小红书": [
                {"name": "毛文超", "type": "individual", "ratio": 18.5, "identity_masked": "毛*", "voting_ratio": 60.0},
                {"name": "瞿芳", "type": "individual", "ratio": 15.0, "identity_masked": "瞿*"},
                {"name": "阿里巴巴战投", "type": "corporate", "ratio": 12.0, "company_id": "ENT-阿里巴巴集团"},
                {"name": "腾讯投资", "type": "corporate", "ratio": 8.0, "company_id": "ENT-腾讯控股"},
                {"name": "员工持股平台", "type": "other", "ratio": 10.5},
                {"name": "其他投资者", "type": "other", "ratio": 36.0},
            ],
            # 理想汽车
            "ENT-理想汽车": [
                {"name": "李想", "type": "individual", "ratio": 21.0, "identity_masked": "李*", "voting_ratio": 70.0},
                {"name": "王兴", "type": "individual", "ratio": 10.0, "identity_masked": "王*"},
                {"name": "红杉资本", "type": "investment_firm", "ratio": 9.5},
                {"name": "美团龙珠", "type": "investment_firm", "ratio": 7.0},
                {"name": "公众股东", "type": "other", "ratio": 52.5},
            ],
        }

        for company_id, shareholders in mock_data.items():
            for shareholder in shareholders:
                self._shareholders[company_id].append(shareholder)

    def add_shareholder(self, company_id: str, shareholder: Dict):
        """添加股东记录"""
        self._shareholders[company_id].append(shareholder)
        # 清除缓存
        if company_id in self._cache:
            del self._cache[company_id]

    def get_shareholders(self, company_id: str) -> List[Dict]:
        """获取公司直接股东列表"""
        return self._shareholders.get(company_id, [])

    def analyze_equity_ownership(self, company_id: str, company_name: str) -> EquityOwnership:
        """
        分析公司股权穿透
        返回完整的股权穿透图、最终受益人、实际控制人
        """
        # 检查缓存
        if company_id in self._cache:
            return self._cache[company_id]

        # 构建股东树
        root_node = self._build_shareholder_tree(company_id, company_name, level=0, visited=set())

        # 计算间接持股和最终受益人
        beneficial_owners = []
        actual_controllers = []
        risk_indicators = []

        if root_node:
            # 递归计算间接持股
            self._calculate_indirect_ownership(root_node)

            # 识别最终受益人
            beneficial_owners = self._identify_beneficial_owners(root_node)

            # 识别实际控制人
            actual_controllers = self._identify_actual_controllers(root_node)

            # 风险识别
            risk_indicators = self._identify_risk_indicators(root_node, beneficial_owners)

        # 生成可视化数据
        visualization_data = self._build_visualization_data(root_node)

        # 控制链分析
        control_chain_analysis = self._analyze_control_chain(root_node)

        result = EquityOwnership(
            company_id=company_id,
            company_name=company_name,
            ownership_tree=root_node,
            beneficial_owners=beneficial_owners,
            actual_controllers=actual_controllers,
            visualization_data=visualization_data,
            control_chain_analysis=control_chain_analysis,
            risk_indicators=risk_indicators
        )

        # 缓存结果
        self._cache[company_id] = result

        return result

    def _build_shareholder_tree(
        self,
        company_id: str,
        company_name: str,
        level: int,
        visited: Set[str],
        max_depth: int = 5
    ) -> Optional[ShareholderNode]:
        """递归构建股东树"""
        if level > max_depth or company_id in visited:
            return None

        visited.add(company_id)

        # 创建当前公司节点
        root = ShareholderNode(
            id=company_id,
            name=company_name,
            type=ShareholderType.CORPORATE,
            level=level,
            direct_ratio=100.0,  # 自身 100%
            children=[]
        )

        # 获取直接股东
        shareholders = self.get_shareholders(company_id)

        for sh in shareholders:
            # 确定股东类型
            sh_type = self._parse_shareholder_type(sh.get("type", "other"))

            # 创建股东节点
            child_node = ShareholderNode(
                id=sh.get("company_id", f"SH-{sh['name']}"),
                name=sh["name"],
                type=sh_type,
                direct_ratio=sh.get("ratio", 0),
                voting_ratio=sh.get("voting_ratio"),
                level=level + 1,
                parent_id=company_id,
                identity_masked=sh.get("identity_masked"),
                children=[]
            )

            # 如果是公司股东，递归向上穿透
            if sh_type == ShareholderType.CORPORATE and sh.get("company_id"):
                grandchildren = self._build_shareholder_tree(
                    sh["company_id"],
                    sh["name"],
                    level + 1,
                    visited.copy(),
                    max_depth
                )
                if grandchildren:
                    child_node.children = grandchildren.children

            root.children.append(child_node)

        return root

    def _parse_shareholder_type(self, type_str: str) -> ShareholderType:
        """解析股东类型"""
        type_map = {
            "individual": ShareholderType.INDIVIDUAL,
            "corporate": ShareholderType.CORPORATE,
            "investment_firm": ShareholderType.INVESTMENT_FIRM,
            "government": ShareholderType.GOVERNMENT,
        }
        return type_map.get(type_str, ShareholderType.OTHER)

    def _calculate_indirect_ownership(self, node: ShareholderNode) -> float:
        """
        递归计算间接持股比例
        返回穿透到该节点的总持股比例
        """
        if not node.parent_id:
            # 根节点
            node.total_ratio = 100.0
            return 100.0

        # 计算从根到当前节点的路径持股比例
        # 简化计算：只计算直接路径的乘积
        total = 0.0

        # 如果有父节点引用，需要计算路径乘积
        # 这里简化为直接使用 direct_ratio
        # 实际场景需要建立父子引用关系

        # 对于叶节点（自然人），total_ratio = 路径上所有持股比例的乘积
        # 对于中间节点，total_ratio = 所有子节点 indirect_ratio 之和

        if node.children:
            # 中间节点：汇总子节点的间接持股
            node.indirect_ratio = sum(
                self._calculate_indirect_ownership(child)
                for child in node.children
            )
            node.total_ratio = node.direct_ratio + node.indirect_ratio
        else:
            # 叶节点
            node.indirect_ratio = 0.0
            node.total_ratio = node.direct_ratio

        return node.total_ratio

    def _identify_beneficial_owners(
        self,
        root: ShareholderNode,
        threshold: float = 1.0
    ) -> List[Dict]:
        """
        识别最终受益人
        阈值：默认穿透持股比例超过 1% 的自然人
        """
        beneficial_owners = []

        def traverse(node: ShareholderNode, path: List[str], cumulative_ratio: float):
            # 更新累计持股比例
            if node.direct_ratio < 100:
                cumulative_ratio = cumulative_ratio * (node.direct_ratio / 100)

            current_path = path + [node.name]

            # 判断是否为最终受益人（自然人或其他无法继续穿透的主体）
            is_beneficial = (
                node.type == ShareholderType.INDIVIDUAL or
                node.type == ShareholderType.OTHER or
                (node.type == ShareholderType.GOVERNMENT) or
                (len(node.children) == 0 and node.direct_ratio > 0)
            )

            if is_beneficial and cumulative_ratio * 100 >= threshold:
                beneficial_owners.append({
                    "name": node.name,
                    "type": node.type.value,
                    "total_ratio": round(cumulative_ratio * 100, 4),
                    "paths": [">".join(current_path)],
                    "identity_masked": node.identity_masked,
                    "level": node.level
                })
            elif node.children:
                # 继续向下穿透
                for child in node.children:
                    traverse(child, current_path, cumulative_ratio)

        if root and root.children:
            for child in root.children:
                traverse(child, [root.name], 1.0)

        # 按持股比例排序
        beneficial_owners.sort(key=lambda x: x["total_ratio"], reverse=True)

        return beneficial_owners

    def _identify_actual_controllers(self, root: ShareholderNode) -> List[Dict]:
        """
        识别实际控制人
        考虑表决权和持股比例
        """
        actual_controllers = []

        def traverse(node: ShareholderNode):
            # 检查是否有表决权信息
            voting_ratio = node.voting_ratio or node.direct_ratio

            # 判断是否为实际控制人
            # 通常持股或表决权超过 25% 可认定为有重大影响
            # 超过 50% 为绝对控股
            is_controller = (
                voting_ratio >= 25.0 or
                (node.type == ShareholderType.INDIVIDUAL and node.direct_ratio >= 10.0 and voting_ratio >= 50.0)
            )

            if is_controller and node.type in [
                ShareholderType.INDIVIDUAL,
                ShareholderType.CORPORATE,
                ShareholderType.GOVERNMENT
            ]:
                control_type = "absolute" if voting_ratio >= 50 else "relative"
                actual_controllers.append({
                    "name": node.name,
                    "type": node.type.value,
                    "equity_ratio": node.direct_ratio,
                    "voting_ratio": voting_ratio,
                    "control_type": control_type,
                    "level": node.level
                })

            for child in node.children:
                traverse(child)

        if root and root.children:
            for child in root.children:
                traverse(child)

        # 去重和排序
        seen = set()
        unique_controllers = []
        for ctrl in actual_controllers:
            if ctrl["name"] not in seen:
                seen.add(ctrl["name"])
                unique_controllers.append(ctrl)

        unique_controllers.sort(key=lambda x: x["voting_ratio"], reverse=True)

        return unique_controllers

    def _identify_risk_indicators(
        self,
        root: ShareholderNode,
        beneficial_owners: List[Dict]
    ) -> List[Dict]:
        """识别股权穿透中的风险点"""
        risks = []

        # 风险 1: 股权过于分散
        if root and root.children:
            max_ratio = max(sh.direct_ratio for sh in root.children) if root.children else 0
            if max_ratio < 20:
                risks.append({
                    "type": "dispersed_ownership",
                    "level": "medium",
                    "description": f"股权较为分散，最大股东持股比例仅{max_ratio}%"
                })

        # 风险 2: 最终受益人过多
        if len(beneficial_owners) > 20:
            risks.append({
                "type": "too_many_beneficial_owners",
                "level": "low",
                "description": f"最终受益人数量过多 ({len(beneficial_owners)}人)，可能存在代持"
            })

        # 风险 3: 股权穿透图层级过深
        max_depth = self._get_max_depth(root)
        if max_depth > 5:
            risks.append({
                "type": "deep_ownership_chain",
                "level": "medium",
                "description": f"股权穿透层级过深 ({max_depth}层)，可能隐藏实际控制人"
            })

        # 风险 4: 存在未知股东
        if root:
            unknown_sh = [sh for sh in root.children if sh.type == ShareholderType.OTHER and sh.direct_ratio > 20]
            if unknown_sh:
                risks.append({
                    "type": "unknown_shareholder",
                    "level": "high",
                    "description": f"存在持股比例较大的未知股东 ({unknown_sh[0].name}: {unknown_sh[0].direct_ratio}%)"
                })

        return risks

    def _get_max_depth(self, node: ShareholderNode) -> int:
        """获取股权穿透图最大深度"""
        if not node or not node.children:
            return 0
        return 1 + max(self._get_max_depth(child) for child in node.children)

    def _build_visualization_data(self, root: ShareholderNode) -> Dict:
        """构建可视化数据（ECharts 力导向图格式）"""
        if not root:
            return {"nodes": [], "links": []}

        nodes = []
        links = []

        def traverse(node: ShareholderNode, parent_id: str = None):
            # 添加节点
            node_color = {
                ShareholderType.INDIVIDUAL: "#91cc75",
                ShareholderType.CORPORATE: "#5470c6",
                ShareholderType.INVESTMENT_FIRM: "#fac858",
                ShareholderType.GOVERNMENT: "#ee6666",
                ShareholderType.OTHER: "#73c0de",
            }.get(node.type, "#91cc75")

            nodes.append({
                "id": node.id,
                "name": node.name,
                "type": node.type.value,
                "ratio": node.direct_ratio,
                "level": node.level,
                "symbolSize": max(20, node.direct_ratio * 2) if node.direct_ratio < 100 else 50,
                "itemStyle": {"color": node_color},
            })

            # 添加关系链接
            if parent_id:
                links.append({
                    "source": parent_id,
                    "target": node.id,
                    "label": {"show": True, "formatter": f"{node.direct_ratio}%"},
                    "value": node.direct_ratio
                })

            # 递归处理子节点
            for child in node.children:
                traverse(child, node.id)

        traverse(root)

        return {"nodes": nodes, "links": links}

    def _analyze_control_chain(self, root: ShareholderNode) -> Dict:
        """分析控制链"""
        if not root:
            return {}

        # 最长控制链
        longest_chain = []

        def find_longest(node: ShareholderNode, current_chain: List[str]) -> List[str]:
            chain = current_chain + [node.name]
            if not node.children:
                return chain

            longest = chain
            for child in node.children:
                child_chain = find_longest(child, chain)
                if len(child_chain) > len(longest):
                    longest = child_chain
            return longest

        if root.children:
            for child in root.children:
                chain = find_longest(child, [root.name])
                if len(chain) > len(longest_chain):
                    longest_chain = chain

        return {
            "max_depth": self._get_max_depth(root),
            "longest_chain": longest_chain,
            "chain_length": len(longest_chain),
            "control_layers": len(longest_chain) - 1 if longest_chain else 0
        }


# 全局服务实例
equity_analysis_service = EquityAnalysisService()
