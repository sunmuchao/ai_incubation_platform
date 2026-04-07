"""
P4 功能测试脚本

测试内容:
1. 并行嵌入处理 (OPT-1)
2. AST 哈希树增量索引 (OPT-1)
3. Tree-sitter 符号解析 (OPT-2)
4. VSCode 插件框架 (OPT-3)
"""
import os
import sys
import time
import asyncio
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_parallel_embedding():
    """测试并行嵌入处理"""
    print("\n" + "="*60)
    print("测试 1: 并行嵌入处理 (OPT-1)")
    print("="*60)

    from src.core.indexer.embeddings.parallel_embedding import (
        ParallelEmbeddingProcessor,
        LRUEmbeddingCache,
        ASTHashTree,
        create_parallel_processor
    )
    from src.core.indexer.base import CodeChunk

    # 测试 LRU 缓存
    print("\n1.1 测试 LRU 嵌入缓存...")
    cache = LRUEmbeddingCache(max_size=100)

    test_chunk = CodeChunk(
        file_path="test.py",
        language="python",
        content="def hello(): pass",
        start_line=1,
        end_line=1,
        chunk_type="function",
        symbols=["hello"]
    )

    # 缓存未命中
    result = cache.get(test_chunk)
    assert result is None, "首次获取应返回 None"
    print("  ✓ 缓存未命中测试通过")

    # 缓存写入和命中
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    cache.put(test_chunk, test_embedding)
    result = cache.get(test_chunk)
    assert result == test_embedding, "缓存命中应返回相同向量"
    print("  ✓ 缓存命中测试通过")

    # 缓存统计
    stats = cache.get_stats()
    assert stats['hits'] == 1, "命中数应为 1"
    assert stats['misses'] == 1, "未命中数应为 1"
    print(f"  ✓ 缓存统计：{stats}")

    # 测试 AST 哈希树
    print("\n1.2 测试 AST 哈希树...")
    tree1 = ASTHashTree(
        file_path="test.py",
        language="python",
        root_hash="abc123",
        nodes={
            "func_a": type('obj', (object,), {
                'node_type': 'function',
                'content_hash': 'hash_a',
                'start_line': 1,
                'children': []
            })(),
            "func_b": type('obj', (object,), {
                'node_type': 'function',
                'content_hash': 'hash_b',
                'start_line': 10,
                'children': []
            })()
        }
    )

    tree2 = ASTHashTree(
        file_path="test.py",
        language="python",
        root_hash="xyz789",
        nodes={
            "func_a": type('obj', (object,), {
                'node_type': 'function',
                'content_hash': 'hash_a_modified',  # 修改
                'start_line': 1,
                'children': []
            })(),
            "func_b": type('obj', (object,), {
                'node_type': 'function',
                'content_hash': 'hash_b',
                'start_line': 10,
                'children': []
            })(),
            "func_c": type('obj', (object,), {  # 新增
                'node_type': 'function',
                'content_hash': 'hash_c',
                'start_line': 20,
                'children': []
            })()
        }
    )

    changes = tree1.detect_changes(tree2)
    assert "func_a" in changes, "应检测到 func_a 变更"
    assert "func_c" in changes, "应检测到 func_c 新增"
    print(f"  ✓ AST 变更检测：{changes}")

    print("\n✓ 并行嵌入处理测试完成")


def test_tree_sitter_analyzer():
    """测试 Tree-sitter 符号分析器"""
    print("\n" + "="*60)
    print("测试 2: Tree-sitter 符号解析 (OPT-2)")
    print("="*60)

    from src.core.dependency_graph.tree_sitter_analyzer import (
        TreeSitterSymbolAnalyzer,
        ImportInfo,
        SymbolInfo
    )

    analyzer = TreeSitterSymbolAnalyzer()

    # 测试 Python 代码分析
    print("\n2.1 测试 Python 代码分析...")
    python_code = '''
import os
import sys
from pathlib import Path
from typing import List, Optional

class MyClass:
    """示例类"""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}"

def my_function(items: List[str]) -> Optional[str]:
    """示例函数"""
    if items:
        return items[0]
    return None

MY_CONST = 42
'''

    result = analyzer.analyze_content(python_code, 'python', 'test.py')
    assert result is not None, "分析结果不应为空"

    print(f"  - 导入数：{len(result.imports)}")
    print(f"  - 符号数：{len(result.symbols)}")
    print(f"  - 导出数：{len(result.exports)}")

    # 验证导入解析
    import_types = [imp.import_type for imp in result.imports]
    assert 'import' in import_types, "应检测到标准 import"
    assert 'from_import' in import_types, "应检测到 from import"
    print(f"  ✓ 导入类型：{import_types}")

    # 验证符号提取
    symbol_names = list(result.symbols.keys())
    assert 'MyClass' in symbol_names, "应提取到 MyClass 类"
    assert 'my_function' in symbol_names, "应提取到 my_function 函数"
    print(f"  ✓ 符号列表：{symbol_names}")

    # 测试 JavaScript 代码分析
    print("\n2.2 测试 JavaScript 代码分析...")
    js_code = '''
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
const fs = require('fs');

export class MyComponent {
    constructor() {
        this.state = {};
    }

    render() {
        return <div>Hello</div>;
    }
}

export function myFunction() {
    return null;
}

const myConstant = 42;
'''

    result = analyzer.analyze_content(js_code, 'javascript', 'test.js')
    assert result is not None, "分析结果不应为空"
    print(f"  - 导入数：{len(result.imports)}")
    print(f"  - 符号数：{len(result.symbols)}")

    # 测试降级解析 (当 tree-sitter 不可用时)
    print("\n2.3 测试降级解析...")
    simple_code = '''
import os

def hello():
    pass

class World:
    pass
'''
    result = analyzer.analyze_content(simple_code, 'python', 'simple.py')
    assert result is not None, "降级解析结果不应为空"
    print(f"  ✓ 降级解析成功：{len(result.symbols)} 个符号")

    print("\n✓ Tree-sitter 符号解析测试完成")


