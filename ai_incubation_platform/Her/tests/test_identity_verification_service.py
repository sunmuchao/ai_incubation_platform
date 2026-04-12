"""
测试实名认证服务

覆盖范围:
- IdentityVerificationService (src/services/identity_verification_service.py)
- 实名认证申请流程
- OCR 识别与人脸核身
- 认证状态管理
- 多源身份核验（学历/职业/收入/房产/无犯罪记录）
- 信任勋章体系
- 信任分计算
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import json
import hashlib


class TestIdentityVerificationServiceInitialization:
    """测试 IdentityVerificationService 初始化"""

    def test_init(self):
        """测试服务初始化"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service.db == mock_db
        assert service.STATUS_PENDING == "pending"
        assert service.STATUS_VERIFIED == "verified"
        assert service.STATUS_REJECTED == "rejected"
        assert service.STATUS_EXPIRED == "expired"

    def test_service_urls_configured(self):
        """测试服务 URL 配置"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service.ocr_service_url == "https://api.example.com/ocr"
        assert service.face_verify_url == "https://api.example.com/face-verify"


class TestIdentityVerificationServiceHashIdNumber:
    """测试身份证号哈希功能"""

    def test_hash_id_number_consistent(self):
        """测试身份证号哈希一致性"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        id_number = "110101199001011234"
        hash1 = service._hash_id_number(id_number)
        hash2 = service._hash_id_number(id_number)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_hash_id_number_different(self):
        """测试不同身份证号产生不同哈希"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        id_number1 = "110101199001011234"
        id_number2 = "110101199001011235"

        hash1 = service._hash_id_number(id_number1)
        hash2 = service._hash_id_number(id_number2)

        assert hash1 != hash2


class TestIdentityVerificationServiceSubmitVerification:
    """测试提交实名认证申请"""

    def test_submit_verification_success(self):
        """测试成功提交实名认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        # First query: get_verification_by_user returns None (no existing verification)
        # Second query: duplicate ID check returns None (no duplicate)
        mock_db.query().filter().order_by().first.return_value = None
        mock_db.query().filter().first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.submit_verification(
            user_id="user-123",
            real_name="张三",
            id_number="110101199001011234",
            verification_type="basic",
            id_front_url="https://example.com/front.jpg",
            id_back_url="https://example.com/back.jpg"
        )

        assert result is not None
        assert result.user_id == "user-123"
        assert result.real_name == "张三"
        assert result.verification_status == "pending"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_submit_verification_already_verified(self):
        """测试用户已完成实名认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_existing = MagicMock()
        mock_existing.verification_status = "verified"
        mock_db.query().filter().order_by().first.return_value = mock_existing

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.submit_verification(
                user_id="user-123",
                real_name="张三",
                id_number="110101199001011234"
            )

        assert "已完成实名认证" in str(exc_info.value)

    def test_submit_verification_duplicate_id_number(self):
        """测试身份证号已被使用"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        # First query returns None (no existing verification for user)
        # Second query returns existing record (duplicate ID)
        mock_duplicate = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None
        mock_db.query().filter().first.return_value = mock_duplicate

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.submit_verification(
                user_id="user-123",
                real_name="张三",
                id_number="110101199001011234"
            )

        assert "已被使用" in str(exc_info.value)

    def test_submit_verification_with_advanced_type(self):
        """测试提交高级认证类型"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None
        mock_db.query().filter().first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.submit_verification(
            user_id="user-123",
            real_name="张三",
            id_number="110101199001011234",
            verification_type="advanced"
        )

        assert result.verification_type == "advanced"


class TestIdentityVerificationServiceSubmitOcrResult:
    """测试提交 OCR 识别结果"""

    def test_submit_ocr_result_success(self):
        """测试成功提交 OCR 结果"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_db.query().filter().first.return_value = mock_verification
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        ocr_data = {
            "name": "张三",
            "id_number": "110101199001011234",
            "gender": "男"
        }
        result = service.submit_ocr_result("verification-123", ocr_data)

        assert result is not None
        mock_db.commit.assert_called_once()

    def test_submit_ocr_result_not_found(self):
        """测试 OCR 结果提交但认证记录不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.submit_ocr_result("non-existent-id", {"name": "张三"})

        assert "不存在" in str(exc_info.value)


class TestIdentityVerificationServiceSubmitFaceVerification:
    """测试提交人脸核身结果"""

    def test_submit_face_verification_success(self):
        """测试成功提交人脸核身结果"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_db.query().filter().first.return_value = mock_verification
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.submit_face_verification(
            verification_id="verification-123",
            face_verify_url="https://example.com/face.jpg",
            similarity_score=0.95
        )

        assert result is not None
        mock_db.commit.assert_called_once()

    def test_submit_face_verification_not_found(self):
        """测试人脸核身提交但认证记录不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.submit_face_verification(
                verification_id="non-existent-id",
                face_verify_url="https://example.com/face.jpg",
                similarity_score=0.95
            )

        assert "不存在" in str(exc_info.value)


class TestIdentityVerificationServiceApproveVerification:
    """测试批准认证申请"""

    def test_approve_verification_success(self):
        """测试成功批准认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_verification.user_id = "user-123"

        mock_user = MagicMock()
        mock_user.id = "user-123"

        # Setup query chain for verification
        mock_db.query().filter().first.side_effect = [mock_verification, mock_user]
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.approve_verification("verification-123", badge="verified", valid_days=365)

        assert result is not None
        assert result.verification_status == "verified"
        assert result.verification_badge == "verified"
        mock_db.commit.assert_called()

    def test_approve_verification_with_custom_badge(self):
        """测试批准认证并设置自定义徽章"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_verification.user_id = "user-123"

        mock_user = MagicMock()
        mock_db.query().filter().first.side_effect = [mock_verification, mock_user]
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.approve_verification("verification-123", badge="premium")

        assert result.verification_badge == "premium"

    def test_approve_verification_not_found(self):
        """测试批准认证但记录不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.approve_verification("non-existent-id")

        assert "不存在" in str(exc_info.value)

    def test_approve_verification_updates_user_name(self):
        """测试批准认证更新用户真实姓名"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_verification.user_id = "user-123"
        mock_verification.real_name = "张三"

        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_db.query().filter().first.side_effect = [mock_verification, mock_user]
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        service.approve_verification("verification-123")

        assert mock_user.name == "张三"


class TestIdentityVerificationServiceRejectVerification:
    """测试拒绝认证申请"""

    def test_reject_verification_success(self):
        """测试成功拒绝认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_db.query().filter().first.return_value = mock_verification
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.reject_verification("verification-123", reason="证件照片不清晰")

        assert result is not None
        assert result.verification_status == "rejected"
        assert result.rejection_reason == "证件照片不清晰"
        mock_db.commit.assert_called_once()

    def test_reject_verification_not_found(self):
        """测试拒绝认证但记录不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)

        with pytest.raises(ValueError) as exc_info:
            service.reject_verification("non-existent-id", reason="测试原因")

        assert "不存在" in str(exc_info.value)


class TestIdentityVerificationServiceGetVerification:
    """测试获取认证记录"""

    def test_get_verification_found(self):
        """测试获取认证记录成功"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.id = "verification-123"
        mock_db.query().filter().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.get_verification("verification-123")

        assert result is not None
        assert result.id == "verification-123"

    def test_get_verification_not_found(self):
        """测试获取认证记录不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)
        result = service.get_verification("non-existent-id")

        assert result is None


class TestIdentityVerificationServiceGetVerificationByUser:
    """测试获取用户认证记录"""

    def test_get_verification_by_user_found(self):
        """测试获取用户认证记录成功"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.user_id = "user-123"
        mock_db.query().filter().order_by().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_by_user("user-123")

        assert result is not None
        assert result.user_id == "user-123"

    def test_get_verification_by_user_not_found(self):
        """测试用户无认证记录"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_by_user("user-123")

        assert result is None


class TestIdentityVerificationServiceGetVerificationStatus:
    """测试获取用户认证状态"""

    def test_get_verification_status_not_submitted(self):
        """测试用户未提交认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_status("user-123")

        assert result["is_verified"] is False
        assert result["status"] == "not_submitted"
        assert "未提交" in result["message"]

    def test_get_verification_status_verified(self):
        """测试用户已认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.verification_status = "verified"
        mock_verification.verification_type = "basic"
        mock_verification.verification_badge = "verified"
        mock_verification.verified_at = datetime.utcnow()
        mock_verification.expires_at = datetime.utcnow() + timedelta(days=365)
        mock_db.query().filter().order_by().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_status("user-123")

        assert result["is_verified"] is True
        assert result["status"] == "verified"
        assert result["verification_type"] == "basic"

    def test_get_verification_status_rejected(self):
        """测试用户认证被拒绝"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.verification_status = "rejected"
        mock_verification.rejection_reason = "证件照片不清晰"
        mock_verification.verification_type = "basic"
        mock_verification.verification_badge = None
        mock_verification.verified_at = None
        mock_verification.expires_at = None
        mock_db.query().filter().order_by().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_status("user-123")

        assert result["is_verified"] is False
        assert result["status"] == "rejected"
        assert result["rejection_reason"] == "证件照片不清晰"


