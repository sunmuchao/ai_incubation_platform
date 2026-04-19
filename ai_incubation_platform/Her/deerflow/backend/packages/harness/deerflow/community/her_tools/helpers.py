"""
Her Tools - Helpers Module

Utility functions for Her tools: path resolution, user ID extraction, database access, etc.

【性能优化】
- 缓存模块导入状态，避免重复 ImportError 处理
- 批量查询减少 N+1 问题
"""
import logging
import json
import asyncio
import os
import sys
import re
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ===== 性能优化：缓存模块导入状态 =====
_module_cache: Dict[str, bool] = {}
_cached_imports: Dict[str, Any] = {}  # 缓存已导入的模块对象


def _cached_import(module_path: str, attr_name: str = None) -> Any:
    """
    缓存导入，避免重复 import 开销

    Args:
        module_path: 模块路径（如 'utils.db_session_manager'）
        attr_name: 要导入的属性名（如 'db_session'），不传则返回模块本身
    """
    cache_key = f"{module_path}:{attr_name}" if attr_name else module_path

    if cache_key in _cached_imports:
        return _cached_imports[cache_key]

    ensure_her_in_path()

    import_start = time.time()
    module = __import__(module_path, fromlist=[attr_name] if attr_name else [])
    logger.info(f"[cached_import] 导入 {cache_key} 耗时: {time.time() - import_start:.3f}s")

    if attr_name:
        result = getattr(module, attr_name)
    else:
        result = module

    _cached_imports[cache_key] = result
    return result


# ==================== Path & Environment ====================

def get_her_root() -> str:
    """获取 Her 项目根目录"""
    # 优先使用环境变量
    her_root = os.environ.get("HER_PROJECT_ROOT")
    if her_root:
        return her_root

    # 降级：通过文件路径推断
    # her_tools 位于 deerflow/backend/packages/harness/deerflow/community/her_tools/
    # Her 根目录是 deerflow 的父目录
    current_file = os.path.abspath(__file__)
    # 向上 5 层到达 Her 根目录
    # her_tools -> community -> deerflow -> harness -> packages -> backend -> deerflow -> Her
    her_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))))))
    return her_root


def ensure_her_in_path():
    """确保 Her 项目在 Python 路径中"""
    her_root = get_her_root()
    src_path = os.path.join(her_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


# ==================== User ID Resolution ====================

def get_current_user_id() -> str:
    """
    获取当前用户 ID（支持用户隔离）

    优先级：
    1. 从 LangGraph configurable 中获取（DeerFlowClient 传入的 user_id）
    2. 从用户独立的 memory 文件中读取
    3. 从全局 memory.json 中读取（降级）
    """
    try:
        # 方式1：从 LangGraph configurable 中获取（最高优先级）
        from langgraph.config import get_config
        config = get_config()
        user_id = config.get("configurable", {}).get("user_id")
        if user_id:
            logger.info(f"[get_current_user_id] 从 configurable 获取: {user_id}")
            return user_id

        # 方式2：从用户独立的 memory 文件中读取
        her_root = get_her_root()
        users_dir = os.path.join(her_root, "deerflow", "backend", ".deer-flow", "users")

        if os.path.exists(users_dir):
            # 找到所有用户目录
            user_dirs = [d for d in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, d))]
            if user_dirs:
                # 取最近更新的用户目录（假设只有一个活跃用户）
                latest_user = None
                latest_mtime = 0
                for user_dir in user_dirs:
                    user_memory_path = os.path.join(users_dir, user_dir, "memory.json")
                    if os.path.exists(user_memory_path):
                        mtime = os.path.getmtime(user_memory_path)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_user = user_dir

                if latest_user:
                    logger.info(f"[get_current_user_id] 从用户独立文件获取: {latest_user}")
                    return latest_user

        # 方式3：从全局 memory.json 中读取（降级）
        memory_path = os.path.join(her_root, "deerflow", "backend", ".deer-flow", "memory.json")

        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory_data = json.load(f)

            facts = memory_data.get("facts", [])
            for fact in facts:
                fact_id = fact.get("id", "")
                if fact_id.startswith("user-id-"):
                    return fact_id.replace("user-id-", "")

                content = fact.get("content", "")
                if "用户ID：" in content:
                    match = re.search(r'用户ID[:\s：]+([a-f0-9-]+)', content)
                    if match:
                        return match.group(1)

    except Exception as e:
        logger.warning(f"[get_current_user_id] 提取失败: {e}")

    return "user-anonymous-dev"


