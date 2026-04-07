"""
智能代码审查服务
提供代码异味检测、最佳实践建议、安全风险识别等功能
"""
import os
import re
import ast
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"  # 严重，必须修复
    MAJOR = "major"        # 重要，建议修复
    MINOR = "minor"        # 轻微，可选修复
    INFO = "info"          # 提示，仅供参考


class IssueCategory(Enum):
    """问题类别"""
    CODE_SMELL = "code_smell"      # 代码异味
    SECURITY = "security"          # 安全风险
    PERFORMANCE = "performance"    # 性能问题
    STYLE = "style"                # 代码风格
    BEST_PRACTICE = "best_practice"  # 最佳实践
    MAINTAINABILITY = "maintainability"  # 可维护性
    BUG_RISK = "bug_risk"          # 潜在 Bug


@dataclass
class CodeIssue:
    """代码问题"""
    id: str
    category: IssueCategory
    severity: IssueSeverity
    line: int
    column: int
    message: str
    suggestion: str
    rule_id: str
    code_snippet: str = ""
    references: List[str] = field(default_factory=list)


class CodeReviewService:
    """
    智能代码审查服务

    功能:
    1. 代码异味检测 (Code Smell Detection)
    2. 最佳实践建议 (Best Practice Suggestions)
    3. 安全风险识别 (Security Risk Detection)
    4. 性能问题分析 (Performance Analysis)
    5. 代码风格检查 (Style Checking)
    """

    def __init__(self):
        self._rules = self._load_rules()
        logger.info("CodeReviewService initialized")

    def _load_rules(self) -> Dict[str, Dict]:
        """加载审查规则"""
        return {
            # === 代码异味规则 ===
            "CS001": {
                "name": "过长函数",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MAJOR,
                "description": "函数过长，难以理解和维护",
                "threshold": 50,  # 最大行数
            },
            "CS002": {
                "name": "过多参数",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MINOR,
                "description": "函数参数过多，建议封装为对象",
                "threshold": 5,  # 最大参数数
            },
            "CS003": {
                "name": "过深嵌套",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MAJOR,
                "description": "嵌套层级过深，建议重构",
                "threshold": 4,  # 最大嵌套深度
            },
            "CS004": {
                "name": "重复代码",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MAJOR,
                "description": "检测到重复代码块，建议提取为公共函数",
            },
            "CS005": {
                "name": "过长行",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MINOR,
                "description": "单行代码过长，建议拆分",
                "threshold": 120,  # 最大字符数
            },
            "CS006": {
                "name": "魔法数字",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MINOR,
                "description": "使用未命名的字面量，建议定义为常量",
            },
            "CS007": {
                "name": "过多返回值",
                "category": IssueCategory.CODE_SMELL,
                "severity": IssueSeverity.MINOR,
                "description": "函数有多个返回点，建议统一返回",
                "threshold": 3,
            },

            # === 安全风险规则 ===
            "SEC001": {
                "name": "SQL 注入风险",
                "category": IssueCategory.SECURITY,
                "severity": IssueSeverity.CRITICAL,
                "description": "检测到可能的 SQL 注入风险",
            },
            "SEC002": {
                "name": "硬编码凭证",
                "category": IssueCategory.SECURITY,
                "severity": IssueSeverity.CRITICAL,
                "description": "检测到硬编码的密码或密钥",
            },
            "SEC003": {
                "name": "不安全的随机数",
                "category": IssueCategory.SECURITY,
                "severity": IssueSeverity.MAJOR,
                "description": "使用不安全的随机数生成器",
            },
            "SEC004": {
                "name": "命令注入风险",
                "category": IssueCategory.SECURITY,
                "severity": IssueSeverity.CRITICAL,
                "description": "检测到可能的命令注入风险",
            },
            "SEC005": {
                "name": "路径遍历风险",
                "category": IssueCategory.SECURITY,
                "severity": IssueSeverity.MAJOR,
                "description": "检测到可能的路径遍历风险",
            },

            # === 性能问题规则 ===
            "PERF001": {
                "name": "低效循环",
                "category": IssueCategory.PERFORMANCE,
                "severity": IssueSeverity.MAJOR,
                "description": "检测到可优化的循环结构",
            },
            "PERF002": {
                "name": "重复计算",
                "category": IssueCategory.PERFORMANCE,
                "severity": IssueSeverity.MINOR,
                "description": "循环内存在可提前的重复计算",
            },
            "PERF003": {
                "name": "大对象创建",
                "category": IssueCategory.PERFORMANCE,
                "severity": IssueSeverity.MINOR,
                "description": "循环内创建大对象，建议移至循环外",
            },

            # === 最佳实践规则 ===
            "BP001": {
                "name": "缺少文档字符串",
                "category": IssueCategory.BEST_PRACTICE,
                "severity": IssueSeverity.MINOR,
                "description": "公共函数缺少文档字符串",
            },
            "BP002": {
                "name": "缺少类型提示",
                "category": IssueCategory.BEST_PRACTICE,
                "severity": IssueSeverity.MINOR,
                "description": "函数缺少类型提示",
            },
            "BP003": {
                "name": "未使用的导入",
                "category": IssueCategory.BEST_PRACTICE,
                "severity": IssueSeverity.MINOR,
                "description": "存在未使用的导入语句",
            },
            "BP004": {
                "name": "宽泛的异常捕获",
                "category": IssueCategory.BEST_PRACTICE,
                "severity": IssueSeverity.MAJOR,
                "description": "使用过于宽泛的异常捕获",
            },
            "BP005": {
                "name": "资源未正确释放",
                "category": IssueCategory.BEST_PRACTICE,
                "severity": IssueSeverity.MAJOR,
                "description": "资源使用后未正确释放",
            },

            # === 潜在 Bug 规则 ===
            "BUG001": {
                "name": "未使用的变量",
                "category": IssueCategory.BUG_RISK,
                "severity": IssueSeverity.MINOR,
                "description": "定义了但未使用的变量",
            },
            "BUG002": {
                "name": "变量未定义就使用",
                "category": IssueCategory.BUG_RISK,
                "severity": IssueSeverity.MAJOR,
                "description": "变量在使用前未定义",
            },
            "BUG003": {
                "name": "可能的空指针",
                "category": IssueCategory.BUG_RISK,
                "severity": IssueSeverity.MAJOR,
                "description": "可能的空指针引用",
            },
            "BUG004": {
                "name": "比较总是为真/假",
                "category": IssueCategory.BUG_RISK,
                "severity": IssueSeverity.MAJOR,
                "description": "检测到逻辑错误的比较",
            },
        }

    def review_code(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        对代码进行全面审查

        Args:
            code: 待审查的代码
            language: 语言标识
            file_path: 文件路径 (可选)
            config: 审查配置 (可选)

        Returns:
            审查报告，包含问题列表、统计信息和质量评分
        """
        logger.info(f"Starting code review: language={language}, code_len={len(code)}")

        issues: List[CodeIssue] = []

        # 根据语言选择审查器
        if language == "python":
            issues.extend(self._review_python(code, file_path, config))
        elif language in ["javascript", "typescript"]:
            issues.extend(self._review_javascript(code, file_path, config))
        else:
            # 通用审查规则
            issues.extend(self._review_generic(code, file_path, config))

        # 生成质量评分
        quality_score = self._calculate_quality_score(issues)

        # 生成统计信息
        stats = self._generate_stats(issues)

        # 生成修复建议
        fix_suggestions = self._generate_fix_suggestions(issues)

        return {
            "success": True,
            "language": language,
            "file_path": file_path,
            "issues": [self._issue_to_dict(issue) for issue in issues],
            "quality_score": quality_score,
            "stats": stats,
            "fix_suggestions": fix_suggestions,
            "summary": self._generate_summary(issues, quality_score),
        }

    def _issue_to_dict(self, issue: CodeIssue) -> Dict[str, Any]:
        """将 CodeIssue 转换为字典"""
        return {
            "id": issue.id,
            "category": issue.category.value,
            "severity": issue.severity.value,
            "line": issue.line,
            "column": issue.column,
            "message": issue.message,
            "suggestion": issue.suggestion,
            "rule_id": issue.rule_id,
            "code_snippet": issue.code_snippet,
            "references": issue.references,
        }

    def _review_python(
        self,
        code: str,
        file_path: Optional[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """Python 特定审查规则"""
        import ast

        issues = []
        lines = code.split('\n')

        # 通用审查
        issues.extend(self._check_line_length(lines, config))
        issues.extend(self._check_magic_numbers(lines, config))
        issues.extend(self._check_security_python(lines, config))

        try:
            tree = ast.parse(code)

            # 检查函数
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    issues.extend(self._check_function(node, lines, config))
                elif isinstance(node, ast.ClassDef):
                    issues.extend(self._check_class(node, lines, config))

        except SyntaxError as e:
            issues.append(CodeIssue(
                id=f"SYN001",
                category=IssueCategory.BUG_RISK,
                severity=IssueSeverity.CRITICAL,
                line=e.lineno or 1,
                column=e.offset or 0,
                message=f"语法错误：{e.msg}",
                suggestion="请修复语法错误",
                rule_id="SYN001",
                code_snippet=lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else "",
            ))

        return issues

    def _review_javascript(
        self,
        code: str,
        file_path: Optional[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """JavaScript/TypeScript 特定审查规则"""
        issues = []
        lines = code.split('\n')

        # 通用审查
        issues.extend(self._check_line_length(lines, config))
        issues.extend(self._check_magic_numbers(lines, config))

        # JS 特定安全检查
        issues.extend(self._check_security_js(lines, config))

        # 检查函数
        issues.extend(self._check_js_functions(lines, config))

        return issues

    def _review_generic(
        self,
        code: str,
        file_path: Optional[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """通用审查规则"""
        issues = []
        lines = code.split('\n')

        issues.extend(self._check_line_length(lines, config))
        issues.extend(self._check_code_smells_generic(lines, config))

        return issues

    def _check_function(
        self,
        node: ast.FunctionDef,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """检查函数相关的问题"""
        issues = []
        rule = self._rules["CS001"]

        # CS001: 过长函数
        func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
        threshold = config.get('max_function_lines', rule['threshold']) if config else rule['threshold']

        if func_lines > threshold:
            issues.append(CodeIssue(
                id=f"CS001_{node.name}",
                category=rule['category'],
                severity=rule['severity'],
                line=node.lineno,
                column=node.col_offset,
                message=f"函数 '{node.name}' 过长 ({func_lines} 行)，建议拆分为更小的函数",
                suggestion=f"将函数拆分为多个小于 {threshold} 行的小函数，每个函数只负责单一职责",
                rule_id="CS001",
                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                references=["https://refactoring.guru/smells/long-method"],
            ))

        # CS002: 过多参数
        rule = self._rules["CS002"]
        num_args = len(node.args.args)
        threshold = config.get('max_params', rule['threshold']) if config else rule['threshold']

        if num_args > threshold:
            issues.append(CodeIssue(
                id=f"CS002_{node.name}",
                category=rule['category'],
                severity=rule['severity'],
                line=node.lineno,
                column=node.col_offset,
                message=f"函数 '{node.name}' 参数过多 ({num_args} 个)，建议封装为数据对象",
                suggestion="使用数据类 (dataclass) 或字典封装相关参数",
                rule_id="CS002",
                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                references=["https://refactoring.guru/smells/long-parameter-list"],
            ))

        # BP001: 缺少文档字符串
        rule = self._rules["BP001"]
        if not ast.get_docstring(node):
            # 只检查公共函数
            if not node.name.startswith('_'):
                issues.append(CodeIssue(
                    id=f"BP001_{node.name}",
                    category=rule['category'],
                    severity=rule['severity'],
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"公共函数 '{node.name}' 缺少文档字符串",
                    suggestion="添加文档字符串说明函数的功能、参数和返回值",
                    rule_id="BP001",
                    code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                ))

        # BP002: 缺少类型提示
        rule = self._rules["BP002"]
        if not node.returns and node.args.args:
            issues.append(CodeIssue(
                id=f"BP002_{node.name}",
                category=rule['category'],
                severity=rule['severity'],
                line=node.lineno,
                column=node.col_offset,
                message=f"函数 '{node.name}' 缺少返回类型提示",
                suggestion="添加类型提示，如 def {node.name}(...) -> ReturnType:",
                rule_id="BP002",
                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            ))

        # BP004: 宽泛的异常捕获
        rule = self._rules["BP004"]
        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler):
                if child.type is None:
                    issues.append(CodeIssue(
                        id=f"BP004_{node.name}_except",
                        category=rule['category'],
                        severity=rule['severity'],
                        line=child.lineno,
                        column=child.col_offset,
                        message="使用 bare except 捕获所有异常，可能掩盖问题",
                        suggestion="使用具体的异常类型，如 except ValueError:",
                        rule_id="BP004",
                        code_snippet=lines[child.lineno - 1] if child.lineno <= len(lines) else "",
                    ))
                elif isinstance(child.type, ast.Name) and child.type.id == "Exception":
                    issues.append(CodeIssue(
                        id=f"BP004_{node.name}_exception",
                        category=rule['category'],
                        severity=rule['severity'],
                        line=child.lineno,
                        column=child.col_offset,
                        message="捕获 Exception 过于宽泛，建议使用更具体的异常类型",
                        suggestion="捕获具体的异常类型，避免使用 Exception",
                        rule_id="BP004",
                        code_snippet=lines[child.lineno - 1] if child.lineno <= len(lines) else "",
                    ))

        return issues

    def _check_class(
        self,
        node: ast.ClassDef,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """检查类相关的问题"""
        issues = []

        # BP001: 缺少文档字符串
        rule = self._rules["BP001"]
        if not ast.get_docstring(node):
            issues.append(CodeIssue(
                id=f"BP001_class_{node.name}",
                category=rule['category'],
                severity=rule['severity'],
                line=node.lineno,
                column=node.col_offset,
                message=f"类 '{node.name}' 缺少文档字符串",
                suggestion="添加文档字符串说明类的职责和用途",
                rule_id="BP001",
                code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
            ))

        return issues

    def _check_line_length(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """检查行长度"""
        issues = []
        rule = self._rules["CS005"]
        threshold = config.get('max_line_length', rule['threshold']) if config else rule['threshold']

        for i, line in enumerate(lines, 1):
            # 忽略注释和导入语句
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('import ') or stripped.startswith('from '):
                continue

            if len(line) > threshold:
                issues.append(CodeIssue(
                    id=f"CS005_line_{i}",
                    category=rule['category'],
                    severity=rule['severity'],
                    line=i,
                    column=threshold,
                    message=f"行过长 ({len(line)} 字符)，超过限制 ({threshold})",
                    suggestion="将长行拆分为多行，或使用括号进行隐式连接",
                    rule_id="CS005",
                    code_snippet=line[:100] + "..." if len(line) > 100 else line,
                ))

        return issues

    def _check_magic_numbers(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """检查魔法数字"""
        issues = []
        rule = self._rules["CS006"]

        # 忽略的常见值
        ignored_values = {0, 1, -1, 2, 10, 100, 1000}

        # 匹配数字的正则
        number_pattern = re.compile(r'\b(\d+\.?\d*)\b')

        for i, line in enumerate(lines, 1):
            # 忽略注释和字符串定义
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            # 跳过常量定义行
            if re.match(r'^[A-Z_]+\s*=\s*\d+', stripped):
                continue

            matches = number_pattern.findall(line)
            for match in matches:
                try:
                    value = float(match)
                    if value not in ignored_values and value != int(value):
                        # 浮点魔法数字
                        issues.append(CodeIssue(
                            id=f"CS006_line_{i}",
                            category=rule['category'],
                            severity=rule['severity'],
                            line=i,
                            column=line.index(match),
                            message=f"魔法数字 '{match}'，建议定义为有意义的常量",
                            suggestion=f"将 {match} 定义为常量，如 MAGIC_CONSTANT = {match}",
                            rule_id="CS006",
                            code_snippet=line.strip()[:80],
                        ))
                except ValueError:
                    pass

        return issues

    def _check_security_python(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """Python 特定安全检查"""
        issues = []
        code = '\n'.join(lines)

        # SEC001: SQL 注入风险
        rule = self._rules["SEC001"]
        sql_patterns = [
            (r'execute\s*\(\s*f["\'].*SELECT.*\{', "f-string 拼接 SQL"),
            (r'execute\s*\(\s*["\'].*%s.*%.*\)', "% 格式化拼接 SQL"),
            (r'execute\s*\(\s*["\'].*\+.*\+', "+ 拼接 SQL"),
        ]
        for pattern, desc in sql_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(CodeIssue(
                    id=f"SEC001_sql_{len(issues)}",
                    category=rule['category'],
                    severity=rule['severity'],
                    line=1,
                    column=0,
                    message=f"检测到 {desc}，存在 SQL 注入风险",
                    suggestion="使用参数化查询，如 execute('SELECT * FROM users WHERE id = ?', (id,))",
                    rule_id="SEC001",
                    references=["https://owasp.org/www-community/attacks/SQL_Injection"],
                ))

        # SEC002: 硬编码凭证
        rule = self._rules["SEC002"]
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "硬编码密码"),
            (r'passwd\s*=\s*["\'][^"\']+["\']', "硬编码密码"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "硬编码密钥"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "硬编码 API 密钥"),
            (r'token\s*=\s*["\'][^"\']+["\']', "硬编码令牌"),
        ]
        for pattern, desc in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(CodeIssue(
                    id=f"SEC002_secret_{len(issues)}",
                    category=rule['category'],
                    severity=rule['severity'],
                    line=1,
                    column=0,
                    message=f"检测到 {desc}",
                    suggestion="使用环境变量或密钥管理服务存储敏感信息",
                    rule_id="SEC002",
                    references=["https://cwe.mitre.org/data/definitions/798.html"],
                ))

        # SEC004: 命令注入风险
        rule = self._rules["SEC004"]
        cmd_patterns = [
            (r'os\.system\s*\(\s*f["\']', "os.system 使用 f-string"),
            (r'subprocess\.call\s*\(\s*\w+\s*\+', "subprocess.call 字符串拼接"),
            (r'eval\s*\(', "使用 eval()"),
            (r'exec\s*\(', "使用 exec()"),
        ]
        for pattern, desc in cmd_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(CodeIssue(
                    id=f"SEC004_cmd_{len(issues)}",
                    category=rule['category'],
                    severity=rule['severity'],
                    line=1,
                    column=0,
                    message=f"检测到 {desc}，存在命令注入风险",
                    suggestion="避免使用 eval/exec，使用 subprocess 并传入列表参数",
                    rule_id="SEC004",
                    references=["https://owasp.org/www-community/attacks/Code_Injection"],
                ))

        return issues

    def _check_security_js(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """JavaScript 特定安全检查"""
        issues = []
        code = '\n'.join(lines)

        # eval 风险
        if re.search(r'\beval\s*\(', code):
            issues.append(CodeIssue(
                id="SEC004_js_eval",
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.CRITICAL,
                line=1,
                column=0,
                message="使用 eval() 存在代码注入风险",
                suggestion="避免使用 eval()，考虑使用 Function 构造函数或更安全的方式",
                rule_id="SEC004",
            ))

        # innerHTML 风险
        if re.search(r'\.innerHTML\s*=', code):
            issues.append(CodeIssue(
                id="SEC006_innerhtml",
                category=IssueCategory.SECURITY,
                severity=IssueSeverity.MAJOR,
                line=1,
                column=0,
                message="使用 innerHTML 可能存在 XSS 风险",
                suggestion="使用 textContent 或确保内容已正确转义",
                rule_id="SEC006",
            ))

        return issues

    def _check_js_functions(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """检查 JavaScript 函数"""
        issues = []

        # 简单的函数长度检查
        in_function = False
        func_start = 0
        func_name = ""
        brace_count = 0

        for i, line in enumerate(lines, 1):
            # 检测函数定义
            func_match = re.search(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*)?=>)', line)
            if func_match:
                func_name = func_match.group(1) or func_match.group(2)
                func_start = i
                in_function = True
                brace_count = line.count('{') - line.count('}')
                continue

            if in_function:
                brace_count += line.count('{') - line.count('}')

                if brace_count <= 0:
                    # 函数结束
                    func_length = i - func_start + 1
                    if func_length > 50:
                        issues.append(CodeIssue(
                            id=f"CS001_{func_name}",
                            category=IssueCategory.CODE_SMELL,
                            severity=IssueSeverity.MAJOR,
                            line=func_start,
                            column=0,
                            message=f"函数 '{func_name}' 过长 ({func_length} 行)",
                            suggestion="将函数拆分为更小的函数",
                            rule_id="CS001",
                        ))
                    in_function = False

        return issues

    def _check_code_smells_generic(
        self,
        lines: List[str],
        config: Optional[Dict[str, Any]]
    ) -> List[CodeIssue]:
        """通用代码异味检查"""
        issues = []

        # 检测 TODO/FIXME 注释
        todo_pattern = re.compile(r'#?\s*(TODO|FIXME|XXX|HACK)\b', re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            match = todo_pattern.search(line)
            if match:
                issues.append(CodeIssue(
                    id=f"INFO_todo_{i}",
                    category=IssueCategory.INFO,
                    severity=IssueSeverity.INFO,
                    line=i,
                    column=line.index(match.group(1)),
                    message=f"检测到 {match.group(1)} 注释",
                    suggestion="考虑处理或移除技术债务标记",
                    rule_id="INFO_TODO",
                    code_snippet=line.strip()[:80],
                ))

        return issues

    def _calculate_quality_score(self, issues: List[CodeIssue]) -> float:
        """
        计算代码质量评分 (0-100)

        基于问题数量和严重程度计算
        """
        if not issues:
            return 100.0

        # 问题权重
        severity_weights = {
            IssueSeverity.CRITICAL: 20,
            IssueSeverity.MAJOR: 10,
            IssueSeverity.MINOR: 5,
            IssueSeverity.INFO: 1,
        }

        total_deduction = sum(
            severity_weights.get(issue.severity, 0)
            for issue in issues
        )

        # 最高扣 100 分
        score = max(0, 100 - total_deduction)
        return round(score, 1)

    def _generate_stats(self, issues: List[CodeIssue]) -> Dict[str, Any]:
        """生成统计信息"""
        stats = {
            "total_issues": len(issues),
            "by_severity": {
                "critical": 0,
                "major": 0,
                "minor": 0,
                "info": 0,
            },
            "by_category": {
                "code_smell": 0,
                "security": 0,
                "performance": 0,
                "style": 0,
                "best_practice": 0,
                "bug_risk": 0,
            },
        }

        for issue in issues:
            stats["by_severity"][issue.severity.value] = \
                stats["by_severity"].get(issue.severity.value, 0) + 1
            stats["by_category"][issue.category.value] = \
                stats["by_category"].get(issue.category.value, 0) + 1

        return stats

    def _generate_fix_suggestions(self, issues: List[CodeIssue]) -> List[Dict[str, Any]]:
        """生成修复建议，按优先级排序"""
        # 按严重程度排序
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.MAJOR: 1,
            IssueSeverity.MINOR: 2,
            IssueSeverity.INFO: 3,
        }

        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity, 99))

        suggestions = []
        for issue in sorted_issues[:10]:  # 只返回前 10 条建议
            suggestions.append({
                "priority": severity_order.get(issue.severity, 99),
                "issue_id": issue.id,
                "rule_id": issue.rule_id,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "line": issue.line,
            })

        return suggestions

    def _generate_summary(self, issues: List[CodeIssue], quality_score: float) -> str:
        """生成审查摘要"""
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        major_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)

        if critical_count > 0:
            return f"发现 {critical_count} 个严重问题，需要立即修复。代码质量评分：{quality_score}/100"
        elif major_count > 0:
            return f"发现 {major_count} 个重要问题，建议修复。代码质量评分：{quality_score}/100"
        elif quality_score >= 90:
            return f"代码质量优秀！评分：{quality_score}/100"
        elif quality_score >= 70:
            return f"代码质量良好，有一些可改进的地方。评分：{quality_score}/100"
        else:
            return f"代码有多个需要改进的地方，建议逐步优化。评分：{quality_score}/100"

    def review_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        审查文件

        Args:
            file_path: 文件路径
            language: 语言标识 (可选，自动从文件扩展名推断)
            config: 审查配置

        Returns:
            审查报告
        """
        logger.info(f"Reviewing file: {file_path}")

        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在：{file_path}"
            }

        # 自动推断语言
        if language is None:
            ext_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.jsx': 'javascript',
                '.tsx': 'typescript',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust',
                '.cpp': 'cpp',
                '.c': 'c',
                '.h': 'cpp',
            }
            ext = os.path.splitext(file_path)[1].lower()
            language = ext_map.get(ext, 'python')

        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"读取文件失败：{str(e)}"
            }

        return self.review_code(code, language, file_path, config)