class TestIdentityVerificationServiceIsVerified:
    """测试检查用户是否已认证"""

    def test_is_verified_true(self):
        """测试用户已认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.verification_status = "verified"
        mock_verification.expires_at = datetime.utcnow() + timedelta(days=365)
        mock_db.query().filter().order_by().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.is_verified("user-123")

        assert result is True

    def test_is_verified_false_no_record(self):
        """测试用户无认证记录"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().order_by().first.return_value = None

        service = IdentityVerificationService(mock_db)
        result = service.is_verified("user-123")

        assert result is False

    def test_is_verified_false_not_verified(self):
        """测试用户认证状态不是 verified"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.verification_status = "pending"
        mock_verification.expires_at = None
        mock_db.query().filter().order_by().first.return_value = mock_verification

        service = IdentityVerificationService(mock_db)
        result = service.is_verified("user-123")

        assert result is False

    def test_is_verified_expired(self):
        """测试认证已过期"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_verification = MagicMock()
        mock_verification.verification_status = "verified"
        mock_verification.expires_at = datetime.utcnow() - timedelta(days=1)  # 已过期
        mock_db.query().filter().order_by().first.return_value = mock_verification
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        result = service.is_verified("user-123")

        assert result is False
        assert mock_verification.verification_status == "expired"
        mock_db.commit.assert_called_once()


