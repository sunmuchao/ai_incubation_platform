"""
跨仓库 Monorepo 索引工具

支持多仓库联合索引，适用于：
1. Monorepo 架构（多个子项目在同一仓库）
2. Microrepo 架构（多个关联仓库）
3. 跨项目代码复用场景

使用方式：
    # 索引多个关联仓库
    python src/tools/monorepo_indexer.py \
      --config monorepo_config.json \
      --output data/monorepo_index
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.understanding_service import understanding_service


class MonorepoIndexer:
    """
    跨仓库索引器

    功能：
    1. 多仓库联合索引
    2. 跨项目依赖分析
    3. 统一全局地图生成
    4. 增量索引优化
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化索引器

        Args:
            config_path: 配置文件路径，定义多个仓库的信息
        """
        self.config = self._load_config(config_path) if config_path else {}
        self.service = understanding_service
        self.indexed_repos: Set[str] = set()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def index_repos(
        self,
        repos: List[Dict[str, str]],
        collection_name: str,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        索引多个仓库

        Args:
            repos: 仓库列表，每个包含 name 和 path
            collection_name: 统一 collection 名称
            incremental: 是否增量索引

        Returns:
            索引结果统计
        """
        stats = {
            "total_repos": len(repos),
            "success_repos": 0,
            "failed_repos": 0,
            "total_files": 0,
            "total_chunks": 0,
            "total_symbols": 0,
            "details": []
        }

        for repo in repos:
            repo_name = repo.get("name", "unknown")
            repo_path = repo.get("path", "")

            print(f"[INFO] 索引仓库：{repo_name} ({repo_path})")

            try:
                # 索引仓库
                result = self.service.index_project(
                    project_name=f"{collection_name}_{repo_name}",
                    repo_path=repo_path,
                    incremental=incremental
                )

                if result.get("success"):
                    stats["success_repos"] += 1
                    repo_stats = result.get("stats", {})
                    stats["total_files"] += repo_stats.get("success_files", 0)
                    stats["total_chunks"] += repo_stats.get("total_chunks", 0)
                    stats["total_symbols"] += repo_stats.get("total_symbols", 0)
                    self.indexed_repos.add(repo_name)
                else:
                    stats["failed_repos"] += 1

                stats["details"].append({
                    "repo_name": repo_name,
                    "success": result.get("success", False),
                    "error": result.get("error"),
                    "stats": result.get("stats", {})
                })

            except Exception as e:
                stats["failed_repos"] += 1
                stats["details"].append({
                    "repo_name": repo_name,
                    "success": False,
                    "error": str(e)
                })
                print(f"[ERROR] 索引失败 {repo_name}: {str(e)}")

        return stats

    def generate_unified_map(
        self,
        project_name: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        生成统一的全局地图（合并所有索引的仓库）

        Args:
            project_name: 项目名称
            output_format: 输出格式 (json/markdown)

        Returns:
            统一的全局地图
        """
        # 收集所有子项目的地图
        all_maps = []
        for repo_name in self.indexed_repos:
            collection_name = f"{project_name}_{repo_name}"
            try:
                # 复用已缓存的地图
                if collection_name in self.service._global_maps:
                    global_map = self.service._global_maps[collection_name]
                    all_maps.append(
                        self.service.global_map_generator.to_dict(global_map)
                    )
            except Exception as e:
                print(f"[WARN] 获取地图失败 {collection_name}: {str(e)}")

        # 合并地图
        unified_map = self._merge_maps(project_name, all_maps)

        if output_format.lower() == "markdown":
            markdown = self._convert_to_markdown(unified_map)
            return {"project": project_name, "markdown": markdown}
        else:
            return unified_map

    def _merge_maps(
        self,
        project_name: str,
        maps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """合并多个地图"""
        unified = {
            "project": project_name,
            "repo_path": "monorepo",
            "stack_hint": "monorepo",
            "tech_stack": self._merge_tech_stacks(maps),
            "layers": self._merge_layers(maps),
            "module_tree": self._merge_module_trees(maps),
            "entrypoints": self._merge_entrypoints(maps),
            "conventions": self._merge_conventions(maps),
            "dependencies": self._merge_dependencies(maps),
            "key_symbols": self._merge_key_symbols(maps),
            "sub_projects": list(self.indexed_repos),
            "generated_at": datetime.now().isoformat()
        }
        return unified

    def _merge_tech_stacks(self, maps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并技术栈信息"""
        merged = {
            "languages": set(),
            "frameworks": set(),
            "databases": set(),
            "tools": set()
        }
        for m in maps:
            tech_stack = m.get("tech_stack", {})
            for key in merged.keys():
                if key in tech_stack:
                    merged[key].update(tech_stack[key])
        return {k: list(v) for k, v in merged.items()}

    def _merge_layers(self, maps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并架构层信息"""
        layer_map = {}
        for m in maps:
            for layer in m.get("layers", []):
                name = layer.get("name", "Unknown")
                if name not in layer_map:
                    layer_map[name] = {
                        "name": name,
                        "description": layer.get("description", ""),
                        "paths": set(),
                        "responsibilities": layer.get("responsibilities", [])
                    }
                layer_map[name]["paths"].update(layer.get("paths", []))
        return [
            {**v, "paths": list(v["paths"])}
            for v in layer_map.values()
        ]

    def _merge_module_trees(self, maps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并模块树"""
        # 简化合并：创建一个包含所有子项目的根节点
        root = {
            "name": "monorepo",
            "path": ".",
            "type": "directory",
            "children": {},
            "file_count": 0,
            "symbol_count": 0,
            "description": "Monorepo 根目录"
        }

        for m in maps:
            tree = m.get("module_tree", {})
            if tree:
                project_name = tree.get("name", "unknown")
                root["children"][project_name] = tree
                root["file_count"] += tree.get("file_count", 0)
                root["symbol_count"] += tree.get("symbol_count", 0)

        return root

    def _merge_entrypoints(self, maps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """合并入口点"""
        entrypoints = []
        for m in maps:
            for entry in m.get("entrypoints", []):
                # 添加项目前缀便于区分
                new_entry = entry.copy()
                new_entry["project"] = m.get("project", "unknown")
                entrypoints.append(new_entry)
        return entrypoints

    def _merge_conventions(self, maps: List[Dict[str, Any]]) -> List[str]:
        """合并代码约定"""
        conventions = set()
        for m in maps:
            conventions.update(m.get("conventions", []))
        return list(conventions)

    def _merge_dependencies(self, maps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并依赖关系"""
        merged = {
            "file_dependencies": {},
            "module_dependencies": {},
            "most_imported": [],
            "reverse_dependencies": {},
            "dependency_heatmap": {},
            "cross_project_deps": []  # 跨项目依赖
        }

        # 收集所有依赖
        for m in maps:
            deps = m.get("dependencies", {})
            project = m.get("project", "unknown")

            # 合并文件依赖
            for file, dep_list in deps.get("file_dependencies", {}).items():
                merged["file_dependencies"][file] = dep_list

            # 合并模块依赖
            for module, dep_list in deps.get("module_dependencies", {}).items():
                merged["module_dependencies"][f"{project}.{module}"] = [
                    f"{project}.{d}" for d in dep_list
                ]

            # 合并依赖热度
            for module, heat in deps.get("dependency_heatmap", {}).items():
                merged["dependency_heatmap"][f"{project}.{module}"] = heat

        # TODO: 分析跨项目依赖
        # merged["cross_project_deps"] = self._analyze_cross_project_deps(merged)

        return merged

    def _merge_key_symbols(self, maps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并关键符号"""
        symbols = []
        for m in maps:
            project = m.get("project", "unknown")
            for sym in m.get("key_symbols", [])[:10]:
                new_sym = sym.copy()
                new_sym["project"] = project
                symbols.append(new_sym)
        return symbols[:100]  # 限制总数

    def _convert_to_markdown(self, unified_map: Dict[str, Any]) -> str:
        """转换为 Markdown 格式"""
        md = f"# Monorepo 全局地图：{unified_map['project']}\n\n"
        md += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"> 子项目数：{len(unified_map.get('sub_projects', []))}\n\n"

        # 子项目列表
        md += "## 子项目列表\n\n"
        for proj in unified_map.get("sub_projects", []):
            md += f"- {proj}\n"
        md += "\n"

        # 技术栈
        md += "## 技术栈\n\n"
        tech_stack = unified_map.get("tech_stack", {})
        if tech_stack.get("languages"):
            md += f"- **编程语言**: {', '.join(tech_stack['languages'])}\n"
        if tech_stack.get("frameworks"):
            md += f"- **框架**: {', '.join(tech_stack['frameworks'])}\n"
        if tech_stack.get("databases"):
            md += f"- **数据库**: {', '.join(tech_stack['databases'])}\n"
        md += "\n"

        # 架构分层
        md += "## 架构分层\n\n"
        for layer in unified_map.get("layers", []):
            md += f"### {layer['name']}\n"
            md += f"- **描述**: {layer['description']}\n"
            md += f"- **路径**: {', '.join(layer['paths'])}\n\n"

        # 入口点
        md += "## 入口点\n\n"
        for entry in unified_map.get("entrypoints", []):
            project = entry.get("project", "unknown")
            md += f"- `{entry['path']}` ({entry['type']}) - 项目：{project}\n"
        md += "\n"

        # 跨项目依赖
        md += "## 跨项目依赖\n\n"
        cross_deps = unified_map.get("dependencies", {}).get("cross_project_deps", [])
        if cross_deps:
            for dep in cross_deps[:10]:
                md += f"- {dep['from']} -> {dep['to']}\n"
        else:
            md += "- 暂无跨项目依赖（或未分析）\n"

        return md


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="跨仓库 Monorepo 索引工具"
    )
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="配置文件路径 (JSON 格式)"
    )
    parser.add_argument(
        "--collection", "-n",
        default="monorepo_collection",
        help="统一 collection 名称"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（不指定则输出到 stdout）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="json",
        help="输出格式"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="是否增量索引"
    )

    args = parser.parse_args()

    # 创建索引器
    indexer = MonorepoIndexer(config_path=args.config)

    # 加载配置
    config = indexer.config
    repos = config.get("repos", [])
    project_name = config.get("project_name", args.collection)

    print(f"[INFO] 开始索引 Monorepo - 项目：{project_name}")
    print(f"[INFO] 仓库数：{len(repos)}")

    # 索引所有仓库
    stats = indexer.index_repos(
        repos=repos,
        collection_name=project_name,
        incremental=args.incremental
    )

    print(f"[INFO] 索引完成 - 成功：{stats['success_repos']}, 失败：{stats['failed_repos']}")

    # 生成统一地图
    unified_map = indexer.generate_unified_map(
        project_name=project_name,
        output_format=args.format
    )

    # 输出结果
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "markdown":
            content = unified_map.get("markdown", "")
        else:
            content = json.dumps(unified_map, ensure_ascii=False, indent=2)
        output_path.write_text(content, encoding="utf-8")
        print(f"[INFO] 地图已保存到：{output_path.absolute()}")
    else:
        if args.format == "markdown":
            print(unified_map.get("markdown", ""))
        else:
            print(json.dumps(unified_map, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
