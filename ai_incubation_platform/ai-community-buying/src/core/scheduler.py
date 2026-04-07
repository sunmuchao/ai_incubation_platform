"""
定时任务模块

提供后台定时任务，用于：
1. 清理过期团购
2. 发送库存预警通知
3. 数据清理和维护
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import threading

logger = logging.getLogger(__name__)


class ScheduledTask:
    """
    定时任务基类

    子类需要实现 run() 方法来定义任务逻辑。
    """

    def __init__(self, name: str, interval_seconds: int):
        self.name = name
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run_async(self, db_session_factory):
        """异步执行任务"""
        while self._running:
            try:
                logger.info(f"执行定时任务：{self.name}")
                await self.execute(db_session_factory)
            except Exception as e:
                logger.error(f"定时任务 {self.name} 执行失败：{e}", exc_info=True)

            await asyncio.sleep(self.interval_seconds)

    async def execute(self, db_session_factory):
        """
        执行任务逻辑（子类实现）

        Args:
            db_session_factory: 数据库会话工厂
        """
        raise NotImplementedError


class CleanupExpiredGroupsTask(ScheduledTask):
    """
    清理过期团购任务

    定期检查并处理过期的团购。
    """

    def __init__(self, interval_seconds: int = 300):  # 默认 5 分钟
        super().__init__("cleanup_expired_groups", interval_seconds)

    async def execute(self, db_session_factory):
        """清理过期团购"""
        from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced
        from models.entities import GroupBuyEntity
        from datetime import datetime

        db = db_session_factory()
        try:
            service = GroupBuyServiceEnhanced(db)
            service._cleanup_expired_groups()
            logger.info("过期团购清理完成")
        except Exception as e:
            logger.error(f"清理过期团购失败：{e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()


class StockAlertTask(ScheduledTask):
    """
    库存预警检查任务

    定期检查库存水平，发送预警通知。
    """

    def __init__(
        self,
        interval_seconds: int = 600,  # 默认 10 分钟
        alert_threshold: int = 10,
        critical_threshold: int = 5
    ):
        super().__init__("stock_alert_check", interval_seconds)
        self.alert_threshold = alert_threshold
        self.critical_threshold = critical_threshold

    async def execute(self, db_session_factory):
        """检查库存预警"""
        from models.entities import ProductEntity, ProductStatus
        from services.notification_facade import NotificationServiceFacade

        db = db_session_factory()
        try:
            # 查询低库存商品
            low_stock_products = db.query(ProductEntity).filter(
                ProductEntity.status == ProductStatus.ACTIVE,
                (ProductEntity.stock - ProductEntity.locked_stock) <= self.alert_threshold
            ).all()

            if not low_stock_products:
                logger.debug("库存检查：无预警商品")
                return

            facade = NotificationServiceFacade(db)
            alerted_count = 0

            for product in low_stock_products:
                available_stock = product.stock - product.locked_stock
                result = facade.send_stock_alert(
                    product_id=product.id,
                    product_name=product.name,
                    current_stock=available_stock
                )
                if result:
                    alerted_count += 1
                    logger.info(
                        f"发送库存预警：{product.name}, 库存={available_stock}"
                    )

            logger.info(f"库存预警检查完成，发送 {alerted_count} 条预警")
        except Exception as e:
            logger.error(f"库存预警检查失败：{e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()


class TaskScheduler:
    """
    任务调度器

    管理和运行多个定时任务。
    """

    def __init__(self, db_session_factory=None):
        self.tasks: list[ScheduledTask] = []
        self._running = False
        self._db_session_factory = db_session_factory
        self._task_runners: list[asyncio.Task] = []

    def add_task(self, task: ScheduledTask):
        """添加定时任务"""
        self.tasks.append(task)
        logger.info(f"添加定时任务：{task.name}, 间隔={task.interval_seconds}s")

    def start(self):
        """启动所有定时任务"""
        if self._running:
            logger.warning("任务调度器已在运行中")
            return

        self._running = True
        logger.info(f"启动任务调度器，共 {len(self.tasks)} 个任务")

        # 在后台线程中运行异步事件循环
        def run_event_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_all_tasks():
                self._task_runners = []
                for task in self.tasks:
                    task._running = True
                    runner = asyncio.create_task(
                        task.run_async(self._db_session_factory)
                    )
                    self._task_runners.append(runner)

                await asyncio.gather(*self._task_runners, return_exceptions=True)

            loop.run_until_complete(run_all_tasks())
            loop.close()

        self._thread = threading.Thread(target=run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止所有定时任务"""
        if not self._running:
            return

        logger.info("停止任务调度器...")
        self._running = False

        for task in self.tasks:
            task._running = False

        # 等待任务结束
        if hasattr(self, '_thread'):
            self._thread.join(timeout=5)

        logger.info("任务调度器已停止")


# 全局调度器实例
_scheduler: Optional[TaskScheduler] = None


def init_scheduler(db_session_factory) -> TaskScheduler:
    """
    初始化任务调度器

    Args:
        db_session_factory: 数据库会话工厂

    Returns:
        任务调度器实例
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    _scheduler = TaskScheduler(db_session_factory)

    # 添加默认任务
    _scheduler.add_task(CleanupExpiredGroupsTask(interval_seconds=300))
    _scheduler.add_task(StockAlertTask(interval_seconds=600))

    return _scheduler


def get_scheduler() -> Optional[TaskScheduler]:
    """获取任务调度器实例"""
    return _scheduler


def start_scheduler():
    """启动任务调度器"""
    if _scheduler:
        _scheduler.start()


def stop_scheduler():
    """停止任务调度器"""
    if _scheduler:
        _scheduler.stop()