class TestIdentityVerificationServiceGetVerifiedUsers:
    """测试获取已认证用户列表"""

    def test_get_verified_users_with_data(self):
        """测试获取已认证用户列表有数据"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().limit().all.return_value = [("user-1",), ("user-2",)]

        mock_user1 = MagicMock()
        mock_user1.id = "user-1"
        mock_user2 = MagicMock()
        mock_user2.id = "user-2"

        mock_db.query().filter().all.return_value = [mock_user1, mock_user2]

        service = IdentityVerificationService(mock_db)
        result = service.get_verified_users(limit=100)

        assert len(result) == 2
        assert result[0].id == "user-1"

    def test_get_verified_users_empty(self):
        """测试获取已认证用户列表无数据"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().limit().all.return_value = []
        mock_db.query().filter().all.return_value = []

        service = IdentityVerificationService(mock_db)
        result = service.get_verified_users()

        assert len(result) == 0


class TestIdentityVerificationServiceGetVerificationStats:
    """测试获取认证统计信息"""

    def test_get_verification_stats(self):
        """测试获取认证统计"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        # Mock count queries
        mock_db.query().count.return_value = 100
        mock_db.query().filter().count.side_effect = [30, 50, 20]  # pending, verified, rejected

        service = IdentityVerificationService(mock_db)
        result = service.get_verification_stats()

        assert result["total"] == 100
        assert result["pending"] == 30
        assert result["verified"] == 50
        assert result["rejected"] == 20


class TestIdentityVerificationServiceSimulateOcrScan:
    """测试模拟 OCR 扫描"""

    def test_simulate_ocr_scan(self):
        """测试模拟 OCR 扫描返回结果"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        result = service.simulate_ocr_scan(
            id_front_url="https://example.com/front.jpg",
            id_back_url="https://example.com/back.jpg"
        )

        assert "name" in result
        assert "id_number" in result
        assert "gender" in result
        assert result["name"] == "张三"


