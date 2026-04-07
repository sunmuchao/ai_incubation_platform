"""
投资关系链分析服务
"""
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import json

from models.investment import (
    InvestmentChain, InvestmentRound, InvestorType,
    InvestmentNetwork, InvestmentTrend
)
from models.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class InvestmentChainService:
    """投资关系链分析服务"""

    def __init__(self):
        # 内存存储投资关系
        self._investments: List[InvestmentChain] = []
        # 投资者 -> 被投资者映射
        self._investor_map: Dict[str, List[InvestmentChain]] = defaultdict(list)
        # 被投资者 -> 投资者映射
        self._investee_map: Dict[str, List[InvestmentChain]] = defaultdict(list)
        # 行业 -> 投资映射
        self._industry_map: Dict[str, List[InvestmentChain]] = defaultdict(list)
        # 初始化模拟数据
        self._init_mock_data()

    def _init_mock_data(self):
        """初始化模拟投资数据"""
        mock_investments = [
            # 腾讯的投资
            {
                "investor_name": "腾讯投资",
                "investor_type": InvestorType.CORPORATE,
                "investee_name": "京东集团",
                "investee_industry": "电商",
                "round": InvestmentRound.STRATEGIC,
                "amount": 214000000,
                "investment_date": datetime(2021, 6, 15),
                "equity_ratio": 17.4,
            },
            {
                "investor_name": "腾讯投资",
                "investor_type": InvestorType.CORPORATE,
                "investee_name": "拼多多",
                "investee_industry": "电商",
                "round": InvestmentRound.C,
                "amount": 300000000,
                "investment_date": datetime(2018, 4, 10),
                "equity_ratio": 8.2,
            },
            {
                "investor_name": "腾讯投资",
                "investor_type": InvestorType.CORPORATE,
                "investee_name": "美团点评",
                "investee_industry": "本地生活",
                "round": InvestmentRound.D_PLUS,
                "amount": 400000000,
                "investment_date": datetime(2019, 3, 20),
                "equity_ratio": 17.0,
            },
            # 阿里巴巴的投资
            {
                "investor_name": "阿里巴巴战投",
                "investor_type": InvestorType.CORPORATE,
                "investee_name": "小红书",
                "investee_industry": "社交电商",
                "round": InvestmentRound.F,
                "amount": 300000000,
                "investment_date": datetime(2019, 11, 5),
                "equity_ratio": 12.0,
            },
            {
                "investor_name": "阿里巴巴战投",
                "investor_type": InvestorType.CORPORATE,
                "investee_name": "哔哩哔哩",
                "investee_industry": "视频娱乐",
                "round": InvestmentRound.E,
                "amount": 400000000,
                "investment_date": datetime(2020, 2, 14),
                "equity_ratio": 13.0,
            },
            # 红杉资本的投资
            {
                "investor_name": "红杉资本中国",
                "investor_type": InvestorType.VC,
                "investee_name": "字节跳动",
                "investee_industry": "内容科技",
                "round": InvestmentRound.A,
                "amount": 5000000,
                "investment_date": datetime(2013, 5, 1),
                "equity_ratio": 15.0,
            },
            {
                "investor_name": "红杉资本中国",
                "investor_type": InvestorType.VC,
                "investee_name": "美团点评",
                "investee_industry": "本地生活",
                "round": InvestmentRound.B,
                "amount": 20000000,
                "investment_date": datetime(2014, 8, 15),
                "equity_ratio": 10.0,
            },
            {
                "investor_name": "红杉资本中国",
                "investor_type": InvestorType.VC,
                "investee_name": "理想汽车",
                "investee_industry": "新能源汽车",
                "round": InvestmentRound.A,
                "amount": 8000000,
                "investment_date": datetime(2016, 4, 1),
                "equity_ratio": 12.0,
            },
            # IDG 资本的投资
            {
                "investor_name": "IDG 资本",
                "investor_type": InvestorType.VC,
                "investee_name": "字节跳动",
                "investee_industry": "内容科技",
                "round": InvestmentRound.B,
                "amount": 10000000,
                "investment_date": datetime(2014, 6, 1),
                "equity_ratio": 8.0,
            },
            {
                "investor_name": "IDG 资本",
                "investor_type": InvestorType.VC,
                "investee_name": "小鹏汽车",
                "investee_industry": "新能源汽车",
                "round": InvestmentRound.A,
                "amount": 6000000,
                "investment_date": datetime(2017, 3, 15),
                "equity_ratio": 10.0,
            },
            # 高瓴资本的投资
            {
                "investor_name": "高瓴资本",
                "investor_type": InvestorType.PE,
                "investee_name": "京东集团",
                "investee_industry": "电商",
                "round": InvestmentRound.D_PLUS,
                "amount": 300000000,
                "investment_date": datetime(2015, 8, 1),
                "equity_ratio": 8.0,
            },
            {
                "investor_name": "高瓴资本",
                "investor_type": InvestorType.PE,
                "investee_name": "百济神州",
                "investee_industry": "生物医药",
                "round": InvestmentRound.C,
                "amount": 150000000,
                "investment_date": datetime(2016, 5, 15),
                "equity_ratio": 12.0,
            },
            # 源码资本的投资
            {
                "investor_name": "源码资本",
                "investor_type": InvestorType.VC,
                "investee_name": "拼多多",
                "investee_industry": "电商",
                "round": InvestmentRound.B,
                "amount": 50000000,
                "investment_date": datetime(2017, 10, 1),
                "equity_ratio": 5.0,
            },
            {
                "investor_name": "源码资本",
                "investor_type": InvestorType.VC,
                "investee_name": "小红书",
                "investee_industry": "社交电商",
                "round": InvestmentRound.D,
                "amount": 100000000,
                "investment_date": datetime(2018, 6, 1),
                "equity_ratio": 6.0,
            },
            # 经纬创投的投资
            {
                "investor_name": "经纬创投",
                "investor_type": InvestorType.VC,
                "investee_name": "理想汽车",
                "investee_industry": "新能源汽车",
                "round": InvestmentRound.B,
                "amount": 30000000,
                "investment_date": datetime(2017, 12, 1),
                "equity_ratio": 8.0,
            },
            {
                "investor_name": "经纬创投",
                "investor_type": InvestorType.VC,
                "investee_name": "小鹏汽车",
                "investee_industry": "新能源汽车",
                "round": InvestmentRound.B,
                "amount": 25000000,
                "investment_date": datetime(2018, 4, 1),
                "equity_ratio": 7.0,
            },
            # 顺为资本的投资
            {
                "investor_name": "顺为资本",
                "investor_type": InvestorType.VC,
                "investee_name": "小米科技",
                "investee_industry": "智能硬件",
                "round": InvestmentRound.A,
                "amount": 10000000,
                "investment_date": datetime(2011, 3, 1),
                "equity_ratio": 15.0,
            },
            {
                "investor_name": "顺为资本",
                "investor_type": InvestorType.VC,
                "investee_name": "爱奇艺",
                "investee_industry": "视频娱乐",
                "round": InvestmentRound.D,
                "amount": 80000000,
                "investment_date": datetime(2014, 11, 1),
                "equity_ratio": 5.0,
            },
        ]

        for inv_data in mock_investments:
            investment = InvestmentChain(
                investor_id=f"INV-{inv_data['investor_name']}",
                investee_id=f"ENT-{inv_data['investee_name']}",
                status="completed",
                tags=[inv_data['investee_industry'], inv_data['round'].value],
                **inv_data
            )
            self._investments.append(investment)
            self._investor_map[inv_data['investor_name']].append(investment)
            self._investee_map[inv_data['investee_name']].append(investment)
            self._industry_map[inv_data['investee_industry']].append(investment)

    def add_investment(self, investment: InvestmentChain):
        """添加投资记录"""
        self._investments.append(investment)
        self._investor_map[investment.investor_name].append(investment)
        self._investee_map[investment.investee_name].append(investment)
        self._industry_map[investment.investee_industry].append(investment)
        logger.info(f"Added investment: {investment.investor_name} -> {investment.investee_name}")

    def get_investments_by_investor(self, investor_name: str) -> List[InvestmentChain]:
        """获取投资方的所有投资记录"""
        return self._investor_map.get(investor_name, [])

    def get_investments_by_investee(self, investee_name: str) -> List[InvestmentChain]:
        """获取被投资方的所有融资记录"""
        return self._investee_map.get(investee_name, [])

    def get_investments_by_industry(self, industry: str) -> List[InvestmentChain]:
        """获取某行业的所有投资记录"""
        return self._industry_map.get(industry, [])

    def find_investment_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """
        查找从 source 到 target 的投资路径
        例如：查找"红杉资本"到"某公司"的投资路径
        """
        # BFS 搜索
        visited = set()
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current == target and len(path) > 1:
                # 找到路径，转换为详细投资信息
                return self._build_path_details(path)

            if current in visited:
                continue
            visited.add(current)

            # 查找 current 投资的公司
            for inv in self._investor_map.get(current, []):
                next_node = inv.investee_name
                if next_node not in visited:
                    queue.append((next_node, path + [next_node]))

            # 查找投资 current 的机构（反向）
            for inv in self._investee_map.get(current, []):
                next_node = inv.investor_name
                if next_node not in visited:
                    queue.append((next_node, path + [next_node]))

        return None

    def _build_path_details(self, path: List[str]) -> List[Dict]:
        """构建路径详细信息"""
        details = []
        for i in range(len(path) - 1):
            from_node = path[i]
            to_node = path[i + 1]

            # 查找投资记录
            investments = [
                inv for inv in self._investments
                if (inv.investor_name == from_node and inv.investee_name == to_node) or
                   (inv.investor_name == to_node and inv.investee_name == from_node)
            ]

            if investments:
                inv = investments[0]
                details.append({
                    "from": from_node,
                    "to": to_node,
                    "direction": "invests" if inv.investor_name == from_node else "invested_by",
                    "round": inv.round.value,
                    "amount": inv.amount,
                    "equity_ratio": inv.equity_ratio,
                    "date": inv.investment_date.isoformat() if inv.investment_date else None
                })
            else:
                details.append({
                    "from": from_node,
                    "to": to_node,
                    "direction": "unknown",
                    "round": None,
                    "amount": None,
                    "equity_ratio": None,
                    "date": None
                })

        return details

    def analyze_investor_preference(self, investor_name: str) -> Dict:
        """分析投资机构的投资偏好"""
        investments = self.get_investments_by_investor(investor_name)

        if not investments:
            return {
                "investor": investor_name,
                "total_investments": 0,
                "error": "No investment data found"
            }

        # 行业分布
        industry_count = defaultdict(int)
        for inv in investments:
            industry_count[inv.investee_industry] += 1

        # 轮次分布
        round_count = defaultdict(int)
        for inv in investments:
            round_count[inv.round.value] += 1

        # 投资金额统计
        total_amount = sum(inv.amount or 0 for inv in investments)
        avg_amount = total_amount / len(investments) if investments else 0

        # 持股比例统计
        avg_equity = sum(inv.equity_ratio or 0 for inv in investments) / len(investments) if investments else 0

        # 投资阶段偏好
        early_stage = sum(1 for inv in investments if inv.round in [
            InvestmentRound.ANGEL, InvestmentRound.PRE_A, InvestmentRound.A, InvestmentRound.B
        ])
        late_stage = sum(1 for inv in investments if inv.round in [
            InvestmentRound.C, InvestmentRound.D_PLUS, InvestmentRound.STRATEGIC, InvestmentRound.PE
        ])

        return {
            "investor": investor_name,
            "total_investments": len(investments),
            "total_amount": total_amount,
            "average_amount": avg_amount,
            "average_equity_ratio": avg_equity,
            "industry_preference": dict(industry_count),
            "round_preference": dict(round_count),
            "stage_preference": {
                "early_stage": early_stage,
                "late_stage": late_stage,
                "early_stage_ratio": early_stage / len(investments) if investments else 0
            },
            "top_investments": [
                {
                    "company": inv.investee_name,
                    "industry": inv.investee_industry,
                    "round": inv.round.value,
                    "amount": inv.amount,
                    "date": inv.investment_date.isoformat() if inv.investment_date else None
                }
                for inv in sorted(investments, key=lambda x: x.amount or 0, reverse=True)[:5]
            ]
        }

    def build_investment_network(
        self,
        center_entity: str = None,
        depth: int = 2,
        industries: List[str] = None
    ) -> InvestmentNetwork:
        """构建投资网络图谱"""
        nodes = []
        edges = []
        node_set = set()

        # 筛选投资记录
        if center_entity:
            # 以特定实体为中心
            center_investments = (
                self.get_investments_by_investor(center_entity) +
                self.get_investments_by_investee(center_entity)
            )
        elif industries:
            # 按行业筛选
            center_investments = []
            for industry in industries:
                center_investments.extend(self.get_investments_by_industry(industry))
        else:
            # 使用所有记录
            center_investments = self._investments

        # 添加节点和边
        for inv in center_investments:
            # 投资方节点
            if inv.investor_name not in node_set:
                inv_count = len(self.get_investments_by_investor(inv.investor_name))
                nodes.append({
                    "id": inv.investor_name,
                    "name": inv.investor_name,
                    "type": "investor",
                    "category": inv.investor_type.value,
                    "size": min(30, 5 + inv_count * 2),
                })
                node_set.add(inv.investor_name)

            # 被投资方节点
            if inv.investee_name not in node_set:
                nodes.append({
                    "id": inv.investee_name,
                    "name": inv.investee_name,
                    "type": "investee",
                    "category": inv.investee_industry,
                    "size": 15,
                })
                node_set.add(inv.investee_name)

            # 投资关系边
            edges.append({
                "source": inv.investor_name,
                "target": inv.investee_name,
                "type": "investment",
                "value": inv.amount or 0,
                "label": f"{inv.round.value}",
                "date": inv.investment_date.isoformat() if inv.investment_date else None
            })

        # 计算网络统计
        network_stats = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "density": len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0,
            "investor_count": len([n for n in nodes if n["type"] == "investor"]),
            "investee_count": len([n for n in nodes if n["type"] == "investee"]),
        }

        # 计算中心性（简化版）
        degree_cent = defaultdict(int)
        for edge in edges:
            degree_cent[edge["source"]] += 1
            degree_cent[edge["target"]] += 1

        # 关键节点
        key_players = sorted(
            [{"id": n["id"], "name": n["name"], "centrality": degree_cent.get(n["id"], 0)}
             for n in nodes],
            key=lambda x: x["centrality"],
            reverse=True
        )[:5]

        for player in key_players:
            if player["centrality"] > 3:
                player["role"] = "hub"
            elif player["centrality"] > 1:
                player["role"] = "connector"
            else:
                player["role"] = "leaf"

        return InvestmentNetwork(
            nodes=nodes,
            edges=edges,
            network_stats=network_stats,
            key_players=key_players
        )

    def analyze_investment_trend(
        self,
        industry: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> InvestmentTrend:
        """分析投资趋势"""
        # 默认时间范围：过去一年
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # 筛选投资记录
        filtered = self._investments
        if industry:
            filtered = [inv for inv in filtered if inv.investee_industry == industry]

        filtered = [
            inv for inv in filtered
            if inv.investment_date and start_date <= inv.investment_date <= end_date
        ]

        # 按月统计
        monthly_data = defaultdict(lambda: {"count": 0, "amount": 0})
        for inv in filtered:
            month_key = inv.investment_date.strftime("%Y-%m")
            monthly_data[month_key]["count"] += 1
            monthly_data[month_key]["amount"] += inv.amount or 0

        trend_data = [
            {"period": k, "count": v["count"], "amount": v["amount"]}
            for k, v in sorted(monthly_data.items())
        ]

        # 计算总额
        total_amount = sum(inv.amount or 0 for inv in filtered)
        avg_investment = total_amount / len(filtered) if filtered else 0

        # 热门投资者
        investor_count = defaultdict(int)
        for inv in filtered:
            investor_count[inv.investor_name] += 1
        top_investors = sorted(
            [{"name": k, "count": v} for k, v in investor_count.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        # 热门被投企业
        investee_count = defaultdict(int)
        for inv in filtered:
            investee_count[inv.investee_name] += 1
        top_investees = sorted(
            [{"name": k, "count": v} for k, v in investee_count.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        # 趋势判断
        if len(trend_data) >= 2:
            recent_avg = sum(d["count"] for d in trend_data[-3:]) / 3
            earlier_avg = sum(d["count"] for d in trend_data[:-3]) / max(1, len(trend_data) - 3)
            if recent_avg > earlier_avg * 1.2:
                trend_direction = "up"
                growth_rate = (recent_avg - earlier_avg) / max(1, earlier_avg) * 100
            elif recent_avg < earlier_avg * 0.8:
                trend_direction = "down"
                growth_rate = (recent_avg - earlier_avg) / max(1, earlier_avg) * 100
            else:
                trend_direction = "stable"
                growth_rate = (recent_avg - earlier_avg) / max(1, earlier_avg) * 100
        else:
            trend_direction = "stable"
            growth_rate = 0

        return InvestmentTrend(
            dimension="industry" if industry else "all",
            dimension_value=industry or "all",
            start_date=start_date,
            end_date=end_date,
            trend_data=trend_data,
            total_investments=len(filtered),
            total_amount=total_amount,
            avg_investment=avg_investment,
            top_investors=top_investors,
            top_investees=top_investees,
            trend_direction=trend_direction,
            growth_rate=growth_rate
        )

    def get_all_investments(self) -> List[InvestmentChain]:
        """获取所有投资记录"""
        return self._investments


# 全局服务实例
investment_chain_service = InvestmentChainService()
