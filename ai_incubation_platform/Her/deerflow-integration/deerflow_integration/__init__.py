"""
DeerFlow Integration for Her Project

提供统一的 DeerFlow Agent 运行时访问接口。

根据孵化器标准（PLATFORM_AGENT_STANDARD），所有 Agent 能力统一使用 DeerFlow 2.0，
包括：意图识别、工具调用编排、工作流、状态管理、长期记忆。

使用方式：
    from deerflow_integration import get_deerflow_client

    client = get_deerflow_client()
    response = client.chat("帮我找对象")
"""

import os
import sys
from pathlib import Path
from typing import Optional

# DeerFlow 可用状态
DEERFLOW_AVAILABLE = False
DeerFlowClient = None

# 配置 DeerFlow 路径
# 优先使用环境变量，否则使用相对路径
HER_PROJECT_ROOT = Path(os.environ.get("HER_PROJECT_ROOT", Path(__file__).parent.parent.parent))
DEERFLOW_PATH = HER_PROJECT_ROOT / "deerflow" / "backend" / "packages" / "harness"
DEERFLOW_CONFIG_PATH = HER_PROJECT_ROOT / "deerflow" / "config.yaml"

# 添加 DeerFlow 到 Python 路径
if DEERFLOW_PATH.exists():
    harness_path = str(DEERFLOW_PATH)
    if harness_path not in sys.path:
        sys.path.insert(0, harness_path)
    sys.path.insert(0, str(DEERFLOW_PATH))

    try:
        from deerflow.client import DeerFlowClient as _DeerFlowClient
        DeerFlowClient = _DeerFlowClient
        DEERFLOW_AVAILABLE = True
    except ImportError as e:
        # DeerFlow 依赖未安装，降级处理
        import logging
        logging.warning(f"DeerFlow 导入失败: {e}")
        logging.warning("请先安装 DeerFlow 依赖: cd Her/deerflow/backend && uv sync")
        DEERFLOW_AVAILABLE = False

# 全局客户端实例（懒加载）
_deerflow_client: Optional[DeerFlowClient] = None


def get_deerflow_client(
    config_path: Optional[str] = None,
    model_name: Optional[str] = None,
    thinking_enabled: bool = True,
    **kwargs
) -> Optional[DeerFlowClient]:
    """
    获取 DeerFlow 客户端实例

    Args:
        config_path: DeerFlow 配置文件路径（默认使用 Her/deerflow/config.yaml）
        model_name: 模型名称（可选）
        thinking_enabled: 是否启用思考模式
        **kwargs: 其他 DeerFlowClient 参数

    Returns:
        DeerFlowClient 实例，如果 DeerFlow 未安装则返回 None

    Example:
        client = get_deerflow_client()
        if client:
            response = client.chat("帮我找对象", thread_id="user-123")
        else:
            # 降级处理
            response = "DeerFlow 未安装"
    """
    if not DEERFLOW_AVAILABLE:
        return None

    global _deerflow_client

    # 使用默认配置路径
    if config_path is None:
        config_path = str(DEERFLOW_CONFIG_PATH)

    # 检查配置文件是否存在
    if not Path(config_path).exists():
        import logging
        logging.warning(f"DeerFlow 配置文件不存在: {config_path}")
        logging.warning("请先创建配置文件: cd Her/deerflow && make config")
        return None

    # 懒加载创建客户端
    if _deerflow_client is None:
        try:
            _deerflow_client = DeerFlowClient(
                config_path=config_path,
                model_name=model_name,
                thinking_enabled=thinking_enabled,
                **kwargs
            )
        except Exception as e:
            import logging
            logging.error(f"DeerFlow 客户端创建失败: {e}")
            return None

    return _deerflow_client


def reset_deerflow_client():
    """重置 DeerFlow 客户端（用于配置更新后）"""
    global _deerflow_client
    _deerflow_client = None


def is_deerflow_available() -> bool:
    """检查 DeerFlow 是否可用"""
    return DEERFLOW_AVAILABLE


def get_deerflow_status() -> dict:
    """
    获取 DeerFlow 状态信息

    Returns:
        dict: {
            "available": bool,
            "path": str,
            "config_path": str,
            "config_exists": bool
        }
    """
    return {
        "available": DEERFLOW_AVAILABLE,
        "path": str(DEERFLOW_PATH),
        "config_path": str(DEERFLOW_CONFIG_PATH),
        "config_exists": DEERFLOW_CONFIG_PATH.exists()
    }


__all__ = [
    "get_deerflow_client",
    "reset_deerflow_client",
    "is_deerflow_available",
    "get_deerflow_status",
    "DEERFLOW_AVAILABLE",
    "DeerFlowClient"
]