class TestIdentityVerificationServiceSimulateFaceCompare:
    """测试模拟人脸比对"""

    def test_simulate_face_compare(self):
        """测试模拟人脸比对返回结果"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        result = service.simulate_face_compare(
            id_photo_url="https://example.com/id.jpg",
            face_photo_url="https://example.com/face.jpg"
        )

        assert "similarity" in result
        assert "is_match" in result
        assert "face_quality" in result
        assert result["similarity"] >= 0.85
        assert result["liveness_detected"] is True


class TestIdentityVerificationServiceGetUserTrustBadges:
    """测试获取用户信任勋章"""

    def test_get_user_trust_badges_empty(self):
        """测试获取用户信任勋章（空列表）"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        service = IdentityVerificationService(mock_db)
        result = service.get_user_trust_badges("user-123")

        assert len(result) == 0

    def test_get_user_trust_badges_with_data(self):
        """测试获取用户信任勋章（有数据）"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_badge1 = MagicMock()
        mock_badge1.id = "badge-1"
        mock_badge1.badge_type = "real_name_verified"
        mock_badge1.badge_name = "实名认证"
        mock_badge1.badge_icon = "🆔"
        mock_badge1.badge_level = None
        mock_badge1.badge_level_value = 20
        mock_badge1.earned_at = datetime.utcnow()

        mock_badge2 = MagicMock()
        mock_badge2.id = "badge-2"
        mock_badge2.badge_type = "education_verified"
        mock_badge2.badge_name = "学历认证"
        mock_badge2.badge_icon = "🎓"
        mock_badge2.badge_level = "本科"
        mock_badge2.badge_level_value = 4
        mock_badge2.earned_at = datetime.utcnow()

        mock_db.query().filter().all.return_value = [mock_badge1, mock_badge2]

        service = IdentityVerificationService(mock_db)
        result = service.get_user_trust_badges("user-123")

        assert len(result) == 2
        assert result[0]["badge_type"] == "real_name_verified"
        assert result[1]["badge_type"] == "education_verified"


class TestIdentityVerificationServiceSubmitEducationVerification:
    """测试提交学历认证"""

    def test_submit_education_verification_success(self):
        """测试成功提交学历认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_education_verification(
            user_id="user-123",
            school_name="清华大学",
            degree_type="bachelor",
            major="计算机科学",
            graduation_year=2020,
            chsi_verification_id="CHSI123456"
        )

        assert success is True
        assert "已提交" in message
        assert credential_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_submit_education_verification_failure(self):
        """测试学历认证提交失败"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock(side_effect=Exception("Database error"))
        mock_db.rollback = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_education_verification(
            user_id="user-123",
            school_name="清华大学",
            degree_type="bachelor",
            major="计算机科学",
            graduation_year=2020
        )

        assert success is False
        assert "Database error" in message
        assert credential_id is None
        mock_db.rollback.assert_called_once()


class TestIdentityVerificationServiceSubmitOccupationVerification:
    """测试提交职业认证"""

    def test_submit_occupation_verification_success(self):
        """测试成功提交职业认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_occupation_verification(
            user_id="user-123",
            company_name="腾讯",
            position="高级工程师",
            work_years=5,
            work_email="zhangsan@tencent.com",
            verification_method="email"
        )

        assert success is True
        assert "已提交" in message
        assert credential_id is not None
        mock_db.add.assert_called_once()

    def test_submit_occupation_verification_failure(self):
        """测试职业认证提交失败"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock(side_effect=Exception("Database error"))
        mock_db.rollback = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_occupation_verification(
            user_id="user-123",
            company_name="腾讯",
            position="高级工程师",
            work_years=5
        )

        assert success is False
        assert "Database error" in message
        assert credential_id is None


class TestIdentityVerificationServiceApproveEducationVerification:
    """测试批准学历认证"""

    def test_approve_education_verification_success(self):
        """测试成功批准学历认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_credential = MagicMock()
        mock_credential.user_id = "user-123"
        mock_db.query().filter().first.return_value = mock_credential
        mock_db.commit = MagicMock()

        # Mock _award_trust_badge and calculate_trust_score
        with patch.object(IdentityVerificationService, '_award_trust_badge') as mock_award:
            with patch.object(IdentityVerificationService, 'calculate_trust_score') as mock_calc:
                service = IdentityVerificationService(mock_db)
                success, message = service.approve_education_verification(
                    credential_id="credential-123",
                    level="985",
                    level_value=4
                )

                assert success is True
                assert "已通过" in message
                mock_award.assert_called_once()
                mock_calc.assert_called_once_with("user-123")

    def test_approve_education_verification_not_found(self):
        """测试批准学历认证但凭证不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)
        success, message = service.approve_education_verification(
            credential_id="non-existent-id",
            level="985",
            level_value=4
        )

        assert success is False
        assert "不存在" in message


class TestIdentityVerificationServiceAwardTrustBadge:
    """测试授予信任勋章"""

    def test_award_trust_badge_new(self):
        """测试授予新勋章"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None  # No existing badge
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        service._award_trust_badge(
            user_id="user-123",
            badge_type="education_verified",
            badge_name="学历认证",
            level="本科",
            level_value=4,
            source_verification_id="credential-123"
        )

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_award_trust_badge_existing(self):
        """测试更新现有勋章"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_existing_badge = MagicMock()
        mock_db.query().filter().first.return_value = mock_existing_badge
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        service._award_trust_badge(
            user_id="user-123",
            badge_type="education_verified",
            badge_name="学历认证",
            level="硕士",
            level_value=5,
            source_verification_id="credential-456"
        )

        assert mock_existing_badge.is_active is True
        assert mock_existing_badge.badge_level == "硕士"
        mock_db.commit.assert_called()


class TestIdentityVerificationServiceCalculateTrustScore:
    """测试计算信任分"""

    def test_calculate_trust_score_no_badges(self):
        """测试无勋章时计算信任分"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        # Mock badges query returns empty list
        mock_db.query().filter().all.return_value = []
        # Mock TrustScoreDB query returns None (no existing record)
        mock_db.query().filter().first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        # Use patch to mock TrustScoreDB creation since model has different field names
        with patch('src.services.identity_verification_service.TrustScoreDB') as MockTrustScoreDB:
            MockTrustScoreDB.return_value = MagicMock()
            score = service.calculate_trust_score("user-123")

            assert score == 0

    def test_calculate_trust_score_with_badges(self):
        """测试有勋章时计算信任分"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_badge1 = MagicMock()
        mock_badge1.badge_type = "real_name_verified"
        mock_badge1.badge_level_value = 20

        mock_badge2 = MagicMock()
        mock_badge2.badge_type = "education_verified"
        mock_badge2.badge_level_value = 4

        mock_badge3 = MagicMock()
        mock_badge3.badge_type = "criminal_clear"
        mock_badge3.badge_level_value = 100

        mock_db.query().filter().all.return_value = [mock_badge1, mock_badge2, mock_badge3]
        mock_db.query().filter().first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        # Use patch to mock TrustScoreDB creation
        with patch('src.services.identity_verification_service.TrustScoreDB') as MockTrustScoreDB:
            MockTrustScoreDB.return_value = MagicMock()
            score = service.calculate_trust_score("user-123")

            # real_name = 20, education = min(20, 4*5)=20, criminal = 15
            assert score > 0
            assert score <= 100

    def test_calculate_trust_score_existing_record(self):
        """测试更新现有信任分记录"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_badge = MagicMock()
        mock_badge.badge_type = "real_name_verified"
        mock_badge.badge_level_value = 20
        mock_db.query().filter().all.return_value = [mock_badge]

        mock_trust_score = MagicMock()
        mock_trust_score.trust_score = 50
        mock_db.query().filter().first.return_value = mock_trust_score
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        score = service.calculate_trust_score("user-123")

        mock_db.commit.assert_called()
        assert mock_trust_score.trust_score == score


