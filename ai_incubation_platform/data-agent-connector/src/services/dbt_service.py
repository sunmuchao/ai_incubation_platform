"""
dbt 集成服务

实现:
1. dbt 项目解析器 - 解析 dbt 项目配置和模型
2. dbt Cloud API 集成 - 与 dbt Cloud 服务交互
3. 血缘关系追踪 - 基于 dbt 模型构建血缘图
4. dbt 任务执行 - 触发 dbt 运行和测试
"""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import aiohttp
import yaml

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index
from config.database import db_manager
from utils.logger import logger
from config.settings import settings


class DbtArtifactType(Enum):
    """dbt 工件类型"""
    MODEL = "model"
    SOURCE = "source"
    SEED = "seed"
    SNAPSHOT = "snapshot"
    TEST = "test"
    ANALYSIS = "analysis"


class JobRunStatus(Enum):
    """任务运行状态"""
    QUEUED = "queued"
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DbtModel:
    """dbt 模型"""
    name: str
    unique_id: str
    package_name: str
    original_file_path: str
    root_path: str
    path: str
    language: str = "sql"
    raw_code: str = ""
    compiled_code: str = ""
    depends_on: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    description: str = ""
    columns: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    database: Optional[str] = None
    schema_name: Optional[str] = None
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "unique_id": self.unique_id,
            "package_name": self.package_name,
            "original_file_path": self.original_file_path,
            "path": self.path,
            "language": self.language,
            "depends_on": self.depends_on,
            "config": self.config,
            "tags": self.tags,
            "description": self.description,
            "columns": self.columns,
            "meta": self.meta,
            "database": self.database,
            "schema": self.schema_name,
            "alias": self.alias
        }


@dataclass
class DbtSource:
    """dbt 源"""
    name: str
    unique_id: str
    source_name: str
    loader: str
    description: str = ""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "unique_id": self.unique_id,
            "source_name": self.source_name,
            "loader": self.loader,
            "description": self.description,
            "tables": self.tables,
            "tags": self.tags,
            "meta": self.meta
        }


@dataclass
class DbtTest:
    """dbt 测试"""
    name: str
    unique_id: str
    test_type: str  # generic, singular
    test_metadata: Dict[str, Any]
    depends_on: List[str]
    config: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "unique_id": self.unique_id,
            "test_type": self.test_type,
            "test_metadata": self.test_metadata,
            "depends_on": self.depends_on,
            "config": self.config,
            "tags": self.tags,
            "description": self.description
        }


@dataclass
class DbtProject:
    """dbt 项目"""
    name: str
    version: str
    project_root: str
    profile_name: Optional[str] = None
    models: Dict[str, DbtModel] = field(default_factory=dict)
    sources: Dict[str, DbtSource] = field(default_factory=dict)
    tests: Dict[str, DbtTest] = field(default_factory=dict)
    seeds: Dict[str, Any] = field(default_factory=dict)
    snapshots: Dict[str, Any] = field(default_factory=dict)
    macros: Dict[str, Any] = field(default_factory=dict)
    exposures: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "project_root": self.project_root,
            "profile_name": self.profile_name,
            "models": {k: v.to_dict() for k, v in self.models.items()},
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "tests": {k: v.to_dict() for k, v in self.tests.items()}
        }


@dataclass
class DbtCloudJob:
    """dbt Cloud 任务"""
    id: int
    account_id: int
    project_id: int
    environment_id: int
    name: str
    dbt_version: str
    schedule: Dict[str, Any]
    settings: Dict[str, Any]
    state: int  # 1=active, 2=deprecated
    deferrable: bool = False
    generate_docs: bool = False
    run_generate_sources: bool = False
    execute_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "name": self.name,
            "dbt_version": self.dbt_version,
            "schedule": self.schedule,
            "state": "active" if self.state == 1 else "deprecated",
            "execute_steps": self.execute_steps
        }


