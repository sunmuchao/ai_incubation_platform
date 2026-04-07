"""
服务管理器
统一管理和提供所有领域服务
"""
from sqlalchemy.orm import Session

from services.tenant_service import TenantService
from services.user_service import UserService
from services.employee_service import EmployeeService
from services.order_service import OrderService
from services.wallet_payment_service import WalletService, PaymentService
from services.invoice_service import UsageService, InvoiceService
from services.review_service import ReviewService, EmployerProfileService, SkillService
from config.logging_config import get_logger


class ServiceManager:
    """
    服务管理器
    负责创建和管理所有领域服务实例
    """

    def __init__(self, db: Session):
        """
        初始化服务管理器

        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = get_logger(self.__class__.__name__)

        # 懒加载服务实例
        self._tenant_service = None
        self._user_service = None
        self._employee_service = None
        self._order_service = None
        self._wallet_service = None
        self._payment_service = None
        self._usage_service = None
        self._invoice_service = None
        # P3 新增服务
        self._review_service = None
        self._employer_profile_service = None
        self._skill_service = None

    @property
    def tenants(self) -> TenantService:
        """获取租户服务"""
        if self._tenant_service is None:
            self._tenant_service = TenantService(self.db)
        return self._tenant_service

    @property
    def users(self) -> UserService:
        """获取用户服务"""
        if self._user_service is None:
            self._user_service = UserService(self.db)
        return self._user_service

    @property
    def employees(self) -> EmployeeService:
        """获取员工服务"""
        if self._employee_service is None:
            self._employee_service = EmployeeService(self.db)
        return self._employee_service

    @property
    def orders(self) -> OrderService:
        """获取订单服务"""
        if self._order_service is None:
            self._order_service = OrderService(self.db)
        return self._order_service

    @property
    def wallet(self) -> WalletService:
        """获取钱包服务"""
        if self._wallet_service is None:
            self._wallet_service = WalletService(self.db)
        return self._wallet_service

    @property
    def payments(self) -> PaymentService:
        """获取支付服务"""
        if self._payment_service is None:
            self._payment_service = PaymentService(self.db)
        return self._payment_service

    @property
    def usage(self) -> UsageService:
        """获取用量服务"""
        if self._usage_service is None:
            self._usage_service = UsageService(self.db)
        return self._usage_service

    @property
    def invoices(self) -> InvoiceService:
        """获取账单服务"""
        if self._invoice_service is None:
            self._invoice_service = InvoiceService(self.db)
        return self._invoice_service

    # P3 新增服务属性

    @property
    def reviews(self) -> ReviewService:
        """获取评价服务"""
        if self._review_service is None:
            self._review_service = ReviewService(self.db)
        return self._review_service

    @property
    def employers(self) -> EmployerProfileService:
        """获取雇主档案服务"""
        if self._employer_profile_service is None:
            self._employer_profile_service = EmployerProfileService(self.db)
        return self._employer_profile_service

    @property
    def skills(self) -> SkillService:
        """获取技能服务"""
        if self._skill_service is None:
            self._skill_service = SkillService(self.db)
        return self._skill_service


# 依赖注入函数
def get_service_manager(db: Session) -> ServiceManager:
    """
    获取服务管理器实例
    用于 FastAPI 依赖注入
    """
    return ServiceManager(db)
