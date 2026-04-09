# 安全与性能测试用例总结

本文档总结了为 Her (红娘 Agent) 项目补充的完整安全测试用例和性能测试用例。

## 测试文件位置

- **安全测试**: `tests/test_security.py`
- **性能测试**: `tests/test_performance.py`

## 安全测试用例覆盖 (test_security.py)

### 1. 认证与授权安全 (Authentication & Authorization)

| 测试项 | 描述 |
|-------|------|
| `test_login_invalid_credentials` | 测试无效凭证登录失败 |
| `test_login_nonexistent_user` | 测试不存在的用户登录失败 |
| `test_token_expiration` | 测试令牌过期验证 |
| `test_token_invalid_signature` | 测试无效签名令牌被拒绝 |
| `test_malformed_token_rejected` | 测试格式错误的令牌被拒绝 |
| `test_empty_token_rejected` | 测试空令牌被拒绝 |
| `test_missing_auth_header` | 测试缺少认证头被拒绝 |
| `test_bearer_prefix_required` | 测试必须使用 Bearer 前缀 |
| `test_user_can_only_access_own_profile` | 测试用户只能访问自己的资料 |
| `test_admin_can_access_other_profiles` | 测试管理员可以访问其他用户资料 |
| `test_non_admin_cannot_access_admin_endpoints` | 测试非管理员无法访问管理员接口 |

### 2. 输入验证与注入防护 (Input Validation)

| 测试项 | 描述 |
|-------|------|
| `test_sql_injection_in_email` | 测试 SQL 注入防护 - 邮箱字段 |
| `test_sql_injection_in_user_id` | 测试 SQL 注入防护 - 用户 ID 字段 |
| `test_xss_script_injection` | 测试 XSS 脚本注入防护 |
| `test_path_traversal_attack` | 测试路径遍历攻击防护 |
| `test_command_injection` | 测试命令注入防护 |
| `test_integer_overflow` | 测试整数溢出防护 |
| `test_wrong_content_type` | 测试错误的 Content-Type 被拒绝 |

### 3. 数据隐私与脱敏 (Data Privacy)

| 测试项 | 描述 |
|-------|------|
| `test_password_not_exposed_in_response` | 测试密码不在响应中暴露 |
| `test_sensitive_data_masking` | 测试敏感数据脱敏 |
| `test_internal_ids_not_exposed` | 测试内部 ID 不暴露给外部 |

### 4. 速率限制与 DoS 防护 (Rate Limiting & DoS)

| 测试项 | 描述 |
|-------|------|
| `test_login_rate_limiting` | 测试登录接口速率限制 |
| `test_api_rate_limiting` | 测试通用 API 速率限制 |
| `test_large_payload_rejected` | 测试大负载被拒绝 |
| `test_deep_json_nesting_rejected` | 测试深层 JSON 嵌套被拒绝 |
| `test_regex_dos_protection` | 测试正则表达式 DoS 防护 |

### 5. 会话安全 (Session Security)

| 测试项 | 描述 |
|-------|------|
| `test_token_invalidated_after_logout` | 测试令牌在登出后失效 |
| `test_concurrent_session_limit` | 测试并发会话限制 |

### 6. 文件上传安全 (File Upload Security)

| 测试项 | 描述 |
|-------|------|
| `test_non_image_file_rejected` | 测试非图片文件被拒绝 |
| `test_file_extension_validation` | 测试文件扩展名验证 |
| `test_file_size_limit` | 测试文件大小限制 |

### 7. API 安全 (API Security)

| 测试项 | 描述 |
|-------|------|
| `test_cors_headers` | 测试 CORS 头配置 |
| `test_security_headers` | 测试安全响应头 |
| `test_error_messages_not_expose_internal` | 测试错误信息不暴露内部细节 |
| `test_enum_injection` | 测试枚举注入防护 |

### 8. 业务逻辑安全 (Business Logic Security)

| 测试项 | 描述 |
|-------|------|
| `test_user_cannot_match_with_themselves` | 测试用户不能与自己匹配 |
| `test_age_preference_violation` | 测试年龄偏好违规防护 |
| `test_blocked_user_cannot_match` | 测试被屏蔽用户无法匹配 |
| `test_safety_report_must_be_valid` | 测试安全举报必须有效 |
| `test_duplicate_safety_report_handling` | 测试重复举报处理 |

