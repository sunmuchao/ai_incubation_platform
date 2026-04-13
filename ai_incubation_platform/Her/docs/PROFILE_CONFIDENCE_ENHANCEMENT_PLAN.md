# 用户置信度评估系统 - 进一步细化方案

> **版本**: v1.31.0 规划
> **目标**: 从基础框架演进为智能可信度判断系统

---

## 一、交叉验证规则扩展

### 1.1 新增验证规则

#### 规则四：兴趣-浏览一致性验证

```python
# 用户声称的兴趣 vs 实际浏览行为
INTEREST_BROWSE_MAPPING = {
    "旅行": ["travel", "outdoor", "photography", "风景"],
    "摄影": ["photography", "camera", "风景", "艺术"],
    "美食": ["food", "cooking", "餐厅", "咖啡"],
    "运动": ["sports", "fitness", "健身", "户外"],
    "阅读": ["books", "reading", "文学", "知识"],
    "音乐": ["music", "concert", "演唱会", "乐器"],
}

# 计算逻辑
def validate_interest_browse_consistency(user_id, db):
    # 获取用户声称的兴趣
    claimed_interests = json.loads(user.interests or "[]")
    
    # 获取用户浏览行为统计（最近30天）
    browse_stats = db.query(BehaviorEventDB).filter(
        BehaviorEventDB.user_id == user_id,
        BehaviorEventDB.event_type == "profile_view",
        BehaviorEventDB.created_at >= datetime.now() - timedelta(days=30)
    ).all()
    
    # 统计浏览目标的兴趣标签
    actual_browse_tags = {}
    for event in browse_stats:
        target_user = get_user(event.target_id)
        for interest in target_user.interests:
            actual_browse_tags[interest] = actual_browse_tags.get(interest, 0) + 1
    
    # 计算匹配率
    matched_interests = []
    for claimed in claimed_interests:
        expected_tags = INTEREST_BROWSE_MAPPING.get(claimed, [claimed])
        if any(tag in actual_browse_tags for tag in expected_tags):
            matched_interests.append(claimed)
    
    match_rate = len(matched_interests) / len(claimed_interests) if claimed_interests else 0
    
    # 异常判断
    if match_rate < 0.3:  # 少于30%匹配
        return {"valid": False, "severity": "medium", "match_rate": match_rate}
    
    return {"valid": True, "match_rate": match_rate}
```

#### 规则五：年龄-自报一致性验证

```python
# 通过聊天内容推断用户真实年龄段
def validate_age_self_declared(user_id, db):
    # 获取用户聊天记录（最近30天）
    messages = db.query(ChatMessageDB).filter(
        ChatMessageDB.sender_id == user_id,
        ChatMessageDB.created_at >= datetime.now() - timedelta(days=30)
    ).limit(100).all()
    
    # 使用 LLM 分析语言风格推断年龄段
    # 年轻人特征：网络用语、表情包、流行梗
    # 中年人特征：正式表达、职场话题、家庭话题
    
    inferred_age_bracket = analyze_age_from_text(messages)
    # inferred_age_bracket: "young" (18-25), "young_adult" (25-35), "middle" (35-45), "senior" (45+)
    
    # 对比声称年龄
    claimed_age = user.age
    age_bracket_map = {
        "young": (18, 25),
        "young_adult": (25, 35),
        "middle": (35, 45),
        "senior": (45, 60),
    }
    
    expected_range = age_bracket_map.get(inferred_age_bracket, (18, 60))
    
    if claimed_age < expected_range[0] - 5 or claimed_age > expected_range[1] + 5:
        return {"valid": False, "severity": "medium", 
                "inferred_bracket": inferred_age_bracket, "claimed_age": claimed_age}
    
    return {"valid": True}
```

#### 规则六：照片-画像风格一致性验证

