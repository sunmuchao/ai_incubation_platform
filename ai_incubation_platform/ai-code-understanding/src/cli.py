#!/usr/bin/env python3
"""
AI 代码理解助手 - 命令行工具
提供便捷的 API 调用接口，支持所有核心功能
"""
import os
import sys
import json
import click
import requests
from typing import Optional, List
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 默认配置
DEFAULT_CONFIG = {
    "base_url": "http://localhost:8011",
    "timeout": 60,
    "output_format": "markdown"
}

CONFIG_FILE = Path.home() / ".ai_code_understanding_config.json"


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return {**DEFAULT_CONFIG, **config}
    return DEFAULT_CONFIG


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_api_url(endpoint: str) -> str:
    """获取完整的 API URL"""
    config = load_config()
    base_url = config.get("base_url", DEFAULT_CONFIG["base_url"]).rstrip("/")
    return f"{base_url}/api/understanding/{endpoint}"


def make_request(endpoint: str, data: dict) -> dict:
    """发送 API 请求"""
    config = load_config()
    url = get_api_url(endpoint)
    timeout = config.get("timeout", DEFAULT_CONFIG["timeout"])

    try:
        response = requests.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        click.echo(click.style("错误：无法连接到 API 服务", fg="red"))
        click.echo(f"请确保服务运行在 {url}")
        click.echo("启动命令：python src/main.py")
        sys.exit(1)
    except requests.exceptions.Timeout:
        click.echo(click.style("错误：请求超时", fg="red"))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"错误：{str(e)}", fg="red"))
        sys.exit(1)


def format_output(response: dict, output_format: str = "markdown"):
    """格式化输出"""
    if output_format == "json":
        click.echo(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        # 使用 output_formatter 进行 Markdown 格式化
        try:
            from tools.output_formatter import OutputFormatter, Visualizer
            formatter = OutputFormatter()
            markdown = formatter.format_response(response)
            markdown = OutputFormatter.add_timestamp(markdown)
            click.echo(markdown)
        except ImportError:
            # 降级到简单输出
            click.echo("\n## 响应结果\n")
            for key, value in response.items():
                if isinstance(value, str):
                    click.echo(f"**{key}**: {value}\n")
            click.echo(json.dumps(response, indent=2, ensure_ascii=False))


@click.group()
@click.version_option(version="0.5.0", prog_name="ai-code-understanding")
def cli():
    """AI 代码理解助手 - 命令行工具

    提供便捷的 API 调用接口，支持以下功能：

    \b
    - explain: 代码片段解释
    - summarize: 模块摘要
    - ask: 代码库问答
    - global-map: 全局地图
    - task-guide: 任务引导
    - index-project: 项目索引
    - dependency-graph: 依赖关系图
    - analyze-impact: 变更影响分析
    """
    pass


@cli.command()
@click.option("--code", "-c", required=True, help="待解释的代码片段")
@click.option("--language", "-l", default="python", help="编程语言 (默认：python)")
@click.option("--context", help="额外上下文")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def explain(code, language, context, output_format):
    """解释代码片段"""
    data = {
        "code": code,
        "language": language,
        "context": context
    }
    response = make_request("explain", data)
    format_output(response, output_format)


@cli.command()
@click.option("--module", "module_name", required=True, help="模块或路径标识")
@click.option("--symbol", "-s", multiple=True, help="关心的符号列表（可多次指定）")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def summarize(module_name, symbol, output_format):
    """生成模块摘要"""
    data = {
        "module_name": module_name,
        "symbols": list(symbol) if symbol else None
    }
    response = make_request("summarize", data)
    format_output(response, output_format)


@cli.command()
@click.option("--question", "-q", required=True, help="关于代码库的自然语言问题")
@click.option("--scope", multiple=True, help="限定检索的目录或文件（可多次指定）")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def ask(question, scope, output_format):
    """代码库问答"""
    data = {
        "question": question,
        "scope_paths": list(scope) if scope else None
    }
    response = make_request("ask", data)
    format_output(response, output_format)


@cli.command()
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--repo", "-r", required=True, help="仓库路径")
@click.option("--stack", help="技术栈提示（如 Python+FastAPI）")
@click.option("--regenerate", is_flag=True, help="强制重新生成")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def global_map(project, repo, stack, regenerate, output_format):
    """生成项目全局地图"""
    data = {
        "project_name": project,
        "repo_hint": repo,
        "stackhint": stack,
        "regenerate": regenerate,
        "format": "json"
    }
    response = make_request("global-map", data)

    if output_format == "markdown" and "markdown" in response:
        click.echo(response["markdown"])
    else:
        format_output(response, output_format)


@cli.command()
@click.option("--task", "-t", required=True, help="任务描述")
@click.option("--path", multiple=True, help="已知的模块路径（可多次指定）")
@click.option("--project", "-p", help="项目名称")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def task_guide(task, path, project, output_format):
    """生成任务引导路径"""
    data = {
        "task_description": task,
        "optional_paths": list(path) if path else None,
        "project_name": project
    }
    response = make_request("task-guide", data)
    format_output(response, output_format)


@cli.command()
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--repo", "-r", required=True, help="仓库路径")
@click.option("--incremental", is_flag=True, default=True, help="增量索引（默认开启）")
def index_project(project, repo, incremental):
    """索引项目代码"""
    data = {
        "project_name": project,
        "repo_path": repo,
        "incremental": incremental
    }
    click.echo(f"开始索引项目：{project}")
    click.echo(f"仓库路径：{repo}")
    click.echo(f"增量索引：{'是' if incremental else '否'}")
    click.echo()
    response = make_request("index-project", data)

    if response.get("success"):
        click.echo(click.style("✓ 索引完成", fg="green"))
        stats = response.get("stats", {})
        if stats:
            click.echo(f"  索引文件数：{stats.get('indexed_files', 0)}")
            click.echo(f"  索引符号数：{stats.get('indexed_symbols', 0)}")
            click.echo(f"  索引分块数：{stats.get('indexed_chunks', 0)}")
    else:
        click.echo(click.style(f"✗ 索引失败：{response.get('error')}", fg="red"))


@cli.command()
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--repo", "-r", required=True, help="项目根目录")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json", "dot"]))
def dependency_graph(project, repo, output_format):
    """生成依赖关系图"""
    data = {
        "project_name": project,
        "repo_path": repo,
        "output_format": "dot" if output_format == "dot" else "json"
    }
    response = make_request("dependency-graph", data)

    if output_format == "dot" and "dot" in response:
        click.echo(response["dot"])
    elif output_format == "markdown":
        try:
            from tools.output_formatter import Visualizer
            visualizer = Visualizer()
            click.echo(visualizer.generate_dependency_graph_text(response))
        except ImportError:
            format_output(response, "json")
    else:
        format_output(response, output_format)