class TestIdentityVerificationServiceGetTrustLevelName:
    """测试获取信任等级名称"""

    def test_get_trust_level_diamond(self):
        """测试钻石等级"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service._get_trust_level_name(95) == "diamond"
        assert service._get_trust_level_name(90) == "diamond"

    def test_get_trust_level_platinum(self):
        """测试铂金等级"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service._get_trust_level_name(85) == "platinum"
        assert service._get_trust_level_name(80) == "platinum"

    def test_get_trust_level_gold(self):
        """测试黄金等级"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service._get_trust_level_name(75) == "gold"
        assert service._get_trust_level_name(60) == "gold"

    def test_get_trust_level_silver(self):
        """测试白银等级"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service._get_trust_level_name(50) == "silver"
        assert service._get_trust_level_name(40) == "silver"

    def test_get_trust_level_bronze(self):
        """测试青铜等级"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        assert service._get_trust_level_name(30) == "bronze"
        assert service._get_trust_level_name(0) == "bronze"


class TestIdentityVerificationServiceGetTrustScore:
    """测试获取用户信任分详情"""

    def test_get_trust_score_existing(self):
        """测试获取现有信任分"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_trust_score = MagicMock()
        mock_trust_score.trust_score = 75
        mock_trust_score.trust_level = "gold"
        mock_trust_score.last_calculated_at = datetime.utcnow()
        mock_db.query().filter().first.return_value = mock_trust_score

        service = IdentityVerificationService(mock_db)
        result = service.get_trust_score("user-123")

        assert result["trust_score"] == 75
        assert result["trust_level"] == "gold"

    def test_get_trust_score_not_existing(self):
        """测试获取不存在信任分时自动计算"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        # First query returns None, then after calculate returns score
        mock_trust_score = MagicMock()
        mock_trust_score.trust_score = 20
        mock_trust_score.trust_level = "bronze"
        mock_trust_score.last_calculated_at = datetime.utcnow()

        mock_db.query().filter().first.side_effect = [None, mock_trust_score]

        with patch.object(IdentityVerificationService, 'calculate_trust_score') as mock_calc:
            mock_calc.return_value = 20
            service = IdentityVerificationService(mock_db)
            result = service.get_trust_score("user-123")

            mock_calc.assert_called_once_with("user-123")
            assert result["trust_score"] == 20


class TestIdentityVerificationServiceSubmitIncomeVerification:
    """测试提交收入认证"""

    def test_submit_income_verification_success(self):
        """测试成功提交收入认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_income_verification(
            user_id="user-123",
            income_range="30k-50k",
            income_type="salary",
            verification_method="tax_record",
            bank_name="中国银行"
        )

        assert success is True
        assert "已提交" in message
        assert credential_id is not None
        mock_db.add.assert_called_once()

    def test_submit_income_verification_failure(self):
        """测试收入认证提交失败"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock(side_effect=Exception("Database error"))
        mock_db.rollback = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_income_verification(
            user_id="user-123",
            income_range="30k-50k"
        )

        assert success is False
        assert "Database error" in message
        assert credential_id is None


class TestIdentityVerificationServiceApproveIncomeVerification:
    """测试批准收入认证"""

    def test_approve_income_verification_success(self):
        """测试成功批准收入认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_credential = MagicMock()
        mock_credential.user_id = "user-123"
        mock_db.query().filter().first.return_value = mock_credential
        mock_db.commit = MagicMock()

        with patch.object(IdentityVerificationService, '_award_trust_badge') as mock_award:
            with patch.object(IdentityVerificationService, 'calculate_trust_score') as mock_calc:
                service = IdentityVerificationService(mock_db)
                success, message = service.approve_income_verification(
                    credential_id="credential-123",
                    level_value=15
                )

                assert success is True
                assert "已通过" in message
                mock_award.assert_called_once()
                mock_calc.assert_called_once()

    def test_approve_income_verification_not_found(self):
        """测试批准收入认证但凭证不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)
        success, message = service.approve_income_verification(
            credential_id="non-existent-id",
            level_value=15
        )

        assert success is False
        assert "不存在" in message


class TestIdentityVerificationServiceSubmitPropertyVerification:
    """测试提交房产认证"""

    def test_submit_property_verification_success(self):
        """测试成功提交房产认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_property_verification(
            user_id="user-123",
            property_location="北京市朝阳区",
            property_type="apartment",
            property_area=100.0,
            property_value=500.0,
            ownership_type="sole"
        )

        assert success is True
        assert "已提交" in message
        assert credential_id is not None
        mock_db.add.assert_called_once()

    def test_submit_property_verification_failure(self):
        """测试房产认证提交失败"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock(side_effect=Exception("Database error"))
        mock_db.rollback = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_property_verification(
            user_id="user-123",
            property_location="北京市朝阳区"
        )

        assert success is False
        assert "Database error" in message
        assert credential_id is None


class TestIdentityVerificationServiceApprovePropertyVerification:
    """测试批准房产认证"""

    def test_approve_property_verification_success(self):
        """测试成功批准房产认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_credential = MagicMock()
        mock_credential.user_id = "user-123"
        mock_db.query().filter().first.return_value = mock_credential
        mock_db.commit = MagicMock()

        with patch.object(IdentityVerificationService, '_award_trust_badge') as mock_award:
            with patch.object(IdentityVerificationService, 'calculate_trust_score') as mock_calc:
                service = IdentityVerificationService(mock_db)
                success, message = service.approve_property_verification(
                    credential_id="credential-123",
                    level_value=15
                )

                assert success is True
                assert "已通过" in message
                mock_award.assert_called_once()
                mock_calc.assert_called_once()

    def test_approve_property_verification_not_found(self):
        """测试批准房产认证但凭证不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)
        success, message = service.approve_property_verification(
            credential_id="non-existent-id",
            level_value=15
        )

        assert success is False
        assert "不存在" in message


class TestIdentityVerificationServiceCriminalRecordVerification:
    """测试无犯罪记录认证"""

    def test_submit_criminal_record_verification_success(self):
        """测试成功提交无犯罪记录认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        service = IdentityVerificationService(mock_db)
        success, message, credential_id = service.submit_criminal_record_verification(
            user_id="user-123",
            verification_method="police_api",
            certificate_url="https://example.com/certificate.pdf"
        )

        assert success is True
        assert "已提交" in message
        assert credential_id is not None

    def test_approve_criminal_record_verification_success(self):
        """测试成功批准无犯罪记录认证"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.commit = MagicMock()

        with patch.object(IdentityVerificationService, '_award_trust_badge') as mock_award:
            with patch.object(IdentityVerificationService, 'calculate_trust_score') as mock_calc:
                service = IdentityVerificationService(mock_db)
                success, message = service.approve_criminal_record_verification("user-123")

                assert success is True
                assert "已通过" in message
                mock_award.assert_called_once()
                mock_calc.assert_called_once_with("user-123")


class TestIdentityVerificationServiceCallExternalVerificationApi:
    """测试调用外部验证 API"""

    def test_call_external_api_config_not_found(self):
        """测试 API 配置不存在"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="chsi",
            params={"student_id": "123"}
        )

        assert success is False
        assert "不存在" in error

    def test_call_external_api_chsi(self):
        """测试调用学信网 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "chsi"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="chsi",
            params={
                "student_id": "123",
                "school_name": "清华大学",
                "degree_type": "bachelor"
            }
        )

        assert success is True
        assert result["verified"] is True
        assert result["school_name"] == "清华大学"
        assert error == ""

    def test_call_external_api_enterprise_email(self):
        """测试调用企业邮箱验证 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "enterprise_email"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="enterprise_email",
            params={
                "email": "zhangsan@company.com",
                "company_name": "腾讯"
            }
        )

        assert success is True
        assert result["verified"] is True

    def test_call_external_api_enterprise_email_invalid(self):
        """测试调用企业邮箱验证 API（无效邮箱）"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "enterprise_email"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="enterprise_email",
            params={
                "email": "zhangsan@gmail.com",  # 不是企业邮箱
                "company_name": "腾讯"
            }
        )

        assert success is True
        assert result["verified"] is False

    def test_call_external_api_tax_bureau(self):
        """测试调用税务局 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "tax_bureau"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="tax_bureau",
            params={
                "tax_id": "123456",
                "name": "张三",
                "annual_income": 200000
            }
        )

        assert success is True
        assert result["verified"] is True
        assert result["tax_level"] == "A"

    def test_call_external_api_property_registry(self):
        """测试调用房产登记 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "property_registry"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="property_registry",
            params={
                "cert_no": "123456",
                "owner_name": "张三",
                "location": "北京市朝阳区",
                "area": 100
            }
        )

        assert success is True
        assert result["verified"] is True
        assert result["property_area"] == 100

    def test_call_external_api_police_record(self):
        """测试调用公安无犯罪记录 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "police_record"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="police_record",
            params={
                "id_number": "110101199001011234",
                "name": "张三"
            }
        )

        assert success is True
        assert result["verified"] is True
        assert result["has_criminal_record"] is False

    def test_call_external_api_unsupported(self):
        """测试调用不支持的 API"""
        from src.services.identity_verification_service import IdentityVerificationService

        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.api_name = "unsupported_api"
        mock_config.is_active = True
        mock_db.query().filter().first.return_value = mock_config

        service = IdentityVerificationService(mock_db)
        success, result, error = service.call_external_verification_api(
            api_name="unsupported_api",
            params={}
        )

        assert success is False
        assert "不支持" in error