```python
# 分析用户照片风格与声称性格的一致性
def validate_photo_personality_consistency(user_id, db):
    # 获取用户照片
    photos = db.query(PhotoDB).filter(PhotoDB.user_id == user_id).limit(5).all()
    
    # 使用 AI 分析照片风格
    # - 正式/职业风格 → 性格："serious", "professional"
    # - 活泼/户外风格 → 性格："outgoing", "active"
    # - 文艺/安静风格 → 性格："introvert", "artistic"
    
    photo_style = analyze_photo_style(photos)
    
    # 获取用户声称的性格
    personality = json.loads(user.personality or "{}")
    claimed_style = personality.get("social_style", "unknown")  # outgoing/introvert/balanced
    
    # 风格匹配矩阵
    STYLE_PERSONALITY_MAP = {
        "professional": ["serious", "introvert"],
        "active": ["outgoing", "active"],
        "artistic": ["introvert", "creative"],
        "casual": ["balanced", "outgoing"],
    }
    
    expected_personalities = STYLE_PERSONALITY_MAP.get(photo_style, [])
    
    if claimed_style not in expected_personalities:
        return {"valid": False, "severity": "low", 
                "photo_style": photo_style, "claimed_style": claimed_style}
    
    return {"valid": True}
```

#### 规则七：地理轨迹一致性验证

```python
# 验证用户声称的地理位置与实际签到/活跃轨迹
def validate_location_trajectory(user_id, db):
    # 获取用户声称的位置
    claimed_location = user.location
    
    # 获取用户地理轨迹（如果有）
    geo_events = db.query(GeoLocationEventDB).filter(
        GeoLocationEventDB.user_id == user_id,
        GeoLocationEventDB.created_at >= datetime.now() - timedelta(days=30)
    ).all()
    
    if not geo_events:
        return {"valid": True, "note": "无地理轨迹数据"}
    
    # 分析主要活跃区域
    locations = [e.location for e in geo_events]
    primary_location = analyze_primary_location(locations)
    
    # 对比声称位置
    if claimed_location != primary_location:
        # 检查是否在合理范围内（同城不同区）
        distance = calculate_location_distance(claimed_location, primary_location)
        
        if distance > 50:  # 超过50公里
            return {"valid": False, "severity": "high",
                    "claimed": claimed_location, "actual": primary_location}
    
    return {"valid": True}
```

---

## 二、动态权重优化系统

### 2.1 用户群体差异化权重

```python
# 不同用户群体使用不同的权重配置
USER_GROUP_WEIGHTS = {
    "new_user": {  # 新用户（注册 < 7天）
        "base_score": 0.2,
        "identity": 0.30,   # 身份验证更重要
        "cross_validation": 0.25,
        "behavior": 0.10,   # 行为数据不足
        "social": 0.15,
        "time": 0.0,        # 无时间积累
    },
    "active_user": {  # 活跃用户（注册 > 30天，活跃 > 10天）
        "base_score": 0.3,
        "identity": 0.20,
        "cross_validation": 0.20,
        "behavior": 0.20,   # 行为数据更丰富
        "social": 0.15,
        "time": 0.15,       # 时间积累有贡献
    },
    "verified_user": {  # 已认证用户
        "base_score": 0.35,
        "identity": 0.15,   # 身份已验证，权重降低
        "cross_validation": 0.25,
        "behavior": 0.20,
        "social": 0.20,
        "time": 0.10,
    },
    "vip_user": {  # VIP 会员
        "base_score": 0.4,
        "identity": 0.20,
        "cross_validation": 0.20,
        "behavior": 0.15,
        "social": 0.15,
        "time": 0.10,
    },
}

def get_user_group(user):
    """判断用户所属群体"""
    if user.created_at < datetime.now() - timedelta(days=7):
        return "new_user"
    
    if user.membership_tier in ["premium", "vip"]:
        return "vip_user"
    
    if user.identity_verified:
        return "verified_user"
    
    if user.created_at > datetime.now() - timedelta(days=30) and user.active_days > 10:
        return "active_user"
    
    return "new_user"
```

### 2.2 基于反馈学习的权重优化

