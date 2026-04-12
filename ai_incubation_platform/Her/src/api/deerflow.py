"""
DeerFlow API Routes - Her 项目 DeerFlow 集成接口

提供前端调用 DeerFlow Agent 的 HTTP 接口。

路由：
- POST /api/deerflow/chat: 发送消息
- POST /api/deerflow/stream: 流式发送消息
- GET /api/deerflow/status: 获取 DeerFlow 状态
- POST /api/deerflow/memory/sync: 同步用户画像到 Memory

设计原则（AI Native）：
- DeerFlow 是 Agent 运行时，负责意图识别、工具编排、状态管理
- Her 只提供业务 Tools（匹配、关系分析、约会策划等）
- Memory 系统打通：用户画像注入 DeerFlow，Agent 知道用户背景
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import sys
import json

from utils.logger import logger

router = APIRouter(prefix="/api/deerflow", tags=["deerflow"])

# DeerFlow 集成
try:
    # 设置 Her 项目根目录
    HER_PROJECT_ROOT = os.environ.get(
        "HER_PROJECT_ROOT",
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )

    # 添加 DeerFlow 到 Python 路径
    deerflow_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", "packages", "harness")
    if deerflow_path not in sys.path:
        sys.path.insert(0, deerflow_path)

    from deerflow.client import DeerFlowClient
    from deerflow.config.app_config import reload_app_config

    DEERFLOW_AVAILABLE = True

    # 初始化 DeerFlow 客户端
    config_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml")

    # 全局客户端缓存
    _deerflow_client_cache: Optional[DeerFlowClient] = None

    def get_deerflow_client() -> Optional[DeerFlowClient]:
        """获取 DeerFlow 客户端实例（带缓存）"""
        global _deerflow_client_cache

        if _deerflow_client_cache is not None:
            return _deerflow_client_cache

        if os.path.exists(config_path):
            reload_app_config(config_path)
            _deerflow_client_cache = DeerFlowClient(config_path=config_path)
            return _deerflow_client_cache
        return None

    def reset_deerflow_client():
        """重置 DeerFlow 客户端缓存（在 Memory 更新后调用）"""
        global _deerflow_client_cache
        _deerflow_client_cache = None
        logger.info("DeerFlow client cache reset")

except ImportError as e:
    logger.warning(f"DeerFlow not available: {e}")
    DEERFLOW_AVAILABLE = False
    DeerFlowClient = None
    get_deerflow_client = lambda: None
    reset_deerflow_client = lambda: None


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None


class StreamRequest(BaseModel):
    """流式聊天请求"""
    message: str
    thread_id: str
    user_id: Optional[str] = None


class DeerFlowResponse(BaseModel):
    """DeerFlow 响应"""
    success: bool
    ai_message: str
    intent: Optional[Dict[str, Any]] = None
    generative_ui: Optional[Dict[str, Any]] = None
    suggested_actions: Optional[list] = None
    deerflow_used: Optional[bool] = None
    tool_result: Optional[Dict[str, Any]] = None  # 新增：工具返回的结构化数据


class DeerFlowStatusResponse(BaseModel):
    """DeerFlow 状态响应"""
    available: bool
    path: str
    config_path: str
    config_exists: bool
    memory_enabled: bool


class MemorySyncRequest(BaseModel):
    """Memory 同步请求"""
    user_id: str


class MemorySyncResponse(BaseModel):
    """Memory 同步响应"""
    success: bool
    facts_count: int
    message: str


# ==================== Helper Functions ====================

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    获取 Her 用户画像

    从 Her 的用户服务获取用户基本信息和偏好
    """
    try:
        # 确保 Her 在路径中
        her_root = HER_PROJECT_ROOT
        if her_root not in sys.path:
            sys.path.insert(0, her_root)

        from src.services.user_service import UserService

        user_service = UserService()
        user = user_service.get_user(user_id)

        if not user:
            return {}

        return {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "relationship_goal": user.relationship_goal,
            "interests": user.interests or [],
            "bio": user.bio or "",
            "occupation": user.occupation or "",
        }

    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        return {}


