"""
密码安全工具

功能:
- 密码强度验证
- 常见弱密码检测
- 密码与用户信息相似度检测
"""
import re
from typing import Tuple, List
from utils.logger import logger


# 常见弱密码列表（生产环境应使用更大的列表或外部服务）
COMMON_WEAK_PASSWORDS = {
    "password", "password123", "123456", "12345678", "123456789",
    "qwerty", "qwerty123", "abc123", "password1", "1234567890",
    "senha", "1234567", "Password1", "password123", "111111",
    "123123", "admin", "root", "guest", "test", "login",
    "welcome", "monkey", "dragon", "master", "letmein",
    "iloveyou", "trustno1", "sunshine", "princess", "football",
}


def validate_password_strength(
    password: str,
    username: str = None,
    email: str = None
) -> Tuple[bool, str, int]:
    """
    验证密码强度

    Args:
        password: 原始密码（未哈希）
        username: 用户名（可选，用于检测相似度）
        email: 邮箱（可选，用于检测相似度）

    Returns:
        (是否通过, 错误信息, 强度分数 0-100)
    """
    if not password:
        return False, "密码不能为空", 0

    errors = []
    score = 0

    # 1. 长度检查
    if len(password) < 8:
        errors.append("密码至少需要 8 个字符")
    elif len(password) >= 12:
        score += 20
    elif len(password) >= 8:
        score += 10

    # 2. 字符类型检查
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/`~]', password))

    type_count = sum([has_lower, has_upper, has_digit, has_special])

    if type_count < 2:
        errors.append("密码需包含大小写字母、数字、特殊字符中的至少 2 种")
    else:
        score += type_count * 15

    # 3. 常见弱密码检查
    lower_password = password.lower()
    if lower_password in COMMON_WEAK_PASSWORDS:
        errors.append("密码过于简单，请使用更复杂的密码")
        score = 0
    else:
        # 检查是否包含常见弱密码
        for weak in COMMON_WEAK_PASSWORDS:
            if weak in lower_password and len(weak) >= 5:
                errors.append("密码包含常见弱密码片段")
                score = max(0, score - 30)
                break

    # 4. 与用户信息相似度检查
    if username and len(username) >= 3:
        if username.lower() in lower_password or lower_password in username.lower():
            errors.append("密码不能包含用户名")
            score = max(0, score - 40)

    if email and "@" in email:
        email_prefix = email.split("@")[0].lower()
        if len(email_prefix) >= 3 and email_prefix in lower_password:
            errors.append("密码不能包含邮箱前缀")
            score = max(0, score - 40)

    # 5. 连续字符检查
    if _has_sequential_chars(password, 4):
        errors.append("密码不能包含 4 位以上连续字符")
        score = max(0, score - 20)

    # 6. 重复字符检查
    if _has_repeated_chars(password, 4):
        errors.append("密码不能包含 4 位以上重复字符")
        score = max(0, score - 20)

    # 最终判定
    is_valid = len(errors) == 0 and score >= 30

    if not is_valid and not errors:
        errors.append("密码强度不足")

    error_msg = "; ".join(errors) if errors else ""

    logger.debug(f"Password validation: valid={is_valid}, score={score}, errors={errors}")

    return is_valid, error_msg, score


def _has_sequential_chars(password: str, length: int) -> bool:
    """检查是否包含连续字符（如 1234, abcd）"""
    lower = password.lower()
    for i in range(len(lower) - length + 1):
        segment = lower[i:i + length]
        # 检查数字序列
        if segment.isdigit():
            if all(int(segment[j]) + 1 == int(segment[j + 1]) for j in range(len(segment) - 1)):
                return True
        # 检查字母序列
        if segment.isalpha():
            if all(ord(segment[j]) + 1 == ord(segment[j + 1]) for j in range(len(segment) - 1)):
                return True
    return False


def _has_repeated_chars(password: str, length: int) -> bool:
    """检查是否包含重复字符（如 aaaa, 1111）"""
    for i in range(len(password) - length + 1):
        segment = password[i:i + length]
        if len(set(segment)) == 1:
            return True
    return False


def get_password_strength_label(score: int) -> str:
    """根据分数返回强度标签"""
    if score >= 80:
        return "强"
    elif score >= 50:
        return "中"
    elif score >= 30:
        return "弱"
    else:
        return "极弱"