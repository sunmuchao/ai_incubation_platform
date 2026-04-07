"""
股权穿透图分析 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict

from services.equity_analysis import equity_analysis_service
from models.investment import EquityOwnership

router = APIRouter(prefix="/api/equity", tags=["股权穿透分析"])


@router.get("/ownership/{company_id}", response_model=Dict)
async def get_equity_ownership(
    company_id: str,
    company_name: str = Query(..., description="公司名称")
):
    """
    获取公司股权穿透图
    返回完整的股权穿透结构、最终受益人、实际控制人
    """
    result = equity_analysis_service.analyze_equity_ownership(company_id, company_name)

    return {
        "company_id": result.company_id,
        "company_name": result.company_name,
        "beneficial_owners": result.beneficial_owners,
        "actual_controllers": result.actual_controllers,
        "visualization_data": result.visualization_data,
        "control_chain_analysis": result.control_chain_analysis,
        "risk_indicators": result.risk_indicators,
        "created_at": result.created_at.isoformat()
    }


@router.get("/shareholders/{company_id}", response_model=List[Dict])
async def get_shareholders(company_id: str):
    """获取公司直接股东列表"""
    shareholders = equity_analysis_service.get_shareholders(company_id)

    if not shareholders:
        raise HTTPException(status_code=404, detail="未找到该公司股东信息")

    return shareholders


@router.get("/beneficial-owners/{company_id}", response_model=List[Dict])
async def get_beneficial_owners(
    company_id: str,
    company_name: str = Query(..., description="公司名称"),
    threshold: float = Query(1.0, description="持股比例阈值 (%)")
):
    """获取最终受益人列表"""
    result = equity_analysis_service.analyze_equity_ownership(company_id, company_name)

    # 按阈值过滤
    filtered = [
        owner for owner in result.beneficial_owners
        if owner["total_ratio"] >= threshold
    ]

    return filtered


@router.get("/actual-controllers/{company_id}", response_model=List[Dict])
async def get_actual_controllers(
    company_id: str,
    company_name: str = Query(..., description="公司名称")
):
    """获取实际控制人列表"""
    result = equity_analysis_service.analyze_equity_ownership(company_id, company_name)
    return result.actual_controllers


@router.get("/risks/{company_id}", response_model=List[Dict])
async def get_equity_risks(
    company_id: str,
    company_name: str = Query(..., description="公司名称")
):
    """获取股权穿透风险识别结果"""
    result = equity_analysis_service.analyze_equity_ownership(company_id, company_name)
    return result.risk_indicators


@router.post("/shareholder/add", response_model=Dict)
async def add_shareholder(shareholder_data: Dict):
    """添加股东记录（管理接口）"""
    try:
        company_id = shareholder_data["company_id"]
        shareholder = {
            "name": shareholder_data["name"],
            "type": shareholder_data.get("type", "individual"),
            "ratio": shareholder_data.get("ratio", 0),
            "company_id": shareholder_data.get("company_id"),
            "voting_ratio": shareholder_data.get("voting_ratio"),
            "identity_masked": shareholder_data.get("identity_masked"),
        }

        equity_analysis_service.add_shareholder(company_id, shareholder)

        return {"status": "success", "message": "股东记录添加成功"}

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"缺少必要字段：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree/{company_id}", response_model=Dict)
async def get_equity_tree(
    company_id: str,
    company_name: str = Query(..., description="公司名称"),
    max_depth: int = Query(5, description="最大穿透深度")
):
    """
    获取完整股权穿透图（树形结构）
    用于前端可视化展示
    """
    result = equity_analysis_service.analyze_equity_ownership(company_id, company_name)

    def serialize_node(node):
        if not node:
            return None

        return {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
            "direct_ratio": node.direct_ratio,
            "indirect_ratio": node.indirect_ratio,
            "total_ratio": node.total_ratio,
            "voting_ratio": node.voting_ratio,
            "is_actual_controller": node.is_actual_controller,
            "is_beneficial_owner": node.is_beneficial_owner,
            "level": node.level,
            "identity_masked": node.identity_masked,
            "children": [serialize_node(child) for child in node.children]
        }

    return {
        "company_id": company_id,
        "company_name": company_name,
        "tree": serialize_node(result.ownership_tree),
        "max_depth": result.control_chain_analysis.get("max_depth", 0),
        "longest_chain": result.control_chain_analysis.get("longest_chain", []),
    }