def build_memory_facts(user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据用户画像构建 DeerFlow Memory Facts

    DeerFlow Memory Facts 格式：
    {
        "id": "fact-id",
        "content": "fact content",
        "category": "preference/knowledge/context/behavior/goal",
        "confidence": 0.9,
        "createdAt": "timestamp",
        "source": "user_profile"
    }
    """
    facts = []

    if not user_profile:
        return facts

    # 基本信息 - context 类别
    if user_profile.get("age"):
        facts.append({
            "id": f"user-age-{user_profile['id']}",
            "content": f"用户年龄：{user_profile['age']}岁",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("gender"):
        gender_text = "男" if user_profile["gender"] == "male" else "女"
        facts.append({
            "id": f"user-gender-{user_profile['id']}",
            "content": f"用户性别：{gender_text}",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("location"):
        facts.append({
            "id": f"user-location-{user_profile['id']}",
            "content": f"用户所在地：{user_profile['location']}",
            "category": "context",
            "confidence": 1.0,
            "source": "user_profile"
        })

    if user_profile.get("occupation"):
        facts.append({
            "id": f"user-occupation-{user_profile['id']}",
            "content": f"用户职业：{user_profile['occupation']}",
            "category": "context",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 关系目标 - goal 类别
    if user_profile.get("relationship_goal"):
        goal_mapping = {
            "serious": "认真恋爱",
            "marriage": "奔着结婚",
            "dating": "轻松交友",
            "casual": "随便聊聊",
        }
        goal_text = goal_mapping.get(user_profile["relationship_goal"], user_profile["relationship_goal"])
        facts.append({
            "id": f"user-goal-{user_profile['id']}",
            "content": f"用户的关系目标：{goal_text}",
            "category": "goal",
            "confidence": 1.0,
            "source": "user_profile"
        })

    # 兴趣爱好 - preference 类别
    interests = user_profile.get("interests", [])
    if interests:
        interests_text = ", ".join(interests[:5])  #最多5个
        facts.append({
            "id": f"user-interests-{user_profile['id']}",
            "content": f"用户的兴趣爱好：{interests_text}",
            "category": "preference",
            "confidence": 0.9,
            "source": "user_profile"
        })

    # 个人简介 - context 类别（如果有）
    bio = user_profile.get("bio", "")
    if bio and len(bio) > 10:
        facts.append({
            "id": f"user-bio-{user_profile['id']}",
            "content": f"用户简介：{bio[:100]}...",  # 截断避免过长
            "category": "context",
            "confidence": 0.8,
            "source": "user_profile"
        })

    return facts


def sync_user_memory_to_deerflow(user_id: str) -> int:
    """
    同步用户画像到 DeerFlow Memory

    Returns:
        同步的 facts 数量
    """
    if not DEERFLOW_AVAILABLE:
        logger.warning("DeerFlow not available, skip memory sync")
        return 0

    client = get_deerflow_client()
    if not client:
        logger.warning("DeerFlow client not initialized, skip memory sync")
        return 0

    try:
        # 获取用户画像
        user_profile = get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found for {user_id}")
            return 0

        # 构建 Memory Facts
        facts = build_memory_facts(user_profile)
        if not facts:
            logger.warning(f"No facts to sync for {user_id}")
            return 0

        # 获取当前 Memory
        current_memory = client.get_memory()
        current_facts = current_memory.get("facts", [])

        # 去重：移除旧的同一用户 facts
        existing_ids = {f.get("id") for f in current_facts}
        user_fact_prefix = f"user-"
        new_facts = [f for f in current_facts if not f.get("id", "").startswith(user_fact_prefix)]

        # 添加新的用户 facts
        new_facts.extend(facts)

        # 更新 Memory
        # 注意：DeerFlow Memory 可能不支持直接写入 facts
        # 这里我们通过 Memory 的文件存储方式直接写入
        memory_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".deer-flow", "memory.json")

        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory_data = json.load(f)
        else:
            memory_data = {
                "workContext": "",
                "personalContext": "",
                "topOfMind": "",
                "recentMonths": "",
                "earlierContext": "",
                "longTermBackground": "",
                "facts": []
            }

        # 更新 facts
        memory_data["facts"] = new_facts

        # 写入文件
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        with open(memory_path, "w") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Synced {len(facts)} facts to DeerFlow Memory for user {user_id}")

        # 重置客户端缓存，让 DeerFlow 重新加载 Memory
        reset_deerflow_client()

        return len(facts)

    except Exception as e:
        logger.error(f"Failed to sync user memory: {e}")
        return 0


# ==================== Routes ====================

@router.post("/memory/sync", response_model=MemorySyncResponse)
async def sync_memory(request: MemorySyncRequest):
    """
    同步用户画像到 DeerFlow Memory

    将用户的年龄、性别、所在地、兴趣爱好、关系目标等信息
    注入到 DeerFlow 的记忆系统，让 Agent 了解用户背景。

    Args:
        request: MemorySyncRequest

    Returns:
        MemorySyncResponse
    """
    logger.info(f"DeerFlow Memory sync request for user {request.user_id}")

    if not DEERFLOW_AVAILABLE:
        return MemorySyncResponse(
            success=False,
            facts_count=0,
            message="DeerFlow 服务未启动"
        )

    facts_count = sync_user_memory_to_deerflow(request.user_id)

    if facts_count > 0:
        return MemorySyncResponse(
            success=True,
            facts_count=facts_count,
            message=f"已同步 {facts_count} 条用户信息到 DeerFlow Memory"
        )
    else:
        return MemorySyncResponse(
            success=False,
            facts_count=0,
            message="同步失败或用户信息不完整"
        )


@router.post("/chat", response_model=DeerFlowResponse)
async def chat(request: ChatRequest):
    """
    发送消息到 DeerFlow Agent

    流程：
    1. 如果提供了 user_id，先同步用户画像到 Memory
    2. 调用 DeerFlow Agent 处理消息
    3. 返回响应（包含结构化数据供前端渲染）

    Args:
        request: ChatRequest

    Returns:
        DeerFlowResponse
    """
    logger.info(f"DeerFlow API: chat request, message={request.message[:50]}...")

    if not DEERFLOW_AVAILABLE:
        return DeerFlowResponse(
            success=False,
            ai_message="DeerFlow 服务未启动，请先启动 DeerFlow：cd Her/deerflow && make dev",
            deerflow_used=False
        )

    client = get_deerflow_client()
    if not client:
        return DeerFlowResponse(
            success=False,
            ai_message="DeerFlow 配置文件不存在或初始化失败",
            deerflow_used=False
        )

    try:
        # 如果有 user_id，同步用户画像到 Memory（首次对话时）
        if request.user_id:
            sync_user_memory_to_deerflow(request.user_id)

        # 调用 DeerFlow
        thread_id = request.thread_id or f"her-{request.user_id or 'anonymous'}-{os.urandom(4).hex()}"

        response_text = client.chat(request.message, thread_id=thread_id)

        # 解析响应，提取结构化数据
        # DeerFlow Agent 调用 Her Tools 后，返回的可能是结构化 JSON
        tool_result = None
        generative_ui = None

        try:
            # 尝试解析 JSON 格式的响应（如果 Agent 返回了结构化数据）
            if response_text.startswith("{") and response_text.endswith("}"):
                parsed = json.loads(response_text)
                if parsed.get("success") and parsed.get("data"):
                    tool_result = parsed
                    # 根据 tool_result 构建 generative_ui
                    generative_ui = build_generative_ui_from_tool_result(parsed)
                    response_text = parsed.get("summary", response_text)
        except json.JSONDecodeError:
            # 不是 JSON，保持原始文本
            pass

        # 构建响应
        return DeerFlowResponse(
            success=True,
            ai_message=response_text,
            deerflow_used=True,
            generative_ui=generative_ui,
            tool_result=tool_result
        )

    except Exception as e:
        logger.error(f"DeerFlow chat error: {e}")
        return DeerFlowResponse(
            success=False,
            ai_message=f"DeerFlow 处理出错：{str(e)}",
            deerflow_used=False
        )


def build_generative_ui_from_tool_result(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据工具返回的结构化数据构建 Generative UI

    前端根据 component_type 渲染不同的卡片
    """
    data = tool_result.get("data", {})

    # 匹配结果 → MatchCardList
    if data.get("matches") or data.get("recommendations"):
        matches = data.get("matches") or data.get("recommendations")
        return {
            "component_type": "MatchCardList",
            "props": {
                "matches": matches,
                "total": data.get("total", len(matches))
            }
        }

    # 兼容性分析 → CompatibilityChart
    if data.get("overall_score") and data.get("dimensions"):
        return {
            "component_type": "CompatibilityChart",
            "props": {
                "overall_score": data.get("overall_score"),
                "dimensions": data.get("dimensions"),
                "conflicts": data.get("conflicts", []),
                "strengths": data.get("strengths", [])
            }
        }

    # 约会方案 → DatePlanCard
    if data.get("plans"):
        return {
            "component_type": "DatePlanCard",
            "props": {
                "plans": data.get("plans"),
                "best_pick": data.get("best_pick"),
                "tips": data.get("tips", [])
            }
        }

    # 破冰建议 → IcebreakerCard
    if data.get("icebreakers"):
        return {
            "component_type": "IcebreakerCard",
            "props": {
                "icebreakers": data.get("icebreakers"),
                "best_pick": data.get("best_pick"),
                "tips": data.get("tips", [])
            }
        }

    # 话题推荐 → TopicsCard
    if data.get("topics"):
        return {
            "component_type": "TopicsCard",
            "props": {
                "topics": data.get("topics"),
                "total": data.get("total")
            }
        }

    # 关系健康度 → RelationshipHealthCard
    if data.get("health_score"):
        return {
            "component_type": "RelationshipHealthCard",
            "props": {
                "health_score": data.get("health_score"),
                "strengths": data.get("strengths", []),
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", [])
            }
        }

    # 默认 → SimpleResponse
    return {
        "component_type": "SimpleResponse",
        "props": {"content": tool_result.get("summary", "")}
    }


@router.post("/stream")
async def stream(request: StreamRequest):
    """
    流式发送消息到 DeerFlow Agent

    Args:
        request: StreamRequest

    Returns:
        StreamingResponse (SSE format)
    """
    from fastapi.responses import StreamingResponse
    import json

    logger.info(f"DeerFlow API: stream request, thread_id={request.thread_id}")

    if not DEERFLOW_AVAILABLE:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': 'DeerFlow not available'}})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    client = get_deerflow_client()
    if not client:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': 'DeerFlow client not initialized'}})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # 同步用户画像
    if request.user_id:
        sync_user_memory_to_deerflow(request.user_id)

    async def generate_stream():
        try:
            for event in client.stream(request.message, thread_id=request.thread_id):
                yield f"data: {json.dumps({'type': event.type, 'data': event.data})}\n\n"
        except Exception as e:
            logger.error(f"DeerFlow stream error: {e}")
            yield f"data: {json.dumps({'type': 'end', 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.get("/status", response_model=DeerFlowStatusResponse)
async def get_status():
    """
    获取 DeerFlow 状态

    Returns:
        DeerFlowStatusResponse
    """
    memory_path = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", ".deer-flow", "memory.json")
    memory_enabled = os.path.exists(memory_path)

    return DeerFlowStatusResponse(
        available=DEERFLOW_AVAILABLE,
        path=os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", "packages", "harness"),
        config_path=os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml"),
        config_exists=os.path.exists(os.path.join(HER_PROJECT_ROOT, "deerflow", "config.yaml")),
        memory_enabled=memory_enabled
    )