"""
心跳规则解析器

读取并解析 HEARTBEAT_RULES.md 文件，提取规则定义。
支持 YAML 格式的规则定义，包括：
- name: 规则名称
- interval: 执行间隔
- prompt: 执行提示词
- action_type: 默认行动类型
"""
import os
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from utils.logger import logger


HEARTBEAT_RULES_FILE = os.path.join(
    os.path.dirname(__file__),
    "HEARTBEAT_RULES.md"
)


class HeartbeatRule:
    """
    心跳规则数据结构
    """

    def __init__(
        self,
        name: str,
        interval: str,
        prompt: str,
        action_type: str = None,
        guidelines: List[str] = None
    ):
        self.name = name
        self.interval = interval
        self.prompt = prompt
        self.action_type = action_type
        self.guidelines = guidelines or []

        # 解析间隔为分钟数
        self.interval_minutes = self._parse_interval(interval)

    def _parse_interval(self, interval: str) -> int:
        """
        解析间隔字符串为分钟数

        支持：
        - 30m = 30分钟
        - 1h = 1小时 = 60分钟
        - 24h = 24小时 = 1440分钟
        - 168h = 168小时 = 10080分钟（一周）
        """
        match = re.match(r'^(\d+)([mh])$', interval.lower())
        if not match:
            logger.warning(f"Invalid interval format: {interval}, defaulting to 30m")
            return 30

        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'm':
            return value
        elif unit == 'h':
            return value * 60

        return 30

    def is_due(self, last_run_at: Optional[datetime]) -> bool:
        """
        判断规则是否到期执行

        Args:
            last_run_at: 最后执行时间

        Returns:
            是否到期
        """
        if last_run_at is None:
            # 从未执行过，需要执行
            return True

        minutes_since_last = (datetime.now() - last_run_at).total_seconds() / 60
        return minutes_since_last >= self.interval_minutes

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "interval": self.interval,
            "interval_minutes": self.interval_minutes,
            "prompt": self.prompt,
            "action_type": self.action_type,
            "guidelines": self.guidelines
        }

    def __repr__(self):
        return f"<HeartbeatRule(name={self.name}, interval={self.interval})>"