class TestIdentityVerificationServiceVerificationTypes:
    """测试认证类型配置"""

    def test_verification_types_defined(self):
        """测试认证类型已定义"""
        from src.services.identity_verification_service import IdentityVerificationService

        assert "real_name" in IdentityVerificationService.VERIFICATION_TYPES
        assert "education" in IdentityVerificationService.VERIFICATION_TYPES
        assert "occupation" in IdentityVerificationService.VERIFICATION_TYPES
        assert "income" in IdentityVerificationService.VERIFICATION_TYPES
        assert "property" in IdentityVerificationService.VERIFICATION_TYPES
        assert "criminal_record" in IdentityVerificationService.VERIFICATION_TYPES

    def test_verification_type_structure(self):
        """测试认证类型结构"""
        from src.services.identity_verification_service import IdentityVerificationService

        for v_type, config in IdentityVerificationService.VERIFICATION_TYPES.items():
            assert "name" in config
            assert "badge_type" in config
            assert "score_weight" in config
            assert "required" in config

    def test_real_name_required(self):
        """测试实名认证为必需"""
        from src.services.identity_verification_service import IdentityVerificationService

        assert IdentityVerificationService.VERIFICATION_TYPES["real_name"]["required"] is True

    def test_optional_verification_types(self):
        """测试可选认证类型"""
        from src.services.identity_verification_service import IdentityVerificationService

        for v_type in ["education", "occupation", "income", "property", "criminal_record"]:
            assert IdentityVerificationService.VERIFICATION_TYPES[v_type]["required"] is False


