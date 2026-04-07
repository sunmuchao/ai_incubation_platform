"""
投资关系链分析 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime

from services.investment_chain_service import investment_chain_service
from models.investment import InvestmentChain, InvestmentNetwork, InvestmentTrend

router = APIRouter(prefix="/api/investment", tags=["投资关系链分析"])


@router.get("/list", response_model=List[Dict])
async def list_investments(
    investor: Optional[str] = Query(None, description="投资方名称"),
    investee: Optional[str] = Query(None, description="被投资方名称"),
    industry: Optional[str] = Query(None, description="行业"),
    limit: int = Query(100, description="返回数量限制")
):
    """获取投资记录列表"""
    if investor:
        investments = investment_chain_service.get_investments_by_investor(investor)
    elif investee:
        investments = investment_chain_service.get_investments_by_investee(investee)
    elif industry:
        investments = investment_chain_service.get_investments_by_industry(industry)
    else:
        investments = investment_chain_service.get_all_investments()

    # 限制返回数量
    investments = investments[:limit]

    return [
        {
            "id": inv.id,
            "investor_name": inv.investor_name,
            "investor_type": inv.investor_type.value,
            "investee_name": inv.investee_name,
            "investee_industry": inv.investee_industry,
            "round": inv.round.value,
            "amount": inv.amount,
            "amount_currency": inv.amount_currency,
            "investment_date": inv.investment_date.isoformat() if inv.investment_date else None,
            "equity_ratio": inv.equity_ratio,
            "status": inv.status,
            "tags": inv.tags,
        }
        for inv in investments
    ]


@router.get("/investor/{investor_name}", response_model=Dict)
async def get_investor_profile(investor_name: str):
    """获取投资方画像和投资偏好分析"""
    profile = investment_chain_service.analyze_investor_preference(investor_name)

    if "error" in profile:
        raise HTTPException(status_code=404, detail=profile["error"])

    return profile


@router.get("/path", response_model=List[Dict])
async def find_investment_path(
    source: str = Query(..., description="起始实体（投资方或公司）"),
    target: str = Query(..., description="目标实体（投资方或公司）"),
    max_depth: int = Query(5, description="最大搜索深度")
):
    """查找两个实体之间的投资路径"""
    path = investment_chain_service.find_investment_path(source, target, max_depth)

    if not path:
        raise HTTPException(
            status_code=404,
            detail=f"未找到从 {source} 到 {target} 的投资路径"
        )

    return path


@router.get("/network", response_model=Dict)
async def get_investment_network(
    center_entity: Optional[str] = Query(None, description="中心实体"),
    industries: Optional[str] = Query(None, description="行业列表（逗号分隔）"),
    depth: int = Query(2, description="网络深度")
):
    """获取投资网络图谱数据"""
    industry_list = [i.strip() for i in industries.split(",")] if industries else None

    network = investment_chain_service.build_investment_network(
        center_entity=center_entity,
        depth=depth,
        industries=industry_list
    )

    return {
        "nodes": network.nodes,
        "edges": network.edges,
        "network_stats": network.network_stats,
        "key_players": network.key_players,
    }


@router.get("/trend", response_model=Dict)
async def get_investment_trend(
    industry: Optional[str] = Query(None, description="行业"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """分析投资趋势"""
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误，应为 YYYY-MM-DD")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为 YYYY-MM-DD")

    trend = investment_chain_service.analyze_investment_trend(
        industry=industry,
        start_date=start_dt,
        end_date=end_dt
    )

    return {
        "dimension": trend.dimension,
        "dimension_value": trend.dimension_value,
        "start_date": trend.start_date.isoformat() if trend.start_date else None,
        "end_date": trend.end_date.isoformat() if trend.end_date else None,
        "trend_data": trend.trend_data,
        "total_investments": trend.total_investments,
        "total_amount": trend.total_amount,
        "avg_investment": trend.avg_investment,
        "top_investors": trend.top_investors,
        "top_investees": trend.top_investees,
        "trend_direction": trend.trend_direction,
        "growth_rate": trend.growth_rate,
    }


@router.post("/add", response_model=Dict)
async def add_investment(investment_data: Dict):
    """添加投资记录（管理接口）"""
    try:
        investment = InvestmentChain(
            investor_id=investment_data.get("investor_id", f"INV-{investment_data['investor_name']}"),
            investor_name=investment_data["investor_name"],
            investor_type=investment_data.get("investor_type", "vc"),
            investee_id=investment_data.get("investee_id", f"ENT-{investment_data['investee_name']}"),
            investee_name=investment_data["investee_name"],
            investee_industry=investment_data.get("investee_industry", ""),
            round=investment_data.get("round", "a"),
            amount=investment_data.get("amount"),
            investment_date=datetime.fromisoformat(investment_data["investment_date"]) if investment_data.get("investment_date") else None,
            equity_ratio=investment_data.get("equity_ratio"),
            status=investment_data.get("status", "completed"),
            source=investment_data.get("source", ""),
            description=investment_data.get("description", ""),
        )

        investment_chain_service.add_investment(investment)

        return {"status": "success", "message": "投资记录添加成功", "id": investment.id}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"缺少必要字段：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
