"""
数据库管理器 - 提供统一的数据库访问入口
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
import logging

from core.config import settings
from repositories.member_repository import MemberRepository
from repositories.post_repository import PostRepository
from repositories.comment_repository import CommentRepository
from repositories.review_repository import ReviewRepository
from repositories.review_rule_repository import ReviewRuleRepository
from repositories.report_repository import ReportRepository
from repositories.ban_repository import BanRepository
from repositories.audit_log_repository import AuditLogRepository
from repositories.rate_limit_repository import RateLimitRepository
from repositories.agent_call_repository import AgentCallRepository
from repositories.like_repository import LikeRepository
from repositories.bookmark_repository import BookmarkRepository
from repositories.follow_repository import FollowRepository
from repositories.notification_repository import NotificationRepository
from db.level_models import DBExperienceLog, DBLevelPrivilege

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self._engine: Optional[create_async_engine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialized = False

    def initialize(self):
        """初始化数据库连接"""
        if self._initialized:
            return

        self._engine = create_async_engine(
            settings.effective_database_url,
            echo=settings.db_echo,
            future=True,
            pool_pre_ping=True,  # 连接前 ping 测试
            pool_size=10,
            max_overflow=20,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self._initialized = True
        logger.info(f"数据库初始化成功：{settings.database_url}")

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("数据库连接已关闭")

    async def get_session(self):
        """获取数据库会话（异步生成器，用于依赖注入）"""
        if not self._initialized:
            self.initialize()
        async with self._session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def get_session_context(self) -> AsyncSession:
        """获取数据库会话（支持 async with 上下文管理器）"""
        if not self._initialized:
            self.initialize()
        session = await self._session_factory()
        return session

    async def init_tables(self):
        """初始化数据库表结构"""
        if not self._initialized:
            self.initialize()

        from db.base import Base
        from db.models import (  #  noqa: F401
            DBCommunityMember,
            DBPost,
            DBComment,
            DBContentReview,
            DBReviewRule,
            DBReport,
            DBBanRecord,
            DBAuditLog,
            DBRateLimitConfig,
            DBAgentCallRecord,
            DBFollow,
            DBLike,
            DBBookmark,
            DBNotification,
        )
        from db.level_models import (  #  noqa: F401
            DBExperienceLog,
            DBLevelPrivilege,
        )
        from db.channel_models import (  #  noqa: F401
            DBChannelCategory,
            DBChannel,
            DBChannelMember,
            DBChannelPermission,
            DBChannelPost,
        )
        from db.models import (  #  noqa: F401
            DBAgentReputation,
            DBBehaviorTrace,
            DBGovernanceReport,
            DBAPIKey,
            DBAPIKeyUsage,
            DBAPIRequestLog,
        )
        from db.economy_models import (  #  noqa: F401
            DBWallet,
            DBWalletTransaction,
            DBTip,
            DBSubscription,
            DBSubscriptionBenefit,
            DBPaidContent,
            DBContentPurchase,
            DBRevenueSplit,
            DBCreatorFundPool,
            DBCreatorFundDistribution,
            DBFanLevel,
            DBFanMembership,
        )
        from db.activity_models import (  #  noqa: F401
            DBActivity,
            DBActivityRegistration,
            DBActivitySession,
            DBActivityInteraction,
            DBLiveStream,
            LiveChatMessage,
            DBVote,
            DBVoteOption,
            DBVoteRecord,
            DBActivityRecap,
            DBActivityRecommendation,
        )
        from db.models import (
            DBEmailConfig,
            DBEmailSendRecord,
            DBEmailTemplate,
            DBSMSConfig,
            DBSMSSendRecord,
            DBOAuthConfig,
            DBOAuthToken,
            DBSSOConfig,
            DBSSOSession,
            DBShareConfig,
            DBShareRecord,
            DBCrossPlatformIdentity,
        )

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表结构初始化完成")

    async def drop_tables(self):
        """删除所有数据库表（仅开发环境）"""
        if settings.environment != "development":
            logger.warning("非开发环境，禁止删除表结构")
            return

        from db.base import Base

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("数据库表结构已删除")

    def get_repositories(self, db: AsyncSession) -> dict:
        """获取所有 Repository 实例"""
        return {
            "member": MemberRepository(db),
            "post": PostRepository(db),
            "comment": CommentRepository(db),
            "review": ReviewRepository(db),
            "review_rule": ReviewRuleRepository(db),
            "report": ReportRepository(db),
            "ban": BanRepository(db),
            "audit_log": AuditLogRepository(db),
            "rate_limit": RateLimitRepository(db),
            "agent_call": AgentCallRepository(db),
            "like": LikeRepository(db),
            "bookmark": BookmarkRepository(db),
            "follow": FollowRepository(db),
            "notification": NotificationRepository(db),
        }


# 全局数据库管理器实例
db_manager = DatabaseManager()