```python
# 用户反馈驱动的权重调整
class WeightOptimizer:
    """基于用户反馈优化置信度权重"""
    
    def __init__(self):
        self.feedback_history = []
        self.current_weights = CONFIDENCE_WEIGHTS.copy()
    
    def record_feedback(self, user_id, predicted_confidence, actual_trustworthiness):
        """
        记录预测结果与实际可信度的对比
        
        actual_trustworthiness 来源：
        - 用户举报/封禁记录 → 低可信度
        - 用户好评/成功约会 → 高可信度
        - 用户投诉虚假信息 → 低可信度
        """
        self.feedback_history.append({
            "user_id": user_id,
            "predicted": predicted_confidence,
            "actual": actual_trustworthiness,
            "timestamp": datetime.now(),
        })
    
    def optimize_weights(self):
        """
        使用历史反馈优化权重
        
        方法：梯度下降，最小化预测误差
        """
        if len(self.feedback_history) < 100:
            return self.current_weights
        
        # 计算各维度的预测误差
        dimension_errors = {}
        for dimension in ["identity", "cross_validation", "behavior", "social", "time"]:
            errors = []
            for record in self.feedback_history:
                # 获取该维度的实际值
                dimension_value = get_dimension_value(record["user_id"], dimension)
                predicted_contribution = dimension_value * self.current_weights[dimension]
                
                # 计算误差
                error = abs(record["predicted"] - record["actual"])
                errors.append(error * predicted_contribution)
            
            dimension_errors[dimension] = sum(errors) / len(errors)
        
        # 调整权重（误差大的维度减少权重）
        total_error = sum(dimension_errors.values())
        for dimension in self.current_weights:
            if dimension != "base_score":
                # 按误差比例调整权重
                adjustment = -0.01 * (dimension_errors[dimension] / total_error)
                new_weight = self.current_weights[dimension] + adjustment
                # 确保权重在合理范围
                new_weight = max(0.05, min(0.35, new_weight))
                self.current_weights[dimension] = new_weight
        
        return self.current_weights
```

---

## 三、LLM 深度验证系统

### 3.1 文本一致性分析

```python
class LLMConfidenceAnalyzer:
    """使用 LLM 进行深度文本分析"""
    
    async def analyze_profile_text_consistency(self, user_id, db):
        """
        分析用户描述文本的一致性
        
        检查：
        - bio 描述与性格测试结果的一致性
        - 自述兴趣与浏览行为的一致性
        - 描述的价值观与实际行为的一致性
        """
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        
        # 收集用户文本数据
        profile_text = user.bio or ""
        interests_text = ", ".join(json.loads(user.interests or "[]"))
        
        # 收集聊天文本样本
        chat_messages = db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user_id
        ).order_by(ChatMessageDB.created_at.desc()).limit(20).all()
        chat_text = "\n".join([m.content for m in chat_messages])
        
        # 使用 LLM 分析
        prompt = f"""
分析以下用户信息的内部一致性：

【个人简介】
{profile_text}

【声称兴趣】
{interests_text}

【聊天样本】
{chat_text[:500]}

请判断：
1. 个人简介与聊天风格是否一致？（如简介说"内向"但聊天很活跃）
2. 声称兴趣与聊天话题是否匹配？
3. 是否存在虚假夸大的迹象？

返回 JSON：
{
    "bio_chat_consistency": 0.8,  // 0-1
    "interest_chat_match": 0.7,   // 0-1
    "authenticity_score": 0.85,   // 0-1，综合真实性判断
    "red_flags": ["简介说内向但聊天很外向"],
    "confidence_boost_suggestions": ["补充兴趣相关的照片"]
}
"""
        
        result = await llm_client.chat(prompt)
        return result
    
    async def analyze_age_from_language(self, messages):
        """
        从语言风格推断用户年龄段
        
        特征：
        - 年轻人（18-25）：网络用语、表情包、流行梗
        - 青年（25-35）：职场话题、成长焦虑、社交话题
        - 中年（35-45）：家庭话题、理财、健康
        - 中老年（45+）：养生、子女、怀旧
        """
        text = "\n".join([m.content for m in messages[:30]])
        
        prompt = f"""
分析以下聊天文本，推断用户的年龄段：

{text}

返回 JSON：
{
    "inferred_age_bracket": "young",  // young/young_adult/middle/senior
    "confidence": 0.8,
    "evidence": ["使用网络用语'yyds'", "提到'毕业找工作'"]
}
"""
        
        return await llm_client.chat(prompt)
```

