"""
数据库迁移脚本 - P5 迭代 (v1.0.0)

添加以下新表：
- dashboard_snapshots - 仪表板快照表
- dashboard_metric_configs - 仪表板指标配置表
- dashboard_alerts - 仪表板告警表
- organizations - 组织表
- team_members - 团队成员表
- roles - 角色表
- permissions - 权限定义表
- team_invitations - 团队邀请表
- organization_audit_logs - 组织审计日志表
"""
import asyncio
import sys
import os

# 支持从不同目录执行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from sqlalchemy import text
from database import create_db_and_tables, engine, Base
from models.dashboard import DashboardSnapshotDB, DashboardMetricConfigDB, DashboardAlertDB
from models.team import OrganizationDB, TeamMemberDB, RoleDB, PermissionDB, TeamInvitationDB, OrganizationAuditLogDB


async def run_migration():
    """运行数据库迁移。"""
    print("Starting database migration for P5 (v1.0.0)...")

    # 创建所有表（包括新表）
    print("Creating database tables...")
    await create_db_and_tables()

    # 插入默认指标配置
    print("Inserting default metric configurations...")
    await insert_default_metric_configs()

    # 初始化系统角色
    print("Initializing system roles...")
    await initialize_system_roles()

    print("Migration completed successfully!")


async def insert_default_metric_configs():
    """插入默认仪表板指标配置。"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_engine = create_async_engine(
        os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/ai_hires_human"),
        echo=False,
    )
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 检查是否已存在配置
        result = await session.execute(
            text("SELECT COUNT(*) FROM dashboard_metric_configs")
        )
        count = result.scalar()
        if count > 0:
            print("  Metric configs already exist, skipping...")
            return

        # 任务指标
        task_metrics = [
            {
                "metric_key": "total_tasks",
                "metric_name": "任务总数",
                "metric_category": "tasks",
                "calculation_method": "count",
                "data_source": "tasks",
                "display_type": "number",
                "unit": "个",
                "precision": 0,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "task_completion_rate",
                "metric_name": "任务完成率",
                "metric_category": "tasks",
                "calculation_method": "ratio",
                "data_source": "tasks",
                "display_type": "percentage",
                "unit": "%",
                "precision": 2,
                "threshold_warning": 70.0,
                "threshold_critical": 50.0,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "avg_completion_time",
                "metric_name": "平均完成时间",
                "metric_category": "tasks",
                "calculation_method": "avg",
                "data_source": "tasks",
                "display_type": "number",
                "unit": "小时",
                "precision": 2,
                "update_frequency": "hourly",
            },
        ]

        # 工人指标
        worker_metrics = [
            {
                "metric_key": "active_workers",
                "metric_name": "活跃工人数",
                "metric_category": "workers",
                "calculation_method": "count",
                "data_source": "worker_submissions",
                "display_type": "number",
                "unit": "人",
                "precision": 0,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "avg_worker_rating",
                "metric_name": "工人平均评分",
                "metric_category": "workers",
                "calculation_method": "avg",
                "data_source": "worker_profiles",
                "display_type": "number",
                "unit": "分",
                "precision": 2,
                "threshold_warning": 4.0,
                "threshold_critical": 3.0,
                "update_frequency": "daily",
            },
        ]

        # 质量指标
        quality_metrics = [
            {
                "metric_key": "approval_rate",
                "metric_name": "验收通过率",
                "metric_category": "quality",
                "calculation_method": "ratio",
                "data_source": "tasks",
                "display_type": "percentage",
                "unit": "%",
                "precision": 2,
                "threshold_warning": 80.0,
                "threshold_critical": 60.0,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "dispute_rate",
                "metric_name": "争议率",
                "metric_category": "quality",
                "calculation_method": "ratio",
                "data_source": "tasks",
                "display_type": "percentage",
                "unit": "%",
                "precision": 2,
                "threshold_warning": 5.0,
                "threshold_critical": 10.0,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "cheating_rate",
                "metric_name": "作弊检测率",
                "metric_category": "quality",
                "calculation_method": "ratio",
                "data_source": "tasks",
                "display_type": "percentage",
                "unit": "%",
                "precision": 2,
                "threshold_warning": 3.0,
                "threshold_critical": 5.0,
                "update_frequency": "realtime",
            },
        ]

        # 财务指标
        financial_metrics = [
            {
                "metric_key": "total_gmv",
                "metric_name": "交易总额",
                "metric_category": "financial",
                "calculation_method": "sum",
                "data_source": "payment_transactions",
                "display_type": "currency",
                "unit": "元",
                "precision": 2,
                "update_frequency": "realtime",
            },
            {
                "metric_key": "platform_fees",
                "metric_name": "平台服务费",
                "metric_category": "financial",
                "calculation_method": "sum",
                "data_source": "payment_transactions",
                "display_type": "currency",
                "unit": "元",
                "precision": 2,
                "update_frequency": "daily",
            },
            {
                "metric_key": "pending_settlement",
                "metric_name": "待结算金额",
                "metric_category": "financial",
                "calculation_method": "sum",
                "data_source": "escrow_transactions",
                "display_type": "currency",
                "unit": "元",
                "precision": 2,
                "update_frequency": "realtime",
            },
        ]

        all_metrics = task_metrics + worker_metrics + quality_metrics + financial_metrics

        for metric in all_metrics:
            await session.execute(
                text("""
                    INSERT INTO dashboard_metric_configs
                    (metric_key, metric_name, metric_category, calculation_method,
                     data_source, display_type, unit, precision,
                     threshold_warning, threshold_critical, update_frequency)
                    VALUES
                    (:metric_key, :metric_name, :metric_category, :calculation_method,
                     :data_source, :display_type, :unit, :precision,
                     :threshold_warning, :threshold_critical, :update_frequency)
                """),
                metric,
            )

        await session.commit()
        print(f"  Inserted {len(all_metrics)} metric configurations")


async def initialize_system_roles():
    """初始化系统角色。"""
    from services.team_service import TeamService
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_engine = create_async_engine(
        os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/ai_hires_human"),
        echo=False,
    )
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        service = TeamService(session)
        await service.initialize_system_roles()
        await session.commit()
        print("  System roles initialized")


if __name__ == "__main__":
    asyncio.run(run_migration())
