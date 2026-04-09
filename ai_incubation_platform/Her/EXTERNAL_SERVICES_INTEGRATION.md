# 外部服务整合报告

## 整合概述

本次整合为 Her 红娘 Agent 项目接入了真实的外部服务，包括地理数据、推送通知、行为分析和举报系统。所有服务都支持 graceful degradation（优雅降级）——当 API 未配置时自动降级为 mock 模式，不影响开发和测试。

---

## 一、高德地图 API 整合

### 整合文件
- `integration/amap_client.py` - 高德地图 API 客户端

### 功能清单
| 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `geocode()` | 地理编码（地址→坐标） | 地址字符串 | `{"location": "经度，纬度", "formatted_address": "..."}` |
| `reverse_geocode()` | 逆地理编码（坐标→地址） | 纬度，经度 | `{"formatted_address": "...", "city": "..."}` |
| `calculate_distance()` | 距离计算 | 起点坐标，终点坐标，模式 | `{"distance": "米", "duration": "秒"}` |
| `search_places()` | 地点搜索 | 关键词，城市，半径 | 地点列表 |
| `getwalking_direction()` | 步行路线规划 | 起点坐标，终点坐标 | `{"distance": "...", "steps": [...]}` |

### 使用示例
```python
from integration.amap_client import get_amap_client

amap = get_amap_client()

# 地理编码
result = await amap.geocode("北京市朝阳区三里屯")
print(result)  # {"location": "116.455093,39.933623", ...}

# 搜索附近餐厅
places = await amap.search_places("餐厅", city="北京市", location="116.455093,39.933623", radius=1000)
```

### 已集成到的功能
- `agent/skills/geo_location_skill.py` - 地理位置技能
- `agent/skills/date_planning_skill.py` - 约会地点规划（中点计算）

### 配置方式
```bash
# .env 文件
AMAP_API_KEY=你的高德地图 API Key
AMAP_ENABLED=true
```

### API Key 获取
访问 https://lbs.amap.com/ 注册账号并创建应用获取 Key。

---

## 二、极光推送整合

### 整合文件
- `integration/jpush_client.py` - 极光推送客户端

### 功能清单
| 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `push()` | 推送通知给指定用户 | 用户 ID 列表，标题，内容，额外参数 | `{"success": true, "msg_id": "..."}` |
| `push_to_all()` | 广播推送给所有用户 | 标题，内容，额外参数 | `{"success": true}` |
| `push_sms()` | 发送短信验证码 | 手机号，模板 ID，参数 | `{"success": true, "msg_id": "..."}` |

### 使用示例
```python
from integration.jpush_client import get_jpush_client

jpush = get_jpush_client()

# 推送通知给特定用户
result = await jpush.push(
    target=["user-123"],
    title="新消息",
    content="张三给你发了一条消息",
    extras={"type": "new_message", "sender_id": "user-456"}
)

# 发送短信验证码
sms_result = await jpush.push_sms(
    mobile="13800138000",
    template_id=1,
    params=["123456"]  # 验证码
)
```

### 已集成到的功能
- `services/notification_service.py` - 推送通知服务（第 372 行）
- `services/report_service.py` - 高优先级举报管理员通知（第 181 行）

### 配置方式
```bash
# .env 文件
JPUSH_APP_KEY=你的 JPush AppKey
JPUSH_MASTER_SECRET=你的 Master Secret
JPUSH_ENABLED=true
```

### API Key 获取
访问 https://www.jiguang.cn/ 注册账号并创建应用获取 AppKey 和 Master Secret。

---

## 三、用户行为日志服务

### 整合文件
- `services/behavior_log_service.py` - 行为日志服务
- 数据库表：`user_behavior_events`, `user_behavior_daily_stats`

### 功能清单
| 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `log_event()` | 记录用户行为事件 | 用户 ID, 事件类型，事件数据 | 事件 ID |
| `get_user_behavior_history()` | 获取用户行为历史 | 用户 ID, 天数，事件类型 | 事件列表 |
| `get_user_daily_stats()` | 获取用户日统计数据 | 用户 ID, 天数 | 日统计列表 |
| `get_active_hours()` | 获取用户活跃时段 | 用户 ID, 天数 | 小时列表 [0-23] |
| `get_message_stats()` | 获取用户消息统计 | 用户 ID, 天数 | 统计数据 |