### 3.2 价值观深度推断

```python
async def infer_deep_values(self, user_id, db):
    """
    从行为和聊天推断用户深层价值观
    
    推断维度：
    - 家庭观念：传统/现代/独立
    - 金钱观念：节俭/适度/享乐
    - 事业态度：进取/稳定/自由
    - 情感需求：独立/依赖/平衡
    """
    # 收集证据数据
    evidence = await self.collect_value_evidence(user_id, db)
    
    prompt = f"""
基于以下证据推断用户的价值观倾向：

【浏览偏好】
- 最常查看的用户类型：{evidence['browse_preference']}
- 常浏览的职业类型：{evidence['occupation_preference']}
- 常浏览的收入范围：{evidence['income_preference']}

【聊天话题】
- 家庭话题频率：{evidence['family_topic_rate']}
- 金钱话题频率：{evidence['money_topic_rate']}
- 事业话题频率：{evidence['career_topic_rate']}

【行为特征】
- 活跃时间分布：{evidence['active_time_pattern']}
- 互动类型偏好：{evidence['interaction_preference']}

推断价值观倾向，返回 JSON：
{
    "family_value": {"tendency": "modern", "confidence": 0.7},
    "money_value": {"tendency": "moderate", "confidence": 0.6},
    "career_value": {"tendency": "stable", "confidence": 0.8},
    "emotional_need": {"tendency": "independent", "confidence": 0.5},
    "overall_consistency": 0.75  // 与声称价值观的一致性
}
"""
    
    return await llm_client.chat(prompt)
```

---

## 四、实时置信度更新机制

### 4.1 事件驱动的置信度更新

```python
class ConfidenceUpdateTrigger:
    """置信度实时更新触发器"""
    
    # 触发规则配置
    UPDATE_TRIGGERS = {
        # 高优先级：立即更新
        "identity_verified": {"priority": "high", "delay": 0},
        "report_received": {"priority": "high", "delay": 0},
        "badge_earned": {"priority": "high", "delay": 0},
        "profile_updated": {"priority": "high", "delay": 0},
        
        # 中优先级：延迟更新
        "behavior_pattern_change": {"priority": "medium", "delay": 300},  # 5分钟后
        "feedback_received": {"priority": "medium", "delay": 0},
        
        # 低优先级：批量更新
        "daily_active": {"priority": "low", "delay": 3600},  # 1小时后
        "chat_completed": {"priority": "low", "delay": 600},  # 10分钟后
    }
    
    async def on_event(self, event_type, user_id, event_data):
        """处理置信度更新事件"""
        trigger_config = self.UPDATE_TRIGGERS.get(event_type)
        if not trigger_config:
            return
        
        priority = trigger_config["priority"]
        delay = trigger_config["delay"]
        
        if priority == "high":
            # 立即更新
            await self._immediate_update(user_id, event_type, event_data)
        elif priority == "medium":
            # 延迟更新（放入队列）
            await self._delayed_update(user_id, event_type, event_data, delay)
        else:
            # 批量更新（标记待更新）
            await self._mark_for_batch_update(user_id, event_type)
    
    async def _immediate_update(self, user_id, event_type, event_data):
        """立即更新置信度"""
        service = ProfileConfidenceService()
        result = service.evaluate_user_confidence(
            user_id=user_id,
            trigger_source=f"event_{event_type}"
        )
        
        # 发送通知（如果置信度有显著变化）
        if result.get("confidence_change", 0) > 0.1:
            await self._notify_confidence_change(user_id, result)
    
    async def _delayed_update(self, user_id, event_type, event_data, delay):
        """延迟更新（使用任务队列）"""
        from agent.autonomous.task_queue import task_queue
        
        task_queue.add_task(
            task_type="confidence_update",
            user_id=user_id,
            trigger=event_type,
            scheduled_at=datetime.now() + timedelta(seconds=delay)
        )
```