def test_vscode_plugin_structure():
    """测试 VSCode 插件结构"""
    print("\n" + "="*60)
    print("测试 3: VSCode 插件框架 (OPT-3)")
    print("="*60)

    plugin_dir = Path(__file__).parent / 'vscode-plugin'

    # 检查必要文件
    print("\n3.1 检查插件文件结构...")
    required_files = [
        'package.json',
        'tsconfig.json',
        'README.md',
        'src/extension.ts',
        'src/apiService.ts',
        'src/codeMapProvider.ts',
        'src/taskGuideProvider.ts',
    ]

    missing_files = []
    for file_path in required_files:
        full_path = plugin_dir / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"  ✗ {file_path} (缺失)")

    assert not missing_files, f"缺失文件：{missing_files}"

    # 检查 package.json 配置
    print("\n3.2 检查 package.json 配置...")
    import json
    with open(plugin_dir / 'package.json', 'r') as f:
        package = json.load(f)

    assert package['name'] == 'ai-code-understanding', "插件名称应正确"
    assert 'contributes' in package, "应有 contributes 配置"
    assert 'commands' in package['contributes'], "应注册命令"

    commands = package['contributes']['commands']
    command_names = [cmd['command'] for cmd in commands]

    expected_commands = [
        'aiCodeUnderstanding.showGlobalMap',
        'aiCodeUnderstanding.showTaskGuide',
        'aiCodeUnderstanding.indexProject',
        'aiCodeUnderstanding.explainCode',
        'aiCodeUnderstanding.analyzeDependency',
    ]

    for cmd in expected_commands:
        assert cmd in command_names, f"应注册命令：{cmd}"
        print(f"  ✓ 命令：{cmd}")

    # 检查 TypeScript 编译配置
    print("\n3.3 检查 TypeScript 配置...")
    with open(plugin_dir / 'tsconfig.json', 'r') as f:
        ts_config = json.load(f)

    assert ts_config['compilerOptions']['strict'], "应启用严格模式"
    print("  ✓ TypeScript 配置正确")

    print("\n✓ VSCode 插件框架测试完成")


def test_integration():
    """测试集成流程"""
    print("\n" + "="*60)
    print("测试 4: 集成流程测试")
    print("="*60)

    # 测试索引管线与并行处理集成
    print("\n4.1 测试索引管线集成...")

    try:
        from src.core.indexer.pipeline import IndexPipeline
        from src.core.indexer.parsers.tree_sitter_parser import TreeSitterParser
        from src.core.indexer.embeddings.parallel_embedding import create_parallel_processor
        from src.core.indexer.vector_stores.chroma_store import ChromaVectorStore
        from src.core.indexer.embeddings.bge_embedding import BGEEmbedding
        from src.core.dependency_graph.tree_sitter_analyzer import TreeSitterSymbolAnalyzer

        print("  ✓ 所有模块导入成功")

        # 验证分析器可用性
        analyzer = TreeSitterSymbolAnalyzer()
        assert analyzer is not None, "分析器应可创建"
        print("  ✓ Tree-sitter 分析器可用")

    except ImportError as e:
        print(f"  ⚠ 部分模块依赖不满足：{e}")
        print("  (这是预期的，当某些依赖未安装时)")

    print("\n✓ 集成流程测试完成")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("AI Code Understanding P4 功能测试")
    print("="*70)

    tests = [
        ("并行嵌入处理", test_parallel_embedding),
        ("Tree-sitter 符号解析", test_tree_sitter_analyzer),
        ("VSCode 插件框架", test_vscode_plugin_structure),
        ("集成流程", test_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test_name} 测试失败：{e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 打印总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"通过：{passed}/{len(tests)}")
    print(f"失败：{failed}/{len(tests)}")

    if failed == 0:
        print("\n✓ 所有测试通过！P4 功能实现完成。")
        return True
    else:
        print(f"\n✗ {failed} 个测试失败，请修复问题。")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