class TestIdentityVerificationServiceBadgeIcons:
    """测试勋章图标配置"""

    def test_badge_icons_mapping(self):
        """测试勋章图标映射"""
        from src.services.identity_verification_service import IdentityVerificationService

        # 内部方法使用的图标映射
        expected_icons = {
            "real_name_verified": "🆔",
            "education_verified": "🎓",
            "occupation_verified": "💼",
            "income_verified": "💰",
            "property_verified": "🏠",
            "criminal_clear": "🛡️",
            "vehicle_verified": "🚗",
        }

        # 验证图标映射存在于 _award_trust_badge 方法中
        mock_db = MagicMock()
        service = IdentityVerificationService(mock_db)

        # 通过调用 _award_trust_badge 验证图标映射
        for badge_type, expected_icon in expected_icons.items():
            mock_db.query().filter().first.return_value = None
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()

            service._award_trust_badge(
                user_id="user-123",
                badge_type=badge_type,
                badge_name="测试勋章",
                level=None,
                level_value=10,
                source_verification_id="test-id"
            )

            # 获取添加的 badge 对象验证图标
            added_objects = [call[0][0] for call in mock_db.add.call_args_list]
            # 找到 TrustBadgeDB 对象 (有 badge_icon 属性)
            badge_obj = None
            for obj in added_objects:
                if hasattr(obj, 'badge_type') and hasattr(obj, 'badge_icon') and obj.badge_type == badge_type:
                    badge_obj = obj
                    break

            assert badge_obj is not None, f"Badge object not found for {badge_type}"
            assert badge_obj.badge_icon == expected_icon