### 4.2 行为模式变化检测

```python
class BehaviorPatternDetector:
    """检测用户行为模式的变化"""
    
    def detect_pattern_change(self, user_id, db):
        """
        检测行为模式变化
        
        变化类型：
        - 兴趣变化：浏览类型分布显著变化
        - 时间变化：活跃时间分布变化（如从晚上改到早上）
        - 互动变化：互动类型偏好变化
        """
        # 获取历史行为统计（最近30天 vs 前30天）
        current_period = datetime.now() - timedelta(days=30)
        previous_period = datetime.now() - timedelta(days=60)
        
        current_stats = self._get_behavior_stats(user_id, current_period, current_period + timedelta(days=30), db)
        previous_stats = self._get_behavior_stats(user_id, previous_period, previous_period + timedelta(days=30), db)
        
        changes = []
        
        # 检测兴趣变化
        interest_change = self._compare_interest_distribution(current_stats, previous_stats)
        if interest_change["change_rate"] > 0.3:  # 30%以上变化
            changes.append({
                "type": "interest_change",
                "severity": "medium",
                "detail": f"兴趣分布变化 {interest_change['change_rate']*100:.0f}%",
            })
        
        # 检测时间变化
        time_change = self._compare_active_time(current_stats, previous_stats)
        if time_change["shift_hours"] > 3:  # 时间偏移超过3小时
            changes.append({
                "type": "time_change",
                "severity": "low",
                "detail": f"活跃时间偏移 {time_change['shift_hours']}小时",
            })
        
        return changes
```

---

## 五、前端完整实现

### 5.1 置信度管理页面