class HeartbeatRuleParser:
    """
    心跳规则解析器

    从 HEARTBEAT_RULES.md 文件解析规则定义
    """

    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or HEARTBEAT_RULES_FILE
        self.rules: List[HeartbeatRule] = []
        self.guidelines: List[str] = []
        self.last_loaded_at: Optional[datetime] = None

    def load_rules(self) -> List[HeartbeatRule]:
        """
        加载并解析规则文件

        Returns:
            规则列表
        """
        if not os.path.exists(self.rules_file):
            logger.warning(f"HEARTBEAT_RULES.md not found at {self.rules_file}, using default rules")
            return self._get_default_rules()

        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                content = f.read()

            self.rules = self._parse_rules_from_markdown(content)
            self.guidelines = self._parse_guidelines_from_markdown(content)
            self.last_loaded_at = datetime.now()

            logger.info(f"Loaded {len(self.rules)} heartbeat rules from {self.rules_file}")
            return self.rules

        except Exception as e:
            logger.error(f"Failed to load heartbeat rules: {e}")
            return self._get_default_rules()

    def _parse_rules_from_markdown(self, content: str) -> List[HeartbeatRule]:
        """
        从 Markdown 内容解析规则

        支持两种格式：
        1. YAML 格式（在 ```yaml 代码块内）
        2. 简化格式（直接定义）
        """
        rules = []

        # 提取 YAML 代码块
        yaml_blocks = re.findall(r'```yaml\s*(.*?)\s*```', content, re.DOTALL)

        for yaml_block in yaml_blocks:
            # 解析 YAML 内容（简化实现，不依赖 yaml 库）
            rules.extend(self._parse_yaml_rules(yaml_block))

        # 如果没有 YAML 块，尝试从结构化内容解析
        if not rules:
            rules = self._parse_structured_rules(content)

        return rules

    def _parse_yaml_rules(self, yaml_content: str) -> List[HeartbeatRule]:
        """
        解析 YAML 格式的规则

        简化实现，使用正则表达式解析
        """
        rules = []

        # 匹配规则块
        rule_pattern = r'-\s*name:\s*(\S+)\s*interval:\s*(\S+)\s*prompt:\s*`?([^`]+)`?\s*action_type:\s*(\S+)?'
        matches = re.findall(rule_pattern, yaml_content, re.MULTILINE)

        for match in matches:
            name = match[0].strip()
            interval = match[1].strip()
            prompt = match[2].strip()
            action_type = match[3].strip() if match[3] else None

            # 处理多行 prompt（简化）
            prompt = prompt.replace('\\n', '\n').strip()

            rule = HeartbeatRule(
                name=name,
                interval=interval,
                prompt=prompt,
                action_type=action_type
            )
            rules.append(rule)

        return rules

    def _parse_structured_rules(self, content: str) -> List[HeartbeatRule]:
        """
        从结构化 Markdown 内容解析规则

        支持格式：
        - name: check_new_matches
        - interval: 30m
        - prompt: 检查是否有新匹配...
        """
        rules = []

        # 匹配规则段落
        rule_sections = re.split(r'\n- name:', content)

        for section in rule_sections[1:]:  # 第一个是规则列表前的内容
            lines = section.strip().split('\n')
            if not lines:
                continue

            # 解析规则属性
            name = lines[0].strip()
            interval = "30m"
            prompt = ""
            action_type = None

            for line in lines[1:]:
                if line.startswith('interval:'):
                    interval = line.replace('interval:', '').strip()
                elif line.startswith('prompt:'):
                    prompt = line.replace('prompt:', '').strip()
                elif line.startswith('action_type:'):
                    action_type = line.replace('action_type:', '').strip()
                elif line.strip() and not line.startswith('-'):
                    # 继续追加 prompt（多行）
                    prompt += '\n' + line.strip()

            if name and interval:
                rule = HeartbeatRule(
                    name=name,
                    interval=interval,
                    prompt=prompt.strip(),
                    action_type=action_type
                )
                rules.append(rule)

        return rules

    def _parse_guidelines_from_markdown(self, content: str) -> List[str]:
        """
        从 Markdown 内容解析指导原则
        """
        guidelines = []

        # 匹配指导原则部分
        guideline_match = re.search(r'## 心跳指导原则\s*(.*?)\s*##', content, re.DOTALL)
        if guideline_match:
            guideline_content = guideline_match.group(1)
            # 提取每条指导原则
            for line in guideline_content.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    guidelines.append(line[1:].strip())

        return guidelines

    def _get_default_rules(self) -> List[HeartbeatRule]:
        """
        获取默认规则（当文件不存在时使用）
        """
        return [
            HeartbeatRule(
                name="check_new_matches",
                interval="30m",
                prompt="检查是否有新匹配成功但未推送破冰建议的用户",
                action_type="icebreaker"
            ),
            HeartbeatRule(
                name="check_stale_conversations",
                interval="1h",
                prompt="检查是否有对话停滞超过72小时的匹配，需要推送话题激活",
                action_type="topic_suggestion"
            ),
            HeartbeatRule(
                name="check_user_activity",
                interval="24h",
                prompt="检查是否有超过7天未活跃的用户，需要推送激活提醒",
                action_type="activation_reminder"
            ),
        ]

    def get_due_rules(self, rule_states: Dict[str, datetime]) -> List[HeartbeatRule]:
        """
        筛选到期需要执行的规则

        Args:
            rule_states: 规则名称到最后执行时间的映射

        Returns:
            到期规则列表
        """
        due_rules = []

        for rule in self.rules:
            last_run = rule_states.get(rule.name)
            if rule.is_due(last_run):
                due_rules.append(rule)

        logger.debug(f"Found {len(due_rules)} due rules out of {len(self.rules)} total")
        return due_rules

    def should_skip_heartbeat(self, due_rules: List[HeartbeatRule]) -> bool:
        """
        判断是否跳过心跳

        无到期规则时跳过，节省 LLM 调用
        """
        if not due_rules:
            logger.info("No due rules, skipping heartbeat (reason=no-rules-due)")
            return True
        return False


def load_heartbeat_rules() -> List[HeartbeatRule]:
    """
    加载心跳规则（便捷函数）
    """
    parser = HeartbeatRuleParser()
    return parser.load_rules()


# ============= 导出 =============

__all__ = [
    "HeartbeatRule",
    "HeartbeatRuleParser",
    "load_heartbeat_rules",
    "HEARTBEAT_RULES_FILE",
]