### 事件类型常量
```python
EventTypes.SWIPE = "swipe"          # 滑动
EventTypes.MESSAGE = "message"       # 发送消息
EventTypes.PROFILE_VIEW = "profile_view"  # 查看资料
EventTypes.MATCH = "match"          # 匹配成功
EventTypes.LOGIN = "login"          # 登录
EventTypes.PROFILE_UPDATE = "profile_update"  # 更新资料
```

### 使用示例
```python
from services.behavior_log_service import get_behavior_log_service

behavior_service = get_behavior_log_service(db)

# 记录滑动行为
behavior_service.log_event(
    user_id="user-123",
    event_type="swipe",
    event_data={
        "target_user_id": "user-456",
        "action": "like",
        "swipe_duration_seconds": 5,
        "viewed_sections": ["photo", "bio"]
    }
)

# 获取活跃时段
active_hours = behavior_service.get_active_hours("user-123", days=7)
print(active_hours)  # [9, 10, 14, 20, 21, 22]
```

### 已集成到的功能
- `agent/skills/omniscient_insight_skill.py` - 全知洞察技能（行为数据分析）

### 数据库初始化
```bash
python scripts/init_new_tables.py
```

---

## 四、举报服务

### 整合文件
- `services/report_service.py` - 举报服务
- 数据库表：`user_reports`

### 功能清单
| 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `create_report()` | 创建举报记录 | 举报人 ID, 被举报人 ID, 类型，原因等 | 举报记录 ID |
| `get_report()` | 获取举报详情 | 举报 ID | 举报详情字典 |
| `update_status()` | 更新举报状态 | 举报 ID, 状态，审核人，备注 | 是否成功 |
| `take_action()` | 对举报采取行动 | 举报 ID, 行动类型，详情 | 是否成功 |
| `get_pending_reports()` | 获取待审核举报 | 数量限制 | 举报列表 |
| `get_report_stats()` | 获取举报统计 | 天数 | 统计数据 |

### 举报状态流程
```
PENDING（待审核） → UNDER_REVIEW（审核中） → APPROVED（已确认） → PROCESSED（已处理）
                                         → REJECTED（已拒绝）
```

### 举报类型
- `inappropriate_content` - 不当内容
- `harassment` - 骚扰
- `fake_profile` - 虚假资料
- `spam` - 垃圾信息
- `underage` - 未成年
- `other` - 其他

### 可采取的行动
- `warning` - 警告（增加违规计数）
- `temporary_ban` - 临时封禁
- `permanent_ban` - 永久封禁
- `content_removal` - 删除内容
- `no_action` - 无需处理

### 优先级计算规则
| 举报类型 | 基础优先级 |
|---------|----------|
| underage | 5（最高） |
| harassment | 4 |
| inappropriate_content | 3 |
| fake_profile | 3 |
| spam | 2 |
| other | 1 |

**加成规则**：
- 被举报人违规次数 ≥ 3 次：优先级 +1
- 被举报人违规次数 ≥ 5 次：优先级 = 5

### 使用示例
```python
from services.report_service import get_report_service, ReportType

report_service = get_report_service(db)

# 创建举报
report_id = report_service.create_report(
    reporter_id="user-123",
    reported_user_id="user-456",
    report_type=ReportType.HARASSMENT.value,
    reason="发送不当消息",
    evidence_urls=["https://example.com/evidence.png"]
)

# 审核举报
report_service.update_status(
    report_id=report_id,
    status="approved",
    reviewed_by="admin-001",
    review_notes="确认存在骚扰行为"
)

# 采取行动
report_service.take_action(
    report_id=report_id,
    action="temporary_ban",
    action_details={"reason": "骚扰其他用户", "ban_days": 7}
)
```

### 已集成到的功能
- `services/report_service.py` - 高优先级举报自动通知管理员（使用 JPush）

### 数据库初始化
```bash
python scripts/init_new_tables.py
```

---

## 五、配置文件更新

