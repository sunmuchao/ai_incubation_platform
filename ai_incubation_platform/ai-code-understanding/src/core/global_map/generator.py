"""
全局地图生成器
从代码索引中自动生成项目的全局结构视图
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import os
import json
import re
from datetime import datetime
from dataclasses import dataclass, field

# LLM客户端（可配置接入OpenAI、Anthropic、本地模型等）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..indexer.base import CodeSymbol, FileIndexResult


@dataclass
class ModuleNode:
    """模块节点：目录或包结构"""
    name: str
    path: str
    type: str  # directory, package, file
    children: Dict[str, 'ModuleNode'] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)
    symbols: List[CodeSymbol] = field(default_factory=list)
    description: str = ""


@dataclass
class Layer:
    """架构层"""
    name: str
    description: str
    paths: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    key_modules: List[str] = field(default_factory=list)


@dataclass
class GlobalMap:
    """全局地图结构"""
    project_name: str
    repo_path: str
    stack_hint: Optional[str] = None
    layers: List[Layer] = field(default_factory=list)
    module_tree: ModuleNode = None
    entrypoints: List[Dict[str, str]] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    key_symbols: List[Dict[str, Any]] = field(default_factory=list)
    tech_stack: Dict[str, str] = field(default_factory=dict)


class GlobalMapGenerator:
    """
    全局地图生成器
    架构思路：
    1. 多源数据融合：目录结构 + 代码符号 + 配置文件 + 文档
    2. 分层自动识别：基于路径模式和代码特征识别架构分层
    3. 可解释性：所有生成内容都有溯源依据
    4. 可扩展：支持自定义分层规则、识别器插件
    """

    # 常见架构层的路径模式
    LAYER_PATTERNS = [
        {
            "name": "接入层",
            "description": "对外提供API、路由、入口控制",
            "patterns": ["**/api/**", "**/routes/**", "**/controllers/**", "**/handler/**",
                        "**/entrypoints/**", "**/gateway/**", "**/rest/**", "**/graphql/**"],
            "responsibilities": ["请求路由", "参数校验", "权限控制", "协议转换"]
        },
        {
            "name": "领域/服务层",
            "description": "核心业务逻辑与领域模型实现",
            "patterns": ["**/services/**", "**/domain/**", "**/biz/**", "**/core/**",
                        "**/logic/**", "**/manager/**", "**/usecase/**"],
            "responsibilities": ["业务规则", "流程编排", "领域模型", "业务校验"]
        },
        {
            "name": "数据访问层",
            "description": "数据存储与外部服务集成",
            "patterns": ["**/db/**", "**/repository/**", "**/dao/**", "**/dal/**",
                        "**/clients/**", "**/infrastructure/**", "**/external/**",
                        "**/persistence/**", "**/adapter/**"],
            "responsibilities": ["数据库操作", "缓存", "外部API调用", "消息队列"]
        },
        {
            "name": "公共组件层",
            "description": "通用工具、配置、中间件",
            "patterns": ["**/common/**", "**/utils/**", "**/helpers/**", "**/config/**",
                        "**/middleware/**", "**/shared/**", "**/libs/**", "**/pkg/**"],
            "responsibilities": ["工具函数", "配置管理", "中间件", "通用组件"]
        },
        {
            "name": "前端展示层",
            "description": "用户界面与前端逻辑",
            "patterns": ["**/frontend/**", "**/web/**", "**/ui/**", "**/components/**",
                        "**/pages/**", "**/views/**", "**/static/**", "**/public/**"],
            "responsibilities": ["界面渲染", "用户交互", "前端路由", "状态管理"]
        }
    ]

    # 入口文件模式
    ENTRYPOINT_PATTERNS = [
        "main.py", "app.py", "index.js", "index.ts", "server.js", "server.ts",
        "Application.java", "Main.java", "main.go", "cmd/main.go", "main.rs",
        "package.json", "pyproject.toml", "setup.py", "pom.xml", "build.gradle",
        "Cargo.toml", "go.mod", "requirements.txt"
    ]

    # 技术栈识别模式
    TECH_STACK_PATTERNS = {
        "languages": {
            "Python": ["*.py", "requirements.txt", "pyproject.toml", "setup.py"],
            "JavaScript": ["*.js", "package.json", "node_modules"],
            "TypeScript": ["*.ts", "*.tsx", "tsconfig.json"],
            "Java": ["*.java", "pom.xml", "build.gradle"],
            "Go": ["*.go", "go.mod", "go.sum"],
            "Rust": ["*.rs", "Cargo.toml", "Cargo.lock"],
            "C++": ["*.cpp", "*.hpp", "CMakeLists.txt"],
            "Ruby": ["*.rb", "Gemfile"],
            "PHP": ["*.php", "composer.json"],
        },
        "frameworks": {
            "FastAPI": ["fastapi", "FastAPI"],
            "Django": ["django", "Django"],
            "Flask": ["flask", "Flask"],
            "Spring Boot": ["spring-boot", "@SpringBootApplication"],
            "React": ["react", "React", "*.jsx", "*.tsx"],
            "Vue": ["vue", "Vue"],
            "Angular": ["angular", "@angular/core"],
            "Next.js": ["next", "Next.js"],
            "Gin": ["gin-gonic", "gin."],
            "Express": ["express", "require('express')"],
        },
        "databases": {
            "PostgreSQL": ["psycopg2", "postgres", "PostgreSQL"],
            "MySQL": ["mysql", "pymysql"],
            "MongoDB": ["pymongo", "mongodb"],
            "Redis": ["redis", "Redis"],
            "SQLite": ["sqlite", "SQLite"],
        }
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_files_per_layer = self.config.get('min_files_per_layer', 1)

        # LLM配置
        self.llm_config = self.config.get('llm', {})
        self.llm_enabled = self.llm_config.get('enabled', False)
        self.llm_client = None
        if self.llm_enabled and OPENAI_AVAILABLE:
            try:
                self.llm_client = OpenAI(
                    api_key=self.llm_config.get('api_key'),
                    base_url=self.llm_config.get('base_url')
                )
            except:
                self.llm_enabled = False

    def generate(
        self,
        project_name: str,
        repo_path: str,
        file_results: List[FileIndexResult],
        stack_hint: Optional[str] = None
    ) -> GlobalMap:
        """生成全局地图"""
        repo_path = Path(repo_path).resolve()

        # 1. 构建模块树
        module_tree = self._build_module_tree(repo_path, file_results)

        # 2. 生成模块职责描述
        self._generate_module_descriptions(module_tree)

        # 3. 识别架构层
        layers = self._identify_layers(repo_path, module_tree)

        # 3. 识别入口点
        entrypoints = self._identify_entrypoints(repo_path, module_tree)

        # 4. 识别技术栈
        tech_stack = self._identify_tech_stack(repo_path, file_results)

        # 5. 分析代码约定
        conventions = self._identify_conventions(file_results)

        # 6. 提取关键符号
        key_symbols = self._extract_key_symbols(file_results)

        # 7. 构建依赖关系
        dependencies = self._build_dependency_graph(repo_path, file_results)

        return GlobalMap(
            project_name=project_name,
            repo_path=str(repo_path),
            stack_hint=stack_hint,
            layers=layers,
            module_tree=module_tree,
            entrypoints=entrypoints,
            conventions=conventions,
            dependencies=dependencies,
            key_symbols=key_symbols,
            tech_stack=tech_stack
        )

    def _build_module_tree(
        self,
        repo_path: Path,
        file_results: List[FileIndexResult]
    ) -> ModuleNode:
        """构建目录模块树"""
        root = ModuleNode(
            name=repo_path.name,
            path=str(repo_path),
            type="directory"
        )

        for file_result in file_results:
            file_path = Path(file_result.file_path)
            try:
                rel_path = file_path.relative_to(repo_path)
            except ValueError:
                continue  # 文件不在仓库路径下，跳过

            # 构建目录结构
            current = root
            parts = list(rel_path.parts[:-1])  # 排除文件名
            for part in parts:
                if part not in current.children:
                    current.children[part] = ModuleNode(
                        name=part,
                        path=str(repo_path / Path(*rel_path.parts[:parts.index(part)+1])),
                        type="directory"
                    )
                current = current.children[part]

            # 添加文件到当前目录
            current.files.append(str(file_path))
            # 添加符号到目录
            current.symbols.extend(file_result.symbols)

        return root

    def _identify_layers(self, repo_path: Path, module_tree: ModuleNode) -> List[Layer]:
        """识别架构分层"""
        layers = []

        def pattern_tokens(pattern: str) -> List[str]:
            """
            将类似 "**/services/**" 的 glob 简化为 token 列表 ["services"]，
            用 token 是否出现在路径分段中完成匹配（避免空段导致匹配失败）。
            """
            # 提取路径分段/标识符 token，例如 **/api/** -> ["api"]
            return re.findall(r"[A-Za-z0-9_\\-]+", pattern)

        def collect_paths(node: ModuleNode, current_path: str = "") -> List[str]:
            """递归收集所有路径"""
            paths = []
            if node.type == "directory":
                node_path = f"{current_path}/{node.name}" if current_path else node.name
                paths.append(node_path)
                for child in node.children.values():
                    paths.extend(collect_paths(child, node_path))
            return paths

        all_paths = collect_paths(module_tree)

        for layer_config in self.LAYER_PATTERNS:
            matched_paths = []
            for pattern in layer_config["patterns"]:
                tokens = pattern_tokens(pattern)
                for path in all_paths:
                    path_parts = path.split("/")
                    if tokens and all(token in path_parts for token in tokens):
                        matched_paths.append(path)

            # 去重
            matched_paths = list(set(matched_paths))
            if len(matched_paths) >= self.min_files_per_layer:
                layer = Layer(
                    name=layer_config["name"],
                    description=layer_config["description"],
                    paths=matched_paths,
                    responsibilities=layer_config["responsibilities"]
                )
                layers.append(layer)

        return layers

    def _identify_entrypoints(self, repo_path: Path, module_tree: ModuleNode) -> List[Dict[str, str]]:
        """识别项目入口点"""
        entrypoints = []

        def scan_files(node: ModuleNode):
            for file_path in node.files:
                file_name = Path(file_path).name
                if file_name in self.ENTRYPOINT_PATTERNS:
                    try:
                        rel_path = Path(file_path).relative_to(repo_path)
                        entrypoints.append({
                            "name": file_name,
                            "path": str(rel_path),
                            "type": self._get_entrypoint_type(file_name)
                        })
                    except ValueError:
                        pass
            for child in node.children.values():
                scan_files(child)

        scan_files(module_tree)
        return entrypoints

    def _get_entrypoint_type(self, file_name: str) -> str:
        """判断入口点类型"""
        ext = Path(file_name).suffix.lower()
        if ext in ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp']:
            return "code"
        elif file_name in ['package.json', 'pyproject.toml', 'pom.xml', 'build.gradle', 'Cargo.toml']:
            return "package_config"
        elif file_name in ['requirements.txt', 'go.mod']:
            return "dependency_config"
        else:
            return "config"

    def _identify_tech_stack(self, repo_path: Path, file_results: List[FileIndexResult]) -> Dict[str, str]:
        """识别技术栈"""
        tech_stack = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": []
        }

        # 按文件存在性检测语言
        for lang, patterns in self.TECH_STACK_PATTERNS["languages"].items():
            for pattern in patterns:
                # patterns 里可能包含类似 "*.py" 这样的扩展名通配符
                if pattern.startswith("*."):
                    ext = pattern[1:]  # "*.py" -> ".py"
                    if any(str(fr.file_path).endswith(ext) for fr in file_results):
                        if lang not in tech_stack["languages"]:
                            tech_stack["languages"].append(lang)
                        break
                else:
                    # 其他情况：用子串命中即可（如 requirements.txt）
                    if any(pattern in fr.file_path for fr in file_results):
                        if lang not in tech_stack["languages"]:
                            tech_stack["languages"].append(lang)
                        break

        # 按代码内容检测框架
        for framework, patterns in self.TECH_STACK_PATTERNS["frameworks"].items():
            for pattern in patterns:
                if any(pattern in fr.file_path or any(pattern in chunk.content for chunk in fr.chunks)
                      for fr in file_results):
                    if framework not in tech_stack["frameworks"]:
                        tech_stack["frameworks"].append(framework)
                    break

        # 检测数据库
        for db, patterns in self.TECH_STACK_PATTERNS["databases"].items():
            for pattern in patterns:
                if any(pattern in chunk.content for fr in file_results for chunk in fr.chunks):
                    if db not in tech_stack["databases"]:
                        tech_stack["databases"].append(db)
                    break

        return tech_stack

    def _identify_conventions(self, file_results: List[FileIndexResult]) -> List[str]:
        """识别代码约定"""
        conventions = []

        if not file_results:
            return conventions

        # 文件命名约定
        extensions = defaultdict(int)
        for fr in file_results:
            ext = Path(fr.file_path).suffix.lower()
            extensions[ext] += 1

        main_exts = [ext for ext, count in extensions.items() if count > len(file_results) * 0.1]
        if main_exts:
            conventions.append(f"主要使用的文件类型: {', '.join(main_exts)}")

        # 目录结构约定
        common_dirs = defaultdict(int)
        for fr in file_results:
            parts = Path(fr.file_path).parts
            for part in parts:
                if part in ['src', 'lib', 'test', 'tests', 'docs', 'config', 'api', 'services']:
                    common_dirs[part] += 1

        if common_dirs:
            top_dirs = [d for d, _ in sorted(common_dirs.items(), key=lambda x: x[1], reverse=True)[:5]]
            conventions.append(f"常见目录结构: {', '.join(top_dirs)}")

        # 命名风格检测
        symbol_names = []
        for fr in file_results:
            for symbol in fr.symbols:
                symbol_names.append(symbol.name)

        if symbol_names:
            # 检测蛇形命名
            snake_case = sum(1 for name in symbol_names if '_' in name and name.islower())
            # 检测驼峰命名
            camel_case = sum(1 for name in symbol_names if name[0].islower() and any(c.isupper() for c in name[1:]))
            # 检测帕斯卡命名
            pascal_case = sum(1 for name in symbol_names if name[0].isupper())

            total = len(symbol_names)
            if snake_case / total > 0.5:
                conventions.append("代码命名风格: 主要使用蛇形命名(snake_case)")
            elif camel_case / total > 0.5:
                conventions.append("代码命名风格: 主要使用小驼峰命名(camelCase)")
            elif pascal_case / total > 0.5:
                conventions.append("代码命名风格: 主要使用大驼峰命名(PascalCase)")

        return conventions

    def _extract_key_symbols(self, file_results: List[FileIndexResult]) -> List[Dict[str, Any]]:
        """提取关键符号（公共类、入口函数等）"""
        key_symbols = []

        # 暂时提取所有公共类和函数，后续可以做更智能的筛选
        for fr in file_results:
            for symbol in fr.symbols:
                if symbol.symbol_type in ['class', 'function']:
                    # 简单的公开性判断
                    is_public = not symbol.name.startswith('_')
                    if is_public:
                        key_symbols.append({
                            "name": symbol.name,
                            "type": symbol.symbol_type,
                            "file_path": fr.file_path,
                            "start_line": symbol.start_line,
                            "signature": symbol.signature,
                            "docstring": symbol.docstring
                        })

        # 限制返回数量
        return key_symbols[:50]

    def _build_dependency_graph(self, repo_path: Path, file_results: List[FileIndexResult]) -> Dict[str, Any]:
        """构建完整的依赖关系图"""
        dependencies = {
            "file_dependencies": {},  # 文件 -> [依赖的文件列表]
            "module_dependencies": {},  # 模块 -> [依赖的模块列表]
            "most_imported": [],  # 被引用最多的模块
            "reverse_dependencies": {},  # 模块 -> [被哪些模块引用]
            "dependency_heatmap": {}  # 模块热度统计
        }

        # 首先构建文件路径到模块名的映射
        file_to_module = {}
        module_files = defaultdict(list)

        for fr in file_results:
            file_path = Path(fr.file_path)
            try:
                rel_path = file_path.relative_to(repo_path)
            except ValueError:
                # 文件不在仓库内：回退到原始实现（尽量不影响整体输出）
                module_name = file_path.with_suffix('').as_posix().replace('/', '.')
                file_to_module[fr.file_path] = module_name
                module_files[module_name].append(fr.file_path)
                continue

            # 提取模块名（去掉扩展名，路径转点分隔）
            # 例如：src/services/understanding_service.py -> services.understanding_service
            module_name = rel_path.with_suffix('').as_posix().replace('/', '.')
            if module_name.startswith("src."):
                module_name = module_name[len("src."):]

            file_to_module[fr.file_path] = module_name
            module_files[module_name].append(fr.file_path)

        # 构建文件级依赖
        file_deps = defaultdict(set)
        reverse_deps = defaultdict(set)
        import_counts = defaultdict(int)

        for fr in file_results:
            current_file = fr.file_path
            current_module = file_to_module.get(current_file)
            if not current_module:
                continue

            file_deps[current_file] = set()

            for imp in fr.imports:
                # 尝试匹配导入的模块
                matched_module = None
                # 简单匹配：导入语句包含模块名
                for module_name in module_files.keys():
                    if module_name in imp or imp.split()[-1] in module_name:
                        matched_module = module_name
                        break

                if matched_module:
                    # 找到模块对应的文件
                    for dep_file in module_files[matched_module]:
                        file_deps[current_file].add(dep_file)
                        reverse_deps[dep_file].add(current_file)
                    import_counts[matched_module] += 1

        # 转换为列表格式
        for file, deps in file_deps.items():
            dependencies["file_dependencies"][file] = list(deps)

        # 构建模块级依赖
        module_deps = defaultdict(set)
        for file, deps in file_deps.items():
            module = file_to_module.get(file)
            if module:
                for dep_file in deps:
                    dep_module = file_to_module.get(dep_file)
                    if dep_module and dep_module != module:
                        module_deps[module].add(dep_module)

        for module, deps in module_deps.items():
            dependencies["module_dependencies"][module] = list(deps)

        # 构建反向依赖
        for file, refs in reverse_deps.items():
            module = file_to_module.get(file)
            if module:
                dependencies["reverse_dependencies"][module] = list({file_to_module.get(ref, ref) for ref in refs})

        # 统计最常被导入的模块
        sorted_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)
        for imp, count in sorted_imports[:20]:
            dependencies["most_imported"].append({
                "module": imp,
                "reference_count": count
            })

        # 依赖热度图（按引用次数）
        dependencies["dependency_heatmap"] = dict(sorted_imports[:50])

        return dependencies

    def _generate_module_descriptions(self, module_tree: ModuleNode) -> None:
        """为模块树自动生成职责描述"""
        if not self.llm_enabled:
            # 无LLM时生成基础描述
            def generate_basic_description(node: ModuleNode):
                file_count = len(node.files)
                symbol_count = len(node.symbols)
                child_count = len(node.children)
                if child_count > 0:
                    node.description = f"包含 {child_count} 个子模块，共 {file_count} 个文件，{symbol_count} 个符号"
                else:
                    node.description = f"包含 {file_count} 个文件，{symbol_count} 个符号"

                for child in node.children.values():
                    generate_basic_description(child)

            generate_basic_description(module_tree)
            return

        def process_node(node: ModuleNode, parent_path: str = ""):
            # 收集模块信息
            module_path = f"{parent_path}.{node.name}" if parent_path else node.name
            symbols_info = []
            for symbol in node.symbols[:10]:  # 最多10个符号
                symbols_info.append(f"- {symbol.symbol_type}: {symbol.name}" + (f" - {symbol.docstring[:50]}..." if symbol.docstring else ""))

            file_count = len(node.files)
            child_count = len(node.children)

            if symbols_info or file_count > 0:
                # 构建提示词
                prompt = f"""
                请分析以下模块的职责，生成简洁的描述（不超过200字）：

                模块路径: {module_path}
                包含文件数: {file_count}
                子模块数: {child_count}
                包含的主要符号:
                {chr(10).join(symbols_info) if symbols_info else "无"}

                请只返回模块职责描述，不需要其他解释。
                """

                try:
                    response = self.llm_client.chat.completions.create(
                        model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                        messages=[
                            {"role": "system", "content": "你是一个专业的代码分析助手，擅长总结模块职责。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=200
                    )
                    node.description = response.choices[0].message.content.strip()
                except Exception as e:
                    print(f"生成模块描述失败 {module_path}: {str(e)}")
                    node.description = f"包含 {file_count} 个文件，{len(node.symbols)} 个符号"
            else:
                node.description = f"包含 {child_count} 个子模块"

            # 递归处理子模块
            for child in node.children.values():
                process_node(child, module_path)

        process_node(module_tree)

    def to_dict(self, global_map: GlobalMap) -> Dict[str, Any]:
        """导出全局地图为可序列化的 JSON 结构"""
        from datetime import datetime

        def module_to_dict(node: ModuleNode) -> Dict[str, Any]:
            return {
                "name": node.name,
                "path": node.path,
                "type": node.type,
                "children": {k: module_to_dict(v) for k, v in node.children.items()},
                "file_count": len(node.files),
                "symbol_count": len(node.symbols),
                "description": node.description,
            }

        def layer_to_dict(layer: Layer) -> Dict[str, Any]:
            return {
                "name": layer.name,
                "description": layer.description,
                "paths": layer.paths,
                "responsibilities": layer.responsibilities,
                "key_modules": layer.key_modules,
            }

        return {
            "project": global_map.project_name,
            "repo_path": global_map.repo_path,
            "stack_hint": global_map.stack_hint,
            "tech_stack": global_map.tech_stack,
            "layers": [layer_to_dict(layer) for layer in global_map.layers],
            "module_tree": module_to_dict(global_map.module_tree) if global_map.module_tree else None,
            "entrypoints": global_map.entrypoints,
            "conventions": global_map.conventions,
            "key_symbols": global_map.key_symbols,
            "dependencies": global_map.dependencies,
            "generated_at": datetime.now().isoformat(),
            "problem_solved": (
                "在 Cursor/Claude Code 等工具里局部改代码很快，但仓库一大容易失去全局图景；"
                "本接口用于聚合「一眼能看懂的系统地图」。"
            ),
            "integration_with_ide": [
                "导出本结构为 Markdown，粘贴到 Cursor/Claude 作项目级上下文",
                "对子路径建索引后，问答与「从哪读起」可接 RAG",
            ],
        }

    def to_markdown(self, global_map: GlobalMap) -> str:
        """导出全局地图为Markdown格式，方便粘贴到AI助手上下文"""
        md = f"# 项目全局地图：{global_map.project_name}\n\n"
        md += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"> 仓库路径：{global_map.repo_path}\n\n"

        # 技术栈
        md += "## 🛠️ 技术栈\n\n"
        if global_map.tech_stack.get("languages"):
            md += f"- **编程语言**: {', '.join(global_map.tech_stack['languages'])}\n"
        if global_map.tech_stack.get("frameworks"):
            md += f"- **框架**: {', '.join(global_map.tech_stack['frameworks'])}\n"
        if global_map.tech_stack.get("databases"):
            md += f"- **数据库**: {', '.join(global_map.tech_stack['databases'])}\n"
        md += "\n"

        # 架构分层
        if global_map.layers:
            md += "## 🏗️ 架构分层\n\n"
            for layer in global_map.layers:
                md += f"### {layer.name}\n"
                md += f"- **描述**: {layer.description}\n"
                md += f"- **职责**: {', '.join(layer.responsibilities)}\n"
                md += f"- **路径**: {', '.join(layer.paths)}\n\n"

        # 入口点
        if global_map.entrypoints:
            md += "## 🚪 入口点\n\n"
            for entry in global_map.entrypoints:
                md += f"- `{entry['path']}` ({entry['type']})\n"
            md += "\n"

        # 代码约定
        if global_map.conventions:
            md += "## 📋 代码约定\n\n"
            for convention in global_map.conventions:
                md += f"- {convention}\n"
            md += "\n"

        # 模块树
        if global_map.module_tree:
            md += "## 📁 模块结构\n\n"

            def print_module(node: ModuleNode, level: int = 0) -> str:
                indent = "  " * level
                md_part = f"{indent}- **{node.name}**"
                if node.description:
                    md_part += f": {node.description}"
                md_part += "\n"

                for child in node.children.values():
                    md_part += print_module(child, level + 1)

                return md_part

            md += print_module(global_map.module_tree)
            md += "\n"

        # 关键符号
        if global_map.key_symbols:
            md += "## 🔑 核心符号\n\n"
            for symbol in global_map.key_symbols[:20]:  # 最多20个
                md += f"- `{symbol['name']}` ({symbol['type']}) - {symbol['file_path']}:{symbol['start_line']}\n"
                if symbol.get('docstring'):
                    md += f"  > {symbol['docstring'][:100]}...\n"
            md += "\n"

        # 依赖分析
        if global_map.dependencies and global_map.dependencies.get("most_imported"):
            md += "## 📊 依赖分析\n\n"
            md += "### 最常引用的模块\n\n"
            for dep in global_map.dependencies["most_imported"][:10]:
                md += f"- `{dep['module']}`: 被引用 {dep['reference_count']} 次\n"
            md += "\n"

        # 使用说明
        md += "## 💡 使用建议\n\n"
        md += "1. 将此文档粘贴到Cursor/Claude等AI助手的项目上下文中，帮助AI理解全局结构\n"
        md += "2. 开发新功能前，先查看相关模块的职责和依赖关系\n"
        md += "3. 排查问题时，从入口点开始，按架构分层逐步定位\n"

        return md
