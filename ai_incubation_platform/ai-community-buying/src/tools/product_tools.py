"""
商品工具 - 商品搜索、比较、推荐等原子能力

供 AI Agent 调用的商品领域工具集。
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from tools.base import BaseTool, ToolMetadata, ToolResponse

logger = logging.getLogger(__name__)


class SearchProductsTool(BaseTool):
    """商品搜索工具"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_products",
            description="搜索商品，支持关键词、类别、价格范围等多种过滤条件",
            version="1.0.0",
            tags=["product", "search", "core"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "category": {
                    "type": "string",
                    "description": "商品类别"
                },
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number", "description": "最低价格"},
                        "max": {"type": "number", "description": "最高价格"}
                    }
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "sort_by": {
                    "type": "string",
                    "description": "排序方式",
                    "enum": ["relevance", "price_asc", "price_desc", "sales", "rating"],
                    "default": "relevance"
                }
            },
            "required": []
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行商品搜索"""
        request_id = context.get("request_id") if context else None

        try:
            query = params.get("query", "")
            category = params.get("category")
            price_range = params.get("price_range")
            limit = params.get("limit", 10)
            sort_by = params.get("sort_by", "relevance")

            # 获取商品目录
            products = self._get_product_catalog()

            # 关键词过滤
            if query:
                products = [
                    p for p in products
                    if query.lower() in p["name"].lower() or
                       query.lower() in p.get("description", "").lower() or
                       any(query.lower() in tag.lower() for tag in p.get("tags", []))
                ]

            # 类别过滤
            if category:
                products = [p for p in products if p.get("category") == category]

            # 价格过滤
            if price_range:
                if "min" in price_range:
                    products = [p for p in products if p.get("group_price", 0) >= price_range["min"]]
                if "max" in price_range:
                    products = [p for p in products if p.get("group_price", 0) <= price_range["max"]]

            # 排序
            if sort_by == "price_asc":
                products.sort(key=lambda x: x.get("group_price", 0))
            elif sort_by == "price_desc":
                products.sort(key=lambda x: x.get("group_price", 0), reverse=True)
            elif sort_by == "sales":
                products.sort(key=lambda x: x.get("sales_count", 0), reverse=True)
            elif sort_by == "rating":
                products.sort(key=lambda x: x.get("rating", 0), reverse=True)

            # 截取结果
            results = products[:limit]

            self.logger.info(f"[{request_id}] 搜索完成：{len(results)} 个商品")

            return ToolResponse.ok(
                data={
                    "products": results,
                    "total": len(products),
                    "returned": len(results)
                },
                request_id=request_id
            )

        except Exception as e:
            self.logger.error(f"[{request_id}] 搜索失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _get_product_catalog(self) -> List[Dict]:
        """获取商品目录"""
        return [
            {
                "id": "p001", "name": "有机草莓", "description": "有机种植，新鲜采摘",
                "price": 49.9, "group_price": 35.9, "category": "水果",
                "rating": 4.9, "sales_count": 1580, "stock": 200,
                "origin": "辽宁丹东", "tags": ["有机", "新鲜", "当季"]
            },
            {
                "id": "p002", "name": "海南芒果", "description": "热带水果，甜度高核小",
                "price": 39.9, "group_price": 29.9, "category": "水果",
                "rating": 4.7, "sales_count": 2300, "stock": 500,
                "origin": "海南三亚", "tags": ["热带", "甜", "当季"]
            },
            {
                "id": "p003", "name": "进口蓝莓", "description": "富含花青素，护眼健康",
                "price": 59.9, "group_price": 45.9, "category": "水果",
                "rating": 4.8, "sales_count": 980, "stock": 150,
                "origin": "智利", "tags": ["进口", "健康", "护眼"]
            },
            {
                "id": "p040", "name": "进口牛奶箱装", "description": "欧盟进口，纯牛奶 24 盒",
                "price": 89.9, "group_price": 69.9, "category": "乳品",
                "rating": 4.9, "sales_count": 3200, "stock": 500,
                "origin": "德国", "tags": ["进口", "纯牛奶", "整箱"]
            },
            {
                "id": "p060", "name": "东北大米 10kg", "description": "黑土地五常大米",
                "price": 69.9, "group_price": 55.9, "category": "粮油",
                "rating": 4.9, "sales_count": 5200, "stock": 1000,
                "origin": "黑龙江五常", "tags": ["五常", "优质", "家庭装"]
            },
            {
                "id": "p050", "name": "混合坚果礼盒", "description": "多种坚果组合",
                "price": 79.9, "group_price": 59.9, "category": "零食",
                "rating": 4.7, "sales_count": 1500, "stock": 300,
                "origin": "国产", "tags": ["坚果", "健康", "礼盒"]
            }
        ]


class CompareProductsTool(BaseTool):
    """商品比较工具"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="compare_products",
            description="比较多个商品的差异，包括价格、规格、评价等维度",
            version="1.0.0",
            tags=["product", "compare", "analysis"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要比较的商品 ID 列表",
                    "minItems": 2,
                    "maxItems": 5
                },
                "compare_dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "比较维度",
                    "default": ["price", "rating", "sales", "origin"]
                }
            },
            "required": ["product_ids"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行商品比较"""
        request_id = context.get("request_id") if context else None

        try:
            product_ids = params.get("product_ids", [])
            dimensions = params.get("compare_dimensions", ["price", "rating", "sales", "origin"])

            # 获取商品详情
            catalog = self._get_product_catalog()
            products = [p for p in catalog if p["id"] in product_ids]

            if len(products) < 2:
                return ToolResponse.fail(error="至少需要 2 个商品进行比较", request_id=request_id)

            # 构建比较矩阵
            comparison = {
                "products": products,
                "dimensions": {},
                "recommendation": self._generate_recommendation(products)
            }

            # 各维度比较
            if "price" in dimensions:
                comparison["dimensions"]["price"] = {
                    "lowest": min(p["group_price"] for p in products),
                    "highest": max(p["group_price"] for p in products),
                    "details": {p["name"]: p["group_price"] for p in products}
                }

            if "rating" in dimensions:
                comparison["dimensions"]["rating"] = {
                    "highest": max(p["rating"] for p in products),
                    "lowest": min(p["rating"] for p in products),
                    "details": {p["name"]: p["rating"] for p in products}
                }

            if "sales" in dimensions:
                comparison["dimensions"]["sales"] = {
                    "most_popular": max(p["sales_count"] for p in products),
                    "details": {p["name"]: p["sales_count"] for p in products}
                }

            self.logger.info(f"[{request_id}] 商品比较完成：{len(products)} 个商品")

            return ToolResponse.ok(data=comparison, request_id=request_id)

        except Exception as e:
            self.logger.error(f"[{request_id}] 比较失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _get_product_catalog(self) -> List[Dict]:
        """获取商品目录（简化版）"""
        return [
            {"id": "p001", "name": "有机草莓", "group_price": 35.9, "rating": 4.9, "sales_count": 1580, "origin": "辽宁丹东"},
            {"id": "p002", "name": "海南芒果", "group_price": 29.9, "rating": 4.7, "sales_count": 2300, "origin": "海南三亚"},
            {"id": "p003", "name": "进口蓝莓", "group_price": 45.9, "rating": 4.8, "sales_count": 980, "origin": "智利"}
        ]

    def _generate_recommendation(self, products: List[Dict]) -> Dict[str, Any]:
        """生成推荐建议"""
        # 按性价比推荐（评分/价格）
        best_value = max(products, key=lambda p: p["rating"] / max(p["group_price"], 1))
        most_popular = max(products, key=lambda p: p["sales_count"])
        highest_rated = max(products, key=lambda p: p["rating"])

        return {
            "best_value": {"id": best_value["id"], "name": best_value["name"], "reason": "性价比最高"},
            "most_popular": {"id": most_popular["id"], "name": most_popular["name"], "reason": "销量最高"},
            "highest_rated": {"id": highest_rated["id"], "name": highest_rated["name"], "reason": "评分最高"}
        }


class GetProductDetailTool(BaseTool):
    """商品详情查询工具"""

    def __init__(self, db_session: Optional[Any] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_product_detail",
            description="获取商品的详细信息，包括规格、评价、库存等",
            version="1.0.0",
            tags=["product", "detail", "query"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "商品 ID"
                }
            },
            "required": ["product_id"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行商品详情查询"""
        request_id = context.get("request_id") if context else None

        try:
            product_id = params["product_id"]

            # 获取商品详情（模拟）
            detail = self._get_product_detail(product_id)

            if not detail:
                return ToolResponse.fail(error=f"商品不存在：{product_id}", request_id=request_id)

            self.logger.info(f"[{request_id}] 商品详情查询成功：{product_id}")

            return ToolResponse.ok(data={"product": detail}, request_id=request_id)

        except Exception as e:
            self.logger.error(f"[{request_id}] 查询失败：{str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)

    def _get_product_detail(self, product_id: str) -> Optional[Dict]:
        """获取商品详情"""
        catalog = {
            "p001": {
                "id": "p001", "name": "有机草莓", "description": "有机种植，新鲜采摘，当季热销",
                "price": 49.9, "group_price": 35.9, "category": "水果",
                "rating": 4.9, "review_count": 856, "sales_count": 1580, "stock": 200,
                "origin": "辽宁丹东", "shelf_life": "3 天", "storage": "冷藏",
                "tags": ["有机", "新鲜", "当季"],
                "specs": {"净重": "500g", "包装": "盒装", "产地": "辽宁丹东"},
                "images": ["strawberry_1.jpg", "strawberry_2.jpg"]
            },
            "p002": {
                "id": "p002", "name": "海南芒果", "description": "热带水果，甜度高核小肉厚",
                "price": 39.9, "group_price": 29.9, "category": "水果",
                "rating": 4.7, "review_count": 1200, "sales_count": 2300, "stock": 500,
                "origin": "海南三亚", "shelf_life": "5 天", "storage": "阴凉处",
                "tags": ["热带", "甜", "当季"],
                "specs": {"净重": "2.5kg", "包装": "箱装", "产地": "海南三亚"},
                "images": ["mango_1.jpg", "mango_2.jpg"]
            }
        }
        return catalog.get(product_id)


# 工具注册工厂
def init_product_tools(db_session: Optional[Any] = None) -> List[BaseTool]:
    """初始化工具"""
    return [
        SearchProductsTool(db_session),
        CompareProductsTool(db_session),
        GetProductDetailTool(db_session)
    ]