@dataclass
class DbtCloudRun:
    """dbt Cloud 运行"""
    id: int
    account_id: int
    project_id: int
    job_id: int
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    triggered_by: str
    git_branch: Optional[str] = None
    git_sha: Optional[str] = None
    schema_override: Optional[str] = None
    dbt_version: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "project_id": self.project_id,
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "triggered_by": self.triggered_by,
            "error": self.error
        }


class DbtProjectParser:
    """dbt 项目解析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._project: Optional[DbtProject] = None

    async def parse(self) -> DbtProject:
        """解析 dbt 项目"""
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")

        # 解析 dbt_project.yml
        project_config = await self._parse_project_yml()

        self._project = DbtProject(
            name=project_config.get("name", "unknown"),
            version=project_config.get("version", "1.0.0"),
            project_root=str(self.project_root),
            profile_name=project_config.get("profile")
        )

        # 解析模型
        await self._parse_models()

        # 解析源
        await self._parse_sources()

        # 解析测试
        await self._parse_tests()

        # 解析 manifest.json (如果存在)
        await self._parse_manifest()

        return self._project

    async def _parse_project_yml(self) -> Dict[str, Any]:
        """解析 dbt_project.yml"""
        project_file = self.project_root / "dbt_project.yml"
        if not project_file.exists():
            raise ValueError(f"dbt_project.yml not found in {self.project_root}")

        with open(project_file, "r") as f:
            return yaml.safe_load(f)

    async def _parse_models(self) -> None:
        """解析模型文件"""
        models_dir = self.project_root / "models"
        if not models_dir.exists():
            return

        for sql_file in models_dir.rglob("*.sql"):
            model = await self._parse_model_file(sql_file)
            if model:
                self._project.models[model.unique_id] = model

        # 也解析 Python 模型
        for py_file in models_dir.rglob("*.py"):
            model = await self._parse_python_model_file(py_file)
            if model:
                self._project.models[model.unique_id] = model

    async def _parse_model_file(self, file_path: Path) -> Optional[DbtModel]:
        """解析模型 SQL 文件"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            content = file_path.read_text()

            # 解析 Jinja2 注释和配置
            config_block = self._extract_config_block(content)
            description = self._extract_description(content)

            # 生成唯一 ID
            name = file_path.stem
            unique_id = f"model.{self._project.name}.{name}"

            # 解析依赖
            depends_on = self._extract_dependencies(content)

            return DbtModel(
                name=name,
                unique_id=unique_id,
                package_name=self._project.name,
                original_file_path=str(relative_path),
                root_path=str(self.project_root),
                path=str(relative_path),
                language="sql",
                raw_code=content,
                config=config_block,
                description=description,
                depends_on=depends_on
            )
        except Exception as e:
            logger.error(f"Failed to parse model file {file_path}: {e}")
            return None

    async def _parse_python_model_file(self, file_path: Path) -> Optional[DbtModel]:
        """解析 Python 模型文件"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            content = file_path.read_text()

            name = file_path.stem
            unique_id = f"model.{self._project.name}.{name}"

            return DbtModel(
                name=name,
                unique_id=unique_id,
                package_name=self._project.name,
                original_file_path=str(relative_path),
                root_path=str(self.project_root),
                path=str(relative_path),
                language="python",
                raw_code=content
            )
        except Exception as e:
            logger.error(f"Failed to parse Python model file {file_path}: {e}")
            return None

    def _extract_config_block(self, content: str) -> Dict[str, Any]:
        """提取配置块"""
        config_match = re.search(r'\{\{\s*config\s*\(\s*(.*?)\s*\)\s*\}\}', content, re.DOTALL)
        if not config_match:
            return {}

        config_str = config_match.group(1)
        config = {}

        # 解析简单的键值对
        for match in re.finditer(r'(\w+)\s*=\s*([\'"]?)([^\'",\)]+)\2', config_str):
            key, _, value = match.groups()
            # 尝试转换类型
            if value.lower() == 'true':
                config[key] = True
            elif value.lower() == 'false':
                config[key] = False
            elif value.isdigit():
                config[key] = int(value)
            else:
                config[key] = value

        return config

    def _extract_description(self, content: str) -> str:
        """提取描述"""
        # 提取文件开头的注释作为描述
        match = re.match(r'^\s*--\s*(.*?)\n', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_dependencies(self, content: str) -> List[str]:
        """提取依赖"""
        dependencies = []

        # 查找 ref() 调用
        for match in re.finditer(r'\{\{\s*ref\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\}\}', content):
            dependencies.append(f"model.{self._project.name}.{match.group(1)}")

        # 查找 source() 调用
        for match in re.finditer(r'\{\{\s*source\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)\s*\}\}', content):
            dependencies.append(f"source.{self._project.name}.{match.group(1)}.{match.group(2)}")

        return dependencies

    async def _parse_sources(self) -> None:
        """解析源定义"""
        # 查找 schema.yml 或 sources.yml 文件
        models_dir = self.project_root / "models"

        for schema_file in models_dir.rglob("*.yml"):
            await self._parse_schema_file(schema_file)

    async def _parse_schema_file(self, file_path: Path) -> None:
        """解析 schema.yml 文件"""
        try:
            content = yaml.safe_load(file_path.read_text())
            if not content:
                return

            sources = content.get("sources", [])
            for source in sources:
                source_name = source.get("name", "")
                unique_id = f"source.{self._project.name}.{source_name}"

                dbt_source = DbtSource(
                    name=source_name,
                    unique_id=unique_id,
                    source_name=source_name,
                    loader=source.get("loader", ""),
                    description=source.get("description", ""),
                    tables=source.get("tables", []),
                    tags=source.get("tags", []),
                    meta=source.get("meta", {})
                )

                self._project.sources[unique_id] = dbt_source

        except Exception as e:
            logger.error(f"Failed to parse schema file {file_path}: {e}")

    async def _parse_tests(self) -> None:
        """解析测试定义"""
        # 从 schema.yml 中解析 generic tests
        models_dir = self.project_root / "models"

        for schema_file in models_dir.rglob("*.yml"):
            try:
                content = yaml.safe_load(schema_file.read_text())
                if not content:
                    continue

                models = content.get("models", [])
                for model in models:
                    model_name = model.get("name", "")
                    columns = model.get("columns", [])

                    for column in columns:
                        tests = column.get("tests", [])
                        for test in tests:
                            test_name = f"{model_name}_{column.get('name')}_{test if isinstance(test, str) else list(test.keys())[0]}"
                            unique_id = f"test.{self._project.name}.{test_name}"

                            dbt_test = DbtTest(
                                name=test_name,
                                unique_id=unique_id,
                                test_type="generic",
                                test_metadata={"column": column.get("name"), "test": test},
                                depends_on=[f"model.{self._project.name}.{model_name}"]
                            )

                            self._project.tests[unique_id] = dbt_test

            except Exception as e:
                logger.error(f"Failed to parse tests from {schema_file}: {e}")

    async def _parse_manifest(self) -> None:
        """解析 manifest.json (如果存在)"""
        target_dir = self.project_root / "target"
        manifest_file = target_dir / "manifest.json"

        if not manifest_file.exists():
            return

        try:
            manifest = json.loads(manifest_file.read_text())

            # 从 manifest 更新模型信息
            nodes = manifest.get("nodes", {})
            for node_id, node_data in nodes.items():
                if node_id.startswith("model."):
                    model = self._project.models.get(node_id)
                    if model:
                        # 更新 compiled code
                        model.compiled_code = node_data.get("compiled_sql", "")
                        model.database = node_data.get("database")
                        model.schema_name = node_data.get("schema")
                        model.alias = node_data.get("alias")

                        # 更新列信息
                        columns = node_data.get("columns", {})
                        model.columns = {
                            col_name: {
                                "name": col_data.get("name"),
                                "description": col_data.get("description"),
                                "type": col_data.get("type")
                            }
                            for col_name, col_data in columns.items()
                        }

            logger.info(f"Updated project info from manifest.json")

        except Exception as e:
            logger.error(f"Failed to parse manifest.json: {e}")


class DbtCloudClient:
    """dbt Cloud API 客户端"""

    BASE_URL = "https://cloud.getdbt.com/api/v2"

    def __init__(self, api_key: str, account_id: int):
        self.api_key = api_key
        self.account_id = account_id
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session

    async def close(self) -> None:
        """关闭会话"""
        if self._session:
            await self._session.close()
            self._session = None

    async def get_projects(self) -> List[Dict[str, Any]]:
        """获取项目列表"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/projects/"

        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                raise Exception(f"Failed to get projects: {response.status}")

    async def get_jobs(self, project_id: int) -> List[DbtCloudJob]:
        """获取任务列表"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/jobs/"
        params = {"project_id": project_id}

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                jobs_data = data.get("data", [])
                return [DbtCloudJob(**job) for job in jobs_data]
            else:
                raise Exception(f"Failed to get jobs: {response.status}")

    async def trigger_job(self, job_id: int, cause: str = "API trigger") -> DbtCloudRun:
        """触发任务运行"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/jobs/{job_id}/run/"

        payload = {
            "cause": cause,
            "defer": False,
            "generate_docs": False,
            "schema": None
        }

        async with session.post(url, json=payload) as response:
            if response.status == 201:
                data = await response.json()
                run_data = data.get("data", {})
                return DbtCloudRun(
                    id=run_data.get("id"),
                    account_id=run_data.get("account_id"),
                    project_id=run_data.get("project_id"),
                    job_id=run_data.get("job_id"),
                    status=run_data.get("status", {}).get("humanized", "queued"),
                    created_at=datetime.fromisoformat(run_data.get("created_at").replace("Z", "+00:00")),
                    finished_at=None,
                    triggered_by=cause
                )
            else:
                raise Exception(f"Failed to trigger job: {response.status}")

    async def get_run(self, run_id: int) -> DbtCloudRun:
        """获取运行状态"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/runs/{run_id}/"

        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                run_data = data.get("data", {})
                status_obj = run_data.get("status", {})

                finished_at = run_data.get("finished_at")
                if finished_at:
                    finished_at = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))

                return DbtCloudRun(
                    id=run_data.get("id"),
                    account_id=run_data.get("account_id"),
                    project_id=run_data.get("project_id"),
                    job_id=run_data.get("job_id"),
                    status=status_obj.get("humanized", "unknown"),
                    created_at=datetime.fromisoformat(run_data.get("created_at").replace("Z", "+00:00")),
                    finished_at=finished_at,
                    triggered_by=run_data.get("triggered_by", ""),
                    error=status_obj.get("message") if status_obj.get("is_failed") else None
                )
            else:
                raise Exception(f"Failed to get run: {response.status}")

    async def get_run_artifacts(self, run_id: int) -> Dict[str, Any]:
        """获取运行产物"""
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/runs/{run_id}/artifacts/"

        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get run artifacts: {response.status}")

    async def get_manifest(self, project_id: int) -> Dict[str, Any]:
        """获取项目 manifest"""
        # 需要先获取最新的成功运行
        session = await self._get_session()
        url = f"{self.BASE_URL}/accounts/{self.account_id}/projects/{project_id}/runs/"
        params = {"status": 10}  # success

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                runs = data.get("data", [])
                if runs:
                    latest_run_id = runs[0].get("id")
                    # 获取 manifest.json
                    artifact_url = f"{self.BASE_URL}/accounts/{self.account_id}/runs/{latest_run_id}/artifacts/manifest.json"
                    async with session.get(artifact_url) as artifact_response:
                        if artifact_response.status == 200:
                            return await artifact_response.json()

        return {}


class DbtLineageBuilder:
    """dbt 血缘关系构建器"""

    def __init__(self, project: DbtProject):
        self.project = project
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []

    def build_lineage(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """构建血缘关系"""
        # 添加模型节点
        for model_id, model in self.project.models.items():
            self._nodes[model_id] = {
                "id": model_id,
                "name": model.name,
                "type": DbtArtifactType.MODEL.value,
                "description": model.description,
                "config": model.config,
                "columns": model.columns
            }

        # 添加源节点
        for source_id, source in self.project.sources.items():
            self._nodes[source_id] = {
                "id": source_id,
                "name": source.name,
                "type": DbtArtifactType.SOURCE.value,
                "description": source.description
            }

        # 添加测试节点
        for test_id, test in self.project.tests.items():
            self._nodes[test_id] = {
                "id": test_id,
                "name": test.name,
                "type": DbtArtifactType.TEST.value,
                "description": test.description
            }

        # 构建边 (依赖关系)
        for model_id, model in self.project.models.items():
            for dep in model.depends_on:
                self._edges.append({
                    "source_id": dep,
                    "target_id": model_id,
                    "type": "depends_on"
                })

        # 测试依赖于模型
        for test_id, test in self.project.tests.items():
            for dep in test.depends_on:
                self._edges.append({
                    "source_id": dep,
                    "target_id": test_id,
                    "type": "tested_by"
                })

        return self._nodes, self._edges

    def get_downstream(self, node_id: str) -> Set[str]:
        """获取下游节点"""
        downstream = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            for edge in self._edges:
                if edge["source_id"] == current and edge["target_id"] not in downstream:
                    downstream.add(edge["target_id"])
                    queue.append(edge["target_id"])

        return downstream

    def get_upstream(self, node_id: str) -> Set[str]:
        """获取上游节点"""
        upstream = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            for edge in self._edges:
                if edge["target_id"] == current and edge["source_id"] not in upstream:
                    upstream.add(edge["source_id"])
                    queue.append(edge["source_id"])

        return upstream

    def get_lineage_graph(self, node_id: str) -> Dict[str, Any]:
        """获取单个节点的血缘图"""
        upstream = self.get_upstream(node_id)
        downstream = self.get_downstream(node_id)

        relevant_nodes = {node_id} | upstream | downstream

        nodes = {k: v for k, v in self._nodes.items() if k in relevant_nodes}
        edges = [e for e in self._edges if e["source_id"] in relevant_nodes and e["target_id"] in relevant_nodes]

        return {
            "center_node": node_id,
            "nodes": nodes,
            "edges": edges,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream)
        }


class DbtIntegrationService:
    """dbt 集成服务"""

    def __init__(self):
        self._projects: Dict[str, DbtProject] = {}
        self._cloud_clients: Dict[str, DbtCloudClient] = {}
        self._lineage_builders: Dict[str, DbtLineageBuilder] = {}
        self._runs: Dict[str, DbtCloudRun] = {}

    async def register_project(self, project_root: str, project_name: Optional[str] = None) -> str:
        """注册 dbt 项目"""
        parser = DbtProjectParser(project_root)
        project = await parser.parse()

        name = project_name or project.name
        self._projects[name] = project

        # 构建血缘
        lineage_builder = DbtLineageBuilder(project)
        nodes, edges = lineage_builder.build_lineage()
        self._lineage_builders[name] = lineage_builder

        # 保存到数据库
        await self._save_project(name, project)

        logger.info(f"Registered dbt project: {name} with {len(project.models)} models")
        return name

    async def register_cloud_project(
        self,
        project_name: str,
        api_key: str,
        account_id: int,
        dbt_project_id: int
    ) -> str:
        """注册 dbt Cloud 项目"""
        client = DbtCloudClient(api_key, account_id)
        self._cloud_clients[project_name] = client

        # 获取项目 manifest
        manifest = await client.get_manifest(dbt_project_id)

        if manifest:
            # 从 manifest 创建项目
            project = await self._parse_manifest(manifest, project_name)
            self._projects[project_name] = project

            lineage_builder = DbtLineageBuilder(project)
            self._lineage_builders[project_name] = lineage_builder

        logger.info(f"Registered dbt Cloud project: {project_name}")
        return project_name

    async def _parse_manifest(self, manifest: Dict[str, Any], project_name: str) -> DbtProject:
        """从 manifest 解析项目"""
        project = DbtProject(
            name=project_name,
            version="1.0.0",
            project_root=""
        )

        nodes = manifest.get("nodes", {})
        for node_id, node_data in nodes.items():
            if node_id.startswith("model."):
                model = DbtModel(
                    name=node_data.get("name", ""),
                    unique_id=node_id,
                    package_name=node_data.get("package_name", ""),
                    original_file_path=node_data.get("original_file_path", ""),
                    root_path="",
                    path=node_data.get("path", ""),
                    language=node_data.get("language", "sql"),
                    raw_code=node_data.get("raw_sql", ""),
                    compiled_code=node_data.get("compiled_sql", ""),
                    depends_on=node_data.get("depends_on", {}).get("nodes", []),
                    config=node_data.get("config", {}),
                    tags=node_data.get("tags", []),
                    description=node_data.get("description", ""),
                    columns=node_data.get("columns", {}),
                    database=node_data.get("database"),
                    schema_name=node_data.get("schema"),
                    alias=node_data.get("alias")
                )
                project.models[model.unique_id] = model

            elif node_id.startswith("source."):
                source = DbtSource(
                    name=node_data.get("name", ""),
                    unique_id=node_id,
                    source_name=node_data.get("source_name", ""),
                    loader=node_data.get("loader", ""),
                    description=node_data.get("description", ""),
                    tables=node_data.get("columns", {})
                )
                project.sources[source.unique_id] = source

            elif node_id.startswith("test."):
                test = DbtTest(
                    name=node_data.get("name", ""),
                    unique_id=node_id,
                    test_type="generic" if "generic" in node_data.get("test_metadata", {}).get("name", "") else "singular",
                    test_metadata=node_data.get("test_metadata", {}),
                    depends_on=node_data.get("depends_on", {}).get("nodes", []),
                    config=node_data.get("config", {}),
                    tags=node_data.get("tags", [])
                )
                project.tests[test.unique_id] = test

        return project

    async def trigger_job(
        self,
        project_name: str,
        job_id: int,
        cause: str = "API trigger"
    ) -> Dict[str, Any]:
        """触发 dbt Cloud 任务"""
        if project_name not in self._cloud_clients:
            raise ValueError(f"Project {project_name} not registered as Cloud project")

        client = self._cloud_clients[project_name]
        run = await client.trigger_job(job_id, cause)

        self._runs[str(run.id)] = run

        return run.to_dict()

    async def get_run_status(self, run_id: int) -> Dict[str, Any]:
        """获取运行状态"""
        # 查找对应的 client
        run = self._runs.get(str(run_id))
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # 查找 client
        client = None
        for c in self._cloud_clients.values():
            try:
                run = await c.get_run(run_id)
                self._runs[str(run_id)] = run
                break
            except Exception:
                continue

        if not run:
            raise ValueError(f"Failed to get run status for {run_id}")

        return run.to_dict()

    async def get_project_models(self, project_name: str) -> List[Dict[str, Any]]:
        """获取项目模型列表"""
        if project_name not in self._projects:
            raise ValueError(f"Project {project_name} not found")

        project = self._projects[project_name]
        return [model.to_dict() for model in project.models.values()]

    async def get_project_sources(self, project_name: str) -> List[Dict[str, Any]]:
        """获取项目源列表"""
        if project_name not in self._projects:
            raise ValueError(f"Project {project_name} not found")

        project = self._projects[project_name]
        return [source.to_dict() for source in project.sources.values()]

    async def get_lineage(self, project_name: str, node_id: str) -> Dict[str, Any]:
        """获取节点血缘关系"""
        if project_name not in self._lineage_builders:
            raise ValueError(f"Project {project_name} not found")

        builder = self._lineage_builders[project_name]
        return builder.get_lineage_graph(node_id)

    async def get_lineage_summary(self, project_name: str) -> Dict[str, Any]:
        """获取血缘统计"""
        if project_name not in self._lineage_builders:
            raise ValueError(f"Project {project_name} not found")

        builder = self._lineage_builders[project_name]

        return {
            "project_name": project_name,
            "total_nodes": len(builder._nodes),
            "total_edges": len(builder._edges),
            "models_count": len(self._projects[project_name].models),
            "sources_count": len(self._projects[project_name].sources),
            "tests_count": len(self._projects[project_name].tests)
        }

    async def search_models(self, project_name: str, query: str) -> List[Dict[str, Any]]:
        """搜索模型"""
        if project_name not in self._projects:
            raise ValueError(f"Project {project_name} not found")

        project = self._projects[project_name]
        query_lower = query.lower()

        results = []
        for model in project.models.values():
            if (query_lower in model.name.lower() or
                query_lower in model.description.lower() or
                any(query_lower in tag.lower() for tag in model.tags)):
                results.append(model.to_dict())

        return results

    async def _save_project(self, name: str, project: DbtProject) -> None:
        """保存项目到数据库"""
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            await session.execute(text("""
                INSERT INTO dbt_projects (name, version, project_root, profile_name, metadata)
                VALUES (:name, :version, :project_root, :profile_name, :metadata)
                ON CONFLICT (name) DO UPDATE SET
                    version = EXCLUDED.version,
                    project_root = EXCLUDED.project_root,
                    profile_name = EXCLUDED.profile_name,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "name": name,
                "version": project.version,
                "project_root": project.project_root,
                "profile_name": project.profile_name,
                "metadata": json.dumps(project.to_dict())
            })
            await session.commit()