### 9. 安全内容检测 (Safety Content Detection)

| 测试项 | 描述 |
|-------|------|
| `test_harassment_keywords_detection` | 测试骚扰关键词检测 |
| `test_scam_keywords_detection` | 测试诈骗关键词检测 |
| `test_inappropriate_content_detection` | 测试不当内容检测 |
| `test_spam_pattern_detection` | 测试垃圾信息模式检测 |
| `test_content_safety_check_comprehensive` | 测试内容安全检查综合 |

### 10. 安全配置检查 (Security Configuration)

| 测试项 | 描述 |
|-------|------|
| `test_jwt_secret_is_strong` | 测试 JWT 密钥强度 |
| `test_debug_mode_disabled_in_prod` | 测试生产环境禁用调试模式 |
| `test_database_url_not_hardcoded` | 测试数据库 URL 不硬编码 |

## 性能测试用例覆盖 (test_performance.py)

### 1. API 响应时间测试 (API Response Time)

| 测试项 | 描述 | 阈值 |
|-------|------|------|
| `test_login_response_time` | 测试登录接口响应时间 | P95 < 2500ms |
| `test_get_candidates_response_time` | 测试获取候选人接口响应时间 | P95 < 1500ms |
| `test_chat_send_response_time` | 测试发送消息接口响应时间 | P95 < 1000ms |
| `test_safety_check_response_time` | 测试安全检查接口响应时间 | P95 < 500ms |

### 2. 数据库查询性能测试 (Database Query Performance)

| 测试项 | 描述 | 阈值 |
|-------|------|------|
| `test_user_lookup_performance` | 测试用户查询性能 | 平均 < 100ms |
| `test_filtered_user_query_performance` | 测试带过滤条件的用户查询性能 | < 200ms |
| `test_message_query_with_pagination` | 测试分页查询性能 | 平均 < 300ms |

### 3. 并发负载测试 (Concurrent Load)

| 测试项 | 描述 | 要求 |
|-------|------|------|
| `test_concurrent_login_load` | 测试并发登录负载 | 成功率 >= 95% |
| `test_concurrent_api_load` | 测试并发 API 负载 | 成功率 >= 90% |
| `test_concurrent_message_send` | 测试并发发送消息 | 成功率 >= 95% |

### 4. 匹配算法性能测试 (Matching Algorithm Performance)

| 测试项 | 描述 | 阈值 |
|-------|------|------|
| `test_matching_performance_small_dataset` | 测试小数据集匹配性能 | < 200ms |
| `test_matching_performance_large_dataset` | 测试大数据集匹配性能 | < 1000ms |
| `test_compatibility_score_performance` | 测试兼容性计算性能 | 平均 < 10ms |

### 5. 内存和资源测试 (Memory and Resources)

| 测试项 | 描述 | 要求 |
|-------|------|------|
| `test_no_memory_leak_in_loop` | 测试循环请求无内存泄漏 | 对象增长 < 50% |
| `test_database_connection_cleanup` | 测试数据库连接清理 | 所有连接正确关闭 |

### 6. 批量操作性能测试 (Bulk Operations)

| 测试项 | 描述 | 阈值 |
|-------|------|------|
| `test_bulk_user_creation` | 测试批量创建用户性能 | 100 用户 < 1000ms |
| `test_bulk_message_insert` | 测试批量插入消息性能 | 500 消息 < 2000ms |
| `test_bulk_behavior_event_log` | 测试批量记录行为事件性能 | 200 事件 < 1000ms |

### 7. 缓存性能测试 (Cache Performance)

| 测试项 | 描述 | 要求 |
|-------|------|------|
| `test_cache_hit_performance` | 测试缓存命中性能 | 命中时间 < 未命中时间 10% |
| `test_cache_invalidation_performance` | 测试缓存失效性能 | 1000 缓存失效 < 50ms |

### 8. 长链路调用性能测试 (Long Chain Call Performance)

| 测试项 | 描述 | 阈值 |
|-------|------|------|
| `test_full_match_flow_performance` | 测试完整匹配流程性能 | < 2000ms |
| `test_chat_full_flow_performance` | 测试完整聊天流程性能 | 10 条消息 < 3000ms |

### 9. 压力测试 (Stress Test)

| 测试项 | 描述 | 要求 |
|-------|------|------|
| `test_sustained_load_performance` | 测试持续负载性能 | 性能退化 < 50% |
| `test_peak_load_handling` | 测试峰值负载处理 | < 30s |