@cli.command()
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--repo", "-r", required=True, help="项目根目录")
@click.option("--base", default="HEAD~1", help="基准 commit (默认：HEAD~1)")
@click.option("--target", default="HEAD", help="目标 commit (默认：HEAD)")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def analyze_impact(project, repo, base, target, output_format):
    """分析代码变更影响"""
    data = {
        "project_name": project,
        "repo_path": repo,
        "base": base,
        "target": target
    }
    click.echo(f"分析变更影响：{project}")
    click.echo(f"变更范围：{base} -> {target}")
    click.echo()
    response = make_request("analyze-change-impact", data)
    format_output(response, output_format)


@cli.command()
@click.option("--file", "file_path", required=True, help="文件路径")
@click.option("--symbol", "-s", help="符号名称（不提供则返回所有符号）")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def resolve_symbols(file_path, symbol, output_format):
    """解析文件符号"""
    data = {
        "file_path": file_path,
        "symbol_name": symbol
    }
    response = make_request("resolve-symbols", data)
    format_output(response, output_format)


@cli.command()
@click.option("--project", "-p", required=True, help="项目名称")
@click.option("--repo", "-r", required=True, help="项目根目录")
@click.option("--symbol", "-s", required=True, help="符号名称")
@click.option("--scope", multiple=True, help="搜索范围（可多次指定）")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def find_references(project, repo, symbol, scope, output_format):
    """查找符号引用"""
    data = {
        "project_name": project,
        "repo_path": repo,
        "symbol_name": symbol,
        "scope_paths": list(scope) if scope else None
    }
    response = make_request("find-symbol-references", data)
    format_output(response, output_format)


@cli.group()
def config():
    """配置管理"""
    pass


@config.command()
@click.option("--base-url", help="API 服务地址")
@click.option("--timeout", type=int, help="请求超时时间（秒）")
def set(base_url, timeout):
    """设置配置项"""
    current = load_config()
    if base_url:
        current["base_url"] = base_url
    if timeout:
        current["timeout"] = timeout
    save_config(current)
    click.echo("配置已保存:")
    for key, value in current.items():
        click.echo(f"  {key}: {value}")


@config.command()
def show():
    """显示当前配置"""
    config = load_config()
    click.echo("当前配置:")
    for key, value in config.items():
        click.echo(f"  {key}: {value}")


@config.command()
def reset():
    """重置为默认配置"""
    save_config(DEFAULT_CONFIG)
    click.echo("配置已重置为默认值")


@cli.command()
def templates():
    """显示快捷指令模板"""
    templates = {
        "Cursor 快捷指令": {
            "解释选中代码": "/explain {{selected_code}}",
            "生成模块摘要": "/summarize {{current_file}}",
            "项目问答": "/ask {{question}}",
            "查看全局地图": "/global-map {{project_name}}",
            "获取任务引导": "/task-guide {{task_description}}"
        },
        "Claude Code 工作流": {
            "新项目上手": "1. 生成全局地图\n2. 阅读 README\n3. 识别核心模块\n4. 创建任务引导",
            "任务开发": "1. 获取阅读路径\n2. 理解相关模块\n3. 实现功能\n4. 分析变更影响",
            "代码审查": "1. 解析符号\n2. 查找引用\n3. 生成依赖图\n4. 评估影响范围"
        }
    }

    click.echo("# 📋 快捷指令模板\n")
    for category, commands in templates.items():
        click.echo(f"## {category}\n")
        for name, description in commands.items():
            click.echo(f"### {name}")
            if isinstance(description, str) and description.startswith("/"):
                click.echo(f"```\n{description}\n```")
            else:
                click.echo(f"{description}\n")
        click.echo()


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
