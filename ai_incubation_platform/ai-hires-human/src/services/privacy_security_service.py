"""
隐私安全服务中心层 - v1.21 隐私安全中心

提供登录设备管理、登录日志、用户举报、安全知识点、隐私设置增强等核心业务逻辑
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import logging
import hashlib
import socket

from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.privacy_security import (
    LoginDeviceDB, LoginLogDB, UserReportDB, SafetyTipDB,
    PrivacySettingsExtensionDB, UserSafetyTipReadDB
)
from models.social_db import PrivacySettingsDB

logger = logging.getLogger(__name__)


# ==================== 登录设备服务 ====================

class LoginDeviceService:
    """登录设备服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_device_id(self, user_agent: str, ip_address: str) -> str:
        """生成设备指纹 ID"""
        content = f"{user_agent}:{ip_address}:{datetime.now().strftime('%Y-%m-%d')}"
        return hashlib.md5(content.encode()).hexdigest()

    def _parse_user_agent(self, user_agent: str) -> Dict:
        """解析 User-Agent"""
        result = {
            'device_type': 'unknown',
            'os_info': None,
            'browser_info': None,
            'device_model': None
        }

        if not user_agent:
            return result

        ua = user_agent.lower()

        # 判断设备类型
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            result['device_type'] = 'mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            result['device_type'] = 'tablet'
        elif 'wince' in ua:
            result['device_type'] = 'mobile'
        else:
            result['device_type'] = 'desktop'

        # 解析操作系统
        if 'windows nt 10.0' in ua:
            result['os_info'] = 'Windows 10'
        elif 'windows nt 6.3' in ua:
            result['os_info'] = 'Windows 8.1'
        elif 'windows nt 6.2' in ua:
            result['os_info'] = 'Windows 8'
        elif 'mac os x' in ua:
            result['os_info'] = 'macOS'
        elif 'android' in ua:
            result['os_info'] = 'Android'
        elif 'iphone' in ua:
            result['os_info'] = 'iOS'
        elif 'linux' in ua:
            result['os_info'] = 'Linux'

        # 解析浏览器
        if 'chrome' in ua and 'edg' not in ua:
            result['browser_info'] = 'Chrome'
        elif 'firefox' in ua:
            result['browser_info'] = 'Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            result['browser_info'] = 'Safari'
        elif 'edg' in ua:
            result['browser_info'] = 'Edge'
        elif 'msie' in ua or 'trident' in ua:
            result['browser_info'] = 'IE'

        return result

    def _get_location_from_ip(self, ip_address: str) -> Optional[str]:
        """从 IP 地址获取粗略位置（简化版，实际应使用 IP 库）"""
        # 简化实现，实际项目应集成 IP 定位服务
        if ip_address:
            if ip_address.startswith('192.168') or ip_address.startswith('10.'):
                return "局域网"
            return "未知位置"
        return None

    async def record_login(
        self,
        user_id: str,
        user_agent: Optional[str],
        ip_address: Optional[str],
        login_type: str = "success"
    ) -> Tuple[LoginDeviceDB, LoginLogDB]:
        """记录登录"""
        device_id = self._generate_device_id(user_agent or "", ip_address or "")
        ua_info = self._parse_user_agent(user_agent or "")
        location = self._get_location_from_ip(ip_address or "")

        # 检查设备是否已存在
        result = await self.db.execute(
            select(LoginDeviceDB).where(LoginDeviceDB.device_id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            # 更新现有设备
            device.last_login_at = datetime.now()
            device.ip_address = ip_address
            device.location_info = location
        else:
            # 创建新设备记录
            device = LoginDeviceDB(
                id=str(uuid.uuid4()),
                device_id=device_id,
                user_id=user_id,
                device_name=ua_info.get('browser_info'),
                device_type=ua_info.get('device_type', 'unknown'),
                os_info=ua_info.get('os_info'),
                browser_info=ua_info.get('browser_info'),
                ip_address=ip_address,
                location_info=location,
                is_current=True,
                is_trusted=False
            )
            self.db.add(device)

        # 将用户其他设备设置为非当前
        await self.db.execute(
            select(LoginDeviceDB)
            .where(LoginDeviceDB.user_id == user_id)
            .where(LoginDeviceDB.device_id != device_id)
        )
        other_devices = (await self.db.execute(
            select(LoginDeviceDB)
            .where(LoginDeviceDB.user_id == user_id)
            .where(LoginDeviceDB.device_id != device_id)
        )).scalars().all()

        for other_device in other_devices:
            other_device.is_current = False

        # 创建登录日志
        risk_level = "low"
        risk_reason = None

        # 简单风险评估
        if login_type == "failed":
            risk_level = "medium"
            risk_reason = "登录失败"
        elif ip_address and not ip_address.startswith(('192.168', '10.')):
            # 非局域网 IP，可能是新地点
            risk_level = "medium"
            risk_reason = "新地点登录"

        log = LoginLogDB(
            id=str(uuid.uuid4()),
            log_id=str(uuid.uuid4()),
            user_id=user_id,
            device_id=device_id,
            login_type=login_type,
            ip_address=ip_address,
            location_info=location,
            user_agent=user_agent,
            risk_level=risk_level,
            risk_reason=risk_reason
        )
        self.db.add(log)

        await self.db.commit()
        await self.db.refresh(device)

        logger.info(f"用户登录：user_id={user_id}, device_id={device_id}, type={login_type}")
        return device, log

    async def get_user_devices(self, user_id: str) -> List[LoginDeviceDB]:
        """获取用户所有设备"""
        result = await self.db.execute(
            select(LoginDeviceDB)
            .where(LoginDeviceDB.user_id == user_id)
            .order_by(desc(LoginDeviceDB.last_login_at))
        )
        return list(result.scalars().all())

    async def remove_device(self, user_id: str, device_id: str) -> bool:
        """移除设备"""
        result = await self.db.execute(
            select(LoginDeviceDB)
            .where(LoginDeviceDB.device_id == device_id)
            .where(LoginDeviceDB.user_id == user_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            return False

        # 不能移除当前设备
        if device.is_current:
            return False

        await self.db.delete(device)
        await self.db.commit()

        logger.info(f"移除设备：user_id={user_id}, device_id={device_id}")
        return True

    async def trust_device(self, user_id: str, device_id: str) -> bool:
        """信任设备"""
        result = await self.db.execute(
            select(LoginDeviceDB)
            .where(LoginDeviceDB.device_id == device_id)
            .where(LoginDeviceDB.user_id == user_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            return False

        device.is_trusted = True
        await self.db.commit()

        logger.info(f"信任设备：user_id={user_id}, device_id={device_id}")
        return True

    async def get_device(self, device_id: str) -> Optional[LoginDeviceDB]:
        """获取设备详情"""
        result = await self.db.execute(
            select(LoginDeviceDB).where(LoginDeviceDB.device_id == device_id)
        )
        return result.scalar_one_or_none()


# ==================== 登录日志服务 ====================

class LoginLogService:
    """登录日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_logs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[LoginLogDB], int]:
        """获取用户登录日志"""
        # 查询日志
        query = select(LoginLogDB).where(
            LoginLogDB.user_id == user_id
        ).order_by(
            desc(LoginLogDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        # 查询总数
        count_query = select(func.count()).select_from(
            LoginLogDB
        ).where(LoginLogDB.user_id == user_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return logs, total

    async def get_login_log(self, log_id: str) -> Optional[LoginLogDB]:
        """获取登录日志详情"""
        result = await self.db.execute(
            select(LoginLogDB).where(LoginLogDB.log_id == log_id)
        )
        return result.scalar_one_or_none()


# ==================== 用户举报服务 ====================

class UserReportService:
    """用户举报服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_report(
        self,
        reporter_id: str,
        reported_id: str,
        report_type: str,
        report_reason: Optional[str] = None,
        evidence_urls: Optional[List[str]] = None,
        related_task_id: Optional[str] = None,
        related_message_id: Optional[str] = None
    ) -> UserReportDB:
        """提交举报"""
        # 检查是否已存在相同举报
        existing = await self.db.execute(
            select(UserReportDB)
            .where(UserReportDB.reporter_id == reporter_id)
            .where(UserReportDB.reported_id == reported_id)
            .where(UserReportDB.report_type == report_type)
            .where(UserReportDB.status == 'pending')
        )
        if existing.scalar_one_or_none():
            raise ValueError("您已提交过相同举报，请勿重复提交")

        report = UserReportDB(
            id=str(uuid.uuid4()),
            report_id=str(uuid.uuid4()),
            reporter_id=reporter_id,
            reported_id=reported_id,
            report_type=report_type,
            report_reason=report_reason,
            evidence_urls=evidence_urls or [],
            related_task_id=related_task_id,
            related_message_id=related_message_id,
            status='pending',
            priority='normal'
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"提交举报：report_id={report.report_id}, reporter={reporter_id}, reported={reported_id}")
        return report

    async def get_user_reports(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[UserReportDB], int]:
        """获取用户举报列表"""
        query = select(UserReportDB).where(
            UserReportDB.reporter_id == user_id
        ).order_by(
            desc(UserReportDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        reports = list(result.scalars().all())

        count_query = select(func.count()).select_from(
            UserReportDB
        ).where(UserReportDB.reporter_id == user_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return reports, total

    async def get_report(self, report_id: str) -> Optional[UserReportDB]:
        """获取举报详情"""
        result = await self.db.execute(
            select(UserReportDB).where(UserReportDB.report_id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_reports(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[UserReportDB], int]:
        """获取待处理举报（管理员）"""
        query = select(UserReportDB).where(
            UserReportDB.status == 'pending'
        ).order_by(
            desc(UserReportDB.created_at)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        reports = list(result.scalars().all())

        count_query = select(func.count()).select_from(
            UserReportDB
        ).where(UserReportDB.status == 'pending')
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        return reports, total

    async def process_report(
        self,
        report_id: str,
        processor_id: str,
        status: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """处理举报"""
        report = await self.get_report(report_id)
        if not report:
            return False

        report.status = status
        report.processed_by = processor_id
        report.processed_at = datetime.now()
        report.resolution_notes = resolution_notes
        report.updated_at = datetime.now()

        await self.db.commit()

        logger.info(f"处理举报：report_id={report_id}, status={status}, processor={processor_id}")
        return True

    async def get_report_statistics(self) -> Dict:
        """获取举报统计"""
        stats = {
            'total_reports': 0,
            'pending_reports': 0,
            'reviewing_reports': 0,
            'resolved_reports': 0,
            'rejected_reports': 0,
            'urgent_reports': 0
        }

        # 总数
        total_result = await self.db.execute(select(func.count()).select_from(UserReportDB))
        stats['total_reports'] = total_result.scalar()

        # 各状态数量
        for status in ['pending', 'reviewing', 'resolved', 'rejected']:
            result = await self.db.execute(
                select(func.count()).select_from(UserReportDB)
                .where(UserReportDB.status == status)
            )
            stats[f'{status}_reports'] = result.scalar()

        # 紧急举报
        urgent_result = await self.db.execute(
            select(func.count()).select_from(UserReportDB)
            .where(UserReportDB.priority == 'urgent')
        )
        stats['urgent_reports'] = urgent_result.scalar()

        return stats


# ==================== 安全知识点服务 ====================

class SafetyTipService:
    """安全知识点服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tips(
        self,
        tip_type: Optional[str] = None,
        target_audience: str = "all",
        limit: int = 20
    ) -> List[SafetyTipDB]:
        """获取安全知识列表"""
        conditions = [SafetyTipDB.is_active == True]

        if tip_type:
            conditions.append(SafetyTipDB.tip_type == tip_type)

        if target_audience != "all":
            conditions.append(
                or_(
                    SafetyTipDB.target_audience == target_audience,
                    SafetyTipDB.target_audience == "all"
                )
            )

        query = select(SafetyTipDB).where(
            and_(*conditions)
        ).order_by(
            SafetyTipDB.sort_order,
            desc(SafetyTipDB.created_at)
        ).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tip(self, tip_id: str) -> Optional[SafetyTipDB]:
        """获取安全知识详情"""
        result = await self.db.execute(
            select(SafetyTipDB).where(SafetyTipDB.tip_id == tip_id)
        )
        tip = result.scalar_one_or_none()

        # 增加阅读计数
        if tip:
            tip.view_count += 1
            await self.db.commit()

        return tip

    async def mark_tip_read(self, user_id: str, tip_id: str) -> bool:
        """标记已读"""
        # 检查是否已标记
        existing = await self.db.execute(
            select(UserSafetyTipReadDB)
            .where(UserSafetyTipReadDB.user_id == user_id)
            .where(UserSafetyTipReadDB.tip_id == tip_id)
        )
        if existing.scalar_one_or_none():
            return True  # 已经标记过

        # 创建记录
        read_record = UserSafetyTipReadDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tip_id=tip_id,
            read_at=datetime.now()
        )
        self.db.add(read_record)
        await self.db.commit()

        return True

    async def get_user_read_tips(self, user_id: str) -> List[str]:
        """获取用户已读的安全知识点 ID 列表"""
        result = await self.db.execute(
            select(UserSafetyTipReadDB.tip_id)
            .where(UserSafetyTipReadDB.user_id == user_id)
        )
        return [row[0] for row in result.all()]


# ==================== 隐私设置扩展服务 ====================

class PrivacySettingsExtensionService:
    """隐私设置扩展服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self, user_id: str) -> Optional[PrivacySettingsExtensionDB]:
        """获取隐私设置"""
        result = await self.db.execute(
            select(PrivacySettingsExtensionDB)
            .where(PrivacySettingsExtensionDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_settings(self, user_id: str) -> PrivacySettingsExtensionDB:
        """创建隐私设置"""
        settings = PrivacySettingsExtensionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            hide_online_status=False,
            hide_distance=True,
            anonymous_mode=False,
            block_keywords=[],
            message_filter_level="normal"
        )
        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def update_settings(
        self,
        user_id: str,
        hide_online_status: Optional[bool] = None,
        hide_distance: Optional[bool] = None,
        anonymous_mode: Optional[bool] = None,
        block_keywords: Optional[List[str]] = None,
        message_filter_level: Optional[str] = None
    ) -> PrivacySettingsExtensionDB:
        """更新隐私设置"""
        settings = await self.get_settings(user_id)
        if not settings:
            settings = await self.create_settings(user_id)

        if hide_online_status is not None:
            settings.hide_online_status = hide_online_status
        if hide_distance is not None:
            settings.hide_distance = hide_distance
        if anonymous_mode is not None:
            settings.anonymous_mode = anonymous_mode
        if block_keywords is not None:
            settings.block_keywords = block_keywords
        if message_filter_level is not None:
            settings.message_filter_level = message_filter_level

        settings.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(settings)
        return settings


# ==================== 工厂函数 ====================

def get_login_device_service(db: AsyncSession) -> LoginDeviceService:
    """获取登录设备服务实例"""
    return LoginDeviceService(db)


def get_login_log_service(db: AsyncSession) -> LoginLogService:
    """获取登录日志服务实例"""
    return LoginLogService(db)


def get_user_report_service(db: AsyncSession) -> UserReportService:
    """获取用户举报服务实例"""
    return UserReportService(db)


def get_safety_tip_service(db: AsyncSession) -> SafetyTipService:
    """获取安全知识点服务实例"""
    return SafetyTipService(db)


def get_privacy_settings_extension_service(db: AsyncSession) -> PrivacySettingsExtensionService:
    """获取隐私设置扩展服务实例"""
    return PrivacySettingsExtensionService(db)
