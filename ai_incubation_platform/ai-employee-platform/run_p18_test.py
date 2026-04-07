import os
import sys

# 设置环境变量（必须在导入任何其他模块之前）
os.environ['ENVIRONMENT'] = 'development'
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing-purposes-only-123456789'
os.environ['DATABASE_URL'] = 'sqlite:///./test_p18.db'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000'

# 运行测试
import test_p18_features
test_p18_features.unittest.main(verbosity=2)
