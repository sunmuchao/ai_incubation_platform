"""
Agent Skill 抽象基类

所有 Skill 必须继承此基类，确保统一的接口和规范。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseSkill(ABC):
    """
    Agent Skill 抽象基类

    定义所有 Skill 必须实现的标准接口：
    - name: Skill 唯一标识符
    - version: 版本号
    - description: 功能描述
    - get_input_schema(): 输入参数 JSONSchema
    - get_output_schema(): 输出参数 JSONSchema
    - execute(): 执行方法

    子类应继承此类并实现抽象方法，而非重复定义通用逻辑。

    示例:
        class MyCustomSkill(BaseSkill):
            name = "my_custom_skill"
            version = "1.0.0"
            description = "自定义 Skill 描述"

            def get_input_schema(self) -> dict:
                return {...}

            def get_output_schema(self) -> dict:
                return {...}

            async def execute(self, **kwargs) -> dict:
                # 实现业务逻辑
                return {"success": True, "data": {...}}
    """

    # ========== 类属性 (子类必须覆盖) ==========

    name: str = ""
    """Skill 唯一标识符，建议使用 snake_case 命名"""

    version: str = "1.0.0"
    """Skill 版本号，遵循语义化版本规范"""

    description: str = ""
    """Skill 功能描述，应包含核心能力和自主触发场景"""

    # ========== 通用配置 (可选覆盖) ==========

    SILENCE_THRESHOLD: Dict[str, int] = {}
    """沉默阈值配置（如需要）"""

    TOPIC_CATEGORIES: List[str] = []
    """话题类别列表（如需要）"""

    # ========== 抽象方法 (必须实现) ==========

    @abstractmethod
    def get_input_schema(self) -> dict:
        """
        获取输入参数 JSONSchema

        定义 Skill 所需的输入参数格式，用于参数校验和文档生成。

        Returns:
            JSONSchema 格式的输入参数定义
        """
        pass

    @abstractmethod
    def get_output_schema(self) -> dict:
        """
        获取输出参数 JSONSchema

        定义 Skill 返回数据的格式，用于响应校验和文档生成。

        Returns:
            JSONSchema 格式的输出参数定义
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """
        执行 Skill 核心逻辑

        Args:
            **kwargs: 输入参数，需符合 get_input_schema() 定义

        Returns:
            执行结果字典，应包含:
            - success: bool - 是否执行成功
            - ai_message: str - AI 生成的自然语言回复
            - data/error: Any - 成功时返回 data，失败时返回 error
        """
        pass

    # ========== 通用方法 (可选覆盖) ==========

    def get_metadata(self) -> dict:
        """
        获取 Skill 元数据

        Returns:
            Skill 元数据字典
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": self.get_input_schema(),
            "output_schema": self.get_output_schema()
        }

    def validate_input(self, data: dict) -> tuple[bool, Optional[str]]:
        """
        验证输入参数

        基于 input_schema 进行基础验证，子类可覆盖以实现更复杂的验证逻辑。

        Args:
            data: 输入数据字典

        Returns:
            (是否有效，错误信息)
        """
        if not isinstance(data, dict):
            return False, "Input must be a dictionary"

        schema = self.get_input_schema()
        required = schema.get("required", [])

        for field in required:
            if field not in data:
                return False, f"Missing required field: {field}"

        return True, None

    def _log_execution(self, message: str, level: str = "info") -> None:
        """
        记录执行日志

        Args:
            message: 日志消息
            level: 日志级别 (info/warning/error/debug)
        """
        from utils.logger import logger
        log_method = getattr(logger, level, logger.info)
        log_method(f"[{self.name}] {message}")

    def _now(self) -> datetime:
        """获取当前时间（方便测试 mock）"""
        return datetime.now()

    def _format_timestamp(self, dt: datetime) -> str:
        """格式化时间戳"""
        return dt.isoformat()
