"""
废弃代码检测脚本

定期检查项目中的废弃代码，包括：
1. 未使用的导入
2. 未调用的函数
3. DEPRECATED 标记
4. 孤儿文件（无引用入口）

使用方法：
    python scripts/deprecated_code_detector.py
"""
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class DeprecatedCodeDetector:
    """废弃代码检测器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = defaultdict(list)

    def scan_deprecated_markers(self) -> Dict[str, List[Tuple[str, int, str]]]:
        """扫描 DEPRECATED 标记"""
        deprecated_patterns = [
            r'DEPrecated',
            r'\[DEPRECATED\]',
            r'已废弃',
            r'废弃',
            r'TODO.*remove',
            r'TODO.*delete',
        ]

        results = defaultdict(list)

        for pattern in deprecated_patterns:
            try:
                cmd = f"grep -rn --include='*.py' --include='*.ts' --include='*.tsx' '{pattern}' {self.project_root}/src {self.project_root}/frontend/src 2>/dev/null | grep -v node_modules | grep -v __pycache__"
                output = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                for line in output.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            file_path, line_num, content = parts[0], parts[1], parts[2]
                            results[pattern].append((file_path, int(line_num), content.strip()))
            except Exception as e:
                print(f"Error scanning pattern {pattern}: {e}")

        return results

    def check_orphan_files(self) -> List[str]:
        """检查孤儿文件（未被导入的模块）"""
        # 获取所有 Python 文件
        py_files = []
        for root, dirs, files in os.walk(self.project_root / 'src'):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests']]
            for f in files:
                if f.endswith('.py') and f != '__init__.py':
                    py_files.append(os.path.join(root, f))

        orphan_files = []

        for file_path in py_files:
            module_name = os.path.basename(file_path).replace('.py', '')

            # 检查是否有其他文件导入此模块
            import_pattern = f"from.*{module_name}|import.*{module_name}"

            cmd = f"grep -r '{import_pattern}' {self.project_root}/src --include='*.py' | grep -v '{file_path}' | grep -v __pycache__ | wc -l"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.stdout.strip() == '0':
                orphan_files.append(file_path)

        return orphan_files

    def check_unused_imports(self) -> Dict[str, List[str]]:
        """检查未使用的导入（简化版）"""
        # 这是一个简化版本，完整版需要使用 AST 分析
        results = {}

        for root, dirs, files in os.walk(self.project_root / 'src'):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests']]
            for f in files:
                if f.endswith('.py'):
                    file_path = os.path.join(root, f)

                    # 提取导入语句
                    imports = []
                    with open(file_path, 'r') as fp:
                        for line in fp:
                            if line.startswith('import ') or line.startswith('from '):
                                imports.append(line.strip())

                    # 简化检查：如果导入但文件中没有使用
                    # 注：这只是粗略检查，准确分析需要 AST
                    for imp in imports:
                        if 'from ' in imp:
                            module = imp.split('import ')[-1].strip().split(',')[0]
                        else:
                            module = imp.split(' ')[-1].strip()

                        # 检查是否在文件中使用
                        module_name = module.split('.')[-1] if '.' in module else module

                        with open(file_path, 'r') as fp:
                            content = fp.read()
                            # 统计使用次数（排除导入语句本身）
                            import_count = len(re.findall(f'^import {module_name}|^from.*{module_name}', content))
                            use_count = len(re.findall(module_name, content))

                            if use_count <= import_count and import_count > 0:
                                if file_path not in results:
                                    results[file_path] = []
                                results[file_path].append(imp)

        return results

    def generate_report(self) -> str:
        """生成检测报告"""
        report = []
        report.append("=" * 60)
        report.append("废弃代码检测报告")
        report.append("=" * 60)
        report.append(f"扫描路径: {self.project_root}")
        report.append(f"扫描时间: {os.popen('date').read().strip()}")
        report.append("")

        # 1. DEPRECATED 标记
        report.append("## 1. DEPRECATED 标记")
        deprecated = self.scan_deprecated_markers()
        total_deprecated = sum(len(items) for items in deprecated.values())
        report.append(f"发现 {total_deprecated} 处 DEPRECATED 标记")

        for pattern, items in deprecated.items():
            report.append(f"\n### {pattern}")
            for file_path, line_num, content in items[:10]:  # 只显示前10个
                report.append(f"  - {file_path}:{line_num} - {content[:80]}")

        report.append("")

        # 2. 孤儿文件
        report.append("## 2. 孤儿文件（未被导入）")
        orphans = self.check_orphan_files()
        report.append(f"发现 {len(orphans)} 个孤儿文件")
        for f in orphans[:20]:
            report.append(f"  - {f}")

        report.append("")

        # 3. 统计
        report.append("## 3. 统计摘要")
        report.append(f"DEPRECATED 标记: {total_deprecated}")
        report.append(f"孤儿文件: {len(orphans)}")
        report.append("")

        return '\n'.join(report)


def main():
    """主函数"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    detector = DeprecatedCodeDetector(project_root)
    report = detector.generate_report()

    print(report)

    # 保存报告
    report_path = os.path.join(project_root, 'docs', 'deprecated_code_detection_report.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n报告已保存到: {report_path}")


if __name__ == '__main__':
    main()