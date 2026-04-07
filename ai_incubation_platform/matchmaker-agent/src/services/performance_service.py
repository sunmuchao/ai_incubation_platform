"""
性能优化服务模块

v1.23 新增功能：
- 缓存预热机制
- 慢查询日志与分析
- API 响应性能监控
- 性能统计仪表板
"""
import time
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
import threading
from utils.logger import logger
from cache import cache_manager


@dataclass
class QueryPerformance:
    """查询性能记录"""
    query_name: str
    execution_time: float  # 毫秒
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict = field(default_factory=dict)
    result_count: int = 0


@dataclass
class ApiPerformance:
    """API 性能记录"""
    endpoint: str
    method: str
    response_time: float  # 毫秒
    status_code: int
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None


class SlowQueryLogger:
    """
    慢查询日志器

    记录超过阈值的查询，用于性能分析和优化
    """

    def __init__(self, threshold_ms: float = 100.0):
        self.threshold_ms = threshold_ms
        self._slow_queries: List[QueryPerformance] = []
        self._lock = threading.Lock()
        self._max_entries = 1000

    def log_query(
        self,
        query_name: str,
        execution_time: float,
        params: Optional[Dict] = None,
        result_count: int = 0
    ) -> None:
        """记录查询性能"""
        if execution_time >= self.threshold_ms:
            record = QueryPerformance(
                query_name=query_name,
                execution_time=execution_time,
                params=params or {},
                result_count=result_count
            )
            with self._lock:
                self._slow_queries.append(record)
                # 保持记录数量在限制内
                if len(self._slow_queries) > self._max_entries:
                    self._slow_queries = self._slow_queries[-self._max_entries:]

            logger.warning(
                f"Slow query detected: {query_name}, "
                f"execution_time={execution_time:.2f}ms, "
                f"params={params}, "
                f"result_count={result_count}"
            )

    def get_slow_queries(
        self,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[QueryPerformance]:
        """获取慢查询列表"""
        with self._lock:
            queries = self._slow_queries.copy()

        if since:
            queries = [q for q in queries if q.timestamp >= since]

        # 按执行时间降序排列
        queries.sort(key=lambda q: q.execution_time, reverse=True)
        return queries[:limit]

    def get_stats(self) -> Dict:
        """获取慢查询统计"""
        with self._lock:
            queries = self._slow_queries.copy()

        if not queries:
            return {
                "total_slow_queries": 0,
                "avg_execution_time": 0,
                "max_execution_time": 0,
                "slowest_query": None
            }

        execution_times = [q.execution_time for q in queries]

        # 按查询名分组统计
        query_stats = defaultdict(list)
        for q in queries:
            query_stats[q.query_name].append(q.execution_time)

        top_slow_queries = []
        for name, times in sorted(query_stats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)[:5]:
            top_slow_queries.append({
                "query_name": name,
                "count": len(times),
                "avg_time": sum(times) / len(times),
                "max_time": max(times)
            })

        return {
            "total_slow_queries": len(queries),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "min_execution_time": min(execution_times),
            "threshold_ms": self.threshold_ms,
            "slowest_query": queries[0].query_name if queries else None,
            "top_slow_queries": top_slow_queries
        }

    def clear(self) -> None:
        """清空慢查询日志"""
        with self._lock:
            self._slow_queries.clear()


class PerformanceMonitor:
    """
    性能监控器

    监控 API 响应时间和系统性能指标
    """

    def __init__(self):
        self._api_records: List[ApiPerformance] = []
        self._lock = threading.Lock()
        self._max_entries = 10000
        self._start_time = datetime.now()

    def record_api(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_id: Optional[str] = None
    ) -> None:
        """记录 API 性能"""
        record = ApiPerformance(
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=status_code,
            user_id=user_id
        )

        with self._lock:
            self._api_records.append(record)
            if len(self._api_records) > self._max_entries:
                self._api_records = self._api_records[-self._max_entries:]

    def get_api_stats(
        self,
        endpoint: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict:
        """获取 API 性能统计"""
        with self._lock:
            records = self._api_records.copy()

        if since:
            records = [r for r in records if r.timestamp >= since]

        if endpoint:
            records = [r for r in records if r.endpoint == endpoint]

        if not records:
            return {
                "total_requests": 0,
                "avg_response_time": 0,
                "p50_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
                "error_rate": 0
            }

        response_times = sorted([r.response_time for r in records])
        error_count = sum(1 for r in records if r.status_code >= 400)

        return {
            "total_requests": len(records),
            "avg_response_time": sum(response_times) / len(response_times),
            "p50_response_time": self._percentile(response_times, 50),
            "p95_response_time": self._percentile(response_times, 95),
            "p99_response_time": self._percentile(response_times, 99),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "error_rate": error_count / len(records),
            "error_count": error_count
        }

    def get_slow_endpoints(self, limit: int = 10) -> List[Dict]:
        """获取最慢的 API 端点"""
        with self._lock:
            records = self._api_records.copy()

        # 按端点分组
        endpoint_stats = defaultdict(list)
        for r in records:
            endpoint_stats[r.endpoint].append(r.response_time)

        # 计算每个端点的平均响应时间
        avg_times = []
        for endpoint, times in endpoint_stats.items():
            avg_times.append({
                "endpoint": endpoint,
                "avg_response_time": sum(times) / len(times),
                "p95_response_time": self._percentile(sorted(times), 95),
                "request_count": len(times)
            })

        # 按平均响应时间排序
        avg_times.sort(key=lambda x: x["avg_response_time"], reverse=True)
        return avg_times[:limit]

    def get_uptime(self) -> timedelta:
        """获取运行时长"""
        return datetime.now() - self._start_time

    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not sorted_data:
            return 0
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

    def clear(self) -> None:
        """清空性能记录"""
        with self._lock:
            self._api_records.clear()


class CacheWarmer:
    """
    缓存预热器

    在后台预热常用数据到缓存，提升访问速度
    """

    def __init__(self):
        self._warm_tasks: Dict[str, Callable] = {}
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def register_warm_task(
        self,
        name: str,
        task: Callable[[], Any],
        interval_seconds: int = 300,
        cache_key: Optional[str] = None
    ) -> None:
        """注册预热任务"""
        self._warm_tasks[name] = {
            "task": task,
            "interval": interval_seconds,
            "cache_key": cache_key or f"warm:{name}",
            "last_run": None
        }
        logger.info(f"Cache warm task registered: {name}")

    def start_background_warming(self) -> None:
        """启动后台预热"""
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._warming_loop, daemon=True)
        self._thread.start()
        logger.info("Cache warming started in background")

    def stop_background_warming(self) -> None:
        """停止后台预热"""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Cache warming stopped")

    def _warming_loop(self) -> None:
        """预热循环"""
        while self._is_running:
            current_time = time.time()

            for name, config in self._warm_tasks.items():
                last_run = config["last_run"]
                interval = config["interval"]

                if last_run is None or (current_time - last_run) >= interval:
                    try:
                        logger.info(f"Warming cache for: {name}")
                        result = config["task"]()

                        # 将结果存入缓存
                        cache_key = config["cache_key"]
                        cache_manager.get_instance().set_cache_item(
                            cache_key,
                            result,
                            timedelta(seconds=interval * 2)
                        )

                        config["last_run"] = current_time
                        logger.info(f"Cache warmed successfully: {name}")
                    except Exception as e:
                        logger.error(f"Cache warm failed for {name}: {e}")

            # 休眠 10 秒后再次检查
            time.sleep(10)

    def warm_now(self, name: str) -> bool:
        """立即执行预热任务"""
        if name not in self._warm_tasks:
            logger.warning(f"Warm task not found: {name}")
            return False

        config = self._warm_tasks[name]
        try:
            result = config["task"]()
            cache_key = config["cache_key"]
            cache_manager.get_instance().set_cache_item(
                cache_key,
                result,
                timedelta(seconds=config["interval"] * 2)
            )
            config["last_run"] = time.time()
            logger.info(f"Cache warmed on demand: {name}")
            return True
        except Exception as e:
            logger.error(f"Cache warm failed for {name}: {e}")
            return False


class PerformanceService:
    """
    性能服务

    统一的性能优化服务入口
    """

    _instance: Optional["PerformanceService"] = None

    def __new__(cls) -> "PerformanceService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.slow_query_logger = SlowQueryLogger(threshold_ms=100.0)
        self.performance_monitor = PerformanceMonitor()
        self.cache_warmer = CacheWarmer()
        self._initialized = True

        logger.info("PerformanceService initialized")

    @classmethod
    def get_instance(cls) -> "PerformanceService":
        """获取单例实例"""
        return cls()

    def get_performance_dashboard(self) -> Dict:
        """获取性能仪表板数据"""
        cache_stats = cache_manager.get_instance().get_cache_stats()

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": self.performance_monitor.get_uptime().total_seconds(),
            "cache": cache_stats,
            "api_performance": self.performance_monitor.get_api_stats(),
            "slow_queries": self.slow_query_logger.get_stats(),
            "slow_endpoints": self.performance_monitor.get_slow_endpoints(limit=5)
        }

    def get_optimization_suggestions(self) -> List[Dict]:
        """获取性能优化建议"""
        suggestions = []

        # 检查慢查询
        slow_stats = self.slow_query_logger.get_stats()
        if slow_stats["total_slow_queries"] > 0:
            for sq in slow_stats.get("top_slow_queries", [])[:3]:
                suggestions.append({
                    "type": "slow_query",
                    "severity": "high" if sq["avg_time"] > 500 else "medium",
                    "query": sq["query_name"],
                    "avg_time_ms": round(sq["avg_time"], 2),
                    "suggestion": f"考虑为 {sq['query_name']} 查询添加索引或优化查询逻辑"
                })

        # 检查慢 API
        slow_endpoints = self.performance_monitor.get_slow_endpoints(limit=3)
        for ep in slow_endpoints:
            if ep["avg_response_time"] > 200:
                suggestions.append({
                    "type": "slow_api",
                    "severity": "high" if ep["avg_response_time"] > 500 else "medium",
                    "endpoint": ep["endpoint"],
                    "avg_response_time_ms": round(ep["avg_response_time"], 2),
                    "suggestion": f"考虑对 {ep['endpoint']} 接口进行缓存优化或异步处理"
                })

        # 检查缓存命中率
        cache_stats = cache_manager.get_instance().get_cache_stats()
        if not cache_stats.get("redis_available", False):
            suggestions.append({
                "type": "cache_configuration",
                "severity": "medium",
                "suggestion": "建议配置 Redis 缓存以提升性能"
            })

        return suggestions


# 性能监控装饰器
def performance_monitor(query_name: str):
    """
    性能监控装饰器

    用法:
        @performance_monitor("get_user_profile")
        def get_user_profile(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000  # 毫秒

                # 记录性能
                perf_service = PerformanceService.get_instance()
                perf_service.slow_query_logger.log_query(
                    query_name=query_name,
                    execution_time=execution_time,
                    params={"args_count": len(args), "kwargs_count": len(kwargs)},
                    result_count=1
                )

                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Query failed: {query_name}, execution_time={execution_time:.2f}ms, error={e}")
                raise

        return wrapper
    return decorator


# 全局性能服务实例
perf_service = PerformanceService.get_instance()