```tsx
// ConfidenceManagementPage.tsx
// 用户查看和管理自己置信度的完整页面

import React, { useState, useEffect } from 'react'
import { Card, Progress, Tag, List, Button, Modal, Tabs, Empty, Spin } from 'antd'
import {
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  StarFilled,
  ReloadOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import ConfidenceBadge, { ConfidenceDetailModal } from '@/components/ConfidenceBadge'
import confidenceApi from '@/api/confidenceClient'

const ConfidenceManagementPage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [history, setHistory] = useState([])
  const [explainVisible, setExplainVisible] = useState(false)

  useEffect(() => {
    loadConfidenceData()
  }, [])

  const loadConfidenceData = async () => {
    setLoading(true)
    try {
      const [detailRes, recRes] = await Promise.all([
        confidenceApi.getConfidenceDetail(),
        confidenceApi.getVerificationRecommendations(),
      ])
      setDetail(detailRes)
      setRecommendations(recRes.recommendations || [])
      setHistory(detailRes.confidence_history || [])
    } catch (error) {
      console.error('Failed to load confidence data:', error)
    } finally {
      setLoading(false)
  }

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await confidenceApi.refreshConfidence(true)
      await loadConfidenceData()
    } catch (error) {
      console.error('Refresh failed:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="confidence-management-page">
      {loading ? (
        <div className="loading-container">
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* 总置信度卡片 */}
          <Card className="overall-card">
            <div className="overall-header">
              <SafetyCertificateOutlined className="overall-icon" />
              <div className="overall-info">
                <h2>我的可信度</h2>
                <ConfidenceBadge data={detail} size="large" showPercent />
              </div>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                重新评估
              </Button>
            </div>
            
            <Progress
              percent={Math.round(detail.overall_confidence * 100)}
              strokeColor="#1890ff"
              trailColor="#f0f0f0"
              strokeWidth={16}
            />
          </Card>

          {/* 各维度评估 */}
          <Card title="各维度评估" className="dimensions-card">
            <div className="dimensions-grid">
              {Object.entries(detail.dimensions).map(([key, value]) => (
                <div className="dimension-item" key={key}>
                  <div className="dimension-header">
                    <span className="dimension-name">
                      {DIMENSION_NAMES[key]}
                    </span>
                    <span className="dimension-value">
                      {Math.round(value * 100)}%
                    </span>
                  </div>
                  <Progress
                    percent={Math.round(value * 100)}
                    strokeColor={value > 0.6 ? '#52c41a' : value > 0.4 ? '#1890ff' : '#fa8c16'}
                    size="small"
                  />
                  <Button size="small" type="link">
                    如何提升？
                  </Button>
                </div>
              ))}
            </div>
          </Card>

          {/* 异常标记 */}
          <Card 
            title={
              <span>
                信息一致性检查
                {Object.keys(detail.cross_validation_flags).length > 0 && (
                  <Tag color="warning" style={{ marginLeft: 8 }}>
                    {Object.keys(detail.cross_validation_flags).length} 项异常
                  </Tag>
                )}
              </span>
            }
            className="flags-card"
          >
            {Object.keys(detail.cross_validation_flags).length === 0 ? (
              <Empty description="无异常标记" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                dataSource={Object.entries(detail.cross_validation_flags)}
                renderItem(([key, flag]) => (
                  <List.Item className={`flag-item ${flag.severity}`}>
                    <WarningOutlined style={{ color: flag.severity === 'high' ? '#ff4d4f' : '#faad14' }} />
                    <div className="flag-content">
                      <div className="flag-title">{FLAG_NAMES[key]}</div>
                      <div className="flag-detail">{flag.detail}</div>
                    </div>
                    <Button size="small" type="link">
                      如何修复？
                    </Button>
                  </List.Item>
                )}
              />
            )}
          </Card>

          {/* 验证建议 */}
          <Card title="提升建议" className="recommendations-card">
            <List
              dataSource={recommendations}
              renderItem={(rec) => (
                <List.Item className={`recommendation-item ${rec.priority}`}>
                  <div className="rec-icon">
                    {rec.priority === 'high' ? '🔴' : rec.priority === 'medium' ? '🟡' : '🟢'}
                  </div>
                  <div className="rec-content">
                    <div className="rec-title">{RECOMMENDATION_NAMES[rec.type]}</div>
                    <div className="rec-reason">{rec.reason}</div>
                    <div className="rec-impact">
                      <StarFilled style={{ color: '#faad14' }} />
                      预估提升 +{Math.round(rec.estimated_confidence_boost * 100)}%
                    </div>
                  </div>
                  <Button size="small" type="primary">
                    立即完成
                  </Button>
                </List.Item>
              )}
            />
          </Card>

          {/* 历史记录 */}
          <Card title="置信度变化历史" className="history-card">
            <List
              dataSource={history.slice(-10)}
              renderItem={(record) => (
                <List.Item>
                  <span className="history-time">
                    {new Date(record.at).toLocaleDateString()}
                  </span>
                  <span className="history-change">
                    {record.change > 0 ? '+' : ''}{Math.round(record.change * 100)}%
                  </span>
                  <span className="history-reason">
                    {TRIGGER_NAMES[record.trigger]}
                  </span>
                </List.Item>
              )}
            />
          </Card>

          {/* 解释系统 */}
          <Button
            type="link"
            icon={<QuestionCircleOutlined />}
            onClick={() => setExplainVisible(true)}
          >
            置信度系统是如何工作的？
          </Button>

          <ExplainModal visible={explainVisible} onClose={() => setExplainVisible(false)} />
        </>
      )}
    </div>
  )
}

export default ConfidenceManagementPage
```

### 5.2 匹配列表置信度筛选

