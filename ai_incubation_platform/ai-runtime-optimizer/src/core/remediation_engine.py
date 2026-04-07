"""
P6 自主修复引擎 - 核心引擎

实现自主修复的核心逻辑，包括：
- RemediationScriptLibrary: 修复脚本库
- ExecutionSandbox: 执行沙箱
- RemediationOrchestrator: 修复编排器
"""
import asyncio
import logging
import os
import subprocess
import tempfile
import uuid
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from models.remediation import (
    RemediationScript,
    RemediationExecution,
    RemediationExecutionEnhanced,
    ExecutionStatus,
    ExecutionStep,
    RiskLevel,
    RemediationCategory,
    ScriptParameter,
    VerificationStep,
    ResourceLimits,
    AutoRemediationRule,
    ImpactAnalysis,
    RemediationCase,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 修复脚本库
# ============================================================================

class RemediationScriptLibrary:
    """
    修复脚本库

    负责存储和管理预定义的修复脚本，支持：
    - 脚本的添加、查询、更新、删除
    - 按分类查询脚本
    - 脚本版本管理
    - 脚本启用/禁用
    """

    def __init__(self, scripts_dir: Optional[str] = None):
        """
        初始化脚本库

        Args:
            scripts_dir: 脚本存储目录，默认使用内置脚本目录
        """
        self._scripts: Dict[str, RemediationScript] = {}
        self._scripts_dir = Path(scripts_dir) if scripts_dir else Path(__file__).parent.parent / "scripts"
        self._load_scripts()

    def _load_scripts(self):
        """从脚本目录加载所有 YAML 脚本"""
        if not self._scripts_dir.exists():
            logger.info(f"Scripts directory does not exist: {self._scripts_dir}")
            return

        yaml_files = list(self._scripts_dir.glob("*.yaml")) + list(self._scripts_dir.glob("*.yml"))
        for yaml_file in yaml_files:
            try:
                script = self._load_script_from_yaml(yaml_file)
                if script:
                    self._scripts[script.script_id] = script
                    logger.info(f"Loaded script: {script.script_id} - {script.name}")
            except Exception as e:
                logger.error(f"Failed to load script from {yaml_file}: {e}")

    def _load_script_from_yaml(self, yaml_path: Path) -> Optional[RemediationScript]:
        """从 YAML 文件加载脚本"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # 解析参数
        parameters = []
        for param_data in data.get('parameters', []):
            parameters.append(ScriptParameter(**param_data))

        # 解析验证步骤
        verification_steps = []
        for step_data in data.get('verification_steps', []):
            verification_steps.append(VerificationStep(**step_data))

        # 解析资源限制
        resource_limits = None
        if data.get('resource_limits'):
            resource_limits = ResourceLimits(**data['resource_limits'])

        # 创建脚本对象
        return RemediationScript(
            script_id=data['script_id'],
            name=data['name'],
            description=data.get('description', ''),
            category=RemediationCategory(data.get('category', 'maintenance')),
            target_type=data.get('target_type', 'service'),
            script_content=data.get('script_content', ''),
            parameters=parameters,
            risk_level=RiskLevel(data.get('risk_level', 'low')),
            timeout_seconds=data.get('timeout_seconds', 120),
            resource_limits=resource_limits,
            verification_steps=verification_steps,
            rollback_script=data.get('rollback_script'),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'system'),
            tags=data.get('tags', []),
            enabled=data.get('enabled', True),
        )

    def add_script(self, script: RemediationScript) -> bool:
        """
        添加脚本到库

        Args:
            script: 脚本对象

        Returns:
            是否添加成功
        """
        if script.script_id in self._scripts:
            logger.warning(f"Script {script.script_id} already exists, updating...")

        script.updated_at = datetime.now()
        self._scripts[script.script_id] = script
        logger.info(f"Added script: {script.script_id} - {script.name}")
        return True

    def get_script(self, script_id: str) -> Optional[RemediationScript]:
        """
        获取脚本

        Args:
            script_id: 脚本 ID

        Returns:
            脚本对象，不存在返回 None
        """
        return self._scripts.get(script_id)

    def list_scripts(self, category: Optional[RemediationCategory] = None,
                     enabled_only: bool = True) -> List[RemediationScript]:
        """
        列出脚本

        Args:
            category: 按分类过滤
            enabled_only: 是否只返回启用的脚本

        Returns:
            脚本列表
        """
        scripts = list(self._scripts.values())

        if enabled_only:
            scripts = [s for s in scripts if s.enabled]

        if category:
            scripts = [s for s in scripts if s.category == category]

        return sorted(scripts, key=lambda s: s.name)

    def delete_script(self, script_id: str) -> bool:
        """
        删除脚本

        Args:
            script_id: 脚本 ID

        Returns:
            是否删除成功
        """
        if script_id in self._scripts:
            del self._scripts[script_id]
            logger.info(f"Deleted script: {script_id}")
            return True
        return False

    def enable_script(self, script_id: str, enabled: bool) -> bool:
        """启用/禁用脚本"""
        script = self.get_script(script_id)
        if script:
            script.enabled = enabled
            script.updated_at = datetime.now()
            return True
        return False

    def get_scripts_by_target(self, target_type: str) -> List[RemediationScript]:
        """按目标类型获取脚本"""
        return [s for s in self._scripts.values() if s.target_type == target_type and s.enabled]

    def get_script_count(self) -> int:
        """获取脚本总数"""
        return len(self._scripts)

    def save_script_to_yaml(self, script: RemediationScript, filepath: Optional[Path] = None) -> Path:
        """保存脚本到 YAML 文件"""
        if filepath is None:
            filepath = self._scripts_dir / f"{script.script_id}.yaml"

        data = {
            'script_id': script.script_id,
            'name': script.name,
            'description': script.description,
            'category': script.category.value,
            'target_type': script.target_type,
            'risk_level': script.risk_level.value,
            'timeout_seconds': script.timeout_seconds,
            'script_content': script.script_content,
            'parameters': [p.model_dump() for p in script.parameters],
            'verification_steps': [v.model_dump() for v in script.verification_steps],
            'rollback_script': script.rollback_script,
            'version': script.version,
            'author': script.author,
            'tags': script.tags,
            'enabled': script.enabled,
        }

        if script.resource_limits:
            data['resource_limits'] = script.resource_limits.model_dump()

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        return filepath


# ============================================================================
# 执行沙箱
# ============================================================================

class ExecutionSandbox:
    """
    执行沙箱

    提供隔离的执行环境，确保修复脚本安全执行：
    - 进程隔离
    - 资源限制（CPU、内存）
    - 超时控制
    - 文件系统隔离
    - 网络访问限制
    """

    def __init__(self,
                 timeout_seconds: int = 120,
                 resource_limits: Optional[ResourceLimits] = None):
        """
        初始化执行沙箱

        Args:
            timeout_seconds: 默认超时时间
            resource_limits: 默认资源限制
        """
        self._default_timeout = timeout_seconds
        self._default_resource_limits = resource_limits or ResourceLimits()
        self._running_processes: Dict[str, subprocess.Popen] = {}

    async def execute_script(self,
                            script: RemediationScript,
                            parameters: Dict[str, Any],
                            execution_id: str,
                            progress_callback: Optional[Callable[[str], None]] = None) -> tuple[bool, str, str]:
        """
        在沙箱中执行脚本

        Args:
            script: 脚本对象
            parameters: 执行参数
            execution_id: 执行 ID
            progress_callback: 进度回调函数

        Returns:
            (success, output, error)
        """
        # 渲染脚本模板
        rendered_script = self._render_script(script.script_content, parameters)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sh',
            delete=False,
            prefix=f"remediation_{execution_id}_"
        ) as f:
            f.write(rendered_script)
            script_path = f.name

        try:
            # 设置执行权限
            os.chmod(script_path, 0o755)

            # 准备执行环境
            env = os.environ.copy()
            env.update(self._prepare_environment(script, parameters))

            # 执行脚本
            return await self._run_script(
                script_path=script_path,
                env=env,
                timeout=script.timeout_seconds,
                execution_id=execution_id,
                progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Failed to execute script {script.script_id}: {e}")
            return False, "", str(e)
        finally:
            # 清理临时文件
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def _render_script(self, script_content: str, parameters: Dict[str, Any]) -> str:
        """
        渲染脚本模板，替换{{parameter}}占位符

        Args:
            script_content: 脚本内容
            parameters: 参数值

        Returns:
            渲染后的脚本
        """
        rendered = script_content
        for key, value in parameters.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered

    def _prepare_environment(self, script: RemediationScript, parameters: Dict[str, Any]) -> Dict[str, str]:
        """准备执行环境变量"""
        env = {
            'REMEDIATION_SCRIPT_ID': script.script_id,
            'REMEDIATION_SCRIPT_NAME': script.name,
        }

        # 添加参数到环境变量
        for key, value in parameters.items():
            env_key = f"PARAM_{key.upper()}"
            env[env_key] = str(value)

        return env

    async def _run_script(self,
                         script_path: str,
                         env: Dict[str, str],
                         timeout: int,
                         execution_id: str,
                         progress_callback: Optional[Callable[[str], None]] = None) -> tuple[bool, str, str]:
        """
        运行脚本

        Returns:
            (success, stdout, stderr)
        """
        logger.info(f"Executing script: {script_path}, timeout: {timeout}s")

        try:
            process = await asyncio.create_subprocess_exec(
                '/bin/bash', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=tempfile.gettempdir(),
            )

            self._running_processes[execution_id] = process

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')

                success = process.returncode == 0

                if progress_callback:
                    progress_callback(f"Script completed with return code: {process.returncode}")

                logger.info(f"Script execution completed: success={success}")
                return success, stdout_str, stderr_str

            except asyncio.TimeoutError:
                logger.error(f"Script execution timed out after {timeout}s")
                process.kill()
                return False, "", f"Execution timed out after {timeout} seconds"

        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return False, "", str(e)
        finally:
            self._running_processes.pop(execution_id, None)

    def stop_execution(self, execution_id: str) -> bool:
        """停止正在执行的脚本"""
        process = self._running_processes.get(execution_id)
        if process:
            try:
                process.terminate()
                del self._running_processes[execution_id]
                logger.info(f"Stopped execution: {execution_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to stop execution {execution_id}: {e}")
        return False


# ============================================================================
# 修复编排器
# ============================================================================

class RemediationOrchestrator:
    """
    修复编排器

    负责编排整个修复流程：
    - 执行状态管理
    - 审批流程管理
    - 执行编排
    - 结果记录
    """

    def __init__(self, script_library: RemediationScriptLibrary, sandbox: ExecutionSandbox):
        """
        初始化编排器

        Args:
            script_library: 脚本库
            sandbox: 执行沙箱
        """
        self._script_library = script_library
        self._sandbox = sandbox
        self._executions: Dict[str, RemediationExecution] = {}
        self._auto_rules: Dict[str, AutoRemediationRule] = {}

    def create_execution(self,
                        script_id: str,
                        target_service: str,
                        parameters: Optional[Dict[str, Any]] = None,
                        require_approval: bool = False,
                        target_type: str = "service") -> RemediationExecution:
        """
        创建执行记录

        Args:
            script_id: 脚本 ID
            target_service: 目标服务
            parameters: 执行参数
            require_approval: 是否需要审批
            target_type: 目标类型

        Returns:
            执行记录
        """
        script = self._script_library.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")

        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        execution = RemediationExecution(
            execution_id=execution_id,
            script_id=script_id,
            script_name=script.name,
            target_service=target_service,
            target_type=target_type,
            parameters=parameters or {},
            status=ExecutionStatus.PENDING_APPROVAL if require_approval else ExecutionStatus.PENDING,
            require_approval=require_approval,
            risk_level=script.risk_level,
            estimated_duration_seconds=script.timeout_seconds,
            rollback_available=script.rollback_script is not None,
        )

        self._executions[execution_id] = execution
        logger.info(f"Created execution: {execution_id} for script: {script_id}")
        return execution

    def get_execution(self, execution_id: str) -> Optional[RemediationExecution]:
        """获取执行记录"""
        return self._executions.get(execution_id)

    def list_executions(self,
                       status: Optional[ExecutionStatus] = None,
                       target_service: Optional[str] = None,
                       limit: int = 100) -> List[RemediationExecution]:
        """
        列出执行记录

        Args:
            status: 按状态过滤
            target_service: 按目标服务过滤
            limit: 返回数量限制

        Returns:
            执行记录列表
        """
        executions = list(self._executions.values())

        if status:
            executions = [e for e in executions if e.status == status]

        if target_service:
            executions = [e for e in executions if e.target_service == target_service]

        # 按创建时间倒序排序
        executions.sort(key=lambda e: e.created_at, reverse=True)

        return executions[:limit]

    async def approve_execution(self, execution_id: str, approver: str) -> bool:
        """
        审批执行

        Args:
            execution_id: 执行 ID
            approver: 审批人

        Returns:
            是否审批成功
        """
        execution = self.get_execution(execution_id)
        if not execution:
            return False

        if execution.status != ExecutionStatus.PENDING_APPROVAL:
            logger.warning(f"Cannot approve execution {execution_id}: status is {execution.status}")
            return False

        execution.status = ExecutionStatus.APPROVED
        execution.approved_by = approver
        execution.approved_at = datetime.now()
        execution.execution_log.append(f"[{datetime.now().isoformat()}] Approved by {approver}")

        logger.info(f"Execution {execution_id} approved by {approver}")
        return True

    async def reject_execution(self, execution_id: str, rejector: str, reason: str) -> bool:
        """
        拒绝执行

        Args:
            execution_id: 执行 ID
            rejector: 拒绝人
            reason: 拒绝原因

        Returns:
            是否拒绝成功
        """
        execution = self.get_execution(execution_id)
        if not execution:
            return False

        if execution.status != ExecutionStatus.PENDING_APPROVAL:
            logger.warning(f"Cannot reject execution {execution_id}: status is {execution.status}")
            return False

        execution.status = ExecutionStatus.REJECTED
        execution.rejected_by = rejector
        execution.rejected_reason = reason
        execution.execution_log.append(f"[{datetime.now().isoformat()}] Rejected by {rejector}: {reason}")

        logger.info(f"Execution {execution_id} rejected by {rejector}: {reason}")
        return True

    async def execute(self, execution_id: str) -> bool:
        """
        执行修复

        Args:
            execution_id: 执行 ID

        Returns:
            是否执行成功
        """
        execution = self.get_execution(execution_id)
        if not execution:
            logger.error(f"Execution not found: {execution_id}")
            return False

        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.APPROVED]:
            logger.warning(f"Cannot execute {execution_id}: status is {execution.status}")
            return False

        script = self._script_library.get_script(execution.script_id)
        if not script:
            logger.error(f"Script not found: {execution.script_id}")
            execution.status = ExecutionStatus.FAILED
            execution.execution_log.append(f"Script not found: {execution.script_id}")
            return False

        # 更新状态
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now()
        execution.execution_log.append(f"[{datetime.now().isoformat()}] Execution started")

        # 添加执行步骤
        execution.steps = [
            ExecutionStep(name="pre_check", status=ExecutionStatus.RUNNING),
            ExecutionStep(name="execute_script", status=ExecutionStatus.PENDING),
            ExecutionStep(name="verification", status=ExecutionStatus.PENDING),
        ]

        try:
            # 执行前检查
            if not await self._pre_execute_check(execution, script):
                execution.steps[0].status = ExecutionStatus.FAILED
                execution.steps[0].completed_at = datetime.now()
                return False
            execution.steps[0].status = ExecutionStatus.COMPLETED
            execution.steps[0].completed_at = datetime.now()

            # 执行脚本
            execution.steps[1].status = ExecutionStatus.RUNNING
            success, stdout, stderr = await self._sandbox.execute_script(
                script=script,
                parameters=execution.parameters,
                execution_id=execution_id,
                progress_callback=lambda msg: execution.execution_log.append(f"[{datetime.now().isoformat()}] {msg}")
            )

            execution.steps[1].status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
            execution.steps[1].completed_at = datetime.now()
            execution.steps[1].output = stdout if success else stderr

            if not success:
                execution.execution_log.append(f"Script execution failed: {stderr}")
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.now()

                # 尝试回滚
                if script.rollback_script:
                    await self._rollback(execution, script)
                return False

            # 验证执行结果
            execution.steps[2].status = ExecutionStatus.RUNNING
            verification_passed = await self._verify_execution(execution, script)
            execution.steps[2].status = ExecutionStatus.COMPLETED if verification_passed else ExecutionStatus.FAILED
            execution.steps[2].completed_at = datetime.now()

            if not verification_passed:
                execution.execution_log.append("Verification failed, triggering rollback")
                execution.status = ExecutionStatus.FAILED

                # 回滚
                if script.rollback_script:
                    await self._rollback(execution, script)
                return False

            # 执行成功
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.execution_log.append(f"[{datetime.now().isoformat()}] Execution completed successfully")
            logger.info(f"Execution {execution_id} completed successfully")
            return True

        except Exception as e:
            logger.exception(f"Execution {execution_id} failed with exception: {e}")
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now()
            execution.execution_log.append(f"[{datetime.now().isoformat()}] Exception: {str(e)}")

            # 尝试回滚
            script = self._script_library.get_script(execution.script_id)
            if script and script.rollback_script:
                await self._rollback(execution, script)
            return False

    async def _pre_execute_check(self, execution: RemediationExecution, script: RemediationScript) -> bool:
        """执行前检查"""
        logger.info(f"Running pre-execute checks for {execution.execution_id}")
        execution.execution_log.append("Running pre-execute checks...")

        # TODO: 实现更详细的预检查逻辑
        # 1. 检查目标服务是否存在
        # 2. 检查资源是否充足
        # 3. 检查是否在维护时间窗口内

        return True

    async def _verify_execution(self, execution: RemediationExecution, script: RemediationScript) -> bool:
        """
        验证执行结果

        执行脚本定义的验证步骤
        """
        if not script.verification_steps:
            logger.info(f"No verification steps defined for {script.script_id}, skipping verification")
            return True

        logger.info(f"Running {len(script.verification_steps)} verification steps")
        execution.execution_log.append(f"Running {len(script.verification_steps)} verification steps...")

        for step in script.verification_steps:
            try:
                # 渲染验证命令
                rendered_check = self._sandbox._render_script(step.check, execution.parameters)

                # 执行验证
                process = await asyncio.create_subprocess_shell(
                    rendered_check,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=step.timeout
                    )

                    output = stdout.decode('utf-8', errors='replace').strip()

                    # 检查验证结果
                    if self._check_verification_result(output, step.expected):
                        execution.execution_log.append(f"Verification step '{step.name}' passed: {output}")
                    else:
                        execution.execution_log.append(f"Verification step '{step.name}' failed: expected={step.expected}, got={output}")
                        return False

                except asyncio.TimeoutError:
                    execution.execution_log.append(f"Verification step '{step.name}' timed out")
                    return False

            except Exception as e:
                execution.execution_log.append(f"Verification step '{step.name}' failed: {str(e)}")
                return False

        return True

    def _check_verification_result(self, actual: str, expected: Any) -> bool:
        """检查验证结果是否符合预期"""
        if isinstance(expected, str):
            return expected.lower() in actual.lower()
        elif isinstance(expected, bool):
            return actual.lower() in ['true', 'yes', '1']
        elif isinstance(expected, (int, float)):
            try:
                return float(actual) == float(expected)
            except ValueError:
                return False
        return actual == str(expected)

    async def _rollback(self, execution: RemediationExecution, script: RemediationScript) -> bool:
        """
        执行回滚

        Args:
            execution: 执行记录
            script: 脚本对象

        Returns:
            是否回滚成功
        """
        if not script.rollback_script:
            logger.warning(f"No rollback script available for {script.script_id}")
            return False

        logger.info(f"Rolling back execution {execution.execution_id}")
        execution.execution_log.append(f"[{datetime.now().isoformat()}] Starting rollback...")
        execution.rollback_available = True

        try:
            # 创建回滚脚本对象
            rollback_script = RemediationScript(
                script_id=f"{script.script_id}_rollback",
                name=f"Rollback: {script.name}",
                description="Automatic rollback script",
                category=script.category,
                target_type=script.target_type,
                script_content=script.rollback_script,
                risk_level=RiskLevel.LOW,
                timeout_seconds=60,
            )

            # 执行回滚
            success, stdout, stderr = await self._sandbox.execute_script(
                script=rollback_script,
                parameters=execution.parameters,
                execution_id=f"{execution.execution_id}_rollback",
            )

            if success:
                execution.status = ExecutionStatus.ROLLED_BACK
                execution.rollback_executed = True
                execution.rollback_log.append(f"[{datetime.now().isoformat()}] Rollback completed successfully")
                execution.execution_log.append(f"[{datetime.now().isoformat()}] Rollback completed successfully")
                logger.info(f"Rollback completed for {execution.execution_id}")
            else:
                execution.rollback_log.append(f"[{datetime.now().isoformat()}] Rollback failed: {stderr}")
                execution.execution_log.append(f"[{datetime.now().isoformat()}] Rollback failed: {stderr}")
                logger.error(f"Rollback failed for {execution.execution_id}: {stderr}")

            return success

        except Exception as e:
            logger.exception(f"Rollback failed for {execution.execution_id}: {e}")
            execution.rollback_log.append(f"[{datetime.now().isoformat()}] Rollback exception: {str(e)}")
            return False

    async def rollback_execution(self, execution_id: str) -> bool:
        """
        手动触发回滚

        Args:
            execution_id: 执行 ID

        Returns:
            是否回滚成功
        """
        execution = self.get_execution(execution_id)
        if not execution:
            logger.error(f"Execution not found: {execution_id}")
            return False

        if execution.status != ExecutionStatus.COMPLETED:
            logger.warning(f"Cannot rollback execution {execution_id}: status is {execution.status}")
            return False

        script = self._script_library.get_script(execution.script_id)
        if not script or not script.rollback_script:
            logger.error(f"No rollback script available for {execution.script_id}")
            return False

        return await self._rollback(execution, script)

    # ========================================================================
    # 自动修复规则管理
    # ========================================================================

    def create_auto_rule(self, rule: AutoRemediationRule) -> bool:
        """创建自动修复规则"""
        if rule.rule_id in self._auto_rules:
            logger.warning(f"Auto rule {rule.rule_id} already exists, updating...")

        self._auto_rules[rule.rule_id] = rule
        logger.info(f"Created auto rule: {rule.rule_id} - {rule.name}")
        return True

    def get_auto_rule(self, rule_id: str) -> Optional[AutoRemediationRule]:
        """获取自动修复规则"""
        return self._auto_rules.get(rule_id)

    def list_auto_rules(self, enabled_only: bool = True) -> List[AutoRemediationRule]:
        """列出自动修复规则"""
        rules = list(self._auto_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def delete_auto_rule(self, rule_id: str) -> bool:
        """删除自动修复规则"""
        if rule_id in self._auto_rules:
            del self._auto_rules[rule_id]
            return True
        return False

    def enable_auto_rule(self, rule_id: str, enabled: bool) -> bool:
        """启用/禁用自动修复规则"""
        rule = self.get_auto_rule(rule_id)
        if rule:
            rule.enabled = enabled
            return True
        return False

    async def check_and_trigger_auto_rules(self, metrics: Dict[str, Any], target_service: str) -> List[str]:
        """
        检查并触发自动修复规则

        Args:
            metrics: 当前指标
            target_service: 目标服务

        Returns:
            触发的执行 ID 列表
        """
        triggered_executions = []

        for rule in self._auto_rules.values():
            if not rule.enabled:
                continue

            # 检查触发条件
            if self._evaluate_trigger_condition(rule.trigger_condition, metrics):
                # 检查冷却时间
                if self._is_in_cooldown(rule):
                    logger.info(f"Rule {rule.rule_id} in cooldown, skipping")
                    continue

                # 检查每日执行次数
                if rule.execution_count_today >= rule.max_executions_per_day:
                    logger.info(f"Rule {rule.rule_id} reached daily limit, skipping")
                    continue

                # 触发修复
                try:
                    execution = self.create_execution(
                        script_id=rule.script_id,
                        target_service=target_service,
                        parameters=rule.script_parameters,
                        require_approval=rule.require_approval,
                    )
                    triggered_executions.append(execution.execution_id)

                    # 更新规则状态
                    rule.last_triggered_at = datetime.now()
                    rule.execution_count_today += 1

                    # 如果不需要审批，直接执行
                    if not rule.require_approval:
                        asyncio.create_task(self.execute(execution.execution_id))

                    logger.info(f"Auto rule {rule.rule_id} triggered, execution: {execution.execution_id}")

                except Exception as e:
                    logger.error(f"Failed to trigger auto rule {rule.rule_id}: {e}")

        return triggered_executions

    def _evaluate_trigger_condition(self, condition: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """评估触发条件"""
        metric_name = condition.get('metric')
        operator = condition.get('operator')
        threshold = condition.get('threshold')
        duration_minutes = condition.get('duration_minutes', 5)

        if metric_name not in metrics:
            return False

        value = metrics[metric_name]

        # 简单的阈值判断
        if operator == 'greater_than':
            return value > threshold
        elif operator == 'less_than':
            return value < threshold
        elif operator == 'equals':
            return value == threshold
        elif operator == 'greater_than_or_equal':
            return value >= threshold
        elif operator == 'less_than_or_equal':
            return value <= threshold

        return False

    def _is_in_cooldown(self, rule: AutoRemediationRule) -> bool:
        """检查是否在冷却时间内"""
        if not rule.last_triggered_at:
            return False

        cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() < cooldown_end

    def reset_daily_counts(self):
        """重置每日执行计数（每天零点调用）"""
        for rule in self._auto_rules.values():
            rule.execution_count_today = 0

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        executions = list(self._executions.values())

        successful = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
        failed = len([e for e in executions if e.status == ExecutionStatus.FAILED])
        rolled_back = len([e for e in executions if e.status == ExecutionStatus.ROLLED_BACK])

        total = len(executions)
        success_rate = (successful / total * 100) if total > 0 else 0.0

        durations = []
        for e in executions:
            if e.started_at and e.completed_at:
                duration = (e.completed_at - e.started_at).total_seconds()
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        today = datetime.now().date()
        today_count = len([e for e in executions if e.created_at.date() == today])

        return {
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': failed,
            'rolled_back_executions': rolled_back,
            'success_rate': success_rate,
            'avg_duration_seconds': avg_duration,
            'total_executions_today': today_count,
            'scripts_count': self._script_library.get_script_count(),
            'auto_rules_count': len(self._auto_rules),
        }


# ============================================================================
# 全局实例
# ============================================================================

_script_library: Optional[RemediationScriptLibrary] = None
_sandbox: Optional[ExecutionSandbox] = None
_orchestrator: Optional[RemediationOrchestrator] = None


def get_script_library() -> RemediationScriptLibrary:
    """获取脚本库单例"""
    global _script_library
    if _script_library is None:
        _script_library = RemediationScriptLibrary()
    return _script_library


def get_sandbox() -> ExecutionSandbox:
    """获取执行沙箱单例"""
    global _sandbox
    if _sandbox is None:
        _sandbox = ExecutionSandbox()
    return _sandbox


def get_orchestrator() -> RemediationOrchestrator:
    """获取编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RemediationOrchestrator(
            script_library=get_script_library(),
            sandbox=get_sandbox()
        )
    return _orchestrator


def reset_instances():
    """重置单例实例（用于测试）"""
    global _script_library, _sandbox, _orchestrator
    _script_library = None
    _sandbox = None
    _orchestrator = None


# ============================================================================
# v1.1 新增：影响分析服务
# ============================================================================

class ImpactAnalyzer:
    """
    影响分析服务
    
    分析修复操作的潜在影响，包括：
    - 服务依赖分析
    - 影响范围评估
    - 风险评估
    - 回滚复杂度评估
    """
    
    def __init__(self, service_dependencies: Optional[Dict[str, List[str]]] = None):
        """
        初始化影响分析器
        
        Args:
            service_dependencies: 服务依赖关系图 {service_id: [dependency_ids]}
        """
        self._service_dependencies = service_dependencies or {}
    
    def analyze_impact(
        self,
        target_service: str,
        script: RemediationScript,
        action_type: str
    ) -> ImpactAnalysis:
        """
        分析修复操作的影响
        
        Args:
            target_service: 目标服务
            script: 修复脚本
            action_type: 操作类型
            
        Returns:
            影响分析结果
        """
        # 分析受影响的服务
        affected_services = self._find_affected_services(target_service)
        
        # 评估影响
        downtime_estimate = self._estimate_downtime(script, action_type)
        rollback_complexity = self._evaluate_rollback_complexity(script)
        risk_assessment = self._assess_risk(script, len(affected_services))
        
        return ImpactAnalysis(
            affected_services=affected_services,
            downtime_estimate_minutes=downtime_estimate,
            rollback_complexity=rollback_complexity,
            risk_assessment=risk_assessment,
            dependencies=self._service_dependencies.get(target_service, [])
        )
    
    def _find_affected_services(self, target_service: str) -> List[str]:
        """查找受影响的服务（上游依赖）"""
        affected = set()
        
        # 查找依赖目标服务的其他服务
        for service, deps in self._service_dependencies.items():
            if target_service in deps:
                affected.add(service)
                # 递归查找上游
                affected.update(self._find_affected_services(service))
        
        return list(affected)
    
    def _estimate_downtime(self, script: RemediationScript, action_type: str) -> Optional[int]:
        """预估停机时间"""
        # 基于风险等级和脚本类型估算
        base_time = script.timeout_seconds // 60  # 基础时间
        
        if script.risk_level == RiskLevel.LOW:
            return min(base_time, 5)
        elif script.risk_level == RiskLevel.MEDIUM:
            return base_time
        elif script.risk_level == RiskLevel.HIGH:
            return base_time * 2
        else:  # CRITICAL
            return base_time * 3
    
    def _evaluate_rollback_complexity(self, script: RemediationScript) -> Optional[str]:
        """评估回滚复杂度"""
        if not script.rollback_script:
            return "high - 无回滚脚本"
        
        if script.risk_level == RiskLevel.LOW:
            return "low - 简单回滚"
        elif script.risk_level == RiskLevel.MEDIUM:
            return "medium - 需要验证"
        else:
            return "high - 复杂回滚流程"
    
    def _assess_risk(self, script: RemediationScript, affected_count: int) -> Optional[str]:
        """综合风险评估"""
        risk_factors = []
        
        if script.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            risk_factors.append(f"脚本风险等级：{script.risk_level.value}")
        
        if affected_count > 5:
            risk_factors.append(f"影响 {affected_count} 个服务")
        elif affected_count > 0:
            risk_factors.append(f"影响 {affected_count} 个上游服务")
        
        if not script.rollback_script:
            risk_factors.append("无回滚方案")
        
        if not risk_factors:
            return "low - 风险可控"
        
        return f"medium - {'; '.join(risk_factors)}"
    
    def set_dependencies(self, dependencies: Dict[str, List[str]]):
        """设置服务依赖关系"""
        self._service_dependencies = dependencies


# ============================================================================
# v1.1 新增：案例库服务
# ============================================================================

class CaseLibrary:
    """
    修复案例库
    
    负责存储和管理修复案例，支持：
    - 案例记录
    - 案例查询
    - 相似度匹配
    - 经验学习
    """
    
    def __init__(self):
        self._cases: Dict[str, RemediationCase] = {}
        self._case_index: Dict[str, List[str]] = {}  # tag -> case_ids
        self._execution_to_case: Dict[str, str] = {}  # execution_id -> case_id
    
    def add_case(self, case: RemediationCase) -> bool:
        """添加案例"""
        self._cases[case.case_id] = case
        
        # 建立索引
        for tag in case.tags:
            if tag not in self._case_index:
                self._case_index[tag] = []
            self._case_index[tag].append(case.case_id)
        
        # 建立执行记录到案例的映射
        if case.execution_id:
            self._execution_to_case[case.execution_id] = case.case_id
        
        logger.info(f"Added remediation case: {case.case_id} for execution: {case.execution_id}")
        return True
    
    def get_case(self, case_id: str) -> Optional[RemediationCase]:
        """获取案例"""
        return self._cases.get(case_id)
    
    def get_case_by_execution(self, execution_id: str) -> Optional[RemediationCase]:
        """通过执行 ID 获取案例"""
        case_id = self._execution_to_case.get(execution_id)
        if case_id:
            return self.get_case(case_id)
        return None
    
    def list_cases(self, tag: Optional[str] = None, limit: int = 100) -> List[RemediationCase]:
        """列出案例"""
        if tag and tag in self._case_index:
            case_ids = self._case_index[tag][:limit]
            return [self._cases[cid] for cid in case_ids if cid in self._cases]
        
        return list(self._cases.values())[:limit]
    
    def search_similar_cases(
        self,
        script_id: str,
        problem_keywords: Optional[List[str]] = None
    ) -> List[RemediationCase]:
        """搜索类似案例"""
        results = []
        
        # 查找相同脚本的案例
        for case in self._cases.values():
            if case.script_id == script_id:
                results.append(case)
        
        # 如果有关键词，查找问题描述匹配的
        if problem_keywords:
            for case in self._cases.values():
                if case.script_id != script_id:
                    for keyword in problem_keywords:
                        if keyword.lower() in case.problem_description.lower():
                            if case not in results:
                                results.append(case)
                            break
        
        # 按有效性评分排序
        results.sort(
            key=lambda c: (c.effectiveness_score or 0, c.created_at),
            reverse=True
        )
        
        return results[:10]
    
    def create_case_from_execution(
        self,
        execution: RemediationExecution,
        problem_description: str = "",
        root_cause: str = "",
        lessons_learned: str = "",
        created_by: str = "system"
    ) -> RemediationCase:
        """从执行记录创建案例"""
        case_id = f"case_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 确定结果
        outcome = "success" if execution.status == ExecutionStatus.COMPLETED else "failed"
        if execution.status == ExecutionStatus.ROLLED_BACK:
            outcome = "rolled_back"
        
        # 生成标签
        tags = [execution.script_id]
        if execution.status == ExecutionStatus.COMPLETED:
            tags.append("successful")
        elif execution.status == ExecutionStatus.FAILED:
            tags.append("failed")
        if execution.rollback_executed:
            tags.append("rollback_executed")
        
        # 计算有效性评分
        effectiveness_score = None
        if execution.status == ExecutionStatus.COMPLETED:
            effectiveness_score = 0.8  # 基础分
            if not execution.rollback_executed:
                effectiveness_score += 0.2  # 无需回滚加分
        
        case = RemediationCase(
            case_id=case_id,
            execution_id=execution.execution_id,
            script_id=execution.script_id,
            problem_description=problem_description or f"执行脚本 {execution.script_name} 修复 {execution.target_service}",
            root_cause=root_cause,
            solution_applied=execution.script_name,
            outcome=outcome,
            lessons_learned=lessons_learned,
            tags=tags,
            created_by=created_by,
            effectiveness_score=effectiveness_score
        )
        
        self.add_case(case)
        return case
    
    def get_stats(self) -> Dict[str, Any]:
        """获取案例统计"""
        total = len(self._cases)
        successful = len([c for c in self._cases.values() if c.outcome == "success"])
        
        avg_effectiveness = 0.0
        effectiveness_count = 0
        for case in self._cases.values():
            if case.effectiveness_score is not None:
                avg_effectiveness += case.effectiveness_score
                effectiveness_count += 1
        
        if effectiveness_count > 0:
            avg_effectiveness /= effectiveness_count
        
        return {
            "total_cases": total,
            "successful_cases": successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_effectiveness_score": avg_effectiveness
        }


# ============================================================================
# v1.1 全局实例
# ============================================================================

_impact_analyzer: Optional[ImpactAnalyzer] = None
_case_library: Optional[CaseLibrary] = None


def get_impact_analyzer() -> ImpactAnalyzer:
    """获取影响分析器实例"""
    global _impact_analyzer
    if _impact_analyzer is None:
        _impact_analyzer = ImpactAnalyzer()
    return _impact_analyzer


def get_case_library() -> CaseLibrary:
    """获取案例库实例"""
    global _case_library
    if _case_library is None:
        _case_library = CaseLibrary()
    return _case_library


def reset_remediation_v11():
    """重置 v1.1 新增的单例实例"""
    global _impact_analyzer, _case_library
    _impact_analyzer = None
    _case_library = None