# ==================== Async Execution ====================

def run_async(coro):
    """安全执行异步协程"""
    start_time = time.time()
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        result = future.result(timeout=30.0)
        logger.info(f"[run_async] 使用现有loop耗时: {time.time() - start_time:.3f}s")
        return result
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        try:
            result = new_loop.run_until_complete(coro)
            logger.info(f"[run_async] 创建新loop耗时: {time.time() - start_time:.3f}s")
            return result
        finally:
            new_loop.close()


def normalize_user_interests_field(raw: Optional[Any]) -> List[str]:
    """
    将 users.interests 存值规范为 List[str]。
    支持：JSON 数组字符串、逗号分隔、空值。
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    parts = [p.strip() for p in text.split(",") if p.strip() and p.strip() != "[]"]
    return parts[:20]


def should_exclude_demo_candidate_name(name: Optional[str]) -> bool:
    """
    过滤明显测试/演示昵称，避免进入真实推荐（数据校验/安全边界）。
    可通过环境变量 HER_EXCLUDE_NAME_SUBSTRINGS 覆盖，逗号分隔子串。
    """
    n = (name or "").strip()
    if not n:
        return False
    raw = os.environ.get("HER_EXCLUDE_NAME_SUBSTRINGS", "安全测试,自动化测试,单元测试")
    for frag in raw.split(","):
        frag = frag.strip()
        if frag and frag in n:
            return True
    return False


# ==================== Database Access ====================

def get_db_user(user_id: str) -> Optional[Dict[str, Any]]:
    """从数据库获取用户信息（包含偏好字段）"""
    start_time = time.time()
    ensure_her_in_path()
    from utils.db_session_manager import db_session
    from db.models import UserDB

    with db_session() as db:
        query_start = time.time()
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        logger.info(f"[get_db_user] 数据库查询耗时: {time.time() - query_start:.3f}s, user_id={user_id}")

        if user:
            interests = normalize_user_interests_field(getattr(user, "interests", None))

            # 基本信息
            user_data = {
                "id": user.id,
                "name": user.name or "",
                "age": user.age or 0,
                "gender": user.gender or "",
                "location": user.location or "",
                "interests": interests[:5],
                "bio": user.bio or "",
                "relationship_goal": getattr(user, 'relationship_goal', None) or "",
            }

            # ===== 偏好字段（用于匹配筛选）=====
            user_data["preferred_age_min"] = getattr(user, 'preferred_age_min', None)
            user_data["preferred_age_max"] = getattr(user, 'preferred_age_max', None)
            user_data["preferred_location"] = getattr(user, 'preferred_location', None)
            user_data["preferred_gender"] = getattr(user, 'preferred_gender', None)  # 想找什么性别（硬约束）
            user_data["accept_remote"] = getattr(user, 'accept_remote', None)  # 是否接受异地
            user_data["want_children"] = getattr(user, 'want_children', None)
            user_data["spending_style"] = getattr(user, 'spending_style', None)

            # ===== 扩展偏好 =====
            user_data["family_importance"] = getattr(user, 'family_importance', None)
            user_data["work_life_balance"] = getattr(user, 'work_life_balance', None)
            user_data["migration_willingness"] = getattr(user, 'migration_willingness', None)
            user_data["sleep_type"] = getattr(user, 'sleep_type', None)

            logger.info(f"[get_db_user] 总耗时: {time.time() - start_time:.3f}s, user_id={user_id}")
            return user_data

    logger.info(f"[get_db_user] 用户不存在, 耗时: {time.time() - start_time:.3f}s, user_id={user_id}")
    return None


def get_user_confidence(user_id: str) -> Dict[str, Any]:
    """
    获取用户置信度信息

    返回：
    - confidence_level: 置信度等级 (very_high/high/medium/low)
    - confidence_score: 置信度分数 (0-100)
    - confidence_icon: UI 图标 (💎/🌟/✓/⚠️)

    用于匹配结果展示，让用户了解候选人的可信程度
    """
    ensure_her_in_path()
    from utils.db_session_manager import db_session_readonly

    try:
        with db_session_readonly() as db:
            # 尝试查询置信度详情表
            try:
                from models.profile_confidence_models import ProfileConfidenceDetailDB
                confidence_detail = db.query(ProfileConfidenceDetailDB).filter(
                    ProfileConfidenceDetailDB.user_id == user_id
                ).first()

                if confidence_detail:
                    level = confidence_detail.confidence_level or "medium"
                    score = int(confidence_detail.overall_confidence * 100) if confidence_detail.overall_confidence else 30

                    # 根据 level 返回图标
                    icon_map = {
                        "very_high": "💎",
                        "high": "🌟",
                        "medium": "✓",
                        "low": "⚠️"
                    }
                    icon = icon_map.get(level, "✓")

                    return {
                        "confidence_level": level,
                        "confidence_score": score,
                        "confidence_icon": icon,
                    }
            except ImportError:
                logger.warning("[_get_user_confidence] ProfileConfidenceDetailDB 模型未导入")

            # 降级：查询实名认证状态
            try:
                from db.models import IdentityVerificationDB
                verification = db.query(IdentityVerificationDB).filter(
                    IdentityVerificationDB.user_id == user_id,
                    IdentityVerificationDB.verification_status == "verified"
                ).first()

                if verification:
                    return {
                        "confidence_level": "high",
                        "confidence_score": 70,
                        "confidence_icon": "🌟",
                    }
            except:
                pass

            # 默认：普通用户
            return {
                "confidence_level": "medium",
                "confidence_score": 40,
                "confidence_icon": "✓",
            }

    except Exception as e:
        logger.warning(f"[_get_user_confidence] 获取置信度失败: {e}")
        return {
            "confidence_level": "medium",
            "confidence_score": 40,
            "confidence_icon": "✓",
        }


def batch_get_user_confidence(user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    🔧 [性能优化] 批量获取用户置信度信息

    解决 N+1 查询问题：一次数据库查询获取所有用户的置信度。

    Args:
        user_ids: 用户 ID 列表

    Returns:
        Dict[user_id, confidence_info]
    """
    start_time = time.time()
    if not user_ids:
        return {}

    ensure_her_in_path()
    from utils.db_session_manager import db_session_readonly

    # 默认置信度
    default_confidence = {
        "confidence_level": "medium",
        "confidence_score": 40,
        "confidence_icon": "✓",
    }

    result = {uid: default_confidence.copy() for uid in user_ids}

    try:
        with db_session_readonly() as db:
            # 批量查询置信度详情表
            try:
                from models.profile_confidence_models import ProfileConfidenceDetailDB
                confidence_details = db.query(ProfileConfidenceDetailDB).filter(
                    ProfileConfidenceDetailDB.user_id.in_(user_ids)
                ).all()

                icon_map = {
                    "very_high": "💎",
                    "high": "🌟",
                    "medium": "✓",
                    "low": "⚠️"
                }

                for detail in confidence_details:
                    level = detail.confidence_level or "medium"
                    score = int(detail.overall_confidence * 100) if detail.overall_confidence else 30
                    result[detail.user_id] = {
                        "confidence_level": level,
                        "confidence_score": score,
                        "confidence_icon": icon_map.get(level, "✓"),
                    }
            except ImportError:
                logger.warning("[batch_get_user_confidence] ProfileConfidenceDetailDB 模型未导入")

            # 批量查询实名认证状态（补充已认证用户的置信度）
            try:
                from db.models import IdentityVerificationDB
                verified_users = db.query(IdentityVerificationDB.user_id).filter(
                    IdentityVerificationDB.user_id.in_(user_ids),
                    IdentityVerificationDB.verification_status == "verified"
                ).all()

                for (uid,) in verified_users:
                    # 如果没有更高级的置信度，升级为 high
                    if result[uid]["confidence_level"] == "medium":
                        result[uid] = {
                            "confidence_level": "high",
                            "confidence_score": 70,
                            "confidence_icon": "🌟",
                        }
            except Exception as e:
                logger.warning(f"[batch_get_user_confidence] 实名认证查询失败: {e}")

    except Exception as e:
        logger.warning(f"[batch_get_user_confidence] 批量获取置信度失败: {e}")

    logger.info(f"[batch_get_user_confidence] 完成: {len(user_ids)} 用户, 耗时 {time.time() - start_time:.3f}s")
    return result


# ==================== Exports ====================

__all__ = [
    "get_her_root",
    "ensure_her_in_path",
    "get_current_user_id",
    "run_async",
    "get_db_user",
    "get_user_confidence",
    "batch_get_user_confidence",
    "normalize_user_interests_field",
    "should_exclude_demo_candidate_name",
]