```tsx
// ConfidenceFilter.tsx
// 在匹配列表中按置信度筛选

import React from 'react'
import { Select, Slider, Tag } from 'antd'

interface ConfidenceFilterProps {
  value: { min: number; level?: string }
  onChange: (value: { min: number; level?: string }) => void
}

const ConfidenceFilter: React.FC<ConfidenceFilterProps> = ({ value, onChange }) => {
  const levelOptions = [
    { value: 'all', label: '全部' },
    { value: 'very_high', label: '极可信 (80%+)', color: '#faad14' },
    { value: 'high', label: '较可信 (60%+)', color: '#52c41a' },
    { value: 'medium', label: '普通用户 (40%+)', color: '#1890ff' },
    { value: 'verified_only', label: '仅已认证', color: '#722ed1' },
  ]

  return (
    <div className="confidence-filter">
      <Select
        value={value.level || 'all'}
        onChange={(level) => onChange({ min: getMinByLevel(level), level })}
        options={levelOptions}
        optionRender={(option) => (
          <span>
            {option.data.color && (
              <Tag color={option.data.color} style={{ marginRight: 4 }}>
                {LEVEL_ICONS[option.value]}
              </Tag>
            )}
            {option.data.label}
          </span>
        )}
      />
      
      <Slider
        min={0}
        max={100}
        value={value.min}
        onChange={(min) => onChange({ min })}
        marks={{
          0: '不限',
          40: '普通',
          60: '较可信',
          80: '极可信',
        }}
        tooltipFormatter={(value) => `${value}%`}
      />
    </div>
  )
}

export default ConfidenceFilter
```

---

## 六、用户反馈闭环

### 6.1 反馈收集机制

```python
class ConfidenceFeedbackCollector:
    """收集用户对置信度判断的反馈"""
    
    async def collect_match_feedback(self, user_id, match_user_id, feedback_type, detail):
        """
        收集匹配后的反馈
        
        feedback_type:
        - "accurate": 置信度判断准确
        - "inaccurate_high": 对方可信度被高估（实际不可信）
        - "inaccurate_low": 对方可信度被低估（实际可信）
        - "fake_info": 发现对方信息造假
        """
        db = SessionLocal()
        
        try:
            # 记录反馈
            feedback = ConfidenceFeedbackDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_user_id=match_user_id,
                feedback_type=feedback_type,
                detail=detail,
                created_at=datetime.now(),
            )
            db.add(feedback)
            
            # 根据反馈调整权重
            if feedback_type == "inaccurate_high":
                # 置信度被高估 → 可能某个维度权重过高
                await self._analyze_overestimation(match_user_id, db)
            
            elif feedback_type == "inaccurate_low":
                # 置信度被低估 → 可能某个维度权重过低
                await self._analyze_underestimation(match_user_id, db)
            
            elif feedback_type == "fake_info":
                # 发现虚假信息 → 标记异常并降级
                await self._mark_fake_info(match_user_id, detail, db)
            
            db.commit()
            
        finally:
            db.close()
    
    async def _analyze_overestimation(self, user_id, db):
        """分析为何置信度被高估"""
        # 获取该用户的置信度详情
        detail = db.query(ProfileConfidenceDetailDB).filter(
            ProfileConfidenceDetailDB.user_id == user_id
        ).first()
        
        if detail:
            # 记录高估案例
            overestimate_log = OverestimateAnalysisDB(
                user_id=user_id,
                predicted_confidence=detail.overall_confidence,
                dimensions_snapshot=json.dumps({
                    "identity": detail.identity_confidence,
                    "cross_validation": detail.cross_validation_confidence,
                    "behavior": detail.behavior_consistency,
                    "social": detail.social_endorsement,
                }),
                analyzed_at=datetime.now(),
            )
            db.add(overestimate_log)
```

### 6.2 反馈驱动的规则优化

