"""
LLM 成本监控服务

提供 LLM 调用指标的记录、统计和成本控制功能：
1. 记录每次 LLM 调用的 token 消耗
2. 统计每日/每周/每月使用情况
3. 成本估算和预警
4. 使用趋势分析
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract
import json

from db.models import LLMMetricsDB, UserDB
from utils.logger import logger
from config import settings


# LLM 定价（每 1000 tokens 的价格，单位：元）
# 参考价格，实际价格可能有所不同
LLM_PRICING = {
    "openai": {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    },
    "qwen": {
        "qwen-turbo": {"input": 0.002, "output": 0.006},
        "qwen-plus": {"input": 0.004, "output": 0.012},
        "qwen-max": {"input": 0.01, "output": 0.03},
    },
    "glm": {
        "glm-4": {"input": 0.05, "output": 0.1},
        "glm-3-turbo": {"input": 0.005, "output": 0.01},
    },
}

# 默认价格（当模型不在列表中时）
DEFAULT_PRICING = {"input": 0.01, "output": 0.03}


class LLMMetricsService:
    """LLM 成本监控服务"""

    def __init__(self, db: Session):
        self.db = db
        self.daily_token_limit = getattr(settings, 'llm_daily_token_limit', 100000)

    def record_metric(
        self,
        endpoint: str,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: int,
        user_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> LLMMetricsDB:
        """
        记录 LLM 调用指标

        Args:
            endpoint: API 端点
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            response_time_ms: 响应时间（毫秒）
            user_id: 用户 ID
            status: 状态（success, error, timeout）
            error_message: 错误信息
            provider: LLM 提供商
            model: 模型名称

        Returns:
            创建的指标记录
        """
        import uuid

        total_tokens = input_tokens + output_tokens
        estimated_cost = self._calculate_cost(
            input_tokens, output_tokens, provider, model
        )

        metric = LLMMetricsDB(
            id=str(uuid.uuid4()),
            endpoint=endpoint,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            response_status=status,
            error_message=error_message,
            response_time_ms=response_time_ms
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)

        # 检查是否接近每日限制
        self._check_daily_limit()

        return metric

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str],
        model: Optional[str]
    ) -> float:
        """计算估算成本"""
        if not provider or not model:
            # 使用默认价格
            return (input_tokens * DEFAULT_PRICING["input"] +
                    output_tokens * DEFAULT_PRICING["output"]) / 1000

        # 获取定价
        pricing = LLM_PRICING.get(provider, {}).get(model, DEFAULT_PRICING)

        input_cost = input_tokens * pricing.get("input", DEFAULT_PRICING["input"]) / 1000
        output_cost = output_tokens * pricing.get("output", DEFAULT_PRICING["output"]) / 1000

        return round(input_cost + output_cost, 6)

    def _check_daily_limit(self):
        """检查每日 token 限制"""
        today = datetime.utcnow().date()
        today_tokens = self.get_daily_usage(today)

        if today_tokens > self.daily_token_limit * 0.8:
            logger.warning(
                f"LLM 今日 token 使用量已达 {today_tokens}/{self.daily_token_limit} "
                f"({today_tokens/self.daily_token_limit*100:.1f}%)"
            )

    def get_daily_usage(
        self,
        date: Optional[datetime] = None
    ) -> int:
        """获取指定日期的 token 使用量"""
        if date is None:
            date = datetime.utcnow().date()

        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        result = self.db.query(
            func.sum(LLMMetricsDB.total_tokens)
        ).filter(
            and_(
                LLMMetricsDB.created_at >= start_date,
                LLMMetricsDB.created_at < end_date
            )
        ).scalar()

        return result or 0

    def get_daily_cost(
        self,
        date: Optional[datetime] = None
    ) -> float:
        """获取指定日期的成本"""
        if date is None:
            date = datetime.utcnow().date()

        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        result = self.db.query(
            func.sum(LLMMetricsDB.estimated_cost)
        ).filter(
            and_(
                LLMMetricsDB.created_at >= start_date,
                LLMMetricsDB.created_at < end_date
            )
        ).scalar()

        return round(result or 0, 4)

    def get_usage_stats(
        self,
        days: int = 7,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        获取使用情况统计

        Args:
            days: 统计天数
            group_by: 分组维度（day, week, month）

        Returns:
            使用统计信息
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 总使用量
        total_usage = self.db.query(
            func.sum(LLMMetricsDB.total_tokens).label("total_tokens"),
            func.sum(LLMMetricsDB.estimated_cost).label("total_cost"),
            func.count(LLMMetricsDB.id).label("total_calls"),
            func.avg(LLMMetricsDB.response_time_ms).label("avg_response_time")
        ).filter(
            LLMMetricsDB.created_at >= start_date
        ).first()

        # 按天统计
        daily_stats = []
        for i in range(days):
            date = end_date.date() - timedelta(days=days - i - 1)
            daily_usage = self.get_daily_usage(date)
            daily_cost = self.get_daily_cost(date)
            daily_stats.append({
                "date": date.isoformat(),
                "tokens": daily_usage,
                "cost": daily_cost
            })

        # 按端点统计
        endpoint_stats = self.db.query(
            LLMMetricsDB.endpoint,
            func.sum(LLMMetricsDB.total_tokens).label("tokens"),
            func.sum(LLMMetricsDB.estimated_cost).label("cost"),
            func.count(LLMMetricsDB.id).label("calls")
        ).filter(
            LLMMetricsDB.created_at >= start_date
        ).group_by(LLMMetricsDB.endpoint).order_by(
            desc("tokens")
        ).all()

        # 错误统计
        error_count = self.db.query(
            func.count(LLMMetricsDB.id)
        ).filter(
            and_(
                LLMMetricsDB.created_at >= start_date,
                LLMMetricsDB.response_status == "error"
            )
        ).scalar()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "totals": {
                "tokens": total_usage.total_tokens or 0,
                "cost": round(total_usage.total_cost or 0, 4),
                "calls": total_usage.total_calls or 0,
                "avg_response_time_ms": round(total_usage.avg_response_time_ms or 0, 2)
            },
            "daily_stats": daily_stats,
            "endpoint_stats": [
                {
                    "endpoint": s.endpoint,
                    "tokens": s.tokens or 0,
                    "cost": round(s.cost or 0, 4),
                    "calls": s.calls or 0
                }
                for s in endpoint_stats
            ],
            "error_rate": round((error_count / max(1, total_usage.total_calls)) * 100, 2),
            "daily_limit": self.daily_token_limit,
            "today_usage": self.get_daily_usage(),
            "today_remaining": max(0, self.daily_token_limit - self.get_daily_usage())
        }

    def get_user_usage(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取指定用户的使用情况"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        result = self.db.query(
            func.sum(LLMMetricsDB.total_tokens).label("total_tokens"),
            func.sum(LLMMetricsDB.estimated_cost).label("total_cost"),
            func.count(LLMMetricsDB.id).label("total_calls")
        ).filter(
            and_(
                LLMMetricsDB.user_id == user_id,
                LLMMetricsDB.created_at >= start_date
            )
        ).first()

        return {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "totals": {
                "tokens": result.total_tokens or 0,
                "cost": round(result.total_cost or 0, 4),
                "calls": result.total_calls or 0
            }
        }

    def get_top_users(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取使用量最高的用户"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        users = self.db.query(
            LLMMetricsDB.user_id,
            func.sum(LLMMetricsDB.total_tokens).label("total_tokens"),
            func.sum(LLMMetricsDB.estimated_cost).label("total_cost"),
            func.count(LLMMetricsDB.id).label("total_calls")
        ).filter(
            and_(
                LLMMetricsDB.user_id.isnot(None),
                LLMMetricsDB.created_at >= start_date
            )
        ).group_by(LLMMetricsDB.user_id).order_by(
            desc("total_tokens")
        ).limit(limit).all()

        return [
            {
                "user_id": u.user_id,
                "tokens": u.total_tokens or 0,
                "cost": round(u.total_cost or 0, 4),
                "calls": u.total_calls or 0
            }
            for u in users
        ]


# 工厂函数
def get_llm_metrics_service(db: Session) -> LLMMetricsService:
    """获取 LLM 指标服务实例"""
    return LLMMetricsService(db)