### 10. 性能基准测试 (Performance Benchmarks)

| 测试项 | 描述 |
|-------|------|
| `test_benchmark_api_response_times` | API 响应时间基准测试 (avg, p50, p95, p99) |

## 运行测试

### 运行安全测试
```bash
cd Her

# 运行所有安全测试
python -m pytest tests/test_security.py -v

# 运行特定类别的安全测试
python -m pytest tests/test_security.py::TestAuthenticationSecurity -v
python -m pytest tests/test_security.py::TestInputValidation -v
python -m pytest tests/test_security.py::TestDataPrivacy -v
python -m pytest tests/test_security.py::TestRateLimiting -v
python -m pytest tests/test_security.py::TestFileUploadSecurity -v
python -m pytest tests/test_security.py::TestAPISecurity -v
python -m pytest tests/test_security.py::TestBusinessLogicSecurity -v
python -m pytest tests/test_security.py::TestSafetyContentDetection -v
python -m pytest tests/test_security.py::TestSecurityConfiguration -v
```

### 运行性能测试
```bash
cd Her

# 运行所有性能测试
python -m pytest tests/test_performance.py -v

# 运行特定类别的性能测试
python -m pytest tests/test_performance.py::TestAPIResponseTime -v
python -m pytest tests/test_performance.py::TestDatabaseQueryPerformance -v
python -m pytest tests/test_performance.py::TestConcurrentLoad -v
python -m pytest tests/test_performance.py::TestMatchingAlgorithmPerformance -v
python -m pytest tests/test_performance.py::TestBulkOperations -v
python -m pytest tests/test_performance.py::TestStressTest -v
python -m pytest tests/test_performance.py::TestPerformanceBenchmarks -v
```

### 查看测试覆盖率
```bash
cd Her

# 运行测试并生成覆盖率报告
python -m pytest tests/test_security.py tests/test_performance.py --cov=src --cov-report=html

# 在浏览器中打开覆盖率报告
open htmlcov/index.html
```

## 测试配置说明

### 性能阈值配置
在 `tests/test_performance.py` 中的 `PerformanceConfig` 类可以配置性能阈值：

```python
class PerformanceConfig:
    # 响应时间阈值（毫秒）
    API_RESPONSE_P95_MS = 500  # P95 响应时间
    API_RESPONSE_P99_MS = 1000  # P99 响应时间
    DB_QUERY_MS = 100  # 数据库查询时间
    MATCHING_ALGORITHM_MS = 200  # 匹配算法时间

    # 并发配置
    CONCURRENT_USERS = 10  # 并发用户数
    REQUESTS_PER_USER = 20  # 每用户请求数

    # 数据量配置
    BATCH_SIZE = 100  # 批量操作大小
    LARGE_DATASET_SIZE = 1000  # 大数据集大小
```

### 测试数据库
测试使用独立的 SQLite 内存数据库 (`sqlite:///./test_security.db` 和 `sqlite:///./test_performance.db`)，不会影响生产数据。

## 测试用例统计

| 测试文件 | 测试类别数 | 总测试用例数 (预估) |
|---------|----------|------------------|
| test_security.py | 10 | 60+ |
| test_performance.py | 10 | 40+ |
| **总计** | **20** | **100+** |

## 后续改进建议

1. **增加 LLM 集成测试**: 当 LLM 真实集成后，增加 AI 响应时间和准确性测试
2. **增加端到端安全测试**: 模拟真实攻击场景的渗透测试
3. **增加负载测试**: 使用 Locust 或 JMeter 进行更复杂的负载测试
4. **持续集成**: 将安全和性能测试纳入 CI/CD 流程
5. **性能基线**: 建立性能基线并跟踪性能退化

## 注意事项

1. 某些测试（如速率限制）取决于实际配置，可能需要根据生产环境配置调整预期
2. 性能测试的阈值应该根据实际业务需求和服务器性能进行调整
3. 安全测试中的某些测试（如 SQL 注入）依赖于 ORM 框架的内置保护
4. 建议定期运行这些测试，特别是在重大代码更改后

## 相关文档

- [项目主文档](./README.md)
- [AI Native 架构增强报告](./AI_NATIVE_ENHANCEMENT_REPORT.md)
- [产品路线图](./PRODUCT_ROADMAP.md)