# 数据库初始化
async def init_dbt_tables():
    """初始化 dbt 相关数据库表"""
    async with db_manager.get_async_session() as session:
        from sqlalchemy import Table, MetaData
        metadata = MetaData()

        dbt_projects = Table(
            'dbt_projects', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255), unique=True, nullable=False),
            Column('version', String(50)),
            Column('project_root', String(500)),
            Column('profile_name', String(255)),
            Column('metadata', JSON),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            Index('idx_dbt_projects_name', 'name'),
        )

        dbt_jobs = Table(
            'dbt_jobs', metadata,
            Column('id', Integer, primary_key=True),
            Column('project_name', String(255), nullable=False),
            Column('job_id', Integer, nullable=False),
            Column('name', String(255)),
            Column('schedule', JSON),
            Column('last_run_at', DateTime),
            Column('last_run_status', String(50)),
            Column('enabled', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_dbt_jobs_project', 'project_name'),
        )

        dbt_runs = Table(
            'dbt_runs', metadata,
            Column('id', Integer, primary_key=True),
            Column('project_name', String(255), nullable=False),
            Column('job_id', Integer, nullable=False),
            Column('run_id', Integer, nullable=False),
            Column('status', String(50)),
            Column('started_at', DateTime),
            Column('finished_at', DateTime),
            Column('error_message', Text),
            Column('metrics', JSON),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_dbt_runs_project', 'project_name'),
            Index('idx_dbt_runs_run_id', 'run_id'),
            Index('idx_dbt_runs_status', 'status'),
        )

        await db_manager.init_db()
        logger.info("dbt database tables initialized")


# 全局服务实例
dbt_service = DbtIntegrationService()


async def start_dbt_service():
    """启动 dbt 服务"""
    await init_dbt_tables()
    logger.info("dbt service started")


async def stop_dbt_service():
    """停止 dbt 服务"""
    # 关闭所有 cloud clients
    for client in dbt_service._cloud_clients.values():
        await client.close()
    logger.info("dbt service stopped")