```python
class RuleOptimizer:
    """基于反馈优化交叉验证规则"""
    
    def optimize_age_education_rule(self):
        """
        基于反馈优化年龄-学历验证规则
        
        场景：很多用户反馈"年龄-学历不匹配"标记不准确
        
        分析：
        - 统计被标记为异常但实际可信的案例比例
        - 调整宽容度（如 -2年 放宽到 -3年）
        - 调整异常阈值
        """
        db = SessionLocal()
        
        # 获取反馈案例
        feedbacks = db.query(ConfidenceFeedbackDB).filter(
            ConfidenceFeedbackDB.feedback_type == "inaccurate_flag",
            ConfidenceFeedbackDB.detail.contains("age_education"),
        ).all()
        
        if len(feedbacks) < 50:
            return  # 样本不足
        
        # 分析误报率
        false_positive_rate = len(feedbacks) / db.query(
            ProfileConfidenceDetailDB.cross_validation_flags.contains("age_education_mismatch")
        ).count()
        
        if false_positive_rate > 0.3:  # 误报率超过30%
            # 调整规则配置
            rule = db.query(CrossValidationRuleDB).filter(
                CrossValidationRuleDB.rule_key == "age_education_match"
            ).first()
            
            current_config = json.loads(rule.rule_config)
            
            # 放宽容忍度
            current_config["tolerance_years"] = current_config.get("tolerance_years", 2) + 1
            
            # 降低异常阈值
            rule.anomaly_threshold = rule.anomaly_threshold * 0.9
            
            rule.rule_config = json.dumps(current_config)
            rule.updated_at = datetime.now()
            
            db.commit()
            
            logger.info(f"Age-education rule optimized: tolerance increased to {current_config['tolerance_years']} years")
```

---

## 七、实施计划

### Phase 1: 规则扩展（1周）

| 任务 | 预估时间 |
|------|---------|
| 实现兴趣-浏览一致性验证 | 2天 |
| 实现照片-画像风格验证 | 2天 |
| 实现年龄-自报一致性验证 | 1天 |
| 单元测试编写 | 2天 |

### Phase 2: 动态权重（1周）

| 任务 | 预估时间 |
|------|---------|
| 用户群体差异化权重 | 2天 |
| 权重优化器实现 | 2天 |
| A/B 测试框架搭建 | 2天 |
| 数据收集与分析 | 1天 |

### Phase 3: LLM 验证（2周）

| 任务 | 预估时间 |
|------|---------|
| 文本一致性分析服务 | 3天 |
| 年龄语言推断服务 | 2天 |
| 价值观深度推断服务 | 3天 |
| 与现有系统集成 | 2天 |
| 测试与调优 | 4天 |

### Phase 4: 前端完善（1周）

| 任务 | 预估时间 |
|------|---------|
| 置信度管理页面 | 2天 |
| 置信度筛选组件 | 1天 |
| 匹配详情置信度展示 | 1天 |
| 反馈收集界面 | 2天 |

### Phase 5: 实时更新（1周）

| 任务 | 预估时间 |
|------|---------|
| 事件驱动触发器 | 2天 |
| 行为模式检测器 | 2天 |
| 任务队列集成 | 1天 |
| 性能测试 | 2天 |

### Phase 6: 反馈闭环（1周）

| 任务 | 预估时间 |
|------|---------|
| 反馈收集 API | 2天 |
| 规则优化器 | 2天 |
| 权重自适应调整 | 2天 |
| 监控与告警 | 1天 |

---

## 八、技术风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|---------|
| LLM 响应慢影响用户体验 | 高 | 异步处理，缓存结果，置信度预计算 |
| 用户反感被"评判" | 中 | 强调"帮助识别可信对象"，而非"评判你" |
| 规则误报引发投诉 | 高 | 反馈闭环快速调整，误报补偿机制 |
| 权重优化不稳定 | 中 | 小步迭代，A/B 测试验证，回滚机制 |
| 隐私合规风险 | 高 | 置信度仅展示摘要，不暴露具体证据 |

---

是否需要我开始实施某个阶段的细化方案？建议从 **Phase 1（规则扩展）** 开始，这是最直接的改进。