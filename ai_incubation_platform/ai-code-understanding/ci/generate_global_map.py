#!/usr/bin/env python3
"""
CI 脚本：生成全局地图产物并导出为 Markdown/JSON

用途：
1. CI/CD 流水线中自动生成项目地图
2. 定时任务更新项目文档
3. 手动触发重新生成地图

使用方式：
    # 生成 Markdown 格式（用于文档）
    python ci/generate_global_map.py --project my_project --repo /path/to/repo --format markdown --output docs/global-map.md

    # 生成 JSON 格式（用于程序消费）
    python ci/generate_global_map.py --project my_project --repo /path/to/repo --format json --output data/global-map.json

    # 定时任务示例（crontab）
    0 2 * * * cd /path/to/ai-code-understanding && python ci/generate_global_map.py --project my_project --repo /path/to/repo --format markdown --output docs/global-map.md
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.understanding_service import understanding_service


def generate_global_map(
    project_name: str,
    repo_path: str,
    output_format: str = "markdown",
    output_file: str = None,
    regenerate: bool = False,
    stack_hint: str = None
) -> dict:
    """生成全局地图并输出到文件"""

    print(f"[INFO] 开始生成全局地图 - 项目：{project_name}")
    print(f"[INFO] 仓库路径：{repo_path}")
    print(f"[INFO] 输出格式：{output_format}")

    # 调用服务生成地图
    result = understanding_service.global_map(
        project_name=project_name,
        repo_hint=repo_path,
        stack_hint=stack_hint,
        regenerate=regenerate,
        format=output_format
    )

    if "error" in result:
        print(f"[ERROR] 生成失败：{result['error']}")
        return {"success": False, "error": result["error"]}

    # 确定输出内容
    if output_format == "markdown":
        content = result.get("markdown", "")
        if not content:
            # 如果是 markdown 格式但没有 markdown 字段，尝试手动转换
            content = _convert_to_markdown(result)
    else:
        content = json.dumps(result, ensure_ascii=False, indent=2)

    # 输出到文件
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"[INFO] 地图已保存到：{output_path.absolute()}")
    else:
        # 输出到 stdout
        print(content)

    return {
        "success": True,
        "project": project_name,
        "output_file": output_file,
        "format": output_format,
        "generated_at": datetime.now().isoformat(),
        "layers_count": len(result.get("layers", [])),
        "entrypoints_count": len(result.get("entrypoints", [])),
    }


def _convert_to_markdown(data: dict) -> str:
    """将 JSON 数据转换为 Markdown 格式"""
    md = f"# 项目全局地图：{data.get('project', 'Unknown')}\n\n"
    md += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    md += f"> 仓库路径：{data.get('repo_path', 'N/A')}\n\n"

    # 技术栈
    tech_stack = data.get("tech_stack", {})
    if tech_stack:
        md += "## 技术栈\n\n"
        if tech_stack.get("languages"):
            md += f"- **编程语言**: {', '.join(tech_stack['languages'])}\n"
        if tech_stack.get("frameworks"):
            md += f"- **框架**: {', '.join(tech_stack['frameworks'])}\n"
        if tech_stack.get("databases"):
            md += f"- **数据库**: {', '.join(tech_stack['databases'])}\n"
        md += "\n"

    # 架构分层
    layers = data.get("layers", [])
    if layers:
        md += "## 架构分层\n\n"
        for layer in layers:
            md += f"### {layer.get('name', 'Unknown')}\n"
            md += f"- **描述**: {layer.get('description', 'N/A')}\n"
            md += f"- **职责**: {', '.join(layer.get('responsibilities', []))}\n"
            md += f"- **路径**: {', '.join(layer.get('paths', []))}\n\n"

    # 入口点
    entrypoints = data.get("entrypoints", [])
    if entrypoints:
        md += "## 入口点\n\n"
        for entry in entrypoints:
            md += f"- `{entry.get('path', 'N/A')}` ({entry.get('type', 'N/A')})\n"
        md += "\n"

    return md


def main():
    parser = argparse.ArgumentParser(
        description="生成项目全局地图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 生成 Markdown 格式
    python ci/generate_global_map.py --project my_project --repo /path/to/repo --format markdown --output docs/global-map.md

    # 生成 JSON 格式
    python ci/generate_global_map.py --project my_project --repo /path/to/repo --format json --output data/global-map.json

    # 强制重新生成
    python ci/generate_global_map.py --project my_project --repo /path/to/repo --regenerate
        """
    )

    parser.add_argument(
        "--project", "-p",
        required=True,
        help="项目名称"
    )
    parser.add_argument(
        "--repo", "-r",
        required=True,
        help="仓库路径"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（不指定则输出到 stdout）"
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="强制重新生成，忽略缓存"
    )
    parser.add_argument(
        "--stack", "-s",
        help="技术栈提示，如 Python+FastAPI、Node+React"
    )

    args = parser.parse_args()

    result = generate_global_map(
        project_name=args.project,
        repo_path=args.repo,
        output_format=args.format,
        output_file=args.output,
        regenerate=args.regenerate,
        stack_hint=args.stack
    )

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
