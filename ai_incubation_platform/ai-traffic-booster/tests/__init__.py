"""
测试配置和工具
"""
import pytest
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