### `.env.example` 新增配置项
```bash
# ==================== 高德地图 API 配置 ====================
AMAP_API_KEY=your_amap_api_key
AMAP_API_SECRET=your_amap_api_secret  # 可选，用于安全签名
AMAP_ENABLED=false

# ==================== 极光推送配置 ====================
JPUSH_APP_KEY=your_jpush_app_key
JPUSH_MASTER_SECRET=your_jpush_master_secret
JPUSH_ENABLED=false

# ==================== 短信服务配置（阿里云） ====================
ALIYUN_SMS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_SMS_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_SMS_SIGN_NAME=你的签名名称
ALIYUN_SMS_TEMPLATE_CODE=SMS_123456789
ALIYUN_SMS_ENABLED=false

# ==================== 支付配置 ====================
WECHAT_PAY_APPID=your_wechat_pay_appid
WECHAT_PAY_MCHID=your_wechat_pay_mchid
WECHAT_PAY_API_V3_KEY=your_wechat_pay_api_v3_key
WECHAT_PAY_SERIAL_NO=your_wechat_pay_serial_no
WECHAT_PAY_ENABLED=false

ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=your_alipay_private_key
ALIPAY_PUBLIC_KEY=your_alipay_public_key
ALIPAY_ENABLED=false
```

---

## 六、快速开始

### 1. 获取 API Key
- 高德地图：https://lbs.amap.com/
- 极光推送：https://www.jiguang.cn/

### 2. 复制并重命名配置文件
```bash
cd Her
cp .env.example .env
```

### 3. 编辑 `.env` 文件
```bash
# 修改以下配置
AMAP_API_KEY=你的密钥
AMAP_ENABLED=true

JPUSH_APP_KEY=你的密钥
JPUSH_MASTER_SECRET=你的密钥
JPUSH_ENABLED=true
```

### 4. 初始化数据库表
```bash
python scripts/init_new_tables.py
```

### 5. 启动服务
```bash
python src/main.py
```

---

## 七、Mock 模式说明

所有外部服务在以下情况会自动降级为 mock 模式：
1. 对应的 `*_ENABLED=false`
2. 对应的 API Key 未配置

**Mock 模式行为**：
- `AMapClient`：返回固定的北京中心点坐标和模拟地址
- `JPushClient`：记录日志但不实际发送推送
- `BehaviorLogService`：正常写入数据库（不依赖外部 API）
- `ReportService`：正常写入数据库（不依赖外部 API）

**开发建议**：
- 开发阶段可以使用 mock 模式
- 生产环境必须配置真实的 API Key 并设置 `*_ENABLED=true`

---

## 八、API 使用限制和计费

### 高德地图
- **免费额度**：个人开发者每日 2 万次调用
- **超出计费**：0.004 元/次
- **QPS 限制**：个人版 50 次/秒
- 文档：https://lbs.amap.com/api/webservice/guide/tools/quota

### 极光推送
- **免费版**：推送通知免费
- **短信验证码**：0.035 元/条
- **文档**：https://docs.jiguang.cn/

### 建议
- 在代码中实现缓存机制减少重复调用
- 对于地理位置等不频繁变化的数据，可以缓存 24 小时
- 批量操作时使用批量 API 减少调用次数

---

## 九、安全注意事项

### 1. API Key 保护
- ❌ 禁止将 `.env` 文件提交到 Git
- ✅ 使用环境变量或配置文件管理密钥
- ✅ 定期轮换密钥

### 2. 敏感信息脱敏
- 日志中不记录完整的用户 ID、手机号
- 举报详情中的证据 URL 需要鉴权访问

### 3. 限流和防滥用
- 对举报接口实施限流（防止恶意举报）
- 对推送通知实施频率控制（防止骚扰）

---

## 十、后续扩展建议

### 待整合的服务（可选）
1. **阿里云短信服务** - 用于验证码、通知短信
2. **微信支付** - 会员订阅、虚拟商品购买
3. **支付宝** - 支付渠道备选
4. **对象存储（OSS）** - 用户头像、照片存储
5. **内容审核 API** - 用户头像、资料的自动审核

### 整合优先级建议
| 服务 | 优先级 | 原因 |
|------|-------|------|
| 高德地图 | 已完成 | 约会地点规划必需 |
| 极光推送 | 已完成 | 用户通知、活跃度提升 |
| 阿里云短信 | 中 | 验证码、重要通知 |
| 微信支付 | 低 | 商业模式未确定 |
| 对象存储 | 中 | 图片管理优化 |
